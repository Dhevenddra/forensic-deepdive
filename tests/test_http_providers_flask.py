"""Flask route-provider extractor (DEC-045, v0.4 Item F gap-closer).

Covers Flask's distinct semantics: ``methods=[...]`` verb list, ``<int:id>``
angle params, ``@bp.post`` shortcuts, and Blueprint url_prefix registration.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.http.providers.flask import extract_flask_providers
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import Confidence, LadybugStore
from forensic_deepdive.pipeline import BuildGraphPhase, PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "flask_provider_sample"


def _extract(tmp_path: Path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"app.py": "python"},
        repo_path=repo,
    )
    return {(c.contract_id, c.symbol_id): c for c in extract_flask_providers(ctx)}


def test_app_route_methods_list_expands_to_one_per_verb(tmp_path):
    by = _extract(tmp_path)
    get = by[("http::GET::/users/{param}", "app.py::get_user")]
    post = by[("http::POST::/users/{param}", "app.py::get_user")]
    assert get.confidence is Confidence.EXTRACTED  # app route, literal
    assert post.confidence is Confidence.EXTRACTED
    assert get.framework == "flask"


def test_blueprint_url_prefix_joined_and_shortcut_verb(tmp_path):
    by = _extract(tmp_path)
    # @bp.route("/items") default GET, blueprint url_prefix "/api"
    listed = by[("http::GET::/api/items", "app.py::list_items")]
    assert listed.confidence is Confidence.INFERRED
    # @bp.post("/items") shortcut verb
    created = by[("http::POST::/api/items", "app.py::create_item")]
    assert created.confidence is Confidence.INFERRED


def test_health_noise_filtered_and_exact_set(tmp_path):
    by = _extract(tmp_path)
    assert {cid for cid, _ in by} == {
        "http::GET::/users/{param}",
        "http::POST::/users/{param}",
        "http::GET::/api/items",
        "http::POST::/api/items",
    }


def test_end_to_end_handles_edges(tmp_path):
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
        handles = {
            (row[0], row[1])
            for row in store.query(
                "MATCH (s:Symbol)-[:HANDLES]->(e:Endpoint) RETURN s.qualified_name, e.contract_id"
            )
        }
    assert handles == {
        ("app.py::get_user", "http::GET::/users/{param}"),
        ("app.py::get_user", "http::POST::/users/{param}"),
        ("app.py::list_items", "http::GET::/api/items"),
        ("app.py::create_item", "http::POST::/api/items"),
    }
