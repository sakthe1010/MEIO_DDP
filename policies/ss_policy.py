class SsPolicy:
    def __init__(self, s, S):
        """
        (s, S) Policy: Order only when inventory < s, and then order up to S
        :param s: reorder point
        :param S: order-up-to level
        """
        assert S >= s, "S must be >= s"
        self.s = s
        self.S = S

    def decide_order(self, current_inventory):
        if current_inventory < self.s:
            return self.S - current_inventory
        return 0
