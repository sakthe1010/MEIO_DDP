import json
import os
import argparse
import pandas as pd
import sys
from pathlib import Path
import numpy as np
from datetime import datetime

# --- make project imports work even when launched via VS Code Run button ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.node import Node
from engine.network import Network, Edge
from engine.simulator import Simulator
from policies.base_stock import BaseStockPolicy
from policies.ss_policy import SsPolicy

# demand/lead-time generators (inline)
from dataclasses import dataclass
import math, random
from typing import List

# ---------- Demand ----------
class DemandGenerator:
    def sample(self, t: int) -> int: raise NotImplementedError

@dataclass
class DeterministicDemand(DemandGenerator):
    value: int
    def sample(self, t): return int(self.value)

@dataclass
class PoissonDemand(DemandGenerator):
    lam: float
    rng: random.Random
    def sample(self, t):
        L = math.exp(-self.lam)
        k = 0
        p = 1.0
        while p > L:
            k += 1
            p *= self.rng.random()
        return k - 1

# NEW: CSV-driven demand (wrap/clip strategies)
@dataclass
class CSVDrivenDemand(DemandGenerator):
    series: List[int]
    strategy: str = "wrap"
    start_index: int = 0
    def sample(self, t: int) -> int:
        if not self.series:
            return 0
        i = self.start_index + t
        if i < len(self.series):
            return int(self.series[i])
        if self.strategy == "wrap":
            return int(self.series[i % len(self.series)])
        return 0

# ---------- Lead time ----------
class LeadTimeGenerator:
    def sample(self) -> int: raise NotImplementedError

@dataclass
class DeterministicLeadTime(LeadTimeGenerator):
    value: int
    def sample(self): return int(self.value)

@dataclass
class NormalIntLeadTime(LeadTimeGenerator):
    mean: float
    std: float
    rng: random.Random
    def sample(self):
        return max(0, int(round(self.rng.gauss(self.mean, self.std))))

def _read_csv_series(path: Path, date_col: str, qty_col: str) -> List[int]:
    if not path.exists():
        raise FileNotFoundError(f"Demand file not found: {path}")
    df = pd.read_csv(path)
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)
    s = df[qty_col].fillna(0).astype(int).tolist()
    return s

# =========================
# PRESENTABILITY HELPERS (ADDED)
# =========================

def print_header():
    print("=" * 70)
    print("DDP – Supply Chain Digital Twin Simulator")
    print("=" * 70)

def _describe_demand(cfg):
    types = set()
    for d in cfg.get("demand", []):
        types.add(d["generator"]["type"])
    if not types:
        return "No external demand"
    if types == {"deterministic"}:
        return "Deterministic"
    if types == {"csv"}:
        return "CSV (historical)"
    if types == {"poisson"}:
        return "Poisson"
    return "Mixed"

def _describe_policy(cfg):
    policies = set()
    for n in cfg["nodes"]:
        policies.add(n.get("policy", {}).get("type", "unknown"))
    if len(policies) == 1:
        return list(policies)[0]
    return "Multiple policy types"

def _print_cost_summary(costs_df):
    overall = costs_df[costs_df["node_id"] == "_OVERALL_"].iloc[0]
    total = overall["total_cost"]

    print("\nCost summary (aggregate)")
    print("-" * 40)
    print(f"Total cost : {total:,.2f}")
    if total > 0:
        print(f"Holding    : {100 * overall['holding_cost'] / total:5.1f}%")
        print(f"Transport  : {100 * overall['transport_cost'] / total:5.1f}%")
        print(f"Ordering   : {100 * overall['ordering_cost'] / total:5.1f}%")
        print(f"Shortage   : {100 * overall['backlog_cost'] / total:5.1f}%")

def print_scenario_summary(cfg):
    nodes = cfg["nodes"]
    edges = cfg["edges"]

    suppliers = sum(n["type"] == "supplier" for n in nodes)
    warehouses = sum(n["type"] == "warehouse" for n in nodes)
    retailers = sum(n["type"] == "retailer" for n in nodes)

    print("\nScenario summary")
    print("-" * 40)
    print(f"Suppliers        : {suppliers}")
    print(f"Warehouses       : {warehouses}")
    print(f"Retailers        : {retailers}")
    print(f"Transport lanes  : {len(edges)}")
    print(f"Time horizon     : {cfg['time_horizon']} days")

    print("\nDemand model")
    print("-" * 40)
    print(_describe_demand(cfg))

    print("\nInventory policy")
    print("-" * 40)
    print(_describe_policy(cfg))

# =========================
# ORIGINAL build_from_config (UNCHANGED)
# =========================

def build_from_config(cfg_or_path):
    if isinstance(cfg_or_path, (str, os.PathLike)):
        with open(cfg_or_path, "r") as f:
            cfg = json.load(f)
    elif isinstance(cfg_or_path, dict):
        cfg = cfg_or_path
    else:
        raise TypeError("build_from_config expects a path or a dict")

    top_seed = cfg.get("seed", None)

    nodes = {}
    for nd in cfg["nodes"]:
        pol = nd.get("policy", {})
        ptype = pol.get("type", "base_stock")
        if ptype == "base_stock":
            policy = BaseStockPolicy(base_stock_level=pol["base_stock_level"])
        elif ptype == "sS":
            policy = SsPolicy(s=pol["s"], S=pol["S"])
        elif ptype == "order_up_to":
            from policies.order_up_to import OrderUpToPolicy
            policy = OrderUpToPolicy(R=pol["R"], S=pol["S"], phase_offset=pol.get("phase_offset", 0))
        elif ptype == "km_cycle":
            from policies.km_cycle import KmCyclePolicy
            policy = KmCyclePolicy(
                k=pol["k"], m=pol["m"], S=pol["S"],
                review_offsets=tuple(pol.get("review_offsets", (0,)))
            )
        else:
            raise ValueError(f"Unknown policy type {ptype}")

        nodes[nd["id"]] = Node(
            node_id=nd["id"],
            node_type=nd["type"],
            policy=policy,
            initial_inventory=nd.get("initial_inventory", 0),
            holding_cost=nd.get("holding_cost", 0.0),
            shortage_cost=nd.get("shortage_cost", 0.0),
            infinite_supply=nd.get("infinite_supply", False),
            order_cost_fixed=nd.get("order_cost_fixed", 0.0),
            order_cost_per_unit=nd.get("order_cost_per_unit", 0.0),
        )

    edges = {}
    for e in cfg["edges"]:
        lt = e["lead_time"]
        lt_seed = lt.get("seed", top_seed)
        lt_rng = random.Random(lt_seed) if lt_seed is not None else random.Random()

        if lt["type"] == "deterministic":
            sampler = DeterministicLeadTime(lt["value"]).sample
        elif lt["type"] == "normal_int":
            sampler = NormalIntLeadTime(lt["mean"], lt["std"], lt_rng).sample
        else:
            raise ValueError("Unknown lead time type")

        key = (e["from"], e["to"])
        edges.setdefault(key, []).append(
            Edge(
                parent=e["from"],
                child=e["to"],
                lead_time_sampler=sampler,
                share=e.get("share"),
                transport_cost_per_unit=e.get("transport_cost_per_unit", 0.0)
            )
        )

    net = Network(nodes=nodes, edges=edges)

    demand_by_node = {}
    for d in cfg.get("demand", []):
        node = d["node"]; g = d["generator"]
        d_seed = g.get("seed", top_seed)
        d_rng = random.Random(d_seed) if d_seed is not None else random.Random()

        gtype = g["type"]
        if gtype == "deterministic":
            demand_by_node[node] = DeterministicDemand(g["value"]).sample
        elif gtype == "poisson":
            demand_by_node[node] = PoissonDemand(g["lam"], d_rng).sample
        elif gtype == "csv":
            date_col = g.get("date_col", "date")
            qty_col = g.get("qty_col", "quantity")

            if "path" in g:
                path = (ROOT / g["path"]).resolve()
                series = _read_csv_series(path, date_col, qty_col)
            elif "manifest" in g and "store_id" in g:
                man_path = (ROOT / g["manifest"]).resolve()
                with open(man_path, "r") as mf:
                    manifest = json.load(mf)
                csv_rel = manifest["files"][str(g["store_id"])]
                path = (man_path.parent / csv_rel).resolve()
                series = _read_csv_series(path, date_col, qty_col)
            else:
                raise ValueError("csv generator requires either 'path' or ('manifest' + 'store_id').")

            start_index = int(g.get("start_index", 0))
            demand_by_node[node] = CSVDrivenDemand(series, g.get("strategy", "wrap"), start_index).sample
        else:
            raise ValueError(f"Unknown demand generator type {gtype}")

    T = int(cfg["time_horizon"])
    return net, demand_by_node, T

# =========================
# MAIN
# =========================

def main():
    parser = argparse.ArgumentParser(description="Run supply chain sim and write CSV.")
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--mode", type=str, default="both",
                        choices=["summary", "detailed", "both"])
    parser.add_argument("--outdir", type=str, default=str(ROOT / "outputs"))
    args = parser.parse_args()

    print_header()

    net, demand_by_node, T = build_from_config(args.config)
    with open(args.config) as f:
        cfg = json.load(f)

    print_scenario_summary(cfg)

    run_name = Path(args.config).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(args.outdir) / f"{run_name}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    sim_sum = Simulator(network=net, demand_by_node=demand_by_node, T=T, order_processing_delay=1)
    metrics_sum = sim_sum.run(mode="summary")
    df_sum = pd.DataFrame([m.__dict__ for m in metrics_sum])
    df_sum.to_csv(run_dir / "opt_results_summary.csv", index=False)

    is_eod = df_sum["phase"] == "EOD"
    c = df_sum[is_eod].copy()
    grp = c.groupby("node_id").agg(
        holding_cost=("holding_cost", "sum"),
        backlog_cost=("backlog_cost", "sum"),
        ordering_cost=("ordering_cost", "sum"),
        transport_cost=("transport_cost", "sum"),
        total_cost=("total_cost", "sum"),
    ).reset_index()

    overall = pd.DataFrame([{
        "node_id": "_OVERALL_",
        "holding_cost": grp["holding_cost"].sum(),
        "backlog_cost": grp["backlog_cost"].sum(),
        "ordering_cost": grp["ordering_cost"].sum(),
        "transport_cost": grp["transport_cost"].sum(),
        "total_cost": grp["total_cost"].sum(),
    }])

    costs_df = pd.concat([grp, overall], ignore_index=True)
    costs_df.to_csv(run_dir / "costs_summary.csv", index=False)

    _print_cost_summary(costs_df)

    def _compute_kpis(df):
        is_eod = df["phase"] == "EOD"
        dfe = df[is_eod].copy()
        grp = dfe.groupby("node_id").agg(
            demand_sum=("demand", "sum"),
            fulfilled_sum=("fulfilled_external", "sum"),
        ).reset_index()
        grp["fill_rate"] = grp["fulfilled_sum"] / grp["demand_sum"]
        overall = pd.DataFrame([{
            "node_id": "_OVERALL_",
            "demand_sum": grp["demand_sum"].sum(),
            "fulfilled_sum": grp["fulfilled_sum"].sum(),
            "fill_rate": grp["fulfilled_sum"].sum() / grp["demand_sum"].sum()
        }])
        return pd.concat([grp, overall], ignore_index=True)

    kpi_df = _compute_kpis(df_sum)
    kpi_df.to_csv(run_dir / "kpis_summary.csv", index=False)

    print("\nService level")
    print("-" * 40)
    overall = kpi_df[kpi_df["node_id"] == "_OVERALL_"].iloc[0]
    print(f"Fill rate : {overall['fill_rate'] * 100:.2f} %")

    print("\nOutputs written to")
    print(run_dir)
    print("=" * 70)

if __name__ == "__main__":
    main()
