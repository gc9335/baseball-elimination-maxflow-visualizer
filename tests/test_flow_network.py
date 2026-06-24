import pytest

from baseball_elimination.flow_network import FlowNetwork


def test_add_edge_creates_forward_and_reverse_residual_edges():
    network = FlowNetwork(3)

    network.add_edge(0, 1, 7)

    forward = network.graph[0][0]
    reverse = network.graph[1][0]
    assert (forward.to, forward.capacity, forward.flow) == (1, 7, 0)
    assert (reverse.to, reverse.capacity, reverse.flow) == (0, 0, 0)
    assert network.graph[forward.to][forward.reverse_index] is reverse
    assert network.graph[reverse.to][reverse.reverse_index] is forward


def test_add_flow_updates_forward_and_reverse_edges():
    network = FlowNetwork(2)
    network.add_edge(0, 1, 5)

    network.add_flow(0, 0, 3)

    assert network.graph[0][0].flow == 3
    assert network.graph[1][0].flow == -3
    assert network.graph[0][0].residual_capacity == 2
    assert network.graph[1][0].residual_capacity == 3


def test_source_side_reachable_uses_positive_residual_capacity():
    network = FlowNetwork(3)
    network.add_edge(0, 1, 2)
    network.add_edge(1, 2, 0)

    assert network.source_side(0) == {0, 1}


def test_negative_capacity_is_rejected():
    network = FlowNetwork(2)

    with pytest.raises(ValueError, match="capacity"):
        network.add_edge(0, 1, -1)
