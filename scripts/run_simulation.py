import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.node import Node
from engine.simulator import NetworkSimulator
from engine.network import Network
from policies.base_stock import BaseStockPolicy
from policies.ss_policy import SsPolicy
from policies.adaptive_policy import AdaptivePolicy

def load_config(path="config/sample_network.json"):
    with open(path, "r") as f:
        return json.load(f)

def main():
    config = load_config()
    T = config["time_horizon"]
    edges = config["edges"]
    network = Network(edges)

    nodes = {}
    for cfg in config["nodes"]:
        policy_type = cfg["policy"]
        if policy_type == "base_stock":
            policy = BaseStockPolicy(cfg["base_stock_level"])
        elif policy_type == "ss":
            policy = SsPolicy(cfg["s"], cfg["S"])
        elif policy_type == "adaptive":
            policy = AdaptivePolicy(cfg["initial_inventory"])
        else:
            raise ValueError(f"Unsupported policy: {policy_type}")

        node = Node(
            name=cfg["name"],
            node_type=cfg["node_type"],
            policy=policy,
            initial_inventory=cfg["initial_inventory"],
            lead_time=cfg["lead_time"],
            holding_cost=cfg.get("holding_cost", 1.0),
            shortage_cost=cfg.get("shortage_cost", 5.0)
        )
        nodes[cfg["name"]] = node

    demand = config.get("demand", {})
    randomness = config.get("randomness", {})

    simulator = NetworkSimulator(nodes, network, demand, T, randomness)
    simulator.simulate()
    simulator.plot_inventory_levels()
    simulator.print_cost_summary()
    simulator.print_otif_summary()

if __name__ == "__main__":
    main()
