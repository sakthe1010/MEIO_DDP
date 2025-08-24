import json
import os
import pandas as pd

from engine.node import Node
from engine.network import Network, Edge
from engine.simulator import Simulator
from policies.base_stock import BaseStockPolicy
from policies.ss_policy import SsPolicy

# demand/lead-time generators (inline for brevity)
from dataclasses import dataclass
import math, random

class DemandGenerator:
    def sample(self, t: int) -> int: raise NotImplementedError

@dataclass
class DeterministicDemand(DemandGenerator):
    value: int
    def sample(self, t): return int(self.value)

@dataclass
class PoissonDemand(DemandGenerator):
    lam: float
    def sample(self, t):
        L = math.exp(-self.lam); k = 0; p = 1.0
        while p > L:
            k += 1; p *= random.random()
        return k - 1

class LeadTimeGenerator:
    def sample(self) -> int: raise NotImplementedError

@dataclass
class DeterministicLeadTime(LeadTimeGenerator):
    value: int
    def sample(self): return int(self.value)

@dataclass
class NormalIntLeadTime(LeadTimeGenerator):
    mean: float; std: float
    def sample(self): return max(0, int(round(random.gauss(self.mean, self.std))))

def build_from_config(cfg_path: str):
    with open(cfg_path, "r") as f:
        cfg = json.load(f)

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

    # edges
    edges = {}
    for e in cfg["edges"]:
        lt = e["lead_time"]
        if lt["type"] == "deterministic":
            sampler = DeterministicLeadTime(lt["value"]).sample
        elif lt["type"] == "normal_int":
            sampler = NormalIntLeadTime(lt["mean"], lt["std"]).sample
        else:
            raise ValueError("Unknown lead time type")
        edges[(e["from"], e["to"])] = Edge(parent=e["from"], child=e["to"], lead_time_sampler=sampler)

    net = Network(nodes=nodes, edges=edges)

    # demand
    demand_by_node = {}
    for d in cfg.get("demand", []):
        node = d["node"]; g = d["generator"]
        if g["type"] == "deterministic":
            demand_by_node[node] = DeterministicDemand(g["value"]).sample
        elif g["type"] == "poisson":
            demand_by_node[node] = PoissonDemand(g["lam"]).sample
        else:
            raise ValueError("Unknown demand generator type")

    return net, demand_by_node, int(cfg["time_horizon"])

def main():
    cfg_path = os.path.join("config", "123.json")
    net, demand_by_node, T = build_from_config(cfg_path)
    sim = Simulator(network=net, demand_by_node=demand_by_node, T=T, order_processing_delay=1)
    metrics = sim.run()
    df = pd.DataFrame([m.__dict__ for m in metrics])
    os.makedirs("outputs", exist_ok=True)
    out = os.path.join("outputs", "opt_results.csv")
    df.to_csv(out, index=False)
    print(f"Simulation complete. Wrote {out}")
    print(df.head(12))

if __name__ == "__main__":
    main()
