"""Express route-provider extractor (DEC-045, v0.4 Item F).

Covers Express's method-call routes, app.use mount prefixes, named vs inline
handler attribution (inline → the file's <module> symbol), and confidence.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.http.providers.express import extract_express_providers
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import Confidence, LadybugStore
from forensic_deepdive.pipeline import BuildGraphPhase, PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "express_provider_sample"


def _extract(tmp_path: Path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"server.js": "javascript"},
        repo_path=repo,
    )
    return {(c.contract_id, c.symbol_id): c for c in extract_express_providers(ctx)}


def test_app_route_named_and_inline_handlers(tmp_path):
    by = _extract(tmp_path)
    # inline arrow handler → attributed to the <module> symbol, EXTRACTED
    inline = by[("http::GET::/users/{param}", "server.js::<module>")]
    assert inline.confidence is Confidence.EXTRACTED
    assert inline.framework == "express"
    # named handler → its own symbol
    named = by[("http::POST::/users", "server.js::createUser")]
    assert named.confidence is Confidence.EXTRACTED


def test_router_use_mount_prefix_joined(tmp_path):
    by = _extract(tmp_path)
    listed = by[("http::GET::/api/items", "server.js::listItems")]
    assert listed.confidence is Confidence.INFERRED  # mount prefix via app.use, by name
    removed = by[("http::DELETE::/api/items/{param}", "server.js::removeItem")]
    assert removed.confidence is Confidence.INFERRED


def test_health_noise_filtered_exact_set(tmp_path):
    by = _extract(tmp_path)
    assert {cid for cid, _ in by} == {
        "http::GET::/users/{param}",
        "http::POST::/users",
        "http::GET::/api/items",
        "http::DELETE::/api/items/{param}",
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
        ("server.js::<module>", "http::GET::/users/{param}"),
        ("server.js::createUser", "http::POST::/users"),
        ("server.js::listItems", "http::GET::/api/items"),
        ("server.js::removeItem", "http::DELETE::/api/items/{param}"),
    }
