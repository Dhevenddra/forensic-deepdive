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
    CallsEndpointEdge,
    CoChangesWithEdge,
    Commit,
    DefinesEdge,
    Endpoint,
    ExtendsEdge,
    File,
    HandlesEdge,
    ImplementsEdge,
    ImportsEdge,
    MemberOfEdge,
    Module,
    Process,
    RoutesToEdge,
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

    @abstractmethod
    def add_endpoint(self, node: Endpoint) -> None: ...  # DEC-043

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

    @abstractmethod
    def add_handles(self, edge: HandlesEdge) -> None: ...  # DEC-043

    @abstractmethod
    def add_calls_endpoint(self, edge: CallsEndpointEdge) -> None: ...  # DEC-043

    @abstractmethod
    def add_routes_to(self, edge: RoutesToEdge) -> None: ...  # DEC-043

    # --- writes (batch, DEC-032) -------------------------------------------
    # Default implementations loop over the single-row equivalents — backends
    # that have a native bulk path (LadybugStore's UNWIND, future COPY FROM)
    # override these. Empty iterables are a no-op.

    def add_many_files(self, nodes: Iterable[File]) -> None:
        for n in nodes:
            self.add_file(n)

    def add_many_symbols(self, nodes: Iterable[Symbol]) -> None:
        for n in nodes:
            self.add_symbol(n)

    def add_many_modules(self, nodes: Iterable[Module]) -> None:
        for n in nodes:
            self.add_module(n)

    def add_many_commits(self, nodes: Iterable[Commit]) -> None:
        for n in nodes:
            self.add_commit(n)

    def add_many_authors(self, nodes: Iterable[Author]) -> None:
        for n in nodes:
            self.add_author(n)

    def add_many_defines(self, edges: Iterable[DefinesEdge]) -> None:
        for e in edges:
            self.add_defines(e)

    def add_many_member_of(self, edges: Iterable[MemberOfEdge]) -> None:
        for e in edges:
            self.add_member_of(e)

    def add_many_imports(self, edges: Iterable[ImportsEdge]) -> None:
        for e in edges:
            self.add_imports(e)

    def add_many_calls(self, edges: Iterable[CallsEdge]) -> None:
        for e in edges:
            self.add_calls(e)

    def add_many_extends(self, edges: Iterable[ExtendsEdge]) -> None:
        for e in edges:
            self.add_extends(e)

    def add_many_implements(self, edges: Iterable[ImplementsEdge]) -> None:
        for e in edges:
            self.add_implements(e)

    def add_many_touched_by_commit(self, edges: Iterable[TouchedByCommitEdge]) -> None:
        for e in edges:
            self.add_touched_by_commit(e)

    def add_many_authored_by(self, edges: Iterable[AuthoredByEdge]) -> None:
        for e in edges:
            self.add_authored_by(e)

    def add_many_co_changes_with(self, edges: Iterable[CoChangesWithEdge]) -> None:
        for e in edges:
            self.add_co_changes_with(e)

    def add_many_endpoints(self, nodes: Iterable[Endpoint]) -> None:
        for n in nodes:
            self.add_endpoint(n)

    def add_many_handles(self, edges: Iterable[HandlesEdge]) -> None:
        for e in edges:
            self.add_handles(e)

    def add_many_calls_endpoint(self, edges: Iterable[CallsEndpointEdge]) -> None:
        for e in edges:
            self.add_calls_endpoint(e)

    def add_many_routes_to(self, edges: Iterable[RoutesToEdge]) -> None:
        for e in edges:
            self.add_routes_to(e)

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
