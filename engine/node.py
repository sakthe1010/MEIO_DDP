# engine/node.py
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Callable, Optional

@dataclass
class Shipment:
    arrival_time: int
    qty: int

@dataclass
class IncomingOrder:
    child_id: str
    qty: int

@dataclass
class Node:
    node_id: str
    node_type: str  # 'supplier'|'warehouse'|'retailer'
    policy: object  # BasePolicy-like
    initial_inventory: int = 0
    holding_cost: float = 0.0
    shortage_cost: float = 0.0
    infinite_supply: bool = False  # set True for supplier if desired

    # dynamic state
    on_hand: int = field(init=False)
    backlog_external: int = 0                 # retailer only
    backlog_children: Dict[str, int] = field(default_factory=dict)  # per child
    pipeline_in: List[Shipment] = field(default_factory=list)       # shipments en route TO this node
    inbound_orders_queue: List[IncomingOrder] = field(default_factory=list)  # child orders to process

    def __post_init__(self):
        self.on_hand = self.initial_inventory

    def total_pipeline_in(self) -> int:
        return sum(s.qty for s in self.pipeline_in)

    def total_backlog_children(self) -> int:
        return sum(self.backlog_children.values()) if self.backlog_children else 0

    def receive_shipments(self, t: int) -> int:
        """Move shipments whose arrival_time == t into on_hand."""
        arrived = 0
        keep = []
        for s in self.pipeline_in:
            if s.arrival_time == t:
                arrived += s.qty
            else:
                keep.append(s)
        self.pipeline_in = keep
        self.on_hand += arrived
        return arrived

    def process_external_demand(self, demand_qty: int) -> Tuple[int, int]:
        """Retailer only: serve current period's demand; backlog remainder.
        NOTE: backlog from prior periods should be cleared *before* calling this (simulator does it)."""
        # ✅ BUGFIX #1: clip weird/negative inputs so they can't inflate on_hand
        demand_qty = max(0, int(demand_qty))
        fulfilled = min(self.on_hand, demand_qty)
        self.on_hand -= fulfilled
        unfilled = demand_qty - fulfilled
        if unfilled > 0:
            self.backlog_external += unfilled
        return fulfilled, unfilled

    def add_inbound_order(self, child_id: str, qty: int):
        self.inbound_orders_queue.append(IncomingOrder(child_id=child_id, qty=qty))

    def process_child_orders(
        self, t: int,
        child_nodes: Dict[str, "Node"],
        lead_time_sampler_by_child: Dict[str, Callable[[], int]],
        on_ship: Optional[Callable[[str, str, int, int, int], None]] = None,  # (parent, child, t, L, qty)
    ) -> Dict[str, int]:
        """
        Serve children (backlog + today's new orders). Schedule shipments to child's pipeline_in.
        Returns shipped qty per child. If on_ship is provided, calls it for each shipment.
        """
        shipped = {}

        # merge today's incoming orders per child
        incoming = {}
        for o in self.inbound_orders_queue:
            incoming[o.child_id] = incoming.get(o.child_id, 0) + o.qty
        self.inbound_orders_queue.clear()

        # union of children that might need serving
        children = set(child_nodes.keys()) | set(self.backlog_children.keys()) | set(incoming.keys())

        for child in children:
            need = self.backlog_children.get(child, 0) + incoming.get(child, 0)
            if need <= 0:
                continue

            if self.infinite_supply:
                ship = need
            else:
                ship = min(self.on_hand, need)

            if ship > 0:
                if not self.infinite_supply:
                    self.on_hand -= ship
                L = int(lead_time_sampler_by_child[child]())
                # ✅ BUGFIX #2: avoid same-day arrivals getting “lost”; earliest arrival is next day
                arrival = t + max(1, L)
                child_nodes[child].pipeline_in.append(Shipment(arrival_time=arrival, qty=ship))
                shipped[child] = ship
                if on_ship:
                    on_ship(self.node_id, child, t, L, ship)

            remaining = need - ship
            if remaining > 0:
                self.backlog_children[child] = remaining
            elif child in self.backlog_children:
                del self.backlog_children[child]

        return shipped
