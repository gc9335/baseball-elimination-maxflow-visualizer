import json
from pathlib import Path


def test_pages_site_contains_required_controls():
    html = Path("docs/index.html").read_text(encoding="utf-8")

    for element_id in [
        "dataset-select",
        "team-select",
        "algorithm-select",
        "play-button",
        "previous-button",
        "next-button",
        "network-stage",
        "timeline",
        "tab-current",
        "tab-pseudocode",
        "tab-state",
    ]:
        assert f'id="{element_id}"' in html


def test_site_uses_manifest_and_svg_renderer():
    javascript = Path("docs/app.js").read_text(encoding="utf-8")

    assert "./data/manifest.json" in javascript
    assert "renderNetwork" in javascript
    assert "renderTimeline" in javascript
    assert "togglePlayback" in javascript


def test_manifest_references_existing_trace_files():
    manifest = json.loads(Path("docs/data/manifest.json").read_text(encoding="utf-8"))

    for dataset in manifest["datasets"]:
        for trace_file in dataset["traces"]:
            assert (Path("docs/data") / trace_file).is_file()


def test_site_has_responsive_and_accessible_styles():
    css = Path("docs/styles.css").read_text(encoding="utf-8")
    html = Path("docs/index.html").read_text(encoding="utf-8")

    assert "@media (max-width: 960px)" in css
    assert "grid-template-columns: minmax(0, 1fr)" in css
    assert "min-width: 0" in css
    assert "--paper: #f6f1e8" in css
    assert 'aria-label="最大流残量网络"' in html


def test_site_focuses_on_the_flow_process_instead_of_benchmark_images():
    html = Path("docs/index.html").read_text(encoding="utf-8")

    assert 'id="flow-phase-indicator"' in html
    assert "performance-section" not in html
    assert "chart-grid" not in html
    assert "./output/" not in html


def test_network_styles_make_capacity_and_flow_phases_prominent():
    css = Path("docs/styles.css").read_text(encoding="utf-8")
    javascript = Path("docs/app.js").read_text(encoding="utf-8")

    assert ".network-edge.phase-search" in css
    assert ".network-edge.phase-path" in css
    assert ".network-edge.phase-push" in css
    assert ".edge-label.phase-push" in css
    assert "font-size: 16px" in css
    assert "function eventPhase" in javascript
    assert "flowPhase" in javascript
