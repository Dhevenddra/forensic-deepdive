"""`forensic serve --ui` bounded graph builder (DEC-053, v0.4 Item K).

The deterministic, unit-testable core: bounded node/edge counts, filter
correctness, ROUTES_TO cross-stack encoding, deterministic serialization, and
the node-detail panel reusing the MCP `context`/`trace` tools. Built on the
`openapi_codegen_sample` fixture (a JS client → FastAPI handler ROUTES_TO plus a
spec-only unlocated endpoint), the same fixture `test_trace.py` uses.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from forensic_deepdive.pipeline import ExtractConfig, PipelineRunner, default_phases
from forensic_deepdive.serve import graph_api

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _build_db(tmp_path: Path, fixture: str) -> Path:
    repo = tmp_path / fixture
    shutil.copytree(FIXTURES / fixture, repo)
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


@pytest.fixture
def cross_stack_db(tmp_path: Path) -> Path:
    return _build_db(tmp_path, "openapi_codegen_sample")


@pytest.fixture
def plain_db(tmp_path: Path) -> Path:
    return _build_db(tmp_path, "python_sample")


# --- bounding (the 348k lesson) --------------------------------------------


def test_bounds_are_respected(cross_stack_db: Path) -> None:
    out = graph_api.build_graph_payload(cross_stack_db, max_nodes=5, max_edges=4)
    assert len(out["nodes"]) <= 5
    assert len(out["edges"]) <= 4
    assert out["meta"]["caps"] == {"max_nodes": 5, "max_edges": 4}


def test_node_and_edge_counts_match_meta(cross_stack_db: Path) -> None:
    out = graph_api.build_graph_payload(cross_stack_db)
    assert out["meta"]["node_count"] == len(out["nodes"])
    assert out["meta"]["edge_count"] == len(out["edges"])


def test_every_node_referenced_by_an_edge_is_present(cross_stack_db: Path) -> None:
    out = graph_api.build_graph_payload(cross_stack_db)
    keys = {n["key"] for n in out["nodes"]}
    for e in out["edges"]:
        assert e["source"] in keys
        assert e["target"] in keys


# --- filters ----------------------------------------------------------------


def test_edge_type_filter(cross_stack_db: Path) -> None:
    out = graph_api.build_graph_payload(cross_stack_db, edge_types=["ROUTES_TO"])
    assert out["edges"], "fixture has at least one ROUTES_TO"
    assert {e["attributes"]["etype"] for e in out["edges"]} == {"ROUTES_TO"}


def test_min_confidence_filter(cross_stack_db: Path) -> None:
    out = graph_api.build_graph_payload(cross_stack_db, min_confidence="EXTRACTED")
    for e in out["edges"]:
        assert e["attributes"]["confidence"] == "EXTRACTED"


def test_unknown_edge_type_falls_back_to_default(cross_stack_db: Path) -> None:
    out = graph_api.build_graph_payload(cross_stack_db, edge_types=["NONSENSE"])
    assert set(out["meta"]["filters"]["edge_types"]) == set(graph_api.DEFAULT_EDGE_TYPES)


def test_language_filter_drops_other_languages(cross_stack_db: Path) -> None:
    out = graph_api.build_graph_payload(cross_stack_db, language="python")
    for n in out["nodes"]:
        if n["attributes"]["ntype"] == "symbol":
            assert n["attributes"]["language"] == "python"


# --- cross-stack encoding (the headline) -----------------------------------


def test_routes_to_is_distinctly_encoded(cross_stack_db: Path) -> None:
    out = graph_api.build_graph_payload(cross_stack_db)
    routes = [e for e in out["edges"] if e["attributes"]["etype"] == "ROUTES_TO"]
    assert routes, "the fixture joins a JS client to a FastAPI handler"
    for e in routes:
        assert e["attributes"]["color"] == graph_api._ROUTES_TO_COLOR
        assert e["attributes"]["size"] > 1.0  # heavier weight than ordinary edges


def test_endpoint_nodes_present_with_default_edges(cross_stack_db: Path) -> None:
    out = graph_api.build_graph_payload(cross_stack_db)
    ntypes = {n["attributes"]["ntype"] for n in out["nodes"]}
    assert "endpoint" in ntypes


# --- determinism ------------------------------------------------------------


def test_serialization_is_deterministic(cross_stack_db: Path) -> None:
    a = graph_api.build_graph_payload(cross_stack_db)
    b = graph_api.build_graph_payload(cross_stack_db)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    keys = [n["key"] for n in a["nodes"]]
    assert keys == sorted(keys)


# --- node detail (reuses context / trace) ----------------------------------


def test_node_detail_symbol_includes_context_and_trace(cross_stack_db: Path) -> None:
    detail = graph_api.build_node_detail(cross_stack_db, "sym:client.js::loadItem")
    assert "context" in detail
    assert detail["trace_downstream"]["chains"], "loadItem routes to a backend handler"


def test_node_detail_endpoint_panel(cross_stack_db: Path) -> None:
    detail = graph_api.build_node_detail(cross_stack_db, "ep:http::GET::/api/items/{param}")
    assert detail["endpoint"]["contract_id"] == "http::GET::/api/items/{param}"
    assert detail["endpoint"]["spec_backed"] is True
    assert any(h["qualified_name"] == "backend.py::get_item" for h in detail["handlers"])


def test_node_detail_unlocated_endpoint(cross_stack_db: Path) -> None:
    detail = graph_api.build_node_detail(cross_stack_db, "ep:http::GET::/api/orphan/{param}")
    assert detail["unlocated"] is True
    assert detail["handlers"] == []


# --- meta -------------------------------------------------------------------


def test_meta_reports_languages_and_edge_counts(cross_stack_db: Path) -> None:
    meta = graph_api.build_meta(cross_stack_db)
    assert "python" in meta["languages"]
    assert meta["edge_type_counts"]["ROUTES_TO"] >= 1
    assert set(meta["edge_types"]) == set(graph_api.ALL_EDGE_TYPES)
    assert meta["endpoint_count"] >= 1


# --- route-free repo: no crash, no routes ----------------------------------


def test_plain_repo_has_no_routes_but_still_builds(plain_db: Path) -> None:
    out = graph_api.build_graph_payload(plain_db)
    assert {e["attributes"]["etype"] for e in out["edges"]} <= set(graph_api.DEFAULT_EDGE_TYPES)
    assert not [e for e in out["edges"] if e["attributes"]["etype"] == "ROUTES_TO"]
