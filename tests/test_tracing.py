from baseball_elimination.dinic import dinic
from baseball_elimination.edmonds_karp import edmonds_karp
from baseball_elimination.flow_network import FlowNetwork
from baseball_elimination.tracing import AlgorithmMetrics, TraceRecorder


def build_network() -> FlowNetwork:
    network = FlowNetwork(4)
    network.add_edge(0, 1, 3)
    network.add_edge(0, 2, 2)
    network.add_edge(1, 2, 1)
    network.add_edge(1, 3, 2)
    network.add_edge(2, 3, 3)
    return network


def test_trace_recorder_assigns_contiguous_steps():
    recorder = TraceRecorder("edmonds-karp")

    recorder.emit("search-start", "开始 BFS")
    recorder.emit("path-found", "找到增广路", path=[0, 1, 3])

    assert [event.step for event in recorder.events] == [0, 1]
    assert recorder.events[1].payload["path"] == [0, 1, 3]


def test_metrics_export_contains_common_and_algorithm_fields():
    metrics = AlgorithmMetrics()
    metrics.edge_inspections = 5
    metrics.bfs_rounds = 2

    exported = metrics.to_dict()

    assert exported["edge_inspections"] == 5
    assert exported["bfs_rounds"] == 2
    assert exported["dfs_calls"] == 0


def test_edmonds_karp_emits_search_path_augment_and_completion_events():
    recorder = TraceRecorder("edmonds-karp")
    metrics = AlgorithmMetrics()

    value = edmonds_karp(
        build_network(),
        0,
        3,
        recorder=recorder,
        metrics=metrics,
    )

    event_types = {event.type for event in recorder.events}
    assert value == 5
    assert {"search-start", "path-found", "augment", "completed"} <= event_types
    assert metrics.bfs_rounds >= 1
    assert metrics.augmentations >= 1
    assert metrics.edge_inspections >= metrics.augmentations


def test_dinic_emits_level_and_blocking_flow_events():
    recorder = TraceRecorder("dinic")
    metrics = AlgorithmMetrics()

    value = dinic(
        build_network(),
        0,
        3,
        recorder=recorder,
        metrics=metrics,
    )

    event_types = {event.type for event in recorder.events}
    assert value == 5
    assert {"level-built", "dfs-enter", "blocking-flow", "completed"} <= event_types
    assert metrics.level_phases >= 1
    assert metrics.dfs_calls >= 1
    assert metrics.blocking_flow_pushes >= 1
    pushes = [event for event in recorder.events if event.type == "blocking-flow"]
    assert all(event.payload["path"][0] == 0 for event in pushes)
    assert all(event.payload["path"][-1] == 3 for event in pushes)
