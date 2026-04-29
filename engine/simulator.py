from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from engine.network import Network
from engine.node import Node, Shipment
from engine.transport import TransportPlanner, VehicleLoad
from policies.echelon_stock import EchelonStockPolicy


# ============================================================
# Metrics now SKU-aware
# ============================================================

@dataclass
class MetricsRow:
    t: int
    node_id: str
    sku: str
    on_hand: int
    backlog_external: int
    backlog_children: int
    pipeline_in: int
    orders_to_parent: int
    received: int
    phase: str = "EOD"
    demand: int = 0
    fulfilled_external: int = 0
    holding_cost: float = 0.0
    backlog_cost: float = 0.0
    ordering_cost: float = 0.0
    transport_cost: float = 0.0
    total_cost: float = 0.0


@dataclass
class Simulator:
    network: Network
    demand_by_node: Dict[str, Dict[str, callable]]  # node -> sku -> demand_fn
    T: int
    order_processing_delay: int = 1
    volume_per_unit: Dict[str, float] = field(default_factory=dict)

    weight_per_unit: Dict[str, float] = field(default_factory=dict)
    metrics: List[MetricsRow] = field(default_factory=list)
    inventory_log: List[Dict] = field(default_factory=list)
    orders_log: List[Dict] = field(default_factory=list)
    shipments_log: List[Dict] = field(default_factory=list)
    pending_dispatch: Dict[Tuple[str, str], Dict[str, float]] = field(default_factory=dict)
    pending_dispatch_time: Dict[Tuple[str, str], int] = field(default_factory=dict)
    max_dispatch_wait: int = 3
    # disruptions: list of {"node_id": str, "start": int, "end": int}
    # During [start, end) the node cannot ship anything (supply disruption).
    disruptions: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        # Build planner with weight awareness after all fields are set
        self.planner = TransportPlanner(weight_per_unit=self.weight_per_unit)
    # ============================================================
    # MAIN RUN
    # ============================================================

    def run(self, mode: str = "summary") -> List[MetricsRow]:

        topo = self._topological_order()

        # parent_id -> list of (process_time, child_id, sku, qty)
        orders_waiting: Dict[str, List[Tuple[int, str, str, int]]] = {}

        for t in range(self.T):

            # -------------------------------
            # DAILY TRACKERS
            # -------------------------------
            received_today = {}
            orders_today = {}
            ordering_cost_today = {}
            transport_cost_today = {}

            for nid in self.network.nodes:
                node = self.network.nodes[nid]
                received_today[nid] = {sku: 0 for sku in node.skus}
                orders_today[nid] = {sku: 0 for sku in node.skus}
                ordering_cost_today[nid] = {sku: 0.0 for sku in node.skus}
                transport_cost_today[nid] = {sku: 0.0 for sku in node.skus}

            # =====================================================
            # 1) ARRIVALS
            # =====================================================

            for nid in topo:
                node = self.network.nodes[nid]
                rec_dict = node.receive_shipments(t)

                for sku in node.skus:
                    received_today[nid][sku] = rec_dict[sku]

            # =====================================================
            # 1a) CLEAR EXTERNAL BACKLOG
            # =====================================================

            for nid in topo:
                node = self.network.nodes[nid]

                if node.node_type == "retailer":

                    for sku in node.skus:
                        if node.backlog_external[sku] > 0 and node.on_hand[sku] > 0:
                            served = min(node.on_hand[sku], node.backlog_external[sku])
                            node.on_hand[sku] -= served
                            node.backlog_external[sku] -= served

            # =====================================================
            # 2) EXTERNAL DEMAND
            # =====================================================

            demand_today = {}
            fulfilled_today = {}

            for nid in topo:
                node = self.network.nodes[nid]
                demand_today[nid] = {}
                fulfilled_today[nid] = {}

                if node.node_type == "retailer":

                    for sku in node.skus:

                        dgen = self.demand_by_node.get(nid, {}).get(sku, None)
                        demand = int(dgen(t)) if dgen else 0

                        fulfilled, _ = node.process_external_demand(sku, demand)

                        demand_today[nid][sku] = demand
                        fulfilled_today[nid][sku] = fulfilled
                else:
                    for sku in node.skus:
                        demand_today[nid][sku] = 0
                        fulfilled_today[nid][sku] = 0

            # =====================================================
            # 3) PROCESS CHILD ORDERS
            # =====================================================

            due = {}

            for pid, lst in list(orders_waiting.items()):
                take = [(c, sku, q) for (tt, c, sku, q) in lst if tt == t]
                if take:
                    due[pid] = take

                orders_waiting[pid] = [(tt, c, sku, q) for (tt, c, sku, q) in lst if tt != t]
                if not orders_waiting[pid]:
                    del orders_waiting[pid]

            for parent_id, items in due.items():

                parent = self.network.nodes[parent_id]

                # Skip shipping if this node is currently disrupted
                disrupted = any(
                    d["node_id"] == parent_id and d["start"] <= t < d["end"]
                    for d in self.disruptions
                )
                if disrupted:
                    # Orders accumulate as backlog — will be served once disruption ends
                    for (child, sku, q) in items:
                        parent.add_inbound_order(child, sku, q)
                    continue

                for (child, sku, q) in items:
                    parent.add_inbound_order(child, sku, q)

                child_nodes = {c: self.network.nodes[c] for c in self.network.children(parent_id)}
                lt_map = self.network.lead_time_sampler_by_child(parent_id)

                def _on_ship(p, c, sku, tt, qty):
                    child_node = self.network.nodes[c]
                    child_node.placed_orders[sku] = max(
                        0,
                        child_node.placed_orders[sku] - qty
                    )


                shipped = parent.process_child_orders(
                    t,
                    child_nodes,
                    lt_map,
                    on_ship=_on_ship
                )

                # Charge transport cost
                # shipped_by_child: Dict[str, Dict[str, float]] = {}
                # for (child, sku), ship_qty in shipped.items():
                #     shipped_by_child.setdefault(child, {})[sku] = float(ship_qty)

                # for child, sku_qtys in shipped_by_child.items():
                #     sku_volumes = {
                #         sku: qty * self.volume_per_unit.get(sku, 1.0)
                #         for sku, qty in sku_qtys.items()
                #     }
                #     options = self.network.get_transport_options(parent_id, child)
                #     loads = self.planner.plan(quantities=sku_volumes, options=options)
                #     for load in loads:
                #         for sku, sku_cost in load.cost_by_sku.items():
                #             transport_cost_today[parent_id][sku] += sku_cost

                # Accumulate shipped quantities into pending dispatch buffer
                for (child, sku), ship_qty in shipped.items():
                    lane = (parent_id, child)
                    self.pending_dispatch.setdefault(lane, {})
                    self.pending_dispatch[lane][sku] = (
                        self.pending_dispatch[lane].get(sku, 0.0) + float(ship_qty)
                    )
            # =====================================================
            # 3b) DISPATCH PENDING SHIPMENTS (ALL LANES EVERY DAY)
            # =====================================================

            for parent_id in self.network.nodes:
                for child in self.network.children(parent_id):
                    lane = (parent_id, child)
                    pending = self.pending_dispatch.get(lane, {})
                    if not pending or all(v <= 0 for v in pending.values()):
                        continue

                    options = self.network.get_transport_options(parent_id, child)
                    if not options:
                        continue

                    opt = sorted(options, key=lambda o: o.mode)[0]
                    min_util = opt.min_dispatch_utilization

                    # Track how long this lane has been waiting
                    wait = self.pending_dispatch_time.get(lane, 0)
                    self.pending_dispatch_time[lane] = wait + 1

                    if min_util > 0.0:
                        total_pending_vol = sum(
                            qty * self.volume_per_unit.get(sku, 1.0)
                            for sku, qty in pending.items()
                        )
                        current_util = total_pending_vol / opt.capacity
                        # Force dispatch after max_dispatch_wait days — prevents indefinite blocking
                        force = self.pending_dispatch_time.get(lane, 0) >= self.max_dispatch_wait
                        if current_util < min_util and not force:
                            continue

                    # Threshold met (or forced) — physically dispatch now
                    sku_volumes = {
                        sku: qty * self.volume_per_unit.get(sku, 1.0)
                        for sku, qty in pending.items()
                        if qty > 0
                    }
                    loads = self.planner.plan(quantities=sku_volumes, options=options)
                    for load in loads:
                        for sku, sku_cost in load.cost_by_sku.items():
                            transport_cost_today[parent_id][sku] += sku_cost

                    # NOW physically move goods into child pipeline
                    lt_map = self.network.lead_time_sampler_by_child(parent_id)
                    child_node = self.network.nodes[child]
                    for sku, qty in pending.items():
                        if qty <= 0:
                            continue
                        L = int(lt_map[child]())
                        arrival = t + L if L > 0 else t + 1
                        child_node.pipeline_in.append(
                            Shipment(arrival_time=arrival, sku=sku, qty=int(qty))
                        )
                        self.shipments_log.append({
                            "t_ship": t,
                            "parent": parent_id,
                            "child": child,
                            "sku": sku,
                            "lead_time": L,
                            "qty": int(qty)
                        })

                    # DIAGNOSTIC
                    # if min_util > 0.0:
                    #     _util = total_pending_vol / opt.capacity
                    #     _forced = force
                    # else:
                    #     _util = 1.0
                    #     _forced = False
                    # if not hasattr(self, '_dispatch_log'):
                    #     self._dispatch_log = []
                    # self._dispatch_log.append({
                    #     'lane': str(lane), 't': t,
                    #     'util': round(_util, 3),
                    #     'forced': _forced
                    # })

                    self.pending_dispatch[lane] = {}
                    self.pending_dispatch_time[lane] = 0
                

            # =====================================================
            # 4) PLACE UPSTREAM ORDERS (PER SKU)
            # =====================================================

            for nid in topo:
                node = self.network.nodes[nid]
                parent_id = self.network.parent_of(nid)

                if parent_id is None:
                    continue

                for sku in node.skus:

                    policy = node.policies[sku]

                    # qty the parent is holding for us but hasn't shipped yet
                    # (blocked by transport consolidation)
                    parent_node = self.network.nodes[parent_id]
                    parent_backlog_for_me = parent_node.backlog_children.get(
                        (nid, sku), 0
                    )

                    lane = (parent_id, nid)
                    pending_for_me = self.pending_dispatch.get(lane, {}).get(sku, 0.0)

                    if isinstance(policy, EchelonStockPolicy):
                        # Echelon IP: sum on_hand + pipeline across all downstream nodes
                        echelon_stock = self._echelon_pipeline(nid, sku)
                        q = policy.order_qty(
                            on_hand=node.on_hand[sku],
                            backlog_external=node.backlog_external[sku],
                            backlog_children=node.total_backlog_children(sku),
                            pipeline_in=echelon_stock - node.on_hand[sku],
                            t=t
                        )
                    else:
                        effective_pipeline = (
                            node.total_pipeline_in(sku)
                            + parent_backlog_for_me
                            + int(pending_for_me)
                        )
                        q = policy.order_qty(
                            on_hand=node.on_hand[sku],
                            backlog_external=node.backlog_external[sku],
                            backlog_children=node.total_backlog_children(sku),
                            pipeline_in=effective_pipeline,
                            t=t
                        )


                    if q > 0:
                        orders_waiting.setdefault(parent_id, []).append(
                            (t + self.order_processing_delay, nid, sku, q)
                        )

                        ordering_cost_today[nid][sku] += (
                            node.order_cost_fixed[sku]
                            + node.order_cost_per_unit[sku] * q
                        )

                        node.placed_orders[sku] += q

                    orders_today[nid][sku] = q

            # =====================================================
            # 5) EOD SNAPSHOT
            # =====================================================

            for nid in topo:
                node = self.network.nodes[nid]

                for sku in node.skus:

                    hold_cost = node.on_hand[sku] * node.holding_cost[sku]
                    back_cost = (
                        node.backlog_external[sku] * node.shortage_cost[sku]
                        if node.node_type == "retailer"
                        else 0.0
                    )

                    ord_cost = ordering_cost_today[nid][sku]
                    trans_cost = transport_cost_today[nid][sku]

                    tot_cost = hold_cost + back_cost + ord_cost + trans_cost

                    self.metrics.append(
                        MetricsRow(
                            t=t,
                            node_id=nid,
                            sku=sku,
                            on_hand=node.on_hand[sku],
                            backlog_external=node.backlog_external[sku],
                            backlog_children=node.total_backlog_children(sku),
                            pipeline_in=node.total_pipeline_in(sku),
                            orders_to_parent=orders_today[nid][sku],
                            received=received_today[nid][sku],
                            demand=demand_today[nid][sku],
                            fulfilled_external=fulfilled_today[nid][sku],
                            holding_cost=hold_cost,
                            backlog_cost=back_cost,
                            ordering_cost=ord_cost,
                            transport_cost=trans_cost,
                            total_cost=tot_cost
                        )
                    )

                    # -----------------------------
                    # INVENTORY LOG
                    # -----------------------------
                    self.inventory_log.append({
                        "t": t,
                        "node_id": nid,
                        "sku": sku,
                        "on_hand": node.on_hand[sku],
                        "backlog_external": node.backlog_external[sku],
                        "backlog_children": node.total_backlog_children(sku),
                        "pipeline_in": node.total_pipeline_in(sku)
                    })

                    # -----------------------------
                    # ORDERS LOG
                    # -----------------------------
                    self.orders_log.append({
                        "t": t,
                        "node_id": nid,
                        "sku": sku,
                        "orders_to_parent": orders_today[nid][sku]
                    })


            # =====================================================
            # SAFETY
            # =====================================================

            for nid, node in self.network.nodes.items():
                if not node.infinite_supply:
                    for sku in node.skus:
                        assert node.on_hand[sku] >= 0, \
                            f"Negative stock at {nid}, SKU {sku}, t={t}"

        return self.metrics

    # ============================================================
    # TOPO SORT (UNCHANGED)
    # ============================================================

    def _echelon_pipeline(self, nid: str, sku: str) -> int:
        """
        Echelon inventory position for node `nid`, SKU `sku`.
        = on_hand(nid) + pipeline_in(nid)
          + sum over all downstream nodes d: on_hand(d) + pipeline_in(d)
          + pending_dispatch en route to any downstream node
        Used by EchelonStockPolicy to compute the correct order trigger.
        """
        total = 0
        stack = [nid]
        visited = set()
        while stack:
            curr = stack.pop()
            if curr in visited:
                continue
            visited.add(curr)
            n = self.network.nodes[curr]
            total += n.on_hand.get(sku, 0) + n.total_pipeline_in(sku)
            for child in self.network.children(curr):
                lane = (curr, child)
                total += int(self.pending_dispatch.get(lane, {}).get(sku, 0.0))
                stack.append(child)
        return total

    def _topological_order(self) -> List[str]:

        indeg = {nid: 0 for nid in self.network.nodes}

        for (p, c) in self.network.edges:
            indeg[c] += 1

        q = [nid for nid, d in indeg.items() if d == 0]
        out = []

        while q:
            u = q.pop(0)
            out.append(u)
            for v in self.network.children(u):
                indeg[v] -= 1
                if indeg[v] == 0:
                    q.append(v)

        if len(out) != len(self.network.nodes):
            raise ValueError("Graph not a DAG or disconnected.")

        return out
