class AdaptivePolicy:
    def __init__(self, initial_level, buffer_ratio=0.2):
        self.level = initial_level
        self.buffer_ratio = buffer_ratio

    def decide_order(self, current_inventory, recent_demand):
        avg_demand = sum(recent_demand[-7:]) / min(len(recent_demand), 7) if recent_demand else self.level
        desired_level = int(avg_demand * (1 + self.buffer_ratio))
        order_qty = max(0, desired_level - current_inventory)
        return order_qty
