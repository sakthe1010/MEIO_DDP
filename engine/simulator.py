import numpy as np
import matplotlib.pyplot as plt
import os

class NetworkSimulator:
    def __init__(self, nodes, network, demand_dict, time_horizon, randomness=None):
        self.nodes = nodes
        self.network = network  # Accepts Network object
        self.demand_dict = demand_dict
        self.T = time_horizon
        self.randomness = randomness or {}

    def get_randomized_demand(self, name, t):
        base_demand = self.demand_dict.get(name, [0] * self.T)[t]
        if name in self.randomness:
            method = self.randomness[name].get("type", "normal")
            if method == "normal":
                std = self.randomness[name].get("std", 5)
                return max(0, int(np.random.normal(loc=base_demand, scale=std)))
            elif method == "poisson":
                return np.random.poisson(lam=base_demand)
        return base_demand

    def simulate(self):
        for t in range(self.T):
            true_demands = {}

            # Step 1: Retailer nodes process actual demand
            for name, node in self.nodes.items():
                if node.node_type == "retailer":
                    demand_today = self.get_randomized_demand(name, t)
                    node.step(t, demand=demand_today)
                    true_demands[name] = demand_today

            # Step 2: Upstream nodes aggregate child demand
            for name, node in self.nodes.items():
                if node.node_type != "retailer":
                    children = self.network.get_downstream(name)
                    downstream_demand = sum(true_demands.get(child, 0) for child in children)
                    node.step(t, demand=downstream_demand)
                    true_demands[name] = downstream_demand

            # Optional daily debug
            # print(f"Day {t+1}")
            # for name, node in self.nodes.items():
            #     print(f"{name}: Inv={node.inventory}, Orders={node.history['orders'][-1]}, Backorders={node.backorders}")

    def plot_inventory_levels(self):
        os.makedirs("visuals", exist_ok=True)
        plt.figure(figsize=(10, 6))
        for name, node in self.nodes.items():
            plt.plot(node.history["inventory"], label=name)
        plt.xlabel("Day")
        plt.ylabel("Inventory Level")
        plt.title("Inventory Levels Over Time")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig("visuals/inventory_plot.png")
        plt.close()

    def print_cost_summary(self):
        print("\n=== Cost Summary ===")
        for name, node in self.nodes.items():
            total_cost = sum(node.history["costs"])
            print(f"{name}: Total Cost = {total_cost:.2f}")

    def print_otif_summary(self):
        print("\n=== OTIF Summary ===")
        for name, node in self.nodes.items():
            if node.node_type != "retailer":
                continue
            otif_list = node.history.get("otif", [])
            if not otif_list:
                print(f"{name}: No OTIF data.")
                continue
            otif_rate = sum(otif_list) / len(otif_list) * 100
            print(f"{name}: OTIF = {otif_rate:.2f}%")
