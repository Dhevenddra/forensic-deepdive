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


def test_dec084_name_substring_bridges_inflection_and_outranks_unrelated(tmp_path: Path) -> None:
    """DEC-084 — the Iris-Nearby "where are messages encoded/decoded" miss.

    BM25 prefix matching is one-directional, so the query term ``encoded`` could
    never reach the identifier token ``encode``; the literal-name hits
    ``_encode/_decodeMessageWithMedia`` were missed entirely while theme/toggle
    junk surfaced. The name-substring tier (with de-inflection) must (a) FIND the
    real hits and (b) rank them above the unrelated symbols."""
    records = [
        _rec("nearby.py::_encodeMessageWithMedia", "_encodeMessageWithMedia"),
        _rec("nearby.py::_decodeMessageWithMedia", "_decodeMessageWithMedia"),
        _rec("theme.py::ThemeProvider.toggleTheme", "toggleTheme", kind="method"),
        _rec("notif.py::registerNotificationChannel", "registerNotificationChannel"),
    ]
    idx = _index(tmp_path, records)
    hits = idx.search("where are messages encoded decoded")
    names = [h.qualified_name for h in hits]
    # (a) Recall: both real hits are found despite the "encoded"/"decoded" inflection.
    assert "nearby.py::_encodeMessageWithMedia" in names
    assert "nearby.py::_decodeMessageWithMedia" in names
    # (b) Ranking: the name hits outrank the unrelated symbols (which don't carry
    # "message"/"encod"/"decod"), and are flagged name_match.
    top2 = set(names[:2])
    assert top2 == {"nearby.py::_encodeMessageWithMedia", "nearby.py::_decodeMessageWithMedia"}
    assert all(h.name_match for h in hits[:2])
    assert "theme.py::ThemeProvider.toggleTheme" not in names


def test_dec084_destem_and_terms() -> None:
    """The de-inflection helper strips one common suffix (≥3 chars kept) and the
    term builder drops stopwords / <3-char tokens, keeping token + stem."""
    from forensic_deepdive.query.lexical import _destem, _name_match_terms, _query_tokens

    assert _destem("encoded") == "encod"
    assert _destem("messages") == "messag"
    assert _destem("decoded") == "decod"
    assert _destem("set") == "set"  # too short to strip below 3
    terms = _name_match_terms(_query_tokens("where are messages encoded"))
    assert "where" not in terms and "are" not in terms  # stopwords dropped
    assert "messag" in terms and "encod" in terms  # stems present


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
