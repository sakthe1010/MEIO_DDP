import numpy as np

class Node:
    def __init__(self, name, node_type, policy, initial_inventory=0, lead_time=1,
                 holding_cost=1.0, shortage_cost=5.0):
        self.name = name
        self.node_type = node_type  # "supplier" | "warehouse" | "retailer"
        self.policy = policy
        self.inventory = initial_inventory
        self.backorders = 0
        # shipments scheduled to arrive: list[(arrival_day, qty)]
        self.incoming_orders = []
        self.lead_time = lead_time
        self.holding_cost = holding_cost
        self.shortage_cost = shortage_cost

        self.history = {
            "inventory": [],
            "orders": [],     # order requests placed to parents (or external if supplier)
            "received": [],
            "demand": [],
            "shortages": [],
            "fulfilled": [],
            "otif": [],
            "costs": []
        }

    def get_lead_time(self):
        if isinstance(self.lead_time, dict):
            mean = self.lead_time.get("mean", 1)
            std = self.lead_time.get("std", 0)
            return max(1, int(np.random.normal(loc=mean, scale=std)))
        return self.lead_time

    def on_order(self, current_day):
        """Quantity already scheduled to arrive after current_day."""
        return sum(q for a, q in self.incoming_orders if a > current_day)

    def receive_orders(self, current_day):
        received_today = 0
        keep = []
        for arrival_day, qty in self.incoming_orders:
            if arrival_day == current_day:
                self.inventory += qty
                received_today += qty
            else:
                keep.append((arrival_day, qty))
        self.incoming_orders = keep
        self.history["received"].append(received_today)

    def fulfill_external_demand(self, demand):
        """For retailers only."""
        total = demand + self.backorders
        shipped = min(self.inventory, total)
        self.inventory -= shipped
        self.backorders = max(0, total - shipped)
        self.history["demand"].append(demand)
        self.history["fulfilled"].append(shipped)
        self.history["shortages"].append(self.backorders)
        self.history["otif"].append(1 if self.backorders == 0 else 0)

    def record_no_external_demand(self):
        """For warehouses/suppliers."""
        self.history["demand"].append(0)
        self.history["fulfilled"].append(0)
        self.history["shortages"].append(self.backorders)
        self.history["otif"].append(1 if self.backorders == 0 else 0)

    def request_order_qty(self, current_day):
        """
        Ask the policy how much to order (request from parents).
        Policies should be given INVENTORY POSITION (on-hand + on-order - backorders).
        """
        inv_pos = self.inventory + self.on_order(current_day) - self.backorders
        # Most simple policies only need one number; pass inv_pos.
        qty = 0
        if hasattr(self.policy, "decide_order"):
            qty = max(0, int(self.policy.decide_order(inv_pos)))
        self.history["orders"].append(qty)
        return qty

    def end_of_day_cost_book(self):
        self.history["inventory"].append(self.inventory)
        holding = self.inventory * self.holding_cost
        shortage = self.backorders * self.shortage_cost
        self.history["costs"].append(holding + shortage)
