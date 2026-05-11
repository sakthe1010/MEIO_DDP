"""optimizer/pareto.py

Two-objective NSGA-II Pareto search over (total_cost, -fill_rate).

Used by experiment E4 to produce a smooth cost-vs-fill-rate frontier that does
not depend on choosing fill-rate target points up-front.

The constraint sweep (existing exp_E4_pareto in run_experiments.py) runs
alongside this and is kept as a sanity check.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import optuna
from optuna.samplers import NSGAIISampler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from optimizer.optimize import (
    _extract_base_stock_levels, _extract_dispatch_thresholds, _apply_params,
    evaluate, S_LOWER_MULT, S_UPPER_MULT, S_MIN_ABS,
    DISPATCH_LOWER, DISPATCH_UPPER,
)
from scripts.run_simulation import build_volume_map


@dataclass
class ParetoResult:
    frontier: List[dict]   # list of {"total_cost", "fill_rate", "params"}
    study: optuna.Study
    n_trials: int


def run_nsga2_pareto(
    base_cfg: dict,
    volume_per_unit: Optional[dict] = None,
    n_trials: int = 200,
    seed: int = 42,
    population_size: int = 32,
    verbose: bool = True,
) -> ParetoResult:
    """Run a two-objective NSGA-II study minimising (cost, -fill).

    Returns the non-dominated set extracted from `study.best_trials`.
    """
    if volume_per_unit is None:
        volume_per_unit = build_volume_map(base_cfg)

    levels   = _extract_base_stock_levels(base_cfg)
    dispatch = _extract_dispatch_thresholds(base_cfg)

    def objective(trial: optuna.Trial) -> Tuple[float, float]:
        params: Dict[str, float] = {}
        for (node_id, sku), S_anal in levels.items():
            lo = max(S_MIN_ABS, int(S_anal * S_LOWER_MULT))
            hi = max(lo + 1,    int(S_anal * S_UPPER_MULT))
            key = f"S_{node_id}__{sku}"
            params[key] = trial.suggest_int(key, lo, hi)
        for route_id in dispatch:
            key = f"D_{route_id}"
            params[key] = trial.suggest_float(key, DISPATCH_LOWER, DISPATCH_UPPER)

        cfg_trial = _apply_params(base_cfg, params)
        total_cost, fill_rate = evaluate(cfg_trial, volume_per_unit)
        trial.set_user_attr("total_cost", total_cost)
        trial.set_user_attr("fill_rate",  fill_rate)
        # Minimise cost; minimise (-fill_rate) is equivalent to maximising fill_rate.
        return total_cost, -fill_rate

    if not verbose:
        optuna.logging.set_verbosity(optuna.logging.WARNING)

    sampler = NSGAIISampler(seed=seed, population_size=population_size)
    study = optuna.create_study(
        directions=["minimize", "minimize"],
        sampler=sampler,
        study_name="ddp_nsga2_pareto",
    )
    study.optimize(objective, n_trials=n_trials, show_progress_bar=verbose)

    frontier: List[dict] = []
    for t in study.best_trials:
        frontier.append({
            "total_cost": float(t.user_attrs.get("total_cost", t.values[0])),
            "fill_rate":  float(t.user_attrs.get("fill_rate", -t.values[1])),
            "params":     dict(t.params),
            "trial_number": t.number,
        })
    # Sort by fill rate ascending for plotting.
    frontier.sort(key=lambda r: r["fill_rate"])
    return ParetoResult(frontier=frontier, study=study, n_trials=n_trials)
