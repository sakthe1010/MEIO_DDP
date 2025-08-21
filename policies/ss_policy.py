class SsPolicy:
    def __init__(self, s, S):
        self.s = int(s)
        self.S = int(S)

    def decide_order(self, inventory, recent_demand=None):
        inv = int(inventory)
        return max(0, int(self.S - inv)) if inv <= self.s else 0
