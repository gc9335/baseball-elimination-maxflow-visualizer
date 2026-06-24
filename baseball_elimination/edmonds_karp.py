"""Edmonds-Karp maximum-flow algorithm."""

from __future__ import annotations

from collections import deque

from .flow_network import FlowNetwork


def edmonds_karp(network: FlowNetwork, source: int, sink: int) -> int:
    """Compute maximum flow by BFS shortest augmenting paths."""

    network._check_vertex(source)
    network._check_vertex(sink)
    if source == sink:
        raise ValueError("source and sink must be different")

    maximum_flow = 0
    while True:
        parent: list[tuple[int, int] | None] = [None] * network.vertex_count
        parent[source] = (source, -1)
        queue = deque([source])

        while queue and parent[sink] is None:
            vertex = queue.popleft()
            for edge_index, edge in enumerate(network.graph[vertex]):
                if edge.residual_capacity <= 0 or parent[edge.to] is not None:
                    continue
                parent[edge.to] = (vertex, edge_index)
                queue.append(edge.to)
                if edge.to == sink:
                    break

        if parent[sink] is None:
            return maximum_flow

        bottleneck: int | None = None
        vertex = sink
        while vertex != source:
            previous, edge_index = parent[vertex]  # type: ignore[misc]
            residual = network.graph[previous][edge_index].residual_capacity
            bottleneck = residual if bottleneck is None else min(bottleneck, residual)
            vertex = previous

        assert bottleneck is not None
        vertex = sink
        while vertex != source:
            previous, edge_index = parent[vertex]  # type: ignore[misc]
            network.add_flow(previous, edge_index, bottleneck)
            vertex = previous
        maximum_flow += bottleneck
