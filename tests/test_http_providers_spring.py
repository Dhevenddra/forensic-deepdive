"""Spring MVC route-provider extractor (DEC-045, v0.4 Item F — Java).

Covers class ``@RequestMapping`` prefix joining, ``@GetMapping``/``@PostMapping``
shortcuts, ``@RequestMapping(method=RequestMethod.GET)``, and the no-prefix +
noise case (a bare ``/health`` controller).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.http.providers.spring import extract_spring_providers
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import Confidence, LadybugStore
from forensic_deepdive.pipeline import BuildGraphPhase, PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "spring_provider_sample"


def _extract(tmp_path: Path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={
            "UserController.java": "java",
            "HealthController.java": "java",
        },
        repo_path=repo,
    )
    return {(c.contract_id, c.symbol_id): c for c in extract_spring_providers(ctx)}


def test_class_prefix_joined_and_extracted(tmp_path):
    by = _extract(tmp_path)
    get = by[("http::GET::/api/users/{param}", "UserController.java::UserController.getUser")]
    assert get.confidence is Confidence.EXTRACTED  # class prefix + method path both literal
    assert get.framework == "spring"
    # bare @PostMapping → class prefix root
    post = by[("http::POST::/api/users", "UserController.java::UserController.create")]
    assert post.confidence is Confidence.EXTRACTED


def test_request_mapping_method_attr(tmp_path):
    by = _extract(tmp_path)
    search = by[("http::GET::/api/users/search", "UserController.java::UserController.search")]
    assert search.method == "GET"


def test_no_prefix_health_is_noise_filtered_exact_set(tmp_path):
    by = _extract(tmp_path)
    assert {cid for cid, _ in by} == {
        "http::GET::/api/users/{param}",
        "http::POST::/api/users",
        "http::GET::/api/users/search",
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
        ("UserController.java::UserController.getUser", "http::GET::/api/users/{param}"),
        ("UserController.java::UserController.create", "http::POST::/api/users"),
        ("UserController.java::UserController.search", "http::GET::/api/users/search"),
    }
