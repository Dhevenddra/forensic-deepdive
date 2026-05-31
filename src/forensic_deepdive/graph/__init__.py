"""v0.2 persistent code knowledge graph.

PRD_v0.2 §4.2 / DEC-013. The public surface is `GraphStore` (ABC), `LadybugStore`
(the v0.2 backend), and the schema types in `schema`. Call sites must not import
`real_ladybug` directly — go through `LadybugStore`.
"""

from forensic_deepdive.graph.ladybug_store import LadybugStore
from forensic_deepdive.graph.schema import (
    NODE_TABLES,
    REL_TABLES,
    Author,
    AuthoredByEdge,
    CallsEdge,
    CallsEndpointEdge,
    CoChangesWithEdge,
    Commit,
    Confidence,
    DefinesEdge,
    Edge,
    Endpoint,
    ExtendsEdge,
    File,
    HandlesEdge,
    ImplementsEdge,
    ImportsEdge,
    MemberOfEdge,
    Module,
    Node,
    Process,
    RoutesToEdge,
    Symbol,
    SymbolKind,
    TouchedByCommitEdge,
    module_pk,
)
from forensic_deepdive.graph.store import GraphStore

__all__ = [
    "NODE_TABLES",
    "REL_TABLES",
    "Author",
    "AuthoredByEdge",
    "CallsEdge",
    "CallsEndpointEdge",
    "CoChangesWithEdge",
    "Commit",
    "Confidence",
    "DefinesEdge",
    "Edge",
    "Endpoint",
    "ExtendsEdge",
    "File",
    "GraphStore",
    "HandlesEdge",
    "ImplementsEdge",
    "ImportsEdge",
    "LadybugStore",
    "MemberOfEdge",
    "Module",
    "Node",
    "Process",
    "RoutesToEdge",
    "Symbol",
    "SymbolKind",
    "TouchedByCommitEdge",
    "module_pk",
]
