import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


POLICY_RUNS = {
    "Base-stock": "synthetic_validation_3_base_stock/inventory_log.csv",
    "(s, S)": "synthetic_validation_3_ss/inventory_log.csv",
    #"Order-up-to": "synthetic_validation_order_upto/inventory_log.csv",
}

OUTPUT_DIR = Path("poster_plots")
OUTPUT_DIR.mkdir(exist_ok=True)


def load_warehouse_onhand(csv_path):
    df = pd.read_csv(csv_path)
    w1 = df[df["node_id"] == "W1"].sort_values("time")
    return w1["time"], w1["on_hand"]


def plot_policy_comparison():
    plt.figure(figsize=(8, 4))

    for label, path in POLICY_RUNS.items():
        time, on_hand = load_warehouse_onhand(path)
        plt.plot(time, on_hand, label=label, linewidth=2)

    plt.xlabel("Time (days)")
    plt.ylabel("Warehouse On-hand Inventory")
    plt.title("Warehouse inventory dynamics under different policies with transport constraints")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    out_path = OUTPUT_DIR / "warehouse_policy_comparison.png"
    plt.savefig(out_path, dpi=300)
    plt.close()

    print(f"Saved plot to {out_path}")


if __name__ == "__main__":
    plot_policy_comparison()
