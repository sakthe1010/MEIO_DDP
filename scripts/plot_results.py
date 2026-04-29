"""
scripts/plot_results.py
=======================
Matplotlib visualizations for DDP experiment outputs.

Generates report-ready figures from the CSVs saved by run_experiments.py.

Usage
-----
  # Plot everything from an experiment run
  python scripts/plot_results.py --expdir outputs/experiments_<timestamp>/

  # Plot only specific charts
  python scripts/plot_results.py --expdir outputs/experiments_<ts>/ --plots cost_breakdown pareto

Available plots
---------------
  cost_breakdown   — stacked bar: cost split per experiment
  fill_rate        — grouped bar: fill rate per experiment
  inventory_ts     — inventory time series for each node/SKU
  orders_ts        — order quantities over time (shows bullwhip visually)
  bullwhip         — bar chart of bullwhip ratios across nodes
  pareto           — scatter: cost vs fill rate Pareto frontier
  all              — all of the above (default)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

import matplotlib
matplotlib.use("Agg")   # non-interactive backend — works in headless environments
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPERIMENT_ORDER = ["E0", "E1a", "E1b", "E2", "E3"]
COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", "#937860"]

# Consistent rcParams for report-quality figures
plt.rcParams.update({
    "font.family":      "sans-serif",
    "font.size":        10,
    "axes.titlesize":   11,
    "axes.labelsize":   10,
    "legend.fontsize":  9,
    "xtick.labelsize":  9,
    "ytick.labelsize":  9,
    "axes.spines.top":  False,
    "axes.spines.right": False,
    "axes.grid":        True,
    "grid.alpha":       0.3,
    "grid.linestyle":   "--",
})

# Figure counter — incremented per saved figure so reports can reference "Figure N"
_fig_counter = 0


def _next_fig_num() -> int:
    global _fig_counter
    _fig_counter += 1
    return _fig_counter


# ============================================================
# Helpers
# ============================================================

def _load_summary(expdir: Path) -> pd.DataFrame:
    p = expdir / "summary_table.csv"
    if not p.exists():
        raise FileNotFoundError(f"summary_table.csv not found in {expdir}")
    return pd.read_csv(p)


def _exp_dirs(expdir: Path) -> List[Path]:
    return sorted(
        [d for d in expdir.iterdir() if d.is_dir() and d.name in EXPERIMENT_ORDER],
        key=lambda d: EXPERIMENT_ORDER.index(d.name)
    )


def _savefig(fig, path: Path, caption: str = "", fig_num: int = None, dpi: int = 150):
    """Tight-layout, add figure-number label + caption, save and close."""
    fig.tight_layout()

    if fig_num is not None:
        # Small "Figure N" label in the bottom-left corner below the axes
        fig.text(
            0.01, 0.005,
            f"Figure {fig_num}.",
            ha="left", va="bottom",
            fontsize=8, color="#555555", style="italic",
            transform=fig.transFigure,
        )

    if caption:
        fig.text(
            0.5, -0.02,
            caption,
            ha="center", va="top",
            fontsize=8.5, color="#333333",
            wrap=True,
            transform=fig.transFigure,
        )

    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path.name}")


def _annotate_bar_values(ax, bars, fmt="{:.0f}", offset=0.5, fontsize=8):
    """Annotate each bar with its height value."""
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + offset,
                fmt.format(h),
                ha="center", va="bottom", fontsize=fontsize, color="#222222",
            )


# ============================================================
# 1. Cost breakdown stacked bar
# ============================================================

def plot_cost_breakdown(expdir: Path, out: Path):
    summary = _load_summary(expdir)
    labels   = summary["Experiment"].tolist()

    exp_dirs = {d.name: d for d in _exp_dirs(expdir)}
    categories = ["holding_cost", "transport_cost", "ordering_cost", "backlog_cost"]
    cat_labels  = ["Holding", "Transport", "Ordering", "Shortage"]
    cat_colors  = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]

    bottoms = np.zeros(len(labels))
    fig, ax = plt.subplots(figsize=(10, 5))

    totals = np.zeros(len(labels))
    for cat, label, color in zip(categories, cat_labels, cat_colors):
        vals = []
        for exp_name in [l.split(" ")[0] for l in labels]:
            d = exp_dirs.get(exp_name)
            if d and (d / "costs_by_node_sku.csv").exists():
                df = pd.read_csv(d / "costs_by_node_sku.csv")
                vals.append(df[cat].sum() if cat in df else 0)
            else:
                vals.append(0)
        vals = np.array(vals)
        ax.bar(labels, vals, bottom=bottoms, label=label, color=color, edgecolor="white", linewidth=0.5)
        bottoms += vals
        totals  += vals

    # Annotate total cost above each bar
    for i, (lbl, tot) in enumerate(zip(labels, totals)):
        if tot > 0:
            ax.text(i, tot + tot * 0.01, f"{tot:,.0f}",
                    ha="center", va="bottom", fontsize=8, fontweight="bold", color="#111111")

    ax.set_ylabel("Total Cost (supply-chain currency units)")
    ax.set_title("Cost Breakdown by Experiment")
    ax.legend(loc="upper right", framealpha=0.9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    plt.xticks(rotation=15, ha="right")

    _savefig(
        fig, out / "cost_breakdown.png",
        caption=(
            "Stacked bar chart of total supply-chain cost split into holding, transport, "
            "ordering, and shortage components for each experiment configuration."
        ),
        fig_num=_next_fig_num(),
    )


# ============================================================
# 2. Fill rate grouped bar
# ============================================================

def plot_fill_rate(expdir: Path, out: Path):
    summary = _load_summary(expdir)
    labels = summary["Experiment"].tolist()
    rates  = summary["Fill Rate %"].astype(float).tolist()

    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(labels, rates, color=COLORS[:len(labels)], edgecolor="white", linewidth=0.5)

    ax.axhline(92, color="red", linestyle="--", linewidth=1.2, label="92% service target", zorder=3)
    ax.set_ylabel("Fill Rate (%)")
    ax.set_title("Fill Rate by Experiment")
    ax.set_ylim(0, 108)
    ax.legend(framealpha=0.9)

    for bar, rate in zip(bars, rates):
        color = "#B22222" if rate < 92 else "#1a6b1a"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.8,
            f"{rate:.1f}%",
            ha="center", va="bottom", fontsize=9, fontweight="bold", color=color,
        )

    plt.xticks(rotation=15, ha="right")

    _savefig(
        fig, out / "fill_rate.png",
        caption=(
            "Fill rate (demand satisfied without backlog) achieved per experiment. "
            "Red dashed line marks the 92% service-level target. "
            "Values in red are below target; green are above."
        ),
        fig_num=_next_fig_num(),
    )


# ============================================================
# 3. Inventory time series
# ============================================================

def plot_inventory_ts(expdir: Path, out: Path, max_skus: int = 3):
    exp_dirs = _exp_dirs(expdir)
    if not exp_dirs:
        return

    exp_dir = exp_dirs[0]   # baseline (E0) by default
    inv_path = exp_dir / "inventory_log.csv"
    if not inv_path.exists():
        return

    df = pd.read_csv(inv_path)
    nodes = df["node_id"].unique()
    skus  = df["sku"].unique()[:max_skus]

    fig, axes = plt.subplots(
        len(nodes), len(skus),
        figsize=(5 * len(skus), 3 * len(nodes)),
        squeeze=False,
    )

    for r, nid in enumerate(nodes):
        for c, sku in enumerate(skus):
            ax = axes[r][c]
            sub = df[(df["node_id"] == nid) & (df["sku"] == sku)]
            ax.plot(sub["t"], sub["on_hand"],     label="On-hand",  linewidth=1.0, color="#4C72B0")
            ax.plot(sub["t"], sub["pipeline_in"], label="Pipeline", linewidth=1.0,
                    linestyle="--", color="#DD8452")
            if sub["backlog_external"].sum() > 0:
                ax.plot(sub["t"], sub["backlog_external"],
                        label="Backlog", linewidth=1.0, color="#C44E52")
            ax.set_title(f"{nid} / {sku}", fontsize=9)
            ax.set_xlabel("Day")
            if c == 0:
                ax.set_ylabel("Units")
            if r == 0 and c == len(skus) - 1:
                ax.legend(fontsize=7, loc="upper right", framealpha=0.8)

    fig.suptitle(f"Inventory Time Series — {exp_dir.name} (Baseline)", fontsize=11, y=1.01)

    _savefig(
        fig, out / "inventory_ts.png",
        caption=(
            f"On-hand inventory, inbound pipeline stock, and external backlog "
            f"over the simulation horizon for experiment {exp_dir.name}. "
            "Each sub-panel shows one node–SKU pair."
        ),
        fig_num=_next_fig_num(),
    )


# ============================================================
# 4. Orders time series (bullwhip visual)
# ============================================================

def plot_orders_ts(expdir: Path, out: Path, sku: str = None):
    exp_dirs_map = {d.name: d for d in _exp_dirs(expdir)}

    for exp_name in ["E0", "E3"]:
        d = exp_dirs_map.get(exp_name)
        if not d or not (d / "orders_log.csv").exists():
            continue

        df = pd.read_csv(d / "orders_log.csv")
        plot_sku = sku if sku else df["sku"].unique()[0]
        df = df[df["sku"] == plot_sku]

        nodes = df["node_id"].unique()
        fig, axes = plt.subplots(len(nodes), 1, figsize=(12, 2.5 * len(nodes)), squeeze=False)

        for r, nid in enumerate(nodes):
            ax = axes[r][0]
            sub = df[df["node_id"] == nid]
            qty = sub["orders_to_parent"]
            ax.plot(sub["t"], qty, linewidth=0.8, color="#4C72B0")
            ax.axhline(qty.mean(), color="#C44E52", linestyle=":", linewidth=1.0,
                       label=f"Mean = {qty.mean():.1f}")
            cv2 = (qty.std() / qty.mean()) ** 2 if qty.mean() > 0 else 0
            ax.set_title(f"{nid} — orders to parent ({plot_sku})   CV² = {cv2:.3f}", fontsize=9)
            ax.set_xlabel("Day")
            ax.set_ylabel("Order qty")
            ax.legend(fontsize=7, framealpha=0.8)

        fig.suptitle(f"Order Quantities — {exp_name} / {plot_sku}", fontsize=11)

        _savefig(
            fig, out / f"orders_ts_{exp_name}_{plot_sku}.png",
            caption=(
                f"Orders placed to upstream node per period for each echelon ({exp_name}, SKU {plot_sku}). "
                "CV² annotated per panel: higher CV² upstream than downstream indicates the bullwhip effect."
            ),
            fig_num=_next_fig_num(),
        )


# ============================================================
# 5. Bullwhip ratio bar chart
# ============================================================

def plot_bullwhip(expdir: Path, out: Path):
    exp_dirs = _exp_dirs(expdir)
    all_frames = []

    for d in exp_dirs:
        p = d / "bullwhip.csv"
        if p.exists():
            df = pd.read_csv(p)
            df["experiment"] = d.name
            all_frames.append(df)

    if not all_frames:
        print("  No bullwhip.csv found — skipping bullwhip chart.")
        return

    combined = pd.concat(all_frames, ignore_index=True)
    combined = combined.dropna(subset=["bullwhip_ratio"])
    skus = combined["sku"].unique()

    fig, axes = plt.subplots(1, len(skus), figsize=(4 * len(skus), 5), squeeze=False)

    for c, sku in enumerate(skus):
        ax = axes[0][c]
        sub = combined[combined["sku"] == sku].copy()
        x_labels = [f"{e}/{n}" for e, n in zip(sub["experiment"], sub["node_id"])]
        bars = ax.bar(x_labels, sub["bullwhip_ratio"],
                      color=[COLORS[i % len(COLORS)] for i in range(len(sub))],
                      edgecolor="white", linewidth=0.5)
        ax.axhline(1.0, color="red", linestyle="--", linewidth=1.2,
                   label="BWE = 1 (no amplification)", zorder=3)

        # Annotate each bar with its ratio value
        for bar, ratio in zip(bars, sub["bullwhip_ratio"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.03,
                f"{ratio:.2f}",
                ha="center", va="bottom", fontsize=7,
            )

        ax.set_title(f"Bullwhip Effect — {sku}", fontsize=9)
        ax.set_ylabel("Order CV² / Demand CV²")
        ax.legend(fontsize=7, framealpha=0.8)
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=7)

    fig.suptitle("Bullwhip Effect Ratio by Experiment, Node and SKU", fontsize=11)

    _savefig(
        fig, out / "bullwhip.png",
        caption=(
            "Bullwhip Effect Ratio (BWE) = order variance coefficient of variation squared "
            "divided by demand CV². BWE > 1 indicates demand variability amplification moving "
            "upstream. Values flagged with ⚠ exceed 2× amplification."
        ),
        fig_num=_next_fig_num(),
    )


# ============================================================
# 6. Pareto frontier
# ============================================================

def _pareto_efficient(df: pd.DataFrame) -> pd.DataFrame:
    """Return non-dominated rows (maximize fill rate, minimize cost)."""
    pts = df[["achieved_fill_pct", "total_cost"]].values
    n = len(pts)
    dominated = np.zeros(n, dtype=bool)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            # j dominates i if j has >= fill rate AND <= cost (at least one strict)
            if (pts[j, 0] >= pts[i, 0] and pts[j, 1] <= pts[i, 1] and
                    (pts[j, 0] > pts[i, 0] or pts[j, 1] < pts[i, 1])):
                dominated[i] = True
                break
    return df[~dominated].sort_values("achieved_fill_pct").reset_index(drop=True)


def plot_pareto(expdir: Path, out: Path):
    pareto_path = expdir / "E4_pareto" / "pareto_frontier.csv"
    if not pareto_path.exists():
        print("  No E4_pareto/pareto_frontier.csv found — skipping Pareto chart.")
        return

    df = pd.read_csv(pareto_path)
    frontier = _pareto_efficient(df)

    fig, ax = plt.subplots(figsize=(9, 5))

    # All optimizer runs as background scatter
    ax.scatter(
        df["achieved_fill_pct"], df["total_cost"] / 1e6,
        marker="o", s=40, color="#aac4e8", zorder=2, label="All optimizer runs",
        alpha=0.7,
    )

    # True Pareto front connected by a line
    ax.plot(
        frontier["achieved_fill_pct"], frontier["total_cost"] / 1e6,
        marker="o", linewidth=2, markersize=8,
        color="#4C72B0", zorder=3, label="Pareto frontier",
    )

    # Annotate frontier points
    for _, row in frontier.iterrows():
        ax.annotate(
            f"target {row['target_fill_pct']:.0f}%\n"
            f"cost {row['total_cost']/1e6:.2f}M",
            xy=(row["achieved_fill_pct"], row["total_cost"] / 1e6),
            xytext=(8, 6), textcoords="offset points",
            fontsize=7.5, color="#222222",
            arrowprops=dict(arrowstyle="-", color="#888888", lw=0.6),
        )

    # Mark the 92% service target line
    ax.axvline(92, color="red", linestyle="--", linewidth=1.2,
               label="92% service target", zorder=3)

    ax.set_xlabel("Achieved Fill Rate (%)")
    ax.set_ylabel("Total Cost (millions)")
    ax.set_title("Pareto Frontier: Cost vs Fill Rate (Joint Optimization — E4)")
    ax.legend(framealpha=0.9)

    _savefig(
        fig, out / "pareto_frontier.png",
        caption=(
            "Pareto frontier (blue line) showing non-dominated solutions from joint inventory "
            "and transport optimisation (E4). Grey dots are all optimizer runs; "
            "connected blue points are Pareto-efficient — no other solution achieves "
            "both higher fill rate and lower cost simultaneously. "
            "Red dashed line marks the 92% minimum service-level requirement."
        ),
        fig_num=_next_fig_num(),
    )


# ============================================================
# CLI
# ============================================================

PLOT_FUNCTIONS = {
    "cost_breakdown": plot_cost_breakdown,
    "fill_rate":      plot_fill_rate,
    "inventory_ts":   plot_inventory_ts,
    "orders_ts":      plot_orders_ts,
    "bullwhip":       plot_bullwhip,
    "pareto":         plot_pareto,
}


def main():
    ap = argparse.ArgumentParser(description="Generate DDP result plots.")
    ap.add_argument("--expdir", required=True,
                    help="Path to an experiments_<timestamp>/ directory")
    ap.add_argument("--plots", nargs="+",
                    default=["all"],
                    choices=list(PLOT_FUNCTIONS.keys()) + ["all"],
                    help="Which plots to generate (default: all)")
    ap.add_argument("--outdir", default=None,
                    help="Where to save PNGs (default: <expdir>/plots/)")
    args = ap.parse_args()

    expdir = Path(args.expdir)
    out    = Path(args.outdir) if args.outdir else expdir / "plots"
    out.mkdir(parents=True, exist_ok=True)

    to_plot = list(PLOT_FUNCTIONS.keys()) if "all" in args.plots else args.plots

    print(f"Generating {len(to_plot)} plot(s) → {out}")
    for name in to_plot:
        try:
            PLOT_FUNCTIONS[name](expdir, out)
        except Exception as e:
            print(f"  [WARN] {name} failed: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
