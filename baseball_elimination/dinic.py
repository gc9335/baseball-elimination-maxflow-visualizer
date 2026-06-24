"""Dinic maximum-flow algorithm with level graphs and current arcs."""

from __future__ import annotations

from collections import deque

from .flow_network import FlowNetwork
from .tracing import AlgorithmMetrics, TraceRecorder, snapshot_network


def dinic(
    network: FlowNetwork,
    source: int,
    sink: int,
    *,
    recorder: TraceRecorder | None = None,
    metrics: AlgorithmMetrics | None = None,
) -> int:
    """Compute maximum flow using Dinic's blocking-flow algorithm."""

    network._check_vertex(source)
    network._check_vertex(sink)
    if source == sink:
        raise ValueError("source and sink must be different")

    vertex_count = network.vertex_count
    maximum_flow = 0
    counters = metrics if metrics is not None else AlgorithmMetrics()
    infinity = sum(
        edge.residual_capacity
        for edge in network.graph[source]
        if edge.residual_capacity > 0
    ) + 1

    def build_levels() -> list[int]:
        counters.bfs_rounds += 1
        levels = [-1] * vertex_count
        levels[source] = 0
        queue = deque([source])
        counters.queue_pushes += 1
        if recorder is not None:
            recorder.emit(
                "search-start",
                f"开始第 {counters.bfs_rounds} 轮分层 BFS",
                "只沿正残量边计算节点层级。",
                "build-levels",
                current_flow=maximum_flow,
                queue=[source],
            )
        while queue:
            vertex = queue.popleft()
            for edge_index, edge in enumerate(network.graph[vertex]):
                counters.edge_inspections += 1
                if edge.residual_capacity > 0 and levels[edge.to] == -1:
                    if edge.capacity == 0:
                        counters.reverse_edge_uses += 1
                    levels[edge.to] = levels[vertex] + 1
                    queue.append(edge.to)
                    counters.queue_pushes += 1
                    if recorder is not None:
                        recorder.emit(
                            "vertex-discovered",
                            f"节点 {edge.to} 进入第 {levels[edge.to]} 层",
                            "分层图只保留从低层指向相邻高层的残量边。",
                            "level-discover",
                            current_flow=maximum_flow,
                            from_vertex=vertex,
                            to_vertex=edge.to,
                            edge_index=edge_index,
                            levels=list(levels),
                            queue=list(queue),
                        )
        return levels

    while True:
        levels = build_levels()
        if levels[sink] == -1:
            if recorder is not None:
                recorder.emit(
                    "completed",
                    "汇点在分层图中不可达",
                    f"Dinic 算法结束，最大流为 {maximum_flow}。",
                    "terminate",
                    current_flow=maximum_flow,
                    levels=levels,
                    edges=snapshot_network(network),
                    metrics=counters.to_dict(),
                )
            return maximum_flow

        counters.level_phases += 1
        if recorder is not None:
            recorder.emit(
                "level-built",
                f"完成第 {counters.level_phases} 个分层图",
                f"汇点位于第 {levels[sink]} 层，开始发送阻塞流。",
                "level-complete",
                current_flow=maximum_flow,
                levels=levels,
                edges=snapshot_network(network),
                metrics=counters.to_dict(),
            )
        current_edge = [0] * vertex_count

        def send_flow(vertex: int, available: int, path: list[int]) -> int:
            counters.dfs_calls += 1
            if recorder is not None:
                recorder.emit(
                    "dfs-enter",
                    f"DFS 进入节点 {vertex}",
                    f"当前最多可继续发送 {available} 单位流。",
                    "dfs-send",
                    current_flow=maximum_flow,
                    active_path=path + [vertex],
                    available=available,
                    levels=levels,
                    current_arc=list(current_edge),
                )
            if vertex == sink:
                return available

            while current_edge[vertex] < len(network.graph[vertex]):
                edge_index = current_edge[vertex]
                edge = network.graph[vertex][edge_index]
                counters.edge_inspections += 1
                if edge.residual_capacity > 0 and levels[edge.to] == levels[vertex] + 1:
                    if edge.capacity == 0:
                        counters.reverse_edge_uses += 1
                    pushed = send_flow(
                        edge.to,
                        min(available, edge.residual_capacity),
                        path + [vertex],
                    )
                    if pushed > 0:
                        network.add_flow(vertex, edge_index, pushed)
                        return pushed
                current_edge[vertex] += 1
                counters.current_arc_skips += 1
            return 0

        while True:
            pushed = send_flow(source, infinity, [])
            if pushed == 0:
                break
            maximum_flow += pushed
            counters.blocking_flow_pushes += 1
            counters.augmentations += 1
            if recorder is not None:
                recorder.emit(
                    "blocking-flow",
                    f"阻塞流推送 {pushed} 单位",
                    f"当前分层阶段累计最大流为 {maximum_flow}。",
                    "blocking-flow",
                    current_flow=maximum_flow,
                    pushed=pushed,
                    levels=levels,
                    current_arc=list(current_edge),
                    edges=snapshot_network(network),
                    metrics=counters.to_dict(),
                )
