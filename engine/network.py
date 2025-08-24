from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Callable
from engine.node import Node

@dataclass
class Edge:
    parent: str
    child: str
    lead_time_sampler: Callable[[], int]

@dataclass
class Network:
    nodes: Dict[str, Node]                           # id -> Node
    edges: Dict[Tuple[str, str], Edge]               # (parent, child) -> Edge
    parents_of: Dict[str, str] = field(default_factory=dict)
    children_of: Dict[str, List[str]] = field(default_factory=dict)

    def __post_init__(self):
        for (p, c), e in self.edges.items():
            if c in self.parents_of:
                raise ValueError(f"Child {c} has multiple parents (single-sourcing enforced).")
            self.parents_of[c] = p
            self.children_of.setdefault(p, []).append(c)

    def parent_of(self, node_id: str):
        return self.parents_of.get(node_id)

    def children(self, node_id: str) -> List[str]:
        return self.children_of.get(node_id, [])

    def lead_time_sampler_by_child(self, parent_id: str) -> Dict[str, Callable[[], int]]:
        return {c: self.edges[(parent_id, c)].lead_time_sampler for c in self.children(parent_id)}
