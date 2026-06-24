from baseball_elimination.cli import main


def test_cli_prints_official_teams4_output(capsys):
    exit_code = main(["data/teams4.txt", "--algorithm", "dinic"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.splitlines() == [
        "Atlanta is not eliminated",
        "Philadelphia is eliminated by the subset R = { Atlanta New_York }",
        "New_York is not eliminated",
        "Montreal is eliminated by the subset R = { Atlanta }",
    ]


def test_cli_can_analyze_one_team_with_details(capsys):
    exit_code = main(
        [
            "data/teams4.txt",
            "--algorithm",
            "edmonds-karp",
            "--team",
            "Philadelphia",
            "--details",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Philadelphia is eliminated" in output
    assert "type: nontrivial" in output
    assert "maximum possible wins: 83" in output
    assert "maximum flow: 6 / 7" in output


def test_cli_reports_invalid_file(capsys):
    exit_code = main(["data/does-not-exist.txt"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "error:" in captured.err
