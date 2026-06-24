from pathlib import Path

import pytest

from baseball_elimination.baseball import BaseballDivision


def write_dataset(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "division.txt"
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_official_teams4_dataset():
    division = BaseballDivision.from_file("data/teams4.txt")

    assert division.number_of_teams == 4
    assert division.teams == (
        "Atlanta",
        "Philadelphia",
        "New_York",
        "Montreal",
    )
    assert division.wins("Atlanta") == 83
    assert division.losses("Montreal") == 82
    assert division.remaining("New_York") == 6
    assert division.against("Atlanta", "New_York") == 6


def test_remaining_may_include_games_outside_the_division(tmp_path):
    path = write_dataset(
        tmp_path,
        "2\nA 5 2 3 0 1\nB 4 3 2 1 0\n",
    )

    division = BaseballDivision.from_file(path)

    assert division.remaining("A") == 3
    assert division.remaining("B") == 2


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("2\nA 1 1 0 0 0\n", "expected 2 team rows"),
        ("2\nA 1 1 0 0 0\nA 1 1 0 0 0\n", "duplicate"),
        ("2\nA 1 1 0 0 0\nB 1 1 0 1\n", "fields"),
        ("2\nA -1 1 0 0 0\nB 1 1 0 0 0\n", "nonnegative"),
        ("2\nA 1 1 0 1 0\nB 1 1 0 0 0\n", "diagonal"),
        ("2\nA 1 1 1 0 1\nB 1 1 0 0 0\n", "symmetric"),
        ("2\nA 1 1 0 0 1\nB 1 1 1 1 0\n", "remaining"),
    ],
)
def test_invalid_datasets_are_rejected(tmp_path, text, message):
    path = write_dataset(tmp_path, text)

    with pytest.raises(ValueError, match=message):
        BaseballDivision.from_file(path)


def test_unknown_team_is_rejected():
    division = BaseballDivision.from_file("data/teams4.txt")

    with pytest.raises(KeyError, match="Unknown"):
        division.wins("Unknown")
