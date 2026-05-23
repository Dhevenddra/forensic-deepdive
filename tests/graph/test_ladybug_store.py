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


def test_unimplemented_writes_raise_with_clear_message(tmp_path):
    """The skeleton's NotImplementedError messages must point at the PRD
    item where the implementation lands."""
    from forensic_deepdive.graph import (
        Author,
        CallsEdge,
        File,
        Module,
    )
    from forensic_deepdive.graph.schema import FileRole

    with LadybugStore(tmp_path / "graph.lbug") as store:
        with pytest.raises(NotImplementedError, match="PRD"):
            store.add_file(
                File(
                    path="a.py",
                    language="python",
                    role=FileRole.SOURCE,
                    sha="x",
                    loc=0,
                    last_modified="2026-05-24T00:00:00Z",
                )
            )
        with pytest.raises(NotImplementedError, match="PRD"):
            store.add_module(Module(path="m", language="python"))
        with pytest.raises(NotImplementedError, match="PRD"):
            store.add_author(Author(email_canonical="x@y", name="X"))
        with pytest.raises(NotImplementedError, match="PRD"):
            store.add_calls(CallsEdge(caller="a", callee="b"))
