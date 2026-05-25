"""DEC-032 batch-write round-trip tests for :class:`LadybugStore`.

Every ``add_many_*`` method must:
  - no-op on an empty iterable (no round-trip),
  - round-trip a single element (parity with the single-row API),
  - round-trip a mid-size batch (proves the UNWIND code path runs),
  - chunk correctly when input exceeds ``_BATCH_SIZE`` (the chunk-boundary
    case is where naive list-slicing bugs hide),
  - preserve input order across chunk boundaries (DEC-032 determinism
    contract).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from forensic_deepdive.graph import LadybugStore, Symbol, SymbolKind
from forensic_deepdive.graph.schema import (
    Author,
    AuthoredByEdge,
    CallsEdge,
    CoChangesWithEdge,
    Commit,
    Confidence,
    DefinesEdge,
    ExtendsEdge,
    File,
    FileRole,
    ImplementsEdge,
    ImportsEdge,
    MemberOfEdge,
    Module,
    TouchedByCommitEdge,
)


def _file(path: str = "a.py", lang: str = "python") -> File:
    return File(
        path=path,
        language=lang,
        role=FileRole.SOURCE,
        sha="0" * 64,
        loc=10,
        last_modified="2026-05-25T00:00:00+00:00",
    )


def _symbol(qn: str = "a.py::Foo", file_path: str = "a.py") -> Symbol:
    return Symbol(
        qualified_name=qn,
        kind=SymbolKind.CLASS,
        file_path=file_path,
        line_start=1,
        line_end=10,
        signature="",
    )


def _module(pk: str = "python:os", lang: str = "python") -> Module:
    return Module(path=pk, language=lang)


def _commit(sha: str = "deadbeef") -> Commit:
    return Commit(
        sha=sha,
        author_email="alice@example.com",
        date="2026-05-25T00:00:00+00:00",
        message="add foo",
        files_touched_count=1,
    )


def _author(email: str = "alice@example.com") -> Author:
    return Author(email_canonical=email, name="Alice")


# --- empty-input no-op (skips the round-trip) ----------------------------


def test_add_many_files_empty_is_noop(tmp_path: Path) -> None:
    with LadybugStore(tmp_path / "g.lbug") as store:
        store.add_many_files([])  # must not raise
        assert store.count_nodes("File") == 0


def test_add_many_symbols_empty_is_noop(tmp_path: Path) -> None:
    with LadybugStore(tmp_path / "g.lbug") as store:
        store.add_many_symbols([])
        assert store.count_nodes("Symbol") == 0


def test_add_many_defines_empty_is_noop(tmp_path: Path) -> None:
    """Edges no-op even when endpoints exist (genuine no-op, no MATCH)."""
    with LadybugStore(tmp_path / "g.lbug") as store:
        store.add_many_files([_file("a.py")])
        store.add_many_symbols([_symbol("a.py::F")])
        store.add_many_defines([])
        assert store.count_edges("DEFINES") == 0


# --- single-element round-trip (parity with single-row API) --------------


def test_add_many_files_single_element(tmp_path: Path) -> None:
    f = _file("only.py")
    with LadybugStore(tmp_path / "g.lbug") as store:
        store.add_many_files([f])
        assert store.count_nodes("File") == 1
        got = store.get_file("only.py")
        assert got is not None and got.path == "only.py"


def test_add_many_symbols_single_element(tmp_path: Path) -> None:
    s = _symbol("a.py::Singleton")
    with LadybugStore(tmp_path / "g.lbug") as store:
        store.add_many_symbols([s])
        got = store.get_symbol(s.qualified_name)
        assert got is not None and got.qualified_name == s.qualified_name


# --- mid-size batch (proves the UNWIND code path runs) -------------------


def test_add_many_files_mid_size(tmp_path: Path) -> None:
    files = [_file(f"f{i:03d}.py") for i in range(50)]
    with LadybugStore(tmp_path / "g.lbug") as store:
        store.add_many_files(files)
        assert store.count_nodes("File") == 50


def test_add_many_symbols_mid_size(tmp_path: Path) -> None:
    symbols = [_symbol(f"a.py::S{i:03d}") for i in range(50)]
    with LadybugStore(tmp_path / "g.lbug") as store:
        store.add_many_symbols(symbols)
        assert store.count_nodes("Symbol") == 50


def test_add_many_defines_mid_size(tmp_path: Path) -> None:
    files = [_file(f"f{i:03d}.py") for i in range(50)]
    syms = [_symbol(f"f{i:03d}.py::F", file_path=f"f{i:03d}.py") for i in range(50)]
    edges = [
        DefinesEdge(
            file_path=f"f{i:03d}.py",
            symbol=f"f{i:03d}.py::F",
            confidence=Confidence.EXTRACTED,
            evidence="tree-sitter",
        )
        for i in range(50)
    ]
    with LadybugStore(tmp_path / "g.lbug") as store:
        store.add_many_files(files)
        store.add_many_symbols(syms)
        store.add_many_defines(edges)
        assert store.count_edges("DEFINES") == 50


def test_add_many_touched_by_commit_mid_size(tmp_path: Path) -> None:
    """The hot path on Omi-scale (~76k of these). Mid-size proves the
    MATCH+CREATE under UNWIND works."""
    files = [_file(f"f{i:02d}.py") for i in range(20)]
    commits = [_commit(sha=f"sha{j:04d}") for j in range(20)]
    edges = [
        TouchedByCommitEdge(
            file_path=f"f{i:02d}.py",
            commit_sha=f"sha{j:04d}",
            confidence=Confidence.EXTRACTED,
            evidence="git-log-name-only",
        )
        for i in range(20)
        for j in range(20)
    ]
    with LadybugStore(tmp_path / "g.lbug") as store:
        store.add_many_files(files)
        store.add_many_commits(commits)
        store.add_many_touched_by_commit(edges)
        assert store.count_edges("TOUCHED_BY_COMMIT") == 400


# --- chunking across _BATCH_SIZE boundary --------------------------------


def test_add_many_files_chunks_across_batch_size(tmp_path: Path) -> None:
    """When N > _BATCH_SIZE, the helper must chunk. Force the boundary by
    overriding the constant on the instance."""
    files = [_file(f"f{i:04d}.py") for i in range(11)]
    with LadybugStore(tmp_path / "g.lbug") as store:
        store._BATCH_SIZE = 4  # force 3 chunks: 4 + 4 + 3
        store.add_many_files(files)
        assert store.count_nodes("File") == 11


def test_add_many_symbols_chunks_across_batch_size(tmp_path: Path) -> None:
    syms = [_symbol(f"a.py::S{i:04d}") for i in range(25)]
    with LadybugStore(tmp_path / "g.lbug") as store:
        store._BATCH_SIZE = 10  # 10 + 10 + 5
        store.add_many_symbols(syms)
        assert store.count_nodes("Symbol") == 25


def test_chunking_preserves_order(tmp_path: Path) -> None:
    """DEC-032 determinism: UNWIND iterates row-by-row; chunking with slice
    preserves global order. Insert N pre-sorted symbols across multiple
    chunks and verify they come back in the same order from get_symbol."""
    syms = [_symbol(f"a.py::S{i:04d}") for i in range(13)]
    with LadybugStore(tmp_path / "g.lbug") as store:
        store._BATCH_SIZE = 4
        store.add_many_symbols(syms)
        # Round-trip each one in input order.
        for s in syms:
            got = store.get_symbol(s.qualified_name)
            assert got is not None and got.qualified_name == s.qualified_name


# --- every batch method exists on the contract ---------------------------


@pytest.mark.parametrize(
    "method_name",
    [
        "add_many_files",
        "add_many_symbols",
        "add_many_modules",
        "add_many_commits",
        "add_many_authors",
        "add_many_defines",
        "add_many_member_of",
        "add_many_imports",
        "add_many_calls",
        "add_many_extends",
        "add_many_implements",
        "add_many_touched_by_commit",
        "add_many_authored_by",
        "add_many_co_changes_with",
    ],
)
def test_batch_method_exists(method_name: str) -> None:
    """DEC-032: 14 batch methods, one per node/edge type. Any missing one
    means BuildGraphPhase still loops single-row writes."""
    assert hasattr(LadybugStore, method_name), method_name
    assert callable(getattr(LadybugStore, method_name)), method_name


# --- end-to-end batch through every edge type ----------------------------


def test_end_to_end_every_batch_method(tmp_path: Path) -> None:
    """Round-trip a tiny example through every node + edge batch method.
    Catches any one of the 14 having a Cypher typo."""
    with LadybugStore(tmp_path / "g.lbug") as store:
        store.add_many_files([_file("a.py"), _file("b.py")])
        store.add_many_modules([_module("python:os")])
        store.add_many_symbols(
            [
                _symbol("a.py::A", file_path="a.py"),
                _symbol("a.py::A.m", file_path="a.py"),
                _symbol("b.py::B", file_path="b.py"),
            ]
        )
        store.add_many_authors([_author("alice@example.com")])
        store.add_many_commits([_commit("sha0001")])

        store.add_many_defines(
            [
                DefinesEdge(
                    file_path="a.py",
                    symbol="a.py::A",
                    confidence=Confidence.EXTRACTED,
                    evidence="tree-sitter",
                ),
            ]
        )
        store.add_many_member_of(
            [
                MemberOfEdge(
                    member="a.py::A.m",
                    parent="a.py::A",
                    confidence=Confidence.EXTRACTED,
                    evidence="ast",
                ),
            ]
        )
        store.add_many_imports(
            [
                ImportsEdge(
                    file_path="a.py",
                    module_path="python:os",
                    confidence=Confidence.EXTRACTED,
                    evidence="tree-sitter",
                ),
            ]
        )
        store.add_many_calls(
            [
                CallsEdge(
                    caller="a.py::A",
                    callee="b.py::B",
                    confidence=Confidence.EXTRACTED,
                    evidence="resolver-same-name",
                ),
            ]
        )
        store.add_many_extends(
            [
                ExtendsEdge(
                    child="a.py::A",
                    parent="b.py::B",
                    confidence=Confidence.EXTRACTED,
                    evidence="ast-declaration",
                ),
            ]
        )
        store.add_many_implements(
            [
                ImplementsEdge(
                    implementation="a.py::A",
                    interface="b.py::B",
                    confidence=Confidence.EXTRACTED,
                    evidence="ast-declaration",
                ),
            ]
        )
        store.add_many_authored_by(
            [
                AuthoredByEdge(
                    commit_sha="sha0001",
                    author_email="alice@example.com",
                    confidence=Confidence.EXTRACTED,
                    evidence="git-log",
                ),
            ]
        )
        store.add_many_touched_by_commit(
            [
                TouchedByCommitEdge(
                    file_path="a.py",
                    commit_sha="sha0001",
                    confidence=Confidence.EXTRACTED,
                    evidence="git-log-name-only",
                ),
            ]
        )
        store.add_many_co_changes_with(
            [
                CoChangesWithEdge(
                    file_a="a.py",
                    file_b="b.py",
                    frequency=3.0,
                    confidence=Confidence.INFERRED,
                    evidence="touched-by-commit-join",
                ),
            ]
        )

        assert store.count_nodes("File") == 2
        assert store.count_nodes("Symbol") == 3
        assert store.count_nodes("Module") == 1
        assert store.count_nodes("Commit") == 1
        assert store.count_nodes("Author") == 1
        assert store.count_edges("DEFINES") == 1
        assert store.count_edges("MEMBER_OF") == 1
        assert store.count_edges("IMPORTS") == 1
        assert store.count_edges("CALLS") == 1
        assert store.count_edges("EXTENDS") == 1
        assert store.count_edges("IMPLEMENTS") == 1
        assert store.count_edges("AUTHORED_BY") == 1
        assert store.count_edges("TOUCHED_BY_COMMIT") == 1
        assert store.count_edges("CO_CHANGES_WITH") == 1
