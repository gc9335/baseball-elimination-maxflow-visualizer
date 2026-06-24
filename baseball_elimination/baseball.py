"""Standings parsing and baseball-elimination analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class BaseballDivision:
    """Immutable standings for one sports division."""

    teams: tuple[str, ...]
    _wins: tuple[int, ...]
    _losses: tuple[int, ...]
    _remaining: tuple[int, ...]
    _games: tuple[tuple[int, ...], ...]
    _index: Mapping[str, int]

    @classmethod
    def from_file(cls, path: str | Path) -> "BaseballDivision":
        file_path = Path(path)
        try:
            lines = [
                line.strip()
                for line in file_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except OSError as exc:
            raise ValueError(f"cannot read standings file {file_path}: {exc}") from exc

        if not lines:
            raise ValueError(f"{file_path}: missing team count")
        header = lines[0].split()
        if len(header) != 1:
            raise ValueError(f"{file_path}: first line must contain only the team count")
        try:
            team_count = int(header[0])
        except ValueError as exc:
            raise ValueError(f"{file_path}: invalid team count") from exc
        if team_count < 1:
            raise ValueError(f"{file_path}: team count must be positive")
        if len(lines) - 1 != team_count:
            raise ValueError(
                f"{file_path}: expected {team_count} team rows, found {len(lines) - 1}"
            )

        names: list[str] = []
        wins: list[int] = []
        losses: list[int] = []
        remaining: list[int] = []
        games: list[tuple[int, ...]] = []

        for line_number, line in enumerate(lines[1:], start=2):
            fields = line.split()
            expected_fields = team_count + 4
            if len(fields) != expected_fields:
                raise ValueError(
                    f"{file_path}:{line_number}: expected {expected_fields} fields, "
                    f"found {len(fields)}"
                )
            name = fields[0]
            if name in names:
                raise ValueError(f"{file_path}:{line_number}: duplicate team {name!r}")
            try:
                numbers = tuple(int(value) for value in fields[1:])
            except ValueError as exc:
                raise ValueError(
                    f"{file_path}:{line_number}: statistics must be integers"
                ) from exc
            if any(value < 0 for value in numbers):
                raise ValueError(
                    f"{file_path}:{line_number}: statistics must be nonnegative"
                )

            names.append(name)
            wins.append(numbers[0])
            losses.append(numbers[1])
            remaining.append(numbers[2])
            games.append(numbers[3:])

        for index, row in enumerate(games):
            if row[index] != 0:
                raise ValueError(
                    f"{file_path}: schedule matrix diagonal must be zero"
                )
            if remaining[index] < sum(row):
                raise ValueError(
                    f"{file_path}: remaining games for {names[index]} are smaller "
                    "than its in-division schedule"
                )
            for opponent in range(index + 1, team_count):
                if row[opponent] != games[opponent][index]:
                    raise ValueError(
                        f"{file_path}: schedule matrix must be symmetric"
                    )

        name_to_index = MappingProxyType(
            {name: index for index, name in enumerate(names)}
        )
        return cls(
            tuple(names),
            tuple(wins),
            tuple(losses),
            tuple(remaining),
            tuple(games),
            name_to_index,
        )

    @property
    def number_of_teams(self) -> int:
        return len(self.teams)

    def _team_index(self, team: str) -> int:
        try:
            return self._index[team]
        except KeyError as exc:
            raise KeyError(f"Unknown team: {team}") from exc

    def wins(self, team: str) -> int:
        return self._wins[self._team_index(team)]

    def losses(self, team: str) -> int:
        return self._losses[self._team_index(team)]

    def remaining(self, team: str) -> int:
        return self._remaining[self._team_index(team)]

    def against(self, team1: str, team2: str) -> int:
        return self._games[self._team_index(team1)][self._team_index(team2)]
