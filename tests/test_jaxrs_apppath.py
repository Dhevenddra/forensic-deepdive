"""JAX-RS completion (DEC-073, v0.7 Step 2).

``@ApplicationPath`` prepends one app-wide prefix to every resource path; ``@Produces``/
``@Consumes`` carry the media type(s) as a non-key Endpoint *property* (``content_type``);
an interface-return sub-resource locator resolves via a single intra-repo ``implements``
(INFERRED). All over the unchanged ``Endpoint``/``base.join``/emit/serve spine.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.http.providers.jaxrs import (
    _application_path,
    _format_content_type,
    _implemented_interfaces,
    _media_annotations,
    extract_jaxrs_providers,
)
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.graph.schema import Confidence
from forensic_deepdive.pipeline import PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig
from forensic_deepdive.static.parse import parse_source

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "jaxrs_apppath_sample"
_LANGS = {
    "RestApplication.java": "java",
    "GreetingResource.java": "java",
    "WidgetService.java": "java",
    "WidgetServiceImpl.java": "java",
    "client.ts": "typescript",
}


# --- pure helpers -----------------------------------------------------------


def _first(src: str, node_type: str):
    root = parse_source(src.encode(), "java").root_node
    stack = [root]
    while stack:
        n = stack.pop()
        if n.type == node_type:
            return n, src.encode()
        stack.extend(n.children)
    raise AssertionError(f"no {node_type}")


def test_application_path_helper():
    c, data = _first('@ApplicationPath("/api") class App {}', "class_declaration")
    assert _application_path(c, data) == "/api"
    # A bare @ApplicationPath → "" (mount at root); a class without one → None.
    c, data = _first("@ApplicationPath class App {}", "class_declaration")
    assert _application_path(c, data) == ""
    c, data = _first("class Plain {}", "class_declaration")
    assert _application_path(c, data) is None


def test_media_annotations_and_format():
    # MediaType constants map to their media strings; a braced array keeps source order.
    m, data = _first(
        "class C { @Produces({MediaType.APPLICATION_JSON, MediaType.APPLICATION_XML}) "
        "@Consumes(MediaType.APPLICATION_JSON) void f() {} }",
        "method_declaration",
    )
    modifiers = next(c for c in m.children if c.type == "modifiers")
    produces, consumes = _media_annotations(modifiers, data)
    assert produces == ["application/json", "application/xml"]
    assert consumes == ["application/json"]
    assert (
        _format_content_type(produces, consumes)
        == "produces=application/json,application/xml; consumes=application/json"
    )
    # A string-literal media type is read verbatim; produces-only omits the consumes half.
    m, data = _first('class C { @Produces("text/csv") void f() {} }', "method_declaration")
    modifiers = next(c for c in m.children if c.type == "modifiers")
    produces, consumes = _media_annotations(modifiers, data)
    assert _format_content_type(produces, consumes) == "produces=text/csv"


def test_implemented_interfaces_helper():
    c, data = _first("class Impl implements A, B {}", "class_declaration")
    assert _implemented_interfaces(c, data) == ["A", "B"]
    c, data = _first("class Plain {}", "class_declaration")
    assert _implemented_interfaces(c, data) == []


# --- extractor-level (content_type is a Contract property, not a graph column) ----------


def _ctx(tmp_path: Path) -> ContractContext:
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    return ContractContext(
        tags=[], imports=[], method_calls=[], source_files_by_path=dict(_LANGS), repo_path=repo
    )


def test_app_prefix_and_content_type_on_contracts(tmp_path):
    by_sym = {c.symbol_id: c for c in extract_jaxrs_providers(_ctx(tmp_path))}
    # Every resource path carries the "/api" @ApplicationPath prefix (EXTRACTED).
    listc = by_sym["GreetingResource.java::GreetingResource.list"]
    assert listc.contract_id == "http::GET::/api/greetings"
    assert listc.confidence is Confidence.EXTRACTED
    # Class-level @Produces is the default content-type property (never part of the key).
    assert listc.content_type == "produces=application/json"
    # Method @Consumes folds in alongside the inherited class @Produces.
    createc = by_sym["GreetingResource.java::GreetingResource.create"]
    assert createc.contract_id == "http::POST::/api/greetings"
    assert createc.content_type == "produces=application/json; consumes=application/json"
    # Method-level @Produces overrides the class default (array → both media types).
    getc = by_sym["GreetingResource.java::GreetingResource.get"]
    assert getc.contract_id == "http::GET::/api/greetings/{param}"
    assert getc.content_type == "produces=application/json,application/xml"


def test_interface_return_locator_resolves_to_single_impl(tmp_path):
    contracts = extract_jaxrs_providers(_ctx(tmp_path))
    impl = next(
        c for c in contracts if c.symbol_id == "WidgetServiceImpl.java::WidgetServiceImpl.read"
    )
    # widget() returns the WidgetService interface → its single implementer (DEC-073),
    # under the app + resource + locator prefix, INFERRED (not a declared concrete return).
    assert impl.contract_id == "http::GET::/api/greetings/widget"
    assert impl.confidence is Confidence.INFERRED


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


def test_app_prefixed_routes_in_graph(tmp_path):
    db_path = _build(tmp_path)
    with LadybugStore(db_path) as s:
        handles = {
            (r[0], r[1], r[2])
            for r in s.query(
                "MATCH (e:Endpoint)<-[r:HANDLES]-(sym:Symbol) WHERE e.framework='jaxrs' "
                "RETURN e.contract_id, sym.qualified_name, r.confidence"
            )
        }
    # The @ApplicationPath prefix reaches the graph; the interface locator joins INFERRED.
    assert (
        "http::GET::/api/greetings",
        "GreetingResource.java::GreetingResource.list",
        "EXTRACTED",
    ) in handles
    assert (
        "http::GET::/api/greetings/widget",
        "WidgetServiceImpl.java::WidgetServiceImpl.read",
        "INFERRED",
    ) in handles


def test_consumer_joins_app_prefixed_route(tmp_path):
    db_path = _build(tmp_path)
    with LadybugStore(db_path) as s:
        routes = {
            (r[0], r[1], r[2])
            for r in s.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) "
                "RETURN c.qualified_name, p.qualified_name, r.endpoint"
            )
        }
    # The TS consumer hits the prefixed path "/api/greetings" → joins list across the stack.
    assert (
        "client.ts::loadGreetings",
        "GreetingResource.java::GreetingResource.list",
        "http::GET::/api/greetings",
    ) in routes
