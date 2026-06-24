# Maxflow Visualizer and Extended Benchmarks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add traceable Python max-flow solvers, a GitHub Pages teaching visualizer, richer benchmark metrics, six additional performance charts, and updated documentation.

**Architecture:** Python remains the only algorithm implementation and emits typed trace events plus operation counters. A build script converts bundled baseball datasets and solver traces into static JSON under `docs/data`; a dependency-free HTML/CSS/JavaScript site replays those snapshots. The benchmark pipeline records timing, operation and memory metrics in tidy CSV files and renders report-ready PNG charts.

**Tech Stack:** Python 3.13, pytest, tracemalloc, Matplotlib, Seaborn, static HTML/CSS/ES modules, SVG, GitHub Pages and GitHub Actions.

---

## File map

- `baseball_elimination/tracing.py`: trace event, metrics, edge snapshot and recorder types.
- `baseball_elimination/edmonds_karp.py`: optional trace/metrics instrumentation.
- `baseball_elimination/dinic.py`: optional trace/metrics instrumentation.
- `baseball_elimination/baseball.py`: reusable baseball-network construction metadata.
- `scripts/export_visualizer_data.py`: build static manifest and trace JSON.
- `scripts/benchmark.py`: extended datasets, metrics, CSV and chart generation.
- `docs/index.html`: static application shell.
- `docs/styles.css`: warm paper visual system and responsive layout.
- `docs/app.js`: state, SVG rendering, controls, tabs and timeline.
- `docs/data/*.json`: generated bundled dataset and trace payloads.
- `docs/output/*.png`: generated performance charts.
- `.github/workflows/pages.yml`: Pages deployment workflow.
- `tests/test_tracing.py`: trace and counter behavior.
- `tests/test_visualizer_export.py`: generated-data contract.
- `tests/test_benchmark.py`: expanded metrics/chart contract.
- `tests/test_pages_site.py`: static site file/manifest checks.
- `README.md`, `实验报告.md`: usage, methodology and measured results.

### Task 1: Isolated feature workspace

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Ignore generated local preview state**

Ensure `.worktrees/`, `.superpowers/`, `.pytest-tmp/` and Python caches remain ignored.

- [ ] **Step 2: Create feature worktree**

Run:

```powershell
git worktree add .worktrees/maxflow-visualizer -b feature/maxflow-visualizer
```

Expected: worktree on `feature/maxflow-visualizer`.

- [ ] **Step 3: Verify baseline**

Run:

```powershell
python -m pytest -q
```

Expected: 36 tests pass.

### Task 2: Trace and metrics primitives

**Files:**
- Create: `baseball_elimination/tracing.py`
- Create: `tests/test_tracing.py`

- [ ] **Step 1: Write failing trace recorder tests**

```python
from baseball_elimination.tracing import AlgorithmMetrics, TraceRecorder


def test_trace_recorder_assigns_contiguous_steps():
    recorder = TraceRecorder("edmonds-karp")
    recorder.emit("search-start", "开始 BFS")
    recorder.emit("path-found", "找到增广路", path=[0, 1, 2])
    assert [event.step for event in recorder.events] == [0, 1]
    assert recorder.events[1].payload["path"] == [0, 1, 2]


def test_metrics_export_contains_common_and_algorithm_fields():
    metrics = AlgorithmMetrics()
    metrics.edge_inspections = 5
    metrics.bfs_rounds = 2
    assert metrics.to_dict()["edge_inspections"] == 5
    assert metrics.to_dict()["bfs_rounds"] == 2
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_tracing.py -q`

Expected: import failure for `baseball_elimination.tracing`.

- [ ] **Step 3: Implement immutable events and mutable counters**

Create:

```python
@dataclass(frozen=True)
class TraceEvent:
    step: int
    type: str
    title: str
    detail: str
    pseudocode_line: str | None
    payload: dict[str, object]


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


class TraceRecorder:
    def emit(self, event_type, title, detail="", pseudocode_line=None, **payload): ...
```

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/test_tracing.py -q`

Expected: tests pass.

- [ ] **Step 5: Commit**

```powershell
git add baseball_elimination/tracing.py tests/test_tracing.py
git commit -m "feat: add maxflow trace and metrics primitives"
```

### Task 3: Instrument Edmonds–Karp

**Files:**
- Modify: `baseball_elimination/edmonds_karp.py`
- Modify: `tests/test_tracing.py`

- [ ] **Step 1: Write failing instrumented-solver test**

```python
def test_edmonds_karp_emits_search_path_augment_and_completion_events():
    recorder = TraceRecorder("edmonds-karp")
    metrics = AlgorithmMetrics()
    value = edmonds_karp(build_network(), 0, 3, recorder=recorder, metrics=metrics)
    assert value == 5
    assert {"search-start", "path-found", "augment", "completed"} <= {
        event.type for event in recorder.events
    }
    assert metrics.bfs_rounds >= 1
    assert metrics.augmentations >= 1
    assert metrics.edge_inspections >= metrics.augmentations
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_tracing.py -k edmonds -q`

Expected: unexpected keyword argument `recorder`.

- [ ] **Step 3: Add optional instrumentation without changing default API behavior**

Change signature to:

```python
def edmonds_karp(
    network: FlowNetwork,
    source: int,
    sink: int,
    *,
    recorder: TraceRecorder | None = None,
    metrics: AlgorithmMetrics | None = None,
) -> int:
```

Increment counters at BFS start, edge inspection, queue insertion, path augmentation and reverse-edge traversal. Emit path node/edge IDs, bottleneck and current total flow.

- [ ] **Step 4: Verify solver and regression tests**

Run:

```powershell
python -m pytest tests/test_tracing.py tests/test_maxflow.py tests/test_baseball.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add baseball_elimination/edmonds_karp.py tests/test_tracing.py
git commit -m "feat: trace edmonds karp execution"
```

### Task 4: Instrument Dinic

**Files:**
- Modify: `baseball_elimination/dinic.py`
- Modify: `tests/test_tracing.py`

- [ ] **Step 1: Write failing Dinic event test**

```python
def test_dinic_emits_level_and_blocking_flow_events():
    recorder = TraceRecorder("dinic")
    metrics = AlgorithmMetrics()
    value = dinic(build_network(), 0, 3, recorder=recorder, metrics=metrics)
    event_types = {event.type for event in recorder.events}
    assert value == 5
    assert {"level-built", "dfs-enter", "blocking-flow", "completed"} <= event_types
    assert metrics.level_phases >= 1
    assert metrics.dfs_calls >= 1
    assert metrics.blocking_flow_pushes >= 1
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_tracing.py -k dinic -q`

Expected: unexpected keyword argument `recorder`.

- [ ] **Step 3: Instrument level graph, DFS and current arc**

Use the same optional keyword arguments as Edmonds–Karp. Emit level arrays, active DFS path, current-edge index changes, pushed flow and phase completion.

- [ ] **Step 4: Verify all max-flow tests**

Run:

```powershell
python -m pytest tests/test_tracing.py tests/test_maxflow.py tests/test_baseball.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add baseball_elimination/dinic.py tests/test_tracing.py
git commit -m "feat: trace dinic level and blocking flows"
```

### Task 5: Reusable baseball network description

**Files:**
- Modify: `baseball_elimination/baseball.py`
- Modify: `baseball_elimination/__init__.py`
- Create: `tests/test_visualizer_export.py`

- [ ] **Step 1: Write failing network-description test**

```python
def test_build_network_describes_game_and_team_vertices():
    division = BaseballDivision.from_file("data/teams4.txt")
    built = division.build_elimination_network("Philadelphia")
    assert built.source == 0
    assert built.target_team == "Philadelphia"
    assert {node.kind for node in built.nodes} == {"source", "game", "team", "sink"}
    assert built.required_flow == 7
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_visualizer_export.py -q`

Expected: missing `build_elimination_network`.

- [ ] **Step 3: Extract construction from `analyze`**

Create dataclasses `NetworkNode`, `NetworkEdge` and `BuiltEliminationNetwork` with stable IDs and labels. `analyze` calls this method for nontrivial cases, preserving all existing output.

- [ ] **Step 4: Add traced analysis method**

Implement:

```python
def trace_analysis(self, team: str, algorithm: str) -> dict[str, object]:
```

Return standings, network description, events, metrics and final elimination result. Direct elimination returns a short trace without max-flow search.

- [ ] **Step 5: Verify**

Run:

```powershell
python -m pytest tests/test_visualizer_export.py tests/test_baseball.py tests/test_cli.py -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add baseball_elimination tests/test_visualizer_export.py
git commit -m "feat: expose baseball flow network and traces"
```

### Task 6: Static trace exporter

**Files:**
- Create: `scripts/export_visualizer_data.py`
- Modify: `tests/test_visualizer_export.py`
- Create: `docs/data/.gitkeep`

- [ ] **Step 1: Write failing export contract test**

```python
def test_export_visualizer_data_writes_manifest_and_trace_files(tmp_path):
    export_site_data(
        datasets=[Path("data/teams4.txt")],
        output_dir=tmp_path,
        algorithms=("edmonds-karp", "dinic"),
    )
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["datasets"][0]["id"] == "teams4"
    trace = json.loads((tmp_path / "teams4__Philadelphia__dinic.json").read_text())
    assert trace["schema"] == "baseball-maxflow-trace.v1"
    assert trace["events"][-1]["type"] == "completed"
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_visualizer_export.py -k export -q`

Expected: missing exporter.

- [ ] **Step 3: Implement deterministic JSON export**

Bundle `teams4`, `teams5`, `teams7`, `teams8`, `teams10` and `teams12`. Use compact JSON and stable ordering. Manifest records dataset, teams and available target/algorithm trace file names.

- [ ] **Step 4: Generate site data**

Run:

```powershell
python scripts/export_visualizer_data.py
```

Expected: manifest and trace JSON files under `docs/data`.

- [ ] **Step 5: Verify**

Run: `python -m pytest tests/test_visualizer_export.py -q`

Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add scripts/export_visualizer_data.py docs/data tests/test_visualizer_export.py
git commit -m "feat: export bundled maxflow visualization traces"
```

### Task 7: Static visualizer shell and warm-paper style

**Files:**
- Create: `docs/index.html`
- Create: `docs/styles.css`
- Create: `docs/app.js`
- Create: `tests/test_pages_site.py`

- [ ] **Step 1: Write failing static-site contract tests**

```python
def test_pages_site_contains_required_controls():
    html = Path("docs/index.html").read_text(encoding="utf-8")
    for element_id in [
        "dataset-select", "team-select", "algorithm-select", "play-button",
        "previous-button", "next-button", "network-stage", "timeline",
        "tab-current", "tab-pseudocode", "tab-state",
    ]:
        assert f'id="{element_id}"' in html


def test_site_uses_manifest_and_svg_renderer():
    javascript = Path("docs/app.js").read_text(encoding="utf-8")
    assert "./data/manifest.json" in javascript
    assert "renderNetwork" in javascript
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_pages_site.py -q`

Expected: files missing.

- [ ] **Step 3: Build semantic HTML shell**

Include hero KPIs, controls, SVG stage, legend, tab buttons, three tab panels, result card, timeline and performance-chart section.

- [ ] **Step 4: Implement visual system**

Use reference-inspired tokens:

```css
--paper: #f6f1e8;
--paper-strong: #fffaf1;
--ink: #1d2433;
--muted: #5e6678;
--accent: #0b4f6c;
--warm: #f28f3b;
```

Use responsive one-column layout below 960 px.

- [ ] **Step 5: Implement application state**

Load manifest and selected trace, render controls, play/pause, step navigation, speed, progress, timeline and tabs. Keep all data local to the static site.

- [ ] **Step 6: Implement adaptive SVG**

Render four columns. Fully expand small networks. For large networks, display active/highlighted nodes plus aggregate game-node cards. Provide SVG wheel zoom, pointer drag and reset view.

- [ ] **Step 7: Verify**

Run: `python -m pytest tests/test_pages_site.py -q`

Expected: all pass.

- [ ] **Step 8: Commit**

```powershell
git add docs/index.html docs/styles.css docs/app.js tests/test_pages_site.py
git commit -m "feat: add interactive maxflow teaching visualizer"
```

### Task 8: Extended benchmark metrics

**Files:**
- Modify: `scripts/benchmark.py`
- Modify: `tests/test_benchmark.py`

- [ ] **Step 1: Write failing benchmark schema tests**

Assert generated rows include:

```text
experiment,dataset,teams,density,seed,algorithm,repeat,elapsed_ms,
peak_kib,vertices,logical_edges,edge_inspections,bfs_rounds,dfs_calls,
augmentations,level_phases,blocking_flow_pushes,current_arc_skips
```

Test deterministic sparse/dense generation and a nonzero peak-memory result.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_benchmark.py -q`

Expected: missing columns/functions.

- [ ] **Step 3: Add density-aware generator and instrumented runner**

Use `tracemalloc.start()`, run all teams, read peak bytes, then stop tracing. Record one metrics aggregate per timed run.

- [ ] **Step 4: Add experiment sets**

- Scaling: sizes `8,12,16,20,24,28`, dense schedules.
- Density: 20 teams, probabilities `0.15..0.90`, three fixed seeds.
- Official: all Princeton datasets, with representative full repeated timing and one instrumentation pass.

- [ ] **Step 5: Verify**

Run: `python -m pytest tests/test_benchmark.py -q`

Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add scripts/benchmark.py tests/test_benchmark.py
git commit -m "feat: measure maxflow operations density and memory"
```

### Task 9: Expanded chart suite

**Files:**
- Modify: `scripts/benchmark.py`
- Modify: `tests/test_benchmark.py`
- Generate: `output/*.png`
- Generate: `docs/output/*.png`

- [ ] **Step 1: Read visualization template guidance**

Read the current Seaborn static-chart template reference before implementation.

- [ ] **Step 2: Write failing chart-output test**

Call `render_all_charts` on a compact synthetic fixture and assert seven named PNG files exist and are larger than 1 KB.

- [ ] **Step 3: Implement chart contracts**

- Runtime scaling: two-series line, log y.
- Speedup scaling: single-series bars with labels.
- Density runtime: two-series line.
- Operation counts: two-panel lines, algorithm-specific operations.
- Memory scaling: two-series line.
- Official scatter: edge count vs runtime, log-log, dataset labels for major outliers.
- Legacy grouped comparison.

- [ ] **Step 4: Run full benchmark**

Run:

```powershell
python scripts/benchmark.py --repeats 5
```

Expected: CSV, summary and all charts generated.

- [ ] **Step 5: Copy chart artifacts to site**

The benchmark script writes identical report images to `output/` and `docs/output/`.

- [ ] **Step 6: Visually inspect every chart**

Check labels, scales, legends, subtitles, color consistency and clipping.

- [ ] **Step 7: Commit**

```powershell
git add scripts/benchmark.py tests/test_benchmark.py output docs/output
git commit -m "feat: add extended maxflow benchmark charts"
```

### Task 10: Documentation and report

**Files:**
- Modify: `README.md`
- Modify: `实验报告.md`

- [ ] **Step 1: Document visualizer build and local preview**

Add:

```powershell
python scripts/export_visualizer_data.py
python -m http.server 8000 --directory docs
```

- [ ] **Step 2: Update experiment methodology**

Define every timing, operation and memory metric; add scale/density/official experiment tables using measured output.

- [ ] **Step 3: Embed all relevant figures**

Use `output/runtime_scaling.png`, `speedup_scaling.png`, `density_runtime.png`, `operation_counts.png`, `memory_scaling.png` and `official_runtime_scatter.png`.

- [ ] **Step 4: Commit**

```powershell
git add README.md 实验报告.md
git commit -m "docs: document visualizer and extended experiments"
```

### Task 11: GitHub Pages workflow

**Files:**
- Create: `.github/workflows/pages.yml`
- Create: `docs/.nojekyll`

- [ ] **Step 1: Add Pages workflow**

Workflow triggers on pushes to `main`, uploads `docs/` via `actions/upload-pages-artifact`, then deploys with `actions/deploy-pages`. Permissions:

```yaml
pages: write
id-token: write
contents: read
```

- [ ] **Step 2: Validate YAML paths**

Confirm workflow artifact path is `docs`.

- [ ] **Step 3: Commit**

```powershell
git add .github/workflows/pages.yml docs/.nojekyll
git commit -m "ci: deploy visualizer to github pages"
```

### Task 12: Final verification and deployment

**Files:**
- Review all files.

- [ ] **Step 1: Run tests and compile**

```powershell
python -m pytest -q
python -m compileall -q baseball_elimination scripts main.py
```

Expected: zero failures and exit code 0.

- [ ] **Step 2: Rebuild generated artifacts**

```powershell
python scripts/export_visualizer_data.py
python scripts/benchmark.py --repeats 5
```

- [ ] **Step 3: Browser QA**

Start `python -m http.server 8000 --directory docs`, then verify:

- default trace loads;
- dataset/team/algorithm selection;
- play/pause and step controls;
- timeline click;
- tabs;
- zoom/reset;
- final certificate;
- performance images;
- responsive width.

- [ ] **Step 4: Create GitHub repository if no remote exists**

Run:

```powershell
gh repo create gc9335/baseball-elimination-maxflow-visualizer --public --source . --remote origin --push
```

If `origin` exists, push `main` instead.

- [ ] **Step 5: Enable Pages workflow and push**

Use the GitHub Pages API if required to set `build_type=workflow`, then push `main`.

- [ ] **Step 6: Wait for Pages deployment**

Inspect the workflow until successful. Open the published URL and repeat a focused online smoke test.

- [ ] **Step 7: Report final URL and verification evidence**

Include test count, generated trace count, generated chart count, repository URL and Pages URL.
