# engine/simulator.py
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from engine.network import Network
from engine.node import Node
from policies.base_stock import BasePolicy

@dataclass
class MetricsRow:
    t: int
    node_id: str
    on_hand: int
    backlog_external: int
    backlog_children: int
    pipeline_in: int
    orders_to_parent: int
    received: int
    phase: str = "EOD"   # keeps optional detailed views possible

@dataclass
class Simulator:
    network: Network
    demand_by_node: Dict[str, callable]   # node_id -> DemandGenerator.sample
    T: int
    order_processing_delay: int = 1       # orders placed at t → processed at t+1

    metrics: List[MetricsRow] = field(default_factory=list)

    def run(self, mode: str = "summary") -> List[MetricsRow]:
        """
        Periodic-review loop.

        mode = "summary"  -> one EOD snapshot per node per t, with same-day flows recorded
        mode = "detailed" -> optional per-phase snapshots + EOD (useful for debugging)
        """
        topo = self._topological_order()
        # parent_id -> list of (process_time, child_id, qty)
        orders_waiting: Dict[str, List[Tuple[int, str, int]]] = {}

        for t in range(self.T):
            # Track today's flows to include in the *EOD* record
            received_today: Dict[str, int] = {nid: 0 for nid in self.network.nodes}
            orders_today: Dict[str, int]   = {nid: 0 for nid in self.network.nodes}

            # 1) Arrivals: move shipments arriving at t into on_hand
            for nid in topo:
                node = self.network.nodes[nid]
                rec = node.receive_shipments(t)
                received_today[nid] = rec
                if mode == "detailed":
                    self._record(t, nid, received=rec, orders_to_parent=0, phase="after_arrivals")

            # 1a) (NEW) Serve *external* backlog immediately after arrivals, before new demand
            #      This models backorders: when stock shows up, you first clear owed customer orders.
            for nid in topo:
                node = self.network.nodes[nid]
                if node.node_type == 'retailer' and node.backlog_external > 0 and node.on_hand > 0:
                    served_backlog = min(node.on_hand, node.backlog_external)
                    node.on_hand -= served_backlog
                    node.backlog_external -= served_backlog
                    if mode == "detailed" and served_backlog > 0:
                        self._record(t, nid, received=0, orders_to_parent=0, phase="after_backlog_clear")

            # 2) External demand (retailers only) for period t
            for nid in topo:
                node = self.network.nodes[nid]
                if node.node_type == 'retailer':
                    dgen = self.demand_by_node.get(nid, None)
                    demand = dgen(t) if dgen else 0
                    node.process_external_demand(demand)
                    if mode == "detailed":
                        self._record(t, nid, received=0, orders_to_parent=0, phase="after_demand")

            # 3) Parents process child orders that are due to be processed at t
            due: Dict[str, List[Tuple[str, int]]] = {}
            for pid, lst in list(orders_waiting.items()):
                take = [(c, q) for (tt, c, q) in lst if tt == t]
                if take:
                    due[pid] = take
                # keep the rest
                orders_waiting[pid] = [(tt, c, q) for (tt, c, q) in lst if tt != t]
                if not orders_waiting[pid]:
                    del orders_waiting[pid]

            for parent_id, items in due.items():
                parent = self.network.nodes[parent_id]
                # enqueue today's incoming child orders at parent
                for (child, q) in items:
                    parent.add_inbound_order(child, q)
                # parent serves children (backlog + today's)
                child_nodes = {c: self.network.nodes[c] for c in self.network.children(parent_id)}
                lt_map = self.network.lead_time_sampler_by_child(parent_id)
                parent.process_child_orders(t, child_nodes, lt_map)

            if mode == "detailed":
                for nid in topo:
                    self._record(t, nid, received=0, orders_to_parent=0, phase="after_shipments")

            # 4) Place replenishment orders upstream (these will be processed at t+order_processing_delay)
            for nid in topo:
                node = self.network.nodes[nid]
                parent_id = self.network.parent_of(nid)
                if parent_id is None:
                    continue
                policy: BasePolicy = node.policy
                q = policy.order_qty(
                    on_hand=node.on_hand,
                    backlog_external=node.backlog_external,
                    backlog_children=node.total_backlog_children(),
                    pipeline_in=node.total_pipeline_in(),
                )
                if q > 0:
                    orders_waiting.setdefault(parent_id, []).append((t + self.order_processing_delay, nid, q))
                # record today's order placed upstream (even if 0, it’s informative for tests & plots)
                orders_today[nid] = q

                if mode == "detailed":
                    self._record(t, nid, received=0, orders_to_parent=q, phase="after_ordering")

            # 5) Record the single End-of-Day snapshot (always)
            for nid in topo:
                self._record(
                    t, nid,
                    received=received_today[nid],
                    orders_to_parent=orders_today[nid],
                    phase="EOD"
                )

            # Safety invariants
            for nid, node in self.network.nodes.items():
                if not node.infinite_supply:
                    assert node.on_hand >= 0, f"Negative stock at {nid} t={t}"

        return self.metrics

    def _record(self, t: int, nid: str, received: int, orders_to_parent: int, phase: str = "EOD"):
        node = self.network.nodes[nid]
        self.metrics.append(MetricsRow(
            t=t, node_id=nid, on_hand=node.on_hand,
            backlog_external=node.backlog_external,
            backlog_children=node.total_backlog_children(),
            pipeline_in=node.total_pipeline_in(),
            orders_to_parent=orders_to_parent,
            received=received,
            phase=phase
        ))

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
