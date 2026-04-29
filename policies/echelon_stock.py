from dataclasses import dataclass
from typing import Optional
from policies.base_stock import BasePolicy


@dataclass
class EchelonStockPolicy(BasePolicy):
    """
    Echelon Base-Stock Policy (Clark & Scarf, 1960).

    Orders to keep echelon inventory position at or above S_e.

    Echelon inventory position (EIP) for node i =
        on_hand_i + pipeline_in_i + sum over all downstream nodes j:
            (on_hand_j + pipeline_in_j) - backlog_external_i

    In the simulator the caller computes EIP and passes it as
    `pipeline_in` (the echelon-aware version). The policy itself is
    then identical to a base-stock policy — the distinction is entirely
    in how the inventory position is measured.

    Usage:
        In config, set "type": "echelon_stock" with "echelon_base_stock_level".
        The simulator/experiment runner must compute EIP before calling order_qty.

    Academic reference:
        Clark, A.J., Scarf, H. (1960). Optimal policies for a multi-echelon
        inventory problem. Management Science, 6(4), 475–490.

    Config example:
        "policy": {
            "SKU_A": {
                "type": "echelon_stock",
                "echelon_base_stock_level": 150
            }
        }
    """

    echelon_base_stock_level: int

    def order_qty(self, on_hand, backlog_external, backlog_children, pipeline_in,
                  t: Optional[int] = None):
        # pipeline_in here should be the full echelon inventory position
        # (computed by the simulator using downstream state).
        # If called naively without echelon adjustment, it degrades gracefully
        # to a standard base-stock policy.
        eip = on_hand - (backlog_external + backlog_children) + pipeline_in
        return max(0, self.echelon_base_stock_level - eip)
