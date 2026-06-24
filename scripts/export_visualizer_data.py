"""Export bundled Python max-flow traces for the static teaching site."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baseball_elimination.baseball import BaseballDivision


DEFAULT_DATASETS = (
    Path("data/teams4.txt"),
    Path("data/teams5.txt"),
    Path("data/princeton/teams7.txt"),
    Path("data/princeton/teams8.txt"),
    Path("data/princeton/teams10.txt"),
    Path("data/princeton/teams12.txt"),
)
DEFAULT_ALGORITHMS = ("edmonds-karp", "dinic")


def safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def export_site_data(
    datasets: Iterable[Path],
    output_dir: Path,
    algorithms: tuple[str, ...] = DEFAULT_ALGORITHMS,
) -> dict[str, object]:
    """Export one trace per dataset/team/algorithm plus a manifest."""

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_datasets: list[dict[str, object]] = []

    for dataset_path in datasets:
        division = BaseballDivision.from_file(dataset_path)
        dataset_id = safe_slug(dataset_path.stem)
        trace_files: list[str] = []
        trace_index: dict[str, dict[str, str]] = {}

        for team in division.teams:
            trace_index[team] = {}
            for algorithm in algorithms:
                file_name = (
                    f"{dataset_id}__{safe_slug(team)}__{safe_slug(algorithm)}.json"
                )
                write_json(
                    output_dir / file_name,
                    division.trace_analysis(team, algorithm),
                )
                trace_files.append(file_name)
                trace_index[team][algorithm] = file_name

        manifest_datasets.append(
            {
                "id": dataset_id,
                "label": dataset_path.name,
                "team_count": division.number_of_teams,
                "teams": list(division.teams),
                "algorithms": list(algorithms),
                "traces": trace_files,
                "trace_index": trace_index,
            }
        )

    manifest = {
        "schema": "baseball-maxflow-manifest.v1",
        "default_dataset": manifest_datasets[0]["id"] if manifest_datasets else None,
        "default_team": (
            manifest_datasets[0]["teams"][0] if manifest_datasets else None
        ),
        "default_algorithm": "dinic",
        "datasets": manifest_datasets,
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/data"),
    )
    parser.add_argument(
        "datasets",
        nargs="*",
        type=Path,
        default=list(DEFAULT_DATASETS),
    )
    args = parser.parse_args()
    manifest = export_site_data(args.datasets, args.output_dir)
    trace_count = sum(
        len(dataset["traces"]) for dataset in manifest["datasets"]  # type: ignore[index]
    )
    print(
        f"exported {len(manifest['datasets'])} datasets and "
        f"{trace_count} traces to {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
