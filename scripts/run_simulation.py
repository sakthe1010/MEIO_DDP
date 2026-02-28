import json
import os
import argparse
import pandas as pd
import sys
from pathlib import Path
import numpy as np
from datetime import datetime
from collections import defaultdict
from typing import Dict, Callable, List, Tuple

# --- make project imports work even when launched via VS Code Run button ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.node import Node
from engine.network import Network, Edge
from engine.simulator import Simulator
from policies.base_stock import BaseStockPolicy
from policies.ss_policy import SsPolicy
from policies.order_up_to import OrderUpToPolicy
from policies.km_cycle import KmCyclePolicy
from policies.periodic_review import PeriodicReviewPolicy

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
        pol_block = n.get("policy", {})
        if not pol_block:
            policies.add("unknown")
            continue
        # policy block is {sku: {type: ...}} — grab type from first SKU
        first_sku_pol = next(iter(pol_block.values()))
        if isinstance(first_sku_pol, dict):
            policies.add(first_sku_pol.get("type", "unknown"))
        else:
            policies.add(pol_block.get("type", "unknown"))
    if not policies:
        return "No policies defined"
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
        raise TypeError("build_from_config expects a path or dict")

    top_seed = cfg.get("seed", None)

    # ============================================================
    # GLOBAL SKU LIST
    # ============================================================

    if "skus" not in cfg:
        # Auto-wrap single SKU configs for tests
        cfg = dict(cfg)  # shallow copy
        cfg["skus"] = ["SKU1"]

        for nd in cfg["nodes"]:
            if "initial_inventory" in nd and not isinstance(nd["initial_inventory"], dict):
                nd["initial_inventory"] = {"SKU1": nd["initial_inventory"]}

            if "policy" in nd and not isinstance(list(nd["policy"].values())[0], dict):
                nd["policy"] = {"SKU1": nd["policy"]}

        for d in cfg.get("demand", []):
            if "sku" not in d:
                d["sku"] = "SKU1"

    skus = cfg["skus"]


    # ============================================================
    # BUILD NODES
    # ============================================================

    nodes = {}

    for nd in cfg["nodes"]:

        # ---- Build policies per SKU ----
        policies = {}

        policy_block = nd.get("policy", {})

        for sku in skus:

            if sku not in policy_block:
                raise ValueError(f"Node {nd['id']} missing policy for SKU {sku}")

            pol = policy_block[sku]
            ptype = pol["type"]

            if ptype == "base_stock":
                policy = BaseStockPolicy(
                    base_stock_level=pol["base_stock_level"]
                )

            elif ptype == "sS":

                policy = SsPolicy(
                    s=pol["s"],
                    S=pol["S"]
                )

            elif ptype == "order_up_to":

                policy = OrderUpToPolicy(
                    R=pol["R"],
                    S=pol["S"],
                    phase_offset=pol.get("phase_offset", 0),
                    k=pol.get("k"),
                    m=pol.get("m")
                )

            elif ptype == "km_cycle":

                policy = KmCyclePolicy(
                    k=pol["k"],
                    m=pol["m"],
                    S=pol["S"],
                    review_offsets=tuple(pol.get("review_offsets", (0,)))
                )

            elif ptype == "periodic_review":

                policy = PeriodicReviewPolicy(
                    review_period=pol["review_period"],
                    order_up_to=pol["order_up_to"]
                )

            else:
                raise ValueError(f"Unknown policy type {ptype}")


            policies[sku] = policy

        # ---- Node creation ----

        nodes[nd["id"]] = Node(
            node_id=nd["id"],
            node_type=nd["type"],
            policies=policies,
            skus=skus,
            initial_inventory=nd.get("initial_inventory", {}),
            holding_cost=nd.get("holding_cost", 0.0),
            shortage_cost=nd.get("shortage_cost", 0.0),
            infinite_supply=nd.get("infinite_supply", False),
            order_cost_fixed=nd.get("order_cost_fixed", 0.0),
            order_cost_per_unit=nd.get("order_cost_per_unit", 0.0),
        )

    # ============================================================
    # BUILD NETWORK
    # ============================================================

    net = Network()

    for node in nodes.values():
        net.add_node(node)

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

        net.add_edge(
            parent_id=e["from"],
            child_id=e["to"],
            route_id=e.get("route_id"),
            mode=e.get("mode", 1),
            capacity=e.get("capacity", 100.0),
            cost_full=e.get("cost_full", 0.0),
            cost_half=e.get("cost_half", 0.0),
            cost_quarter=e.get("cost_quarter", 0.0),
            lead_time_sampler=sampler,
            share=e.get("share", None)
        )

    # ============================================================
    # BUILD DEMAND (PER NODE, PER SKU)
    # ============================================================

    demand_by_node: Dict[str, Dict[str, callable]] = {}

    for d in cfg.get("demand", []):

        node = d["node"]
        sku = d["sku"]
        g = d["generator"]

        d_seed = g.get("seed", top_seed)
        d_rng = random.Random(d_seed) if d_seed is not None else random.Random()

        gtype = g["type"]

        if gtype == "deterministic":

            gen = DeterministicDemand(g["value"]).sample

        elif gtype == "poisson":

            gen = PoissonDemand(g["lam"], d_rng).sample

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
                raise ValueError("csv generator requires 'path' or ('manifest' + 'store_id')")

            start_index = int(g.get("start_index", 0))
            strategy = g.get("strategy", "wrap")

            gen = CSVDrivenDemand(series, strategy, start_index).sample

        else:
            raise ValueError(f"Unknown demand generator type {gtype}")


        demand_by_node.setdefault(node, {})
        demand_by_node[node][sku] = gen

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
    pd.DataFrame(sim_sum.inventory_log).to_csv(run_dir / "inventory_log.csv", index=False)
    pd.DataFrame(sim_sum.orders_log).to_csv(run_dir / "orders_log.csv", index=False)

    shipments_df = pd.DataFrame(sim_sum.shipments_log)
    if not shipments_df.empty:
        shipments_df["arrival_time"] = (
            shipments_df["t_ship"] + shipments_df["lead_time"]
        )
        shipments_df.rename(columns={
            "parent": "from_node",
            "child": "to_node"
        }, inplace=True)

        shipments_df.to_csv(
            run_dir / "shipments_log.csv", index=False
        )

    df_sum = pd.DataFrame([m.__dict__ for m in metrics_sum])
    df_sum.to_csv(run_dir / "opt_results_summary.csv", index=False)

    is_eod = df_sum["phase"] == "EOD"
    c = df_sum[is_eod].copy()
    grp = c.groupby(["node_id", "sku"]).agg(
        holding_cost=("holding_cost", "sum"),
        backlog_cost=("backlog_cost", "sum"),
        ordering_cost=("ordering_cost", "sum"),
        transport_cost=("transport_cost", "sum"),
        total_cost=("total_cost", "sum"),
    ).reset_index()


    overall = pd.DataFrame([{
    "node_id": "_OVERALL_",
    "sku": "_ALL_",
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

        grp = dfe.groupby(["node_id", "sku"]).agg(
            demand_sum=("demand", "sum"),
            fulfilled_sum=("fulfilled_external", "sum"),
        ).reset_index()

        grp["fill_rate"] = grp["fulfilled_sum"] / grp["demand_sum"].replace(0, 1)

        overall = pd.DataFrame([{
            "node_id": "_OVERALL_",
            "sku": "_ALL_",
            "demand_sum": grp["demand_sum"].sum(),
            "fulfilled_sum": grp["fulfilled_sum"].sum(),
            "fill_rate": grp["fulfilled_sum"].sum() /
                        grp["demand_sum"].sum()
                        if grp["demand_sum"].sum() > 0 else 1.0
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
