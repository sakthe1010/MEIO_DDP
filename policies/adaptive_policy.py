import math

class AdaptivePolicy:
    """
    Simple adaptive policy:
      forecast = avg(recent_demand_window)  (0 if no history yet)
      target   = cover_horizon * forecast
      order    = max(0, target - inventory)
    """
    def __init__(self, initial_inventory=None, cover_horizon=3, buffer_ratio=0.2):
        self.cover_horizon = int(cover_horizon)
        self.buffer_ratio = float(buffer_ratio)

    def decide_order(self, inventory, recent_demand=None):
        recent = list(recent_demand) if recent_demand is not None else []
        if len(recent) == 0:
            forecast = 0.0
        else:
            forecast = sum(recent) / len(recent)
        # add a small buffer
        target = (self.cover_horizon * forecast) * (1.0 + self.buffer_ratio)
        return max(0, int(round(target - float(inventory))))
