"""Round-trip tests for :class:`LadybugStore`.

DEC-013. The kickoff acceptance gate for v0.2 phase 1: a Symbol node written
to a fresh ``.lbug`` DB comes back identical on read.
"""

from __future__ import annotations

import pytest

from forensic_deepdive.graph import LadybugStore, Symbol, SymbolKind


def _sample_symbol() -> Symbol:
    return Symbol(
        qualified_name="src/foo.py::Bar.baz",
        kind=SymbolKind.METHOD,
        file_path="src/foo.py",
        line_start=10,
        line_end=42,
        signature="def baz(self, x: int) -> str",
    )


def test_instantiate_does_not_open_db(tmp_path):
    # connect() is explicit; constructing the store must not touch the FS.
    store = LadybugStore(tmp_path / "graph.lbug")
    assert not store._connected
    assert not (tmp_path / "graph.lbug").exists()


def test_connect_creates_db_and_schema(tmp_path):
    store = LadybugStore(tmp_path / "graph.lbug")
    store.connect()
    try:
        assert store._connected
        # Schema query must succeed (proves the DDL ran).
        rows = list(store.query("MATCH (n:Symbol) RETURN count(n)"))
        assert rows == [[0]]
    finally:
        store.close()


def test_round_trip_single_symbol(tmp_path):
    """The kickoff smoke test: write a Symbol, read it back, get the same
    dataclass back."""
    sym = _sample_symbol()
    with LadybugStore(tmp_path / "graph.lbug") as store:
        store.add_symbol(sym)
        got = store.get_symbol(sym.qualified_name)
    assert got == sym


def test_get_symbol_returns_none_when_absent(tmp_path):
    with LadybugStore(tmp_path / "graph.lbug") as store:
        assert store.get_symbol("nope") is None


def test_iter_symbols_yields_every_inserted(tmp_path):
    symbols = [
        Symbol(
            qualified_name=f"f.py::s{i}",
            kind=SymbolKind.FUNCTION,
            file_path="f.py",
            line_start=i,
            line_end=i + 1,
        )
        for i in range(3)
    ]
    with LadybugStore(tmp_path / "graph.lbug") as store:
        for s in symbols:
            store.add_symbol(s)
        got = sorted(store.iter_symbols(), key=lambda s: s.qualified_name)
    assert got == symbols


def test_connect_is_idempotent(tmp_path):
    store = LadybugStore(tmp_path / "graph.lbug")
    store.connect()
    store.connect()  # must not crash
    store.close()


def test_close_is_idempotent(tmp_path):
    store = LadybugStore(tmp_path / "graph.lbug")
    store.connect()
    store.close()
    store.close()  # must not crash


def test_reopen_existing_db_preserves_data(tmp_path):
    db_path = tmp_path / "graph.lbug"
    sym = _sample_symbol()
    with LadybugStore(db_path) as store:
        store.add_symbol(sym)
    with LadybugStore(db_path) as store2:
        assert store2.get_symbol(sym.qualified_name) == sym


def test_use_before_connect_raises(tmp_path):
    store = LadybugStore(tmp_path / "graph.lbug")
    with pytest.raises(RuntimeError, match="connect"):
        store.add_symbol(_sample_symbol())


def test_all_dec013_schema_writes_are_implemented(tmp_path):
    """Item 8b complete: every node and edge type declared in the
    DEC-013 schema now has a real LadybugStore.add_* implementation.
    Smoke-test by calling each on an empty DB and verifying no
    NotImplementedError is raised (Cypher MATCH-failures from missing
    endpoints are expected and OK — what we're guarding against is
    the v0.2-phase-1 NotImplementedError surface)."""
    from forensic_deepdive.graph import (
        CoChangesWithEdge,
        ExtendsEdge,
        ImplementsEdge,
    )

    with LadybugStore(tmp_path / "graph.lbug") as store:
        # These are MATCH-then-CREATE Cypher and will silently no-op
        # when endpoints don't exist. Just verify they don't raise
        # NotImplementedError anymore.
        try:
            store.add_co_changes_with(CoChangesWithEdge(file_a="x", file_b="y"))
            store.add_extends(ExtendsEdge(child="x", parent="y"))
            store.add_implements(ImplementsEdge(implementation="x", interface="y"))
        except NotImplementedError as exc:  # pragma: no cover
            pytest.fail(f"item 8b incomplete: {exc}")


def test_file_round_trip(tmp_path):
    """DEC-013 / item 8. File node writes via add_file and reads back via
    get_file, with role enum preserved."""
    from forensic_deepdive.graph import File
    from forensic_deepdive.graph.schema import FileRole

    f = File(
        path="src/foo.py",
        language="python",
        role=FileRole.SOURCE,
        sha="abc123",
        loc=42,
        last_modified="2026-05-24T12:00:00+00:00",
    )
    with LadybugStore(tmp_path / "graph.lbug") as store:
        store.add_file(f)
        got = store.get_file("src/foo.py")
    assert got == f


def test_defines_edge_links_file_to_symbol(tmp_path):
    """DEC-013 / item 8. After add_file + add_symbol + add_defines, the
    File-DEFINES->Symbol traversal returns the symbol."""
    from forensic_deepdive.graph import DefinesEdge, File
    from forensic_deepdive.graph.schema import FileRole

    f = File(
        path="src/foo.py",
        language="python",
        role=FileRole.SOURCE,
        sha="abc",
        loc=10,
        last_modified="2026-05-24T12:00:00+00:00",
    )
    s = Symbol(
        qualified_name="src/foo.py::Foo",
        kind=SymbolKind.CLASS,
        file_path="src/foo.py",
        line_start=1,
        line_end=5,
    )
    with LadybugStore(tmp_path / "graph.lbug") as store:
        store.add_file(f)
        store.add_symbol(s)
        store.add_defines(DefinesEdge(file_path=f.path, symbol=s.qualified_name))
        got = list(store.iter_symbols_for_file(f.path))
    assert got == [s]


def test_count_nodes_and_edges(tmp_path):
    """Convenience for stats. After a small build, counts are right."""
    from forensic_deepdive.graph import DefinesEdge, File
    from forensic_deepdive.graph.schema import FileRole

    with LadybugStore(tmp_path / "graph.lbug") as store:
        for i in range(3):
            store.add_file(
                File(
                    path=f"f{i}.py",
                    language="python",
                    role=FileRole.SOURCE,
                    sha="x",
                    loc=1,
                    last_modified="2026-05-24T00:00:00Z",
                )
            )
            store.add_symbol(
                Symbol(
                    qualified_name=f"f{i}.py::S",
                    kind=SymbolKind.CLASS,
                    file_path=f"f{i}.py",
                    line_start=1,
                    line_end=1,
                )
            )
            store.add_defines(DefinesEdge(file_path=f"f{i}.py", symbol=f"f{i}.py::S"))
        assert store.count_nodes("File") == 3
        assert store.count_nodes("Symbol") == 3
        assert store.count_edges("DEFINES") == 3
