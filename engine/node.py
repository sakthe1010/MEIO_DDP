from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Callable, Optional

@dataclass
class Shipment:
    arrival_time: int
    sku: str
    qty: int

@dataclass
class IncomingOrder:
    child_id: str
    sku: str
    qty: int

class Node:

    def __init__(
        self,
        node_id: str,
        node_type: str,  # 'supplier'|'warehouse'|'retailer'
        policies: Dict[str, object] = None,   # policy per SKU
        skus: List[str] = None,
        policy = None,  # legacy single policy (deprecated)
        initial_inventory: Optional[Dict[str, int]] = None,
        holding_cost: object = 0.0,   # accepts float OR Dict[str, float]
        shortage_cost: object = 0.0,
        infinite_supply: bool = False,
        order_cost_fixed: float = 0.0,
        order_cost_per_unit: float = 0.0,
    ):

        # -----------------------------
        # Static attributes
        # -----------------------------
        self.node_id = node_id
        self.node_type = node_type
        self.policies = policies
        self.skus = skus

        self.holding_cost = holding_cost
        self.shortage_cost = shortage_cost
        self.infinite_supply = infinite_supply
        self.order_cost_fixed = order_cost_fixed
        self.order_cost_per_unit = order_cost_per_unit

        # Backward compatibility for single-policy tests
        # Backward compatibility for single-policy tests
        if policy is not None:
            self.skus = ["SKU1"]
            self.policies = {"SKU1": policy}
            skus = self.skus        # keep local var in sync for lines below
            policies = self.policies
            if isinstance(initial_inventory, int):
                initial_inventory = {"SKU1": initial_inventory}

        # holding_cost
        if isinstance(holding_cost, dict):
            self.holding_cost: Dict[str, float] = {sku: float(holding_cost.get(sku, 0.0)) for sku in skus}
        else:
            self.holding_cost: Dict[str, float] = {sku: float(holding_cost) for sku in skus}

        # shortage_cost
        if isinstance(shortage_cost, dict):
            self.shortage_cost: Dict[str, float] = {sku: float(shortage_cost.get(sku, 0.0)) for sku in skus}
        else:
            self.shortage_cost: Dict[str, float] = {sku: float(shortage_cost) for sku in skus}

        


        # -----------------------------
        # Initial inventory
        # -----------------------------
        if initial_inventory is None:
            initial_inventory = {}

        self.on_hand: Dict[str, int] = {
            sku: int(initial_inventory.get(sku, 0))
            for sku in skus
        }

        # -----------------------------
        # Backlogs
        # -----------------------------
        self.backlog_external: Dict[str, int] = {
            sku: 0 for sku in skus
        }

        # backlog_children[(child_id, sku)] = qty
        self.backlog_children: Dict[Tuple[str, str], int] = {}

        # -----------------------------
        # Pipeline
        # -----------------------------
        self.pipeline_in: List[Shipment] = []

        # -----------------------------
        # Incoming child orders
        # -----------------------------
        self.inbound_orders_queue: List[IncomingOrder] = []

        # placed but not yet shipped
        self.placed_orders: Dict[str, int] = {
            sku: 0 for sku in skus
        }

    # ============================================================
    # Aggregation Helpers (SKU-aware)
    # ============================================================

    def total_pipeline_in(self, sku: str) -> int:
        return sum(s.qty for s in self.pipeline_in if s.sku == sku)

    def total_backlog_children(self, sku: str) -> int:
        return sum(
            qty for (child, s), qty in self.backlog_children.items()
            if s == sku
        )

    # ============================================================
    # Shipment Arrival
    # ============================================================

    def receive_shipments(self, t: int) -> Dict[str, int]:

        arrived = {sku: 0 for sku in self.skus}
        keep = []

        for s in self.pipeline_in:
            if s.arrival_time == t:
                arrived[s.sku] += s.qty
            else:
                keep.append(s)

        self.pipeline_in = keep

        for sku in self.skus:
            self.on_hand[sku] += arrived[sku]

        return arrived

    # ============================================================
    # External Demand (Retailer only)
    # ============================================================

    def process_external_demand(
        self,
        sku: str,
        demand_qty: int
    ) -> Tuple[int, int]:

        demand_qty = max(0, int(demand_qty))

        fulfilled = min(self.on_hand[sku], demand_qty)
        self.on_hand[sku] -= fulfilled

        unfilled = demand_qty - fulfilled

        if unfilled > 0:
            self.backlog_external[sku] += unfilled

        return fulfilled, unfilled

    # ============================================================
    # Add inbound order (from child)
    # ============================================================

    def add_inbound_order(
        self,
        child_id: str,
        sku: str,
        qty: int
    ):
        self.inbound_orders_queue.append(
            IncomingOrder(child_id=child_id, sku=sku, qty=qty)
        )

    # ============================================================
    # Process Child Orders (Fully SKU-Aware)
    # ============================================================

    def process_child_orders(
        self,
        t: int,
        child_nodes: Dict[str, "Node"],
        lead_time_sampler_by_child: Dict[str, Callable[[], int]],
        on_ship: Optional[
            Callable[[str, str, str, int, int, int], None]
        ] = None,
        transport_constraint_fn=None
    ) -> Dict[Tuple[str, str], int]:

        """
        Serve children backlog + today's orders.
        Returns shipped qty per (child_id, sku).
        """

        shipped = {}

        # --------------------------------------------------------
        # Merge today's incoming orders
        # --------------------------------------------------------
        incoming = {}

        for o in self.inbound_orders_queue:
            key = (o.child_id, o.sku)
            incoming[key] = incoming.get(key, 0) + o.qty

        self.inbound_orders_queue.clear()

        # --------------------------------------------------------
        # Determine all (child, sku) needing service
        # --------------------------------------------------------
        keys = set(self.backlog_children.keys()) | set(incoming.keys())

        for (child, sku) in keys:

            need = (
                self.backlog_children.get((child, sku), 0)
                + incoming.get((child, sku), 0)
            )

            if need <= 0:
                continue

            if self.infinite_supply:
                ship = need
            else:
                ship = min(self.on_hand[sku], need)

            # ----------------------------------------------------
            # Transport constraint (still per SKU for now)
            # ----------------------------------------------------

            # DEBUG (keep available if needed)
            # print(f"[DEBUG] Node {self.node_id} → {child} SKU {sku}: need={need}, ship={ship}")

            if ship > 0:

                if not self.infinite_supply:
                    self.on_hand[sku] -= ship

                L = int(lead_time_sampler_by_child[child]())
                arrival = t + L if L > 0 else t + 1

                child_nodes[child].pipeline_in.append(
                    Shipment(
                        arrival_time=arrival,
                        sku=sku,
                        qty=ship
                    )
                )

                shipped[(child, sku)] = ship

                if on_ship:
                    on_ship(
                        self.node_id,
                        child,
                        sku,
                        t,
                        L,
                        ship
                    )

            remaining = need - ship

            if remaining > 0:
                self.backlog_children[(child, sku)] = remaining
            elif (child, sku) in self.backlog_children:
                del self.backlog_children[(child, sku)]

        return shipped
