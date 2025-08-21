import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from collections import deque

class NetworkSimulator:
    def __init__(self, nodes, network, demand_dict, time_horizon, randomness=None):
        self.nodes = nodes
        self.network = network
        self.demand_dict = demand_dict
        self.T = time_horizon
        self.randomness = randomness or {}

    def topological_sort(self):
        in_degree = {n: 0 for n in self.nodes}
        for u in self.nodes:
            for v in self.network.get_downstream(u):
                in_degree[v] += 1
        q = deque([n for n, d in in_degree.items() if d == 0])
        order = []
        while q:
            u = q.popleft()
            order.append(u)
            for v in self.network.get_downstream(u):
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    q.append(v)
        return order

    def _rand_demand(self, name, t):
        base = self.demand_dict.get(name, [0]*self.T)[t]
        r = self.randomness.get(name)
        if not r:
            return base
        if r.get("type", "normal") == "poisson":
            return np.random.poisson(lam=base)
        std = r.get("std", 5)
        return max(0, int(np.random.normal(base, std)))

    def simulate(self):
        order = self.topological_sort()

        for t in range(self.T):
            # 1) Receive all arrivals scheduled for today
            for node in self.nodes.values():
                node.receive_orders(t)

            # 2) External demand only at leaves (retailers)
            for name in order:
                node = self.nodes[name]
                children = self.network.get_downstream(name)
                is_leaf = len(children) == 0
                if is_leaf and node.node_type == "retailer":
                    d = self._rand_demand(name, t)
                    node.fulfill_external_demand(d)
                else:
                    node.record_no_external_demand()

            # 3) Each node decides how much to ORDER from its parents
            order_requests = {name: self.nodes[name].request_order_qty(t) for name in self.nodes}

            # 4) Parents allocate shipments to children proportional to children's requests
            for parent_name in order:
                parent = self.nodes[parent_name]
                children = self.network.get_downstream(parent_name)
                if not children:
                    continue

                # what each child asked for FROM THIS parent (simple split: equal share from each parent)
                child_requests = {}
                total_req = 0
                for child_name in children:
                    # If child has multiple parents, we assume it will try to split evenly
                    parents_of_child = self.network.get_upstream(child_name)
                    share = 1 / max(1, len(parents_of_child))
                    req = int(share * order_requests.get(child_name, 0))
                    child_requests[child_name] = req
                    total_req += req

                if total_req == 0:
                    continue

                available = parent.inventory
                # Allocate proportionally
                for child_name in children:
                    req = child_requests[child_name]
                    if req == 0 or available <= 0:
                        alloc = 0
                    else:
                        portion = req / total_req
                        alloc = min(int(round(portion * available)), req)
                    if alloc > 0:
                        parent.inventory -= alloc
                        arrival = t + parent.get_lead_time()
                        if arrival < self.T:
                            self.nodes[child_name].incoming_orders.append((arrival, alloc))

            # 5) Suppliers order from outside (external source)
            for name in order:
                node = self.nodes[name]
                if len(self.network.get_upstream(name)) == 0:
                    # root node(s) – buy externally
                    ext_buy = order_requests.get(name, 0)
                    if ext_buy > 0:
                        arrival = t + node.get_lead_time()
                        if arrival < self.T:
                            node.incoming_orders.append((arrival, ext_buy))

            # 6) Book costs & inventory snapshots
            for node in self.nodes.values():
                node.end_of_day_cost_book()

    def plot_inventory_levels(self):
        os.makedirs("visuals", exist_ok=True)
        plt.figure(figsize=(12, 6))
        names = list(self.nodes.keys())
        cmap = cm.get_cmap('tab10', len(names))
        for i, name in enumerate(names):
            inv = self.nodes[name].history["inventory"]
            plt.plot(inv, label=name, color=cmap(i), linewidth=1.6)
        plt.xlabel("Day"); plt.ylabel("Inventory Level")
        plt.title("Inventory Levels Over Time")
        plt.legend(loc='upper right'); plt.grid(True); plt.tight_layout()
        plt.savefig("visuals/inventory_plot.png")
        plt.close()

    def print_cost_summary(self):
        print("\n=== Cost Summary ===")
        for name, node in self.nodes.items():
            print(f"{name}: Total Cost = {sum(node.history['costs']):.2f}")

    def print_otif_summary(self):
        print("\n=== OTIF Summary ===")
        for name, node in self.nodes.items():
            if node.node_type != "retailer":
                continue
            otif = node.history["otif"]
            rate = 100 * sum(otif) / len(otif) if otif else 0.0
            print(f"{name}: OTIF = {rate:.2f}%")
