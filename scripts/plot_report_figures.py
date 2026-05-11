#!/usr/bin/env python3
"""
Generate report figures from the canonical experiment run.
Saves PNGs to REPORT/images/.
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

EXPDIR = "outputs/experiments_20260506_212928"
OUTDIR = "REPORT/images"
os.makedirs(OUTDIR, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2", "#937860"]
cost_fmt = mticker.FuncFormatter(lambda v, _: f"${v:.0f}k")


# ── helpers ──────────────────────────────────────────────────────────────────

def read_summary():
    return pd.read_csv(os.path.join(EXPDIR, "summary_table.csv"))

def parse_cost(s):
    return float(str(s).replace(",", ""))

def label_bars(ax, bars, values, fmt="{:.0f}k", prefix="$", offset=0):
    for bar, v in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + offset,
            f"{prefix}{fmt.format(v)}",
            ha="center", va="bottom", fontsize=8,
        )


# ── 1. Cost breakdown stacked bar ─────────────────────────────────────────────

def plot_cost_breakdown():
    exps    = ["E0",         "E1a",          "E1b",              "E2",               "E3",        "E3_per_sku"]
    xlabels = ["E0\nBaseline","E1a\nFixed 25%","E1b\nTransport\nonly","E2\nInventory\nonly","E3\nJoint","E3_per_sku\nPer-SKU"]

    cat_keys   = ["holding_cost", "transport_cost", "ordering_cost", "backlog_cost"]
    cat_labels = ["Holding",      "Transport",       "Ordering",      "Shortage"]
    cat_colors = [COLORS[0], COLORS[1], COLORS[2], COLORS[3]]

    rows = {e: {} for e in exps}
    for exp in exps:
        path = os.path.join(EXPDIR, exp, "costs_by_node_sku.csv")
        if not os.path.exists(path):
            print(f"  [skip] {path} not found")
            continue
        df = pd.read_csv(path)
        for k in cat_keys:
            rows[exp][k] = df[k].sum() / 1000  # in $k

    fig, ax = plt.subplots(figsize=(9, 5))
    x      = np.arange(len(exps))
    bottom = np.zeros(len(exps))

    for k, label, col in zip(cat_keys, cat_labels, cat_colors):
        vals = np.array([rows[e].get(k, 0) for e in exps])
        ax.bar(x, vals, bottom=bottom, label=label, color=col, width=0.6, edgecolor="white", linewidth=0.5)
        bottom += vals

    # total label on top of each bar
    for i, total in enumerate(bottom):
        ax.text(x[i], total + 2, f"${total:.0f}k", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(xlabels, fontsize=8.5)
    ax.set_ylabel("Total cost ($k)")
    ax.set_title("Cost decomposition across experiments")
    ax.yaxis.set_major_formatter(cost_fmt)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
    plt.tight_layout()
    out = os.path.join(OUTDIR, "cost_breakdown.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")


# ── 2. Fill rate bar ──────────────────────────────────────────────────────────

def plot_fill_rate():
    df      = read_summary()
    exps    = ["E0", "E1a", "E1b", "E2", "E3", "E3_per_sku"]
    xlabels = ["E0\nBaseline","E1a\nFixed 25%","E1b\nTransport\nonly",
               "E2\nInventory\nonly","E3\nJoint","E3_per_sku\nPer-SKU"]

    fills = []
    for exp in exps:
        row = df[df["Exp"] == exp]
        fills.append(float(row.iloc[0]["Fill Rate %"]))

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x    = np.arange(len(exps))
    bars = ax.bar(x, fills, color=COLORS[:len(exps)], width=0.6, edgecolor="white", linewidth=0.5)
    ax.axhline(92, color="red", linestyle="--", linewidth=1.2, label="92% target")

    for bar, v in zip(bars, fills):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.5,
                f"{v:.1f}%", ha="center", va="bottom", fontsize=8.5)

    ax.set_xticks(x)
    ax.set_xticklabels(xlabels, fontsize=8.5)
    ax.set_ylabel("Fill rate (%)")
    ax.set_ylim(60, 108)
    ax.set_title("Fill rate across experiments")
    ax.legend(fontsize=9)
    plt.tight_layout()
    out = os.path.join(OUTDIR, "fill_rate.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")


# ── 3. Pareto frontier (E4) ───────────────────────────────────────────────────

def plot_pareto():
    # try NSGA-II output first, fall back to constraint-sweep legacy file
    nsga2_path  = os.path.join(EXPDIR, "E4_pareto", "nsga2_frontier.csv")
    sweep_path  = os.path.join(EXPDIR, "E4_pareto", "sweep_frontier.csv")
    legacy_path = os.path.join(EXPDIR, "E4_pareto", "pareto_frontier.csv")

    fig, ax = plt.subplots(figsize=(7, 5))

    plotted_something = False

    if os.path.exists(nsga2_path):
        ns = pd.read_csv(nsga2_path)
        ns_sorted = ns.sort_values("fill_rate")
        ax.plot(ns_sorted["fill_rate"], ns_sorted["total_cost"] / 1000,
                color=COLORS[0], linewidth=1.5, alpha=0.6)
        ax.scatter(ns_sorted["fill_rate"], ns_sorted["total_cost"] / 1000,
                   color=COLORS[0], s=40, zorder=5, label="NSGA-II frontier")
        plotted_something = True

    if os.path.exists(sweep_path):
        sw = pd.read_csv(sweep_path)
        sw_sorted = sw.sort_values("achieved_fill_pct")
        ax.scatter(sw_sorted["achieved_fill_pct"], sw_sorted["total_cost"] / 1000,
                   color=COLORS[1], s=60, marker="D", zorder=5, label="Constraint sweep")
        plotted_something = True

    if not plotted_something and os.path.exists(legacy_path):
        leg = pd.read_csv(legacy_path)
        leg_sorted = leg.sort_values("achieved_fill_pct")
        ax.scatter(leg_sorted["achieved_fill_pct"], leg_sorted["total_cost"] / 1000,
                   color=COLORS[1], s=60, marker="D", zorder=5, label="Constraint sweep")
        ax.plot(leg_sorted["achieved_fill_pct"], leg_sorted["total_cost"] / 1000,
                color=COLORS[1], linewidth=1, alpha=0.5)

    # Mark E3 operating point
    ax.scatter([98.72], [261.248], marker="*", s=250, color=COLORS[3],
               zorder=6, label="E3 joint optimum")

    ax.set_xlabel("Achieved fill rate (%)")
    ax.set_ylabel("Total cost ($k)")
    ax.set_title("E4 — Cost–service Pareto frontier")
    ax.yaxis.set_major_formatter(cost_fmt)
    ax.legend(fontsize=9)
    plt.tight_layout()
    out = os.path.join(OUTDIR, "pareto_frontier.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")


# ── 4. E5 Disruption robustness ───────────────────────────────────────────────

def plot_e5_disruption():
    df = read_summary()

    def get(exp_val, desc_substr=None):
        rows = df[df["Exp"] == exp_val]
        if desc_substr:
            rows = rows[rows["Description"].str.contains(desc_substr, case=False)]
        r = rows.iloc[0]
        return parse_cost(r["Total Cost"]), float(r["Fill Rate %"])

    e0_cost,    e0_fill    = get("E0")
    e3_cost,    e3_fill    = get("E3")
    e5e0_cost,  e5e0_fill  = get("E5", "E0")
    e5e3_cost,  e5e3_fill  = get("E5", "E3")

    xlabels = ["E0\nNo disruption", "E3\nNo disruption",
               "E5: E0 params\nW1 outage", "E5: E3 params\nW1 outage"]
    costs = [e0_cost/1000, e3_cost/1000, e5e0_cost/1000, e5e3_cost/1000]
    fills = [e0_fill,      e3_fill,      e5e0_fill,       e5e3_fill]
    colors = [COLORS[0], COLORS[1], COLORS[2], COLORS[3]]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

    bars1 = ax1.bar(range(4), costs, color=colors, width=0.6, edgecolor="white", linewidth=0.5)
    ax1.set_xticks(range(4))
    ax1.set_xticklabels(xlabels, fontsize=8)
    ax1.set_ylabel("Total cost ($k)")
    ax1.set_title("Total cost")
    ax1.yaxis.set_major_formatter(cost_fmt)
    for bar, v in zip(bars1, costs):
        ax1.text(bar.get_x() + bar.get_width()/2, v + 15, f"${v:.0f}k",
                 ha="center", va="bottom", fontsize=7.5)

    bars2 = ax2.bar(range(4), fills, color=colors, width=0.6, edgecolor="white", linewidth=0.5)
    ax2.axhline(92, color="red", linestyle="--", linewidth=1.2, label="92% target")
    ax2.set_xticks(range(4))
    ax2.set_xticklabels(xlabels, fontsize=8)
    ax2.set_ylabel("Fill rate (%)")
    ax2.set_title("Fill rate")
    ax2.set_ylim(60, 108)
    ax2.legend(fontsize=8)
    for bar, v in zip(bars2, fills):
        ax2.text(bar.get_x() + bar.get_width()/2, v + 0.5, f"{v:.1f}%",
                 ha="center", va="bottom", fontsize=7.5)

    fig.suptitle("E5 — Disruption robustness: 14-day W1 outage", fontsize=11)
    plt.tight_layout()
    out = os.path.join(OUTDIR, "e5_disruption.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")


# ── 5. E6 Policy comparison ───────────────────────────────────────────────────

def plot_e6_policy():
    df = read_summary()
    e6 = df[df["Exp"] == "E6"].copy()

    policy_map = {
        "base_stock":      "Base-stock",
        "ss":              "$(s,S)$",
        "periodic_review": "Periodic\nreview",
        "echelon_stock":   "Echelon\nbase-stock",
    }

    costs, fills, xlabels = [], [], []
    for key, label in policy_map.items():
        row = e6[e6["Description"].str.contains(key, case=False)]
        if row.empty:
            continue
        costs.append(parse_cost(row.iloc[0]["Total Cost"]) / 1000)
        fills.append(float(row.iloc[0]["Fill Rate %"]))
        xlabels.append(label)

    # Add E3 as reference
    e3 = df[df["Exp"] == "E3"].iloc[0]
    costs.append(parse_cost(e3["Total Cost"]) / 1000)
    fills.append(float(e3["Fill Rate %"]))
    xlabels.append("E3\nJoint opt")

    colors = COLORS[:len(costs)]
    x = np.arange(len(costs))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

    bars1 = ax1.bar(x, costs, color=colors, width=0.6, edgecolor="white", linewidth=0.5)
    ax1.set_xticks(x)
    ax1.set_xticklabels(xlabels, fontsize=8.5)
    ax1.set_ylabel("Total cost ($k)")
    ax1.set_title("Total cost by policy")
    ax1.yaxis.set_major_formatter(cost_fmt)
    for bar, v in zip(bars1, costs):
        ax1.text(bar.get_x() + bar.get_width()/2, v + 3, f"${v:.0f}k",
                 ha="center", va="bottom", fontsize=8)

    bars2 = ax2.bar(x, fills, color=colors, width=0.6, edgecolor="white", linewidth=0.5)
    ax2.axhline(92, color="red", linestyle="--", linewidth=1.2, label="92% target")
    ax2.set_xticks(x)
    ax2.set_xticklabels(xlabels, fontsize=8.5)
    ax2.set_ylabel("Fill rate (%)")
    ax2.set_title("Fill rate by policy")
    ax2.set_ylim(60, 108)
    ax2.legend(fontsize=9)
    for bar, v in zip(bars2, fills):
        ax2.text(bar.get_x() + bar.get_width()/2, v + 0.5, f"{v:.1f}%",
                 ha="center", va="bottom", fontsize=8)

    fig.suptitle("E6 — Policy comparison (each individually optimised)", fontsize=11)
    plt.tight_layout()
    out = os.path.join(OUTDIR, "e6_policy.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")


# ── 6. E7 Forecast sensitivity ────────────────────────────────────────────────

def plot_e7_forecast():
    df = pd.read_csv(os.path.join(EXPDIR, "E7_forecast_sweep.csv"))

    fig, ax1 = plt.subplots(figsize=(7, 4.5))
    ax2 = ax1.twinx()
    ax2.spines["right"].set_visible(True)

    l1, = ax1.plot(df["sigma_pct"], df["total_cost"] / 1000,
                   color=COLORS[0], marker="o", linewidth=2, label="Total cost")
    l2, = ax2.plot(df["sigma_pct"], df["fill_rate"],
                   color=COLORS[1], marker="s", linewidth=2, linestyle="--", label="Fill rate")
    ax2.axhline(92, color="red", linestyle=":", linewidth=1.2, label="92% target")

    ax1.set_xlabel("Forecast error $\\sigma_f$ (%)")
    ax1.set_ylabel("Total cost ($k)", color=COLORS[0])
    ax1.tick_params(axis="y", labelcolor=COLORS[0])
    ax2.set_ylabel("Fill rate (%)", color=COLORS[1])
    ax2.tick_params(axis="y", labelcolor=COLORS[1])
    ax1.set_title("E7 — Sensitivity to forecast error")
    ax1.yaxis.set_major_formatter(cost_fmt)

    lines  = [l1, l2]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper left", fontsize=9)
    plt.tight_layout()
    out = os.path.join(OUTDIR, "e7_forecast.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")


# ── 7. E8 Bullwhip lambda sweep ───────────────────────────────────────────────

def plot_e8_bullwhip():
    df = pd.read_csv(os.path.join(EXPDIR, "E8_lambda_sweep.csv"))

    x_pos    = np.arange(len(df))
    x_labels = ["0", "1k", "10k", "100k", "1M"]

    fig, ax1 = plt.subplots(figsize=(7, 4.5))
    ax2 = ax1.twinx()
    ax2.spines["right"].set_visible(True)

    l1, = ax1.plot(x_pos, df["total_cost"] / 1000,
                   color=COLORS[0], marker="o", linewidth=2, label="Total cost")
    l2, = ax2.plot(x_pos, df["fill_rate"],
                   color=COLORS[1], marker="s", linewidth=2, linestyle="--", label="Fill rate")
    ax2.axhline(92, color="red", linestyle=":", linewidth=1.2, label="92% target")

    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(x_labels)
    ax1.set_xlabel("Bullwhip penalty $\\lambda$")
    ax1.set_ylabel("Total cost ($k)", color=COLORS[0])
    ax1.tick_params(axis="y", labelcolor=COLORS[0])
    ax2.set_ylabel("Fill rate (%)", color=COLORS[1])
    ax2.tick_params(axis="y", labelcolor=COLORS[1])
    ax1.set_title("E8 — Bullwhip-aware optimisation ($\\lambda$ sweep)")
    ax1.yaxis.set_major_formatter(cost_fmt)

    lines  = [l1, l2]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="upper right", fontsize=9)
    plt.tight_layout()
    out = os.path.join(OUTDIR, "e8_bullwhip.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Reading from : {EXPDIR}")
    print(f"Saving  to   : {OUTDIR}\n")

    plot_cost_breakdown()
    plot_fill_rate()
    plot_pareto()
    plot_e5_disruption()
    plot_e6_policy()
    plot_e7_forecast()
    plot_e8_bullwhip()

    print("\nDone.")
