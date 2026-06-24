"""Standings parsing and baseball-elimination analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from .dinic import dinic
from .edmonds_karp import edmonds_karp
from .flow_network import FlowNetwork
from .tracing import AlgorithmMetrics, TraceRecorder, snapshot_network


@dataclass(frozen=True)
class EliminationResult:
    """Result and max-flow certificate for one target team."""

    team: str
    eliminated: bool
    trivial: bool
    maximum_wins: int
    max_flow: int
    required_flow: int
    certificate: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["certificate"] = list(self.certificate)
        return value


@dataclass(frozen=True)
class NetworkNode:
    id: int
    kind: str
    label: str
    team: str | None = None
    teams: tuple[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        if self.teams is not None:
            value["teams"] = list(self.teams)
        return value


@dataclass(frozen=True)
class NetworkEdge:
    id: int
    start: int
    end: int
    capacity: int
    kind: str
    edge_index: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BuiltEliminationNetwork:
    target_team: str
    maximum_wins: int
    required_flow: int
    source: int
    sink: int
    network: FlowNetwork
    nodes: tuple[NetworkNode, ...]
    edges: tuple[NetworkEdge, ...]
    team_vertices: Mapping[int, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_team": self.target_team,
            "maximum_wins": self.maximum_wins,
            "required_flow": self.required_flow,
            "source": self.source,
            "sink": self.sink,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }


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

    def _solver(
        self,
        algorithm: str,
    ) -> Callable[..., int]:
        solvers: dict[str, Callable[..., int]] = {
            "edmonds-karp": edmonds_karp,
            "dinic": dinic,
        }
        try:
            return solvers[algorithm]
        except KeyError as exc:
            choices = ", ".join(solvers)
            raise ValueError(
                f"unknown algorithm {algorithm!r}; choose one of: {choices}"
            ) from exc

    def _trivial_certificate(self, target: int, maximum_wins: int) -> tuple[str, ...]:
        return tuple(
            name
            for index, name in enumerate(self.teams)
            if index != target and self._wins[index] > maximum_wins
        )

    def build_elimination_network(self, team: str) -> BuiltEliminationNetwork:
        """Construct and describe the nontrivial baseball flow network."""

        target = self._team_index(team)
        maximum_wins = self._wins[target] + self._remaining[target]
        opponents = [index for index in range(self.number_of_teams) if index != target]
        game_pairs = [
            (first, second)
            for pair_index, first in enumerate(opponents)
            for second in opponents[pair_index + 1 :]
        ]
        source = 0
        first_game_vertex = 1
        first_team_vertex = first_game_vertex + len(game_pairs)
        team_vertices = MappingProxyType(
            {
                team_index: first_team_vertex + offset
                for offset, team_index in enumerate(opponents)
            }
        )
        sink = first_team_vertex + len(opponents)
        network = FlowNetwork(sink + 1)
        nodes: list[NetworkNode] = [NetworkNode(source, "source", "Source")]
        edges: list[NetworkEdge] = []

        for offset, (first, second) in enumerate(game_pairs):
            game_vertex = first_game_vertex + offset
            nodes.append(
                NetworkNode(
                    game_vertex,
                    "game",
                    f"{self.teams[first]} vs {self.teams[second]}",
                    teams=(self.teams[first], self.teams[second]),
                )
            )

        for opponent in opponents:
            nodes.append(
                NetworkNode(
                    team_vertices[opponent],
                    "team",
                    self.teams[opponent],
                    team=self.teams[opponent],
                )
            )
        nodes.append(NetworkNode(sink, "sink", "Sink"))

        required_flow = sum(self._games[first][second] for first, second in game_pairs)
        infinite_capacity = required_flow + 1

        def add_described_edge(start: int, end: int, capacity: int, kind: str) -> None:
            edge_index = len(network.graph[start])
            network.add_edge(start, end, capacity)
            edges.append(
                NetworkEdge(
                    id=len(edges),
                    start=start,
                    end=end,
                    capacity=capacity,
                    kind=kind,
                    edge_index=edge_index,
                )
            )

        for offset, (first, second) in enumerate(game_pairs):
            game_vertex = first_game_vertex + offset
            add_described_edge(
                source,
                game_vertex,
                self._games[first][second],
                "source-game",
            )
            add_described_edge(
                game_vertex,
                team_vertices[first],
                infinite_capacity,
                "game-team",
            )
            add_described_edge(
                game_vertex,
                team_vertices[second],
                infinite_capacity,
                "game-team",
            )

        for opponent in opponents:
            capacity = maximum_wins - self._wins[opponent]
            if capacity < 0:
                raise ValueError(
                    f"{team} is trivially eliminated by {self.teams[opponent]}"
                )
            add_described_edge(
                team_vertices[opponent],
                sink,
                capacity,
                "team-sink",
            )

        return BuiltEliminationNetwork(
            target_team=team,
            maximum_wins=maximum_wins,
            required_flow=required_flow,
            source=source,
            sink=sink,
            network=network,
            nodes=tuple(nodes),
            edges=tuple(edges),
            team_vertices=team_vertices,
        )

    def analyze(
        self,
        team: str,
        algorithm: str = "dinic",
    ) -> EliminationResult:
        """Determine whether team is mathematically eliminated."""

        solver = self._solver(algorithm)

        target = self._team_index(team)
        maximum_wins = self._wins[target] + self._remaining[target]
        trivial_certificate = self._trivial_certificate(target, maximum_wins)
        if trivial_certificate:
            return EliminationResult(
                team,
                True,
                True,
                maximum_wins,
                0,
                0,
                trivial_certificate,
            )

        built = self.build_elimination_network(team)
        maximum_flow = solver(built.network, built.source, built.sink)
        eliminated = maximum_flow < built.required_flow
        certificate: tuple[str, ...] = ()
        if eliminated:
            source_side = built.network.source_side(built.source)
            certificate = tuple(
                self.teams[opponent]
                for opponent, vertex in built.team_vertices.items()
                if vertex in source_side
            )

        return EliminationResult(
            team,
            eliminated,
            False,
            maximum_wins,
            maximum_flow,
            built.required_flow,
            certificate,
        )

    def _standings_dict(self) -> dict[str, Any]:
        return {
            "teams": [
                {
                    "name": name,
                    "wins": self._wins[index],
                    "losses": self._losses[index],
                    "remaining": self._remaining[index],
                    "games": list(self._games[index]),
                }
                for index, name in enumerate(self.teams)
            ]
        }

    def trace_analysis(self, team: str, algorithm: str = "dinic") -> dict[str, Any]:
        """Run an analysis and return a browser-ready trace payload."""

        solver = self._solver(algorithm)
        target = self._team_index(team)
        maximum_wins = self._wins[target] + self._remaining[target]
        trivial_certificate = self._trivial_certificate(target, maximum_wins)
        recorder = TraceRecorder(algorithm)
        metrics = AlgorithmMetrics()

        if trivial_certificate:
            recorder.emit(
                "trivial-check",
                "直接淘汰检查",
                f"{', '.join(trivial_certificate)} 已经超过 {team} 的最大可能胜场 "
                f"{maximum_wins}。",
                "trivial-check",
                certificate=list(trivial_certificate),
                maximum_wins=maximum_wins,
            )
            result = EliminationResult(
                team,
                True,
                True,
                maximum_wins,
                0,
                0,
                trivial_certificate,
            )
            recorder.emit(
                "completed",
                f"{team} 被直接淘汰",
                "无需构造最大流网络。",
                "terminate",
                result=result.to_dict(),
                metrics=metrics.to_dict(),
            )
            return {
                "schema": "baseball-maxflow-trace.v1",
                "algorithm": algorithm,
                "target_team": team,
                "standings": self._standings_dict(),
                "network": None,
                "events": recorder.to_list(),
                "metrics": metrics.to_dict(),
                "result": result.to_dict(),
            }

        built = self.build_elimination_network(team)
        recorder.emit(
            "network-built",
            "完成棒球淘汰流网络",
            f"需要分配的比赛总数为 {built.required_flow}。",
            "build-network",
            current_flow=0,
            edges=snapshot_network(built.network),
            required_flow=built.required_flow,
        )
        maximum_flow = solver(
            built.network,
            built.source,
            built.sink,
            recorder=recorder,
            metrics=metrics,
        )
        eliminated = maximum_flow < built.required_flow
        certificate: tuple[str, ...] = ()
        source_side = built.network.source_side(built.source)
        if eliminated:
            certificate = tuple(
                self.teams[opponent]
                for opponent, vertex in built.team_vertices.items()
                if vertex in source_side
            )
            recorder.emit(
                "min-cut",
                "提取最小割证明集合",
                f"源侧可达球队为 {', '.join(certificate)}。",
                "min-cut",
                current_flow=maximum_flow,
                source_side=sorted(source_side),
                certificate=list(certificate),
                edges=snapshot_network(built.network),
            )

        result = EliminationResult(
            team,
            eliminated,
            False,
            maximum_wins,
            maximum_flow,
            built.required_flow,
            certificate,
        )
        recorder.emit(
            "completed",
            f"{team} {'被淘汰' if eliminated else '仍有机会'}",
            f"最大流 {maximum_flow} / 待分配比赛 {built.required_flow}。",
            "terminate",
            current_flow=maximum_flow,
            source_side=sorted(source_side),
            edges=snapshot_network(built.network),
            metrics=metrics.to_dict(),
            result=result.to_dict(),
        )

        return {
            "schema": "baseball-maxflow-trace.v1",
            "algorithm": algorithm,
            "target_team": team,
            "standings": self._standings_dict(),
            "network": built.to_dict(),
            "events": recorder.to_list(),
            "metrics": metrics.to_dict(),
            "result": result.to_dict(),
        }
