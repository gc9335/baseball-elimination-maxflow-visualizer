"""Residual-network primitives shared by the maximum-flow algorithms."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class Edge:
    """A directed residual edge."""

    to: int
    reverse_index: int
    capacity: int
    flow: int = 0

    @property
    def residual_capacity(self) -> int:
        return self.capacity - self.flow


class FlowNetwork:
    """Adjacency-list residual network with paired forward/reverse edges."""

    def __init__(self, vertex_count: int) -> None:
        if vertex_count <= 0:
            raise ValueError("vertex_count must be positive")
        self.vertex_count = vertex_count
        self.graph: list[list[Edge]] = [[] for _ in range(vertex_count)]

    def _check_vertex(self, vertex: int) -> None:
        if not 0 <= vertex < self.vertex_count:
            raise IndexError(f"vertex {vertex} is outside the network")

    def add_edge(self, start: int, end: int, capacity: int) -> Edge:
        self._check_vertex(start)
        self._check_vertex(end)
        if capacity < 0:
            raise ValueError("capacity must be nonnegative")

        forward = Edge(end, len(self.graph[end]), capacity)
        reverse = Edge(start, len(self.graph[start]), 0)
        self.graph[start].append(forward)
        self.graph[end].append(reverse)
        return forward

    def add_flow(self, start: int, edge_index: int, amount: int) -> None:
        self._check_vertex(start)
        if amount < 0:
            raise ValueError("flow increment must be nonnegative")
        edge = self.graph[start][edge_index]
        if amount > edge.residual_capacity:
            raise ValueError("flow increment exceeds residual capacity")

        edge.flow += amount
        reverse = self.graph[edge.to][edge.reverse_index]
        reverse.flow -= amount

    def source_side(self, source: int) -> set[int]:
        """Return vertices reachable from source through residual edges."""

        self._check_vertex(source)
        reachable = {source}
        queue = deque([source])
        while queue:
            vertex = queue.popleft()
            for edge in self.graph[vertex]:
                if edge.residual_capacity > 0 and edge.to not in reachable:
                    reachable.add(edge.to)
                    queue.append(edge.to)
        return reachable
