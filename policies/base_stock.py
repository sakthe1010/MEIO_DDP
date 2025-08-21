class BaseStockPolicy:
    def __init__(self, base_stock_level):
        self.B = int(base_stock_level)

    # accept optional recent_demand to keep a uniform signature
    def decide_order(self, inventory, recent_demand=None):
        return max(0, int(self.B - inventory))
