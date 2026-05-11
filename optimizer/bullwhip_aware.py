"""optimizer/bullwhip_aware.py

Joint optimization that adds the per-echelon bullwhip ratio (mean across
nodes/SKUs) to the objective with a multiplier λ.

Re-uses the simulator + the corrected bullwhip metric from run_experiments.
Used by experiment E8.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, Tuple

import optuna
from optuna.samplers import TPESampler
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from optimizer.optimize import (
    _extract_base_stock_levels, _extract_dispatch_thresholds, _apply_params,
    S_LOWER_MULT, S_UPPER_MULT, S_MIN_ABS, DISPATCH_LOWER, DISPATCH_UPPER,
)
from scripts.run_simulation import (
    build_from_config, build_volume_map, build_weight_map, build_disruptions,
)
from engine.simulator import Simulator


PENALTY_PER_PCT = 1_000_000


def _evaluate_with_bullwhip(cfg: dict, vpu: dict, warmup: int = 0
                            ) -> Tuple[float, float, float]:
    """Run the sim and return (total_cost, fill_rate, mean_bullwhip)."""
    net, demand_by_node, T = build_from_config(cfg)
    sim = Simulator(network=net, demand_by_node=demand_by_node, T=T,
                    order_processing_delay=1, volume_per_unit=vpu,
                    weight_per_unit=build_weight_map(cfg),
                    disruptions=build_disruptions(cfg))
    sim.run()
    rows = [m.__dict__ for m in sim.metrics]
    df = pd.DataFrame(rows)
    eod = df[(df["phase"] == "EOD") & (df["t"] >= warmup)]

    total_cost = float(eod["total_cost"].sum())
    total_dem  = float(eod["demand"].sum())
    total_ful  = float(eod["fulfilled_external"].sum())
    fill_rate  = total_ful / total_dem if total_dem > 0 else 1.0

    orders_df = pd.DataFrame(sim.orders_log)
    orders_df = orders_df[orders_df["t"] >= warmup] if not orders_df.empty else orders_df
    if orders_df.empty:
        return total_cost, fill_rate, float("nan")

    retailer_ids = {n["id"] for n in cfg["nodes"] if n["type"] == "retailer"}
    child_to_parent = {e["to"]: e["from"] for e in cfg["edges"]}

    incoming: Dict[tuple, pd.Series] = {}
    for (nid, sku), grp in eod[eod["node_id"].isin(retailer_ids)].groupby(["node_id", "sku"]):
        incoming[(nid, sku)] = grp.set_index("t")["demand"].sort_index()
    for (cid, sku), grp in orders_df.groupby(["node_id", "sku"]):
        parent = child_to_parent.get(cid)
        if parent is None:
            continue
        s = grp.set_index("t")["orders_to_parent"].sort_index()
        key = (parent, sku)
        incoming[key] = (incoming.get(key, pd.Series(dtype=float))
                         .add(s, fill_value=0.0))

    def cv2(s: pd.Series) -> float:
        if s is None or s.empty:
            return float("nan")
        m = s.mean()
        return float((s.std() / m) ** 2) if m > 0 else float("nan")

    ratios = []
    for (nid, sku), grp in orders_df.groupby(["node_id", "sku"]):
        out = grp.set_index("t")["orders_to_parent"].sort_index()
        cv2_in  = cv2(incoming.get((nid, sku)))
        cv2_out = cv2(out)
        if cv2_in and not math.isnan(cv2_in) and cv2_in > 0 and not math.isnan(cv2_out):
            ratios.append(cv2_out / cv2_in)
    mean_bw = sum(ratios) / len(ratios) if ratios else float("nan")
    return total_cost, fill_rate, mean_bw


def run_bullwhip_aware_optimizer(
    base_cfg: dict,
    vpu: dict,
    lam: float,
    n_trials: int = 100,
    min_fill_rate: float = 0.92,
    seed: int = 42,
    verbose: bool = False,
) -> Tuple[dict, dict]:
    """Joint search with objective = total_cost + λ × mean_bullwhip."""
    levels   = _extract_base_stock_levels(base_cfg)
    dispatch = _extract_dispatch_thresholds(base_cfg)

    def objective(trial: optuna.Trial) -> float:
        params: Dict[str, float] = {}
        for (nid, sku), S_anal in levels.items():
            lo = max(S_MIN_ABS, int(S_anal * S_LOWER_MULT))
            hi = max(lo + 1, int(S_anal * S_UPPER_MULT))
            params[f"S_{nid}__{sku}"] = trial.suggest_int(f"S_{nid}__{sku}", lo, hi)
        for route_id in dispatch:
            params[f"D_{route_id}"] = trial.suggest_float(
                f"D_{route_id}", DISPATCH_LOWER, DISPATCH_UPPER
            )

        cfg_trial = _apply_params(base_cfg, params)
        cost, fill, bw = _evaluate_with_bullwhip(cfg_trial, vpu)
        shortfall = max(0.0, min_fill_rate - fill)
        penalty = shortfall * 100 * PENALTY_PER_PCT
        bw_term = lam * bw if not math.isnan(bw) else 0.0

        trial.set_user_attr("total_cost",  cost)
        trial.set_user_attr("fill_rate",   fill)
        trial.set_user_attr("mean_bullwhip", bw)
        return cost + penalty + bw_term

    if not verbose:
        optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(
        direction="minimize",
        sampler=TPESampler(seed=seed),
        study_name=f"ddp_e8_lambda_{lam:.0e}",
    )
    study.optimize(objective, n_trials=n_trials, show_progress_bar=verbose)

    feasible = [t for t in study.trials
                if t.user_attrs.get("fill_rate", 0) >= min_fill_rate]
    best = (min(feasible, key=lambda t: t.user_attrs["total_cost"])
            if feasible else study.best_trial)

    summary = {
        "lambda":    lam,
        "n_trials":  n_trials,
        "n_feasible": len(feasible),
        "best_trial": best.number,
        "best_cost":  best.user_attrs.get("total_cost"),
        "best_fill":  best.user_attrs.get("fill_rate"),
        "best_bullwhip": best.user_attrs.get("mean_bullwhip"),
    }
    return best.params, summary
