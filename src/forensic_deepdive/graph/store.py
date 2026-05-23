"""``GraphStore`` — the abstract backend interface.

DEC-013. Every backend (v0.2 LadybugDB, future ArcadeDB / DuckDB-graph)
implements this; the rest of the codebase imports only this ABC.

The surface is intentionally narrow. Higher-level concerns (DAG runner,
PageRank, MCP tool implementations) live in callers — the store knows only
about *connect, schema, write, read, query*.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from pathlib import Path

from forensic_deepdive.graph.schema import (
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
    TouchedByCommitEdge,
)


class GraphStore(ABC):
    """Embedded code-knowledge graph backend.

    Lifecycle: ``__init__(db_path)`` → :meth:`connect` → use → :meth:`close`.
    Also usable as a context manager. The schema is created on first
    :meth:`connect` (idempotent; ``CREATE … IF NOT EXISTS``).
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._connected = False

    # --- lifecycle ----------------------------------------------------------

    @abstractmethod
    def connect(self) -> None:
        """Open the DB; create node/rel tables if absent. Idempotent."""

    @abstractmethod
    def close(self) -> None:
        """Release native resources. Idempotent."""

    def __enter__(self) -> GraphStore:
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    # --- writes (nodes) -----------------------------------------------------

    @abstractmethod
    def add_file(self, node: File) -> None: ...

    @abstractmethod
    def add_symbol(self, node: Symbol) -> None: ...

    @abstractmethod
    def add_module(self, node: Module) -> None: ...

    @abstractmethod
    def add_commit(self, node: Commit) -> None: ...

    @abstractmethod
    def add_author(self, node: Author) -> None: ...

    @abstractmethod
    def add_process(self, node: Process) -> None: ...

    # --- writes (edges) -----------------------------------------------------

    @abstractmethod
    def add_calls(self, edge: CallsEdge) -> None: ...

    @abstractmethod
    def add_imports(self, edge: ImportsEdge) -> None: ...

    @abstractmethod
    def add_extends(self, edge: ExtendsEdge) -> None: ...

    @abstractmethod
    def add_implements(self, edge: ImplementsEdge) -> None: ...

    @abstractmethod
    def add_defines(self, edge: DefinesEdge) -> None: ...

    @abstractmethod
    def add_member_of(self, edge: MemberOfEdge) -> None: ...

    @abstractmethod
    def add_touched_by_commit(self, edge: TouchedByCommitEdge) -> None: ...

    @abstractmethod
    def add_authored_by(self, edge: AuthoredByEdge) -> None: ...

    @abstractmethod
    def add_co_changes_with(self, edge: CoChangesWithEdge) -> None: ...

    # --- reads --------------------------------------------------------------

    @abstractmethod
    def get_symbol(self, qualified_name: str) -> Symbol | None:
        """Return the symbol with that primary key, or ``None`` if absent."""

    @abstractmethod
    def iter_symbols(self) -> Iterator[Symbol]:
        """Stream every symbol. Order is backend-defined; sort upstream if you
        need determinism."""

    @abstractmethod
    def query(self, cypher: str, params: dict | None = None) -> Iterable[list]:
        """Run an arbitrary Cypher query and yield rows. The MCP ``query``
        tool (DEC-016, planned) calls this directly; callers must understand
        backend-specific Cypher dialect quirks."""
