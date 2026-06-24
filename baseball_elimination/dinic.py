"""Dinic maximum-flow algorithm with level graphs and current arcs."""

from __future__ import annotations

from collections import deque

from .flow_network import FlowNetwork


def dinic(network: FlowNetwork, source: int, sink: int) -> int:
    """Compute maximum flow using Dinic's blocking-flow algorithm."""

    network._check_vertex(source)
    network._check_vertex(sink)
    if source == sink:
        raise ValueError("source and sink must be different")

    vertex_count = network.vertex_count
    maximum_flow = 0
    infinity = sum(
        edge.residual_capacity
        for edge in network.graph[source]
        if edge.residual_capacity > 0
    ) + 1

    def build_levels() -> list[int]:
        levels = [-1] * vertex_count
        levels[source] = 0
        queue = deque([source])
        while queue:
            vertex = queue.popleft()
            for edge in network.graph[vertex]:
                if edge.residual_capacity > 0 and levels[edge.to] == -1:
                    levels[edge.to] = levels[vertex] + 1
                    queue.append(edge.to)
        return levels

    while True:
        levels = build_levels()
        if levels[sink] == -1:
            return maximum_flow

        current_edge = [0] * vertex_count

        def send_flow(vertex: int, available: int) -> int:
            if vertex == sink:
                return available

            while current_edge[vertex] < len(network.graph[vertex]):
                edge_index = current_edge[vertex]
                edge = network.graph[vertex][edge_index]
                if edge.residual_capacity > 0 and levels[edge.to] == levels[vertex] + 1:
                    pushed = send_flow(
                        edge.to,
                        min(available, edge.residual_capacity),
                    )
                    if pushed > 0:
                        network.add_flow(vertex, edge_index, pushed)
                        return pushed
                current_edge[vertex] += 1
            return 0

        while True:
            pushed = send_flow(source, infinity)
            if pushed == 0:
                break
            maximum_flow += pushed
