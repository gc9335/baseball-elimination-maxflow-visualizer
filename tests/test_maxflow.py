import random

import pytest

from baseball_elimination.dinic import dinic
from baseball_elimination.edmonds_karp import edmonds_karp
from baseball_elimination.flow_network import FlowNetwork


def build_clrs_network() -> FlowNetwork:
    network = FlowNetwork(6)
    for start, end, capacity in [
        (0, 1, 16),
        (0, 2, 13),
        (1, 2, 10),
        (2, 1, 4),
        (1, 3, 12),
        (3, 2, 9),
        (2, 4, 14),
        (4, 3, 7),
        (3, 5, 20),
        (4, 5, 4),
    ]:
        network.add_edge(start, end, capacity)
    return network


@pytest.mark.parametrize("solver", [edmonds_karp, dinic])
def test_solvers_find_clrs_max_flow(solver):
    assert solver(build_clrs_network(), 0, 5) == 23


def test_edmonds_karp_returns_zero_when_sink_is_unreachable():
    network = FlowNetwork(3)
    network.add_edge(0, 1, 4)

    assert edmonds_karp(network, 0, 2) == 0


def test_edmonds_karp_leaves_correct_min_cut_reachability():
    network = build_clrs_network()

    edmonds_karp(network, 0, 5)

    assert network.source_side(0) == {0, 1, 2, 4}


def solve_edges(
    vertex_count: int,
    edges: list[tuple[int, int, int]],
    solver,
) -> int:
    network = FlowNetwork(vertex_count)
    for start, end, capacity in edges:
        network.add_edge(start, end, capacity)
    return solver(network, 0, vertex_count - 1)


def test_dinic_and_edmonds_karp_match_on_seeded_random_networks():
    for seed in range(20):
        generator = random.Random(seed)
        vertex_count = 8
        edges = []
        for start in range(vertex_count - 1):
            for end in range(start + 1, vertex_count):
                if generator.random() < 0.35:
                    edges.append((start, end, generator.randint(1, 20)))

        assert solve_edges(vertex_count, edges, dinic) == solve_edges(
            vertex_count,
            edges,
            edmonds_karp,
        )
