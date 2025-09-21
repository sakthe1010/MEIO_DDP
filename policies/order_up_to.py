from dataclasses import dataclass
from typing import Optional
from policies.base_stock import BasePolicy

@dataclass
class OrderUpToPolicy(BasePolicy):
    R: int                 # review period (e.g., weekly = 7)
    S: int                 # order-up-to target
    phase_offset: int = 0  # review happens when (t - phase_offset) % R == 0

    def order_qty(self, *, on_hand: int, backlog_external: int,
                  backlog_children: int, pipeline_in: int, t: Optional[int] = None) -> int:
        if t is None:
            # If simulator didn't pass time (older code), behave like base stock (always review)
            review_due = True
        else:
            review_due = ((t - self.phase_offset) % self.R) == 0

        if not review_due:
            return 0

        ip = on_hand - (backlog_external + backlog_children) + pipeline_in
        return max(0, self.S - ip)
