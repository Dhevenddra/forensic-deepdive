"""`trace` 9th MCP tool — cross-stack feature-slice traversal (DEC-052, v0.4 Item J).

Walks the `Endpoint` join node the CALLS-only tools can't reach: downstream
(frontend → endpoint → handler → CALLS tail) and upstream (handler → endpoint →
who-calls). Built on the `openapi_codegen_sample` fixture, which pairs a JS client
with a FastAPI handler plus a spec-only (unlocated) endpoint.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from forensic_deepdive.mcp_server import server as srv
from forensic_deepdive.pipeline import ExtractConfig, PipelineRunner, default_phases

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def cross_stack_db(tmp_path: Path) -> Path:
    """Build a real .lbug from openapi_codegen_sample (ROUTES_TO + a spec-only
    unlocated endpoint)."""
    repo = tmp_path / "openapi_codegen_sample"
    shutil.copytree(FIXTURES / "openapi_codegen_sample", repo)
    db_path = tmp_path / "graph.lbug"
    cfg = ExtractConfig(
        repo_path=repo.resolve(),
        output_dir=repo / "out",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    PipelineRunner(default_phases()).run(cfg)
    return db_path


def test_trace_self_notes_inapplicability_on_non_web_repo(tmp_path: Path) -> None:
    """DEC-091 (DEFERRED 7d): on a repo with no Endpoints, trace self-notes it is
    inapplicable instead of returning a bare empty result."""
    repo = tmp_path / "python_sample"
    shutil.copytree(FIXTURES / "python_sample", repo)
    db_path = tmp_path / "graph.lbug"
    PipelineRunner(default_phases()).run(
        ExtractConfig(
            repo_path=repo.resolve(),
            output_dir=repo / "out",
            flatten=False,
            write_editor_shims=False,
            build_graph_db=True,
            graph_db_path=db_path,
        )
    )
    out = srv.trace(db_path, "format_message", direction="downstream")
    assert out.get("applicable") is False
    assert "No HTTP/MCP/gRPC/messaging endpoints" in out.get("note", "")


def test_trace_applicable_note_absent_on_cross_stack_repo(cross_stack_db: Path) -> None:
    """The self-note appears only when there are no endpoints — a cross-stack repo
    has them, so no inapplicability note is added."""
    out = srv.trace(cross_stack_db, "loadItem", direction="downstream")
    assert "applicable" not in out


def test_trace_downstream_component_to_handler(cross_stack_db: Path) -> None:
    """downstream from the frontend caller walks CALLS_ENDPOINT → Endpoint →
    HANDLES → handler."""
    out = srv.trace(cross_stack_db, "loadItem", direction="downstream")
    assert out["matches"], "loadItem should resolve"
    assert out["direction"] == "downstream"
    chain = next(c for c in out["chains"] if c["endpoint"] == "http::GET::/api/items/{param}")
    assert chain["consumer"] == "client.js::loadItem"
    assert chain["handler"] == "backend.py::get_item"
    assert chain["spec_backed"] is True
    assert chain["handles_confidence"] == "EXTRACTED"
    assert "service→repository→table" in out["boundary"]  # honest v0.5 boundary


def test_trace_downstream_unlocated_endpoint_surfaced(cross_stack_db: Path) -> None:
    """A spec-only endpoint (no located handler) is surfaced honestly, not
    dropped — handler=None, unlocated=True (the DEC-043 posture)."""
    out = srv.trace(cross_stack_db, "loadOrphan", direction="downstream")
    chain = next(c for c in out["chains"] if c["endpoint"] == "http::GET::/api/orphan/{param}")
    assert chain["handler"] is None
    assert chain["unlocated"] is True
    assert chain["downstream"] == []


def test_trace_upstream_who_calls_endpoint(cross_stack_db: Path) -> None:
    """upstream from a handler answers 'who calls this endpoint'."""
    out = srv.trace(cross_stack_db, "backend.py::get_item", direction="upstream")
    assert out["direction"] == "upstream"
    chain = next(c for c in out["chains"] if c["endpoint"] == "http::GET::/api/items/{param}")
    callers = {c["consumer"] for c in chain["callers"]}
    assert "client.js::loadItem" in callers


def test_trace_unresolved_symbol(cross_stack_db: Path) -> None:
    out = srv.trace(cross_stack_db, "no_such_symbol_xyz")
    assert out["matches"] == []
    assert out["chains"] == []
    assert out["unresolved"] is True


def test_trace_rejects_bad_direction(cross_stack_db: Path) -> None:
    out = srv.trace(cross_stack_db, "loadItem", direction="sideways")
    assert "error" in out


def test_trace_is_deterministic(cross_stack_db: Path) -> None:
    a = srv.trace(cross_stack_db, "loadItem", direction="downstream")
    b = srv.trace(cross_stack_db, "loadItem", direction="downstream")
    assert a == b
