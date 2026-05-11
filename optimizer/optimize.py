"""
optimizer/optimize.py
=====================
Optuna-based optimizer for the DDP supply chain simulator.

Searches over base-stock levels (and optionally dispatch thresholds)
to minimise total cost subject to a minimum fill rate constraint.

Three optimization modes
------------------------
  inventory   : optimize base-stock S levels only
  transport   : optimize min_dispatch_utilization per lane only
  joint       : optimize both simultaneously (main research contribution)

Usage (CLI)
-----------
  python optimizer/optimize.py --config config/1n3_5sku.json
  python optimizer/optimize.py --config config/1n3_5sku.json --mode joint
  python optimizer/optimize.py --config config/1n3_5sku.json --mode inventory --trials 200

Usage (programmatic)
--------------------
  from optimizer.optimize import run_optimizer
  result = run_optimizer("config/1n3_5sku.json", mode="joint", n_trials=100)
  # OR pass a pre-loaded dict:
  result = run_optimizer(base_cfg=cfg_dict, mode="joint", n_trials=100,
                         volume_per_unit=vpu_dict)
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import optuna
from optuna.samplers import TPESampler

# ── project root on path ────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_simulation import build_from_config, build_volume_map
from engine.simulator import Simulator


# ============================================================
# Result container
# ============================================================

@dataclass
class OptimizationResult:
    best_params: Dict          # the winning parameter set
    best_cost: float
    best_fill_rate: float
    best_trial: int
    n_trials: int
    mode: str
    min_fill_rate: float       # constraint that was enforced
    study: optuna.Study        # full optuna study for further analysis


# ============================================================
# Parameter bounds
# ============================================================

# Base-stock level search bounds — multipliers on the analytical S level
S_LOWER_MULT = 0.3    # minimum = 30% of analytical S
S_UPPER_MULT = 3.0    # maximum = 300% of analytical S
S_MIN_ABS    = 10     # absolute floor so we never try S=0

# Dispatch utilization bounds
DISPATCH_LOWER = 0.0
DISPATCH_UPPER = 0.9


# ============================================================
# Config manipulation helpers
# ============================================================

def _extract_base_stock_levels(cfg: dict) -> Dict[Tuple[str, str], int]:
    """Return {(node_id, sku): base_stock_level} for all non-supplier nodes."""
    skus = cfg["skus"]
    levels = {}
    for nd in cfg["nodes"]:
        if nd.get("infinite_supply", False):
            continue
        for sku in skus:
            pol = nd["policy"].get(sku, {})
            if pol.get("type") == "base_stock":
                levels[(nd["id"], sku)] = int(pol["base_stock_level"])
    return levels


def _extract_dispatch_thresholds(cfg: dict) -> Dict[str, float]:
    """Return {route_id: min_dispatch_utilization} for all edges."""
    thresholds = {}
    for e in cfg["edges"]:
        rid = e.get("route_id") or f"{e['from']}_{e['to']}"
        thresholds[rid] = float(e.get("min_dispatch_utilization", 0.0))
    return thresholds


def _apply_params(cfg: dict, params: dict) -> dict:
    """
    Deep-copy cfg and inject candidate parameter values.
    params keys:
      S_{node_id}__{sku}   -> base_stock_level
      D_{route_id}         -> min_dispatch_utilization
    """
    cfg = copy.deepcopy(cfg)
    skus = cfg["skus"]

    for nd in cfg["nodes"]:
        if nd.get("infinite_supply", False):
            continue
        for sku in skus:
            key = f"S_{nd['id']}__{sku}"
            if key in params:
                pol = nd["policy"].get(sku, {})
                if pol.get("type") == "base_stock":
                    nd["policy"][sku]["base_stock_level"] = int(params[key])

    for e in cfg["edges"]:
        rid = e.get("route_id") or f"{e['from']}_{e['to']}"
        key = f"D_{rid}"
        if key in params:
            e["min_dispatch_utilization"] = float(params[key])

    return cfg


# ============================================================
# Single simulation evaluation
# ============================================================

def evaluate(cfg: dict, volume_per_unit: dict) -> Tuple[float, float]:
    """
    Run one full simulation. Returns (total_cost, fill_rate).
    """
    net, demand_by_node, T = build_from_config(cfg)
    sim = Simulator(
        network=net,
        demand_by_node=demand_by_node,
        T=T,
        order_processing_delay=1,
        volume_per_unit=volume_per_unit,
    )
    sim.run()

    total_cost = sum(m.total_cost for m in sim.metrics)
    total_dem  = sum(m.demand for m in sim.metrics)
    total_ful  = sum(m.fulfilled_external for m in sim.metrics)
    fill_rate  = total_ful / total_dem if total_dem > 0 else 1.0

    return total_cost, fill_rate


def evaluate_with_sku_fills(cfg: dict, volume_per_unit: dict) -> Tuple[float, float, Dict[str, float]]:
    """Same as evaluate, but also returns per-SKU fill rates."""
    net, demand_by_node, T = build_from_config(cfg)
    sim = Simulator(
        network=net, demand_by_node=demand_by_node, T=T,
        order_processing_delay=1, volume_per_unit=volume_per_unit,
    )
    sim.run()
    total_cost = sum(m.total_cost for m in sim.metrics)
    sku_dem: Dict[str, float] = {}
    sku_ful: Dict[str, float] = {}
    total_dem = 0.0
    total_ful = 0.0
    for m in sim.metrics:
        sku_dem[m.sku] = sku_dem.get(m.sku, 0.0) + m.demand
        sku_ful[m.sku] = sku_ful.get(m.sku, 0.0) + m.fulfilled_external
        total_dem += m.demand
        total_ful += m.fulfilled_external
    fill_rate = total_ful / total_dem if total_dem > 0 else 1.0
    sku_fills = {
        sku: (sku_ful[sku] / sku_dem[sku] if sku_dem[sku] > 0 else 1.0)
        for sku in sku_dem
    }
    return total_cost, fill_rate, sku_fills


# ============================================================
# Optuna objective factory
# ============================================================

def make_objective(
    base_cfg: dict,
    volume_per_unit: dict,
    mode: str,
    min_fill_rate: float,
    analytical_levels: Dict[Tuple[str, str], int],
    analytical_dispatch: Dict[str, float],
    per_sku_constraint: bool = False,
):
    PENALTY_PER_PCT = 1_000_000   # cost penalty per 1% fill rate shortfall

    def objective(trial: optuna.Trial) -> float:
        params = {}

        if mode in ("inventory", "joint"):
            for (node_id, sku), S_anal in analytical_levels.items():
                lo = max(S_MIN_ABS, int(S_anal * S_LOWER_MULT))
                hi = max(lo + 1,    int(S_anal * S_UPPER_MULT))
                key = f"S_{node_id}__{sku}"
                params[key] = trial.suggest_int(key, lo, hi)

        if mode in ("transport", "joint"):
            for route_id in analytical_dispatch:
                key = f"D_{route_id}"
                params[key] = trial.suggest_float(key, DISPATCH_LOWER, DISPATCH_UPPER)

        cfg_trial = _apply_params(base_cfg, params)

        if per_sku_constraint:
            total_cost, fill_rate, sku_fills = evaluate_with_sku_fills(
                cfg_trial, volume_per_unit
            )
            penalty = 0.0
            for sku, f in sku_fills.items():
                shortfall = max(0.0, min_fill_rate - f)
                penalty += shortfall * 100 * PENALTY_PER_PCT
            trial.set_user_attr("sku_fills", sku_fills)
            min_sku_fill = min(sku_fills.values()) if sku_fills else fill_rate
            trial.set_user_attr("min_sku_fill", min_sku_fill)
        else:
            total_cost, fill_rate = evaluate(cfg_trial, volume_per_unit)
            shortfall = max(0.0, min_fill_rate - fill_rate)
            penalty   = shortfall * 100 * PENALTY_PER_PCT

        trial.set_user_attr("fill_rate",  fill_rate)
        trial.set_user_attr("total_cost", total_cost)
        trial.set_user_attr("penalty",    penalty)

        return total_cost + penalty

    return objective


# ============================================================
# Main optimizer entry point
# ============================================================

def run_optimizer(
    config_path: Optional[str] = None,
    mode: str = "inventory",
    n_trials: int = 100,
    min_fill_rate: float = 0.92,
    n_jobs: int = 1,
    seed: int = 42,
    verbose: bool = True,
    # --- programmatic use: pass pre-loaded config instead of path ---
    base_cfg: Optional[dict] = None,
    volume_per_unit: Optional[dict] = None,
    per_sku_constraint: bool = False,
) -> OptimizationResult:
    """
    Run the optimizer.

    Supply either config_path (CLI use) or base_cfg + volume_per_unit
    (programmatic use from run_experiments.py).

    Parameters
    ----------
    config_path    : path to JSON config file (or None if base_cfg provided)
    base_cfg       : pre-loaded config dict (alternative to config_path)
    volume_per_unit: pre-computed volume map (required when base_cfg is used)
    mode           : 'inventory' | 'transport' | 'joint'
    n_trials       : number of optuna trials
    min_fill_rate  : minimum acceptable fill rate (soft constraint)
    n_jobs         : parallel trials (-1 = all cores)
    seed           : random seed for reproducibility
    verbose        : print progress
    """

    if mode not in ("inventory", "transport", "joint"):
        raise ValueError(f"mode must be 'inventory', 'transport', or 'joint'. Got: {mode}")

    # ── resolve config ────────────────────────────────────────────────────────
    if base_cfg is None:
        if config_path is None:
            raise ValueError("Provide either config_path or base_cfg.")
        with open(config_path) as f:
            base_cfg = json.load(f)
        volume_per_unit = build_volume_map(base_cfg)
    else:
        if volume_per_unit is None:
            volume_per_unit = build_volume_map(base_cfg)

    analytical_levels   = _extract_base_stock_levels(base_cfg)
    analytical_dispatch = _extract_dispatch_thresholds(base_cfg)

    if verbose:
        print("=" * 65)
        print("DDP Optimizer")
        print("=" * 65)
        print(f"  Mode         : {mode}")
        print(f"  Trials       : {n_trials}")
        print(f"  Min fill rate: {min_fill_rate*100:.1f}%")
        print(f"  SKUs         : {base_cfg['skus']}")
        n_vars = 0
        if mode in ("inventory", "joint"):
            n_vars += len(analytical_levels)
        if mode in ("transport", "joint"):
            n_vars += len(analytical_dispatch)
        print(f"  Decision vars: {n_vars}")
        print()

    # ── baseline ─────────────────────────────────────────────────────────────
    if verbose:
        print("Running baseline simulation...")
    baseline_cost, baseline_fill = evaluate(base_cfg, volume_per_unit)
    if verbose:
        print(f"  Baseline cost      : {baseline_cost:,.2f}")
        print(f"  Baseline fill rate : {baseline_fill*100:.2f}%")
        print()

    # ── optuna study ─────────────────────────────────────────────────────────
    sampler = TPESampler(seed=seed)
    if not verbose:
        optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(
        direction="minimize",
        sampler=sampler,
        study_name=f"ddp_{mode}",
    )

    objective = make_objective(
        base_cfg=base_cfg,
        volume_per_unit=volume_per_unit,
        mode=mode,
        min_fill_rate=min_fill_rate,
        analytical_levels=analytical_levels,
        analytical_dispatch=analytical_dispatch,
        per_sku_constraint=per_sku_constraint,
    )

    if verbose:
        print(f"Starting optimization ({n_trials} trials)...")
        print("-" * 65)

    study.optimize(
        objective,
        n_trials=n_trials,
        n_jobs=n_jobs,
        show_progress_bar=verbose,
    )

    # ── best feasible trial ───────────────────────────────────────────────────
    if per_sku_constraint:
        feasible = [
            t for t in study.trials
            if t.user_attrs.get("min_sku_fill", 0) >= min_fill_rate
        ]
    else:
        feasible = [
            t for t in study.trials
            if t.user_attrs.get("fill_rate", 0) >= min_fill_rate
        ]

    if feasible:
        best = min(feasible, key=lambda t: t.user_attrs["total_cost"])
    else:
        best = study.best_trial
        if verbose:
            print(f"\n⚠  No trial met fill rate ≥ {min_fill_rate*100:.1f}%.")
            print("   Returning best overall. Consider lowering min_fill_rate.")

    best_cost      = best.user_attrs.get("total_cost", best.value)
    best_fill_rate = best.user_attrs.get("fill_rate",  0.0)

    # ── print summary ─────────────────────────────────────────────────────────
    if verbose:
        improvement = 100 * (baseline_cost - best_cost) / baseline_cost
        direction   = "improvement" if improvement >= 0 else "increase"

        print("\n" + "=" * 65)
        print("Optimization complete")
        print("=" * 65)
        print(f"  Best trial         : #{best.number}")
        print(f"  Best total cost    : {best_cost:,.2f}  "
              f"({abs(improvement):.1f}% {direction} vs baseline)")
        print(f"  Best fill rate     : {best_fill_rate*100:.2f}%")
        print(f"  Baseline cost      : {baseline_cost:,.2f}")
        print(f"  Feasible trials    : {len(feasible)} / {n_trials}")
        print()

        if mode in ("inventory", "joint"):
            print("Best base-stock levels:")
            skus = base_cfg["skus"]
            nodes_in_order = [
                nd["id"] for nd in base_cfg["nodes"]
                if not nd.get("infinite_supply", False)
            ]
            header = f"  {'Node':<14}" + "".join(f"  {s:<20}" for s in skus)
            print(header)
            print("  " + "-" * (14 + 22 * len(skus)))
            for nid in nodes_in_order:
                row = f"  {nid:<14}"
                for sku in skus:
                    key = f"S_{nid}__{sku}"
                    if key in best.params:
                        anal = analytical_levels.get((nid, sku), "—")
                        opt  = best.params[key]
                        row += f"  {opt:<6} (anal:{anal:<6})"
                    else:
                        row += f"  {'—':<20}"
                print(row)

        if mode in ("transport", "joint"):
            print("\nBest dispatch thresholds:")
            for e in base_cfg["edges"]:
                rid = e.get("route_id") or f"{e['from']}_{e['to']}"
                key = f"D_{rid}"
                if key in best.params:
                    print(f"  {e['from']:>12} → {e['to']:<12}  "
                          f"{best.params[key]*100:.1f}%  "
                          f"(was {analytical_dispatch[rid]*100:.1f}%)")
        print()

    return OptimizationResult(
        best_params=best.params,
        best_cost=best_cost,
        best_fill_rate=best_fill_rate,
        best_trial=best.number,
        n_trials=n_trials,
        mode=mode,
        min_fill_rate=min_fill_rate,
        study=study,
    )


# ============================================================
# CLI entry point
# ============================================================

def main():
    ap = argparse.ArgumentParser(
        description="Optimize inventory and/or transport policies."
    )
    ap.add_argument("--config",        required=True)
    ap.add_argument("--mode",          default="inventory",
                    choices=["inventory", "transport", "joint"])
    ap.add_argument("--trials",        type=int,   default=100)
    ap.add_argument("--min_fill_rate", type=float, default=0.92)
    ap.add_argument("--jobs",          type=int,   default=1)
    ap.add_argument("--seed",          type=int,   default=42)
    ap.add_argument("--out",           default=None,
                    help="Save best params to this JSON file")
    args = ap.parse_args()

    result = run_optimizer(
        config_path=args.config,
        mode=args.mode,
        n_trials=args.trials,
        min_fill_rate=args.min_fill_rate,
        n_jobs=args.jobs,
        seed=args.seed,
        verbose=True,
    )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "mode":           result.mode,
            "best_trial":     result.best_trial,
            "best_cost":      result.best_cost,
            "best_fill_rate": result.best_fill_rate,
            "min_fill_rate":  result.min_fill_rate,
            "n_trials":       result.n_trials,
            "best_params":    result.best_params,
        }
        out_path.write_text(json.dumps(payload, indent=2))
        print(f"Best params saved to: {out_path}")


if __name__ == "__main__":
    main()