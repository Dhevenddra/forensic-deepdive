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


def test_public_run_extract_builds_graph_by_default(tmp_path):
    """DEC-030 (item 9 phase 2): the public ``run_extract`` now builds
    the LadybugDB graph AND emits the markdown artifacts by default.
    Inverted from the v0.2-phase-1 invariant."""
    repo = _copy_fixture("python_sample", tmp_path)
    result = run_extract(repo, flatten=False, write_editor_shims=False)
    assert result.artifacts  # markdown still emitted
    # LadybugDB is built at the default path now.
    assert (repo / ".deepdive" / "graph.lbug").exists()


def test_public_run_extract_can_opt_out_of_graph(tmp_path):
    """DEC-030 escape hatch: callers wanting the v0.1-only path can
    pass ``build_graph_db=False`` via the lower-level runner. Used by
    a few existing test paths that want speed over richness."""
    repo = _copy_fixture("python_sample", tmp_path)
    cfg = ExtractConfig(
        repo_path=repo.resolve(),
        output_dir=repo / "docs" / "codebase",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=False,
    )
    PipelineRunner(default_phases()).run(cfg)
    assert not (repo / ".deepdive" / "graph.lbug").exists()


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


# ---------------------------------------------------------------------------
# DEC-024 — IMPORTS + Module nodes
# ---------------------------------------------------------------------------


def test_imports_python_fixture_writes_module_and_edge(tmp_path):
    """DEC-024: Python `import` / `from import` statements produce Module
    nodes and IMPORTS edges in the LadybugDB."""
    repo = tmp_path / "py-imports"
    repo.mkdir()
    (repo / "a.py").write_text(
        "import os\nimport os.path as P\nfrom typing import List\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "graph.lbug"
    out = _build(repo, db_path)
    assert out.module_count == 3  # os, os.path, typing — distinct PKs
    assert out.imports_count == 3
    with LadybugStore(db_path) as store:
        # IMPORTS targets are language-prefixed (DEC-024 / module_pk).
        rows = list(
            store.query(
                "MATCH (:File {path: 'a.py'})-[:IMPORTS]->(m:Module) RETURN m.path ORDER BY m.path"
            )
        )
        paths = [row[0] for row in rows]
        assert paths == ["python:os", "python:os.path", "python:typing"]


def test_imports_module_pk_disambiguates_cross_language_collision(tmp_path):
    """DEC-024: Python's ``os`` and Go's ``os`` must be two distinct
    Module nodes — the language prefix on the PK guarantees it. Without
    the prefix, real-ladybug's single-column PK would collide and the
    second CREATE would fail (or worse, silently merge two unrelated
    modules)."""
    repo = tmp_path / "cross"
    repo.mkdir()
    (repo / "p.py").write_text("import os\n", encoding="utf-8")
    (repo / "g.go").write_text('package main\nimport "os"\n', encoding="utf-8")
    db_path = tmp_path / "graph.lbug"
    out = _build(repo, db_path)
    assert out.module_count == 2  # python:os AND go:os, not collapsed
    with LadybugStore(db_path) as store:
        rows = list(store.query("MATCH (m:Module) RETURN m.path, m.language ORDER BY m.path"))
        assert rows == [["go:os", "go"], ["python:os", "python"]]


def test_imports_dedupes_within_a_file(tmp_path):
    """Two imports of the same module from one file share one Module node
    and produce two IMPORTS edges (one per statement)."""
    repo = tmp_path / "dedup"
    repo.mkdir()
    (repo / "a.py").write_text(
        # Two distinct statements referencing the same module.
        "import os\nfrom os import path\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "graph.lbug"
    out = _build(repo, db_path)
    assert out.module_count == 1
    assert out.imports_count == 2
    with LadybugStore(db_path) as store:
        rows = list(
            store.query(
                "MATCH (f:File)-[r:IMPORTS]->(m:Module {path: 'python:os'}) RETURN count(r)"
            )
        )
        assert rows == [[2]]


def test_imports_use_extracted_confidence(tmp_path):
    """DEC-024: imports are AST-deterministic — every IMPORTS edge MUST
    be EXTRACTED."""
    repo = tmp_path / "conf"
    repo.mkdir()
    (repo / "a.py").write_text("import os\n", encoding="utf-8")
    db_path = tmp_path / "graph.lbug"
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        rows = list(store.query("MATCH ()-[r:IMPORTS]->() RETURN DISTINCT r.confidence"))
    assert rows == [["EXTRACTED"]]


def test_imports_polyglot_every_language_with_imports(tmp_path):
    """DEC-024: build a repo with one import-bearing file per supported
    language and verify each produces at least one IMPORTS edge in the
    same .lbug. Modules are language-namespaced."""
    repo = tmp_path / "polyglot-imports"
    repo.mkdir()
    sources = {
        "py.py": "import os\n",
        "ts.ts": 'import { Z } from "./y";\n',
        "js.js": 'const z = require("./legacy");\n',
        "g.go": 'package main\nimport "fmt"\n',
        "J.java": "package x;\nimport java.util.List;\npublic class J {}\n",
        "d.dart": "import 'package:foo/bar.dart';\n",
        "S.swift": "import Foundation\n",
        "h.c": '#include "local.h"\n',
    }
    for name, src in sources.items():
        (repo / name).write_text(src, encoding="utf-8")
    db_path = tmp_path / "graph.lbug"
    out = _build(repo, db_path)
    assert out.imports_count >= 8  # at least one per file
    with LadybugStore(db_path) as store:
        rows = list(
            store.query(
                "MATCH (f:File)-[:IMPORTS]->(m:Module) "
                "RETURN DISTINCT m.language ORDER BY m.language"
            )
        )
        langs = [row[0] for row in rows]
    assert set(langs) == {
        "c",
        "dart",
        "go",
        "java",
        "javascript",
        "python",
        "swift",
        "typescript",
    }


def test_imports_module_path_preserves_raw_form(tmp_path):
    """DEC-024: Module.path encodes ``<language>:<raw>``; the raw module
    string is recoverable by stripping the language prefix. Used by the
    future CALLS resolver to walk the import graph."""
    repo = tmp_path / "preserve"
    repo.mkdir()
    (repo / "a.py").write_text("from typing import List\n", encoding="utf-8")
    (repo / "h.c").write_text("#include <stdio.h>\n", encoding="utf-8")
    db_path = tmp_path / "graph.lbug"
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        rows = list(store.query("MATCH (m:Module) RETURN m.path ORDER BY m.path"))
        paths = [row[0] for row in rows]
    # Angle brackets preserved for C system include.
    assert "c:<stdio.h>" in paths
    assert "python:typing" in paths


# ---------------------------------------------------------------------------
# DEC-025 — CALLS resolver + synthetic <module> Symbol
# ---------------------------------------------------------------------------


def test_synthetic_module_symbol_per_file(tmp_path):
    """DEC-025: every File has a synthetic ``<module>`` Symbol so
    module-level refs have a valid caller endpoint."""
    repo = _copy_fixture("python_sample", tmp_path)
    db_path = tmp_path / "graph.lbug"
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        # One MODULE-kind symbol per source file.
        rows = list(
            store.query(
                "MATCH (s:Symbol {kind: 'module'}) "
                "RETURN s.qualified_name ORDER BY s.qualified_name"
            )
        )
        names = [r[0] for r in rows]
    assert "app.py::<module>" in names
    assert "greeter.py::<module>" in names


def test_module_symbol_has_defines_edge_from_its_file(tmp_path):
    """Invariant: every Symbol has a File-DEFINES->Symbol edge, including
    the synthetic ``<module>`` Symbol. Keeps the
    ``symbol_count == defines_count`` invariant intact."""
    repo = _copy_fixture("python_sample", tmp_path)
    db_path = tmp_path / "graph.lbug"
    out = _build(repo, db_path)
    assert out.symbol_count == out.defines_count
    with LadybugStore(db_path) as store:
        rows = list(
            store.query(
                "MATCH (f:File {path: 'greeter.py'})-[:DEFINES]->"
                "(s:Symbol {qualified_name: 'greeter.py::<module>'}) "
                "RETURN s.qualified_name"
            )
        )
    assert rows == [["greeter.py::<module>"]]


def test_calls_python_fixture_writes_edges(tmp_path):
    """DEC-025: Python fixture produces real CALLS edges with the right
    confidence. The fixture's app.py imports Greeter + format_message
    from greeter.py and calls them inside ``run``."""
    repo = _copy_fixture("python_sample", tmp_path)
    db_path = tmp_path / "graph.lbug"
    out = _build(repo, db_path)
    assert out.calls_count >= 3  # run->Greeter, run->format_message, greet->format_message
    with LadybugStore(db_path) as store:
        # Greeter.greet calls format_message (same-file, EXTRACTED).
        rows = list(
            store.query(
                "MATCH (caller:Symbol {qualified_name: 'greeter.py::Greeter.greet'})"
                "-[r:CALLS]->(callee:Symbol) "
                "RETURN callee.qualified_name, r.confidence"
            )
        )
        assert [r[0] for r in rows] == ["greeter.py::format_message"]
        assert rows[0][1] == "EXTRACTED"

        # app.py::run calls greeter.py::format_message via explicit import.
        rows = list(
            store.query(
                "MATCH (caller:Symbol {qualified_name: 'app.py::run'})"
                "-[r:CALLS]->(callee:Symbol "
                "{qualified_name: 'greeter.py::format_message'}) "
                "RETURN r.confidence"
            )
        )
        assert rows == [["EXTRACTED"]]


def test_calls_use_iter_callees_and_callers_readers(tmp_path):
    """DEC-025 helpers ``iter_callees_of`` + ``iter_callers_of`` power
    the future MCP ``impact()`` tool."""
    repo = _copy_fixture("python_sample", tmp_path)
    db_path = tmp_path / "graph.lbug"
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        callees = {s.qualified_name for s in store.iter_callees_of("app.py::run")}
        assert "greeter.py::format_message" in callees
        assert "greeter.py::Greeter" in callees

        callers = {s.qualified_name for s in store.iter_callers_of("greeter.py::format_message")}
        # Both app.py::run (via import) and greeter.py::Greeter.greet
        # (same-file) call format_message.
        assert "app.py::run" in callers
        assert "greeter.py::Greeter.greet" in callers


def test_calls_carry_evidence_tag(tmp_path):
    """Every CALLS edge stores its resolution path in ``evidence`` so
    debugging/auditing can trace why the resolver picked it."""
    repo = _copy_fixture("python_sample", tmp_path)
    db_path = tmp_path / "graph.lbug"
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        rows = list(
            store.query("MATCH ()-[r:CALLS]->() RETURN DISTINCT r.evidence ORDER BY r.evidence")
        )
        evidences = {r[0] for r in rows}
    # Python fixture should exercise at least same-file + import.
    assert "same-file" in evidences
    assert "import" in evidences


def test_calls_polyglot_every_language_produces_calls(tmp_path):
    """All 8 DEC-020 languages produce CALLS edges in one shared .lbug."""
    repo = tmp_path / "polyglot-calls"
    repo.mkdir()
    for sample in (
        "python_sample",
        "dart_sample",
        "swift_sample",
        "typescript_sample",
        "javascript_sample",
        "java_sample",
        "go_sample",
        "c_sample",
    ):
        shutil.copytree(FIXTURES / sample, repo / sample)
    db_path = tmp_path / "graph.lbug"
    out = _build(repo, db_path)
    assert out.calls_count >= 8
    with LadybugStore(db_path) as store:
        rows = list(
            store.query(
                "MATCH (caller:Symbol)-[:CALLS]->(callee:Symbol) "
                "MATCH (f:File {path: caller.file_path}) "
                "RETURN DISTINCT f.language ORDER BY f.language"
            )
        )
        langs = {r[0] for r in rows}
    # Every supported language with calls should appear. C, Dart, Go,
    # Java, JavaScript, Python, Swift, TypeScript -- at least one each.
    assert langs == {
        "c",
        "dart",
        "go",
        "java",
        "javascript",
        "python",
        "swift",
        "typescript",
    }


def test_calls_confidence_distribution(tmp_path):
    """Resolver produces a mix of EXTRACTED + INFERRED on the polyglot
    fixture. No AMBIGUOUS because fixtures have no name collisions —
    a dedicated test below covers that case."""
    repo = tmp_path / "polyglot-conf"
    repo.mkdir()
    for sample in (
        "python_sample",
        "typescript_sample",
        "java_sample",
        "c_sample",
        "dart_sample",
    ):
        shutil.copytree(FIXTURES / sample, repo / sample)
    db_path = tmp_path / "graph.lbug"
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        rows = list(
            store.query(
                "MATCH ()-[r:CALLS]->() RETURN r.confidence, count(r) ORDER BY r.confidence"
            )
        )
        by_conf = dict(rows)
    assert by_conf.get("EXTRACTED", 0) > 0
    assert by_conf.get("INFERRED", 0) > 0


def test_calls_ambiguous_when_multiple_same_name_defs(tmp_path):
    """DEC-015 + DEC-025: when cross-file fallback finds multiple
    candidates, emit AMBIGUOUS edges to EVERY one."""
    repo = tmp_path / "ambiguous"
    repo.mkdir()
    (repo / "a.py").write_text("def helper(): pass\n", encoding="utf-8")
    (repo / "b.py").write_text("def helper(): pass\n", encoding="utf-8")
    (repo / "c.py").write_text("def use(): helper()\n", encoding="utf-8")
    db_path = tmp_path / "graph.lbug"
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        rows = list(
            store.query(
                "MATCH (:Symbol {qualified_name: 'c.py::use'})-[r:CALLS]->"
                "(callee:Symbol) "
                "RETURN callee.qualified_name, r.confidence "
                "ORDER BY callee.qualified_name"
            )
        )
    assert rows == [
        ["a.py::helper", "AMBIGUOUS"],
        ["b.py::helper", "AMBIGUOUS"],
    ]


# ---------------------------------------------------------------------------
# DEC-026 — Commit / Author / TOUCHED_BY_COMMIT / AUTHORED_BY
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str, env_extra: dict[str, str] | None = None) -> None:
    """Local subprocess helper for committing into a tmp repo."""
    import os
    import subprocess

    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _commit_in(repo: Path, author: str, email: str, date: str, **files: str) -> None:
    """Commit *files* (name -> contents) with the given author + date."""
    for name, content in files.items():
        (repo / name).write_text(content, encoding="utf-8")
    env = {
        "GIT_AUTHOR_NAME": author,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_NAME": author,
        "GIT_COMMITTER_EMAIL": email,
        "GIT_COMMITTER_DATE": date,
    }
    _git(repo, "add", "-A")
    _git(
        repo,
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        f"add/update {','.join(files)}",
        env_extra=env,
    )


def _build_in_git(tmp_path: Path) -> tuple[Path, Path]:
    """Build a small real git repo with commits, return (repo_path, db_path)."""
    repo = tmp_path / "history_repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _commit_in(
        repo,
        author="Alice",
        email="alice@example.com",
        date="2022-01-01T00:00:00+00:00",
        **{"a.py": "def helper():\n    pass\n"},
    )
    _commit_in(
        repo,
        author="Alice",
        email="alice@example.com",
        date="2022-06-15T00:00:00+00:00",
        **{"a.py": "def helper():\n    return 1\n", "b.py": "from a import helper\n"},
    )
    _commit_in(
        repo,
        author="Bob",
        email="bob@example.com",
        date="2023-03-10T00:00:00+00:00",
        **{"a.py": "def helper():\n    return 2\n"},
    )
    db_path = tmp_path / "graph.lbug"
    return repo, db_path


def test_commit_and_author_nodes_persisted(tmp_path):
    """DEC-026: BuildGraphPhase writes every non-merge commit and every
    canonical author. Counts match the git log."""
    repo, db_path = _build_in_git(tmp_path)
    out = _build(repo, db_path)
    assert out.commit_count == 3
    assert out.author_count == 2  # Alice + Bob
    with LadybugStore(db_path) as store:
        rows = list(store.query("MATCH (a:Author) RETURN a.name ORDER BY a.name"))
        names = [r[0] for r in rows]
    assert names == ["Alice", "Bob"]


def test_authored_by_edges_link_commits_to_authors(tmp_path):
    """DEC-026: every Commit has exactly one outgoing AUTHORED_BY edge."""
    repo, db_path = _build_in_git(tmp_path)
    out = _build(repo, db_path)
    # 3 commits -> 3 AUTHORED_BY edges.
    assert out.authored_by_count == 3
    with LadybugStore(db_path) as store:
        rows = list(
            store.query(
                "MATCH (c:Commit)-[:AUTHORED_BY]->(a:Author) "
                "RETURN a.name, count(c) ORDER BY a.name"
            )
        )
    by_author = dict(rows)
    assert by_author["Alice"] == 2
    assert by_author["Bob"] == 1


def test_touched_by_commit_edges_only_for_inventoried_files(tmp_path):
    """DEC-026: git history may reference files we don't analyze
    (deleted / renamed / non-source). Only edges to inventoried files
    are persisted."""
    repo, db_path = _build_in_git(tmp_path)
    # Add a markdown commit that touches a non-source file. The repo's
    # inventory will exclude it; no TOUCHED_BY_COMMIT should be written
    # for it.
    _commit_in(
        repo,
        author="Carol",
        email="carol@example.com",
        date="2023-04-01T00:00:00+00:00",
        **{"README.md": "hello\n"},
    )
    out = _build(repo, db_path)
    with LadybugStore(db_path) as store:
        rows = list(
            store.query(
                "MATCH (f:File)-[:TOUCHED_BY_COMMIT]->(c:Commit) "
                "RETURN DISTINCT f.path ORDER BY f.path"
            )
        )
        touched_paths = [r[0] for r in rows]
    # Only .py files inventoried -> only those have edges.
    assert "a.py" in touched_paths
    assert "b.py" in touched_paths
    assert "README.md" not in touched_paths
    # 4 commits total now (3 from helper + Carol's) but only 3 touched
    # source files (a.py x3 commits + b.py x1 commit = 4 edges).
    assert out.touched_by_commit_count == 4


def test_history_edges_use_extracted_confidence(tmp_path):
    """DEC-026: git history is ground truth — every history-derived edge
    must be EXTRACTED."""
    repo, db_path = _build_in_git(tmp_path)
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        for rel in ("AUTHORED_BY", "TOUCHED_BY_COMMIT"):
            rows = list(store.query(f"MATCH ()-[r:{rel}]->() RETURN DISTINCT r.confidence"))
            assert rows == [["EXTRACTED"]], rel


def test_authors_deduped_across_commits(tmp_path):
    """DEC-026: two commits by the same author share one Author node
    (PK on email_canonical)."""
    repo, db_path = _build_in_git(tmp_path)
    out = _build(repo, db_path)
    # Alice has 2 commits but only 1 Author node.
    assert out.author_count == 2  # Alice + Bob
    with LadybugStore(db_path) as store:
        rows = list(store.query("MATCH (a:Author {name: 'Alice'}) RETURN count(a)"))
    assert rows == [[1]]


def test_history_phase_off_when_build_graph_db_disabled(tmp_path):
    """Verify the HistoryPhase doesn't waste time collecting per-commit
    files when build_graph_db is off."""
    repo, _ = _build_in_git(tmp_path)
    from forensic_deepdive.pipeline import Context, ExtractConfig, HistoryPhase

    cfg = ExtractConfig(repo_path=repo, output_dir=repo / "out", build_graph_db=False)
    out = HistoryPhase().run(Context(config=cfg))
    # commits list is empty when include_commit_files=False (the default
    # gated by build_graph_db).
    assert out.history.commits == []


# ---------------------------------------------------------------------------
# DEC-027 — CO_CHANGES_WITH derived from TOUCHED_BY_COMMIT joins
# ---------------------------------------------------------------------------


def _build_co_change_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Build a tmp git repo where:
    - a.py + b.py are committed together 3x (clear co-change pattern)
    - c.py is committed alone (no co-change)
    - d.py touches once with a.py (single co-occurrence)
    With threshold=2 we expect a single CO_CHANGES_WITH between a.py
    and b.py (count=3) and nothing else.
    """
    repo = tmp_path / "co_change_repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    commits = [
        ({"a.py": "# v1\n", "b.py": "# v1\n"}, "2023-01-01T00:00:00+00:00"),
        ({"a.py": "# v2\n", "b.py": "# v2\n"}, "2023-02-01T00:00:00+00:00"),
        ({"a.py": "# v3\n", "b.py": "# v3\n"}, "2023-03-01T00:00:00+00:00"),
        ({"c.py": "x = 1\n"}, "2023-04-01T00:00:00+00:00"),
        ({"a.py": "# touched alone\n", "d.py": "y = 2\n"}, "2023-05-01T00:00:00+00:00"),
    ]
    for files, date in commits:
        _commit_in(repo, author="Alice", email="alice@example.com", date=date, **files)
    db_path = tmp_path / "graph.lbug"
    return repo, db_path


def test_co_changes_with_threshold_filters_coincidence(tmp_path):
    """DEC-027: only file pairs with co-occurrence count >= threshold
    get edges. Default threshold = 2 — a single shared commit doesn't
    qualify."""
    repo, db_path = _build_co_change_repo(tmp_path)
    out = _build(repo, db_path)
    # a.py + b.py appear together in 3 commits -> 1 CO_CHANGES_WITH.
    # a.py + d.py appear together in 1 commit -> filtered out.
    # c.py alone -> no pairs.
    assert out.co_changes_count == 1
    with LadybugStore(db_path) as store:
        rows = list(
            store.query(
                "MATCH (a:File)-[r:CO_CHANGES_WITH]->(b:File) "
                "RETURN a.path, b.path, r.frequency ORDER BY a.path, b.path"
            )
        )
    assert rows == [["a.py", "b.py", 3.0]]


def test_co_changes_with_pair_stored_alphabetically(tmp_path):
    """DEC-027: each unordered pair {a, b} maps to exactly ONE edge with
    file_a < file_b alphabetically — no double-counting."""
    repo, db_path = _build_co_change_repo(tmp_path)
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        # Should be exactly 1 CO_CHANGES_WITH between a.py and b.py
        # (alphabetical: a < b), not 2.
        rows = list(
            store.query(
                "MATCH (:File {path: 'a.py'})-[r:CO_CHANGES_WITH]->(:File {path: 'b.py'}) "
                "RETURN count(r)"
            )
        )
        assert rows == [[1]]
        # The reverse direction shouldn't exist.
        rows = list(
            store.query(
                "MATCH (:File {path: 'b.py'})-[r:CO_CHANGES_WITH]->(:File {path: 'a.py'}) "
                "RETURN count(r)"
            )
        )
        assert rows == [[0]]


def test_co_changes_with_uses_inferred_confidence(tmp_path):
    """DEC-027: co-change is a computed signal, not a fact — INFERRED
    is the honest level."""
    repo, db_path = _build_co_change_repo(tmp_path)
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        rows = list(store.query("MATCH ()-[r:CO_CHANGES_WITH]->() RETURN DISTINCT r.confidence"))
    assert rows == [["INFERRED"]]


def test_co_changes_reader_returns_neighbors_in_both_directions(tmp_path):
    """The ``iter_co_changes_of`` reader walks the undirected co-change
    cluster — agents querying for a file's neighbors get them on
    either side of the alphabetically-stored edge."""
    repo, db_path = _build_co_change_repo(tmp_path)
    _build(repo, db_path)
    with LadybugStore(db_path) as store:
        # Querying from b.py finds a.py even though the edge is stored
        # a.py -> b.py.
        neighbors = [(f.path, freq) for f, freq in store.iter_co_changes_of("b.py")]
    assert neighbors == [("a.py", 3.0)]


def test_co_changes_threshold_is_configurable(tmp_path):
    """DEC-027: bumping ``co_changes_threshold`` raises the bar."""
    repo, db_path = _build_co_change_repo(tmp_path)
    # threshold=4 means a.py+b.py (count=3) drops out — no edges left.
    cfg = ExtractConfig(
        repo_path=repo.resolve(),
        output_dir=repo / "docs" / "codebase",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
        co_changes_threshold=4,
    )
    ctx = PipelineRunner(default_phases()).run(cfg)
    out = ctx.get(BuildGraphPhase)
    assert out.co_changes_count == 0


def test_co_changes_excludes_non_source_files(tmp_path):
    """DEC-027 inherits DEC-026's filter — co-change is computed only
    over inventoried source files. A README.md touched alongside a.py
    doesn't form a co-change edge."""
    repo = tmp_path / "cc_with_readme"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    for i in range(3):
        _commit_in(
            repo,
            author="Alice",
            email="alice@example.com",
            date=f"2023-0{i + 1}-01T00:00:00+00:00",
            **{"a.py": f"# {i}\n", "README.md": f"v{i}\n"},
        )
    db_path = tmp_path / "graph.lbug"
    out = _build(repo, db_path)
    # a.py + README.md together 3x, but README.md isn't a source file.
    # No CO_CHANGES_WITH edge.
    assert out.co_changes_count == 0


# ---------------------------------------------------------------------------
# DEC-028 — EXTENDS + IMPLEMENTS class-hierarchy edges
# ---------------------------------------------------------------------------


def test_extends_edge_python_same_file(tmp_path):
    """DEC-028: `class Derived(Base)` -> EXTRACTED EXTENDS edge."""
    repo = tmp_path / "ext_py"
    repo.mkdir()
    (repo / "a.py").write_text("class Base: pass\nclass Derived(Base): pass\n", encoding="utf-8")
    db_path = tmp_path / "graph.lbug"
    out = _build(repo, db_path)
    assert out.extends_count >= 1
    with LadybugStore(db_path) as store:
        rows = list(
            store.query(
                "MATCH (:Symbol {qualified_name: 'a.py::Derived'})-[r:EXTENDS]->"
                "(p:Symbol) RETURN p.qualified_name, r.confidence"
            )
        )
    assert rows == [["a.py::Base", "EXTRACTED"]]


def test_extends_and_implements_java(tmp_path):
    """DEC-028: Java `extends X implements I, J` produces 1 EXTENDS +
    2 IMPLEMENTS edges, all EXTRACTED."""
    repo = tmp_path / "ext_java"
    repo.mkdir()
    (repo / "A.java").write_text(
        "class Base {}\ninterface I {}\ninterface J {}\n"
        "class Derived extends Base implements I, J {}\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "graph.lbug"
    out = _build(repo, db_path)
    assert out.extends_count == 1
    assert out.implements_count == 2
    with LadybugStore(db_path) as store:
        impls = list(
            store.query(
                "MATCH (:Symbol {qualified_name: 'A.java::Derived'})-[:IMPLEMENTS]->"
                "(i:Symbol) RETURN i.qualified_name ORDER BY i.qualified_name"
            )
        )
    assert impls == [["A.java::I"], ["A.java::J"]]


def test_extends_cross_file_import_resolves_extracted(tmp_path):
    """DEC-028: when the parent class is imported, the EXTENDS edge
    resolves to the imported file's Symbol — EXTRACTED."""
    repo = tmp_path / "ext_ts"
    repo.mkdir()
    (repo / "base.ts").write_text("export class Base {}\n", encoding="utf-8")
    (repo / "derived.ts").write_text(
        'import { Base } from "./base";\nclass Derived extends Base {}\n',
        encoding="utf-8",
    )
    db_path = tmp_path / "graph.lbug"
    out = _build(repo, db_path)
    assert out.extends_count >= 1
    with LadybugStore(db_path) as store:
        rows = list(
            store.query(
                "MATCH (:Symbol {qualified_name: 'derived.ts::Derived'})-[r:EXTENDS]->"
                "(p:Symbol) RETURN p.qualified_name, r.confidence"
            )
        )
    assert rows == [["base.ts::Base", "EXTRACTED"]]


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
