import random

import pytest

from baseball_elimination.baseball import BaseballDivision


TEAMS4_EXPECTED = {
    "Atlanta": (False, ()),
    "Philadelphia": (True, ("Atlanta", "New_York")),
    "New_York": (False, ()),
    "Montreal": (True, ("Atlanta",)),
}


@pytest.mark.parametrize("algorithm", ["edmonds-karp", "dinic"])
def test_teams4_matches_official_output(algorithm):
    division = BaseballDivision.from_file("data/teams4.txt")

    for team, expected in TEAMS4_EXPECTED.items():
        result = division.analyze(team, algorithm)
        assert (result.eliminated, result.certificate) == expected


@pytest.mark.parametrize("algorithm", ["edmonds-karp", "dinic"])
def test_teams5_matches_official_output(algorithm):
    division = BaseballDivision.from_file("data/teams5.txt")

    for team in ("New_York", "Baltimore", "Boston", "Toronto"):
        assert not division.analyze(team, algorithm).eliminated
    detroit = division.analyze("Detroit", algorithm)
    assert detroit.eliminated
    assert detroit.certificate == (
        "New_York",
        "Baltimore",
        "Boston",
        "Toronto",
    )


def make_random_division(seed: int, team_count: int = 7) -> BaseballDivision:
    generator = random.Random(seed)
    games = [[0] * team_count for _ in range(team_count)]
    for first in range(team_count):
        for second in range(first + 1, team_count):
            games[first][second] = games[second][first] = generator.randint(0, 5)
    remaining = tuple(sum(row) + generator.randint(0, 3) for row in games)
    return BaseballDivision(
        tuple(f"T{index}" for index in range(team_count)),
        tuple(generator.randint(20, 80) for _ in range(team_count)),
        tuple(generator.randint(20, 80) for _ in range(team_count)),
        remaining,
        tuple(tuple(row) for row in games),
        {f"T{index}": index for index in range(team_count)},
    )


def test_solvers_agree_on_seeded_baseball_divisions():
    for seed in range(12):
        division = make_random_division(seed)
        for team in division.teams:
            baseline = division.analyze(team, "edmonds-karp")
            optimized = division.analyze(team, "dinic")
            assert baseline.eliminated == optimized.eliminated
            assert baseline.maximum_wins == optimized.maximum_wins
            assert baseline.max_flow == optimized.max_flow
            assert baseline.required_flow == optimized.required_flow


def test_unknown_algorithm_is_rejected():
    division = BaseballDivision.from_file("data/teams4.txt")

    with pytest.raises(ValueError, match="algorithm"):
        division.analyze("Atlanta", "ford-fulkerson")
