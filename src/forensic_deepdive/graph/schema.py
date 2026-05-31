"""Schema for the v0.2 code knowledge graph.

PRD_v0.2 §4.2 (nodes / edges) and §4.4 (confidence taxonomy, DEC-015 plumbing).
Node and Edge dataclasses are the in-Python contract; ``NODE_TABLES`` and
``REL_TABLES`` translate that contract into LadybugDB Cypher DDL (DEC-013).

Every edge carries a ``confidence`` field — DEC-015 is satisfied at the schema
layer in v0.2 phase 1 even though only EXTRACTED edges are produced today.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Confidence(StrEnum):
    """DEC-015. Every edge carries one of these."""

    EXTRACTED = "EXTRACTED"
    INFERRED = "INFERRED"
    AMBIGUOUS = "AMBIGUOUS"


class SymbolKind(StrEnum):
    """PRD §4.2 Symbol.kind. Open list — extend per language as needed."""

    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    INTERFACE = "interface"
    STRUCT = "struct"
    ENUM = "enum"
    MODULE = "module"
    TRAIT = "trait"
    DECORATOR = "decorator"
    ROUTE = "route"
    TYPE = "type"  # type aliases (TS, Go), typedefs (C), generic types


class FileRole(StrEnum):
    """DEC-012 + DEC-021 + DEC-049. v0.1 has source/test/fixture; v0.2 adds
    vendored/generated; v0.4 adds example (in the graph, but demoted in ranking
    + query). Carried here so the schema is the source of truth."""

    SOURCE = "source"
    TEST = "test"
    FIXTURE = "fixture"
    VENDORED = "vendored"
    GENERATED = "generated"
    EXAMPLE = "example"  # DEC-049


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Node:
    """Marker base. Not abstract — concrete nodes inherit just for typing."""


@dataclass(frozen=True, slots=True)
class File(Node):
    path: str  # repo-relative, forward-slashed (PRIMARY KEY)
    language: str
    role: FileRole
    sha: str  # SHA-256 of content, hex
    loc: int
    last_modified: str  # ISO-8601 UTC


@dataclass(frozen=True, slots=True)
class Symbol(Node):
    qualified_name: str  # e.g. "src/foo/bar.py::Baz.qux" (display / human-facing key)
    kind: SymbolKind
    file_path: str  # FK to File.path
    line_start: int
    line_end: int
    signature: str = ""  # rendered declaration, optional
    # DEC-051 (v0.4 Item A): the stable node ID — the LadybugDB PRIMARY KEY.
    # Minted by ``static.ids.make_symbol_id`` (``<kind>:<rel_path>:<qn_local>``
    # + overload disambiguator), it is line-number-free so it survives an
    # unrelated same-file edit (the v1.0 incremental/rename seam). Falls back to
    # ``qualified_name`` when unset, so read-side reconstructions and ad-hoc
    # construction need not supply it.
    node_id: str = ""

    def __post_init__(self) -> None:
        if not self.node_id:
            object.__setattr__(self, "node_id", self.qualified_name)


@dataclass(frozen=True, slots=True)
class Module(Node):
    """A target of an IMPORTS edge.

    DEC-024 schema convention: ``path`` is the LadybugDB primary key and
    encodes both the language and the raw module identifier as
    ``"<language>:<raw_path>"`` (e.g. ``"python:os"``,
    ``"go:os"``, ``"java:java.util.List"``). This avoids the cross-language
    collision real-ladybug would otherwise hit on its single-column PK
    (Python and Go both importing ``os`` would map to the same node).

    Use :func:`module_pk` to construct it; do not concatenate manually.
    """

    path: str  # PRIMARY KEY — format: f"{language}:{raw_path}"
    language: str  # redundant with the prefix in path; kept for query ergonomics


def module_pk(language: str, raw_path: str) -> str:
    """DEC-024 convention. The Module-table PK that disambiguates
    cross-language same-string imports (``python:os`` vs ``go:os``)."""
    return f"{language}:{raw_path}"


@dataclass(frozen=True, slots=True)
class Commit(Node):
    sha: str  # PRIMARY KEY
    author_email: str  # FK to Author.email_canonical
    date: str  # ISO-8601 UTC
    message: str
    files_touched_count: int


@dataclass(frozen=True, slots=True)
class Author(Node):
    email_canonical: str  # PRIMARY KEY (post-mailmap, DEC-022 planned)
    name: str


@dataclass(frozen=True, slots=True)
class Process(Node):
    """Execution flow — populated lazily by the `flow` MCP tool. PRD §4.5."""

    name: str  # PRIMARY KEY
    entry_point_symbol: str  # FK to Symbol.qualified_name
    terminal_symbol: str = ""  # FK to Symbol.qualified_name, may be empty


@dataclass(frozen=True, slots=True)
class Endpoint(Node):
    """DEC-043 (v0.4). The canonical cross-boundary contract — the join *node*.

    PK is ``contract_id`` (e.g. ``http::GET::/users/{param}``), built by a
    per-protocol key-builder. A consumer with no resolvable provider still gets
    an Endpoint (CALLS_ENDPOINT with no HANDLES — the honest "calls an endpoint
    we can't locate"), which is also the v0.5 cross-repo federation seam."""

    contract_id: str  # PRIMARY KEY
    protocol: str  # "http" (v0.4); "grpc" / "topic" are v0.5
    method: str = ""  # HTTP verb, or "" for method-agnostic / non-HTTP
    normalized_path: str = ""  # the canonical path/key portion
    raw_path_samples: str = ""  # a few originals for display (joined)
    framework: str = ""  # fastapi | flask | spring | express | ...
    spec_backed: bool = False  # DEC-048 — backed by an OpenAPI/proto/etc. spec


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Edge:
    """All edges carry confidence (DEC-015). Concrete edges add their own
    endpoint fields; ``evidence`` is a free-form short tag (e.g. "tree-sitter",
    "scip", "string-match")."""

    confidence: Confidence = Confidence.EXTRACTED
    evidence: str = ""


@dataclass(frozen=True, slots=True)
class CallsEdge(Edge):
    caller: str = ""  # Symbol.qualified_name
    callee: str = ""  # Symbol.qualified_name
    # DEC-037 (v0.3 Item C): how the callee was resolved — the rationale
    # behind ``confidence``. ``bare`` = a bare-name call (DEC-025's resolver);
    # ``self``/``this`` = receiver is the enclosing instance; ``ctor`` = receiver
    # bound to a local constructor; ``static`` = class-qualified ``Foo.bar()``;
    # ``module`` = import-alias-qualified ``mod.bar()``. Debuggability +
    # confidence rationale; never silently upgrades the confidence tag.
    via: str = "bare"


@dataclass(frozen=True, slots=True)
class ImportsEdge(Edge):
    file_path: str = ""  # File.path
    module_path: str = ""  # Module.path


@dataclass(frozen=True, slots=True)
class ExtendsEdge(Edge):
    child: str = ""  # Symbol.qualified_name
    parent: str = ""  # Symbol.qualified_name


@dataclass(frozen=True, slots=True)
class ImplementsEdge(Edge):
    implementation: str = ""  # Symbol.qualified_name
    interface: str = ""  # Symbol.qualified_name


@dataclass(frozen=True, slots=True)
class DefinesEdge(Edge):
    """Always EXTRACTED — the file literally contains the symbol's AST node."""

    file_path: str = ""
    symbol: str = ""
    confidence: Confidence = Confidence.EXTRACTED


@dataclass(frozen=True, slots=True)
class MemberOfEdge(Edge):
    """Always EXTRACTED — lexical containment is AST-deterministic."""

    member: str = ""  # Symbol.qualified_name
    parent: str = ""  # Symbol.qualified_name (class/module)
    confidence: Confidence = Confidence.EXTRACTED


@dataclass(frozen=True, slots=True)
class TouchedByCommitEdge(Edge):
    """Always EXTRACTED — `git log --name-only` is ground truth."""

    file_path: str = ""
    commit_sha: str = ""
    confidence: Confidence = Confidence.EXTRACTED


@dataclass(frozen=True, slots=True)
class AuthoredByEdge(Edge):
    """Always EXTRACTED — every commit has exactly one author."""

    commit_sha: str = ""
    author_email: str = ""
    confidence: Confidence = Confidence.EXTRACTED


@dataclass(frozen=True, slots=True)
class CoChangesWithEdge(Edge):
    """INFERRED by default — co-change is a computed signal, not a fact."""

    file_a: str = ""
    file_b: str = ""
    frequency: float = 0.0
    confidence: Confidence = Confidence.INFERRED


# --- cross-boundary edges (DEC-043, v0.4) ----------------------------------


@dataclass(frozen=True, slots=True)
class HandlesEdge(Edge):
    """A provider Symbol (route handler) exposes an Endpoint contract. The
    audit trail behind a ROUTES_TO. ``symbol`` is the handler's qualified_name."""

    symbol: str = ""  # provider Symbol.qualified_name
    contract_id: str = ""  # Endpoint PK
    confidence: Confidence = Confidence.EXTRACTED


@dataclass(frozen=True, slots=True)
class CallsEndpointEdge(Edge):
    """A consumer Symbol (frontend call site) hits an Endpoint contract. Exists
    even when no provider resolves (the honest "endpoint we can't locate").
    ``symbol`` is the caller's qualified_name."""

    symbol: str = ""  # consumer Symbol.qualified_name
    contract_id: str = ""  # Endpoint PK
    confidence: Confidence = Confidence.EXTRACTED


@dataclass(frozen=True, slots=True)
class RoutesToEdge(Edge):
    """The materialized cross-stack edge: consumer Symbol → provider Symbol.
    This is what agents and the visualizer traverse; HANDLES / CALLS_ENDPOINT
    are the audit trail. Confidence is the join confidence (DEC-047)."""

    consumer: str = ""  # consumer Symbol.qualified_name
    provider: str = ""  # provider Symbol.qualified_name
    via: str = "http"  # protocol: http | grpc | topic
    endpoint: str = ""  # the Endpoint contract_id this join is on


# ---------------------------------------------------------------------------
# LadybugDB DDL
# ---------------------------------------------------------------------------
#
# Translation of the dataclasses above into Cypher CREATE NODE TABLE / REL TABLE
# statements. The ``LadybugStore`` runs these on first open. Edits here must
# round-trip with the dataclasses — the test suite asserts that.

NODE_TABLES: list[str] = [
    # File
    (
        "CREATE NODE TABLE IF NOT EXISTS File("
        "path STRING, language STRING, role STRING, sha STRING, "
        "loc INT64, last_modified STRING, "
        "PRIMARY KEY(path))"
    ),
    # Symbol — DEC-051: PK is the stable ``node_id``; ``qualified_name`` stays
    # as the display property (no longer the PK, so overloaded symbols can be
    # distinct nodes sharing a qualified_name).
    (
        "CREATE NODE TABLE IF NOT EXISTS Symbol("
        "node_id STRING, qualified_name STRING, kind STRING, file_path STRING, "
        "line_start INT64, line_end INT64, signature STRING, "
        "PRIMARY KEY(node_id))"
    ),
    # Module
    ("CREATE NODE TABLE IF NOT EXISTS Module(path STRING, language STRING, PRIMARY KEY(path))"),
    # Commit
    (
        "CREATE NODE TABLE IF NOT EXISTS Commit("
        "sha STRING, author_email STRING, date STRING, message STRING, "
        "files_touched_count INT64, "
        "PRIMARY KEY(sha))"
    ),
    # Author
    (
        "CREATE NODE TABLE IF NOT EXISTS Author("
        "email_canonical STRING, name STRING, "
        "PRIMARY KEY(email_canonical))"
    ),
    # Process
    (
        "CREATE NODE TABLE IF NOT EXISTS Process("
        "name STRING, entry_point_symbol STRING, terminal_symbol STRING, "
        "PRIMARY KEY(name))"
    ),
    # Endpoint (DEC-043) — the cross-boundary contract join node.
    (
        "CREATE NODE TABLE IF NOT EXISTS Endpoint("
        "contract_id STRING, protocol STRING, method STRING, "
        "normalized_path STRING, raw_path_samples STRING, framework STRING, "
        "spec_backed BOOLEAN, "
        "PRIMARY KEY(contract_id))"
    ),
]


REL_TABLES: list[str] = [
    (
        "CREATE REL TABLE IF NOT EXISTS CALLS("
        "FROM Symbol TO Symbol, confidence STRING, evidence STRING, via STRING)"
    ),
    (
        "CREATE REL TABLE IF NOT EXISTS IMPORTS("
        "FROM File TO Module, confidence STRING, evidence STRING)"
    ),
    (
        "CREATE REL TABLE IF NOT EXISTS EXTENDS("
        "FROM Symbol TO Symbol, confidence STRING, evidence STRING)"
    ),
    (
        "CREATE REL TABLE IF NOT EXISTS IMPLEMENTS("
        "FROM Symbol TO Symbol, confidence STRING, evidence STRING)"
    ),
    (
        "CREATE REL TABLE IF NOT EXISTS DEFINES("
        "FROM File TO Symbol, confidence STRING, evidence STRING)"
    ),
    (
        "CREATE REL TABLE IF NOT EXISTS MEMBER_OF("
        "FROM Symbol TO Symbol, confidence STRING, evidence STRING)"
    ),
    (
        "CREATE REL TABLE IF NOT EXISTS TOUCHED_BY_COMMIT("
        "FROM File TO Commit, confidence STRING, evidence STRING)"
    ),
    (
        "CREATE REL TABLE IF NOT EXISTS AUTHORED_BY("
        "FROM Commit TO Author, confidence STRING, evidence STRING)"
    ),
    (
        "CREATE REL TABLE IF NOT EXISTS CO_CHANGES_WITH("
        "FROM File TO File, confidence STRING, evidence STRING, "
        "frequency DOUBLE)"
    ),
    # Cross-boundary edges (DEC-043, v0.4).
    (
        "CREATE REL TABLE IF NOT EXISTS HANDLES("
        "FROM Symbol TO Endpoint, confidence STRING, evidence STRING)"
    ),
    (
        "CREATE REL TABLE IF NOT EXISTS CALLS_ENDPOINT("
        "FROM Symbol TO Endpoint, confidence STRING, evidence STRING)"
    ),
    (
        "CREATE REL TABLE IF NOT EXISTS ROUTES_TO("
        "FROM Symbol TO Symbol, confidence STRING, evidence STRING, "
        "via STRING, endpoint STRING)"
    ),
]
