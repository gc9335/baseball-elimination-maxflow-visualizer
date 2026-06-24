"""Correctness checks, timing experiments, CSV export, and chart generation."""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median
from time import perf_counter_ns
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from baseball_elimination.baseball import BaseballDivision


CSV_FIELDS = [
    "category",
    "dataset",
    "teams",
    "algorithm",
    "repeat",
    "elapsed_ms",
]
ALGORITHMS = ("edmonds-karp", "dinic")
TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}
COLORS = {
    "edmonds-karp": ("#F0986E", "#804126"),
    "dinic": ("#A3BEFA", "#2E4780"),
}


def generate_random_division(team_count: int, seed: int) -> BaseballDivision:
    """Generate a deterministic dense division for scaling experiments."""

    if team_count < 2:
        raise ValueError("team_count must be at least 2")
    generator = random.Random(seed)
    games = [[0] * team_count for _ in range(team_count)]
    for first in range(team_count):
        for second in range(first + 1, team_count):
            games[first][second] = games[second][first] = generator.randint(1, 9)

    names = tuple(f"Team_{index:02d}" for index in range(team_count))
    wins = tuple(60 + generator.randint(0, max(2, team_count // 2)) for _ in names)
    losses = tuple(50 + generator.randint(0, 20) for _ in names)
    remaining = tuple(sum(row) for row in games)
    return BaseballDivision(
        names,
        wins,
        losses,
        remaining,
        tuple(tuple(row) for row in games),
        MappingProxyType({name: index for index, name in enumerate(names)}),
    )


def analyze_all(division: BaseballDivision, algorithm: str):
    return tuple(division.analyze(team, algorithm) for team in division.teams)


def validate_algorithms(paths: list[Path]) -> dict[str, dict[str, int]]:
    """Cross-check both solvers on every team in each supplied dataset."""

    summary: dict[str, dict[str, int]] = {}
    for path in paths:
        division = BaseballDivision.from_file(path)
        baseline = analyze_all(division, "edmonds-karp")
        optimized = analyze_all(division, "dinic")
        for first, second in zip(baseline, optimized, strict=True):
            comparable_first = (
                first.eliminated,
                first.trivial,
                first.maximum_wins,
                first.max_flow,
                first.required_flow,
            )
            comparable_second = (
                second.eliminated,
                second.trivial,
                second.maximum_wins,
                second.max_flow,
                second.required_flow,
            )
            if comparable_first != comparable_second:
                raise AssertionError(
                    f"solver mismatch for {path.name}/{first.team}: "
                    f"{comparable_first} != {comparable_second}"
                )
        summary[path.name] = {
            "teams": division.number_of_teams,
            "eliminated": sum(result.eliminated for result in optimized),
        }
    return summary


def benchmark_division(
    division: BaseballDivision,
    category: str,
    dataset: str,
    repeats: int,
) -> list[dict[str, object]]:
    """Time complete all-team analysis for both solvers."""

    rows: list[dict[str, object]] = []
    for algorithm in ALGORITHMS:
        analyze_all(division, algorithm)
        for repeat in range(1, repeats + 1):
            start = perf_counter_ns()
            analyze_all(division, algorithm)
            elapsed_ms = (perf_counter_ns() - start) / 1_000_000
            rows.append(
                {
                    "category": category,
                    "dataset": dataset,
                    "teams": division.number_of_teams,
                    "algorithm": algorithm,
                    "repeat": repeat,
                    "elapsed_ms": elapsed_ms,
                }
            )
    return rows


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            formatted = dict(row)
            formatted["elapsed_ms"] = f"{float(row['elapsed_ms']):.6f}"
            writer.writerow(formatted)


def _median_series(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    for row in rows:
        if row["category"] != "synthetic":
            continue
        key = (
            str(row["dataset"]),
            int(row["teams"]),
            str(row["algorithm"]),
        )
        groups[key].append(float(row["elapsed_ms"]))
    return [
        {
            "dataset": key[0],
            "teams": key[1],
            "algorithm": key[2],
            "median_ms": median(values),
        }
        for key, values in sorted(groups.items(), key=lambda item: item[0][1])
    ]


def plot_comparison(rows: list[dict[str, object]], path: Path) -> None:
    """Render the grouped bar chart used in the Markdown report."""

    medians = _median_series(rows)
    if not medians:
        raise ValueError("no synthetic benchmark rows available for plotting")

    team_counts = sorted({int(row["teams"]) for row in medians})
    values = {
        algorithm: {
            int(row["teams"]): float(row["median_ms"])
            for row in medians
            if row["algorithm"] == algorithm
        }
        for algorithm in ALGORITHMS
    }

    sns.set_theme(
        style="whitegrid",
        rc={
            "figure.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["panel"],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "grid.color": TOKENS["grid"],
            "grid.linewidth": 0.8,
            "font.family": "sans-serif",
            "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
        },
    )
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    x = np.arange(len(team_counts))
    width = 0.34
    for offset, algorithm in zip((-width / 2, width / 2), ALGORITHMS, strict=True):
        fill, edge = COLORS[algorithm]
        plotted = [values[algorithm][team_count] for team_count in team_counts]
        bars = ax.bar(
            x + offset,
            plotted,
            width=width,
            label="Edmonds–Karp" if algorithm == "edmonds-karp" else "Dinic",
            color=fill,
            edgecolor=edge,
            linewidth=1.0,
        )
        ax.bar_label(
            bars,
            labels=[f"{value:.1f}" for value in plotted],
            padding=3,
            fontsize=8,
            color=TOKENS["muted"],
        )

    all_values = [float(row["median_ms"]) for row in medians]
    positive_values = [value for value in all_values if value > 0]
    if positive_values and max(positive_values) / min(positive_values) >= 100:
        ax.set_yscale("log")

    ax.set_xticks(x, [str(team_count) for team_count in team_counts])
    ax.set_xlabel("Number of teams")
    ax.set_ylabel("Median elapsed time (ms)")
    ax.grid(axis="x", visible=False)
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0, 1.02),
        frameon=False,
        ncol=2,
        borderaxespad=0,
    )
    sns.despine(ax=ax)
    fig.subplots_adjust(top=0.78, left=0.10, right=0.98, bottom=0.12)
    left = ax.get_position().x0
    fig.text(
        left,
        0.965,
        "Dinic scales better on dense baseball-elimination networks",
        ha="left",
        va="top",
        fontsize=14,
        fontweight="semibold",
        color=TOKENS["ink"],
    )
    fig.text(
        left,
        0.915,
        "Median time to analyze every team; five repeated runs after one warm-up",
        ha="left",
        va="top",
        fontsize=9.5,
        color=TOKENS["muted"],
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor=TOKENS["surface"])
    plt.close(fig)


def write_summary(
    official_summary: dict[str, dict[str, int]],
    rows: list[dict[str, object]],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    medians = _median_series(rows)
    lines = [
        "Official Princeton dataset correctness check",
        "============================================",
    ]
    for name, result in sorted(
        official_summary.items(),
        key=lambda item: (item[1]["teams"], item[0]),
    ):
        lines.append(
            f"{name}: teams={result['teams']}, eliminated={result['eliminated']}, "
            "solvers=consistent"
        )
    lines.extend(
        [
            "",
            "Synthetic benchmark medians (ms)",
            "================================",
        ]
    )
    for row in medians:
        lines.append(
            f"{row['dataset']} {row['algorithm']}: {row['median_ms']:.6f}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_sizes(text: str) -> list[int]:
    sizes = [int(value.strip()) for value in text.split(",") if value.strip()]
    if not sizes or any(size < 2 for size in sizes):
        raise argparse.ArgumentTypeError("sizes must be comma-separated integers >= 2")
    return sizes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument(
        "--sizes",
        type=parse_sizes,
        default=parse_sizes("8,12,16,20,24,28"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")

    official_paths = sorted(Path("data/princeton").glob("teams*.txt"))
    if not official_paths:
        parser.error("no official datasets found; run scripts/download_datasets.py")
    official_summary = validate_algorithms(official_paths)

    rows: list[dict[str, object]] = []
    representative = {"teams4.txt", "teams12.txt", "teams24.txt", "teams36.txt"}
    for path in official_paths:
        if path.name in representative:
            rows.extend(
                benchmark_division(
                    BaseballDivision.from_file(path),
                    "official",
                    path.stem,
                    args.repeats,
                )
            )
    for team_count in args.sizes:
        division = generate_random_division(team_count, seed=20260624 + team_count)
        baseline = analyze_all(division, "edmonds-karp")
        optimized = analyze_all(division, "dinic")
        if [
            (item.eliminated, item.max_flow, item.required_flow) for item in baseline
        ] != [
            (item.eliminated, item.max_flow, item.required_flow) for item in optimized
        ]:
            raise AssertionError(f"solver mismatch for random-{team_count}")
        rows.extend(
            benchmark_division(
                division,
                "synthetic",
                f"random-{team_count}",
                args.repeats,
            )
        )

    write_csv(rows, args.output_dir / "benchmark_results.csv")
    plot_comparison(rows, args.output_dir / "maxflow_comparison.png")
    write_summary(official_summary, rows, args.output_dir / "test_results.txt")
    print(f"validated {len(official_summary)} official datasets")
    print(f"wrote {args.output_dir / 'benchmark_results.csv'}")
    print(f"wrote {args.output_dir / 'maxflow_comparison.png'}")
    print(f"wrote {args.output_dir / 'test_results.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
