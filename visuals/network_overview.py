import os
import pandas as pd
import matplotlib.pyplot as plt

def network_overview(csv_path="outputs/opt_results.csv",
                     out_path="visuals/network_overview.png",
                     metric="ip",          # "ip" or "on_hand"
                     show_backlog=True):   # shade backlog near zero
    """
    Make ONE combined chart for the entire network.
    - metric: "ip" (Inventory Position) or "on_hand"
    - backlog is shaded light per node to spot issues
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Metrics CSV not found: {csv_path}")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    df = pd.read_csv(csv_path)
    # Derived columns
    df["backlog_total"] = df["backlog_external"].fillna(0) + df["backlog_children"].fillna(0)
    df["ip"] = df["on_hand"] - df["backlog_total"] + df["pipeline_in"]

    # Choose y-series
    if metric not in ("ip", "on_hand"):
        raise ValueError("metric must be 'ip' or 'on_hand'")
    ycol = metric

    # One figure for all nodes
    plt.figure(figsize=(11, 5))
    nodes = list(df["node_id"].unique())

    for node in nodes:
        sub = df[df.node_id == node].copy()
        t = sub["t"].values
        y = sub[ycol].values
        plt.plot(t, y, marker="o", linewidth=1.8, label=f"{node} {ycol.upper()}")

        if show_backlog and sub["backlog_total"].max() > 0:
            try:
                plt.fill_between(t, 0, sub["backlog_total"].values,
                                 alpha=0.12, step="mid", label=f"{node} backlog")
            except TypeError:
                plt.fill_between(t, 0, sub["backlog_total"].values,
                                 alpha=0.12, label=f"{node} backlog")

    title_metric = "Inventory Position (IP)" if metric == "ip" else "On‑hand"
    plt.title(f"Network Overview — {title_metric} per Node")
    plt.xlabel("Period (t)")
    plt.ylabel("Quantity")
    plt.axhline(0, linewidth=0.8)

    # Keep legend readable: place outside if many nodes
    plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0., fontsize=9)
    plt.tight_layout(rect=[0,0,0.82,1])  # make space for legend
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved: {os.path.abspath(out_path)}")

if __name__ == "__main__":
    # Default: IP with backlog shading
    network_overview()
