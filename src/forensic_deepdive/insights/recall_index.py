"""Derived SQLite/FTS5 BM25 recall index for agent insights (DEC-069, v0.6 Step 6).

Lane-(iii) memory hardening. The JSONL store (DEC-019) stays the **authoritative**
source; this is a *derived*, rebuildable sidecar index — delete it and it rebuilds from
the JSONL files — that gives ``recall_insights`` BM25 ranking over the full insight text
(symbol + claim + evidence) instead of a linear substring scan. Reuses the DEC-041 lexical
sidecar infrastructure (stdlib ``sqlite3`` FTS5/BM25 — no new dependency, the pure-static
floor holds) and the DEC-036 content-hash discipline to dedup identical insights.

Located at ``<repo>/.forensic-deepdive/index/insights.db`` (next to the lexical sidecar).
Recall semantics stay backward-compatible: a symbol substring match (the DEC-019 contract)
is returned first (newest-first), then BM25 full-text matches — so the existing
``recall_insights(symbol, …)`` signature is unchanged, only its backend improves.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from forensic_deepdive.insights.store import Insight
from forensic_deepdive.query.lexical import _tokenize

_INDEX_SUBPATH = (".forensic-deepdive", "index", "insights.db")


def recall_index_path_for_jsonl(jsonl_path: Path) -> Path:
    """The sidecar index location derived from the JSONL store path. The JSONL lives at
    ``<repo>/.deepdive/insights.jsonl``; the index co-locates with the lexical sidecar."""
    jsonl_path = Path(jsonl_path)
    parent = jsonl_path.parent
    repo = parent.parent if parent.name == ".deepdive" else parent
    return repo.joinpath(*_INDEX_SUBPATH)


def _content_for(ins: Insight) -> str:
    """The FTS5-indexed text: tokens of the symbol + claim + evidence (camelCase-split,
    lowercased — the DEC-041 tokenizer), so natural-language queries match identifiers."""
    return " ".join(_tokenize(ins.symbol) + _tokenize(ins.claim) + _tokenize(ins.evidence))


def _fts5_available(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE _fts5_probe USING fts5(x)")
        conn.execute("DROP TABLE _fts5_probe")
        return True
    except sqlite3.OperationalError:
        return False


def build_recall_index(index_path: Path, insights: Iterable[Insight]) -> Path:
    """Build (or rebuild) the FTS5 recall index from *insights* — a wholesale wipe-and-
    rebuild (the DEC-030 graph semantics). **Dedup by content hash** (DEC-036): identical
    insights collapse to one row. Rows are ordered by ``(recorded_at, content_hash)`` so the
    index is byte-deterministic for a given set of insights."""
    index_path = Path(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if index_path.exists():
        index_path.unlink()

    # Dedup by content hash, keeping the EARLIEST recording of each distinct insight.
    by_hash: dict[str, Insight] = {}
    for ins in insights:
        h = ins.content_hash()
        prev = by_hash.get(h)
        if prev is None or ins.recorded_at < prev.recorded_at:
            by_hash[h] = ins
    ordered = sorted(by_hash.items(), key=lambda kv: (kv[1].recorded_at, kv[0]))

    conn = sqlite3.connect(index_path)
    try:
        if not _fts5_available(conn):
            raise RuntimeError(
                "this SQLite build lacks FTS5; the insight recall index needs it "
                "(CPython's bundled SQLite has shipped FTS5 since 3.9 / 2015)"
            )
        conn.execute(
            "CREATE TABLE insights("
            "id INTEGER PRIMARY KEY, content_hash TEXT UNIQUE, symbol TEXT, claim TEXT, "
            "evidence TEXT, verified_by TEXT, recorded_at TEXT, session_id TEXT)"
        )
        conn.execute("CREATE VIRTUAL TABLE insights_fts USING fts5(content)")
        for i, (h, ins) in enumerate(ordered, start=1):
            conn.execute(
                "INSERT INTO insights(id, content_hash, symbol, claim, evidence, "
                "verified_by, recorded_at, session_id) VALUES (?,?,?,?,?,?,?,?)",
                (
                    i,
                    h,
                    ins.symbol,
                    ins.claim,
                    ins.evidence,
                    ins.verified_by,
                    ins.recorded_at,
                    ins.session_id,
                ),
            )
            conn.execute(
                "INSERT INTO insights_fts(rowid, content) VALUES (?, ?)",
                (i, _content_for(ins)),
            )
        conn.commit()
    finally:
        conn.close()
    return index_path


def ensure_recall_index(index_path: Path, jsonl_path: Path) -> Path:
    """Rebuild the index from the authoritative JSONL when it is missing or stale (the JSONL
    has been written since the index was built). Cheap mtime check — the index is derived,
    so a rebuild is always safe."""
    from forensic_deepdive.insights.jsonl_store import JsonlInsightStore

    index_path = Path(index_path)
    jsonl_path = Path(jsonl_path)
    if not jsonl_path.exists():
        return index_path
    stale = (not index_path.exists()) or (jsonl_path.stat().st_mtime > index_path.stat().st_mtime)
    if stale:
        build_recall_index(index_path, JsonlInsightStore(jsonl_path).iter_all())
    return index_path


def _row_to_insight(row: tuple) -> Insight:
    return Insight(
        symbol=row[0],
        claim=row[1],
        evidence=row[2],
        verified_by=row[3],
        recorded_at=row[4],
        session_id=row[5],
    )


class InsightRecallIndex:
    """Read-only handle over a built recall index (the ``recall_insights`` backend)."""

    def __init__(self, index_path: Path) -> None:
        self.index_path = Path(index_path)

    def exists(self) -> bool:
        return self.index_path.is_file()

    def search(self, symbol: str, *, since: str | None = None, limit: int = 50) -> list[Insight]:
        """Backward-compatible recall (DEC-019 semantics) + BM25 (DEC-069): a **symbol
        substring** match first (newest-first — the existing contract), then **BM25**
        full-text matches for the query tokens (best-ranked first), de-duplicated. ``since``
        filters by ISO timestamp; ``limit`` caps the total."""
        if not self.exists():
            return []
        conn = sqlite3.connect(self.index_path)
        try:
            return self._search(conn, symbol, since, limit)
        finally:
            conn.close()

    def _search(
        self, conn: sqlite3.Connection, symbol: str, since: str | None, limit: int
    ) -> list[Insight]:
        cols = "symbol, claim, evidence, verified_by, recorded_at, session_id"
        seen: set[str] = set()
        out: list[Insight] = []

        def _keep(row: tuple) -> bool:
            ins = _row_to_insight(row)
            if since is not None and ins.recorded_at < since:
                return False
            key = ins.content_hash()
            if key in seen:
                return False
            seen.add(key)
            out.append(ins)
            return True

        # (a) symbol substring match — the DEC-019 contract, newest-first.
        for row in conn.execute(
            f"SELECT {cols} FROM insights WHERE symbol LIKE ? ESCAPE '\\' "
            "ORDER BY recorded_at DESC",
            (f"%{_like_escape(symbol)}%",),
        ):
            _keep(row)
            if len(out) >= limit:
                return out

        # (b) BM25 full-text over symbol+claim+evidence (best rank first).
        tokens = _query_tokens(symbol)
        if tokens:
            match_expr = " OR ".join(f"{tok}*" for tok in tokens)
            for row in conn.execute(
                "SELECT i.symbol, i.claim, i.evidence, i.verified_by, i.recorded_at, "
                "i.session_id, bm25(insights_fts) AS rank "
                "FROM insights_fts JOIN insights i ON i.id = insights_fts.rowid "
                "WHERE insights_fts MATCH ? ORDER BY rank ASC, i.recorded_at DESC",
                (match_expr,),
            ):
                _keep(row[:6])
                if len(out) >= limit:
                    break
        return out[:limit]


def _query_tokens(query: str) -> list[str]:
    seen: set[str] = set()
    tokens: list[str] = []
    for tok in _tokenize(query):
        if tok not in seen:
            seen.add(tok)
            tokens.append(tok)
    return tokens


def _like_escape(text: str) -> str:
    """Escape SQL LIKE wildcards so a symbol with ``%``/``_`` matches literally."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
