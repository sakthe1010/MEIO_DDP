import json, os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.node import Node
from engine.simulator import NetworkSimulator
from engine.network import Network
from policies.base_stock import BaseStockPolicy
from policies.ss_policy import SsPolicy

def load_config(path="config/sample_network_123.json"):
    with open(path, "r") as f:
        return json.load(f)

def make_policy(cfg):
    if cfg["policy"] == "base_stock":
        return BaseStockPolicy(cfg["base_stock_level"])
    if cfg["policy"] == "ss":
        return SsPolicy(cfg["s"], cfg["S"])
    raise ValueError("Only 'base_stock' and 'ss' are supported.")

def main():
    config = load_config()
    net = Network(config["edges"])
    nodes = {}
    for nc in config["nodes"]:
        nodes[nc["name"]] = Node(
            name=nc["name"],
            node_type=nc["node_type"],
            policy=make_policy(nc),
            initial_inventory=nc["initial_inventory"],
            lead_time=nc["lead_time"],
            holding_cost=nc.get("holding_cost", 1.0),
            shortage_cost=nc.get("shortage_cost", 5.0),
        )
    sim = NetworkSimulator(
        nodes, net,
        demand_dict=config.get("demand", {}),
        time_horizon=config["time_horizon"],
        randomness=config.get("randomness", {})
    )
    sim.simulate()
    sim.plot_inventory_levels()
    sim.print_cost_summary()
    sim.print_otif_summary()

if __name__ == "__main__":
    main()
