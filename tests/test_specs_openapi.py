"""OpenAPI codegen shortcut — detection, parsing, reconciliation, end-to-end
(DEC-048, v0.4 Item I — the differentiator).

The headline proof is :func:`test_spec_upgrades_routes_to_extracted`: a template
consumer joins an in-code handler at INFERRED on its own, but the committed
``openapi.json`` upgrades the ROUTES_TO to EXTRACTED (``spec_backed``). The
spec-only ``/api/orphan`` op shows the documented-but-unlocated posture: an
EXTRACTED CALLS_ENDPOINT, no HANDLES, no ROUTES_TO.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.specs import (
    collect_spec_operations,
    detect_spec_files,
    reconcile_with_specs,
)
from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.pipeline import PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig

FIXTURES = Path(__file__).parent / "fixtures"
_FIXTURE = "openapi_codegen_sample"
_YAML_AVAILABLE = importlib.util.find_spec("yaml") is not None


# --------------------------------------------------------------------------- #
# Detection + parsing                                                         #
# --------------------------------------------------------------------------- #


def test_detect_finds_committed_json_spec():
    found = detect_spec_files(FIXTURES / _FIXTURE)
    assert [p.name for p in found] == ["openapi.json"]


def test_detect_is_sorted_and_prunes_ignored_dirs(tmp_path):
    (tmp_path / "openapi.json").write_text("{}", encoding="utf-8")
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "service.openapi.json").write_text("{}", encoding="utf-8")
    # node_modules is an ignore-dir — a spec inside must NOT be picked up.
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "swagger.json").write_text("{}", encoding="utf-8")
    rel = [p.relative_to(tmp_path).as_posix() for p in detect_spec_files(tmp_path)]
    assert rel == ["api/service.openapi.json", "openapi.json"]


def test_parse_json_paths_methods_operation_ids():
    scan = collect_spec_operations(FIXTURES / _FIXTURE)
    assert scan.skipped_yaml == []
    assert {(o.method, o.raw_path, o.operation_id, o.source) for o in scan.operations} == {
        ("GET", "/api/items/{item_id}", "getItem", "openapi.json"),
        ("GET", "/api/orphan/{orphan_id}", "getOrphan", "openapi.json"),
    }


def test_swagger2_base_path_prefixed(tmp_path):
    (tmp_path / "swagger.json").write_text(
        json.dumps({"basePath": "/v2", "paths": {"/pets": {"get": {"operationId": "listPets"}}}}),
        encoding="utf-8",
    )
    scan = collect_spec_operations(tmp_path)
    assert [(o.method, o.raw_path) for o in scan.operations] == [("GET", "/v2/pets")]


def test_noise_health_path_filtered_from_providers(tmp_path):
    (tmp_path / "openapi.json").write_text(
        json.dumps({"paths": {"/health": {"get": {}}, "/api/x": {"get": {}}}}),
        encoding="utf-8",
    )
    scan = collect_spec_operations(tmp_path)
    providers = reconcile_with_specs([], scan.operations)
    ids = {p.contract_id for p in providers}
    assert "http::GET::/api/x" in ids
    assert not any("health" in cid for cid in ids)


def test_malformed_json_skipped_silently(tmp_path):
    (tmp_path / "openapi.json").write_text("{ not valid json", encoding="utf-8")
    scan = collect_spec_operations(tmp_path)
    assert scan.operations == []
    assert scan.skipped_yaml == []


def test_yaml_loud_degradation_or_parse(tmp_path):
    """A YAML spec without the [openapi] extra is skipped LOUDLY (recorded, never
    silent); with the extra it parses. Asserted against the live env."""
    (tmp_path / "openapi.yaml").write_text(
        "paths:\n  /api/y:\n    get:\n      operationId: getY\n", encoding="utf-8"
    )
    scan = collect_spec_operations(tmp_path)
    if _YAML_AVAILABLE:
        assert scan.skipped_yaml == []
        assert [(o.method, o.raw_path) for o in scan.operations] == [("GET", "/api/y")]
    else:
        assert scan.skipped_yaml == ["openapi.yaml"]
        assert scan.operations == []


# --------------------------------------------------------------------------- #
# Reconciliation                                                              #
# --------------------------------------------------------------------------- #


def _in_code_provider(contract_id: str, *, spec_backed: bool = False) -> Contract:
    return Contract(
        role=ContractRole.PROVIDER,
        contract_id=contract_id,
        symbol_id="app.py::handler",
        confidence=Confidence.EXTRACTED,
        method="GET",
        normalized_path="/api/items/{param}",
        spec_backed=spec_backed,
        rel_path="app.py",
    )


def test_reconcile_marks_matching_in_code_provider_spec_backed():
    op_scan = collect_spec_operations(FIXTURES / _FIXTURE)
    provider = _in_code_provider("http::GET::/api/items/{param}")
    out = reconcile_with_specs([provider], op_scan.operations)
    items = [c for c in out if c.contract_id == "http::GET::/api/items/{param}"]
    # the in-code handler is upgraded (not duplicated) and the spec op didn't add
    # a second provider for the same contract_id.
    assert len(items) == 1
    assert items[0].symbol_id == "app.py::handler" and items[0].spec_backed is True


def test_reconcile_emits_spec_only_provider_for_unmatched_op():
    op_scan = collect_spec_operations(FIXTURES / _FIXTURE)
    out = reconcile_with_specs([], op_scan.operations)
    orphan = next(c for c in out if c.contract_id == "http::GET::/api/orphan/{param}")
    assert orphan.spec_backed is True
    assert orphan.confidence is Confidence.EXTRACTED
    assert orphan.framework == "openapi"
    # synthetic symbol_id (operationId) — not a real graph symbol → HANDLES filtered.
    assert orphan.symbol_id == "openapi.json::getOrphan"


def test_reconcile_no_specs_is_identity():
    provider = _in_code_provider("http::GET::/api/items/{param}")
    assert reconcile_with_specs([provider], []) == [provider]


def test_reconcile_already_spec_backed_unchanged():
    provider = _in_code_provider("http::GET::/api/items/{param}", spec_backed=True)
    op_scan = collect_spec_operations(FIXTURES / _FIXTURE)
    out = reconcile_with_specs([provider], op_scan.operations)
    assert provider in out  # frozen dataclass identity-by-value, not rebuilt


def test_collect_is_deterministic():
    a = collect_spec_operations(FIXTURES / _FIXTURE).operations
    b = collect_spec_operations(FIXTURES / _FIXTURE).operations
    assert a == b


# --------------------------------------------------------------------------- #
# End-to-end (.lbug)                                                          #
# --------------------------------------------------------------------------- #


def _extract(tmp_path: Path) -> LadybugStore:
    repo = tmp_path / _FIXTURE
    shutil.copytree(FIXTURES / _FIXTURE, repo)
    db_path = tmp_path / "graph.lbug"
    cfg = ExtractConfig(
        repo_path=repo,
        output_dir=tmp_path / "out",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    PipelineRunner(default_phases()).run(cfg)
    return LadybugStore(db_path)


def test_spec_upgrades_routes_to_extracted(tmp_path):
    """The mandated proof: a template consumer (`/api/items/${id}`, INFERRED on its
    own) joins the in-code FastAPI handler at **EXTRACTED** because openapi.json
    marks the provider spec_backed (DEC-047 tier, flipped by DEC-048)."""
    with _extract(tmp_path) as store:
        routes = {
            (r[0], r[1], r[2], r[3])
            for r in store.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) "
                "RETURN c.qualified_name, p.qualified_name, r.endpoint, r.confidence"
            )
        }
        endpoints = {
            (r[0], r[1])
            for r in store.query("MATCH (e:Endpoint) RETURN e.contract_id, e.spec_backed")
        }
    assert routes == {
        (
            "client.js::loadItem",
            "backend.py::get_item",
            "http::GET::/api/items/{param}",
            "EXTRACTED",
        ),
    }
    assert ("http::GET::/api/items/{param}", True) in endpoints


def test_spec_only_endpoint_calls_endpoint_no_handler(tmp_path):
    """A consumer hitting the spec-only `/api/orphan` op gets an EXTRACTED
    CALLS_ENDPOINT (spec is provider truth) — but NO HANDLES (no located handler)
    and NO ROUTES_TO (no provider symbol to target)."""
    with _extract(tmp_path) as store:
        calls = {
            (r[0], r[1], r[2])
            for r in store.query(
                "MATCH (c:Symbol)-[r:CALLS_ENDPOINT]->(e:Endpoint) "
                "RETURN c.qualified_name, e.contract_id, r.confidence"
            )
        }
        orphan_handles = list(
            store.query(
                "MATCH (p:Symbol)-[:HANDLES]->"
                "(e:Endpoint {contract_id: 'http::GET::/api/orphan/{param}'}) "
                "RETURN p.qualified_name"
            )
        )
        orphan_routes = list(
            store.query(
                "MATCH (:Symbol)-[r:ROUTES_TO]->(:Symbol) "
                "WHERE r.endpoint = 'http::GET::/api/orphan/{param}' RETURN r.endpoint"
            )
        )
    assert (
        "client.js::loadOrphan",
        "http::GET::/api/orphan/{param}",
        "EXTRACTED",
    ) in calls
    assert orphan_handles == []
    assert orphan_routes == []
