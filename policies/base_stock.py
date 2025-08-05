class BaseStockPolicy:
    def __init__(self, base_stock_level):
        """
        Base-stock policy: order enough to restore inventory to base level.

        :param base_stock_level: Desired inventory level to maintain
        """
        self.base_stock_level = base_stock_level

    def decide_order(self, current_inventory):
        """
        Decide how much to order to reach base-stock level.

        :param current_inventory: Current inventory at the node
        :return: Quantity to order
        """
        order_quantity = max(0, self.base_stock_level - current_inventory)
        return order_quantity
