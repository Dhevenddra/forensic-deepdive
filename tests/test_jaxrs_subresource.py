"""JAX-RS sub-resource locators (DEC-066, v0.6 Step 3).

A ``@Path`` method with no verb is a sub-resource locator: its declared return type
resolves to a resource class (shared resolver + JAX-RS class index), and we recurse
into that class's routes, concatenating the prefix. Unresolvable (``Object``) returns
emit an honest unmatched locator. Over the unchanged Endpoint/base.join spine.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.http.providers.jaxrs import (
    _method_locator,
    _return_type_name,
)
from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.pipeline import PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig
from forensic_deepdive.static.parse import parse_source

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "jaxrs_subresource_sample"


# --- pure helpers -----------------------------------------------------------


def _method(src: str):
    root = parse_source(src.encode(), "java").root_node
    stack = [root]
    while stack:
        n = stack.pop()
        if n.type == "method_declaration":
            return n, src.encode()
        stack.extend(n.children)
    raise AssertionError("no method")


def test_locator_detection_and_return_type():
    m, data = _method('class C { @Path("items/{id}/") public Item getItem() {} }')
    assert _method_locator(m, data) == "items/{id}/"
    assert _return_type_name(m, data) == "Item"
    # A verb method is not a locator.
    m, data = _method('class C { @GET @Path("x/") public Item read() {} }')
    assert _method_locator(m, data) is None
    # A @Path method returning a non-resource (String/void) is not a locator.
    m, data = _method('class C { @Path("y/") public String label() {} }')
    assert _method_locator(m, data) is None
    # Class<Item> → the type argument.
    m, data = _method('class C { @Path("z/") public Class<Item> locate() {} }')
    assert _return_type_name(m, data) == "Item"


# --- full-pipeline acceptance -----------------------------------------------


def _build(tmp_path: Path) -> Path:
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
    return db_path


def test_subresource_routes_resolve_across_files(tmp_path):
    db_path = _build(tmp_path)
    with LadybugStore(db_path) as s:
        handles = {
            (r[0], r[1], r[2])
            for r in s.query(
                "MATCH (e:Endpoint)<-[r:HANDLES]-(sym:Symbol) WHERE e.framework='jaxrs' "
                "RETURN e.contract_id, sym.qualified_name, r.confidence"
            )
        }
        endpoints = {r[0] for r in s.query("MATCH (e:Endpoint) RETURN e.contract_id")}
        handled = {
            r[0] for r in s.query("MATCH (e:Endpoint)<-[:HANDLES]-(:Symbol) RETURN e.contract_id")
        }
    # Locator BookStore.getItem -> Item.read, prefix concatenated, resolved cross-file.
    assert ("http::GET::/store/items/{param}", "Item.java::Item.read", "EXTRACTED") in handles
    # Nested locator Item.getTrack -> Track.read.
    nested = ("http::GET::/store/items/{param}/track", "Track.java::Track.read", "EXTRACTED")
    assert nested in handles
    # Object return -> honest unmatched locator (Endpoint exists, no handler).
    assert "http::*::/store/anything" in endpoints
    assert "http::*::/store/anything" not in handled


def test_subresource_route_joins_consumer(tmp_path):
    db_path = _build(tmp_path)
    with LadybugStore(db_path) as s:
        routes = {
            (r[0], r[1], r[2])
            for r in s.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) "
                "RETURN c.qualified_name, p.qualified_name, r.endpoint"
            )
        }
    assert (
        "client.ts::loadItem",
        "Item.java::Item.read",
        "http::GET::/store/items/{param}",
    ) in routes
