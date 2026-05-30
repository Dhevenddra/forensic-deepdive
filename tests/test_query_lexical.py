"""SQLite FTS5/BM25 lexical index (DEC-041, PRD §4.5 test 1).

Offline, deterministic. No network, no graph — pure SymbolRecords in, ranked
hits out.
"""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.query.lexical import (
    LexicalIndex,
    SymbolRecord,
    build_lexical_index,
    lexical_index_path_for_db,
)


def _rec(qn: str, name: str, *, kind: str = "function", role: str = "source") -> SymbolRecord:
    return SymbolRecord(
        qualified_name=qn,
        name=name,
        signature="",
        file_path=qn.split("::")[0],
        kind=kind,
        role=role,
        line_start=1,
    )


def _index(tmp_path: Path, records: list[SymbolRecord]) -> LexicalIndex:
    path = build_lexical_index(tmp_path / "lexical.db", records)
    return LexicalIndex(path)


def test_exact_identifier_ranks_first(tmp_path: Path) -> None:
    records = [
        _rec("greeter.py::Greeter", "Greeter", kind="class"),
        _rec("greeter.py::Greeter.greet", "greet"),
        _rec("util.py::greet_helper", "greet_helper"),
    ]
    idx = _index(tmp_path, records)
    hits = idx.search("greet")
    assert hits[0].qualified_name == "greeter.py::Greeter.greet"  # exact name == "greet"
    assert hits[0].exact is True
    # prefix match still surfaces the class + helper.
    names = {h.qualified_name for h in hits}
    assert "greeter.py::Greeter" in names
    assert "util.py::greet_helper" in names


def test_prefix_match_finds_longer_identifier(tmp_path: Path) -> None:
    idx = _index(tmp_path, [_rec("a.py::Greeter", "Greeter", kind="class")])
    # "greet" is a prefix of the token "greeter".
    hits = idx.search("greet")
    assert any(h.qualified_name == "a.py::Greeter" for h in hits)


def test_camelcase_query_word_matches_identifier(tmp_path: Path) -> None:
    idx = _index(
        tmp_path,
        [
            _rec("ws.py::handleWebsocketReconnect", "handleWebsocketReconnect"),
            _rec("other.py::unrelated", "unrelated"),
        ],
    )
    hits = idx.search("websocket reconnection")
    assert hits, "a camelCase identifier should match its split words"
    assert hits[0].qualified_name == "ws.py::handleWebsocketReconnect"


def test_no_match_returns_empty(tmp_path: Path) -> None:
    idx = _index(tmp_path, [_rec("a.py::foo", "foo")])
    assert idx.search("zzzznotoken") == []
    assert idx.search("") == []


def test_search_is_deterministic_across_builds(tmp_path: Path) -> None:
    records = [
        _rec("a.py::parse", "parse"),
        _rec("b.py::parser", "parser"),
        _rec("c.py::Parser", "Parser", kind="class"),
    ]
    idx1 = _index(tmp_path / "one", records)
    idx2 = _index(tmp_path / "two", list(reversed(records)))  # different input order
    order1 = [h.qualified_name for h in idx1.search("parse")]
    order2 = [h.qualified_name for h in idx2.search("parse")]
    assert order1 == order2  # sorted-qn rowids => order independent of input order


def test_missing_index_search_is_empty(tmp_path: Path) -> None:
    idx = LexicalIndex(tmp_path / "nope.db")
    assert not idx.exists()
    assert idx.search("anything") == []


def test_index_path_resolves_from_default_graph_layout(tmp_path: Path) -> None:
    db = tmp_path / "repo" / ".deepdive" / "graph.lbug"
    got = lexical_index_path_for_db(db)
    assert got == tmp_path / "repo" / ".forensic-deepdive" / "index" / "lexical.db"


def test_index_path_resolves_for_custom_db_path(tmp_path: Path) -> None:
    db = tmp_path / "graph.lbug"  # not under .deepdive
    got = lexical_index_path_for_db(db)
    assert got == tmp_path / ".forensic-deepdive" / "index" / "lexical.db"
