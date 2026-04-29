"""
scripts/multi_seed_validation.py
=================================
Runs any DDP experiment configuration across multiple random seeds and
reports mean ± 95% confidence intervals for total cost and fill rate.

This is essential for academic credibility — single-seed results can be
lucky or unlucky; CI across N seeds shows the result is robust.

Usage
-----
  # Validate the joint-optimized params from a previous E3 run
  python scripts/multi_seed_validation.py \\
      --config config/1n3_5sku.json \\
      --params outputs/experiments_<ts>/E3/params.json \\
      --seeds 5

  # Validate the baseline (no params file = uses config as-is)
  python scripts/multi_seed_validation.py \\
      --config config/1n3_5sku.json \\
      --seeds 10 --warmup 100

  # Compare two configurations side by side
  python scripts/multi_seed_validation.py \\
      --config config/1n3_5sku.json \\
      --params outputs/experiments_<ts>/E3/params.json \\
      --compare outputs/experiments_<ts>/E0/params.json \\
      --seeds 5

Output
------
  Prints a summary table with mean, std, 95% CI for each KPI.
  Saves results to --outdir if provided.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_experiments import run_one
from scripts.run_simulation import build_volume_map
from optimizer.optimize import _apply_params


# ============================================================
# Core
# ============================================================

def run_multi_seed(
    cfg: dict,
    seeds: List[int],
    label: str = "experiment",
    warmup_periods: int = 0,
) -> pd.DataFrame:
    """
    Run the same configuration under each seed in `seeds`.
    Returns a DataFrame with one row per seed and columns:
    seed, total_cost, holding_cost, transport_cost, ordering_cost,
    backlog_cost, fill_rate_pct.
    """
    vpu = build_volume_map(cfg)
    rows = []
    for i, seed in enumerate(seeds):
        seeded_cfg = copy.deepcopy(cfg)
        seeded_cfg["seed"] = seed
        print(f"  [{label}] seed {seed}  ({i+1}/{len(seeds)})", flush=True)
        result = run_one(seeded_cfg, vpu, label=f"{label}_s{seed}",
                         warmup_periods=warmup_periods)
        rows.append({
            "seed":            seed,
            "total_cost":      result["total_cost"],
            "holding_cost":    result["holding_cost"],
            "transport_cost":  result["transport_cost"],
            "ordering_cost":   result["ordering_cost"],
            "backlog_cost":    result["backlog_cost"],
            "fill_rate_pct":   result["fill_rate_pct"],
        })
    return pd.DataFrame(rows)


def summarise(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Compute mean, std, 95% CI half-width for each KPI column."""
    n = len(df)
    # t-critical for 95% CI (use z=1.96 for n >= 30, t-table otherwise)
    from scipy import stats as _stats
    t_crit = _stats.t.ppf(0.975, df=n - 1) if n > 1 else 0.0

    metrics = ["total_cost", "holding_cost", "transport_cost",
               "ordering_cost", "backlog_cost", "fill_rate_pct"]
    rows = []
    for m in metrics:
        mean = df[m].mean()
        std  = df[m].std(ddof=1) if n > 1 else 0.0
        ci   = t_crit * std / (n ** 0.5) if n > 1 else 0.0
        rows.append({
            "label":    label,
            "metric":   m,
            "n_seeds":  n,
            "mean":     round(mean, 2),
            "std":      round(std, 2),
            "ci_95":    round(ci, 2),
            "ci_lo":    round(mean - ci, 2),
            "ci_hi":    round(mean + ci, 2),
        })
    return pd.DataFrame(rows)


def print_summary(summary: pd.DataFrame):
    label = summary["label"].iloc[0]
    n     = summary["n_seeds"].iloc[0]
    print(f"\n{'='*62}")
    print(f"  {label}  (n={n} seeds, 95% CI)")
    print(f"{'='*62}")
    print(f"  {'Metric':<18}  {'Mean':>14}  {'±CI':>12}  {'[Lo, Hi]'}")
    print(f"  {'-'*58}")
    for _, row in summary.iterrows():
        print(f"  {row['metric']:<18}  {row['mean']:>14,.2f}"
              f"  ±{row['ci_95']:>10,.2f}"
              f"  [{row['ci_lo']:,.2f}, {row['ci_hi']:,.2f}]")


# ============================================================
# CLI
# ============================================================

def main():
    ap = argparse.ArgumentParser(
        description="Multi-seed statistical validation for DDP experiments."
    )
    ap.add_argument("--config",   required=True,  help="Base JSON config")
    ap.add_argument("--params",   default=None,
                    help="params.json from a previous experiment run (e.g. E3/params.json). "
                         "If omitted, the config is used as-is.")
    ap.add_argument("--compare",  default=None,
                    help="Optional second params.json to compare against --params")
    ap.add_argument("--seeds",    type=int, default=5,
                    help="Number of random seeds to use (default: 5)")
    ap.add_argument("--seed_start", type=int, default=100,
                    help="First seed value; subsequent seeds = seed_start + i*37 (default: 100)")
    ap.add_argument("--warmup",   type=int, default=0,
                    help="Warm-up days excluded from KPIs (default: 0)")
    ap.add_argument("--outdir",   default=None, help="Directory to save CSV results")
    args = ap.parse_args()

    seeds = [args.seed_start + i * 37 for i in range(args.seeds)]

    with open(args.config) as f:
        base_cfg = json.load(f)

    configs = {}

    if args.params:
        with open(args.params) as f:
            raw = json.load(f)
        params = raw if not isinstance(raw.get("best_params"), dict) else raw
        # handle both formats: direct params dict OR {best_params: ...}
        param_dict = params.get("best_params", params)
        label = Path(args.params).parent.name  # e.g. "E3"
        configs[label] = _apply_params(base_cfg, param_dict)
    else:
        configs["baseline"] = base_cfg

    if args.compare:
        with open(args.compare) as f:
            raw = json.load(f)
        param_dict2 = raw.get("best_params", raw)
        label2 = Path(args.compare).parent.name
        configs[label2] = _apply_params(base_cfg, param_dict2)

    all_summaries = []
    raw_dfs = {}
    print(f"\nSeeds: {seeds}")
    print(f"Warm-up: {args.warmup} days")
    print("Note: CIs will be zero if config uses deterministic demand "
          "and lead times — switch to Poisson/normal_int generators for "
          "meaningful variance across seeds.\n")

    for lbl, cfg in configs.items():
        print(f"\nRunning '{lbl}' across {args.seeds} seeds...")
        df   = run_multi_seed(cfg, seeds, label=lbl, warmup_periods=args.warmup)
        summ = summarise(df, lbl)
        print_summary(summ)
        all_summaries.append(summ)
        raw_dfs[lbl] = df

    if args.compare and len(all_summaries) == 2:
        _print_comparison(all_summaries[0], all_summaries[1])

    if args.outdir:
        out = Path(args.outdir)
        out.mkdir(parents=True, exist_ok=True)
        for lbl, df in raw_dfs.items():
            df.to_csv(out / f"raw_{lbl}.csv", index=False)
        pd.concat(all_summaries).to_csv(out / "ci_summary.csv", index=False)
        print(f"\nResults saved to: {out}")


def _print_comparison(s1: pd.DataFrame, s2: pd.DataFrame):
    """Print a side-by-side comparison with statistical significance note."""
    print(f"\n{'='*62}")
    print(f"  Comparison: {s1['label'].iloc[0]} vs {s2['label'].iloc[0]}")
    print(f"{'='*62}")
    for m in s1["metric"].unique():
        r1 = s1[s1["metric"] == m].iloc[0]
        r2 = s2[s2["metric"] == m].iloc[0]
        diff_pct = 100 * (r2["mean"] - r1["mean"]) / r1["mean"] if r1["mean"] != 0 else 0
        # CIs overlap check (conservative significance test)
        overlap = r1["ci_lo"] <= r2["ci_hi"] and r2["ci_lo"] <= r1["ci_hi"]
        sig = "" if overlap else "  *"
        print(f"  {m:<18}  {r1['mean']:>12,.1f}  vs  {r2['mean']:>12,.1f}"
              f"  ({diff_pct:+.1f}%){sig}")
    print(f"\n  * = 95% CIs do not overlap (statistically significant)")


if __name__ == "__main__":
    main()
