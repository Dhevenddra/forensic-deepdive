"""Graph-mode emit tests (DEC-029, REMAINING.md item 9 phase 1).

When ``ExtractConfig.build_graph_db=True``, ``EmitPhase`` passes the
populated LadybugDB path through to ``RepoFacts.graph_db_path`` and the
HOTPATHS / AGENT_BRIEF emitters render additional graph-driven
sections (call-graph hot spots, co-change clusters, top-callee /
co-change rules).

These tests verify:
- The new sections APPEAR when the graph is built.
- The new sections do NOT appear when graph mode is off (existing
  golden-emit invariants stay green; the golden artifacts themselves
  pin the no-graph baseline).
- The graph-derived content is correct against known fixture data.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.pipeline import (
    BuildGraphPhase,
    EmitPhase,
    ExtractConfig,
    PipelineRunner,
    default_phases,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _run_with_graph(repo: Path, db_path: Path) -> dict[str, Path]:
    cfg = ExtractConfig(
        repo_path=repo.resolve(),
        output_dir=repo / "docs" / "codebase",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    ctx = PipelineRunner(default_phases()).run(cfg)
    return ctx.get(EmitPhase).artifacts


def _copy(name: str, tmp_path: Path) -> Path:
    repo = tmp_path / name
    shutil.copytree(FIXTURES / name, repo)
    return repo


# ---------------------------------------------------------------------------
# HOTPATHS — new sections
# ---------------------------------------------------------------------------


def test_hotpaths_dependency_hotspots_use_graph_in_graph_mode(tmp_path):
    """DEC-030: in graph mode, the "Dependency hot spots" section
    reads from CALLS edges (DEC-025 resolver) and includes the
    confidence-mix column the v0.1 NetworkX path can't produce."""
    repo = _copy("python_sample", tmp_path)
    artifacts = _run_with_graph(repo, tmp_path / "graph.lbug")
    hot = artifacts["HOTPATHS.md"].read_text(encoding="utf-8")
    # Graph-mode "Dependency hot spots" mentions CALLS resolver
    # explicitly and adds a Callers / Confidence-mix column.
    assert "## Dependency hot spots" in hot
    assert "CALLS" in hot or "Callers" in hot
    # python_sample's format_message is called from app.py::run and
    # greeter.py::Greeter.greet -> 2 callers, both EXTRACTED.
    assert "format_message" in hot
    assert "EXTRACTED" in hot


def test_dec085_dependency_hotspots_count_distinct_callers(tmp_path):
    """DEC-085 (metric honesty): the "Callers" number is **distinct caller
    symbols**, not raw CALLS-edge count. A callee called twice from the SAME
    caller is 1 caller (verifiable by listing callers), even though there are 2
    edges — the inflation behind "383 inbound vs 271 grep". The per-edge
    confidence mix stays edge-based on purpose."""
    repo = tmp_path / "dup"
    repo.mkdir()
    (repo / "m.py").write_text(
        "def target():\n    return 1\n\n\ndef caller():\n    target()\n    target()\n"
    )
    artifacts = _run_with_graph(repo, tmp_path / "graph.lbug")
    hot = artifacts["HOTPATHS.md"].read_text(encoding="utf-8")
    # The reconciled definition is stated at the point of use.
    assert "distinct callers" in hot
    row = next(line for line in hot.splitlines() if "`target`" in line and "|" in line)
    cells = [c.strip() for c in row.split("|")]
    # | Symbol | Defined in | Callers | Confidence mix |
    assert cells[3] == "1", f"expected 1 distinct caller, got: {row}"
    # ...while the confidence mix remains edge-based (2 EXTRACTED edges).
    assert "2 `EXTRACTED`" in row


def test_hotpaths_cross_stack_routes_section_in_graph_mode(tmp_path):
    """DEC-052: in graph mode on a cross-stack repo, HOTPATHS grows a
    ``## Cross-stack routes`` section listing ROUTES_TO joins with confidence."""
    repo = _copy("openapi_codegen_sample", tmp_path)
    artifacts = _run_with_graph(repo, tmp_path / "graph.lbug")
    hot = artifacts["HOTPATHS.md"].read_text(encoding="utf-8")
    assert "## Cross-stack routes" in hot
    assert "client.js::loadItem" in hot
    assert "backend.py::get_item" in hot
    assert "http::GET::/api/items/{param}" in hot
    assert "EXTRACTED" in hot


def test_hotpaths_cross_stack_routes_absent_without_routes(tmp_path):
    """DEC-052 byte-identical guard: a repo with no ROUTES_TO edges (python_sample)
    renders no ``## Cross-stack routes`` section even in graph mode — the same
    graph-only-disappears contract as ``## Co-change clusters``."""
    repo = _copy("python_sample", tmp_path)
    artifacts = _run_with_graph(repo, tmp_path / "graph.lbug")
    hot = artifacts["HOTPATHS.md"].read_text(encoding="utf-8")
    assert "## Cross-stack routes" not in hot


def test_hotpaths_graph_only_sections_absent_without_graph(tmp_path):
    """DEC-029/030 invariant: when build_graph_db is off, "Co-change
    clusters" does not render and "Dependency hot spots" falls back to
    the v0.1 NetworkX rendering (different column shape)."""
    from forensic_deepdive.pipeline import (
        BuildGraphPhase,
        Context,
        ExtractConfig,
        InventoryPhase,
        PipelineRunner,
        StaticPhase,
        default_phases,
    )

    repo = _copy("python_sample", tmp_path)
    # Force graph-off (the default flips to True in this phase, so
    # we explicitly opt out to test the fallback path).
    cfg = ExtractConfig(
        repo_path=repo.resolve(),
        output_dir=repo / "docs" / "codebase",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=False,
    )
    PipelineRunner(default_phases()).run(cfg)
    hot = (repo / "docs" / "codebase" / "HOTPATHS.md").read_text(encoding="utf-8")
    # Co-change is a graph-only section — must not appear.
    assert "## Co-change clusters" not in hot
    # v0.1 path uses "Rank" column header instead of "Callers".
    assert "Rank" in hot
    # Silence unused-import — these are needed elsewhere in the module.
    _ = (BuildGraphPhase, Context, InventoryPhase, StaticPhase)


# ---------------------------------------------------------------------------
# AGENT_BRIEF — new rules
# ---------------------------------------------------------------------------


def test_agent_brief_includes_top_called_symbol_rule(tmp_path):
    """DEC-029: AGENT_BRIEF gets an extra "Always" rule citing the
    most-called symbol from the CALLS graph."""
    repo = _copy("python_sample", tmp_path)
    artifacts = _run_with_graph(repo, tmp_path / "graph.lbug")
    brief = artifacts["AGENT_BRIEF.md"].read_text(encoding="utf-8")
    assert "most-called symbol" in brief
    # format_message is called from two sites in the fixture (the
    # method body + the bare call in app.py).
    assert "format_message" in brief


def test_agent_brief_stays_under_5kb_with_graph_sections(tmp_path):
    """DEC-029 + existing AGENT_BRIEF cap: the extra graph-mode rules
    must not push the brief over the 5 KB hard cap. Overflow goes
    into AGENT_BRIEF_DEEP.md."""
    repo = _copy("python_sample", tmp_path)
    artifacts = _run_with_graph(repo, tmp_path / "graph.lbug")
    brief_bytes = artifacts["AGENT_BRIEF.md"].stat().st_size
    assert brief_bytes <= 5120


# ---------------------------------------------------------------------------
# RepoFacts plumbing
# ---------------------------------------------------------------------------


def test_emit_phase_populates_graph_db_path_when_graph_built(tmp_path):
    """EmitPhase reads BuildGraphPhase's db_path and threads it onto
    RepoFacts.graph_db_path — that's the plumbing graph-mode emitters
    use to opt in."""
    repo = _copy("python_sample", tmp_path)
    db_path = tmp_path / "graph.lbug"
    cfg = ExtractConfig(
        repo_path=repo.resolve(),
        output_dir=repo / "docs" / "codebase",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    ctx = PipelineRunner(default_phases()).run(cfg)
    facts = ctx.get(EmitPhase).facts
    assert facts.graph_db_path == db_path


def test_emit_phase_leaves_graph_db_path_none_when_disabled(tmp_path):
    """v0.1 invariant: with build_graph_db off, RepoFacts.graph_db_path
    is None — emitters see no graph and fall back to NetworkX."""
    repo = _copy("python_sample", tmp_path)
    cfg = ExtractConfig(
        repo_path=repo.resolve(),
        output_dir=repo / "docs" / "codebase",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=False,
    )
    ctx = PipelineRunner(default_phases()).run(cfg)
    facts = ctx.get(EmitPhase).facts
    assert facts.graph_db_path is None
    # And BuildGraphPhase was a no-op.
    assert not ctx.get(BuildGraphPhase).enabled
