"""FastAPI route-provider extractor (DEC-045, v0.4 Item F).

Unit-level: the extractor over the fixture (contractId, prefix joining, noise
filter, confidence, handler symbol_id). End-to-end: HANDLES edges + Endpoint
nodes land in a real .lbug with the handler symbols resolved.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts import ContractRole
from forensic_deepdive.contracts.http.providers.fastapi import extract_fastapi_providers
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import Confidence, LadybugStore
from forensic_deepdive.pipeline import BuildGraphPhase, PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "fastapi_provider_sample"


def _ctx(repo: Path) -> ContractContext:
    return ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"main.py": "python", "items.py": "python"},
        repo_path=repo,
    )


def _extract(tmp_path: Path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    contracts = extract_fastapi_providers(_ctx(repo))
    return {c.contract_id: c for c in contracts}


def test_app_route_literal_is_extracted(tmp_path):
    by_id = _extract(tmp_path)
    c = by_id["http::GET::/users/{param}"]
    assert c.role is ContractRole.PROVIDER
    assert c.confidence is Confidence.EXTRACTED  # app route, literal path
    assert c.symbol_id == "main.py::read_user"
    assert c.method == "GET"
    assert c.framework == "fastapi"
    assert c.raw_path == "/users/{user_id}"


def test_router_prefix_and_include_router_mount_joined(tmp_path):
    by_id = _extract(tmp_path)
    # /api (include_router mount) + /items (APIRouter prefix) + / (decorator)
    post = by_id["http::POST::/api/items"]
    assert post.symbol_id == "items.py::create_item"
    assert post.confidence is Confidence.INFERRED  # cross-file mount heuristic
    # ...and the param route the same way
    get = by_id["http::GET::/api/items/{param}"]
    assert get.symbol_id == "items.py::get_item"
    assert get.confidence is Confidence.INFERRED


def test_health_path_is_noise_filtered(tmp_path):
    by_id = _extract(tmp_path)
    assert "http::GET::/health" not in by_id
    # exactly the three real routes survive
    assert set(by_id) == {
        "http::GET::/users/{param}",
        "http::POST::/api/items",
        "http::GET::/api/items/{param}",
    }


def test_no_routes_when_no_fastapi_markers(tmp_path):
    """A repo with no FastAPI markers yields nothing — the pre-filter holds."""
    repo = tmp_path / "plain"
    repo.mkdir()
    (repo / "x.py").write_text("def f():\n    return 1\n")
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"x.py": "python"},
        repo_path=repo,
    )
    assert extract_fastapi_providers(ctx) == []


def test_determinism(tmp_path):
    a = _extract(tmp_path / "a")
    b = _extract(tmp_path / "b")
    assert sorted(a) == sorted(b)


def test_end_to_end_handles_edges_and_endpoints(tmp_path):
    """The full pipeline persists Endpoint nodes + HANDLES edges to the handler
    symbols (proves symbol_id matches the graph's qualified_name convention)."""
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    db_path = tmp_path / "graph.lbug"
    cfg = ExtractConfig(
        repo_path=repo,
        output_dir=tmp_path / "out",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    ctx = PipelineRunner(default_phases()).run(cfg)
    assert ctx.get(BuildGraphPhase).enabled is True

    with LadybugStore(db_path) as store:
        endpoints = {row[0] for row in store.query("MATCH (e:Endpoint) RETURN e.contract_id")}
        assert endpoints == {
            "http::GET::/users/{param}",
            "http::POST::/api/items",
            "http::GET::/api/items/{param}",
        }
        handles = {
            (row[0], row[1])
            for row in store.query(
                "MATCH (s:Symbol)-[:HANDLES]->(e:Endpoint) RETURN s.qualified_name, e.contract_id"
            )
        }
        assert handles == {
            ("main.py::read_user", "http::GET::/users/{param}"),
            ("items.py::create_item", "http::POST::/api/items"),
            ("items.py::get_item", "http::GET::/api/items/{param}"),
        }
