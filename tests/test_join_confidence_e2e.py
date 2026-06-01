"""DEC-047 join confidence model — end-to-end in a real .lbug (v0.4 Item H).

Two proofs: (1) the EXTRACTED ROUTES_TO tier — a unique both-literal join is
EXTRACTED, a template-generalized one stays INFERRED; (2) the method-wildcard
fallback — a concrete-verb consumer joins a Spring bare-@RequestMapping (`http::*::`)
provider, INFERRED.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.pipeline import PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig

FIXTURES = Path(__file__).parent / "fixtures"


def _routes(repo_name: str, tmp_path: Path) -> set[tuple[str, str, str, str]]:
    repo = tmp_path / repo_name
    shutil.copytree(FIXTURES / repo_name, repo)
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
    with LadybugStore(db_path) as store:
        return {
            (row[0], row[1], row[2], row[3])
            for row in store.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) "
                "RETURN c.qualified_name, p.qualified_name, r.endpoint, r.confidence"
            )
        }


def test_extracted_vs_inferred_tier(tmp_path):
    routes = _routes("cross_stack_sample", tmp_path)
    assert routes == {
        # template consumer (`/api/users/${id}`) → INFERRED join
        (
            "client.js::loadUser",
            "server.js::getUser",
            "http::GET::/api/users/{param}",
            "INFERRED",
        ),
        # both sides literal + unique → EXTRACTED join
        ("client.js::addUser", "server.js::createUser", "http::POST::/api/users", "EXTRACTED"),
    }


def test_method_wildcard_routes_to(tmp_path):
    routes = _routes("wildcard_route_sample", tmp_path)
    # fetch('/admin/stats') (GET) joins the bare-@RequestMapping (`*`) handler.
    assert routes == {
        (
            "client.js::loadStats",
            "AdminController.java::AdminController.getStats",
            "http::GET::/admin/stats",
            "INFERRED",
        ),
    }
