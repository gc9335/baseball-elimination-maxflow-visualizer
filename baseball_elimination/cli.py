"""Command-line interface for baseball elimination."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .baseball import BaseballDivision, EliminationResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Determine baseball elimination with maximum flow."
    )
    parser.add_argument("dataset", help="Princeton-format standings file")
    parser.add_argument(
        "--algorithm",
        choices=("edmonds-karp", "dinic"),
        default="dinic",
        help="maximum-flow algorithm (default: dinic)",
    )
    parser.add_argument("--team", help="analyze only one team")
    parser.add_argument(
        "--details",
        action="store_true",
        help="print maximum wins, elimination type, and flow values",
    )
    return parser


def format_result(result: EliminationResult, details: bool = False) -> str:
    if result.eliminated:
        certificate = " ".join(result.certificate)
        first_line = (
            f"{result.team} is eliminated by the subset R = {{ {certificate} }}"
        )
    else:
        first_line = f"{result.team} is not eliminated"

    if not details:
        return first_line

    elimination_type = "trivial" if result.trivial else "nontrivial"
    lines = [
        first_line,
        f"  type: {elimination_type}",
        f"  maximum possible wins: {result.maximum_wins}",
        f"  maximum flow: {result.max_flow} / {result.required_flow}",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        division = BaseballDivision.from_file(args.dataset)
        teams = (args.team,) if args.team else division.teams
        for team in teams:
            print(format_result(division.analyze(team, args.algorithm), args.details))
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
