"""fetch/axios consumer extractor + the first end-to-end ROUTES_TO (DEC-046, Item G).

Unit: fetch default-GET, fetch {method}, axios.<verb>, axios({method,url}),
template normalization, /health noise drop, fully-dynamic URL drop. Keystone:
a JS client paired with an Express provider yields real ROUTES_TO edges.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts import ContractRole
from forensic_deepdive.contracts.http.consumers.fetch_axios import extract_fetch_axios_consumers
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import Confidence, LadybugStore
from forensic_deepdive.pipeline import BuildGraphPhase, PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "cross_stack_sample"


def _consumers(tmp_path: Path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"client.js": "javascript"},
        repo_path=repo,
    )
    return {(c.contract_id, c.symbol_id): c for c in extract_fetch_axios_consumers(ctx)}


def test_fetch_template_normalized_inferred(tmp_path):
    by = _consumers(tmp_path)
    c = by[("http::GET::/api/users/{param}", "client.js::loadUser")]
    assert c.role is ContractRole.CONSUMER
    assert c.confidence is Confidence.INFERRED  # template ${id} → {param}
    assert c.method == "GET"


def test_axios_verb_literal_extracted(tmp_path):
    by = _consumers(tmp_path)
    c = by[("http::POST::/api/users", "client.js::addUser")]
    assert c.confidence is Confidence.EXTRACTED  # literal URL


def test_fetch_method_option_and_axios_object(tmp_path):
    by = _consumers(tmp_path)
    assert ("http::GET::/api/users", "client.js::listUsers") in by  # fetch {method:'GET'}
    rm = by[("http::DELETE::/api/users/{param}", "client.js::removeUser")]
    assert rm.method == "DELETE"  # axios({method:'delete', url:`...${id}`})


def test_health_and_dynamic_url_dropped(tmp_path):
    by = _consumers(tmp_path)
    cids = {cid for cid, _ in by}
    assert "http::GET::/health" not in cids  # noise
    # the fully-dynamic fetch(u) produced nothing
    assert all(sym != "client.js::dynamic" for _, sym in by)
    assert cids == {
        "http::GET::/api/users/{param}",
        "http::POST::/api/users",
        "http::GET::/api/users",
        "http::DELETE::/api/users/{param}",
    }


def test_end_to_end_routes_to_edges(tmp_path):
    """The keystone: the JS client joins the Express provider → real ROUTES_TO."""
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
        routes = {
            (row[0], row[1], row[2])
            for row in store.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) "
                "RETURN c.qualified_name, p.qualified_name, r.endpoint"
            )
        }
    # loadUser→getUser (GET /api/users/{param}) and addUser→createUser (POST /api/users).
    # listUsers/removeUser have no provider → CALLS_ENDPOINT only, no ROUTES_TO.
    assert routes == {
        ("client.js::loadUser", "server.js::getUser", "http::GET::/api/users/{param}"),
        ("client.js::addUser", "server.js::createUser", "http::POST::/api/users"),
    }
