"""Correctness checks, extended benchmarks, CSV export, and chart generation."""

from __future__ import annotations

import argparse
import csv
import gc
import random
import shutil
import sys
import textwrap
import tracemalloc
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
import matplotlib.ticker as mticker
import numpy as np
import seaborn as sns

from baseball_elimination.baseball import BaseballDivision
from baseball_elimination.tracing import AlgorithmMetrics


CSV_FIELDS = [
    "category",
    "experiment",
    "dataset",
    "teams",
    "density",
    "seed",
    "algorithm",
    "repeat",
    "elapsed_ms",
    "peak_kib",
    "vertices",
    "logical_edges",
    "edge_inspections",
    "bfs_rounds",
    "dfs_calls",
    "queue_pushes",
    "augmentations",
    "level_phases",
    "blocking_flow_pushes",
    "current_arc_skips",
    "reverse_edge_uses",
]
ALGORITHMS = ("edmonds-karp", "dinic")
FONT_FAMILY = ["Segoe UI", "DejaVu Sans", "Arial", "sans-serif"]
MONO_FONT_FAMILY = ["Consolas", "DejaVu Sans Mono", "monospace"]
TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}
COLORS = {
    "edmonds-karp": {
        "base": "#F0986E",
        "light": "#FFBDA1",
        "dark": "#804126",
    },
    "dinic": {
        "base": "#A3BEFA",
        "light": "#CEDFFE",
        "dark": "#2E4780",
    },
}
LABELS = {
    "edmonds-karp": "Edmonds–Karp",
    "dinic": "Dinic",
}


def use_chart_theme() -> None:
    sns.set_theme(
        style="whitegrid",
        rc={
            "figure.facecolor": TOKENS["surface"],
            "figure.edgecolor": "none",
            "savefig.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["panel"],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "axes.grid": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": TOKENS["grid"],
            "grid.linewidth": 0.8,
            "font.family": "sans-serif",
            "font.sans-serif": FONT_FAMILY,
            "font.monospace": MONO_FONT_FAMILY,
            "patch.linewidth": 1.0,
        },
    )


def add_chart_header(
    fig: plt.Figure,
    ax: plt.Axes,
    title: str,
    subtitle: str,
) -> None:
    title = textwrap.fill(title, width=78, break_long_words=False)
    subtitle = textwrap.fill(subtitle, width=112, break_long_words=False)
    fig.subplots_adjust(top=0.80, left=0.10, right=0.98, bottom=0.13)
    left = ax.get_position().x0
    fig.text(
        left,
        0.975,
        title,
        ha="left",
        va="top",
        fontsize=14,
        fontweight="semibold",
        color=TOKENS["ink"],
    )
    fig.text(
        left,
        0.925,
        subtitle,
        ha="left",
        va="top",
        fontsize=9.5,
        color=TOKENS["muted"],
    )


def save_chart(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor=TOKENS["surface"])
    fig.savefig(
        path.with_suffix(".svg"),
        bbox_inches="tight",
        facecolor=TOKENS["surface"],
    )
    plt.close(fig)


def generate_random_division(
    team_count: int,
    seed: int,
    density: float = 1.0,
    max_games: int = 9,
) -> BaseballDivision:
    """Generate a deterministic division with controllable schedule density."""

    if team_count < 2:
        raise ValueError("team_count must be at least 2")
    if not 0 < density <= 1:
        raise ValueError("density must be in (0, 1]")
    if max_games < 1:
        raise ValueError("max_games must be positive")

    generator = random.Random(seed)
    games = [[0] * team_count for _ in range(team_count)]
    for first in range(team_count):
        for second in range(first + 1, team_count):
            if generator.random() <= density:
                games[first][second] = games[second][first] = generator.randint(
                    1,
                    max_games,
                )

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


def division_density(division: BaseballDivision) -> float:
    possible = division.number_of_teams * (division.number_of_teams - 1) // 2
    if possible == 0:
        return 0.0
    positive = sum(
        division._games[first][second] > 0
        for first in range(division.number_of_teams)
        for second in range(first + 1, division.number_of_teams)
    )
    return positive / possible


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


def profile_division(
    division: BaseballDivision,
    algorithm: str,
) -> dict[str, int]:
    """Aggregate network sizes and solver operation counters over every team."""

    solver = division._solver(algorithm)
    total_metrics = AlgorithmMetrics()
    vertices = 0
    logical_edges = 0

    for team in division.teams:
        target = division._team_index(team)
        maximum_wins = division._wins[target] + division._remaining[target]
        if division._trivial_certificate(target, maximum_wins):
            continue
        built = division.build_elimination_network(team)
        metrics = AlgorithmMetrics()
        solver(
            built.network,
            built.source,
            built.sink,
            metrics=metrics,
        )
        total_metrics.add(metrics)
        vertices += built.network.vertex_count
        logical_edges += len(built.edges)

    return {
        "vertices": vertices,
        "logical_edges": logical_edges,
        **total_metrics.to_dict(),
    }


def measure_peak_memory_kib(
    division: BaseballDivision,
    algorithm: str,
) -> float:
    gc.collect()
    tracemalloc.start()
    try:
        analyze_all(division, algorithm)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return peak / 1024


def benchmark_division(
    division: BaseballDivision,
    category: str,
    dataset: str,
    repeats: int,
    *,
    experiment: str | None = None,
    density: float | None = None,
    seed: int | None = None,
) -> list[dict[str, object]]:
    """Time and profile complete all-team analysis for both solvers."""

    rows: list[dict[str, object]] = []
    actual_density = division_density(division) if density is None else density
    for algorithm in ALGORITHMS:
        analyze_all(division, algorithm)
        profile = profile_division(division, algorithm)
        peak_kib = measure_peak_memory_kib(division, algorithm)
        for repeat in range(1, repeats + 1):
            start = perf_counter_ns()
            analyze_all(division, algorithm)
            elapsed_ms = (perf_counter_ns() - start) / 1_000_000
            rows.append(
                {
                    "category": category,
                    "experiment": experiment or category,
                    "dataset": dataset,
                    "teams": division.number_of_teams,
                    "density": actual_density,
                    "seed": "" if seed is None else seed,
                    "algorithm": algorithm,
                    "repeat": repeat,
                    "elapsed_ms": elapsed_ms,
                    "peak_kib": peak_kib,
                    **profile,
                }
            )
    return rows


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            formatted = {field: row.get(field, "") for field in CSV_FIELDS}
            formatted["elapsed_ms"] = f"{float(row['elapsed_ms']):.6f}"
            formatted["peak_kib"] = f"{float(row.get('peak_kib', 0)):.3f}"
            formatted["density"] = f"{float(row.get('density', 0)):.4f}"
            writer.writerow(formatted)


def _median_rows(
    rows: list[dict[str, object]],
    experiment: str,
) -> list[dict[str, object]]:
    groups: dict[tuple[str, int, float, str], list[dict[str, object]]] = defaultdict(
        list
    )
    for row in rows:
        if row.get("experiment") != experiment:
            continue
        key = (
            str(row["dataset"]),
            int(row["teams"]),
            float(row.get("density", 0)),
            str(row["algorithm"]),
        )
        groups[key].append(row)

    result: list[dict[str, object]] = []
    for (dataset, teams, density, algorithm), group in groups.items():
        representative = group[0]
        result.append(
            {
                "dataset": dataset,
                "teams": teams,
                "density": density,
                "algorithm": algorithm,
                "median_ms": median(float(item["elapsed_ms"]) for item in group),
                "peak_kib": median(float(item.get("peak_kib", 0)) for item in group),
                "vertices": int(representative.get("vertices", 0)),
                "logical_edges": int(representative.get("logical_edges", 0)),
                "edge_inspections": int(representative.get("edge_inspections", 0)),
                "bfs_rounds": int(representative.get("bfs_rounds", 0)),
                "dfs_calls": int(representative.get("dfs_calls", 0)),
                "queue_pushes": int(representative.get("queue_pushes", 0)),
                "augmentations": int(representative.get("augmentations", 0)),
                "level_phases": int(representative.get("level_phases", 0)),
            }
        )
    return sorted(
        result,
        key=lambda item: (
            int(item["teams"]),
            float(item["density"]),
            str(item["dataset"]),
            str(item["algorithm"]),
        ),
    )


def _median_series(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return _median_rows(rows, "scaling")


def benchmark_subtitle(rows: list[dict[str, object]]) -> str:
    repeats = max(
        (
            int(row["repeat"])
            for row in rows
            if row.get("experiment") == "scaling"
        ),
        default=0,
    )
    return (
        "Median time to analyze every team; "
        f"{repeats} repeated runs after one warm-up"
    )


def _plot_runtime_scaling(
    rows: list[dict[str, object]],
    path: Path,
) -> None:
    medians = _median_rows(rows, "scaling")
    if not medians:
        raise ValueError("no scaling benchmark rows available for plotting")

    use_chart_theme()
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    for algorithm, marker, linestyle in (
        ("edmonds-karp", "o", "--"),
        ("dinic", "s", "-"),
    ):
        selected = [row for row in medians if row["algorithm"] == algorithm]
        ax.plot(
            [row["teams"] for row in selected],
            [row["median_ms"] for row in selected],
            color=COLORS[algorithm]["base"],
            marker=marker,
            markeredgecolor=COLORS[algorithm]["dark"],
            markerfacecolor=COLORS[algorithm]["base"],
            linestyle=linestyle,
            linewidth=1.3,
            label=LABELS[algorithm],
        )
    values = [float(row["median_ms"]) for row in medians if row["median_ms"]]
    if values and max(values) / min(values) >= 100:
        ax.set_yscale("log")
    ax.set_xlabel("Number of teams")
    ax.set_ylabel("Median elapsed time (ms)")
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0, 1.02),
        frameon=False,
        ncol=2,
        borderaxespad=0,
    )
    ax.grid(axis="x", visible=False)
    add_chart_header(
        fig,
        ax,
        "Dinic scales more smoothly as the division grows",
        benchmark_subtitle(rows)
        + "; dense synthetic schedules, complete all-team elimination analysis.",
    )
    save_chart(fig, path)


def plot_comparison(rows: list[dict[str, object]], path: Path) -> None:
    """Compatibility wrapper for the original single comparison chart."""

    _plot_runtime_scaling(rows, path)


def _plot_speedup(rows: list[dict[str, object]], path: Path) -> None:
    medians = _median_rows(rows, "scaling")
    by_size: dict[int, dict[str, float]] = defaultdict(dict)
    for row in medians:
        by_size[int(row["teams"])][str(row["algorithm"])] = float(row["median_ms"])
    points = [
        (
            teams,
            values["edmonds-karp"] / values["dinic"]
            if values.get("dinic", 0) > 0
            else 0,
        )
        for teams, values in sorted(by_size.items())
        if set(ALGORITHMS).issubset(values)
    ]
    if not points:
        raise ValueError("no paired scaling rows available for speedup plotting")

    use_chart_theme()
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    bars = ax.bar(
        [str(team_count) for team_count, _ in points],
        [speedup for _, speedup in points],
        color=COLORS["dinic"]["base"],
        edgecolor=COLORS["dinic"]["dark"],
        linewidth=1.0,
    )
    ax.axhline(1, color=TOKENS["ink"], linestyle=":", linewidth=1.0)
    ax.bar_label(
        bars,
        labels=[f"{speedup:.2f}×" for _, speedup in points],
        padding=3,
        fontsize=8.5,
        color=TOKENS["ink"],
    )
    ax.set_xlabel("Number of teams")
    ax.set_ylabel("Edmonds–Karp time / Dinic time")
    ax.grid(axis="x", visible=False)
    add_chart_header(
        fig,
        ax,
        "Dinic's advantage becomes visible on larger flow networks",
        "Speedup uses paired median runtimes from the dense scaling experiment; "
        "the dotted line marks equal performance.",
    )
    save_chart(fig, path)


def _plot_density_runtime(rows: list[dict[str, object]], path: Path) -> None:
    medians = _median_rows(rows, "density")
    if not medians:
        raise ValueError("no density benchmark rows available for plotting")

    use_chart_theme()
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    for algorithm, marker, linestyle in (
        ("edmonds-karp", "o", "--"),
        ("dinic", "s", "-"),
    ):
        selected = [row for row in medians if row["algorithm"] == algorithm]
        ax.plot(
            [float(row["density"]) * 100 for row in selected],
            [row["median_ms"] for row in selected],
            color=COLORS[algorithm]["base"],
            marker=marker,
            markeredgecolor=COLORS[algorithm]["dark"],
            linestyle=linestyle,
            linewidth=1.3,
            label=LABELS[algorithm],
        )
    ax.set_xlabel("Scheduled-pair density (%)")
    ax.set_ylabel("Median elapsed time (ms)")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(100))
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0, 1.02),
        frameon=False,
        ncol=2,
        borderaxespad=0,
    )
    ax.grid(axis="x", visible=False)
    add_chart_header(
        fig,
        ax,
        "Denser remaining schedules create harder elimination networks",
        "Fixed team count with the probability of a nonzero remaining matchup "
        "varied from sparse to dense; medians include all target teams.",
    )
    save_chart(fig, path)


def _plot_operation_counts(rows: list[dict[str, object]], path: Path) -> None:
    medians = _median_rows(rows, "scaling")
    if not medians:
        raise ValueError("no scaling rows available for operation plotting")

    use_chart_theme()
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 5.4))
    metrics = (
        ("edge_inspections", "Residual-edge inspections"),
        ("bfs_rounds", "BFS / level-build rounds"),
        ("queue_pushes", "BFS queue insertions"),
    )
    for ax, (field, label) in zip(axes, metrics, strict=True):
        for algorithm, marker, linestyle in (
            ("edmonds-karp", "o", "--"),
            ("dinic", "s", "-"),
        ):
            selected = [row for row in medians if row["algorithm"] == algorithm]
            ax.plot(
                [row["teams"] for row in selected],
                [row[field] for row in selected],
                color=COLORS[algorithm]["base"],
                marker=marker,
                markeredgecolor=COLORS[algorithm]["dark"],
                linestyle=linestyle,
                linewidth=1.2,
                label=LABELS[algorithm],
            )
        ax.set_xlabel("Teams")
        ax.set_ylabel(label)
        ax.grid(axis="x", visible=False)
        if field == "edge_inspections":
            positive = [float(row[field]) for row in medians if float(row[field]) > 0]
            if positive and max(positive) / min(positive) >= 100:
                ax.set_yscale("log")
    axes[0].legend(
        loc="lower left",
        bbox_to_anchor=(0, 1.04),
        frameon=False,
        ncol=2,
        borderaxespad=0,
    )
    fig.subplots_adjust(top=0.76, left=0.07, right=0.99, bottom=0.15, wspace=0.30)
    left = axes[0].get_position().x0
    fig.text(
        left,
        0.975,
        "Operation counters explain the runtime gap",
        ha="left",
        va="top",
        fontsize=14,
        fontweight="semibold",
        color=TOKENS["ink"],
    )
    fig.text(
        left,
        0.925,
        "Counters are summed over all nontrivial target-team networks; "
        "Dinic reuses a level graph and current arcs within each phase.",
        ha="left",
        va="top",
        fontsize=9.5,
        color=TOKENS["muted"],
    )
    save_chart(fig, path)


def _plot_memory_scaling(rows: list[dict[str, object]], path: Path) -> None:
    medians = _median_rows(rows, "scaling")
    if not medians:
        raise ValueError("no scaling rows available for memory plotting")

    use_chart_theme()
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    for algorithm, marker, linestyle in (
        ("edmonds-karp", "o", "--"),
        ("dinic", "s", "-"),
    ):
        selected = [row for row in medians if row["algorithm"] == algorithm]
        ax.plot(
            [row["teams"] for row in selected],
            [row["peak_kib"] for row in selected],
            color=COLORS[algorithm]["base"],
            marker=marker,
            markeredgecolor=COLORS[algorithm]["dark"],
            linestyle=linestyle,
            linewidth=1.3,
            label=LABELS[algorithm],
        )
    ax.set_xlabel("Number of teams")
    ax.set_ylabel("Peak traced memory (KiB)")
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0, 1.02),
        frameon=False,
        ncol=2,
        borderaxespad=0,
    )
    ax.grid(axis="x", visible=False)
    add_chart_header(
        fig,
        ax,
        "Both solvers share the same dominant network-memory growth",
        "Peak Python allocations are measured with tracemalloc during complete "
        "all-team analysis; timing runs are measured separately.",
    )
    save_chart(fig, path)


def _plot_official_scatter(rows: list[dict[str, object]], path: Path) -> None:
    medians = _median_rows(rows, "official")
    if not medians:
        raise ValueError("no official benchmark rows available for plotting")

    use_chart_theme()
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    for algorithm, marker in (("edmonds-karp", "o"), ("dinic", "s")):
        selected = [row for row in medians if row["algorithm"] == algorithm]
        ax.scatter(
            [row["logical_edges"] for row in selected],
            [row["median_ms"] for row in selected],
            s=55,
            color=COLORS[algorithm]["base"],
            edgecolor=COLORS[algorithm]["dark"],
            marker=marker,
            linewidth=0.9,
            alpha=0.82,
            label=LABELS[algorithm],
        )
        for row in selected:
            if algorithm == "dinic":
                ax.annotate(
                    str(row["dataset"]),
                    (float(row["logical_edges"]), float(row["median_ms"])),
                    xytext=(4, 4),
                    textcoords="offset points",
                    fontsize=7,
                    color=TOKENS["muted"],
                )
    positive_x = [float(row["logical_edges"]) for row in medians if row["logical_edges"]]
    positive_y = [float(row["median_ms"]) for row in medians if row["median_ms"]]
    if positive_x and max(positive_x) / min(positive_x) >= 100:
        ax.set_xscale("log")
    if positive_y and max(positive_y) / min(positive_y) >= 100:
        ax.set_yscale("log")
    ax.set_xlabel("Logical flow-network edges, summed over target teams")
    ax.set_ylabel("Median elapsed time (ms)")
    ax.legend(
        loc="lower left",
        bbox_to_anchor=(0, 1.02),
        frameon=False,
        ncol=2,
        borderaxespad=0,
    )
    add_chart_header(
        fig,
        ax,
        "Official datasets confirm that network size drives runtime",
        "Each point is one Princeton dataset and one solver; labels identify "
        "the Dinic point for each dataset.",
    )
    save_chart(fig, path)


def plot_benchmark_suite(
    rows: list[dict[str, object]],
    output_dir: Path,
) -> list[Path]:
    paths = [
        output_dir / "runtime_scaling.png",
        output_dir / "speedup_scaling.png",
        output_dir / "density_runtime.png",
        output_dir / "operation_counts.png",
        output_dir / "memory_scaling.png",
        output_dir / "official_runtime_scatter.png",
    ]
    _plot_runtime_scaling(rows, paths[0])
    _plot_speedup(rows, paths[1])
    _plot_density_runtime(rows, paths[2])
    _plot_operation_counts(rows, paths[3])
    _plot_memory_scaling(rows, paths[4])
    _plot_official_scatter(rows, paths[5])
    return paths


def write_summary(
    official_summary: dict[str, dict[str, int]],
    rows: list[dict[str, object]],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scaling = _median_rows(rows, "scaling")
    density = _median_rows(rows, "density")
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
            "Synthetic scaling benchmark medians (ms)",
            "========================================",
        ]
    )
    for row in scaling:
        lines.append(
            f"{row['dataset']} {row['algorithm']}: {row['median_ms']:.6f}"
        )
    lines.extend(
        [
            "",
            "Density benchmark medians (ms)",
            "==============================",
        ]
    )
    for row in density:
        lines.append(
            f"density={float(row['density']):.2f} {row['algorithm']}: "
            f"{row['median_ms']:.6f}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_sizes(text: str) -> list[int]:
    sizes = [int(value.strip()) for value in text.split(",") if value.strip()]
    if not sizes or any(size < 2 for size in sizes):
        raise argparse.ArgumentTypeError("sizes must be comma-separated integers >= 2")
    return sizes


def parse_densities(text: str) -> list[float]:
    densities = [float(value.strip()) for value in text.split(",") if value.strip()]
    if not densities or any(not 0 < density <= 1 for density in densities):
        raise argparse.ArgumentTypeError(
            "densities must be comma-separated numbers in (0, 1]"
        )
    return densities


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--sizes",
        type=parse_sizes,
        default=parse_sizes("8,12,16,20,24,28"),
    )
    parser.add_argument(
        "--densities",
        type=parse_densities,
        default=parse_densities("0.15,0.30,0.45,0.60,0.75,0.90"),
    )
    parser.add_argument("--density-teams", type=int, default=20)
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--docs-output-dir", type=Path, default=Path("docs/output"))
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    if args.density_teams < 2:
        parser.error("--density-teams must be at least 2")

    official_paths = sorted(Path("data/princeton").glob("teams*.txt"))
    if not official_paths:
        parser.error("no official datasets found; run scripts/download_datasets.py")
    official_summary = validate_algorithms(official_paths)

    rows: list[dict[str, object]] = []
    representative = {
        "teams4.txt",
        "teams5.txt",
        "teams7.txt",
        "teams8.txt",
        "teams10.txt",
        "teams12.txt",
        "teams24.txt",
        "teams36.txt",
    }
    for path in official_paths:
        if path.name in representative:
            rows.extend(
                benchmark_division(
                    BaseballDivision.from_file(path),
                    "official",
                    path.stem,
                    args.repeats,
                    experiment="official",
                )
            )

    for team_count in args.sizes:
        seed = 20260624 + team_count
        division = generate_random_division(team_count, seed=seed, density=1.0)
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
                experiment="scaling",
                density=1.0,
                seed=seed,
            )
        )

    for density_index, density in enumerate(args.densities):
        seed = 20261624 + density_index
        division = generate_random_division(
            args.density_teams,
            seed=seed,
            density=density,
        )
        rows.extend(
            benchmark_division(
                division,
                "synthetic",
                f"density-{density:.2f}",
                args.repeats,
                experiment="density",
                density=division_density(division),
                seed=seed,
            )
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(rows, args.output_dir / "benchmark_results.csv")
    chart_paths = plot_benchmark_suite(rows, args.output_dir)
    plot_comparison(rows, args.output_dir / "maxflow_comparison.png")
    write_summary(official_summary, rows, args.output_dir / "test_results.txt")

    args.docs_output_dir.mkdir(parents=True, exist_ok=True)
    for chart_path in chart_paths:
        shutil.copy2(chart_path, args.docs_output_dir / chart_path.name)
        svg_path = chart_path.with_suffix(".svg")
        shutil.copy2(svg_path, args.docs_output_dir / svg_path.name)

    print(f"validated {len(official_summary)} official datasets")
    print(f"wrote {args.output_dir / 'benchmark_results.csv'}")
    for chart_path in chart_paths:
        print(f"wrote {chart_path}")
    print(f"copied charts to {args.docs_output_dir}")
    print(f"wrote {args.output_dir / 'test_results.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
