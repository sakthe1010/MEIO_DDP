import numpy as np
from policies.adaptive_policy import AdaptivePolicy  # For instance checks

class Node:
    def __init__(self, name, node_type, policy, initial_inventory=0, lead_time=1,
                 holding_cost=1.0, shortage_cost=5.0):
        self.name = name
        self.node_type = node_type
        self.policy = policy
        self.inventory = initial_inventory
        self.backorders = 0
        self.incoming_orders = []  # List of (arrival_day, quantity)
        self.lead_time = lead_time
        self.holding_cost = holding_cost
        self.shortage_cost = shortage_cost

        self.history = {
            "inventory": [],
            "orders": [],
            "received": [],
            "demand": [],
            "shortages": [],
            "fulfilled": [],
            "otif": [],
            "costs": []
        }

    def get_lead_time(self):
        """Returns lead time — either fixed or sampled from distribution"""
        if isinstance(self.lead_time, dict):
            mean = self.lead_time.get("mean", 1)
            std = self.lead_time.get("std", 0)
            return max(1, int(np.random.normal(loc=mean, scale=std)))
        return self.lead_time

    def receive_orders(self, current_day):
        received_today = 0
        remaining_orders = []
        for arrival_day, quantity in self.incoming_orders:
            if arrival_day == current_day:
                self.inventory += quantity
                received_today += quantity
            else:
                remaining_orders.append((arrival_day, quantity))
        self.incoming_orders = remaining_orders
        self.history["received"].append(received_today)

    def fulfill_demand(self, demand):
        total_demand = demand + self.backorders
        fulfilled = min(self.inventory, total_demand)
        self.inventory -= fulfilled
        self.backorders = max(0, total_demand - fulfilled)

        self.history["demand"].append(demand)
        self.history["fulfilled"].append(fulfilled)
        self.history["shortages"].append(self.backorders)
        self.history["otif"].append(1 if self.backorders == 0 else 0)

    def place_order(self, current_day):
        if isinstance(self.policy, AdaptivePolicy):
            recent_demand = self.history["demand"]
            order_qty = self.policy.decide_order(self.inventory, recent_demand)
        else:
            order_qty = self.policy.decide_order(self.inventory)

        lead_time_days = self.get_lead_time()
        arrival_day = current_day + lead_time_days
        self.incoming_orders.append((arrival_day, order_qty))
        self.history["orders"].append(order_qty)

    def step(self, current_day, demand=0):
        self.receive_orders(current_day)

        if self.node_type == "retailer":
            self.fulfill_demand(demand)
        else:
            self.history["demand"].append(demand)  # For upstream nodes

        self.place_order(current_day)

        self.history["inventory"].append(self.inventory)
        holding_cost = self.inventory * self.holding_cost
        shortage_cost = self.backorders * self.shortage_cost
        total_cost = holding_cost + shortage_cost
        self.history["costs"].append(total_cost)
