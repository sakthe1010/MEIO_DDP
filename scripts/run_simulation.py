import json
import os
import argparse
import pandas as pd

from engine.node import Node
from engine.network import Network, Edge
from engine.simulator import Simulator
from policies.base_stock import BaseStockPolicy
from policies.ss_policy import SsPolicy

# demand/lead-time generators (inline)
from dataclasses import dataclass
import math, random

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

def build_from_config(cfg_or_path):
    if isinstance(cfg_or_path, (str, os.PathLike)):
        with open(cfg_or_path, "r") as f:
            cfg = json.load(f)
    elif isinstance(cfg_or_path, dict):
        cfg = cfg_or_path
    else:
        raise TypeError("build_from_config expects a path or a dict")

    top_seed = cfg.get("seed", None)

    # nodes
    nodes = {}
    for nd in cfg["nodes"]:
        pol = nd.get("policy", {})
        ptype = pol.get("type", "base_stock")
        if ptype == "base_stock":
            policy = BaseStockPolicy(base_stock_level=pol["base_stock_level"])
        elif ptype == "sS":
            policy = SsPolicy(s=pol["s"], S=pol["S"])
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
        )

    # edges with seeded LTs
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

        edges[(e["from"], e["to"])] = Edge(
            parent=e["from"], child=e["to"], lead_time_sampler=sampler,
            share=e.get("share")
        )

    net = Network(nodes=nodes, edges=edges)

    # demand with seeded RNGs
    demand_by_node = {}
    for d in cfg.get("demand", []):
        node = d["node"]; g = d["generator"]
        d_seed = g.get("seed", top_seed)
        d_rng = random.Random(d_seed) if d_seed is not None else random.Random()

        if g["type"] == "deterministic":
            demand_by_node[node] = DeterministicDemand(g["value"]).sample
        elif g["type"] == "poisson":
            demand_by_node[node] = PoissonDemand(g["lam"], d_rng).sample
        else:
            raise ValueError("Unknown demand generator type")

    T = int(cfg["time_horizon"])
    return net, demand_by_node, T


def main():
    parser = argparse.ArgumentParser(description="Run supply chain sim and write CSV.")
    parser.add_argument("--config", type=str, default=os.path.join("config", "112.json"))
    parser.add_argument("--mode", type=str, default="both",
                        choices=["summary", "detailed", "both"],
                        help="What to emit into CSVs.")
    parser.add_argument("--outdir", type=str, default="outputs")
    args = parser.parse_args()

    net, demand_by_node, T = build_from_config(args.config)
    os.makedirs(args.outdir, exist_ok=True)

    if args.mode in ("detailed", "both"):
        sim = Simulator(network=net, demand_by_node=demand_by_node, T=T, order_processing_delay=1)
        metrics = sim.run(mode="detailed")
        df = pd.DataFrame([m.__dict__ for m in metrics])
        out = os.path.join(args.outdir, "opt_results_detailed.csv")
        df.to_csv(out, index=False)
        print(f"[detailed] wrote {out}")

    if args.mode in ("summary", "both"):
        sim2 = Simulator(network=net, demand_by_node=demand_by_node, T=T, order_processing_delay=1)
        metrics2 = sim2.run(mode="summary")
        df2 = pd.DataFrame([m.__dict__ for m in metrics2])
        out2 = os.path.join(args.outdir, "opt_results_summary.csv")
        df2.to_csv(out2, index=False)
        print(f"[summary] wrote {out2}")

if __name__ == "__main__":
    main()
