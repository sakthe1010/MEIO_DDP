"""
build_1n3_config_v3.py
======================
Generates a multi-SKU JSON config for the 1-Supplier → 2-Warehouse → 3-Retailer
network using real M5 demand data.

Each SKU has:
  - its own demand CSV directory
  - its own physical properties (volume_per_unit, weight_per_unit)
  - its own independently computed base-stock levels (newsvendor formula)
  - its own cost parameters

Usage
-----
  python build_1n3_config_v3.py                          # 5-SKU default
  python build_1n3_config_v3.py --out_config config/1n3_5sku.json
  python build_1n3_config_v3.py --skus SKU_A SKU_B       # 2-SKU subset

Requirements
------------
Each SKU needs a folder under dataset/m5_dataset/processed/<ITEM_ID>/
containing one CSV per store (CA_1.csv, CA_2.csv, ...) with columns
[date, quantity].

The 5 default SKUs:
  SKU_A  FOODS_3_586  fast mover     ~48/day   0.002 m³/unit
  SKU_B  FOODS_3_714  slow mover     ~21/day   0.008 m³/unit
  SKU_C  FOODS_3_252  medium         ~35/day   0.003 m³/unit
  SKU_D  FOODS_3_555  medium-slow    ~28/day   0.005 m³/unit
  SKU_E  FOODS_3_694  slow           ~18/day   0.006 m³/unit
"""

import json
import math
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import pandas as pd


# ============================================================
# SKU catalogue — edit here to add / swap SKUs
# ============================================================

SKU_CATALOGUE = {
    "SKU_A": {
        "item_id":         "FOODS_3_586",
        "volume_per_unit": 0.002,   # m³ per unit
        "weight_per_unit": 0.80,    # kg per unit
        "holding_cost":    {"supplier": 0.005, "warehouse": 0.015, "retailer": 0.025},
        "shortage_cost":   {"supplier": 0.0,   "warehouse": 0.0,   "retailer": 0.50},
        "order_cost_fixed":    {"supplier": 0.0, "warehouse": 12.0, "retailer": 0.0},
        "order_cost_per_unit": {"supplier": 0.0, "warehouse": 0.008, "retailer": 0.002},
    },
    "SKU_B": {
        "item_id":         "FOODS_3_714",
        "volume_per_unit": 0.008,
        "weight_per_unit": 0.50,
        "holding_cost":    {"supplier": 0.005, "warehouse": 0.018, "retailer": 0.030},
        "shortage_cost":   {"supplier": 0.0,   "warehouse": 0.0,   "retailer": 0.60},
        "order_cost_fixed":    {"supplier": 0.0, "warehouse": 10.0, "retailer": 0.0},
        "order_cost_per_unit": {"supplier": 0.0, "warehouse": 0.006, "retailer": 0.002},
    },
    "SKU_C": {
        "item_id":         "FOODS_3_252",
        "volume_per_unit": 0.003,
        "weight_per_unit": 1.20,
        "holding_cost":    {"supplier": 0.005, "warehouse": 0.016, "retailer": 0.027},
        "shortage_cost":   {"supplier": 0.0,   "warehouse": 0.0,   "retailer": 0.45},
        "order_cost_fixed":    {"supplier": 0.0, "warehouse": 11.0, "retailer": 0.0},
        "order_cost_per_unit": {"supplier": 0.0, "warehouse": 0.007, "retailer": 0.002},
    },
    "SKU_D": {
        "item_id":         "FOODS_3_555",
        "volume_per_unit": 0.005,
        "weight_per_unit": 0.70,
        "holding_cost":    {"supplier": 0.005, "warehouse": 0.017, "retailer": 0.028},
        "shortage_cost":   {"supplier": 0.0,   "warehouse": 0.0,   "retailer": 0.55},
        "order_cost_fixed":    {"supplier": 0.0, "warehouse": 10.0, "retailer": 0.0},
        "order_cost_per_unit": {"supplier": 0.0, "warehouse": 0.007, "retailer": 0.002},
    },
    "SKU_E": {
        "item_id":         "FOODS_3_694",
        "volume_per_unit": 0.006,
        "weight_per_unit": 0.90,
        "holding_cost":    {"supplier": 0.005, "warehouse": 0.016, "retailer": 0.026},
        "shortage_cost":   {"supplier": 0.0,   "warehouse": 0.0,   "retailer": 0.40},
        "order_cost_fixed":    {"supplier": 0.0, "warehouse": 9.0, "retailer": 0.0},
        "order_cost_per_unit": {"supplier": 0.0, "warehouse": 0.006, "retailer": 0.002},
    },
}

# ============================================================
# Network topology — edit here to change network shape
# ============================================================

STORE_GROUPS = {
    "R1": ["CA_1", "CA_2", "WI_1", "TX_1"],
    "R2": ["CA_3", "CA_4", "WI_2"],
    "R3": ["WI_3", "TX_2", "TX_3"],
}

# Which warehouse serves which retailer
RETAILER_PARENT = {"R1": "W1", "R2": "W1", "R3": "W2"}

LEAD_TIMES = {
    ("Supplier", "W1"): 5,
    ("Supplier", "W2"): 6,
    ("W1", "R1"):        2,
    ("W1", "R2"):        3,
    ("W2", "R3"):        4,
}

# Vehicle capacity (m³) and tiered cost per vehicle dispatch
TRANSPORT = {
    ("Supplier", "W1"): {"capacity": 67.0, "cost_full": 800.0,  "cost_half": 480.0,  "cost_quarter": 280.0},
    ("Supplier", "W2"): {"capacity": 67.0, "cost_full": 900.0,  "cost_half": 540.0,  "cost_quarter": 315.0},
    ("W1",       "R1"): {"capacity": 33.0, "cost_full": 350.0,  "cost_half": 210.0,  "cost_quarter": 122.0},
    ("W1",       "R2"): {"capacity": 33.0, "cost_full": 400.0,  "cost_half": 240.0,  "cost_quarter": 140.0},
    ("W2",       "R3"): {"capacity": 33.0, "cost_full": 380.0,  "cost_half": 228.0,  "cost_quarter": 133.0},
}


# ============================================================
# File helpers
# ============================================================

def find_repo_root(start: Path) -> Path:
    for p in [start.resolve()] + list(start.resolve().parents):
        if (p / "engine").exists():
            return p
    return start.resolve()


def read_store_csv(path: Path) -> pd.Series:
    """Read a store CSV, return a sorted integer quantity series."""
    df = pd.read_csv(path)
    col_lower = {c.lower(): c for c in df.columns}
    date_col = col_lower.get("date", df.columns[0])
    qty_col  = (col_lower.get("quantity")
                or col_lower.get("qty")
                or col_lower.get("demand")
                or col_lower.get("sales")
                or df.columns[1])
    try:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.sort_values(date_col)
    except Exception:
        pass
    return df[qty_col].fillna(0).clip(lower=0).round().astype(int).reset_index(drop=True)


def aggregate_stores(src_dir: Path, store_ids: List[str]) -> pd.Series:
    parts = []

    for sid in store_ids:
        p = src_dir / f"{sid}.csv"

        if not p.exists():
            print(f"[warn] missing {p.name} for {src_dir.name} — skipping")
            continue

        parts.append(read_store_csv(p))

    if not parts:
        raise RuntimeError(f"No valid store CSVs found in {src_dir}")

    min_len = min(len(s) for s in parts)
    total = sum(s.iloc[:min_len].values for s in parts)

    return pd.Series(total, dtype=int)


def newsvendor_base_stock(mu: float, sigma: float, lead_time: int, z: float = 1.64) -> int:
    """
    S = mu*(L+1) + z*sigma*sqrt(L+1)
    Protection interval = lead time + 1 review day.
    """
    PT = lead_time + 1
    return int(math.ceil(mu * PT + z * sigma * math.sqrt(PT)))


def sku_src_dir(processed_root: Path, item_id: str) -> Path:
    """Locate the per-store CSV directory for this item."""
    candidate = processed_root / item_id
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"No demand data for '{item_id}' — expected directory: {candidate}\n"
        f"Populate it with per-store CSVs: CA_1.csv, CA_2.csv, WI_1.csv, ..."
    )


# ============================================================
# Core builder
# ============================================================

def build_config(
    skus: List[str],
    processed_root: Path,
    out_csv_root: Path,
    repo_root: Path,
    time_horizon: Optional[int] = None,
    z: float = 1.64,
) -> dict:
    """
    Build the full config dict.

    Parameters
    ----------
    skus           : ordered list of SKU keys (must be in SKU_CATALOGUE)
    processed_root : .../dataset/m5_dataset/processed/
    out_csv_root   : where to write aggregated retailer demand CSVs
    repo_root      : project root (for making CSV paths relative)
    time_horizon   : override simulation length (days)
    z              : newsvendor z-score
    """

    # ----------------------------------------------------------
    # Step 1 — Aggregate demand & compute retailer S levels
    # ----------------------------------------------------------
    print("\n[build] Retailer demand statistics")
    print(f"  {'SKU':<8} {'Retailer':<6} {'mu':>8} {'sigma':>8} {'L':>4} {'S':>6} {'T':>6}")
    print(f"  {'-'*8} {'-'*6} {'-'*8} {'-'*8} {'-'*4} {'-'*6} {'-'*6}")

    # r_stats[sku][retailer] = {"S", "mu", "sigma", "T"}
    r_stats: Dict[str, Dict[str, dict]] = {}
    # agg_paths[sku][retailer] = absolute Path to written CSV
    agg_paths: Dict[str, Dict[str, Path]] = {}

    for sku in skus:
        item_id = SKU_CATALOGUE[sku]["item_id"]
        src_dir = sku_src_dir(processed_root, item_id)
        r_stats[sku]  = {}
        agg_paths[sku] = {}

        sku_store_groups = SKU_CATALOGUE[sku].get("store_groups", STORE_GROUPS)
        for r_id, stores in sku_store_groups.items():
            series = aggregate_stores(src_dir, stores)
            parent = RETAILER_PARENT[r_id]
            lt     = LEAD_TIMES[(parent, r_id)]
            mu     = float(series.mean())
            sigma  = float(series.std(ddof=1)) if len(series) > 1 else 0.0
            S      = newsvendor_base_stock(mu, sigma, lt, z)
            T_sku  = len(series)

            r_stats[sku][r_id] = {"S": S, "mu": mu, "sigma": sigma, "T": T_sku}
            print(f"  {sku:<8} {r_id:<6} {mu:>8.1f} {sigma:>8.1f} {lt:>4} {S:>6} {T_sku:>6}")

            # write CSV
            out_dir = out_csv_root / sku
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{r_id}.csv"
            pd.DataFrame({"date": range(T_sku), "quantity": series.values}).to_csv(out_path, index=False)
            agg_paths[sku][r_id] = out_path

    # ----------------------------------------------------------
    # Step 2 — Time horizon
    # ----------------------------------------------------------
    all_T = [r_stats[sku][r]["T"] for sku in skus for r in STORE_GROUPS]
    T = time_horizon if time_horizon else int(min(all_T))
    print(f"\n[build] Time horizon: {T} days")

    # ----------------------------------------------------------
    # Step 3 — Warehouse S levels
    # ----------------------------------------------------------
    print("\n[build] Warehouse base-stock levels")
    print(f"  {'SKU':<8} {'W1':>8} {'W2':>8}")
    print(f"  {'-'*8} {'-'*8} {'-'*8}")

    # w_stats[sku][wh] = {"S", "mu", "sigma"}
    w_stats: Dict[str, Dict[str, dict]] = {}

    for sku in skus:
        w_stats[sku] = {}

        # W1 aggregates R1 + R2
        mu_W1    = r_stats[sku]["R1"]["mu"]    + r_stats[sku]["R2"]["mu"]
        sigma_W1 = math.sqrt(r_stats[sku]["R1"]["sigma"]**2 + r_stats[sku]["R2"]["sigma"]**2)
        S_W1     = newsvendor_base_stock(mu_W1, sigma_W1, LEAD_TIMES[("Supplier", "W1")], z)
        w_stats[sku]["W1"] = {"S": S_W1, "mu": mu_W1, "sigma": sigma_W1}

        # W2 serves R3 only
        mu_W2    = r_stats[sku]["R3"]["mu"]
        sigma_W2 = r_stats[sku]["R3"]["sigma"]
        S_W2     = newsvendor_base_stock(mu_W2, sigma_W2, LEAD_TIMES[("Supplier", "W2")], z)
        w_stats[sku]["W2"] = {"S": S_W2, "mu": mu_W2, "sigma": sigma_W2}

        print(f"  {sku:<8} {S_W1:>8} {S_W2:>8}")

    # ----------------------------------------------------------
    # Step 4 — Assemble config dict
    # ----------------------------------------------------------

    def _per_sku(cost_key: str, node_type: str) -> dict:
        """Return {SKU_A: val, ...} for a cost field at a given node type."""
        return {sku: SKU_CATALOGUE[sku][cost_key].get(node_type, 0.0) for sku in skus}

    nodes = []

    # Supplier (infinite, no costs)
    nodes.append({
        "id": "Supplier",
        "type": "supplier",
        "infinite_supply": True,
        "policy": {sku: {"type": "base_stock", "base_stock_level": 0} for sku in skus},
        "holding_cost":        0.0,
        "shortage_cost":       0.0,
        "order_cost_fixed":    0.0,
        "order_cost_per_unit": 0.0,
    })

    # Warehouses
    for wh in ("W1", "W2"):
        nodes.append({
            "id": wh,
            "type": "warehouse",
            "initial_inventory": {sku: w_stats[sku][wh]["S"] for sku in skus},
            "policy": {
                sku: {"type": "base_stock", "base_stock_level": w_stats[sku][wh]["S"]}
                for sku in skus
            },
            "holding_cost":        _per_sku("holding_cost",        "warehouse"),
            "shortage_cost":       0.0,
            "order_cost_fixed":    _per_sku("order_cost_fixed",    "warehouse"),
            "order_cost_per_unit": _per_sku("order_cost_per_unit", "warehouse"),
        })

    # Retailers
    for r_id in ("R1", "R2", "R3"):
        nodes.append({
            "id": r_id,
            "type": "retailer",
            "initial_inventory": {sku: r_stats[sku][r_id]["S"] for sku in skus},
            "policy": {
                sku: {"type": "base_stock", "base_stock_level": r_stats[sku][r_id]["S"]}
                for sku in skus
            },
            "holding_cost":        _per_sku("holding_cost",        "retailer"),
            "shortage_cost":       _per_sku("shortage_cost",       "retailer"),
            "order_cost_fixed":    0.0,
            "order_cost_per_unit": _per_sku("order_cost_per_unit", "retailer"),
        })

    # Edges
    edges = []
    for (parent, child), lt in LEAD_TIMES.items():
        tr = TRANSPORT[(parent, child)]
        edges.append({
            "from":         parent,
            "to":           child,
            "route_id":     f"{parent}_{child}",
            "mode":         1,
            "lead_time":    {"type": "deterministic", "value": lt},
            "capacity":     tr["capacity"],
            "cost_full":    tr["cost_full"],
            "cost_half":    tr["cost_half"],
            "cost_quarter": tr["cost_quarter"],
        })

    # Demand entries — one per (SKU, retailer)
    demand = []
    for sku in skus:
        for r_id in ("R1", "R2", "R3"):
            rel_path = str(agg_paths[sku][r_id].relative_to(repo_root))
            demand.append({
                "node": r_id,
                "sku":  sku,
                "generator": {
                    "type":     "csv",
                    "path":     rel_path,
                    "date_col": "date",
                    "qty_col":  "quantity",
                    "strategy": "clip",
                },
            })

    # SKU physical properties
    sku_properties = {
        sku: {
            "item_id":         SKU_CATALOGUE[sku]["item_id"],
            "volume_per_unit": SKU_CATALOGUE[sku]["volume_per_unit"],
            "weight_per_unit": SKU_CATALOGUE[sku]["weight_per_unit"],
        }
        for sku in skus
    }

    return {
        "seed":           42,
        "time_horizon":   T,
        "skus":           skus,
        "sku_properties": sku_properties,
        "nodes":          nodes,
        "edges":          edges,
        "demand":         demand,
    }


# ============================================================
# Entry point
# ============================================================

def main():
    ap = argparse.ArgumentParser(
        description="Build N-SKU 1-Supplier→2-Warehouse→3-Retailer config from M5 data."
    )
    ap.add_argument(
        "--skus", nargs="+", default=list(SKU_CATALOGUE.keys()),
        help="SKU keys to include (default: all 5). E.g. --skus SKU_A SKU_B"
    )
    ap.add_argument(
        "--out_config", default="config/1n3_5sku.json",
        help="Output config path relative to repo root"
    )
    ap.add_argument(
        "--out_csv_dir", default="dataset/m5_dataset/processed/retailers_multisku",
        help="Directory for aggregated retailer demand CSVs"
    )
    ap.add_argument(
        "--z", type=float, default=1.64,
        help="Newsvendor z-score (default 1.64 = 95%% service level)"
    )
    ap.add_argument(
        "--horizon", type=int, default=None,
        help="Override simulation length in days"
    )
    args = ap.parse_args()

    # Validate SKU keys early
    for sku in args.skus:
        if sku not in SKU_CATALOGUE:
            raise ValueError(f"Unknown SKU '{sku}'. Available: {list(SKU_CATALOGUE.keys())}")

    here = Path(__file__).resolve()
    root = find_repo_root(here.parent)
    print(f"[build] Repo root  : {root}")
    print(f"[build] SKUs       : {args.skus}")
    print(f"[build] z-score    : {args.z}  (service level ~{100*(1-(1-0.5*math.erf(args.z/math.sqrt(2)))):.1f}%)")

    processed_root = root / "dataset" / "m5_dataset" / "processed"
    out_csv_root   = (root / args.out_csv_dir).resolve()
    out_cfg_path   = (root / args.out_config).resolve()

    cfg = build_config(
        skus=args.skus,
        processed_root=processed_root,
        out_csv_root=out_csv_root,
        repo_root=root,
        time_horizon=args.horizon,
        z=args.z,
    )

    out_cfg_path.parent.mkdir(parents=True, exist_ok=True)
    out_cfg_path.write_text(json.dumps(cfg, indent=2))

    # Summary table
    print(f"\n[build] Base-stock levels written to config")
    header = f"  {'Node':<12}" + "".join(f"  {s:<10}" for s in args.skus)
    print(header)
    print("  " + "-" * (12 + 12 * len(args.skus)))
    for node in cfg["nodes"]:
        inv = node.get("initial_inventory", {})
        if isinstance(inv, dict):
            row = "".join(f"  {inv.get(s, 0):<10}" for s in args.skus)
        else:
            row = f"  {inv}"
        print(f"  {node['id']:<12}{row}")

    print(f"\n[build] Config  → {out_cfg_path}")
    print(f"[build] CSVs    → {out_csv_root}")
    print(f"\n[build] Run simulation with:")
    print(f"  python scripts/run_simulation.py --config {args.out_config}")


if __name__ == "__main__":
    main()