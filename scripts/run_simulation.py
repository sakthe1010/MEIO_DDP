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
        # Knuth’s algorithm (integer-valued, uses our seeded RNG)
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
        # round to nearest int, lower-bounded at 0
        return max(0, int(round(self.rng.gauss(self.mean, self.std))))

def build_from_config(cfg_or_path):
    import os, json
    if isinstance(cfg_or_path, (str, os.PathLike)):
        with open(cfg_or_path, "r") as f:
            cfg = json.load(f)
    elif isinstance(cfg_or_path, dict):
        cfg = cfg_or_path
    else:
        raise TypeError("build_from_config expects a path or a dict")

    # Optional top-level seed for convenience; specific seeds override it
    top_seed = cfg.get("seed", None)

    # nodes (same as before) ...
    nodes = {}
    for nd in cfg["nodes"]:
        pol = nd.get("policy", {})
        ptype = pol.get("type", "base_stock")
        if ptype == "base_stock":
            from policies.base_stock import BaseStockPolicy
            policy = BaseStockPolicy(base_stock_level=pol["base_stock_level"])
        elif ptype == "sS":
            from policies.ss_policy import SsPolicy
            policy = SsPolicy(s=pol["s"], S=pol["S"])
        else:
            raise ValueError(f"Unknown policy type {ptype}")

        from engine.node import Node
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
    from engine.network import Network, Edge
    edges = {}
    for e in cfg["edges"]:
        lt = e["lead_time"]
        # choose RNG for this edge
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
            share=e.get("share")  # harmless if you didn't implement multi-parent
        )

    net = Network(nodes=nodes, edges=edges)

    # demand with seeded RNGs
    demand_by_node = {}
    for d in cfg.get("demand", []):
        node = d["node"]; g = d["generator"]
        # choose RNG for this demand stream
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
    cfg_path = os.path.join("config", "111_poisson_normal.json")
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
