"""Framework-breadth providers (DEC-062, v0.5 Step 6) — NestJS + JAX-RS.

Pure additions to ``contracts/http/providers/`` (the coverage track): a NestJS
``@Controller`` + verb decorators and a JAX-RS ``@Path`` resource + verb annotations
become HTTP providers that join existing fetch consumers via ROUTES_TO.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.http.providers.jaxrs import extract_jaxrs_providers
from forensic_deepdive.contracts.http.providers.nestjs import extract_nestjs_providers
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.pipeline import PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "framework_breadth_sample"
_LANGS = {
    "cats.controller.ts": "typescript",
    "OwnerResource.java": "java",
    "client.ts": "typescript",
}


def _ctx(tmp_path: Path) -> ContractContext:
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    return ContractContext(
        tags=[], imports=[], method_calls=[], source_files_by_path=dict(_LANGS), repo_path=repo
    )


def test_nestjs_controller_routes(tmp_path):
    provs = {(c.contract_id, c.symbol_id) for c in extract_nestjs_providers(_ctx(tmp_path))}
    assert ("http::GET::/cats/{param}", "cats.controller.ts::CatsController.findOne") in provs
    assert ("http::POST::/cats", "cats.controller.ts::CatsController.create") in provs


def test_nestjs_enclosing_controller_guard(tmp_path):
    # A verb decorator outside a @Controller class is not a route.
    repo = tmp_path / "x"
    repo.mkdir()
    (repo / "svc.ts").write_text("export class Svc {\n  @Get('x')\n  f() {}\n}\n")
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"svc.ts": "typescript"},
        repo_path=repo,
    )
    assert extract_nestjs_providers(ctx) == []


def test_jaxrs_resource_routes(tmp_path):
    provs = {(c.contract_id, c.symbol_id) for c in extract_jaxrs_providers(_ctx(tmp_path))}
    assert ("http::GET::/owners", "OwnerResource.java::OwnerResource.list") in provs
    assert ("http::GET::/owners/{param}", "OwnerResource.java::OwnerResource.get") in provs
    assert ("http::POST::/owners", "OwnerResource.java::OwnerResource.create") in provs


def test_jaxrs_requires_class_path_guard(tmp_path):
    repo = tmp_path / "y"
    repo.mkdir()
    (repo / "Plain.java").write_text("public class Plain {\n  @GET\n  public void f() {}\n}\n")
    ctx = ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"Plain.java": "java"},
        repo_path=repo,
    )
    assert extract_jaxrs_providers(ctx) == []


def test_routes_to_joins_breadth_frameworks(tmp_path):
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    db_path = tmp_path / "graph.lbug"
    PipelineRunner(default_phases()).run(
        ExtractConfig(
            repo_path=repo,
            output_dir=tmp_path / "out",
            flatten=False,
            write_editor_shims=False,
            build_graph_db=True,
            graph_db_path=db_path,
        )
    )
    with LadybugStore(db_path) as s:
        routes = {
            (r[0], r[1], r[2])
            for r in s.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) "
                "RETURN c.qualified_name, p.qualified_name, r.endpoint"
            )
        }
    # NestJS: templated GET /cats/${id} consumer → findOne.
    assert (
        "client.ts::loadCat",
        "cats.controller.ts::CatsController.findOne",
        "http::GET::/cats/{param}",
    ) in routes
    # JAX-RS: literal POST /owners consumer → create.
    assert (
        "client.ts::createOwner",
        "OwnerResource.java::OwnerResource.create",
        "http::POST::/owners",
    ) in routes
