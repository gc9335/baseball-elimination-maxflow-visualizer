import csv
from pathlib import Path

from scripts.benchmark import (
    CSV_FIELDS,
    LABELS,
    benchmark_subtitle,
    generate_random_division,
    plot_benchmark_suite,
    plot_comparison,
    profile_division,
    validate_algorithms,
    write_csv,
)


def test_random_division_is_reproducible():
    first = generate_random_division(8, seed=2026)
    second = generate_random_division(8, seed=2026)

    assert first.teams == second.teams
    assert first._wins == second._wins
    assert first._remaining == second._remaining
    assert first._games == second._games


def test_random_division_density_controls_schedule_sparsity():
    sparse = generate_random_division(12, seed=2026, density=0.15)
    dense = generate_random_division(12, seed=2026, density=0.90)

    sparse_games = sum(
        sparse._games[first][second] > 0
        for first in range(12)
        for second in range(first + 1, 12)
    )
    dense_games = sum(
        dense._games[first][second] > 0
        for first in range(12)
        for second in range(first + 1, 12)
    )

    assert sparse_games < dense_games


def test_validate_algorithms_accepts_official_example():
    summary = validate_algorithms(
        [Path("data/teams4.txt"), Path("data/teams5.txt")]
    )

    assert summary == {
        "teams4.txt": {"teams": 4, "eliminated": 2},
        "teams5.txt": {"teams": 5, "eliminated": 1},
    }


def test_write_csv_uses_expected_columns(tmp_path):
    rows = [
        {
            "category": "synthetic",
            "experiment": "scaling",
            "dataset": "random-8",
            "teams": 8,
            "density": 1.0,
            "seed": 2026,
            "algorithm": "dinic",
            "repeat": 1,
            "elapsed_ms": 1.25,
            "peak_kib": 64.5,
            "vertices": 30,
            "logical_edges": 70,
            "edge_inspections": 120,
            "bfs_rounds": 3,
            "dfs_calls": 20,
            "queue_pushes": 18,
            "augmentations": 5,
            "level_phases": 2,
            "blocking_flow_pushes": 5,
            "current_arc_skips": 30,
            "reverse_edge_uses": 0,
        }
    ]
    path = tmp_path / "results.csv"

    write_csv(rows, path)

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == CSV_FIELDS
        written = list(reader)[0]
        assert written["elapsed_ms"] == "1.250000"
        assert written["peak_kib"] == "64.500"


def test_plot_comparison_creates_nonempty_png(tmp_path):
    rows = []
    for team_count in (8, 12):
        for algorithm, elapsed in (("edmonds-karp", 3.0), ("dinic", 1.0)):
            for repeat in range(1, 4):
                rows.append(
                    {
                        "category": "synthetic",
                        "experiment": "scaling",
                        "dataset": f"random-{team_count}",
                        "teams": team_count,
                        "density": 1.0,
                        "seed": 2026,
                        "algorithm": algorithm,
                        "repeat": repeat,
                        "elapsed_ms": elapsed + repeat / 10,
                        "peak_kib": 50.0,
                        "vertices": 30,
                        "logical_edges": 70,
                        "edge_inspections": 100,
                        "bfs_rounds": 3,
                        "dfs_calls": 10,
                        "queue_pushes": 15,
                        "augmentations": 4,
                        "level_phases": 2,
                        "blocking_flow_pushes": 4,
                        "current_arc_skips": 20,
                        "reverse_edge_uses": 0,
                    }
                )
    path = tmp_path / "comparison.png"

    plot_comparison(rows, path)

    assert path.exists()
    assert path.stat().st_size > 1_000


def test_benchmark_subtitle_uses_actual_repeat_count():
    rows = [
        {
            "category": "synthetic",
            "experiment": "scaling",
            "dataset": "random-8",
            "teams": 8,
            "density": 1.0,
            "seed": 2026,
            "algorithm": algorithm,
            "repeat": repeat,
            "elapsed_ms": 1.0,
        }
        for algorithm in ("edmonds-karp", "dinic")
        for repeat in range(1, 4)
    ]

    assert "重复 3 次" in benchmark_subtitle(rows)


def test_chart_copy_uses_chinese_for_report_images():
    source = Path("scripts/benchmark.py").read_text(encoding="utf-8")

    for forbidden in [
        "Number of teams",
        "Median elapsed time",
        "Operation counters explain",
        "Official datasets confirm",
        "Scheduled-pair density",
        "Peak traced memory",
        "Logical flow-network edges",
        "Residual-edge inspections",
        "BFS queue insertions",
        "Speedup uses paired",
    ]:
        assert forbidden not in source

    for expected in [
        "球队数量",
        "中位运行时间",
        "赛程密度",
        "残量边检查次数",
        "峰值内存",
        "官方数据集",
    ]:
        assert expected in source


def test_algorithm_labels_keep_english_names():
    assert LABELS == {
        "edmonds-karp": "Edmonds-Karp",
        "dinic": "Dinic",
    }


def test_profile_division_collects_network_and_operation_metrics():
    division = generate_random_division(8, seed=2026, density=0.7)

    profile = profile_division(division, "dinic")

    assert profile["vertices"] > 0
    assert profile["logical_edges"] > 0
    assert profile["edge_inspections"] > 0
    assert profile["bfs_rounds"] > 0
    assert profile["dfs_calls"] > 0


def test_plot_benchmark_suite_creates_six_nonempty_charts(tmp_path):
    rows = []
    for experiment, team_count, density in (
        ("scaling", 8, 1.0),
        ("scaling", 12, 1.0),
        ("density", 16, 0.25),
        ("density", 16, 0.75),
        ("official", 4, 0.5),
        ("official", 8, 0.5),
        ("official", 12, 0.5),
        ("official", 16, 0.5),
    ):
        for algorithm, elapsed in (("edmonds-karp", 4.0), ("dinic", 1.5)):
            for repeat in range(1, 3):
                rows.append(
                    {
                        "category": "synthetic"
                        if experiment != "official"
                        else "official",
                        "experiment": experiment,
                        "dataset": f"{experiment}-{team_count}-{density}",
                        "teams": team_count,
                        "density": density,
                        "seed": 2026,
                        "algorithm": algorithm,
                        "repeat": repeat,
                        "elapsed_ms": elapsed * team_count / 8 + repeat / 10,
                        "peak_kib": 30 + team_count * 2,
                        "vertices": team_count * team_count,
                        "logical_edges": team_count * team_count * 2,
                        "edge_inspections": team_count * 100,
                        "bfs_rounds": team_count,
                        "dfs_calls": team_count * 3,
                        "queue_pushes": team_count * 2,
                        "augmentations": team_count,
                        "level_phases": team_count // 2,
                        "blocking_flow_pushes": team_count,
                        "current_arc_skips": team_count * 4,
                        "reverse_edge_uses": 0,
                    }
                )

    paths = plot_benchmark_suite(rows, tmp_path)

    assert {path.name for path in paths} == {
        "runtime_scaling.png",
        "speedup_scaling.png",
        "density_runtime.png",
        "operation_counts.png",
        "memory_scaling.png",
        "official_runtime_scatter.png",
    }
    assert all(path.stat().st_size > 1_000 for path in paths)
