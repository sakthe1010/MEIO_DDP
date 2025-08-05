import json
import itertools
import csv
import matplotlib.pyplot as plt
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.node import Node
from engine.simulator import NetworkSimulator
from engine.network import Network
from policies.base_stock import BaseStockPolicy
from policies.ss_policy import SsPolicy
from policies.adaptive_policy import AdaptivePolicy

def load_template_config(path="config/sample_network.json"):
    with open(path, "r") as f:
        return json.load(f)
      
def run_simulation_with_config(config):
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
            policy = AdaptivePolicy(cfg["initial_inventory"], buffer_ratio=cfg.get("buffer_ratio", 0.2))
        else:
            raise ValueError(f"Unknown policy: {policy_type}")

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

    total_cost = sum(sum(node.history["costs"]) for node in nodes.values())
    otif = nodes["Retailer"].history["otif"]
    otif_rate = sum(otif) / len(otif) * 100 if otif else 0.0
    return total_cost, otif_rate

def optimize():
    config_template = load_template_config()

    base_stock_range = [200, 250, 300, 350, 400]
    ss_range = [(20, 60), (30, 70), (35, 75), (40, 80), (45, 85)]
    buffer_ratios = [0.1, 0.2, 0.3, 0.4, 0.5]

    best_config = None
    best_cost = float('inf')
    results = []

    print("Running optimization loop...\n")

    for bs, (s, S), buf in itertools.product(base_stock_range, ss_range, buffer_ratios):
        config = json.loads(json.dumps(config_template))  # deep copy

        for node_cfg in config["nodes"]:
            if node_cfg["name"] == "Supplier":
                node_cfg["base_stock_level"] = bs
            elif node_cfg["name"] == "Warehouse":
                node_cfg["policy"] = "adaptive"
                node_cfg["buffer_ratio"] = buf
            elif node_cfg["name"] == "Retailer":
                node_cfg["s"] = s
                node_cfg["S"] = S

        total_cost, otif_rate = run_simulation_with_config(config)

        results.append({
            "base_stock": bs,
            "s": s,
            "S": S,
            "buffer_ratio": buf,
            "cost": total_cost,
            "otif": otif_rate
        })

        if otif_rate >= 95 and total_cost < best_cost:
            best_cost = total_cost
            best_config = results[-1]

        print(f"[bs={bs}, s={s}, S={S}, buf={buf:.2f}] => Cost = {total_cost:.2f}, OTIF = {otif_rate:.2f}%")

    # Save CSV
    with open("outputs/opt_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # Plot
    plt.figure(figsize=(10, 6))
    for r in results:
        plt.scatter(r["cost"], r["otif"], color="blue")
        plt.text(r["cost"], r["otif"] + 0.2, f'{r["s"]}/{r["S"]}', fontsize=8)
    plt.xlabel("Total Cost")
    plt.ylabel("OTIF (%)")
    plt.title("Cost vs OTIF")
    plt.grid(True)
    plt.savefig("visuals/cost_vs_otif.png")
    plt.close()

    print("\nBest Configuration Found:")
    print(json.dumps(best_config, indent=2))

if __name__ == "__main__":
    optimize()  
