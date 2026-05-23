"""Tests for ``BuildGraphPhase`` — the DEC-013 / PRD §10 item 8 activation.

End-to-end: take a real fixture, run the static pipeline, persist the
result into a LadybugDB, and verify the round-trip via Cypher.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.pipeline import (
    BuildGraphPhase,
    ExtractConfig,
    InventoryPhase,
    PipelineRunner,
    StaticPhase,
    default_phases,
    run_extract,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# default_phases() shape
# ---------------------------------------------------------------------------


def test_default_phases_includes_build_graph():
    names = [p.name for p in default_phases()]
    assert names == ["inventory", "static", "flatten", "history", "build_graph", "emit"]


def test_build_graph_runs_before_emit():
    runner = PipelineRunner(default_phases())
    order = [p.name for p in runner.order]
    assert order.index("build_graph") < order.index("emit")


# ---------------------------------------------------------------------------
# Opt-in behavior (DEC-013: off by default)
# ---------------------------------------------------------------------------


def test_phase_is_no_op_when_disabled(tmp_path):
    cfg = ExtractConfig(repo_path=tmp_path, output_dir=tmp_path / "out", build_graph_db=False)
    out = BuildGraphPhase().run(_seeded_ctx(cfg, tmp_path))
    assert out.enabled is False
    assert out.db_path is None
    assert out.file_count == 0
    # No DB file should be created.
    assert not (tmp_path / ".deepdive").exists()


# ---------------------------------------------------------------------------
# Real fixture populates the graph
# ---------------------------------------------------------------------------


def test_persists_files_symbols_and_defines_for_python_fixture(tmp_path):
    repo = _copy_fixture("python_sample", tmp_path)
    db_path = tmp_path / "graph.lbug"
    cfg = ExtractConfig(
        repo_path=repo,
        output_dir=tmp_path / "out",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    runner = PipelineRunner(default_phases())
    ctx = runner.run(cfg)
    out = ctx.get(BuildGraphPhase)

    assert out.enabled is True
    assert out.db_path == db_path
    assert out.file_count == 2  # greeter.py + app.py
    assert out.symbol_count > 0
    assert out.defines_count == out.symbol_count

    # Round-trip via the store: read the graph back and assert structure.
    with LadybugStore(db_path) as store:
        assert store.count_nodes("File") == 2
        assert store.count_nodes("Symbol") == out.symbol_count
        assert store.count_edges("DEFINES") == out.defines_count
        # Greeter class is a known definition in greeter.py.
        greeter_symbols = {s.qualified_name for s in store.iter_symbols_for_file("greeter.py")}
        assert "greeter.py::Greeter" in greeter_symbols
        # Files round-trip with their language and role.
        greeter_file = store.get_file("greeter.py")
        assert greeter_file is not None
        assert greeter_file.language == "python"
        assert greeter_file.sha != "0" * 64  # SHA was computed, not the default
        assert greeter_file.loc > 0


def test_polyglot_persists_every_language(tmp_path):
    """All 8 DEC-020 languages get their files + symbols persisted in the
    same .lbug database."""
    repo = tmp_path / "polyglot"
    repo.mkdir()
    for sample in (
        "python_sample",
        "dart_sample",
        "c_sample",
        "swift_sample",
        "typescript_sample",
        "javascript_sample",
        "java_sample",
        "go_sample",
    ):
        shutil.copytree(FIXTURES / sample, repo / sample)

    db_path = tmp_path / "graph.lbug"
    cfg = ExtractConfig(
        repo_path=repo,
        output_dir=tmp_path / "out",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    PipelineRunner(default_phases()).run(cfg)

    with LadybugStore(db_path) as store:
        langs = {row[0] for row in store.query("MATCH (f:File) RETURN DISTINCT f.language")}
        assert langs == {
            "python",
            "dart",
            "c",
            "swift",
            "typescript",
            "javascript",
            "java",
            "go",
        }
        # Every File has at least one DEFINES edge to a Symbol.
        rows = list(
            store.query(
                "MATCH (f:File)-[:DEFINES]->(s:Symbol) "
                "RETURN f.language, count(s) AS n ORDER BY f.language"
            )
        )
        by_lang = dict(rows)
        # Every supported language produces at least one symbol.
        for lang in langs:
            assert by_lang.get(lang, 0) > 0, f"{lang} produced no symbols"


# ---------------------------------------------------------------------------
# run_extract integration: build_graph_db flag flows through
# ---------------------------------------------------------------------------


def test_public_run_extract_does_not_build_graph_by_default(tmp_path):
    """v0.2 invariant: the public ``run_extract`` keeps v0.1 behavior —
    the LadybugDB graph is opt-in via the lower-level runner only, until
    the markdown emitters cut over (PRD §10 item 9). This test will be
    inverted when item 9 lands."""
    repo = _copy_fixture("python_sample", tmp_path)
    result = run_extract(repo, flatten=False, write_editor_shims=False)
    assert result.artifacts  # markdown still emitted
    assert not (repo / ".deepdive").exists()  # no LadybugDB built


def test_runner_opt_in_builds_graph_at_configured_path(tmp_path):
    """DEC-013: ``build_graph_db=True`` + ``graph_db_path`` populates the
    LadybugDB at the requested location."""
    repo = _copy_fixture("python_sample", tmp_path)
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
    out = ctx.get(BuildGraphPhase)
    assert out.enabled is True
    assert db_path.exists()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _copy_fixture(name: str, tmp_path: Path) -> Path:
    repo = tmp_path / name
    shutil.copytree(FIXTURES / name, repo)
    return repo


def _seeded_ctx(cfg: ExtractConfig, tmp_path: Path):
    """Build a minimal Context with inventory + static outputs pre-seeded
    via the actual phases — keeps the BuildGraphPhase under test without
    depending on the full pipeline."""
    from forensic_deepdive.pipeline import Context

    ctx = Context(config=cfg)
    inv = InventoryPhase().run(ctx)
    ctx.put(InventoryPhase.name, inv)
    static = StaticPhase().run(ctx)
    ctx.put(StaticPhase.name, static)
    return ctx
