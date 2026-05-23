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
        raise NotImplementedError("PRD §10 future — Module nodes")

    def add_commit(self, node: Commit) -> None:
        raise NotImplementedError("PRD §10 future — Commit nodes")

    def add_author(self, node: Author) -> None:
        raise NotImplementedError("PRD §10 future — Author nodes")

    def add_process(self, node: Process) -> None:
        raise NotImplementedError("PRD §10 future — Process nodes")

    # --- writes (edges) -----------------------------------------------------

    def add_calls(self, edge: CallsEdge) -> None:
        # CALLS requires symbol-level resolution; v0.2 phase 1 only writes
        # what the v0.1 name-based pipeline can produce honestly.
        raise NotImplementedError("PRD §10 future — symbol-level CALLS resolver")

    def add_imports(self, edge: ImportsEdge) -> None:
        raise NotImplementedError("PRD §10 future — import extraction")

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
        raise NotImplementedError("PRD §10 future — MEMBER_OF edges")

    def add_touched_by_commit(self, edge: TouchedByCommitEdge) -> None:
        raise NotImplementedError("PRD §10 future — TOUCHED_BY_COMMIT edges")

    def add_authored_by(self, edge: AuthoredByEdge) -> None:
        raise NotImplementedError("PRD §10 future — AUTHORED_BY edges")

    def add_co_changes_with(self, edge: CoChangesWithEdge) -> None:
        raise NotImplementedError("PRD §10 future — CO_CHANGES_WITH edges")

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
