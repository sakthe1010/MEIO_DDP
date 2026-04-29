from dataclasses import dataclass
from policies.base_stock import BasePolicy


@dataclass
class RQPolicy(BasePolicy):
    """
    (R, Q) Reorder-Point / Fixed-Order-Quantity policy.

    Place an order of exactly Q units whenever inventory position (IP)
    falls at or below the reorder point R.

    IP = on_hand - backlog_external - backlog_children + pipeline_in

    Common in manufacturing where order quantities are fixed (e.g. a
    pallet, a production batch, a container load).

    Config example:
        "policy": {
            "SKU_A": {"type": "rq", "reorder_point": 40, "order_qty": 100}
        }
    """

    reorder_point: int   # R — trigger level
    order_quantity: int  # Q — fixed replenishment quantity

    def order_qty(self, on_hand, backlog_external, backlog_children, pipeline_in,
                  t=None):
        ip = on_hand - (backlog_external + backlog_children) + pipeline_in
        return self.order_quantity if ip <= self.reorder_point else 0
