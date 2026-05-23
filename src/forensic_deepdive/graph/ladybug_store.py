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
        raise NotImplementedError("PRD §10 item 8 — graph build phase")

    def add_module(self, node: Module) -> None:
        raise NotImplementedError("PRD §10 item 8 — graph build phase")

    def add_commit(self, node: Commit) -> None:
        raise NotImplementedError("PRD §10 item 8 — graph build phase")

    def add_author(self, node: Author) -> None:
        raise NotImplementedError("PRD §10 item 8 — graph build phase")

    def add_process(self, node: Process) -> None:
        raise NotImplementedError("PRD §10 item 8 — graph build phase")

    # --- writes (edges) -----------------------------------------------------

    def add_calls(self, edge: CallsEdge) -> None:
        raise NotImplementedError("PRD §10 item 8 — graph build phase")

    def add_imports(self, edge: ImportsEdge) -> None:
        raise NotImplementedError("PRD §10 item 8 — graph build phase")

    def add_extends(self, edge: ExtendsEdge) -> None:
        raise NotImplementedError("PRD §10 item 8 — graph build phase")

    def add_implements(self, edge: ImplementsEdge) -> None:
        raise NotImplementedError("PRD §10 item 8 — graph build phase")

    def add_defines(self, edge: DefinesEdge) -> None:
        raise NotImplementedError("PRD §10 item 8 — graph build phase")

    def add_member_of(self, edge: MemberOfEdge) -> None:
        raise NotImplementedError("PRD §10 item 8 — graph build phase")

    def add_touched_by_commit(self, edge: TouchedByCommitEdge) -> None:
        raise NotImplementedError("PRD §10 item 8 — graph build phase")

    def add_authored_by(self, edge: AuthoredByEdge) -> None:
        raise NotImplementedError("PRD §10 item 8 — graph build phase")

    def add_co_changes_with(self, edge: CoChangesWithEdge) -> None:
        raise NotImplementedError("PRD §10 item 8 — graph build phase")

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
