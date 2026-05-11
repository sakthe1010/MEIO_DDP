"""optimizer/policy_search.py

Per-policy parameter search for the E6 policy comparison experiment.

Each policy has its own parameter shape, so the generic
optimize.run_optimizer (which assumes base_stock_level keys) doesn't work
out-of-the-box for `ss`, `periodic_review`, or `echelon_stock`.

This module wraps Optuna with a small registry of policy search spaces and
returns a config dict where the chosen policy has been written into every
non-supplier node.
"""
from __future__ import annotations

import copy
import math
import sys
from pathlib import Path
from typing import Dict, Tuple

import optuna
from optuna.samplers import TPESampler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from optimizer.optimize import (
    _extract_base_stock_levels, _extract_dispatch_thresholds, _apply_params,
    evaluate, S_LOWER_MULT, S_UPPER_MULT, S_MIN_ABS,
)


PENALTY_PER_PCT = 1_000_000


def _set_policy_for_all_nodes(cfg: dict, policy_type: str,
                              params: Dict[str, float],
                              levels: Dict[Tuple[str, str], int]) -> dict:
    """Inject the chosen policy (with trial params) into every non-supplier node."""
    cfg = copy.deepcopy(cfg)
    for nd in cfg["nodes"]:
        if nd.get("infinite_supply", False):
            continue
        for sku in cfg["skus"]:
            S_anal = levels.get((nd["id"], sku), 100)
            key_S = f"S_{nd['id']}__{sku}"
            S = int(params.get(key_S, S_anal))

            if policy_type == "base_stock":
                nd["policy"][sku] = {"type": "base_stock", "base_stock_level": S}

            elif policy_type == "ss":
                # s = α·S; reorder when on_hand+pipe ≤ s, refill to S.
                key_alpha = f"alpha_{nd['id']}__{sku}"
                alpha = float(params.get(key_alpha, 0.7))
                s = max(1, int(round(S * alpha)))
                nd["policy"][sku] = {"type": "sS", "s": s, "S": max(s + 1, S)}

            elif policy_type == "periodic_review":
                key_R = f"R_{nd['id']}__{sku}"
                R = int(params.get(key_R, 7))
                nd["policy"][sku] = {
                    "type": "periodic_review",
                    "review_period": R,
                    "order_up_to": S,
                }

            elif policy_type == "echelon_stock":
                nd["policy"][sku] = {
                    "type": "echelon_stock",
                    "echelon_base_stock_level": S,
                }

            else:
                raise ValueError(f"Unsupported policy_type: {policy_type}")
    return cfg


def run_policy_optimizer(
    base_cfg: dict,
    vpu: dict,
    policy_type: str,
    n_trials: int = 100,
    min_fill_rate: float = 0.92,
    seed: int = 42,
    verbose: bool = False,
    mode: str = "inventory",
) -> Tuple[dict, dict, dict]:
    """Optimize a specific policy. Returns (cfg_with_best_params, params, summary).

    mode="inventory" searches only inventory parameters (original E6 behaviour).
    mode="joint" additionally optimises all dispatch thresholds, giving each
    policy equal access to transport consolidation benefits.
    """
    levels = _extract_base_stock_levels(base_cfg)
    dispatch_routes = _extract_dispatch_thresholds(base_cfg) if mode == "joint" else {}

    def objective(trial: optuna.Trial) -> float:
        params: Dict[str, float] = {}
        for (nid, sku), S_anal in levels.items():
            lo = max(S_MIN_ABS, int(S_anal * S_LOWER_MULT))
            hi = max(lo + 1, int(S_anal * S_UPPER_MULT))
            params[f"S_{nid}__{sku}"] = trial.suggest_int(f"S_{nid}__{sku}", lo, hi)

        if policy_type == "ss":
            for (nid, sku) in levels:
                params[f"alpha_{nid}__{sku}"] = trial.suggest_float(
                    f"alpha_{nid}__{sku}", 0.3, 0.95
                )
        elif policy_type == "periodic_review":
            for (nid, sku) in levels:
                params[f"R_{nid}__{sku}"] = trial.suggest_int(
                    f"R_{nid}__{sku}", 1, 14
                )

        if mode == "joint":
            for route_id in dispatch_routes:
                params[f"D_{route_id}"] = trial.suggest_float(
                    f"D_{route_id}", 0.0, 0.95
                )

        cfg_trial = _set_policy_for_all_nodes(base_cfg, policy_type, params, levels)
        if mode == "joint":
            cfg_trial = _apply_params(cfg_trial, params)
        total_cost, fill_rate = evaluate(cfg_trial, vpu)

        shortfall = max(0.0, min_fill_rate - fill_rate)
        penalty = shortfall * 100 * PENALTY_PER_PCT
        trial.set_user_attr("fill_rate", fill_rate)
        trial.set_user_attr("total_cost", total_cost)
        return total_cost + penalty

    if not verbose:
        optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(
        direction="minimize",
        sampler=TPESampler(seed=seed),
        study_name=f"ddp_e6_{policy_type}",
    )
    study.optimize(objective, n_trials=n_trials, show_progress_bar=verbose)

    feasible = [t for t in study.trials
                if t.user_attrs.get("fill_rate", 0) >= min_fill_rate]
    best = (min(feasible, key=lambda t: t.user_attrs["total_cost"])
            if feasible else study.best_trial)

    cfg_best = _set_policy_for_all_nodes(base_cfg, policy_type, best.params, levels)
    if mode == "joint":
        cfg_best = _apply_params(cfg_best, best.params)
    summary = {
        "policy_type":  policy_type,
        "n_trials":     n_trials,
        "n_feasible":   len(feasible),
        "best_trial":   best.number,
        "best_cost":    best.user_attrs.get("total_cost", best.value),
        "best_fill":    best.user_attrs.get("fill_rate", 0.0),
    }
    return cfg_best, best.params, summary
