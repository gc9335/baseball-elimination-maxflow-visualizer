"""Trace events and operation counters for maximum-flow algorithms."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .flow_network import FlowNetwork


@dataclass(frozen=True)
class TraceEvent:
    step: int
    type: str
    title: str
    detail: str
    pseudocode_line: str | None
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AlgorithmMetrics:
    bfs_rounds: int = 0
    dfs_calls: int = 0
    edge_inspections: int = 0
    queue_pushes: int = 0
    augmentations: int = 0
    blocking_flow_pushes: int = 0
    current_arc_skips: int = 0
    reverse_edge_uses: int = 0
    level_phases: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)

    def add(self, other: "AlgorithmMetrics") -> None:
        for name in self.to_dict():
            setattr(self, name, getattr(self, name) + getattr(other, name))


@dataclass
class TraceRecorder:
    algorithm: str
    events: list[TraceEvent] = field(default_factory=list)

    def emit(
        self,
        event_type: str,
        title: str,
        detail: str = "",
        pseudocode_line: str | None = None,
        **payload: Any,
    ) -> TraceEvent:
        event = TraceEvent(
            step=len(self.events),
            type=event_type,
            title=title,
            detail=detail,
            pseudocode_line=pseudocode_line,
            payload=payload,
        )
        self.events.append(event)
        return event

    def to_list(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.events]


def snapshot_network(network: FlowNetwork) -> list[dict[str, int]]:
    """Return forward logical edges and their current residual state."""

    edges: list[dict[str, int]] = []
    for start, adjacency in enumerate(network.graph):
        for edge_index, edge in enumerate(adjacency):
            if edge.capacity <= 0:
                continue
            edges.append(
                {
                    "id": len(edges),
                    "start": start,
                    "end": edge.to,
                    "edge_index": edge_index,
                    "capacity": edge.capacity,
                    "flow": edge.flow,
                    "residual": edge.residual_capacity,
                }
            )
    return edges
