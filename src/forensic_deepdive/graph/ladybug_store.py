"""LadybugDB-backed :class:`GraphStore` implementation.

DEC-013. Wraps the ``real_ladybug`` Python bindings (PyPI dist ``real-ladybug``,
import name ``real_ladybug`` — note the underscore and the awkward ``real_``
prefix; the v0.2 contract is that no code outside this module imports it).

This is the v0.2 phase-1 *skeleton*. ``connect``, ``close``, ``add_symbol``,
``get_symbol``, and ``query`` are implemented (enough to round-trip one node
and back the kickoff smoke test). Other writes raise :class:`NotImplementedError`
and are filled in during PRD §10 item 8 (graph build phase).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import real_ladybug as lb  # noqa: I001 — single allowed call site per DEC-013

from forensic_deepdive.graph.schema import (
    NODE_TABLES,
    REL_TABLES,
    Author,
    AuthoredByEdge,
    CallsEdge,
    CoChangesWithEdge,
    Commit,
    DefinesEdge,
    ExtendsEdge,
    File,
    ImplementsEdge,
    ImportsEdge,
    MemberOfEdge,
    Module,
    Process,
    Symbol,
    SymbolKind,
    TouchedByCommitEdge,
)
from forensic_deepdive.graph.store import GraphStore


class LadybugStore(GraphStore):
    """Embedded graph store backed by LadybugDB (Kuzu community fork)."""

    def __init__(self, db_path: str | Path) -> None:
        super().__init__(db_path)
        self._db: Any | None = None
        self._conn: Any | None = None

    # --- lifecycle ----------------------------------------------------------

    def connect(self) -> None:
        if self._connected:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = lb.Database(str(self.db_path))
        self._conn = lb.Connection(self._db)
        for ddl in (*NODE_TABLES, *REL_TABLES):
            self._conn.execute(ddl)
        self._connected = True

    def close(self) -> None:
        # real_ladybug holds native handles; dropping the Python refs releases
        # them deterministically. No explicit .close() on the bindings.
        self._conn = None
        self._db = None
        self._connected = False

    # --- writes (nodes) -----------------------------------------------------

    def add_symbol(self, node: Symbol) -> None:
        self._require_conn()
        self._conn.execute(
            "CREATE (n:Symbol {"
            "qualified_name: $qualified_name, kind: $kind, "
            "file_path: $file_path, line_start: $line_start, "
            "line_end: $line_end, signature: $signature})",
            {
                "qualified_name": node.qualified_name,
                "kind": str(node.kind),
                "file_path": node.file_path,
                "line_start": node.line_start,
                "line_end": node.line_end,
                "signature": node.signature,
            },
        )

    def add_file(self, node: File) -> None:
        self._require_conn()
        self._conn.execute(
            "CREATE (n:File {"
            "path: $path, language: $language, role: $role, sha: $sha, "
            "loc: $loc, last_modified: $last_modified})",
            {
                "path": node.path,
                "language": node.language,
                "role": str(node.role),
                "sha": node.sha,
                "loc": node.loc,
                "last_modified": node.last_modified,
            },
        )

    def add_module(self, node: Module) -> None:
        """DEC-024. One Module node per imported package/file/URI.

        Module path is the primary key; callers must dedup before
        writing — see ``BuildGraphPhase`` which groups by
        ``(module_path, language)`` and writes once per unique pair.
        """
        self._require_conn()
        self._conn.execute(
            "CREATE (n:Module {path: $path, language: $language})",
            {"path": node.path, "language": node.language},
        )

    def add_commit(self, node: Commit) -> None:
        """DEC-026. One Commit node per non-merge commit. ``sha`` is the
        PK; callers dedup before writing."""
        self._require_conn()
        self._conn.execute(
            "CREATE (n:Commit {"
            "sha: $sha, author_email: $email, date: $date, "
            "message: $msg, files_touched_count: $ftc})",
            {
                "sha": node.sha,
                "email": node.author_email,
                "date": node.date,
                "msg": node.message,
                "ftc": node.files_touched_count,
            },
        )

    def add_author(self, node: Author) -> None:
        """DEC-026. One Author node per canonical (mailmap-resolved)
        identity. ``email_canonical`` is the PK; callers dedup before
        writing. Both human contributors and bot accounts (per DEC-022)
        get Author nodes — agents can filter on ``kind`` at query time
        if they want only humans."""
        self._require_conn()
        self._conn.execute(
            "CREATE (n:Author {email_canonical: $email, name: $name})",
            {"email": node.email_canonical, "name": node.name},
        )

    def add_process(self, node: Process) -> None:
        raise NotImplementedError("PRD §10 future — Process nodes")

    # --- writes (edges) -----------------------------------------------------

    def add_calls(self, edge: CallsEdge) -> None:
        """DEC-025. CALLS edge from caller Symbol to callee Symbol.

        Both endpoints must already exist. Confidence reflects the
        resolver step that matched (EXTRACTED for same-file or
        explicit-name import; INFERRED for whole-module / wildcard
        import and single-candidate cross-file fallback; AMBIGUOUS
        when multiple candidates remain — one edge per candidate is
        emitted, all surfaced per DEC-015).
        """
        self._require_conn()
        self._conn.execute(
            "MATCH (caller:Symbol {qualified_name: $cq}), "
            "(callee:Symbol {qualified_name: $eq}) "
            "CREATE (caller)-[:CALLS {confidence: $conf, evidence: $ev}]->(callee)",
            {
                "cq": edge.caller,
                "eq": edge.callee,
                "conf": str(edge.confidence),
                "ev": edge.evidence,
            },
        )

    def add_imports(self, edge: ImportsEdge) -> None:
        """DEC-024. File -> Module dependency. Both endpoints must exist.

        Always ``EXTRACTED`` confidence today — imports are
        AST-deterministic. v0.3 may add INFERRED for re-export chains
        whose source module isn't itself imported.
        """
        self._require_conn()
        self._conn.execute(
            "MATCH (f:File {path: $fp}), (m:Module {path: $mp}) "
            "CREATE (f)-[:IMPORTS {confidence: $conf, evidence: $ev}]->(m)",
            {
                "fp": edge.file_path,
                "mp": edge.module_path,
                "conf": str(edge.confidence),
                "ev": edge.evidence,
            },
        )

    def add_extends(self, edge: ExtendsEdge) -> None:
        raise NotImplementedError("PRD §10 future — EXTENDS edges")

    def add_implements(self, edge: ImplementsEdge) -> None:
        raise NotImplementedError("PRD §10 future — IMPLEMENTS edges")

    def add_defines(self, edge: DefinesEdge) -> None:
        self._require_conn()
        self._conn.execute(
            "MATCH (f:File {path: $fp}), (s:Symbol {qualified_name: $sq}) "
            "CREATE (f)-[:DEFINES {confidence: $conf, evidence: $ev}]->(s)",
            {
                "fp": edge.file_path,
                "sq": edge.symbol,
                "conf": str(edge.confidence),
                "ev": edge.evidence,
            },
        )

    def add_member_of(self, edge: MemberOfEdge) -> None:
        """DEC-023. Member -> parent containment edge. Both endpoints must
        already exist as Symbol nodes (callers add parents before children
        by ordering on the dotted qualified-name prefix)."""
        self._require_conn()
        self._conn.execute(
            "MATCH (m:Symbol {qualified_name: $mq}), "
            "(p:Symbol {qualified_name: $pq}) "
            "CREATE (m)-[:MEMBER_OF {confidence: $conf, evidence: $ev}]->(p)",
            {
                "mq": edge.member,
                "pq": edge.parent,
                "conf": str(edge.confidence),
                "ev": edge.evidence,
            },
        )

    def add_touched_by_commit(self, edge: TouchedByCommitEdge) -> None:
        """DEC-026. File touched by a Commit. Both endpoints must exist.
        Always EXTRACTED — ``git log --name-only`` is ground truth."""
        self._require_conn()
        self._conn.execute(
            "MATCH (f:File {path: $fp}), (c:Commit {sha: $sha}) "
            "CREATE (f)-[:TOUCHED_BY_COMMIT {confidence: $conf, evidence: $ev}]->(c)",
            {
                "fp": edge.file_path,
                "sha": edge.commit_sha,
                "conf": str(edge.confidence),
                "ev": edge.evidence,
            },
        )

    def add_authored_by(self, edge: AuthoredByEdge) -> None:
        """DEC-026. Commit -> Author. Both endpoints must exist. Always
        EXTRACTED — every commit has exactly one author per git."""
        self._require_conn()
        self._conn.execute(
            "MATCH (c:Commit {sha: $sha}), (a:Author {email_canonical: $email}) "
            "CREATE (c)-[:AUTHORED_BY {confidence: $conf, evidence: $ev}]->(a)",
            {
                "sha": edge.commit_sha,
                "email": edge.author_email,
                "conf": str(edge.confidence),
                "ev": edge.evidence,
            },
        )

    def add_co_changes_with(self, edge: CoChangesWithEdge) -> None:
        """DEC-027. Two files frequently committed together. ``INFERRED``
        by default — co-change is a computed signal, not a fact. The
        edge is undirected in spirit but Cypher requires direction;
        callers convention: ``file_a < file_b`` alphabetically so each
        unordered pair becomes exactly one edge."""
        self._require_conn()
        self._conn.execute(
            "MATCH (a:File {path: $a}), (b:File {path: $b}) "
            "CREATE (a)-[:CO_CHANGES_WITH "
            "{confidence: $conf, evidence: $ev, frequency: $freq}]->(b)",
            {
                "a": edge.file_a,
                "b": edge.file_b,
                "conf": str(edge.confidence),
                "ev": edge.evidence,
                "freq": edge.frequency,
            },
        )

    # --- reads --------------------------------------------------------------

    def get_symbol(self, qualified_name: str) -> Symbol | None:
        self._require_conn()
        rows = list(
            self.query(
                "MATCH (n:Symbol {qualified_name: $qn}) "
                "RETURN n.qualified_name, n.kind, n.file_path, "
                "n.line_start, n.line_end, n.signature",
                {"qn": qualified_name},
            )
        )
        if not rows:
            return None
        qn, kind, file_path, line_start, line_end, signature = rows[0]
        return Symbol(
            qualified_name=qn,
            kind=SymbolKind(kind),
            file_path=file_path,
            line_start=int(line_start),
            line_end=int(line_end),
            signature=signature or "",
        )

    def get_file(self, path: str) -> File | None:
        """Return the file with that path, or ``None`` if absent."""
        from forensic_deepdive.graph.schema import FileRole

        self._require_conn()
        rows = list(
            self.query(
                "MATCH (n:File {path: $p}) "
                "RETURN n.path, n.language, n.role, n.sha, n.loc, n.last_modified",
                {"p": path},
            )
        )
        if not rows:
            return None
        p, lang, role, sha, loc, last_mod = rows[0]
        return File(
            path=p,
            language=lang,
            role=FileRole(role),
            sha=sha,
            loc=int(loc),
            last_modified=last_mod,
        )

    def iter_symbols_for_file(self, file_path: str) -> Iterator[Symbol]:
        """Stream every symbol defined in *file_path* per the DEFINES edges."""
        self._require_conn()
        for row in self.query(
            "MATCH (:File {path: $fp})-[:DEFINES]->(s:Symbol) "
            "RETURN s.qualified_name, s.kind, s.file_path, "
            "s.line_start, s.line_end, s.signature",
            {"fp": file_path},
        ):
            qn, kind, fp, ls, le, sig = row
            yield Symbol(
                qualified_name=qn,
                kind=SymbolKind(kind),
                file_path=fp,
                line_start=int(ls),
                line_end=int(le),
                signature=sig or "",
            )

    def parent_of(self, member_qn: str) -> Symbol | None:
        """Return the parent Symbol of *member_qn* via the MEMBER_OF edge,
        or ``None`` if the symbol is top-level (no MEMBER_OF outgoing)."""
        self._require_conn()
        rows = list(
            self.query(
                "MATCH (:Symbol {qualified_name: $mq})-[:MEMBER_OF]->(p:Symbol) "
                "RETURN p.qualified_name, p.kind, p.file_path, "
                "p.line_start, p.line_end, p.signature",
                {"mq": member_qn},
            )
        )
        if not rows:
            return None
        qn, kind, fp, ls, le, sig = rows[0]
        return Symbol(
            qualified_name=qn,
            kind=SymbolKind(kind),
            file_path=fp,
            line_start=int(ls),
            line_end=int(le),
            signature=sig or "",
        )

    def iter_members_of(self, parent_qn: str) -> Iterator[Symbol]:
        """Stream every Symbol that has a MEMBER_OF edge to *parent_qn*."""
        self._require_conn()
        for row in self.query(
            "MATCH (m:Symbol)-[:MEMBER_OF]->(:Symbol {qualified_name: $pq}) "
            "RETURN m.qualified_name, m.kind, m.file_path, "
            "m.line_start, m.line_end, m.signature",
            {"pq": parent_qn},
        ):
            qn, kind, fp, ls, le, sig = row
            yield Symbol(
                qualified_name=qn,
                kind=SymbolKind(kind),
                file_path=fp,
                line_start=int(ls),
                line_end=int(le),
                signature=sig or "",
            )

    def iter_callees_of(self, caller_qn: str) -> Iterator[Symbol]:
        """Stream symbols *caller_qn* calls via outgoing CALLS edges.
        Powers the MCP ``impact(symbol, direction='downstream')`` tool."""
        self._require_conn()
        for row in self.query(
            "MATCH (:Symbol {qualified_name: $cq})-[:CALLS]->(callee:Symbol) "
            "RETURN callee.qualified_name, callee.kind, callee.file_path, "
            "callee.line_start, callee.line_end, callee.signature",
            {"cq": caller_qn},
        ):
            qn, kind, fp, ls, le, sig = row
            yield Symbol(
                qualified_name=qn,
                kind=SymbolKind(kind),
                file_path=fp,
                line_start=int(ls),
                line_end=int(le),
                signature=sig or "",
            )

    def iter_callers_of(self, callee_qn: str) -> Iterator[Symbol]:
        """Stream symbols that call *callee_qn* via incoming CALLS edges.
        Powers the MCP ``impact(symbol, direction='upstream')`` tool."""
        self._require_conn()
        for row in self.query(
            "MATCH (caller:Symbol)-[:CALLS]->(:Symbol {qualified_name: $eq}) "
            "RETURN caller.qualified_name, caller.kind, caller.file_path, "
            "caller.line_start, caller.line_end, caller.signature",
            {"eq": callee_qn},
        ):
            qn, kind, fp, ls, le, sig = row
            yield Symbol(
                qualified_name=qn,
                kind=SymbolKind(kind),
                file_path=fp,
                line_start=int(ls),
                line_end=int(le),
                signature=sig or "",
            )

    def iter_co_changes_of(self, file_path: str) -> Iterator[tuple[File, float]]:
        """Stream files that co-change with *file_path* via CO_CHANGES_WITH
        edges, plus the edge's frequency score. Bidirectional — the
        builder writes the edge in alphabetical order but agents
        querying for a file's co-change cluster want neighbors on either
        side."""
        from forensic_deepdive.graph.schema import FileRole

        self._require_conn()
        for row in self.query(
            "MATCH (a:File {path: $p})-[r:CO_CHANGES_WITH]-(b:File) "
            "RETURN b.path, b.language, b.role, b.sha, b.loc, "
            "b.last_modified, r.frequency "
            "ORDER BY r.frequency DESC, b.path",
            {"p": file_path},
        ):
            p, lang, role, sha, loc, last_mod, freq = row
            yield (
                File(
                    path=p,
                    language=lang,
                    role=FileRole(role),
                    sha=sha,
                    loc=int(loc),
                    last_modified=last_mod,
                ),
                float(freq),
            )

    def count_nodes(self, label: str) -> int:
        """Convenience for tests and stats: count nodes of a given label."""
        self._require_conn()
        rows = list(self.query(f"MATCH (n:{label}) RETURN count(n)"))
        return int(rows[0][0]) if rows else 0

    def count_edges(self, label: str) -> int:
        """Convenience for tests and stats: count edges of a given REL label."""
        self._require_conn()
        rows = list(self.query(f"MATCH ()-[r:{label}]->() RETURN count(r)"))
        return int(rows[0][0]) if rows else 0

    def iter_symbols(self) -> Iterator[Symbol]:
        self._require_conn()
        for row in self.query(
            "MATCH (n:Symbol) RETURN n.qualified_name, n.kind, n.file_path, "
            "n.line_start, n.line_end, n.signature"
        ):
            qn, kind, file_path, line_start, line_end, signature = row
            yield Symbol(
                qualified_name=qn,
                kind=SymbolKind(kind),
                file_path=file_path,
                line_start=int(line_start),
                line_end=int(line_end),
                signature=signature or "",
            )

    def query(self, cypher: str, params: dict | None = None) -> Iterable[list]:
        self._require_conn()
        result = self._conn.execute(cypher, params) if params else self._conn.execute(cypher)
        while result.has_next():
            yield result.get_next()

    # --- internals ----------------------------------------------------------

    def _require_conn(self) -> None:
        if not self._connected or self._conn is None:
            raise RuntimeError("LadybugStore: call connect() before use")
