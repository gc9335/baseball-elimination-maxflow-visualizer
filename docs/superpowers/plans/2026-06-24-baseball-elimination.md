# Baseball Elimination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python implementation of baseball elimination with Edmonds–Karp and optimized Dinic max-flow solvers, official-data tests, reproducible benchmarks, a comparison chart, usage documentation, and a Markdown lab report.

**Architecture:** A shared residual-network type supports two interchangeable max-flow solvers. The baseball layer parses Princeton-format standings, performs trivial elimination, builds one flow network per target team, and extracts a min-cut certificate. Separate scripts download public fixtures and benchmark both algorithms without coupling experimental code to the core implementation.

**Tech Stack:** Python 3.13, standard library, pytest 8, matplotlib 3.10, Git.

---

## File map

- `baseball_elimination/flow_network.py`: residual edge/network primitives and source-side reachability.
- `baseball_elimination/edmonds_karp.py`: BFS augmenting-path baseline.
- `baseball_elimination/dinic.py`: level graph, blocking flow, current-arc optimization.
- `baseball_elimination/baseball.py`: standings model, parser, flow reduction, certificates.
- `baseball_elimination/cli.py`: command-line parsing and human-readable output.
- `main.py`: thin executable entry point.
- `scripts/download_datasets.py`: safe download/extraction of official public fixtures.
- `scripts/benchmark.py`: correctness cross-check, repeated timing, CSV, and PNG chart.
- `tests/`: behavior tests for algorithms, parser, baseball reduction, CLI, and benchmark helpers.
- `README.md`: program instructions.
- `实验报告.md`: final Markdown report populated from measured outputs.

### Task 1: Shared residual network

**Files:**
- Create: `baseball_elimination/__init__.py`
- Create: `baseball_elimination/flow_network.py`
- Create: `tests/test_flow_network.py`

- [ ] **Step 1: Write failing edge/network tests**

```python
from baseball_elimination.flow_network import FlowNetwork


def test_add_edge_creates_forward_and_reverse_residual_edges():
    network = FlowNetwork(3)
    network.add_edge(0, 1, 7)
    forward = network.graph[0][0]
    reverse = network.graph[1][0]
    assert (forward.to, forward.capacity, forward.flow) == (1, 7, 0)
    assert (reverse.to, reverse.capacity, reverse.flow) == (0, 0, 0)
    assert network.graph[forward.to][forward.reverse_index] is reverse


def test_source_side_reachable_uses_positive_residual_capacity():
    network = FlowNetwork(3)
    network.add_edge(0, 1, 2)
    network.add_edge(1, 2, 0)
    assert network.source_side(0) == {0, 1}
```

- [ ] **Step 2: Run tests and verify missing-module failure**

Run: `python -m pytest tests/test_flow_network.py -q`

Expected: FAIL because `baseball_elimination.flow_network` does not exist.

- [ ] **Step 3: Implement the residual network**

Implement:

```python
@dataclass
class Edge:
    to: int
    reverse_index: int
    capacity: int
    flow: int = 0

    @property
    def residual_capacity(self) -> int:
        return self.capacity - self.flow


class FlowNetwork:
    def __init__(self, vertex_count: int): ...
    def add_edge(self, start: int, end: int, capacity: int) -> Edge: ...
    def add_flow(self, start: int, edge_index: int, amount: int) -> None: ...
    def source_side(self, source: int) -> set[int]: ...
```

Reject negative capacities and out-of-range vertices. `add_flow` must update both the forward and reverse edge flows.

- [ ] **Step 4: Run the focused tests**

Run: `python -m pytest tests/test_flow_network.py -q`

Expected: 2 passed.

- [ ] **Step 5: Commit**

```powershell
git add baseball_elimination tests/test_flow_network.py
git commit -m "feat: add residual flow network"
```

### Task 2: Edmonds–Karp baseline

**Files:**
- Create: `baseball_elimination/edmonds_karp.py`
- Create: `tests/test_maxflow.py`

- [ ] **Step 1: Write failing known-network tests**

Use a helper that builds the CLRS six-vertex network with maximum flow 23, plus a disconnected graph with maximum flow 0:

```python
def test_edmonds_karp_finds_clrs_max_flow():
    network = build_clrs_network()
    assert edmonds_karp(network, 0, 5) == 23


def test_edmonds_karp_returns_zero_when_sink_is_unreachable():
    network = FlowNetwork(3)
    network.add_edge(0, 1, 4)
    assert edmonds_karp(network, 0, 2) == 0
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_maxflow.py -k edmonds -q`

Expected: FAIL because `edmonds_karp` is missing.

- [ ] **Step 3: Implement BFS augmentation**

Implement `edmonds_karp(network, source, sink) -> int` with:

1. BFS parent arrays storing `(previous_vertex, edge_index)`.
2. Bottleneck calculation by walking from sink to source.
3. Forward/reverse residual updates through `FlowNetwork.add_flow`.
4. Termination when BFS cannot reach the sink.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_maxflow.py -k edmonds -q`

Expected: Edmonds–Karp tests pass.

- [ ] **Step 5: Commit**

```powershell
git add baseball_elimination/edmonds_karp.py tests/test_maxflow.py
git commit -m "feat: implement edmonds karp max flow"
```

### Task 3: Optimized Dinic solver

**Files:**
- Create: `baseball_elimination/dinic.py`
- Modify: `tests/test_maxflow.py`

- [ ] **Step 1: Add failing Dinic and cross-solver tests**

```python
@pytest.mark.parametrize("solver", [edmonds_karp, dinic])
def test_solvers_find_clrs_max_flow(solver):
    assert solver(build_clrs_network(), 0, 5) == 23


def test_dinic_and_edmonds_karp_match_on_seeded_random_networks():
    for seed in range(20):
        edges = random_edges(seed)
        assert solve(edges, edmonds_karp) == solve(edges, dinic)
```

Include a network where reverse residual edges are required to reach the optimum.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_maxflow.py -q`

Expected: FAIL because `dinic` is missing.

- [ ] **Step 3: Implement Dinic**

Implement:

```python
def dinic(network: FlowNetwork, source: int, sink: int) -> int:
    # BFS level graph
    # current_edge[v] stores the next edge index to inspect
    # DFS only traverses edges with level[to] == level[v] + 1
    # repeat blocking-flow phases until sink is unreachable
```

Use integer capacities and a safe per-network infinity value such as the sum of outgoing source capacities plus one.

- [ ] **Step 4: Verify both solvers**

Run: `python -m pytest tests/test_maxflow.py -q`

Expected: all known and randomized max-flow tests pass.

- [ ] **Step 5: Commit**

```powershell
git add baseball_elimination/dinic.py tests/test_maxflow.py
git commit -m "feat: implement optimized dinic max flow"
```

### Task 4: Princeton standings parser

**Files:**
- Create: `baseball_elimination/baseball.py`
- Create: `data/teams4.txt`
- Create: `data/teams5.txt`
- Create: `tests/test_parser.py`

- [ ] **Step 1: Add official example fixtures**

Store the exact `teams4.txt` and `teams5.txt` examples published by Princeton.

- [ ] **Step 2: Write failing parser/API tests**

Test:

```python
division = BaseballDivision.from_file("data/teams4.txt")
assert division.number_of_teams == 4
assert division.teams == ("Atlanta", "Philadelphia", "New_York", "Montreal")
assert division.wins("Atlanta") == 83
assert division.losses("Montreal") == 82
assert division.remaining("New_York") == 6
assert division.against("Atlanta", "New_York") == 6
```

Also test duplicate names, wrong field count, negative values, asymmetric matrices, nonzero diagonal, and `remaining < sum(in-division games)`. Explicitly accept `remaining > row sum`, as allowed by the official specification.

- [ ] **Step 3: Verify RED**

Run: `python -m pytest tests/test_parser.py -q`

Expected: FAIL because `BaseballDivision` is missing.

- [ ] **Step 4: Implement immutable standings data**

Implement `BaseballDivision.from_file(path)` and query methods. Store names and numeric data as tuples, map names to indices, and raise `ValueError` with the filename/line context for invalid files and `KeyError` for unknown teams.

- [ ] **Step 5: Verify parser**

Run: `python -m pytest tests/test_parser.py -q`

Expected: all parser tests pass.

- [ ] **Step 6: Commit**

```powershell
git add baseball_elimination/baseball.py data tests/test_parser.py
git commit -m "feat: parse baseball standings data"
```

### Task 5: Baseball elimination reduction and certificate

**Files:**
- Modify: `baseball_elimination/baseball.py`
- Create: `tests/test_baseball.py`

- [ ] **Step 1: Write failing `teams4` expectations**

```python
EXPECTED = {
    "Atlanta": (False, ()),
    "Philadelphia": (True, ("Atlanta", "New_York")),
    "New_York": (False, ()),
    "Montreal": (True, ("Atlanta",)),
}

@pytest.mark.parametrize("algorithm", ["edmonds-karp", "dinic"])
def test_teams4_matches_official_output(algorithm):
    division = BaseballDivision.from_file("data/teams4.txt")
    for team, expected in EXPECTED.items():
        result = division.analyze(team, algorithm)
        assert (result.eliminated, result.certificate) == expected
```

Add `teams5` expectations: only Detroit is eliminated, certified by all four other teams.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_baseball.py -q`

Expected: FAIL because `analyze` and `EliminationResult` are missing.

- [ ] **Step 3: Implement direct elimination**

Create immutable:

```python
@dataclass(frozen=True)
class EliminationResult:
    team: str
    eliminated: bool
    trivial: bool
    maximum_wins: int
    max_flow: int
    required_flow: int
    certificate: tuple[str, ...]
```

If any `wins[i] > wins[x] + remaining[x]`, return a direct certificate containing all such teams in input order.

- [ ] **Step 4: Verify direct-elimination test**

Run: `python -m pytest tests/test_baseball.py -k Montreal -q`

Expected: Montreal test passes.

- [ ] **Step 5: Implement nontrivial network construction**

For target `x`:

1. Enumerate every pair `i < j`, excluding pairs involving `x`.
2. Create source, game vertices, team vertices, and sink.
3. Add source-game capacities `g[i][j]`.
4. Add game-team capacities equal to `required_flow + 1`.
5. Add team-sink capacities `maximum_wins - wins[i]`.
6. Run the selected solver.
7. If `max_flow < required_flow`, obtain source-side reachable team vertices as the certificate.

- [ ] **Step 6: Verify all baseball tests**

Run: `python -m pytest tests/test_baseball.py -q`

Expected: both algorithms match official `teams4` and `teams5` output.

- [ ] **Step 7: Add solver-consistency property test**

Generate small, symmetric, seeded schedules and assert both solvers return the same elimination boolean, maximum flow, and required flow for every team.

- [ ] **Step 8: Commit**

```powershell
git add baseball_elimination/baseball.py tests/test_baseball.py
git commit -m "feat: solve baseball elimination with max flow"
```

### Task 6: Command-line program

**Files:**
- Create: `baseball_elimination/cli.py`
- Create: `main.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Test the official compact output and a detailed mode:

```python
exit_code = main(["data/teams4.txt", "--algorithm", "dinic"])
assert exit_code == 0
assert "Atlanta is not eliminated" in captured.out
assert "Philadelphia is eliminated by the subset R = { Atlanta New_York }" in captured.out
```

Also assert invalid files return a nonzero code and print a concise error to stderr.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_cli.py -q`

Expected: FAIL because CLI modules are missing.

- [ ] **Step 3: Implement CLI**

Arguments:

```text
dataset
--algorithm {edmonds-karp,dinic}
--team TEAM
--details
```

Default algorithm is Dinic. Without `--team`, print all teams in input order. With `--details`, additionally print direct/nontrivial status and `max_flow / required_flow`.

- [ ] **Step 4: Verify CLI**

Run: `python -m pytest tests/test_cli.py -q`

Expected: all CLI tests pass.

- [ ] **Step 5: Commit**

```powershell
git add baseball_elimination/cli.py main.py tests/test_cli.py
git commit -m "feat: add baseball elimination command line interface"
```

### Task 7: Official Princeton datasets

**Files:**
- Create: `scripts/download_datasets.py`
- Create: `tests/test_download_datasets.py`
- Populate: `data/princeton/`

- [ ] **Step 1: Write failing safe-extraction tests**

Test that ZIP members resolving outside the destination are rejected, `.txt` fixtures are extracted, and an existing valid file is not corrupted by a failed download.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_download_datasets.py -q`

Expected: FAIL because downloader helpers are missing.

- [ ] **Step 3: Implement downloader**

Use `urllib.request` and `zipfile`. Download the official assignment archive from:

```text
https://coursera.cs.princeton.edu/algs4/assignments/baseball/baseball.zip
```

Write to a temporary file, validate ZIP paths, extract only `.txt` test fixtures into `data/princeton/`, then atomically replace destination files.

- [ ] **Step 4: Verify downloader helpers**

Run: `python -m pytest tests/test_download_datasets.py -q`

Expected: all safe extraction tests pass.

- [ ] **Step 5: Download official fixtures**

Run: `python scripts/download_datasets.py`

Expected: prints downloaded/extracted dataset names including `teams4.txt`, `teams5.txt`, and `teams12.txt`.

- [ ] **Step 6: Parse every official text dataset**

Run a Python one-liner that loads all matching `data/princeton/teams*.txt` files and prints their team counts.

Expected: all files parse without error.

- [ ] **Step 7: Commit**

```powershell
git add scripts/download_datasets.py tests/test_download_datasets.py data/princeton
git commit -m "test: add official princeton baseball datasets"
```

### Task 8: Benchmarking and chart generation

**Files:**
- Create: `scripts/benchmark.py`
- Create: `tests/test_benchmark.py`
- Create: `output/.gitkeep`
- Create at runtime: `output/benchmark_results.csv`
- Create at runtime: `output/maxflow_comparison.png`
- Create at runtime: `output/test_results.txt`

- [ ] **Step 1: Read the static chart template guidance**

Read `data-analytics:visualize-data/references/seaborn-templates.md` before implementing the static chart, then use matplotlib in the same restrained visual style because matplotlib is already available.

- [ ] **Step 2: Write failing benchmark helper tests**

Test deterministic random divisions, median calculation, solver equality validation, CSV headers, and creation of a nonempty PNG from a tiny synthetic result set.

- [ ] **Step 3: Verify RED**

Run: `python -m pytest tests/test_benchmark.py -q`

Expected: FAIL because benchmark helpers are missing.

- [ ] **Step 4: Implement official-data and synthetic benchmarks**

Benchmark contract:

- Analytical question: how much faster is Dinic than Edmonds–Karp as the baseball network grows?
- Takeaway to test: Dinic should scale better on larger/dense cases while matching all results.
- Chart: grouped vertical bar chart of median elapsed milliseconds by dataset/size.
- Repetitions: default 5, one untimed warm-up.
- Synthetic sizes: deterministic divisions such as 8, 12, 16, 20, 24, and 28 teams.
- Output CSV fields: `category,dataset,teams,algorithm,repeat,elapsed_ms`.

- [ ] **Step 5: Verify benchmark helpers**

Run: `python -m pytest tests/test_benchmark.py -q`

Expected: all benchmark tests pass.

- [ ] **Step 6: Run the benchmark**

Run: `python scripts/benchmark.py --repeats 5`

Expected: both algorithms agree; CSV, PNG, and text summary are generated.

- [ ] **Step 7: Visually inspect the chart**

Open `output/maxflow_comparison.png` and verify title, units, labels, legend, bar separation, and no clipping. Revise plotting code if necessary, then rerun the benchmark.

- [ ] **Step 8: Commit benchmark source**

Generated output remains ignored because it is reproducible.

```powershell
git add scripts/benchmark.py tests/test_benchmark.py output/.gitkeep
git commit -m "feat: benchmark max flow implementations"
```

### Task 9: Program instructions and experiment report

**Files:**
- Create: `requirements.txt`
- Create: `README.md`
- Create: `实验报告.md`

- [ ] **Step 1: Record actual program output**

Run:

```powershell
python main.py data/teams4.txt --algorithm dinic --details
python main.py data/teams5.txt --algorithm dinic --details
python main.py data/princeton/teams12.txt --algorithm dinic --details
```

Use only measured output in documentation.

- [ ] **Step 2: Calculate certificate arithmetic**

For each important eliminated team, especially Japan in `teams12.txt`, calculate:

```text
sum(current wins in R) + sum(remaining games entirely inside R)
```

Compare the average forced final wins of `R` with the target's maximum possible wins.

- [ ] **Step 3: Write README**

Include environment, installation, directory map, input format, CLI examples, testing command, benchmark command, and generated-file locations.

- [ ] **Step 4: Write the Markdown report**

Include:

1. Experiment objective.
2. Problem and notation.
3. Network construction.
4. Correctness argument in both directions.
5. Max-flow/min-cut certificate explanation.
6. Edmonds–Karp and Dinic pseudocode, complexity, and optimizations.
7. Four-team result table.
8. Official dataset test summary.
9. Benchmark method and measured table.
10. Embedded chart: `![最大流算法性能对比](output/maxflow_comparison.png)`.
11. Interpretation, limitations, and conclusion.

For one target team, the baseball network has `O(n²)` vertices and `O(n²)` logical edges. Under the assignment's Edmonds–Karp assumption `O(VE²)`, one elimination test is `O(n⁶)` and checking all teams is `O(n⁷)`.

- [ ] **Step 5: Commit documentation**

```powershell
git add requirements.txt README.md 实验报告.md
git commit -m "docs: add program guide and experiment report"
```

### Task 10: Final verification

**Files:**
- Review all project files.

- [ ] **Step 1: Run the complete test suite**

Run: `python -m pytest -q`

Expected: zero failures.

- [ ] **Step 2: Compile all Python modules**

Run:

```powershell
python -m compileall -q baseball_elimination scripts main.py
```

Expected: exit code 0.

- [ ] **Step 3: Re-run official examples**

Run:

```powershell
python main.py data/teams4.txt --algorithm edmonds-karp
python main.py data/teams4.txt --algorithm dinic
```

Expected: both outputs match Princeton's published four-team output.

- [ ] **Step 4: Re-run benchmark artifacts**

Run: `python scripts/benchmark.py --repeats 5`

Expected: algorithm results agree and all three output artifacts are regenerated.

- [ ] **Step 5: Check repository status and history**

Run:

```powershell
git status --short
git log --oneline --decorate -10
```

Expected: only ignored generated artifacts are untracked; source and documentation changes are committed.

- [ ] **Step 6: Requirements audit**

Confirm each user requirement maps to an implemented file, passing test, measured output, and report section before claiming completion.
