"""DEC-056 end-to-end — the v0.4 Superset flagship gap closed (v0.5 Step 1).

A configured-client frontend (``SupersetClient.get/post/request({ endpoint })``)
joins a Flask-AppBuilder backend (``ModelRestApi``/``BaseApi`` + ``@expose``) on a
shared ``contract_id`` → a materialized ``ROUTES_TO`` graph, with the honest
EXTRACTED/INFERRED split and no fabricated joins. This is the 8/9 → 9/9 proof
(the join machinery is unchanged — only two new extractors).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.pipeline import PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "superset_flagship_sample"


def _run(tmp_path: Path):
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
    PipelineRunner(default_phases()).run(cfg)
    return db_path


def _routes(db_path: Path) -> set[tuple[str, str, str, str]]:
    with LadybugStore(db_path) as store:
        return {
            (row[0], row[1], row[2], row[3])
            for row in store.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) "
                "RETURN c.qualified_name, p.qualified_name, r.endpoint, r.confidence"
            )
        }


def test_flagship_routes_to_materializes(tmp_path):
    routes = _routes(_run(tmp_path))
    assert routes == {
        # templated client endpoint → INFERRED join
        (
            "chart.ts::fetchChartData",
            "api.py::ChartRestApi.data",
            "http::GET::/api/v1/chart/{param}/data",
            "INFERRED",
        ),
        # literal both-sides + unique → EXTRACTED join
        (
            "chart.ts::createChart",
            "api.py::ChartRestApi.bulk_create",
            "http::POST::/api/v1/chart",
            "EXTRACTED",
        ),
        # .request({ method, endpoint }) literal → EXTRACTED join
        (
            "chart.ts::exportDashboard",
            "api.py::DashboardRestApi.export",
            "http::GET::/api/v1/dashboard/export",
            "EXTRACTED",
        ),
    }


def test_unmatched_provider_has_no_route(tmp_path):
    # LogRestApi.recent is a located handler with no consumer → HANDLES, no ROUTES_TO
    # (the honest unmatched-provider posture, DEC-043).
    routes = _routes(_run(tmp_path))
    assert not any(p == "api.py::LogRestApi.recent" for _, p, _, _ in routes)
