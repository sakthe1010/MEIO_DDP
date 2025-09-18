# engine/network.py
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Callable, Optional
import random
from engine.node import Node

@dataclass
class Edge:
    parent: str
    child: str
    lead_time_sampler: Callable[[], int]
    share: Optional[float] = None  # optional weight for route selection

@dataclass
class Network:
    nodes: Dict[str, Node]                                     # id -> Node
    edges: Dict[Tuple[str, str], List[Edge]]                   # (parent, child) -> [Edge]
    parents_of: Dict[str, str] = field(default_factory=dict)   # single-sourcing (one parent per child)
    children_of: Dict[str, List[str]] = field(default_factory=dict)

    def __post_init__(self):
        # enforce single parent per child; collect children per parent
        for (p, c), edge_list in self.edges.items():
            if c in self.parents_of:
                if self.parents_of[c] != p:
                    raise ValueError(f"Child {c} has multiple parents (single-sourcing enforced).")
            else:
                self.parents_of[c] = p
            self.children_of.setdefault(p, [])
            if c not in self.children_of[p]:
                self.children_of[p].append(c)

    def parent_of(self, node_id: str):
        return self.parents_of.get(node_id)

    def children(self, node_id: str) -> List[str]:
        return self.children_of.get(node_id, [])

    def _mixed_sampler(self, edge_list: List[Edge]) -> Callable[[], int]:
        # choose a route according to normalized shares (uniform if all None)
        weights = [e.share if (e.share is not None and e.share > 0) else 1.0 for e in edge_list]
        total = sum(weights)
        probs = [w / total for w in weights]

        def sample():
            r = random.random()
            acc = 0.0
            for e, p in zip(edge_list, probs):
                acc += p
                if r <= acc:
                    return e.lead_time_sampler()
            return edge_list[-1].lead_time_sampler()

        return sample

    def lead_time_sampler_by_child(self, parent_id: str) -> Dict[str, Callable[[], int]]:
        # For each child, return a single callable that mixes across routes
        out: Dict[str, Callable[[], int]] = {}
        for c in self.children(parent_id):
            e_list = self.edges[(parent_id, c)]
            out[c] = e_list[0].lead_time_sampler if len(e_list) == 1 else self._mixed_sampler(e_list)
        return out
