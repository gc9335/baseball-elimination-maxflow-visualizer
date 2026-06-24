"""Edmonds-Karp maximum-flow algorithm."""

from __future__ import annotations

from collections import deque

from .flow_network import FlowNetwork
from .tracing import AlgorithmMetrics, TraceRecorder, snapshot_network


def edmonds_karp(
    network: FlowNetwork,
    source: int,
    sink: int,
    *,
    recorder: TraceRecorder | None = None,
    metrics: AlgorithmMetrics | None = None,
) -> int:
    """Compute maximum flow by BFS shortest augmenting paths."""

    network._check_vertex(source)
    network._check_vertex(sink)
    if source == sink:
        raise ValueError("source and sink must be different")

    maximum_flow = 0
    counters = metrics if metrics is not None else AlgorithmMetrics()
    while True:
        counters.bfs_rounds += 1
        if recorder is not None:
            recorder.emit(
                "search-start",
                f"开始第 {counters.bfs_rounds} 轮 BFS",
                "在残量网络中寻找从源点到汇点的最短增广路。",
                "bfs-search",
                current_flow=maximum_flow,
                queue=[source],
                metrics=counters.to_dict(),
            )
        parent: list[tuple[int, int] | None] = [None] * network.vertex_count
        parent[source] = (source, -1)
        queue = deque([source])
        counters.queue_pushes += 1

        while queue and parent[sink] is None:
            vertex = queue.popleft()
            for edge_index, edge in enumerate(network.graph[vertex]):
                counters.edge_inspections += 1
                if edge.residual_capacity <= 0 or parent[edge.to] is not None:
                    continue
                if edge.capacity == 0:
                    counters.reverse_edge_uses += 1
                parent[edge.to] = (vertex, edge_index)
                queue.append(edge.to)
                counters.queue_pushes += 1
                if recorder is not None:
                    recorder.emit(
                        "vertex-discovered",
                        f"发现节点 {edge.to}",
                        f"通过残量为 {edge.residual_capacity} 的边到达节点 {edge.to}。",
                        "bfs-discover",
                        current_flow=maximum_flow,
                        from_vertex=vertex,
                        to_vertex=edge.to,
                        edge_index=edge_index,
                        queue=list(queue),
                        metrics=counters.to_dict(),
                    )
                if edge.to == sink:
                    break

        if parent[sink] is None:
            if recorder is not None:
                recorder.emit(
                    "completed",
                    "不存在新的增广路",
                    f"算法结束，最大流为 {maximum_flow}。",
                    "terminate",
                    current_flow=maximum_flow,
                    edges=snapshot_network(network),
                    metrics=counters.to_dict(),
                )
            return maximum_flow

        bottleneck: int | None = None
        path_vertices = [sink]
        path_edges: list[dict[str, int]] = []
        vertex = sink
        while vertex != source:
            previous, edge_index = parent[vertex]  # type: ignore[misc]
            path_edge = network.graph[previous][edge_index]
            residual = path_edge.residual_capacity
            bottleneck = residual if bottleneck is None else min(bottleneck, residual)
            path_edges.append(
                {
                    "start": previous,
                    "end": vertex,
                    "edge_index": edge_index,
                }
            )
            path_vertices.append(previous)
            vertex = previous

        assert bottleneck is not None
        path_vertices.reverse()
        path_edges.reverse()
        if recorder is not None:
            recorder.emit(
                "path-found",
                "找到增广路径",
                f"路径瓶颈容量为 {bottleneck}。",
                "find-bottleneck",
                current_flow=maximum_flow,
                path=path_vertices,
                path_edges=path_edges,
                bottleneck=bottleneck,
                metrics=counters.to_dict(),
            )
        vertex = sink
        while vertex != source:
            previous, edge_index = parent[vertex]  # type: ignore[misc]
            network.add_flow(previous, edge_index, bottleneck)
            vertex = previous
        maximum_flow += bottleneck
        counters.augmentations += 1
        if recorder is not None:
            recorder.emit(
                "augment",
                f"沿增广路推送 {bottleneck} 单位流",
                f"累计流量更新为 {maximum_flow}，同时更新正向边和反向残量边。",
                "augment",
                current_flow=maximum_flow,
                path=path_vertices,
                path_edges=path_edges,
                bottleneck=bottleneck,
                edges=snapshot_network(network),
                metrics=counters.to_dict(),
            )
