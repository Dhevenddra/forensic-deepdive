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


def test_hotpaths_has_call_graph_section_in_graph_mode(tmp_path):
    """DEC-029: HOTPATHS gets a 'Call-graph hot spots' section when
    the LadybugDB graph has at least one CALLS edge."""
    repo = _copy("python_sample", tmp_path)
    artifacts = _run_with_graph(repo, tmp_path / "graph.lbug")
    hot = artifacts["HOTPATHS.md"].read_text(encoding="utf-8")
    assert "## Call-graph hot spots" in hot
    # python_sample has Greeter.greet calling format_message and
    # app.py::run calling format_message + Greeter — so
    # format_message should appear with >= 1 caller.
    assert "format_message" in hot


def test_hotpaths_call_graph_section_absent_without_graph(tmp_path):
    """DEC-029 invariant: when build_graph_db is off, the graph-mode
    sections do NOT render — protects the golden-emit fixtures from
    drifting."""
    from forensic_deepdive.pipeline import run_extract

    repo = _copy("python_sample", tmp_path)
    run_extract(repo, flatten=False, write_editor_shims=False)
    hot = (repo / "docs" / "codebase" / "HOTPATHS.md").read_text(encoding="utf-8")
    assert "## Call-graph hot spots" not in hot
    assert "## Co-change clusters" not in hot


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
