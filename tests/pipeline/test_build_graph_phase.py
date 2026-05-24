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
# DEC-023 — MEMBER_OF + qualified-name correctness
# ---------------------------------------------------------------------------


def test_member_of_qualified_name_includes_parent(tmp_path):
    """DEC-023: a method's qualified_name is ``<file>::<Class>.<method>``,
    not the bare ``<file>::<method>``. Two methods named ``greet`` in two
    classes in one file would have collided under the v0.2 phase-1 schema;
    they don't under DEC-023."""
    repo = _copy_fixture("python_sample", tmp_path)
    db_path = tmp_path / "graph.lbug"
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        # Top-level definitions keep their bare qn.
        assert store.get_symbol("greeter.py::Greeter") is not None
        assert store.get_symbol("greeter.py::format_message") is not None
        # Methods are dotted under their class.
        assert store.get_symbol("greeter.py::Greeter.greet") is not None
        assert store.get_symbol("greeter.py::Greeter.__init__") is not None
        # The bare-name forms must NOT exist (they did under phase-1).
        assert store.get_symbol("greeter.py::greet") is None
        assert store.get_symbol("greeter.py::__init__") is None


def test_member_of_edge_links_method_to_class(tmp_path):
    """DEC-023: every method emits a MEMBER_OF edge to its enclosing class
    Symbol, with EXTRACTED confidence (AST-deterministic)."""
    repo = _copy_fixture("python_sample", tmp_path)
    db_path = tmp_path / "graph.lbug"
    out = _build(repo, db_path)
    assert out.member_of_count >= 2  # __init__ + greet at minimum
    with LadybugStore(db_path) as store:
        # greet -> Greeter
        parent = store.parent_of("greeter.py::Greeter.greet")
        assert parent is not None
        assert parent.qualified_name == "greeter.py::Greeter"
        # Greeter class has BOTH methods listed via the reverse traversal.
        members = {s.qualified_name for s in store.iter_members_of("greeter.py::Greeter")}
        assert "greeter.py::Greeter.greet" in members
        assert "greeter.py::Greeter.__init__" in members
        # The class itself is top-level — no outgoing MEMBER_OF.
        assert store.parent_of("greeter.py::Greeter") is None
        # format_message is also top-level.
        assert store.parent_of("greeter.py::format_message") is None


def test_member_of_uses_extracted_confidence(tmp_path):
    """DEC-023: containment is deterministic — every MEMBER_OF edge MUST
    be EXTRACTED. AMBIGUOUS / INFERRED appearing here is a bug."""
    repo = _copy_fixture("python_sample", tmp_path)
    db_path = tmp_path / "graph.lbug"
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        rows = list(store.query("MATCH ()-[r:MEMBER_OF]->() RETURN DISTINCT r.confidence"))
    assert rows == [["EXTRACTED"]]


def test_member_of_go_method_uses_receiver_type_as_parent(tmp_path):
    """DEC-023 (Go branch): methods bind via the receiver, not lexical
    nesting. ``func (g *Greeter) Greet()`` must MEMBER_OF -> Greeter even
    though the method is not lexically inside the type declaration."""
    repo = _copy_fixture("go_sample", tmp_path)
    db_path = tmp_path / "graph.lbug"
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        # Greet and Name are receiver-methods on Greeter.
        for method in ("greeter.go::Greeter.Greet", "greeter.go::Greeter.Name"):
            parent = store.parent_of(method)
            assert parent is not None, method
            assert parent.qualified_name == "greeter.go::Greeter"
        # formatMessage is a bare function — no parent.
        assert store.parent_of("greeter.go::formatMessage") is None


def test_member_of_polyglot_every_language_with_methods(tmp_path):
    """DEC-023: every fixture that has class methods or receiver methods
    produces at least one MEMBER_OF edge in the same shared .lbug."""
    repo = tmp_path / "polyglot"
    repo.mkdir()
    for sample in (
        "python_sample",
        "dart_sample",
        "swift_sample",
        "typescript_sample",
        "javascript_sample",
        "java_sample",
        "go_sample",
        "c_sample",  # no methods — verify it doesn't break
    ):
        shutil.copytree(FIXTURES / sample, repo / sample)
    db_path = tmp_path / "graph.lbug"
    out = _build(repo, db_path)
    # 7 of 8 fixtures define class methods; each should contribute >= 1
    # MEMBER_OF. Concrete lower bound: at least 7.
    assert out.member_of_count >= 7
    with LadybugStore(db_path) as store:
        rows = list(
            store.query(
                "MATCH (m:Symbol)-[:MEMBER_OF]->(p:Symbol) "
                "RETURN DISTINCT p.file_path ORDER BY p.file_path"
            )
        )
        parent_files = {row[0] for row in rows}
        # Every language with methods must show up as a parent's file.
        for expected in (
            "python_sample/greeter.py",
            "dart_sample/greeter.dart",
            "swift_sample/Greeter.swift",
            "typescript_sample/greeter.ts",
            "javascript_sample/greeter.js",
            "java_sample/Greeter.java",
            "go_sample/greeter.go",
        ):
            assert expected in parent_files, expected
        # C had no methods — must not show.
        for f in parent_files:
            assert not f.endswith(".c"), f


def test_member_of_nested_classes_chain(tmp_path):
    """DEC-023: nested classes produce a chain of MEMBER_OF edges.
    ``Outer.Inner.deep`` -> ``Outer.Inner`` -> ``Outer``."""
    repo = tmp_path / "nested"
    repo.mkdir()
    (repo / "n.py").write_text(
        "class Outer:\n"
        "    class Inner:\n"
        "        def deep(self):\n"
        "            pass\n"
        "    def outer_method(self):\n"
        "        pass\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "graph.lbug"
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        assert store.get_symbol("n.py::Outer") is not None
        assert store.get_symbol("n.py::Outer.Inner") is not None
        assert store.get_symbol("n.py::Outer.Inner.deep") is not None
        assert store.get_symbol("n.py::Outer.outer_method") is not None
        # deep -> Inner -> Outer
        assert store.parent_of("n.py::Outer.Inner.deep").qualified_name == ("n.py::Outer.Inner")
        assert store.parent_of("n.py::Outer.Inner").qualified_name == "n.py::Outer"
        # Outer is top-level.
        assert store.parent_of("n.py::Outer") is None
        # outer_method skips Inner.
        assert store.parent_of("n.py::Outer.outer_method").qualified_name == ("n.py::Outer")


def test_member_of_java_same_method_name_in_two_classes_does_not_collide(tmp_path):
    """DEC-023 fixes a v0.2-phase-1 limitation: Java's Greeter and Named
    both declare a method ``name()``. They must be two distinct Symbols
    in the graph (different MEMBER_OF parents), not a single Symbol the
    phase-1 schema would have collided on bare-name PK."""
    repo = _copy_fixture("java_sample", tmp_path)
    db_path = tmp_path / "graph.lbug"
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        # Two distinct Symbols, distinguished by their parent class.
        named = store.get_symbol("Greeter.java::Named.name")
        greeter = store.get_symbol("Greeter.java::Greeter.name")
        assert named is not None
        assert greeter is not None
        assert named != greeter
        # Each MEMBER_OF its declared interface/class.
        assert store.parent_of(named.qualified_name).qualified_name == ("Greeter.java::Named")
        assert store.parent_of(greeter.qualified_name).qualified_name == ("Greeter.java::Greeter")


# ---------------------------------------------------------------------------
# helpers (added with the DEC-023 tests)
# ---------------------------------------------------------------------------


def _build(repo: Path, db_path: Path):
    cfg = ExtractConfig(
        repo_path=repo.resolve(),
        output_dir=repo / "docs" / "codebase",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    ctx = PipelineRunner(default_phases()).run(cfg)
    return ctx.get(BuildGraphPhase)


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
