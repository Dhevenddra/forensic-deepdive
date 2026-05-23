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


class FileRole(StrEnum):
    """DEC-012 + DEC-021 (planned). v0.1 has source/test/fixture; v0.2 adds
    vendored/generated. Carried here so the schema is the source of truth."""

    SOURCE = "source"
    TEST = "test"
    FIXTURE = "fixture"
    VENDORED = "vendored"
    GENERATED = "generated"


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
    qualified_name: str  # e.g. "src/foo/bar.py::Baz.qux" (PRIMARY KEY)
    kind: SymbolKind
    file_path: str  # FK to File.path
    line_start: int
    line_end: int
    signature: str = ""  # rendered declaration, optional


@dataclass(frozen=True, slots=True)
class Module(Node):
    path: str  # PRIMARY KEY
    language: str


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
    # Symbol
    (
        "CREATE NODE TABLE IF NOT EXISTS Symbol("
        "qualified_name STRING, kind STRING, file_path STRING, "
        "line_start INT64, line_end INT64, signature STRING, "
        "PRIMARY KEY(qualified_name))"
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
]


REL_TABLES: list[str] = [
    (
        "CREATE REL TABLE IF NOT EXISTS CALLS("
        "FROM Symbol TO Symbol, confidence STRING, evidence STRING)"
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
]
