import json
from pathlib import Path

from baseball_elimination.baseball import BaseballDivision
from scripts.export_visualizer_data import export_site_data


def test_build_network_describes_game_and_team_vertices():
    division = BaseballDivision.from_file("data/teams4.txt")

    built = division.build_elimination_network("Philadelphia")

    assert built.source == 0
    assert built.target_team == "Philadelphia"
    assert {node.kind for node in built.nodes} == {"source", "game", "team", "sink"}
    assert built.required_flow == 7
    assert any(node.label == "Atlanta vs New_York" for node in built.nodes)


def test_trace_analysis_contains_network_events_metrics_and_result():
    division = BaseballDivision.from_file("data/teams4.txt")

    trace = division.trace_analysis("Philadelphia", "dinic")

    assert trace["schema"] == "baseball-maxflow-trace.v1"
    assert trace["result"]["eliminated"] is True
    assert trace["result"]["certificate"] == ["Atlanta", "New_York"]
    assert trace["network"]["required_flow"] == 7
    assert trace["events"][0]["type"] == "network-built"
    assert trace["events"][-1]["type"] == "completed"
    assert trace["metrics"]["level_phases"] >= 1


def test_trace_analysis_handles_trivial_elimination_without_flow_network():
    division = BaseballDivision.from_file("data/teams4.txt")

    trace = division.trace_analysis("Montreal", "edmonds-karp")

    assert trace["result"]["trivial"] is True
    assert trace["network"] is None
    assert [event["type"] for event in trace["events"]] == [
        "trivial-check",
        "completed",
    ]


def test_export_visualizer_data_writes_manifest_and_trace_files(tmp_path):
    export_site_data(
        datasets=[Path("data/teams4.txt")],
        output_dir=tmp_path,
        algorithms=("edmonds-karp", "dinic"),
    )

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["datasets"][0]["id"] == "teams4"
    trace_path = tmp_path / "teams4__Philadelphia__dinic.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["schema"] == "baseball-maxflow-trace.v1"
    assert trace["events"][-1]["type"] == "completed"
    assert trace_path.name in manifest["datasets"][0]["traces"]
