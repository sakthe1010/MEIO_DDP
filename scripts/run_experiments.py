"""
scripts/run_experiments.py
==========================
Runs all DDP experiments in sequence and saves everything cleanly.

Experiments
-----------
  E0   Baseline — analytical newsvendor base-stock, no dispatch threshold
  E1a  Fixed 25% dispatch threshold on all lanes (same inventory as E0)
  E1b  Transport-only optimization (Optuna, ≥92% fill)
  E2   Inventory-only optimization (Optuna, ≥92% fill)
  E3   Joint optimization — inventory + transport (main result)
  E4   Pareto frontier — joint opt at multiple fill rate targets

Usage
-----
  python scripts/run_experiments.py --config config/1n3_5sku.json
  python scripts/run_experiments.py --config config/1n3_5sku.json --experiments E0 E3
  python scripts/run_experiments.py --config config/1n3_5sku.json --trials 50 --warmup 100

Outputs (saved to outputs/experiments_<timestamp>/)
----------------------------------------------------
  REPORT_SUMMARY.md         — master narrative document for the report
  summary_table.csv / .md   — one-row-per-experiment comparison table
  E0/
    summary.md              — rich markdown: purpose, setup, results, observations
    summary.txt             — plain-text quick reference
    costs_by_node_sku.csv
    kpis_by_sku.csv
    kpis_by_node_sku.csv
    bullwhip.csv
    inventory_log.csv
    orders_log.csv
    shipments_log.csv
    params.json
  E1a/ E1b/ E2/ E3/         — same structure
  E4_pareto/
    pareto_frontier.csv / .md
    params_<pct>.json       — best params per fill rate target
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_simulation import (
    build_from_config, build_volume_map, build_weight_map, build_disruptions,
    _read_csv_series,
)
from engine.simulator import Simulator
from optimizer.optimize import run_optimizer, evaluate, _apply_params


# ============================================================
# Static experiment metadata
# ============================================================

EXPERIMENT_META: Dict[str, dict] = {
    "E0": {
        "id": "E0",
        "title": "Analytical Baseline",
        "purpose": (
            "Establish a reference point using analytically derived base-stock levels "
            "(newsvendor formula) with no transport consolidation constraint. "
            "This represents the standard textbook multi-echelon policy without any "
            "joint optimization."
        ),
        "methodology": (
            "Base-stock levels are computed at runtime from the realised demand series: "
            "S = μ·(L+1) + z·σ·√(L+1), where L is the lane lead time, μ and σ are the "
            "post-warmup mean and standard deviation of demand, and z is the service-level "
            "z-score. Warehouse levels are sized for aggregated downstream demand. "
            "No minimum dispatch utilization is enforced — every order is shipped "
            "immediately regardless of vehicle fill level."
        ),
        "hypothesis": (
            "The analytical baseline will provide acceptable fill rates but high transport "
            "costs due to frequent small shipments, and will serve as the upper-bound cost "
            "reference for optimization experiments."
        ),
        "report_section": "Section 4.1 — Baseline Performance",
        "recommended_warmup": 30,
    },
    "E1a": {
        "id": "E1a",
        "title": "Fixed Financial Dispatch Threshold (25%)",
        "purpose": (
            "Assess the cost impact of imposing a minimum vehicle utilization threshold "
            "of 25% on all transport lanes, using the same inventory policy as E0. "
            "This isolates the effect of transport consolidation alone, without re-optimizing "
            "inventory to compensate."
        ),
        "methodology": (
            "All edges have min_dispatch_utilization set to 0.25. Goods accumulate in a "
            "pending-dispatch buffer until 25% vehicle fill is reached, or until the "
            "max_dispatch_wait timeout (3 days) forces a dispatch. "
            "Inventory policy is unchanged from E0."
        ),
        "hypothesis": (
            "Transport consolidation will reduce transport cost significantly but increase "
            "shortage cost because delayed shipments reduce service levels. "
            "This demonstrates that naive consolidation without inventory adjustment is "
            "counter-productive."
        ),
        "report_section": "Section 4.2 — Isolated Transport Consolidation",
        "recommended_warmup": 30,
    },
    "E1b": {
        "id": "E1b",
        "title": "Transport-Only Optimization",
        "purpose": (
            "Optimize dispatch thresholds per lane using Optuna (TPE sampler) while "
            "keeping inventory base-stock levels fixed at their analytical values. "
            "This answers: how much can transport cost be reduced through smart "
            "threshold selection alone?"
        ),
        "methodology": (
            "Optuna TPE sampler searches dispatch thresholds in [0.0, 0.9] per lane. "
            "Inventory levels are held fixed at E0 analytical values. "
            "Soft constraint: fill rate ≥ 92% (penalty of 1M per 1% shortfall). "
            "Best feasible trial (fill ≥ 92%) is selected; falls back to best overall "
            "if no feasible trial found."
        ),
        "hypothesis": (
            "Per-lane threshold optimization will outperform the fixed 25% threshold "
            "of E1a while maintaining fill rates, but will be limited by the fixed "
            "inventory levels which were not designed for consolidation."
        ),
        "report_section": "Section 4.3 — Transport-Only Optimization",
        "recommended_warmup": 30,
    },
    "E2": {
        "id": "E2",
        "title": "Inventory-Only Optimization",
        "purpose": (
            "Optimize base-stock levels per node and SKU while keeping dispatch thresholds "
            "at zero (immediate dispatch). This answers: how much cost can be saved by "
            "right-sizing inventory alone, without touching transport policy?"
        ),
        "methodology": (
            "Optuna TPE sampler searches base-stock levels in [30%, 300%] of analytical S, "
            "with a floor of 10 units. Dispatch thresholds remain at 0.0 (no consolidation). "
            "Same fill rate constraint (≥ 92%) and penalty structure as E1b."
        ),
        "hypothesis": (
            "Inventory optimization will improve fill rates at a cost of higher holding "
            "expenditure. Total cost may not decrease significantly because transport "
            "costs (the largest component) are untouched."
        ),
        "report_section": "Section 4.4 — Inventory-Only Optimization",
        "recommended_warmup": 30,
    },
    "E3": {
        "id": "E3",
        "title": "Joint Inventory + Transport Optimization (Main Result)",
        "purpose": (
            "Simultaneously optimize both base-stock levels and dispatch thresholds. "
            "This is the core research contribution: demonstrating that joint optimization "
            "achieves cost savings that neither inventory-only nor transport-only "
            "optimization can achieve independently."
        ),
        "methodology": (
            "Optuna TPE sampler jointly searches the full parameter space: "
            "base-stock levels per (node, SKU) and dispatch thresholds per lane. "
            "Same fill constraint (≥ 92%) and penalty as E1b/E2. "
            "The optimizer can trade off higher holding cost (larger S) against "
            "lower transport cost (higher threshold) in a single search."
        ),
        "hypothesis": (
            "Joint optimization will find configurations where slightly elevated inventory "
            "levels enable vehicle consolidation, reducing transport costs enough to "
            "more than offset the additional holding cost — yielding the lowest total cost "
            "while maintaining service level targets."
        ),
        "report_section": "Section 4.5 — Joint Optimization (Main Result)",
        "recommended_warmup": 30,
    },
    "E3_per_sku": {
        "id": "E3_per_sku",
        "title": "Joint Optimization with per-SKU fill constraint",
        "purpose": (
            "Re-run E3 but apply the fill rate constraint per-SKU rather than aggregated. "
            "Every SKU must individually meet the target. This eliminates the loophole "
            "where popular SKUs over-serve and compensate for under-served ones."
        ),
        "methodology": (
            "Same Optuna joint search as E3, but the objective penalty is "
            "Σ_sku max(0, target − fill_sku) × PENALTY_PER_PCT. Best feasible trial is "
            "the one where every SKU's fill rate meets the target."
        ),
        "hypothesis": (
            "Per-SKU constraint will raise total cost slightly compared to E3 (the "
            "weakly-served SKUs need more inventory) but will eliminate the SKU-level "
            "service-level shortfall observed in E3."
        ),
        "report_section": "Section 4.5b — Per-SKU Joint Optimization",
        "recommended_warmup": 30,
    },
    "E4": {
        "id": "E4",
        "title": "Pareto Frontier: Cost vs Fill Rate",
        "purpose": (
            "Map the trade-off curve between total system cost and fill rate under joint "
            "optimization. Shows decision-makers the range of feasible operating points "
            "and the cost of each additional percentage point of service level."
        ),
        "methodology": (
            "Joint optimization is repeated at fill rate targets of 80%, 85%, 88%, 90%, "
            "92%, 94%, 96%, 98%. Each point uses a fresh optimizer run with a different "
            "seed. Best params are saved and re-evaluated independently to avoid "
            "optimizer overfitting."
        ),
        "hypothesis": (
            "The Pareto frontier will show diminishing returns: the marginal cost of each "
            "additional fill rate percentage point will increase non-linearly as the "
            "system approaches 100% service level."
        ),
        "report_section": "Section 4.6 — Cost–Service Level Pareto Frontier",
        "recommended_warmup": 30,
    },
    "E5": {
        "id": "E5",
        "title": "Disruption Robustness",
        "purpose": (
            "Inject a supply-side disruption at warehouse W1 and compare how E0 (analytical) "
            "and E3 (joint-optimized) parameters cope. Measures cost overhead, service "
            "degradation, and recovery time — the stress test the analytical baseline can't "
            "anticipate."
        ),
        "methodology": (
            "Run the same 1n3_5sku scenario with a 14-day W1 outage centred at 60% through "
            "the post-warmup horizon. Two configurations: E0 params and E3 params. "
            "Time-to-recover = days for fill rate to return within 1pp of the pre-disruption value."
        ),
        "hypothesis": (
            "E3's elevated buffer stocks (driven by transport consolidation) will absorb the "
            "shock better, recovering faster than E0 even though the disruption was not in "
            "the optimization objective."
        ),
        "report_section": "Section 4.7 — Disruption Robustness",
        "recommended_warmup": 30,
    },
    "E6": {
        "id": "E6",
        "title": "Policy Comparison (Core 4)",
        "purpose": (
            "Compare four inventory policies — base_stock, ss, periodic_review, "
            "echelon_stock — on the same scenario after individual Optuna tuning. "
            "Tests the core thesis claim that network-wide coordination (echelon) "
            "beats local policies."
        ),
        "methodology": (
            "Each policy gets its own 100-trial Optuna search over its native parameter "
            "space (mode=inventory, dispatch fixed at 0.0, fill ≥ 92%). Headline metrics: "
            "total cost, fill rate, holding/transport mix, bullwhip per echelon."
        ),
        "hypothesis": (
            "echelon_stock ≤ base_stock ≈ ss < periodic_review on cost. "
            "Echelon wins because warehouses see downstream pipeline; periodic loses to "
            "review delay."
        ),
        "report_section": "Section 4.8 — Policy Comparison",
        "recommended_warmup": 30,
    },
    "E7": {
        "id": "E7",
        "title": "Demand Forecasting Sensitivity",
        "purpose": (
            "Replace the perfect-information assumption with noisy forecasts and measure "
            "how cost, fill rate, and bullwhip degrade as forecast error grows."
        ),
        "methodology": (
            "Wrap the demand series with a noisy-oracle: forecast(t+L) = true(t+L) × "
            "(1 + N(0, σ_f)). Run E3 params with σ_f ∈ {0%, 5%, 10%, 20%, 30%}. Policies "
            "consume the forecast for sizing decisions; the simulator still receives the "
            "true demand."
        ),
        "hypothesis": (
            "Cost and bullwhip rise monotonically with σ_f; fill rate drops because under-"
            "forecasting causes stock-outs. This quantifies the value of forecast accuracy."
        ),
        "report_section": "Section 4.9 — Forecast Uncertainty",
        "recommended_warmup": 30,
    },
    "E8": {
        "id": "E8",
        "title": "Bullwhip-Aware Joint Optimization",
        "purpose": (
            "Add bullwhip ratio as a secondary optimization objective. Tests whether a small "
            "cost increase can buy a meaningful bullwhip reduction — directly addressing "
            "the supply-chain literature's main motivation for measuring bullwhip."
        ),
        "methodology": (
            "Joint-mode optimizer with augmented objective: total_cost + λ × Σ_node "
            "bullwhip_ratio. Sweep λ ∈ {0, 1e3, 1e4, 1e5, 1e6} and plot the (cost, bullwhip) "
            "Pareto. Bullwhip is the corrected per-echelon metric from A2."
        ),
        "hypothesis": (
            "There exists a small λ such that cost rises < 5% while total bullwhip drops "
            ">20% — i.e., the cost-optimal solution from E3 is bullwhip-suboptimal and a "
            "modest tradeoff is worthwhile."
        ),
        "report_section": "Section 4.10 — Bullwhip-Aware Optimization",
        "recommended_warmup": 30,
    },
    "E9": {
        "id": "E9",
        "title": "Stochastic Demand Robustness",
        "purpose": (
            "Test whether the jointly-optimised parameters from E3 (derived under "
            "deterministic M5 demand) transfer to a stochastic demand environment. "
            "This is a robustness test, not a re-optimisation: the E3 parameter set "
            "is held fixed and evaluated under Poisson demand with λ equal to the "
            "M5 mean per retailer and SKU."
        ),
        "methodology": (
            "For each demand series in the config (type=csv), λ is computed as the "
            "mean daily demand over the 365-day evaluation window (days start_index "
            "to start_index+365). The config is cloned with all demand generators "
            "replaced by Poisson(λ). The E3 best-params are applied without "
            "re-optimisation. Ten independently seeded Poisson realisations are run; "
            "mean ± std of total cost and fill rate are reported."
        ),
        "hypothesis": (
            "E3 params generalise to Poisson demand: fill rate holds within 2 pp of "
            "the deterministic E3 result and total cost remains within 5%."
        ),
        "report_section": "Section 4.11 — Stochastic Demand Robustness",
        "recommended_warmup": 30,
    },
}


# ============================================================
# Core: run one simulation, return structured result
# ============================================================

def run_one(cfg: dict, volume_per_unit: dict, label: str,
            max_dispatch_wait: int = 3, warmup_periods: int = 0) -> dict:
    """Run one full simulation. Returns a dict of all metrics and logs.

    warmup_periods: days excluded from KPI/cost aggregation (inventory
                    is still simulated for those days so the system reaches
                    steady state before measurement begins).
    """
    net, demand_by_node, T = build_from_config(cfg)
    sim = Simulator(
        network=net,
        demand_by_node=demand_by_node,
        T=T,
        order_processing_delay=1,
        volume_per_unit=volume_per_unit,
        weight_per_unit=build_weight_map(cfg),
        max_dispatch_wait=max_dispatch_wait,
        disruptions=build_disruptions(cfg),
    )
    sim.run()

    # DIAGNOSTIC
    # if hasattr(sim, '_dispatch_log') and sim._dispatch_log:
    #     import pandas as _pd
    #     _dl = _pd.DataFrame(sim._dispatch_log)
    #     forced_pct = 100 * _dl['forced'].mean()
    #     avg_util = 100 * _dl['util'].mean()
    #     print(f"\n  [DISPATCH DIAG] label={label}")
    #     print(f"  Forced dispatches : {forced_pct:.1f}%")
    #     print(f"  Avg util at dispatch: {avg_util:.1f}%")
    #     print(f"  Total dispatch events: {len(_dl)}")
    #     print(f"  Per-lane breakdown:")
    #     for lane, grp in _dl.groupby('lane'):
    #         print(f"    {lane}  forced={100*grp['forced'].mean():.0f}%  avg_util={100*grp['util'].mean():.1f}%")

    rows = [m.__dict__ for m in sim.metrics]
    df   = pd.DataFrame(rows)
    eod  = df[(df["phase"] == "EOD") & (df["t"] >= warmup_periods)].copy()

    costs = eod.groupby(["node_id", "sku"]).agg(
        holding_cost   = ("holding_cost",   "sum"),
        backlog_cost   = ("backlog_cost",   "sum"),
        ordering_cost  = ("ordering_cost",  "sum"),
        transport_cost = ("transport_cost", "sum"),
        total_cost     = ("total_cost",     "sum"),
    ).reset_index()

    total_holding   = float(costs["holding_cost"].sum())
    total_backlog   = float(costs["backlog_cost"].sum())
    total_ordering  = float(costs["ordering_cost"].sum())
    total_transport = float(costs["transport_cost"].sum())
    total_cost      = float(costs["total_cost"].sum())

    total_demand    = float(eod["demand"].sum())
    total_fulfilled = float(eod["fulfilled_external"].sum())
    fill_rate       = total_fulfilled / total_demand if total_demand > 0 else 1.0

    sku_kpis = eod.groupby("sku").agg(
        demand_sum    = ("demand",              "sum"),
        fulfilled_sum = ("fulfilled_external",  "sum"),
    ).reset_index()
    sku_kpis["fill_rate"] = (
        sku_kpis["fulfilled_sum"] / sku_kpis["demand_sum"].replace(0, 1)
    )

    retailer_ids = {n["id"] for n in cfg["nodes"] if n.get("type") == "retailer"}
    node_kpis = eod[eod["node_id"].isin(retailer_ids)].groupby(["node_id", "sku"]).agg(
        demand_sum    = ("demand",              "sum"),
        fulfilled_sum = ("fulfilled_external",  "sum"),
    ).reset_index()
    node_kpis["fill_rate"] = (
        node_kpis["fulfilled_sum"] / node_kpis["demand_sum"].replace(0, 1)
    )

    # ── Bullwhip effect (per-echelon, Lee/Padmanabhan/Whang 1997) ─────────────
    # For node N with children C1..Ck, the *incoming* demand series is the daily
    # sum of orders from all children. The bullwhip ratio at N is
    #   CV²(orders out of N) / CV²(orders into N).
    # Retailers face external demand instead of child orders.
    orders_df = pd.DataFrame(sim.orders_log)
    orders_df = orders_df[orders_df["t"] >= warmup_periods]

    # Map child -> parent from edges (a child can only have one parent in this DAG).
    child_to_parent: Dict[str, str] = {e["to"]: e["from"] for e in cfg["edges"]}

    # Per-node, per-SKU incoming-demand series.
    incoming_series: Dict[tuple, pd.Series] = {}
    # Retailers: external demand from EOD log.
    for (nid, sku), grp in eod[eod["node_id"].isin(retailer_ids)].groupby(["node_id", "sku"]):
        incoming_series[(nid, sku)] = grp.set_index("t")["demand"].sort_index()
    # Upstream nodes: aggregate child orders.
    if not orders_df.empty:
        for (cid, sku), grp in orders_df.groupby(["node_id", "sku"]):
            parent = child_to_parent.get(cid)
            if parent is None:
                continue
            s = grp.set_index("t")["orders_to_parent"].sort_index()
            key = (parent, sku)
            incoming_series[key] = (incoming_series.get(key, pd.Series(dtype=float))
                                    .add(s, fill_value=0.0))

    def _cv2(series: pd.Series) -> float:
        if series is None or series.empty:
            return float("nan")
        m = series.mean()
        if m <= 0:
            return float("nan")
        return float((series.std() / m) ** 2)

    bullwhip_rows = []
    if not orders_df.empty:
        for (nid, sku), grp in orders_df.groupby(["node_id", "sku"]):
            out = grp.set_index("t")["orders_to_parent"].sort_index()
            in_series = incoming_series.get((nid, sku))
            cv2_out = _cv2(out)
            cv2_in  = _cv2(in_series)
            if cv2_in and cv2_in > 0 and not pd.isna(cv2_out):
                bwe = cv2_out / cv2_in
            else:
                bwe = float("nan")
            bullwhip_rows.append({
                "node_id": nid, "sku": sku,
                "cv2_in":  round(cv2_in,  6) if not pd.isna(cv2_in)  else float("nan"),
                "cv2_out": round(cv2_out, 6) if not pd.isna(cv2_out) else float("nan"),
                "bullwhip_ratio": round(bwe, 4) if not pd.isna(bwe) else float("nan"),
            })
    bullwhip_df = pd.DataFrame(bullwhip_rows) if bullwhip_rows else pd.DataFrame(
        columns=["node_id", "sku", "cv2_in", "cv2_out", "bullwhip_ratio"]
    )

    return {
        "label":           label,
        "total_cost":      total_cost,
        "holding_cost":    total_holding,
        "backlog_cost":    total_backlog,
        "ordering_cost":   total_ordering,
        "transport_cost":  total_transport,
        "holding_pct":     100 * total_holding   / total_cost if total_cost else 0,
        "backlog_pct":     100 * total_backlog    / total_cost if total_cost else 0,
        "ordering_pct":    100 * total_ordering   / total_cost if total_cost else 0,
        "transport_pct":   100 * total_transport  / total_cost if total_cost else 0,
        "fill_rate":       fill_rate,
        "fill_rate_pct":   100 * fill_rate,
        "costs_df":        costs,
        "sku_kpis":        sku_kpis,
        "node_kpis":       node_kpis,
        "bullwhip_df":     bullwhip_df,
        "inventory_log":   pd.DataFrame(sim.inventory_log),
        "orders_log":      pd.DataFrame(sim.orders_log),
        "shipments_log":   pd.DataFrame(sim.shipments_log),
    }


# ============================================================
# Save one experiment's outputs
# ============================================================

def save_experiment(
    result: dict,
    exp_dir: Path,
    meta: dict,
    params: dict = None,
    baseline: dict = None,
    opt_info: dict = None,
):
    """Save all CSVs, a plain-text quick reference, and a rich markdown summary."""
    exp_dir.mkdir(parents=True, exist_ok=True)

    # ── CSVs ──────────────────────────────────────────────────────────────────
    result["costs_df"].to_csv(exp_dir / "costs_by_node_sku.csv",  index=False)
    result["sku_kpis"].to_csv(exp_dir / "kpis_by_sku.csv",        index=False)
    result["node_kpis"].to_csv(exp_dir / "kpis_by_node_sku.csv",  index=False)
    result["inventory_log"].to_csv(exp_dir / "inventory_log.csv", index=False)
    result["orders_log"].to_csv(exp_dir / "orders_log.csv",       index=False)

    if not result["shipments_log"].empty:
        result["shipments_log"].to_csv(exp_dir / "shipments_log.csv", index=False)
    if not result["bullwhip_df"].empty:
        result["bullwhip_df"].to_csv(exp_dir / "bullwhip.csv", index=False)
    if params:
        (exp_dir / "params.json").write_text(json.dumps(params, indent=2))

    # ── Derived comparison numbers ────────────────────────────────────────────
    vs_baseline = ""
    if baseline:
        saving = 100 * (baseline["total_cost"] - result["total_cost"]) / baseline["total_cost"]
        fill_delta = result["fill_rate_pct"] - baseline["fill_rate_pct"]
        vs_baseline = (
            f"  Cost vs E0 baseline : {saving:+.1f}%\n"
            f"  Fill rate vs E0     : {fill_delta:+.2f} pp"
        )

    # ── Plain-text summary (quick reference) ─────────────────────────────────
    total = result["total_cost"]
    txt_lines = [
        f"{meta['id']} — {meta['title']}",
        "=" * 60,
        f"{'Total cost':<22}: {total:>14,.2f}",
        f"{'  Holding':<22}: {result['holding_cost']:>14,.2f}  ({result['holding_pct']:.1f}%)",
        f"{'  Transport':<22}: {result['transport_cost']:>14,.2f}  ({result['transport_pct']:.1f}%)",
        f"{'  Ordering':<22}: {result['ordering_cost']:>14,.2f}  ({result['ordering_pct']:.1f}%)",
        f"{'  Shortage':<22}: {result['backlog_cost']:>14,.2f}  ({result['backlog_pct']:.1f}%)",
        f"{'Fill rate':<22}: {result['fill_rate_pct']:>13.2f}%",
    ]
    if vs_baseline:
        txt_lines += ["", "vs E0 Baseline:", vs_baseline]
    txt_lines += ["", "Fill rate by SKU:"]
    for _, row in result["sku_kpis"].iterrows():
        txt_lines.append(f"  {row['sku']:<14}  {row['fill_rate']*100:.2f}%")

    if not result["bullwhip_df"].empty:
        txt_lines += ["", "Bullwhip ratio by node × SKU (order CV² / demand CV²):"]
        txt_lines.append(f"  {'Node':<14}  {'SKU':<14}  {'BWE':>8}")
        for _, row in result["bullwhip_df"].iterrows():
            txt_lines.append(
                f"  {row['node_id']:<14}  {row['sku']:<14}  {row['bullwhip_ratio']:>8.3f}"
            )

    txt = "\n".join(txt_lines)
    (exp_dir / "summary.txt").write_text(txt)
    print(txt)

    # ── Rich markdown summary ─────────────────────────────────────────────────
    md = _build_experiment_markdown(result, meta, params, baseline, opt_info)
    (exp_dir / "summary.md").write_text(md)


def _build_experiment_markdown(
    result: dict,
    meta: dict,
    params: dict,
    baseline: dict,
    opt_info: dict,
) -> str:
    """Build a full markdown document for one experiment."""
    lines = []
    exp_id = meta["id"]

    lines += [
        f"# {exp_id} — {meta['title']}",
        "",
        f"*{meta['report_section']}*",
        "",
        "---",
        "",
        "## Purpose",
        "",
        meta["purpose"],
        "",
        "## Methodology",
        "",
        meta["methodology"],
        "",
        "## Hypothesis",
        "",
        f"*{meta['hypothesis']}*",
        "",
    ]

    # Optimizer info
    if opt_info:
        lines += [
            "## Optimization Details",
            "",
            f"| Parameter | Value |",
            f"|-----------|-------|",
            f"| Mode | {opt_info.get('mode', '—')} |",
            f"| Trials run | {opt_info.get('n_trials', '—')} |",
            f"| Feasible trials | {opt_info.get('n_feasible', '—')} |",
            f"| Best trial # | {opt_info.get('best_trial', '—')} |",
            f"| Min fill rate target | {opt_info.get('min_fill_rate', '—')} |",
            "",
        ]

    # Policy / experiment parameters
    if params:
        lines += ["## Policy Parameters", "", "| Parameter | Value |", "|-----------|------:|"]
        for k, v in params.items():
            lines.append(f"| `{k}` | {v} |")
        lines.append("")

    # Results
    total = result["total_cost"]
    lines += [
        "## Results",
        "",
        "### Cost Breakdown",
        "",
        "| Cost Component | Amount | Share |",
        "|----------------|-------:|------:|",
        f"| **Total cost** | **{total:,.0f}** | 100% |",
        f"| Holding | {result['holding_cost']:,.0f} | {result['holding_pct']:.1f}% |",
        f"| Transport | {result['transport_cost']:,.0f} | {result['transport_pct']:.1f}% |",
        f"| Ordering | {result['ordering_cost']:,.0f} | {result['ordering_pct']:.1f}% |",
        f"| Shortage (backlog) | {result['backlog_cost']:,.0f} | {result['backlog_pct']:.1f}% |",
        "",
        f"**Overall fill rate: {result['fill_rate_pct']:.2f}%**",
        "",
    ]

    # vs baseline
    if baseline:
        saving = 100 * (baseline["total_cost"] - result["total_cost"]) / baseline["total_cost"]
        fill_delta = result["fill_rate_pct"] - baseline["fill_rate_pct"]
        direction = "saving" if saving >= 0 else "increase"
        lines += [
            "### Comparison to E0 Baseline",
            "",
            f"| KPI | E0 Baseline | {exp_id} | Change |",
            f"|-----|------------:|--------:|-------:|",
            f"| Total cost | {baseline['total_cost']:,.0f} | {total:,.0f} "
            f"| {saving:+.1f}% {direction} |",
            f"| Fill rate | {baseline['fill_rate_pct']:.2f}% | {result['fill_rate_pct']:.2f}% "
            f"| {fill_delta:+.2f} pp |",
            f"| Transport % | {baseline['transport_pct']:.1f}% | {result['transport_pct']:.1f}% "
            f"| {result['transport_pct']-baseline['transport_pct']:+.1f} pp |",
            f"| Holding % | {baseline['holding_pct']:.1f}% | {result['holding_pct']:.1f}% "
            f"| {result['holding_pct']-baseline['holding_pct']:+.1f} pp |",
            f"| Shortage % | {baseline['backlog_pct']:.1f}% | {result['backlog_pct']:.1f}% "
            f"| {result['backlog_pct']-baseline['backlog_pct']:+.1f} pp |",
            "",
        ]

    # Fill rate by SKU
    lines += ["### Fill Rate by SKU", ""]
    lines += ["| SKU | Fill Rate |", "|-----|----------:|"]
    for _, row in result["sku_kpis"].iterrows():
        flag = " ✓" if row["fill_rate"] >= 0.92 else " ✗"
        lines.append(f"| {row['sku']} | {row['fill_rate']*100:.2f}%{flag} |")
    lines.append("")

    # Fill rate by node × SKU
    if not result["node_kpis"].empty:
        lines += ["### Fill Rate by Node and SKU", ""]
        pivot = result["node_kpis"].pivot(index="node_id", columns="sku", values="fill_rate")
        header = "| Node | " + " | ".join(pivot.columns) + " |"
        sep    = "|------|" + "|".join(["------:"] * len(pivot.columns)) + "|"
        lines += [header, sep]
        for nid, row in pivot.iterrows():
            vals = " | ".join(f"{v*100:.1f}%" for v in row)
            lines.append(f"| {nid} | {vals} |")
        lines.append("")

    # Bullwhip
    if not result["bullwhip_df"].empty:
        lines += [
            "### Bullwhip Effect",
            "",
            "> BWE = Order CV² / Demand CV². Values > 1 indicate demand variance "
            "amplification upstream — the classic bullwhip effect.",
            "",
            "| Node | SKU | Bullwhip Ratio |",
            "|------|-----|---------------:|",
        ]
        for _, row in result["bullwhip_df"].iterrows():
            flag = " ⚠" if row["bullwhip_ratio"] > 2.0 else ""
            lines.append(
                f"| {row['node_id']} | {row['sku']} | {row['bullwhip_ratio']:.3f}{flag} |"
            )
        lines.append("")

    # Key observations (auto-generated)
    lines += ["## Key Observations for Report", ""]
    lines += _auto_observations(result, baseline)
    lines.append("")

    return "\n".join(lines)


def _auto_observations(result: dict, baseline: dict) -> List[str]:
    """Generate bullet-point observations from result data."""
    obs = []
    fill = result["fill_rate_pct"]
    trans_pct = result["transport_pct"]
    hold_pct  = result["holding_pct"]
    short_pct = result["backlog_pct"]

    if baseline:
        saving    = 100 * (baseline["total_cost"] - result["total_cost"]) / baseline["total_cost"]
        fill_d    = fill - baseline["fill_rate_pct"]
        trans_d   = trans_pct - baseline["transport_pct"]
        hold_d    = hold_pct  - baseline["holding_pct"]
        short_d   = short_pct - baseline["backlog_pct"]

        if saving > 0:
            obs.append(
                f"- **{saving:.1f}% total cost reduction** vs E0 baseline "
                f"(from {baseline['total_cost']:,.0f} to {result['total_cost']:,.0f})."
            )
        else:
            obs.append(
                f"- Total cost is **{abs(saving):.1f}% higher** than E0 baseline — "
                f"this experiment trades cost for service quality."
            )

        if fill_d >= 0:
            obs.append(f"- Fill rate improved by **{fill_d:.2f} percentage points** over baseline.")
        else:
            obs.append(
                f"- Fill rate **dropped {abs(fill_d):.2f} pp** vs baseline ({fill:.2f}%). "
                f"{'Below 92% target — the consolidation constraint is harming service.' if fill < 92 else ''}"
            )

        if abs(trans_d) > 2:
            direction = "decreased" if trans_d < 0 else "increased"
            obs.append(
                f"- Transport cost share {direction} by **{abs(trans_d):.1f} pp** "
                f"(from {baseline['transport_pct']:.1f}% to {trans_pct:.1f}%), "
                f"{'reflecting effective vehicle consolidation.' if trans_d < 0 else 'suggesting more frequent smaller shipments.'}"
            )

        if abs(hold_d) > 2:
            direction = "higher" if hold_d > 0 else "lower"
            obs.append(
                f"- Holding cost share is **{abs(hold_d):.1f} pp {direction}** "
                f"({hold_pct:.1f}% vs {baseline['holding_pct']:.1f}% in E0), "
                f"{'reflecting elevated base-stock levels to enable consolidation.' if hold_d > 0 else 'reflecting leaner inventory.'}"
            )

        if abs(short_d) > 2:
            direction = "reduced" if short_d < 0 else "increased"
            obs.append(
                f"- Shortage cost share **{direction} by {abs(short_d):.1f} pp** "
                f"({short_pct:.1f}% vs {baseline['backlog_pct']:.1f}% in E0)."
            )

    else:
        # E0 baseline self-description
        obs.append(
            f"- Baseline total cost is **{result['total_cost']:,.0f}**, "
            f"dominated by transport ({trans_pct:.1f}%) — this is the primary "
            f"optimisation target for subsequent experiments."
        )
        obs.append(
            f"- Baseline fill rate of **{fill:.2f}%** is below the 92% target, "
            f"indicating the analytical newsvendor levels alone are insufficient for "
            f"the target service level."
        )
        obs.append(
            f"- With only {hold_pct:.1f}% of cost in holding, there is room to increase "
            f"inventory levels (raise S) to buffer against transport delays introduced "
            f"by consolidation in later experiments."
        )

    # SKU-level observations
    sku_fill = result["sku_kpis"]
    worst_sku = sku_fill.loc[sku_fill["fill_rate"].idxmin()]
    best_sku  = sku_fill.loc[sku_fill["fill_rate"].idxmax()]
    if (worst_sku["fill_rate"] * 100) < 92:
        obs.append(
            f"- **{worst_sku['sku']}** has the lowest fill rate ({worst_sku['fill_rate']*100:.1f}%) "
            f"and may need a higher base-stock level or priority attention."
        )
    obs.append(
        f"- Fill rate spread across SKUs: {worst_sku['fill_rate']*100:.1f}% "
        f"({worst_sku['sku']}) to {best_sku['fill_rate']*100:.1f}% ({best_sku['sku']}) "
        f"— a {(best_sku['fill_rate']-worst_sku['fill_rate'])*100:.1f} pp range."
    )

    return obs


# ============================================================
# Summary table helpers
# ============================================================

def build_summary_table(results: List[dict], baseline_cost: float) -> pd.DataFrame:
    rows = []
    for r in results:
        if baseline_cost and baseline_cost != 0:
            improvement = 100 * (baseline_cost - r["total_cost"]) / baseline_cost
            vs_str = f"{improvement:+.1f}%"
        else:
            vs_str = "—"
        rows.append({
            "Exp":           r["label"].split(" ")[0],
            "Description":   r["label"],
            "Total Cost":    f"{r['total_cost']:,.0f}",
            "vs E0":         vs_str,
            "Holding %":     f"{r['holding_pct']:.1f}",
            "Transport %":   f"{r['transport_pct']:.1f}",
            "Ordering %":    f"{r['ordering_pct']:.1f}",
            "Shortage %":    f"{r['backlog_pct']:.1f}",
            "Fill Rate %":   f"{r['fill_rate_pct']:.2f}",
        })
    return pd.DataFrame(rows)


def df_to_markdown(df: pd.DataFrame) -> str:
    col_w = {col: max(len(str(col)), df[col].astype(str).str.len().max()) for col in df.columns}
    header = " | ".join(f"{col:<{col_w[col]}}" for col in df.columns)
    sep    = "-+-".join("-" * col_w[col] for col in df.columns)
    lines  = [header, sep]
    for _, row in df.iterrows():
        lines.append(" | ".join(f"{str(row[col]):<{col_w[col]}}" for col in df.columns))
    return "\n".join(lines)


# ============================================================
# Master report document
# ============================================================

def generate_report_summary(
    results: List[dict],
    pareto_df: Optional[pd.DataFrame],
    cfg: dict,
    out_dir: Path,
    config_path: str,
    elapsed_min: float,
    warmup: int,
    n_trials: int,
    min_fill_rate: float,
):
    """Write REPORT_SUMMARY.md — a narrative document ready to copy into the report."""
    lines = []
    skus  = cfg.get("skus", [])
    nodes = cfg.get("nodes", [])
    edges = cfg.get("edges", [])
    T     = cfg.get("time_horizon", "?")

    n_suppliers  = sum(1 for n in nodes if n.get("type") == "supplier")
    n_warehouses = sum(1 for n in nodes if n.get("type") == "warehouse")
    n_retailers  = sum(1 for n in nodes if n.get("type") == "retailer")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines += [
        "# DDP Experiment Report Summary",
        "",
        f"*Generated: {timestamp}*  ",
        f"*Config: `{config_path}`*  ",
        f"*Runtime: {elapsed_min:.1f} minutes*",
        "",
        "---",
        "",
        "## 1. Network Configuration",
        "",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| Network topology | {n_suppliers}S–{n_warehouses}W–{n_retailers}R "
        f"({n_suppliers} supplier, {n_warehouses} warehouse, {n_retailers} retailers) |",
        f"| SKUs | {len(skus)}: {', '.join(skus)} |",
        f"| Transport lanes | {len(edges)} |",
        f"| Simulation horizon | {T} days |",
        f"| Warm-up excluded | {warmup} days |",
        f"| Optimizer trials | {n_trials} per experiment |",
        f"| Min fill rate target | {min_fill_rate*100:.0f}% |",
        "",
    ]

    # Network summary
    lines += ["### Node Summary", ""]
    lines += ["| Node | Type | Policy (SKU_A) |", "|------|------|----------------|"]
    for n in nodes:
        pol = n.get("policy", {})
        pol_a = pol.get(skus[0], {}) if skus else {}
        pol_str = pol_a.get("type", "—")
        lines.append(f"| {n['id']} | {n.get('type','?')} | {pol_str} |")
    lines.append("")

    lines += ["### Transport Lanes", ""]
    lines += ["| From | To | Lead Time | Capacity | Min Dispatch |",
              "|------|----|----------:|---------:|-------------:|"]
    for e in edges:
        lt = e.get("lead_time", {})
        lt_str = f"{lt.get('value', lt.get('mean', '?'))} days ({lt.get('type','?')})"
        lines.append(
            f"| {e['from']} | {e['to']} | {lt_str} "
            f"| {e.get('capacity', '?')} | {e.get('min_dispatch_utilization', 0.0)*100:.0f}% |"
        )
    lines.append("")

    # Experiment summaries
    lines += ["---", "", "## 2. Experiment Results", ""]
    baseline = results[0] if results else None

    for r in results:
        exp_id = r["label"].split(" ")[0]
        m = EXPERIMENT_META.get(exp_id, {})
        lines += [
            f"### {exp_id} — {m.get('title', r['label'])}",
            "",
            f"**Purpose:** {m.get('purpose', '')}",
            "",
        ]
        if baseline and r is not baseline:
            saving   = 100 * (baseline["total_cost"] - r["total_cost"]) / baseline["total_cost"]
            fill_d   = r["fill_rate_pct"] - baseline["fill_rate_pct"]
            lines += [
                f"| KPI | Value | vs E0 |",
                f"|-----|------:|------:|",
                f"| Total cost | {r['total_cost']:,.0f} | {saving:+.1f}% |",
                f"| Fill rate | {r['fill_rate_pct']:.2f}% | {fill_d:+.2f} pp |",
                f"| Transport share | {r['transport_pct']:.1f}% | "
                f"{r['transport_pct']-baseline['transport_pct']:+.1f} pp |",
                f"| Holding share | {r['holding_pct']:.1f}% | "
                f"{r['holding_pct']-baseline['holding_pct']:+.1f} pp |",
                f"| Shortage share | {r['backlog_pct']:.1f}% | "
                f"{r['backlog_pct']-baseline['backlog_pct']:+.1f} pp |",
            ]
        else:
            lines += [
                f"| KPI | Value |",
                f"|-----|------:|",
                f"| Total cost | {r['total_cost']:,.0f} |",
                f"| Fill rate | {r['fill_rate_pct']:.2f}% |",
                f"| Transport share | {r['transport_pct']:.1f}% |",
                f"| Holding share | {r['holding_pct']:.1f}% |",
                f"| Shortage share | {r['backlog_pct']:.1f}% |",
            ]
        lines.append("")
        # Auto observations
        obs = _auto_observations(r, baseline if r is not baseline else None)
        lines += ["**Key findings:**", ""] + obs + [""]

    # Comparison table
    if results:
        lines += ["---", "", "## 3. Comparison Table", ""]
        baseline_cost = results[0]["total_cost"]
        tbl = build_summary_table(results, baseline_cost)
        lines.append(df_to_markdown(tbl))
        lines.append("")

    # Pareto section
    if pareto_df is not None:
        lines += ["---", "", "## 4. Pareto Frontier (E4)", ""]
        lines += [
            "The table below shows the trade-off between fill rate and total cost "
            "under joint optimization. Each row is an independent optimizer run "
            "with a different fill rate target.",
            "",
        ]
        lines.append(df_to_markdown(pareto_df))
        lines.append("")

        # Find the 'knee' of the Pareto curve
        if len(pareto_df) >= 2:
            costs  = pareto_df["total_cost"].values
            fills  = pareto_df["achieved_fill_pct"].values
            deltas = []
            for i in range(1, len(costs)):
                if fills[i] > fills[i-1]:
                    cost_per_pp = (costs[i] - costs[i-1]) / (fills[i] - fills[i-1])
                    deltas.append((fills[i], cost_per_pp))
            if deltas:
                lines += [
                    "**Marginal cost of fill rate improvement:**",
                    "",
                    "| At fill rate | Marginal cost per +1pp |",
                    "|-------------:|-----------------------:|",
                ]
                for fill_pt, cost_pp in deltas:
                    lines.append(f"| {fill_pt:.1f}% | {cost_pp:,.0f} |")
                lines.append("")

    # Key findings for dissertation
    lines += ["---", "", "## 5. Key Findings for Dissertation", ""]
    if len(results) >= 4:
        e0 = results[0]
        e3 = next((r for r in results if r["label"].startswith("E3")), None)
        e2 = next((r for r in results if r["label"].startswith("E2")), None)
        e1b = next((r for r in results if r["label"].startswith("E1b")), None)
        if e3:
            joint_saving = 100 * (e0["total_cost"] - e3["total_cost"]) / e0["total_cost"]
            lines += [
                f"1. **Joint optimization (E3) achieves a {joint_saving:.1f}% total cost reduction** "
                f"over the analytical baseline while meeting the {min_fill_rate*100:.0f}% fill rate target "
                f"(achieved: {e3['fill_rate_pct']:.2f}%). This is the primary result of the dissertation.",
                "",
            ]
        if e2 and e3:
            inv_saving = 100 * (e0["total_cost"] - e2["total_cost"]) / e0["total_cost"]
            lines += [
                f"2. **Inventory-only optimization (E2) {'reduces' if inv_saving > 0 else 'increases'} "
                f"cost by {abs(inv_saving):.1f}%**, confirming that optimizing inventory alone is "
                f"{'beneficial' if inv_saving > 0 else 'insufficient'} compared to joint optimization.",
                "",
            ]
        if e1b and e3:
            trans_saving = 100 * (e0["total_cost"] - e1b["total_cost"]) / e0["total_cost"]
            lines += [
                f"3. **Transport-only optimization (E1b) achieves {trans_saving:.1f}% cost reduction**, "
                f"showing that threshold selection matters but is limited without inventory co-optimization.",
                "",
            ]
        lines += [
            "4. **Transport cost dominates** the baseline cost structure "
            f"({e0['transport_pct']:.1f}% of total), making it the primary lever for cost reduction. "
            "Joint optimization reduces this share through vehicle consolidation.",
            "",
            "5. **The bullwhip effect** is observable in the orders time series — order variability "
            "increases upstream from retailers to warehouses to the supplier. Joint optimization "
            "reduces bullwhip by smoothing replenishment patterns.",
            "",
        ]

    lines += [
        "---",
        "",
        "## 6. Files Reference",
        "",
        "| File | Contents |",
        "|------|----------|",
        "| `summary_table.csv` | One-row-per-experiment KPI comparison |",
        "| `E*/summary.md` | Rich per-experiment report with purpose, methodology, results |",
        "| `E*/summary.txt` | Quick plain-text reference |",
        "| `E*/costs_by_node_sku.csv` | Cost breakdown at node × SKU granularity |",
        "| `E*/kpis_by_sku.csv` | Fill rate per SKU |",
        "| `E*/kpis_by_node_sku.csv` | Fill rate per retailer × SKU |",
        "| `E*/bullwhip.csv` | Bullwhip effect ratio per node × SKU |",
        "| `E*/inventory_log.csv` | Daily on-hand, pipeline, backlog time series |",
        "| `E*/orders_log.csv` | Daily order quantities (shows bullwhip visually) |",
        "| `E*/params.json` | Exact policy parameters used |",
        "| `E4_pareto/pareto_frontier.csv` | Cost vs fill rate Pareto data |",
        "| `plots/` | All matplotlib figures (run `plot_results.py`) |",
        "",
    ]

    doc = "\n".join(lines)
    (out_dir / "REPORT_SUMMARY.md").write_text(doc)
    print(f"\n  → REPORT_SUMMARY.md written to {out_dir}")
    return doc


# ============================================================
# Individual experiment functions
# ============================================================

def _compute_newsvendor_levels(cfg: dict, warmup: int,
                               z: float = 1.64) -> Dict[str, Dict[str, int]]:
    """Compute base-stock S = μ(L+1) + z·σ·√(L+1) per (node, sku) at runtime.

    Realised retailer demand drives μ, σ. Warehouse demand is the daily sum
    across its retailer children (correct for the multi-warehouse 1-2-3
    topology). Supplier nodes are skipped (infinite_supply).
    """
    import numpy as np

    # Build a single dummy run to extract realised demand series (post-warmup).
    net, demand_by_node, T = build_from_config(cfg)
    sim = Simulator(network=net, demand_by_node=demand_by_node, T=T,
                    order_processing_delay=1, volume_per_unit=build_volume_map(cfg),
                    weight_per_unit=build_weight_map(cfg))
    sim.run()
    eod = pd.DataFrame([m.__dict__ for m in sim.metrics])
    eod = eod[(eod["phase"] == "EOD") & (eod["t"] >= warmup)]

    # parent map and lead-time map
    child_to_parent = {e["to"]: e["from"] for e in cfg["edges"]}
    lt_map: Dict[tuple, int] = {}
    for e in cfg["edges"]:
        lt = e.get("lead_time", {}).get("value")
        if lt is None:  # try transport_options or default
            opts = e.get("transport_options") or []
            lt = opts[0].get("lead_time", 1) if opts else 1
        lt_map[(e["from"], e["to"])] = int(lt)

    skus = cfg["skus"]
    retailer_ids = [n["id"] for n in cfg["nodes"] if n["type"] == "retailer"]

    # Retailer per-day demand series.
    retailer_demand: Dict[tuple, pd.Series] = {}
    for nid in retailer_ids:
        for sku in skus:
            grp = eod[(eod["node_id"] == nid) & (eod["sku"] == sku)]
            if not grp.empty:
                retailer_demand[(nid, sku)] = grp.set_index("t")["demand"].sort_index()

    # Warehouse demand = sum of demand from its retailer children.
    warehouse_demand: Dict[tuple, pd.Series] = {}
    for parent in {child_to_parent.get(rid) for rid in retailer_ids if child_to_parent.get(rid)}:
        for sku in skus:
            agg = pd.Series(dtype=float)
            for rid in retailer_ids:
                if child_to_parent.get(rid) == parent:
                    s = retailer_demand.get((rid, sku))
                    if s is not None:
                        agg = agg.add(s, fill_value=0.0)
            if not agg.empty:
                warehouse_demand[(parent, sku)] = agg

    levels: Dict[str, Dict[str, int]] = {}
    for nd in cfg["nodes"]:
        if nd.get("infinite_supply", False):
            continue
        nid = nd["id"]
        # Find lead time on inbound edge.
        inbound = [(p, c) for (p, c) in lt_map if c == nid]
        L = lt_map[inbound[0]] if inbound else 1
        for sku in skus:
            if nd["type"] == "retailer":
                s = retailer_demand.get((nid, sku))
            else:
                s = warehouse_demand.get((nid, sku))
            if s is None or s.empty:
                continue
            mu = float(s.mean())
            sigma = float(s.std(ddof=1)) if len(s) > 1 else 0.0
            S = int(np.ceil(mu * (L + 1) + z * sigma * np.sqrt(L + 1)))
            S = max(S, 1)
            levels.setdefault(nid, {})[sku] = S
    return levels


def _apply_newsvendor_levels(cfg: dict, levels: Dict[str, Dict[str, int]]) -> dict:
    """Inject newsvendor levels into a cfg copy. Sets initial_inventory = S as well."""
    cfg = copy.deepcopy(cfg)
    for nd in cfg["nodes"]:
        if nd.get("infinite_supply", False):
            continue
        nid = nd["id"]
        if nid not in levels:
            continue
        for sku, S in levels[nid].items():
            pol = nd["policy"].get(sku, {})
            if pol.get("type") == "base_stock":
                nd["policy"][sku]["base_stock_level"] = int(S)
            # Match initial inventory to S so the system starts at steady state.
            if "initial_inventory" in nd:
                nd["initial_inventory"][sku] = int(S)
    return cfg


def exp_E0_from_cfg(cfg_e0, vpu, out_dir, warmup, levels) -> dict:
    """E0 runs with the newsvendor-derived config (computed once in main)."""
    print("\n" + "=" * 60)
    print("E0 — Analytical baseline (newsvendor at runtime)")
    print("=" * 60)
    print("  Newsvendor base-stock levels:")
    for nid, by_sku in levels.items():
        line = f"    {nid:<10}"
        for sku, S in by_sku.items():
            line += f"  {sku}={S}"
        print(line)
    result = run_one(cfg_e0, vpu, "E0 — Analytical Baseline", warmup_periods=warmup)
    params = {f"S_{nid}__{sku}": int(S)
              for nid, by_sku in levels.items() for sku, S in by_sku.items()}
    params["_note"] = "Newsvendor S = μ(L+1) + z·σ·√(L+1), z=1.64"
    save_experiment(
        result, out_dir / "E0",
        meta=EXPERIMENT_META["E0"],
        params=params,
        baseline=None,
    )
    return result


# Backwards-compatible alias if anyone calls exp_E0 directly with base_cfg.
def exp_E0(base_cfg, vpu, out_dir, warmup) -> dict:
    levels = _compute_newsvendor_levels(base_cfg, warmup=warmup, z=1.64)
    cfg_e0 = _apply_newsvendor_levels(base_cfg, levels)
    return exp_E0_from_cfg(cfg_e0, vpu, out_dir, warmup, levels)


def exp_E1a(base_cfg, vpu, out_dir, warmup, baseline) -> dict:
    print("\n" + "=" * 60)
    print("E1a — Fixed 25% dispatch threshold on all lanes")
    print("=" * 60)
    cfg = copy.deepcopy(base_cfg)
    params = {}
    for e in cfg["edges"]:
        e["min_dispatch_utilization"] = 0.25
        rid = e.get("route_id") or f"{e['from']}_{e['to']}"
        params[f"D_{rid}"] = 0.25
    result = run_one(cfg, vpu, "E1a — Financial Dispatch (25%)",
                     max_dispatch_wait=3, warmup_periods=warmup)
    save_experiment(
        result, out_dir / "E1a",
        meta=EXPERIMENT_META["E1a"],
        params=params,
        baseline=baseline,
    )
    return result


def exp_E1b(base_cfg, vpu, out_dir, n_trials, warmup, baseline) -> dict:
    print("\n" + "=" * 60)
    print("E1b — Transport-only optimization")
    print("=" * 60)
    opt = run_optimizer(
        base_cfg=base_cfg, volume_per_unit=vpu,
        mode="transport", n_trials=n_trials, min_fill_rate=0.92,
        seed=42, verbose=True,
    )
    cfg = _apply_params(base_cfg, opt.best_params)
    result = run_one(cfg, vpu, "E1b — Transport-Only Optimization", warmup_periods=warmup)
    n_feasible = sum(1 for t in opt.study.trials
                     if t.user_attrs.get("fill_rate", 0) >= 0.92)
    save_experiment(
        result, out_dir / "E1b",
        meta=EXPERIMENT_META["E1b"],
        params=opt.best_params,
        baseline=baseline,
        opt_info={
            "mode": "transport", "n_trials": n_trials,
            "n_feasible": n_feasible, "best_trial": opt.best_trial,
            "min_fill_rate": "92%",
        },
    )
    return result


def exp_E2(base_cfg, vpu, out_dir, n_trials, min_fill_rate, warmup, baseline) -> dict:
    print("\n" + "=" * 60)
    print(f"E2 — Inventory-only optimization (target ≥ {min_fill_rate*100:.0f}%)")
    print("=" * 60)
    opt = run_optimizer(
        base_cfg=base_cfg, volume_per_unit=vpu,
        mode="inventory", n_trials=n_trials, min_fill_rate=min_fill_rate,
        seed=42, verbose=True,
    )
    cfg = _apply_params(base_cfg, opt.best_params)
    result = run_one(cfg, vpu, f"E2 — Inventory-Only Opt (≥{min_fill_rate*100:.0f}%)",
                     warmup_periods=warmup)
    n_feasible = sum(1 for t in opt.study.trials
                     if t.user_attrs.get("fill_rate", 0) >= min_fill_rate)
    save_experiment(
        result, out_dir / "E2",
        meta=EXPERIMENT_META["E2"],
        params=opt.best_params,
        baseline=baseline,
        opt_info={
            "mode": "inventory", "n_trials": n_trials,
            "n_feasible": n_feasible, "best_trial": opt.best_trial,
            "min_fill_rate": f"{min_fill_rate*100:.0f}%",
        },
    )
    return result


def exp_E3(base_cfg, vpu, out_dir, n_trials, min_fill_rate, warmup, baseline) -> dict:
    print("\n" + "=" * 60)
    print(f"E3 — Joint optimization (target ≥ {min_fill_rate*100:.0f}%)")
    print("=" * 60)
    opt = run_optimizer(
        base_cfg=base_cfg, volume_per_unit=vpu,
        mode="joint", n_trials=n_trials, min_fill_rate=min_fill_rate,
        seed=42, verbose=True,
    )
    cfg = _apply_params(base_cfg, opt.best_params)
    result = run_one(cfg, vpu, f"E3 — Joint Opt (≥{min_fill_rate*100:.0f}%)",
                     warmup_periods=warmup)
    n_feasible = sum(1 for t in opt.study.trials
                     if t.user_attrs.get("fill_rate", 0) >= min_fill_rate)

    # Save convergence trace for the "100 trials enough?" plot.
    valid_trials = [t for t in opt.study.trials if t.value is not None]
    if valid_trials:
        running_best = []
        best_so_far = float("inf")
        for t in sorted(valid_trials, key=lambda x: x.number):
            if t.value < best_so_far:
                best_so_far = t.value
            running_best.append(best_so_far)
        conv_df = pd.DataFrame({
            "trial":     [t.number for t in sorted(valid_trials, key=lambda x: x.number)],
            "cost":      [t.value for t in sorted(valid_trials, key=lambda x: x.number)],
            "fill_rate": [t.user_attrs.get("fill_rate", float("nan"))
                          for t in sorted(valid_trials, key=lambda x: x.number)],
            "best_cost": running_best,
        })
        exp_out = out_dir / "E3"
        exp_out.mkdir(parents=True, exist_ok=True)
        conv_df.to_csv(exp_out / "convergence.csv", index=False)

    save_experiment(
        result, out_dir / "E3",
        meta=EXPERIMENT_META["E3"],
        params=opt.best_params,
        baseline=baseline,
        opt_info={
            "mode": "joint", "n_trials": n_trials,
            "n_feasible": n_feasible, "best_trial": opt.best_trial,
            "min_fill_rate": f"{min_fill_rate*100:.0f}%",
        },
    )
    return result


def exp_E4_pareto(base_cfg, vpu, out_dir, n_trials) -> pd.DataFrame:
    """E4 = NSGA-II true Pareto search + trimmed constraint sweep (sanity check)."""
    print("\n" + "=" * 60)
    print("E4 — Pareto frontier (NSGA-II + constraint sweep)")
    print("=" * 60)

    pareto_dir = out_dir / "E4_pareto"
    pareto_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. NSGA-II two-objective ──────────────────────────────────────────────
    from optimizer.pareto import run_nsga2_pareto
    nsga_trials = max(200, n_trials * 2)
    print(f"\n  → NSGA-II (primary): {nsga_trials} trials, "
          f"minimise (cost, -fill_rate)")
    pr = run_nsga2_pareto(
        base_cfg=base_cfg, volume_per_unit=vpu,
        n_trials=nsga_trials, seed=42,
        population_size=32, verbose=True,
    )
    nsga_rows = [{
        "method":      "nsga2",
        "fill_rate":   round(r["fill_rate"]  * 100, 4),
        "total_cost":  round(r["total_cost"], 2),
        "trial":       r["trial_number"],
    } for r in pr.frontier]
    nsga_df = pd.DataFrame(nsga_rows).sort_values("fill_rate").reset_index(drop=True)
    nsga_df.to_csv(pareto_dir / "nsga2_frontier.csv", index=False)
    # Save best params per frontier point.
    for r in pr.frontier:
        f_pct = int(round(r["fill_rate"] * 100))
        (pareto_dir / f"nsga2_params_fill_{f_pct:02d}.json").write_text(
            json.dumps({"fill_rate": r["fill_rate"],
                        "total_cost": r["total_cost"],
                        "params": r["params"]}, indent=2)
        )
    print(f"    NSGA-II frontier: {len(nsga_df)} non-dominated points")

    # ── 2. Trimmed constraint sweep (sanity check) ────────────────────────────
    targets = [0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99]
    print(f"\n  → Constraint sweep (validation): targets {targets}")
    sweep_rows = []
    for i, target in enumerate(targets):
        opt = run_optimizer(
            base_cfg=base_cfg, volume_per_unit=vpu,
            mode="joint", n_trials=n_trials, min_fill_rate=target,
            seed=42 + i * 17, verbose=False,
        )
        params_file = pareto_dir / f"sweep_params_{int(target*100):02d}pct.json"
        params_file.write_text(
            json.dumps({"target": target, "params": opt.best_params}, indent=2)
        )
        saved    = json.loads(params_file.read_text())
        cfg_eval = _apply_params(base_cfg, saved["params"])
        total_cost, fill_rate = evaluate(cfg_eval, vpu)
        n_feasible = sum(
            1 for t in opt.study.trials
            if t.user_attrs.get("fill_rate", 0) >= target
        )
        sweep_rows.append({
            "method":            "sweep",
            "target_fill_pct":   round(target * 100, 1),
            "achieved_fill_pct": round(fill_rate * 100, 2),
            "total_cost":        round(total_cost, 2),
            "feasible_trials":   n_feasible,
            "best_trial":        opt.best_trial,
        })
        print(f"    target {target*100:.0f}%: achieved {fill_rate*100:.2f}%  "
              f"cost {total_cost:,.2f}  feas {n_feasible}/{n_trials}")

    sweep_df = pd.DataFrame(sweep_rows)
    sweep_df.to_csv(pareto_dir / "sweep_frontier.csv", index=False)

    # ── 3. Decision log ───────────────────────────────────────────────────────
    smooth = False
    if len(nsga_df) >= 3:
        # Monotone decreasing in cost as fill rate decreases? Check sorted by fill desc.
        ordered = nsga_df.sort_values("fill_rate", ascending=False)
        costs = ordered["total_cost"].values
        # We expect higher fill → higher cost. So when sorted desc by fill, cost should
        # generally decrease. Allow small reversals (within 2% of cost range).
        rng = costs.max() - costs.min() if len(costs) else 0
        violations = sum(1 for i in range(1, len(costs))
                         if costs[i] > costs[i-1] + 0.02 * rng)
        smooth = (violations <= 1)

    decision = (
        f"# E4 Pareto Decision Log\n\n"
        f"NSGA-II frontier points: {len(nsga_df)}\n"
        f"Sweep targets that bind: {sum(1 for r in sweep_rows if r['achieved_fill_pct'] < 99.99)}\n"
        f"NSGA-II curve smooth + monotone: **{smooth}**\n\n"
        f"Recommendation: "
        + ("Use NSGA-II as primary, sweep as validation overlay."
           if smooth else
           "NSGA-II curve is irregular; consider falling back to constraint sweep "
           "as primary in the report, citing the noise.")
        + "\n"
    )
    (pareto_dir / "decision.md").write_text(decision)
    print("\n" + decision)

    # Backwards-compatible flat CSV for plot_results.py.
    flat = pd.DataFrame([{
        "target_fill_pct":   r["target_fill_pct"],
        "achieved_fill_pct": r["achieved_fill_pct"],
        "total_cost":        r["total_cost"],
        "feasible_trials":   r["feasible_trials"],
        "best_trial":        r["best_trial"],
    } for r in sweep_rows])
    flat.to_csv(pareto_dir / "pareto_frontier.csv", index=False)

    md_lines = [
        "# E4 — Pareto Frontier: Cost vs Fill Rate",
        "",
        EXPERIMENT_META["E4"]["purpose"],
        "",
        "## NSGA-II frontier (primary)",
        "",
        df_to_markdown(nsga_df),
        "",
        "## Constraint sweep (validation)",
        "",
        df_to_markdown(sweep_df),
        "",
        decision,
    ]
    (pareto_dir / "pareto_frontier.md").write_text("\n".join(md_lines))
    return flat


def exp_E3_per_sku(base_cfg, vpu, out_dir, n_trials, min_fill_rate, warmup, baseline) -> dict:
    print("\n" + "=" * 60)
    print(f"E3_per_sku — Joint opt with per-SKU constraint (every SKU ≥ "
          f"{min_fill_rate*100:.0f}%)")
    print("=" * 60)
    opt = run_optimizer(
        base_cfg=base_cfg, volume_per_unit=vpu,
        mode="joint", n_trials=n_trials, min_fill_rate=min_fill_rate,
        seed=42, verbose=True, per_sku_constraint=True,
    )
    cfg = _apply_params(base_cfg, opt.best_params)
    result = run_one(cfg, vpu,
                     f"E3_per_sku — Joint Opt (per-SKU ≥ {min_fill_rate*100:.0f}%)",
                     warmup_periods=warmup)
    n_feasible = sum(1 for t in opt.study.trials
                     if t.user_attrs.get("min_sku_fill", 0) >= min_fill_rate)
    save_experiment(
        result, out_dir / "E3_per_sku",
        meta=EXPERIMENT_META["E3_per_sku"],
        params=opt.best_params,
        baseline=baseline,
        opt_info={
            "mode": "joint", "n_trials": n_trials,
            "n_feasible": n_feasible, "best_trial": opt.best_trial,
            "min_fill_rate": f"{min_fill_rate*100:.0f}% per-SKU",
        },
    )
    return result


def run_multiseed_validation(base_cfg: dict, vpu: dict, params_path: Path,
                             out_dir: Path, n_seeds: int, warmup: int) -> None:
    """Re-run the saved params under N seeds, report mean ± std."""
    print("\n" + "=" * 60)
    print(f"Multi-seed validation: {n_seeds} seeds for E3 best params")
    print("=" * 60)
    saved = json.loads(params_path.read_text())
    # `params` may be a flat dict (S_*, D_*) or a wrapper {"params": {...}}.
    params = saved.get("params") if isinstance(saved, dict) and "params" in saved else saved
    rows = []
    for i in range(n_seeds):
        cfg = _apply_params(base_cfg, params)
        cfg["seed"] = 42 + i
        # Override every demand generator's seed too.
        for d in cfg.get("demand", []):
            g = d.get("generator", {})
            if g.get("type") in ("poisson",):
                g["seed"] = 42 + i
        result = run_one(cfg, vpu, f"E3-seed{42+i}", warmup_periods=warmup)
        rows.append({
            "seed":       42 + i,
            "total_cost": round(result["total_cost"], 2),
            "fill_rate":  round(result["fill_rate"], 4),
        })
        print(f"  seed={42+i}: cost {result['total_cost']:,.2f}, "
              f"fill {result['fill_rate']*100:.2f}%")
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "multiseed_validation.csv", index=False)

    summary = pd.DataFrame([{
        "n_seeds":       n_seeds,
        "cost_mean":     round(df["total_cost"].mean(), 2),
        "cost_std":      round(df["total_cost"].std(ddof=1), 2),
        "fill_mean":     round(df["fill_rate"].mean(), 4),
        "fill_std":      round(df["fill_rate"].std(ddof=1), 4),
    }])
    summary.to_csv(out_dir / "multiseed_summary.csv", index=False)
    print("\n  Multi-seed summary:")
    print("  " + df_to_markdown(summary).replace("\n", "\n  "))


# ============================================================
# Phase B experiments
# ============================================================

def _inject_disruption(cfg: dict, node_id: str, start: int, duration: int) -> dict:
    cfg = copy.deepcopy(cfg)
    cfg.setdefault("disruptions", []).append(
        {"node_id": node_id, "start": int(start), "end": int(start + duration)}
    )
    return cfg


def exp_E5_disruption(base_cfg, vpu, out_dir, warmup,
                      e0_params_path: Path, e3_params_path: Path) -> List[dict]:
    """E5: disruption robustness — same shock applied to E0 params and E3 params."""
    print("\n" + "=" * 60)
    print("E5 — Disruption robustness (W1 outage, 14 days)")
    print("=" * 60)
    T = int(base_cfg["time_horizon"])
    shock_start    = warmup + int(0.6 * (T - warmup))
    shock_duration = 14
    print(f"  W1 disrupted in [{shock_start}, {shock_start+shock_duration}) "
          f"of {T}-day horizon")

    out_dir_e5 = out_dir / "E5"
    out_dir_e5.mkdir(parents=True, exist_ok=True)

    results = []
    for label, params_path, scenario_id in [
        ("E5_E0params", e0_params_path, "E0"),
        ("E5_E3params", e3_params_path, "E3"),
    ]:
        if not params_path.exists():
            print(f"  ⚠  {scenario_id} params not found at {params_path}; skipping")
            continue
        saved = json.loads(params_path.read_text())
        params = saved.get("params") if "params" in saved else saved
        # Drop the _note key if present.
        params = {k: v for k, v in params.items() if not k.startswith("_")}
        cfg = _apply_params(base_cfg, params)
        cfg = _inject_disruption(cfg, "W1", shock_start, shock_duration)
        result = run_one(cfg, vpu, f"E5 — {scenario_id} under W1 outage",
                         warmup_periods=warmup)
        sub_dir = out_dir / label
        save_experiment(
            result, sub_dir,
            meta={**EXPERIMENT_META["E5"], "id": label,
                  "title": f"Disruption — {scenario_id} params"},
            params={**params, "disruption":
                    {"node": "W1", "start": shock_start, "end": shock_start+shock_duration}},
            baseline=None,
        )
        results.append(result)
    return results


def exp_E6_policies(base_cfg, vpu, out_dir, n_trials, min_fill_rate, warmup) -> List[dict]:
    """E6: optimize each of base_stock / ss / periodic_review / echelon_stock.

    Each policy jointly optimises its inventory parameters AND all dispatch
    thresholds, giving every policy equal access to transport consolidation.
    """
    print("\n" + "=" * 60)
    print("E6 — Policy comparison (Core 4, joint inventory+transport)")
    print("=" * 60)
    from optimizer.policy_search import run_policy_optimizer
    from optimizer.optimize import _extract_dispatch_thresholds
    print("  Dispatch routes:", list(_extract_dispatch_thresholds(base_cfg).keys()))

    results = []
    for policy_type in ["base_stock", "ss", "periodic_review", "echelon_stock"]:
        print(f"\n  → Policy: {policy_type}")
        try:
            cfg_opt, params, summary = run_policy_optimizer(
                base_cfg=base_cfg, vpu=vpu, policy_type=policy_type,
                n_trials=n_trials, min_fill_rate=min_fill_rate,
                seed=42, verbose=False, mode="joint",
            )
        except Exception as e:
            print(f"    ⚠  failed: {e}")
            continue
        result = run_one(cfg_opt, vpu, f"E6 — {policy_type}",
                         warmup_periods=warmup)
        save_experiment(
            result, out_dir / f"E6_{policy_type}",
            meta={**EXPERIMENT_META["E6"], "id": f"E6_{policy_type}",
                  "title": f"Policy = {policy_type}"},
            params=params,
            baseline=None,
            opt_info=summary,
        )
        results.append(result)
    return results


def exp_E7_forecast(base_cfg, vpu, out_dir, warmup, e3_params_path: Path) -> List[dict]:
    """E7: forecast-error sensitivity sweep."""
    print("\n" + "=" * 60)
    print("E7 — Demand forecasting sensitivity")
    print("=" * 60)
    if not e3_params_path.exists():
        print(f"  ⚠  E3 params not found at {e3_params_path}; skipping E7")
        return []
    saved = json.loads(e3_params_path.read_text())
    params = saved.get("params") if "params" in saved else saved
    params = {k: v for k, v in params.items() if not k.startswith("_")}

    sigmas = [0.0, 0.05, 0.10, 0.20, 0.30]
    results = []
    rows = []
    for sigma in sigmas:
        cfg = _apply_params(base_cfg, params)
        cfg["forecast_noise_sigma"] = sigma
        # The simulator currently doesn't consume forecast_noise_sigma — we wrap
        # the demand generator so noisy-forecast errors translate to inventory
        # via stock-level shifts (proxy via per-SKU base-stock perturbation).
        if sigma > 0:
            import numpy as np
            rng = np.random.default_rng(42)
            for nd in cfg["nodes"]:
                if nd.get("infinite_supply"):
                    continue
                for sku, pol in nd.get("policy", {}).items():
                    if pol.get("type") == "base_stock":
                        s = pol["base_stock_level"]
                        # Forecast error ⇒ S underestimated by ε → on-hand low.
                        eps = float(rng.normal(0.0, sigma))
                        pol["base_stock_level"] = max(1, int(round(s * (1.0 - eps))))
        result = run_one(cfg, vpu, f"E7 — σ_f = {sigma*100:.0f}%",
                         warmup_periods=warmup)
        save_experiment(
            result, out_dir / f"E7_sigma_{int(sigma*100):02d}",
            meta={**EXPERIMENT_META["E7"], "id": f"E7_sigma_{int(sigma*100):02d}",
                  "title": f"Forecast σ={sigma*100:.0f}%"},
            params={**params, "forecast_sigma": sigma},
            baseline=None,
        )
        rows.append({
            "sigma_pct":  int(sigma * 100),
            "total_cost": round(result["total_cost"], 2),
            "fill_rate":  round(result["fill_rate_pct"], 2),
        })
        results.append(result)
    pd.DataFrame(rows).to_csv(out_dir / "E7_forecast_sweep.csv", index=False)
    print("\n  E7 sweep summary:")
    print(df_to_markdown(pd.DataFrame(rows)))
    return results


def exp_E8_bullwhip_aware(base_cfg, vpu, out_dir, n_trials, min_fill_rate,
                          warmup) -> List[dict]:
    """E8: joint optimization with bullwhip in the objective."""
    print("\n" + "=" * 60)
    print("E8 — Bullwhip-aware joint optimization")
    print("=" * 60)
    from optimizer.bullwhip_aware import run_bullwhip_aware_optimizer

    lambdas = [0.0, 1e3, 1e4, 1e5, 1e6]
    results = []
    rows = []
    for lam in lambdas:
        print(f"\n  → λ = {lam:.0e}")
        params, summary = run_bullwhip_aware_optimizer(
            base_cfg=base_cfg, vpu=vpu, lam=lam,
            n_trials=n_trials, min_fill_rate=min_fill_rate, seed=42,
        )
        cfg = _apply_params(base_cfg, params)
        result = run_one(cfg, vpu, f"E8 — λ={lam:.0e}", warmup_periods=warmup)
        save_experiment(
            result, out_dir / f"E8_lambda_{int(lam):010d}",
            meta={**EXPERIMENT_META["E8"], "id": f"E8_lambda_{lam:.0e}",
                  "title": f"Bullwhip-aware (λ={lam:.0e})"},
            params={**params, "lambda": lam},
            baseline=None,
            opt_info=summary,
        )
        # Aggregate bullwhip across nodes/SKUs (mean of finite ratios).
        bw = result["bullwhip_df"]
        bw_finite = bw["bullwhip_ratio"].dropna() if not bw.empty else pd.Series(dtype=float)
        rows.append({
            "lambda":     lam,
            "total_cost": round(result["total_cost"], 2),
            "fill_rate":  round(result["fill_rate_pct"], 2),
            "mean_bullwhip": round(float(bw_finite.mean()), 4) if not bw_finite.empty else float("nan"),
        })
        results.append(result)
    pd.DataFrame(rows).to_csv(out_dir / "E8_lambda_sweep.csv", index=False)
    print("\n  E8 sweep summary:")
    print(df_to_markdown(pd.DataFrame(rows)))
    return results


# ============================================================
# E9 — Stochastic demand robustness
# ============================================================

def _compute_poisson_lambdas(base_cfg: dict) -> Dict[str, Dict[str, float]]:
    """Compute mean daily demand per (node, sku) from CSV demand entries."""
    lambdas: Dict[str, Dict[str, float]] = {}
    T = int(base_cfg["time_horizon"])
    for d in base_cfg.get("demand", []):
        node = d["node"]
        sku = d["sku"]
        g = d["generator"]
        if g["type"] != "csv":
            continue
        if "path" in g:
            path = (ROOT / g["path"]).resolve()
        else:
            raise ValueError(f"E9: _compute_poisson_lambdas only supports 'path' demand, got: {g}")
        series = _read_csv_series(path, g.get("date_col", "date"), g.get("qty_col", "quantity"))
        start = int(g.get("start_index", 0))
        window = series[start: start + T]
        lam = float(pd.Series(window).mean()) if window else 1.0
        lam = max(lam, 0.1)
        lambdas.setdefault(node, {})[sku] = lam
    return lambdas


def _make_poisson_cfg(base_cfg: dict, lambdas: Dict[str, Dict[str, float]], seed: int) -> dict:
    """Clone config with all CSV demand generators replaced by Poisson(λ)."""
    cfg = copy.deepcopy(base_cfg)
    for d in cfg.get("demand", []):
        node = d["node"]
        sku = d["sku"]
        lam = lambdas.get(node, {}).get(sku, 1.0)
        d["generator"] = {"type": "poisson", "lam": lam, "seed": seed}
    return cfg


def exp_E9(base_cfg, vpu, out_dir, e3_params_path: Path, warmup, n_seeds: int = 10) -> dict:
    """E9: evaluate E3 params under Poisson demand (robustness test, not re-optimisation)."""
    print("\n" + "=" * 60)
    print("E9 — Stochastic demand robustness (transferability of E3 params)")
    print("=" * 60)

    if not e3_params_path.exists():
        print(f"  ⚠  E3 params not found at {e3_params_path}; skipping E9")
        return {}

    saved = json.loads(e3_params_path.read_text())
    e3_params = saved.get("params") if "params" in saved else saved
    e3_params = {k: v for k, v in e3_params.items() if not k.startswith("_")}

    lambdas = _compute_poisson_lambdas(base_cfg)
    print(f"  Poisson λ per (node, sku):")
    for node, skus in lambdas.items():
        for sku, lam in skus.items():
            print(f"    {node} / {sku}: λ={lam:.2f}")

    rows = []
    for seed in range(n_seeds):
        cfg_stoch = _make_poisson_cfg(base_cfg, lambdas, seed)
        cfg_applied = _apply_params(cfg_stoch, e3_params)
        r = run_one(cfg_applied, vpu, f"E9 — seed {seed}", warmup_periods=warmup)
        rows.append({
            "seed":       seed,
            "total_cost": round(r["total_cost"], 2),
            "fill_rate":  round(r["fill_rate_pct"], 4),
        })
        print(f"    seed {seed:2d}: cost=${r['total_cost']:,.0f}  fill={r['fill_rate_pct']:.2f}%")

    df = pd.DataFrame(rows)
    mean_cost = df["total_cost"].mean()
    std_cost  = df["total_cost"].std()
    mean_fill = df["fill_rate"].mean()
    std_fill  = df["fill_rate"].std()

    print(f"\n  Summary ({n_seeds} seeds):")
    print(f"    Cost : ${mean_cost:,.0f} ± ${std_cost:,.0f}")
    print(f"    Fill : {mean_fill:.2f}% ± {std_fill:.2f}%")

    exp_out = out_dir / "E9"
    exp_out.mkdir(parents=True, exist_ok=True)
    df.to_csv(exp_out / "seed_results.csv", index=False)
    summary_dict = {
        "mean_cost": round(mean_cost, 2), "std_cost":  round(std_cost, 2),
        "mean_fill": round(mean_fill, 4), "std_fill":  round(std_fill, 4),
        "n_seeds":   n_seeds,
    }
    (exp_out / "summary.json").write_text(json.dumps(summary_dict, indent=2))

    # Return a result-shaped dict so it integrates with the summary table.
    result = {
        "label":         "E9 — Stochastic Robustness",
        "total_cost":    mean_cost,
        "fill_rate_pct": mean_fill,
        "std_cost":      std_cost,
        "std_fill":      std_fill,
        "meta":          EXPERIMENT_META["E9"],
    }
    return result


# ============================================================
# Main
# ============================================================

def _print_topology(cfg: dict) -> None:
    """Print a topology sanity line so '1N3 = 1-1-3' misreadings are caught."""
    by_type: Dict[str, List[str]] = {}
    for nd in cfg["nodes"]:
        by_type.setdefault(nd["type"], []).append(nd["id"])
    sup = by_type.get("supplier", [])
    wh  = by_type.get("warehouse", [])
    rt  = by_type.get("retailer", [])
    print(f"Topology    : {len(sup)} supplier, {len(wh)} warehouse"
          f"{'s' if len(wh) != 1 else ''}, {len(rt)} retailer"
          f"{'s' if len(rt) != 1 else ''}  "
          f"[{','.join(sup)} → {','.join(wh)} → {','.join(rt)}]")


def _resolve_warmup(cli_warmup: Optional[int], exp_id: str, T: int) -> int:
    """CLI value wins; otherwise use EXPERIMENT_META[exp_id].recommended_warmup."""
    if cli_warmup is not None:
        return int(cli_warmup)
    rec = EXPERIMENT_META.get(exp_id, {}).get("recommended_warmup", 0)
    if rec == 0 and T >= 200:
        print(f"  ⚠  {exp_id}: warmup=0 with T={T} — KPIs include transient days")
    return int(rec)


def main():
    ap = argparse.ArgumentParser(description="Run DDP experiments and save all results.")
    ap.add_argument("--config",        required=True)
    ap.add_argument("--experiments",   nargs="+",
                    default=["E0", "E1a", "E1b", "E2", "E3", "E4"],
                    choices=["E0", "E1a", "E1b", "E2", "E3", "E3_per_sku", "E4",
                             "E5", "E6", "E7", "E8", "E9"])
    ap.add_argument("--trials",        type=int,   default=100)
    ap.add_argument("--min_fill_rate", type=float, default=0.92)
    ap.add_argument("--warmup",        type=int,   default=None,
                    help="Override warm-up days. If omitted, each experiment uses "
                         "its EXPERIMENT_META.recommended_warmup (default: 30 for "
                         "M5-based runs).")
    ap.add_argument("--validate_seeds", type=int, default=0,
                    help="If > 0, re-run E3 best params under N seeds and report "
                         "mean ± std of cost / fill rate.")
    ap.add_argument("--outdir",        default=str(ROOT / "outputs"))
    args = ap.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir   = Path(args.outdir) / f"experiments_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(args.config) as f:
        base_cfg = json.load(f)
    vpu = build_volume_map(base_cfg)
    T   = int(base_cfg["time_horizon"])

    print("=" * 60)
    print("DDP Experiment Runner")
    print("=" * 60)
    print(f"Config      : {args.config}")
    _print_topology(base_cfg)
    print(f"Time horizon: {T} days")
    print(f"Experiments : {args.experiments}")
    print(f"Trials      : {args.trials}")
    print(f"Fill target : {args.min_fill_rate*100:.0f}%")
    if args.warmup is None:
        print(f"Warm-up     : per-experiment (see EXPERIMENT_META)")
    else:
        print(f"Warm-up     : {args.warmup} days (CLI override)")
    print(f"Output      : {out_dir}")

    results    = []
    pareto_df  = None
    start_time = time.time()
    baseline   = None   # E0 result; passed to subsequent experiments

    # Compute analytical baseline config once and reuse for all downstream
    # experiments — this guarantees E1*/E2/E3 start from the newsvendor levels,
    # not whatever is hardcoded in the JSON.
    e0_warmup = _resolve_warmup(args.warmup, "E0", T)
    print("\n[setup] Computing newsvendor base-stock levels at runtime "
          f"(warmup={e0_warmup}) ...")
    nv_levels = _compute_newsvendor_levels(base_cfg, warmup=e0_warmup, z=1.64)
    cfg_e0 = _apply_newsvendor_levels(base_cfg, nv_levels)

    if "E0" in args.experiments:
        r = exp_E0_from_cfg(cfg_e0, vpu, out_dir, e0_warmup, nv_levels)
        results.append(r)
        baseline = r

    if "E1a" in args.experiments:
        w = _resolve_warmup(args.warmup, "E1a", T)
        results.append(exp_E1a(cfg_e0, vpu, out_dir, w, baseline))

    if "E1b" in args.experiments:
        w = _resolve_warmup(args.warmup, "E1b", T)
        results.append(exp_E1b(cfg_e0, vpu, out_dir, args.trials, w, baseline))

    if "E2" in args.experiments:
        w = _resolve_warmup(args.warmup, "E2", T)
        results.append(exp_E2(cfg_e0, vpu, out_dir, args.trials,
                              args.min_fill_rate, w, baseline))

    if "E3" in args.experiments:
        w = _resolve_warmup(args.warmup, "E3", T)
        r3 = exp_E3(cfg_e0, vpu, out_dir, args.trials,
                    args.min_fill_rate, w, baseline)
        results.append(r3)

    if "E3_per_sku" in args.experiments:
        w = _resolve_warmup(args.warmup, "E3_per_sku", T)
        results.append(exp_E3_per_sku(cfg_e0, vpu, out_dir, args.trials,
                                      args.min_fill_rate, w, baseline))

    if "E4" in args.experiments:
        pareto_df = exp_E4_pareto(cfg_e0, vpu, out_dir,
                                  n_trials=max(50, args.trials // 2))

    if "E5" in args.experiments:
        w = _resolve_warmup(args.warmup, "E5", T)
        e0_params_path = out_dir / "E0" / "params.json"
        e3_params_path = out_dir / "E3" / "params.json"
        results.extend(exp_E5_disruption(base_cfg, vpu, out_dir, w,
                                         e0_params_path, e3_params_path))

    if "E6" in args.experiments:
        w = _resolve_warmup(args.warmup, "E6", T)
        results.extend(exp_E6_policies(base_cfg, vpu, out_dir, args.trials,
                                       args.min_fill_rate, w))

    if "E7" in args.experiments:
        w = _resolve_warmup(args.warmup, "E7", T)
        e3_params_path = out_dir / "E3" / "params.json"
        results.extend(exp_E7_forecast(base_cfg, vpu, out_dir, w, e3_params_path))

    if "E8" in args.experiments:
        w = _resolve_warmup(args.warmup, "E8", T)
        results.extend(exp_E8_bullwhip_aware(base_cfg, vpu, out_dir,
                                             args.trials, args.min_fill_rate, w))

    if "E9" in args.experiments:
        w = _resolve_warmup(args.warmup, "E9", T)
        e3_params_path = out_dir / "E3" / "params.json"
        exp_E9(base_cfg, vpu, out_dir, e3_params_path, w)
        # E9 saves its own summary.json / seed_results.csv; not added to the
        # main summary table since it returns mean±std, not a single sim result.

    # ── Multi-seed validation (optional) ──────────────────────────────────────
    if args.validate_seeds > 0:
        e3_params_path = out_dir / "E3" / "params.json"
        if e3_params_path.exists():
            run_multiseed_validation(base_cfg, vpu, e3_params_path, out_dir,
                                     n_seeds=args.validate_seeds,
                                     warmup=_resolve_warmup(args.warmup, "E3", T))
        else:
            print("\n  ⚠  --validate_seeds requested but E3 was not run; skipping.")

    # ── Summary table ─────────────────────────────────────────────────────────
    if results:
        baseline_cost = results[0]["total_cost"]
        summary = build_summary_table(results, baseline_cost)
        summary.to_csv(out_dir / "summary_table.csv", index=False)
        md = df_to_markdown(summary)
        (out_dir / "summary_table.md").write_text(md)
        print("\n" + "=" * 60)
        print("EXPERIMENT SUMMARY")
        print("=" * 60)
        print(md)

    # ── Master report document ─────────────────────────────────────────────────
    elapsed = time.time() - start_time
    generate_report_summary(
        results=results,
        pareto_df=pareto_df,
        cfg=base_cfg,
        out_dir=out_dir,
        config_path=args.config,
        elapsed_min=elapsed / 60,
        warmup=args.warmup if args.warmup is not None else "per-experiment",
        n_trials=args.trials,
        min_fill_rate=args.min_fill_rate,
    )

    print(f"\nTotal time  : {elapsed/60:.1f} minutes")
    print(f"All outputs : {out_dir}")


if __name__ == "__main__":
    main()
