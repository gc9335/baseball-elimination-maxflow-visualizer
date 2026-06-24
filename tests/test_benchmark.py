import csv
from pathlib import Path

from scripts.benchmark import (
    benchmark_subtitle,
    generate_random_division,
    plot_comparison,
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
            "dataset": "random-8",
            "teams": 8,
            "algorithm": "dinic",
            "repeat": 1,
            "elapsed_ms": 1.25,
        }
    ]
    path = tmp_path / "results.csv"

    write_csv(rows, path)

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == [
            "category",
            "dataset",
            "teams",
            "algorithm",
            "repeat",
            "elapsed_ms",
        ]
        assert list(reader)[0]["elapsed_ms"] == "1.250000"


def test_plot_comparison_creates_nonempty_png(tmp_path):
    rows = []
    for team_count in (8, 12):
        for algorithm, elapsed in (("edmonds-karp", 3.0), ("dinic", 1.0)):
            for repeat in range(1, 4):
                rows.append(
                    {
                        "category": "synthetic",
                        "dataset": f"random-{team_count}",
                        "teams": team_count,
                        "algorithm": algorithm,
                        "repeat": repeat,
                        "elapsed_ms": elapsed + repeat / 10,
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
            "dataset": "random-8",
            "teams": 8,
            "algorithm": algorithm,
            "repeat": repeat,
            "elapsed_ms": 1.0,
        }
        for algorithm in ("edmonds-karp", "dinic")
        for repeat in range(1, 4)
    ]

    assert "3 repeated runs" in benchmark_subtitle(rows)
