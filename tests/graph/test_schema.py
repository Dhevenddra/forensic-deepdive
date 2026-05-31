"""Schema-level tests for ``forensic_deepdive.graph.schema``.

DEC-013 / DEC-015. The schema is the contract between the static-analysis
phase, the LadybugStore, and (eventually) the MCP server — drift between
the dataclasses and the LadybugDB DDL is a load-bearing bug, so we assert
it directly.
"""

from __future__ import annotations

import re

from forensic_deepdive.graph.schema import (
    NODE_TABLES,
    REL_TABLES,
    Author,
    AuthoredByEdge,
    CallsEdge,
    CoChangesWithEdge,
    Commit,
    Confidence,
    DefinesEdge,
    File,
    FileRole,
    ImportsEdge,
    MemberOfEdge,
    Module,
    Process,
    Symbol,
    SymbolKind,
    TouchedByCommitEdge,
)


def test_confidence_enum_values():
    assert Confidence.EXTRACTED == "EXTRACTED"
    assert Confidence.INFERRED == "INFERRED"
    assert Confidence.AMBIGUOUS == "AMBIGUOUS"
    assert {c.value for c in Confidence} == {"EXTRACTED", "INFERRED", "AMBIGUOUS"}


def test_default_confidence_is_extracted():
    # PRD §4.4: edges default to EXTRACTED; DEFINES/MEMBER_OF/TOUCHED_BY_COMMIT/
    # AUTHORED_BY are ALWAYS EXTRACTED; CO_CHANGES_WITH is INFERRED by default.
    assert CallsEdge().confidence == Confidence.EXTRACTED
    assert ImportsEdge().confidence == Confidence.EXTRACTED
    assert DefinesEdge().confidence == Confidence.EXTRACTED
    assert MemberOfEdge().confidence == Confidence.EXTRACTED
    assert TouchedByCommitEdge().confidence == Confidence.EXTRACTED
    assert AuthoredByEdge().confidence == Confidence.EXTRACTED
    assert CoChangesWithEdge().confidence == Confidence.INFERRED


def test_nodes_are_hashable_and_frozen():
    # frozen=True means dataclasses can live in sets / dict keys.
    f = File(
        path="a.py",
        language="python",
        role=FileRole.SOURCE,
        sha="abc",
        loc=10,
        last_modified="2026-05-24T00:00:00Z",
    )
    assert {f, f} == {f}
    s = Symbol(
        qualified_name="a.py::foo",
        kind=SymbolKind.FUNCTION,
        file_path="a.py",
        line_start=1,
        line_end=5,
    )
    assert hash(s) == hash(s)


def test_all_node_dataclasses_constructable():
    # Smoke: every node type accepts its declared fields.
    Author(email_canonical="x@y", name="X")
    Commit(
        sha="deadbeef",
        author_email="x@y",
        date="2026-05-24T00:00:00Z",
        message="msg",
        files_touched_count=3,
    )
    Module(path="pkg.mod", language="python")
    Process(name="boot", entry_point_symbol="a.py::main")


def test_ddl_covers_every_node_dataclass():
    # If a Node type is added to schema.py, NODE_TABLES must grow too.
    declared_tables = {_node_name(stmt) for stmt in NODE_TABLES}
    expected = {"File", "Symbol", "Module", "Commit", "Author", "Process", "Endpoint"}
    assert declared_tables == expected


def test_ddl_covers_every_edge_dataclass():
    declared_rels = {_rel_name(stmt) for stmt in REL_TABLES}
    expected = {
        "CALLS",
        "IMPORTS",
        "EXTENDS",
        "IMPLEMENTS",
        "DEFINES",
        "MEMBER_OF",
        "TOUCHED_BY_COMMIT",
        "AUTHORED_BY",
        "CO_CHANGES_WITH",
        "HANDLES",  # DEC-043
        "CALLS_ENDPOINT",  # DEC-043
        "ROUTES_TO",  # DEC-043
    }
    assert declared_rels == expected


def test_every_rel_table_carries_confidence_and_evidence():
    # DEC-015: every edge has confidence + evidence columns in the DDL.
    for stmt in REL_TABLES:
        assert "confidence STRING" in stmt, stmt
        assert "evidence STRING" in stmt, stmt


def test_ddl_uses_if_not_exists_for_idempotent_connect():
    # LadybugStore.connect() runs every DDL; if it weren't idempotent,
    # reconnecting to an existing DB would crash.
    for stmt in (*NODE_TABLES, *REL_TABLES):
        assert "IF NOT EXISTS" in stmt, stmt


# helpers ------------------------------------------------------------------


_NODE_RE = re.compile(r"CREATE NODE TABLE IF NOT EXISTS (\w+)")
_REL_RE = re.compile(r"CREATE REL TABLE IF NOT EXISTS (\w+)")


def _node_name(stmt: str) -> str:
    m = _NODE_RE.search(stmt)
    assert m, stmt
    return m.group(1)


def _rel_name(stmt: str) -> str:
    m = _REL_RE.search(stmt)
    assert m, stmt
    return m.group(1)
