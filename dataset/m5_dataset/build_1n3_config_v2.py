"""
build_1n3_config_v3.py
----------------------
Builds a two-SKU config for the 1-supplier / 2-warehouse / 3-retailer network.

SKU_A : FOODS_3_586  (fast mover  ~48 units/day, strong seasonality)
SKU_B : FOODS_3_714  (slow mover  ~21 units/day, milder yearly pattern)

Each SKU has its own:
  - retailer demand CSVs  (aggregated from per-store series)
  - base-stock levels     (computed independently per SKU per node)
  - physical dimensions   (volume_per_unit, weight_per_unit)
  - cost parameters       (holding, shortage)

Usage:
    python build_1n3_config_v3.py
    python build_1n3_config_v3.py --out_config config/1n3_2sku.json
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


# ---------------------------------------------------------------------------
# Column autodetect (unchanged from v2)
# ---------------------------------------------------------------------------
DATE_CANDIDATES = ["date", "Date", "ds", "d", "timestamp", "time"]
QTY_CANDIDATES  = ["quantity", "qty", "demand", "sales", "value", "y", "units", "qty_sold"]


def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur] + list(cur.parents):
        if (p / "engine").exists() and (
            (p / "config").exists() or (p / "dataset").exists()
        ):
            return p
    return cur


def detect_cols(df: pd.DataFrame) -> Tuple[str, str]:
    date_col = next((c for c in DATE_CANDIDATES if c in df.columns), None)
    if date_col is None:
        date_col = next(
            (c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])),
            None,
        )
    if date_col is None:
        date_col = "date"
        df[date_col] = pd.RangeIndex(len(df))

    qty_col = next((c for c in QTY_CANDIDATES if c in df.columns), None)
    if qty_col is None:
        num_cols = [
            c for c in df.columns
            if c != date_col and pd.api.types.is_numeric_dtype(df[c])
        ]
        if not num_cols:
            raise ValueError(f"No quantity column found in {list(df.columns)}")
        qty_col = num_cols[0]

    return date_col, qty_col


def read_series(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    dcol, qcol = detect_cols(df)
    try:
        df[dcol] = pd.to_datetime(df[dcol])
        df = df.sort_values(dcol)
    except Exception:
        pass
    out = pd.DataFrame({
        "date": df[dcol],
        "quantity": df[qcol].fillna(0).clip(lower=0).round().astype(int),
    })
    return out[["date", "quantity"]]


def aggregate_stores(store_dir: Path, store_ids: List[str]) -> pd.DataFrame:
    """Read per-store CSVs from a directory and sum them into one series."""
    series_list = []
    for sid in store_ids:
        p = store_dir / f"{sid}.csv"
        if not p.exists():
            raise FileNotFoundError(f"Store CSV not found: {p}")
        s = read_series(p).set_index("date").rename(columns={"quantity": sid})
        series_list.append(s)
    joined = pd.concat(series_list, axis=1, join="outer").fillna(0)
    agg = joined.sum(axis=1).astype(int).reset_index()
    agg.columns = ["date", "quantity"]
    return agg


def base_stock_S(series: pd.Series, L: int, z: float = 1.64) -> Tuple[int, float, float]:
    """S = mu*(L+1) + z*sigma*sqrt(L+1)  — review period = 1 day."""
    mu = float(series.mean())
    sd = float(series.std(ddof=1))
    PT = L + 1
    S = mu * PT + z * sd * (PT ** 0.5)
    return int(math.ceil(S)), mu, sd


# ---------------------------------------------------------------------------
# SKU physical & cost properties
# Realistic values for grocery retail:
#   SKU_A (FOODS_3_586): small food item, e.g. canned goods  — dense, light
#   SKU_B (FOODS_3_714): bulkier food item, e.g. cereal box  — less dense, lighter per unit
# ---------------------------------------------------------------------------
SKU_PROPERTIES = {
    "SKU_A": {
        "volume_per_unit": 0.002,   # m³  (e.g. ~2-litre can)
        "weight_per_unit": 0.8,     # kg
        "holding_cost_retailer":  0.04,
        "holding_cost_warehouse": 0.02,
        "holding_cost_supplier":  0.01,
        "shortage_cost": 0.60,
        "order_cost_fixed": 15.0,
        "order_cost_per_unit": 0.01,
    },
    "SKU_B": {
        "volume_per_unit": 0.008,   # m³  (e.g. cereal box — 4x bulkier)
        "weight_per_unit": 0.5,     # kg  (lighter per unit)
        "holding_cost_retailer":  0.03,
        "holding_cost_warehouse": 0.015,
        "holding_cost_supplier":  0.008,
        "shortage_cost": 0.40,
        "order_cost_fixed": 15.0,
        "order_cost_per_unit": 0.01,
    },
}

# Store groupings — same 4-3-3 split as v2
RETAILER_GROUPS = {
    "R1": ["CA_1", "CA_2", "WI_1", "TX_1"],
    "R2": ["CA_3", "CA_4", "WI_2"],
    "R3": ["WI_3", "TX_2", "TX_3"],
}

# Lead times
LEAD_TIMES = {
    ("Supplier", "W1"): 5,
    ("Supplier", "W2"): 6,
    ("W1", "R1"): 2,
    ("W1", "R2"): 3,
    ("W2", "R3"): 4,
}

# Transport options per lane — one truck mode for now
# capacity in m³ — a standard 40ft container ~ 67 m³
TRANSPORT_OPTIONS = {
    ("Supplier", "W1"): {"mode": 1, "capacity": 67.0, "cost_full": 800.0,  "cost_half": 480.0, "cost_quarter": 280.0},
    ("Supplier", "W2"): {"mode": 1, "capacity": 67.0, "cost_full": 960.0,  "cost_half": 576.0, "cost_quarter": 336.0},
    ("W1", "R1"):       {"mode": 1, "capacity": 33.0, "cost_full": 300.0,  "cost_half": 180.0, "cost_quarter": 105.0},
    ("W1", "R2"):       {"mode": 1, "capacity": 33.0, "cost_full": 375.0,  "cost_half": 225.0, "cost_quarter": 131.0},
    ("W2", "R3"):       {"mode": 1, "capacity": 33.0, "cost_full": 300.0,  "cost_half": 180.0, "cost_quarter": 105.0},
}


def main(
    sku_a_dir: str = "dataset/m5_dataset/processed",
    sku_b_dir: str = "dataset/m5_dataset/processed/sku_b",
    out_config_path: str = "config/1n3_2sku.json",
    out_csv_dir_a: str = "dataset/m5_dataset/processed/retailers",
    out_csv_dir_b: str = "dataset/m5_dataset/processed/retailers_sku_b",
    z: float = 1.64,
):
    here = Path(__file__).resolve()
    root = find_repo_root(here.parent)
    print(f"[info] repo root : {root}")

    sku_a_store_dir = (root / sku_a_dir).resolve()
    sku_b_store_dir = (root / sku_b_dir).resolve()

    retailer_csv: Dict[str, Dict[str, str]] = {}   # sku -> retailer -> relative path
    retailer_info: Dict[str, Dict[str, dict]] = {}  # sku -> retailer -> {S, mu, sd, T}

    for sku, store_dir, out_csv_dir in [
        ("SKU_A", sku_a_store_dir, root / out_csv_dir_a),
        ("SKU_B", sku_b_store_dir, root / out_csv_dir_b),
    ]:
        out_csv_dir.mkdir(parents=True, exist_ok=True)
        retailer_csv[sku] = {}
        retailer_info[sku] = {}

        print(f"\n[{sku}] aggregating retailer demand...")

        for r_id, stores in RETAILER_GROUPS.items():
            df = aggregate_stores(store_dir, stores)

            out_csv = out_csv_dir / f"{r_id}.csv"
            df.to_csv(out_csv, index=False)
            retailer_csv[sku][r_id] = str(out_csv.relative_to(root))

            L = LEAD_TIMES[("W1" if r_id in ("R1","R2") else "W2", r_id)]
            S, mu, sd = base_stock_S(df["quantity"], L=L, z=z)
            retailer_info[sku][r_id] = {"S": S, "mu": mu, "sd": sd, "T": len(df)}

            print(f"  {r_id}: mu={mu:.1f}  sd={sd:.1f}  S={S}  (L={L})")

    # Time horizon = shortest series across all SKUs and retailers
    T = int(min(
        retailer_info[sku][r]["T"]
        for sku in retailer_info
        for r in retailer_info[sku]
    ))
    print(f"\n[info] time horizon: {T} days")

    # ------------------------------------------------------------------
    # Warehouse base-stock levels — computed per SKU independently
    # ------------------------------------------------------------------
    warehouse_info: Dict[str, Dict[str, dict]] = {}

    for sku in ("SKU_A", "SKU_B"):
        warehouse_info[sku] = {}
        ri = retailer_info[sku]

        # W1 serves R1 + R2
        mu_W1 = ri["R1"]["mu"] + ri["R2"]["mu"]
        sd_W1 = (ri["R1"]["sd"]**2 + ri["R2"]["sd"]**2) ** 0.5
        L_W1  = LEAD_TIMES[("Supplier", "W1")]
        S_W1, _, _ = base_stock_S(
            pd.Series([mu_W1] * T),   # use mu as proxy — S formula only needs mu/sd
            L=L_W1, z=z
        )
        # Recompute properly using formula directly (avoid dummy series)
        PT = L_W1 + 1
        S_W1 = int(math.ceil(mu_W1 * PT + z * sd_W1 * (PT**0.5)))
        warehouse_info[sku]["W1"] = {"S": S_W1, "mu": mu_W1, "sd": sd_W1}

        # W2 serves R3 only
        mu_W2 = ri["R3"]["mu"]
        sd_W2 = ri["R3"]["sd"]
        L_W2  = LEAD_TIMES[("Supplier", "W2")]
        PT = L_W2 + 1
        S_W2 = int(math.ceil(mu_W2 * PT + z * sd_W2 * (PT**0.5)))
        warehouse_info[sku]["W2"] = {"S": S_W2, "mu": mu_W2, "sd": sd_W2}

        print(f"[{sku}] W1: S={S_W1}  W2: S={S_W2}")

    # ------------------------------------------------------------------
    # Build config
    # ------------------------------------------------------------------
    skus = ["SKU_A", "SKU_B"]

    def node_policy(node_id: str) -> dict:
        """Build per-SKU policy block for a node."""
        pol = {}
        for sku in skus:
            if node_id == "Supplier":
                S = 0
            elif node_id in ("W1", "W2"):
                S = warehouse_info[sku][node_id]["S"]
            else:
                S = retailer_info[sku][node_id]["S"]
            pol[sku] = {"type": "base_stock", "base_stock_level": S}
        return pol

    def node_inventory(node_id: str) -> dict:
        inv = {}
        for sku in skus:
            if node_id == "Supplier":
                inv[sku] = 0
            elif node_id in ("W1", "W2"):
                inv[sku] = warehouse_info[sku][node_id]["S"]
            else:
                inv[sku] = retailer_info[sku][node_id]["S"]
        return inv

    props_a = SKU_PROPERTIES["SKU_A"]
    props_b = SKU_PROPERTIES["SKU_B"]

    nodes = [
        {
            "id": "Supplier",
            "type": "supplier",
            "infinite_supply": True,
            "policy": node_policy("Supplier"),
            "initial_inventory": {"SKU_A": 0, "SKU_B": 0},
            "holding_cost": {"SKU_A": props_a["holding_cost_supplier"],
                             "SKU_B": props_b["holding_cost_supplier"]},
            "shortage_cost": {"SKU_A": 0.0, "SKU_B": 0.0},
            "order_cost_fixed": 20.0,
            "order_cost_per_unit": 0.005,
        },
        {
            "id": "W1",
            "type": "warehouse",
            "policy": node_policy("W1"),
            "initial_inventory": node_inventory("W1"),
            "holding_cost": {"SKU_A": props_a["holding_cost_warehouse"],
                             "SKU_B": props_b["holding_cost_warehouse"]},
            "shortage_cost": {"SKU_A": 0.0, "SKU_B": 0.0},
            "order_cost_fixed": 15.0,
            "order_cost_per_unit": 0.01,
        },
        {
            "id": "W2",
            "type": "warehouse",
            "policy": node_policy("W2"),
            "initial_inventory": node_inventory("W2"),
            "holding_cost": {"SKU_A": props_a["holding_cost_warehouse"],
                             "SKU_B": props_b["holding_cost_warehouse"]},
            "shortage_cost": {"SKU_A": 0.0, "SKU_B": 0.0},
            "order_cost_fixed": 15.0,
            "order_cost_per_unit": 0.01,
        },
        {
            "id": "R1",
            "type": "retailer",
            "policy": node_policy("R1"),
            "initial_inventory": node_inventory("R1"),
            "holding_cost": {"SKU_A": props_a["holding_cost_retailer"],
                             "SKU_B": props_b["holding_cost_retailer"]},
            "shortage_cost": {"SKU_A": props_a["shortage_cost"],
                              "SKU_B": props_b["shortage_cost"]},
            "order_cost_fixed": 0.0,
            "order_cost_per_unit": 0.0,
        },
        {
            "id": "R2",
            "type": "retailer",
            "policy": node_policy("R2"),
            "initial_inventory": node_inventory("R2"),
            "holding_cost": {"SKU_A": props_a["holding_cost_retailer"],
                             "SKU_B": props_b["holding_cost_retailer"]},
            "shortage_cost": {"SKU_A": props_a["shortage_cost"],
                              "SKU_B": props_b["shortage_cost"]},
            "order_cost_fixed": 0.0,
            "order_cost_per_unit": 0.0,
        },
        {
            "id": "R3",
            "type": "retailer",
            "policy": node_policy("R3"),
            "initial_inventory": node_inventory("R3"),
            "holding_cost": {"SKU_A": props_a["holding_cost_retailer"],
                             "SKU_B": props_b["holding_cost_retailer"]},
            "shortage_cost": {"SKU_A": props_a["shortage_cost"],
                              "SKU_B": props_b["shortage_cost"]},
            "order_cost_fixed": 0.0,
            "order_cost_per_unit": 0.0,
        },
    ]

    edges = []
    for (frm, to), lt in LEAD_TIMES.items():
        tr = TRANSPORT_OPTIONS[(frm, to)]
        edges.append({
            "from": frm,
            "to": to,
            "lead_time": {"type": "deterministic", "value": lt},
            "mode": tr["mode"],
            "capacity": tr["capacity"],
            "cost_full": tr["cost_full"],
            "cost_half": tr["cost_half"],
            "cost_quarter": tr["cost_quarter"],
        })

    demand = []
    for sku in skus:
        for r_id in ("R1", "R2", "R3"):
            demand.append({
                "node": r_id,
                "sku": sku,
                "generator": {
                    "type": "csv",
                    "path": retailer_csv[sku][r_id],
                    "date_col": "date",
                    "qty_col": "quantity",
                    "strategy": "wrap",
                },
            })

    # SKU physical properties — used by transport planner
    sku_properties = {
        sku: {
            "volume_per_unit": SKU_PROPERTIES[sku]["volume_per_unit"],
            "weight_per_unit": SKU_PROPERTIES[sku]["weight_per_unit"],
        }
        for sku in skus
    }

    cfg = {
        "seed": 42,
        "time_horizon": T,
        "skus": skus,
        "sku_properties": sku_properties,
        "nodes": nodes,
        "edges": edges,
        "demand": demand,
    }

    out_cfg = (root / out_config_path).resolve()
    out_cfg.parent.mkdir(parents=True, exist_ok=True)
    out_cfg.write_text(json.dumps(cfg, indent=2))
    print(f"\n[ok] config written : {out_cfg}")
    print(f"[ok] SKU_A CSVs     : {root / out_csv_dir_a}")
    print(f"[ok] SKU_B CSVs     : {root / out_csv_dir_b}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sku_a_dir",      default="dataset/m5_dataset/processed")
    ap.add_argument("--sku_b_dir",      default="dataset/m5_dataset/processed/sku_b")
    ap.add_argument("--out_config",     default="config/1n3_2sku.json")
    ap.add_argument("--out_csv_dir_a",  default="dataset/m5_dataset/processed/retailers")
    ap.add_argument("--out_csv_dir_b",  default="dataset/m5_dataset/processed/retailers_sku_b")
    ap.add_argument("--z",              default=1.64, type=float,
                    help="Service level z-score for base-stock computation")
    args = ap.parse_args()
    main(
        sku_a_dir=args.sku_a_dir,
        sku_b_dir=args.sku_b_dir,
        out_config_path=args.out_config,
        out_csv_dir_a=args.out_csv_dir_a,
        out_csv_dir_b=args.out_csv_dir_b,
        z=args.z,
    )