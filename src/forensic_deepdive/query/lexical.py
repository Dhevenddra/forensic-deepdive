"""Sidecar SQLite FTS5/BM25 lexical index (DEC-041).

The always-on, deterministic, offline floor of the hybrid NL query (DEC-038).
LadybugDB has no full-text search, so we keep a sidecar SQLite file at
``<repo>/.forensic-deepdive/index/lexical.db``. FTS5 + BM25 ship in the stdlib
``sqlite3`` (no new dependency).

Schema (DEC-041): a plain ``symbols`` table paired with an external-content
``symbols_fts`` FTS5 table whose ``rowid`` is ``symbols.id``. ``id`` is assigned
in ``sorted(qualified_name)`` order so the index — and therefore query ordering
— is byte-deterministic for a given repo state.

Search ordering: exact (case-insensitive) identifier matches first, then BM25
prefix matches. Prefix matching (``token*``) is what lets ``greet`` match the
token ``greeter``.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from forensic_deepdive.graph import LadybugStore

# Default sidecar location, relative to the repo root.
_INDEX_SUBPATH = (".forensic-deepdive", "index", "lexical.db")


# ---------------------------------------------------------------------------
# Records / hits
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SymbolRecord:
    """One symbol to index. ``name`` is the leaf identifier; ``role`` is the
    DEC-012/021 file role used by output shaping."""

    qualified_name: str
    name: str
    signature: str
    file_path: str
    kind: str
    role: str
    line_start: int


@dataclass(frozen=True, slots=True)
class LexicalHit:
    """One lexical match. ``score`` is a relevance score where higher is
    better (BM25 is negated so it composes with the rest of the stack);
    ``exact`` marks an exact-identifier match (the strongest lexical signal)."""

    qualified_name: str
    name: str
    file_path: str
    line_start: int
    kind: str
    role: str
    score: float
    exact: bool


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------

_NON_ALNUM = re.compile(r"[^0-9a-zA-Z]+")
# camelCase / PascalCase boundary: a lower/digit followed by an upper, or an
# acronym run followed by a Capitalized word (HTTPServer -> HTTP, Server).
_CAMEL_1 = re.compile(r"([a-z0-9])([A-Z])")
_CAMEL_2 = re.compile(r"([A-Z]+)([A-Z][a-z])")


def _split_camel(token: str) -> list[str]:
    token = _CAMEL_2.sub(r"\1 \2", token)
    token = _CAMEL_1.sub(r"\1 \2", token)
    return token.split()


def _tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumerics AND camelCase boundaries.

    ``handleWebsocketReconnect`` -> ``["handle", "websocket", "reconnect"]`` so
    natural-language words match identifiers (DEC-041).
    """
    if not text:
        return []
    out: list[str] = []
    for chunk in _NON_ALNUM.split(text):
        if not chunk:
            continue
        out.extend(part.lower() for part in _split_camel(chunk) if part)
    return out


def _query_tokens(query: str) -> list[str]:
    """Distinct query tokens, order-preserving."""
    seen: set[str] = set()
    tokens: list[str] = []
    for tok in _tokenize(query):
        if tok not in seen:
            seen.add(tok)
            tokens.append(tok)
    return tokens


def _leaf_name(qualified_name: str) -> str:
    """The bare identifier: part after the last ``::`` then the last ``.``."""
    tail = qualified_name.split("::")[-1]
    return tail.split(".")[-1]


def _content_for(rec: SymbolRecord) -> str:
    """The FTS5-indexed text for a record: tokens of the leaf name + the
    qn_local + the signature (signature is ``""`` today — DEC-041 reserves it
    for when signature/docstring extraction lands)."""
    qn_local = rec.qualified_name.split("::")[-1]
    tokens = _tokenize(rec.name) + _tokenize(qn_local) + _tokenize(rec.signature)
    return " ".join(tokens)


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def lexical_index_path(repo_path: Path) -> Path:
    """The canonical sidecar location under a repo root."""
    return Path(repo_path).joinpath(*_INDEX_SUBPATH)


def lexical_index_path_for_db(db_path: Path) -> Path:
    """Resolve the sidecar index path from a graph-db path (DEC-041).

    The default graph lives at ``<repo>/.deepdive/graph.lbug`` — strip that to
    find the repo root. For a custom/test db path, co-locate the index under
    the db's parent so it's still deterministically derivable.
    """
    db_path = Path(db_path)
    parent = db_path.parent
    repo = parent.parent if parent.name == ".deepdive" else parent
    return lexical_index_path(repo)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def _fts5_available(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE _fts5_probe USING fts5(x)")
        conn.execute("DROP TABLE _fts5_probe")
        return True
    except sqlite3.OperationalError:
        return False


def build_lexical_index(index_path: Path, records: Iterable[SymbolRecord]) -> Path:
    """Build (or rebuild) the FTS5 index at *index_path* from *records*.

    Wholesale rebuild — mirrors DEC-030's wipe-and-rebuild graph semantics.
    ``id`` is assigned in sorted-``qualified_name`` order for determinism.
    """
    index_path = Path(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if index_path.exists():
        index_path.unlink()

    conn = sqlite3.connect(index_path)
    try:
        if not _fts5_available(conn):
            raise RuntimeError(
                "this SQLite build lacks FTS5; the lexical query floor needs it "
                "(CPython's bundled SQLite has shipped FTS5 since 3.9 / 2015)"
            )
        conn.execute(
            "CREATE TABLE symbols("
            "id INTEGER PRIMARY KEY, qualified_name TEXT, name TEXT, "
            "signature TEXT, file_path TEXT, kind TEXT, role TEXT, line_start INTEGER)"
        )
        conn.execute("CREATE VIRTUAL TABLE symbols_fts USING fts5(content)")
        ordered = sorted(records, key=lambda r: r.qualified_name)
        for i, rec in enumerate(ordered, start=1):
            conn.execute(
                "INSERT INTO symbols(id, qualified_name, name, signature, "
                "file_path, kind, role, line_start) VALUES (?,?,?,?,?,?,?,?)",
                (
                    i,
                    rec.qualified_name,
                    rec.name,
                    rec.signature,
                    rec.file_path,
                    rec.kind,
                    rec.role,
                    rec.line_start,
                ),
            )
            conn.execute(
                "INSERT INTO symbols_fts(rowid, content) VALUES (?, ?)",
                (i, _content_for(rec)),
            )
        conn.commit()
    finally:
        conn.close()
    return index_path


def records_from_store(store: LadybugStore) -> list[SymbolRecord]:
    """Read every indexable symbol from a populated graph store.

    Joins Symbol -> File for the role (shaping input). Synthetic ``<module>``
    symbols are skipped — they carry no searchable identifier. Shared by the
    lexical and semantic index builders so both index exactly the same set.
    """
    role_by_path: dict[str, str] = {
        path: role for path, role in store.query("MATCH (f:File) RETURN f.path, f.role")
    }
    records: list[SymbolRecord] = []
    for qn, kind, fp, ls, sig in store.query(
        "MATCH (s:Symbol) RETURN s.qualified_name, s.kind, s.file_path, s.line_start, s.signature"
    ):
        name = _leaf_name(qn)
        if name == "<module>":
            continue
        records.append(
            SymbolRecord(
                qualified_name=qn,
                name=name,
                signature=sig or "",
                file_path=fp,
                kind=kind,
                role=role_by_path.get(fp, "source"),
                line_start=int(ls),
            )
        )
    return records


def build_lexical_index_from_store(store: LadybugStore, index_path: Path) -> Path:
    """Build the lexical index from a populated graph store.

    The single builder used by both the extract-time pre-build (BuildGraphPhase)
    and the lazy first-query rebuild (nl.hybrid_query).
    """
    return build_lexical_index(index_path, records_from_store(store))


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class LexicalIndex:
    """Read-only handle over a built lexical index."""

    def __init__(self, index_path: Path) -> None:
        self.index_path = Path(index_path)

    def exists(self) -> bool:
        return self.index_path.is_file()

    def search(self, query: str, *, limit: int = 50) -> list[LexicalHit]:
        """Return ranked hits: exact-identifier matches first (sorted by
        qualified_name), then BM25 prefix matches (best first), de-duplicated.
        Empty if the query has no usable tokens or the index is missing."""
        tokens = _query_tokens(query)
        if not tokens or not self.exists():
            return []

        conn = sqlite3.connect(self.index_path)
        try:
            return self._search(conn, tokens, limit)
        finally:
            conn.close()

    def _search(self, conn: sqlite3.Connection, tokens: list[str], limit: int) -> list[LexicalHit]:
        seen: set[str] = set()
        hits: list[LexicalHit] = []

        # (a) Exact-identifier matches — strongest lexical signal. Deterministic
        # order by qualified_name.
        placeholders = ",".join("?" for _ in tokens)
        for row in conn.execute(
            "SELECT qualified_name, name, file_path, kind, role, line_start "
            f"FROM symbols WHERE lower(name) IN ({placeholders}) "
            "ORDER BY qualified_name",
            tokens,
        ):
            qn = row[0]
            if qn in seen:
                continue
            seen.add(qn)
            hits.append(_row_to_hit(row, score=1.0, exact=True))
            if len(hits) >= limit:
                return hits

        # (b) BM25 prefix matches. bm25() is smaller-is-better and negative;
        # negate so higher == better for the rest of the stack. Tie-break by
        # qualified_name for total order.
        # Tokens are guaranteed alphanumeric (see _tokenize), so a bareword
        # prefix term is safe and lets "greet" match the token "greeter".
        match_expr = " OR ".join(f"{tok}*" for tok in tokens)
        for row in conn.execute(
            "SELECT s.qualified_name, s.name, s.file_path, s.kind, s.role, "
            "s.line_start, bm25(symbols_fts) AS rank "
            "FROM symbols_fts JOIN symbols s ON s.id = symbols_fts.rowid "
            "WHERE symbols_fts MATCH ? "
            "ORDER BY rank ASC, s.qualified_name ASC",
            (match_expr,),
        ):
            qn = row[0]
            if qn in seen:
                continue
            seen.add(qn)
            hits.append(_row_to_hit(row[:6], score=-float(row[6]), exact=False))
            if len(hits) >= limit:
                break
        return hits


def _row_to_hit(row: tuple, *, score: float, exact: bool) -> LexicalHit:
    qn, name, fp, kind, role, ls = row
    return LexicalHit(
        qualified_name=qn,
        name=name,
        file_path=fp,
        line_start=int(ls),
        kind=kind,
        role=role,
        score=score,
        exact=exact,
    )
