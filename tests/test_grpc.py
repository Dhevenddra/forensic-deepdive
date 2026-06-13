"""gRPC as a CrossBoundaryEdge protocol (DEC-060/061, v0.5 Step 5).

Covers the three extractors (`.proto` spec scan, Python servicer provider, Python
stub consumer) in isolation and the end-to-end join: a stub call joins its servicer
method on `grpc::<Svc>/<Method>`, EXTRACTED because the `.proto` makes it spec-backed
(the generalized reconcile collapses spec+servicer into one provider). An rpc with no
servicer is an honest spec-only endpoint. Zero new runtime dep — the `.proto` floor is
the tree-sitter-proto grammar already in tree-sitter-language-pack (DEC-061).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.grpc.consumers.stubs import extract_stub_consumers
from forensic_deepdive.contracts.grpc.normalize import (
    grpc_module_alias_table,
    grpc_resolve_module,
)
from forensic_deepdive.contracts.grpc.proto_scan import extract_proto_providers
from forensic_deepdive.contracts.grpc.providers.servicers import extract_servicer_providers
from forensic_deepdive.contracts.registry import ContractContext
from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.pipeline import PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig
from forensic_deepdive.static.imports import Import, ImportedName

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "grpc_sample"


def _ctx(tmp_path: Path) -> ContractContext:
    repo = tmp_path / SAMPLE
    shutil.copytree(FIXTURES / SAMPLE, repo)
    return ContractContext(
        tags=[],
        imports=[],
        method_calls=[],
        source_files_by_path={"server.py": "python", "client.py": "python"},
        repo_path=repo,
    )


def _imp(rel_path, module_path, names=(), alias=""):
    return Import(
        rel_path=rel_path,
        module_path=module_path,
        language="python",
        line=0,
        module_alias=alias,
        imported_names=tuple(ImportedName(n, a) for n, a in names),
    )


def test_grpc_module_alias_table_and_resolution():
    rel = "examples/helloworld/greeter_server.py"
    # flat sibling import → directory-qualified (two dirs that both `import X` differ).
    t = grpc_module_alias_table([_imp(rel, "helloworld_pb2_grpc")], rel)
    assert (
        grpc_resolve_module("helloworld_pb2_grpc", t) == "examples/helloworld/helloworld_pb2_grpc"
    )
    # aliased flat import.
    t = grpc_module_alias_table([_imp(rel, "helloworld_pb2_grpc", alias="hw")], rel)
    assert grpc_resolve_module("hw", t) == "examples/helloworld/helloworld_pb2_grpc"
    # `from . import X_pb2_grpc` (relative submodule) → directory-qualified sibling.
    t = grpc_module_alias_table([_imp(rel, ".", names=[("route_guide_pb2_grpc", "")])], rel)
    assert (
        grpc_resolve_module("route_guide_pb2_grpc", t) == "examples/helloworld/route_guide_pb2_grpc"
    )
    # `from pkg.gen import foo_pb2_grpc` (dotted package) → shared dotted identity.
    t = grpc_module_alias_table([_imp(rel, "pkg.gen", names=[("foo_pb2_grpc", "")])], rel)
    assert grpc_resolve_module("foo_pb2_grpc", t) == "pkg.gen.foo_pb2_grpc"
    # `from helloworld_pb2_grpc import GreeterStub` (symbol from a flat module).
    t = grpc_module_alias_table(
        [_imp(rel, "helloworld_pb2_grpc", names=[("GreeterStub", "")])], rel
    )
    assert grpc_resolve_module("GreeterStub", t) == "examples/helloworld/helloworld_pb2_grpc"


def test_proto_scan_emits_spec_backed_providers(tmp_path):
    provs = {c.contract_id: c for c in extract_proto_providers(_ctx(tmp_path))}
    assert set(provs) == {
        "grpc::route_guide_pb2_grpc::RouteGuide/GetFeature",
        "grpc::route_guide_pb2_grpc::RouteGuide/ListFeatures",
        "grpc::route_guide_pb2_grpc::RouteGuide/RecordRoute",
    }
    assert all(c.spec_backed and c.protocol == "grpc" for c in provs.values())


def test_servicer_methods_are_providers(tmp_path):
    provs = {(c.contract_id, c.symbol_id) for c in extract_servicer_providers(_ctx(tmp_path))}
    assert (
        "grpc::route_guide_pb2_grpc::RouteGuide/GetFeature",
        "server.py::RouteGuideServicer.GetFeature",
    ) in provs
    assert (
        "grpc::route_guide_pb2_grpc::RouteGuide/ListFeatures",
        "server.py::RouteGuideServicer.ListFeatures",
    ) in provs
    # RecordRoute has no servicer method.
    assert not any(cid.endswith("RecordRoute") for cid, _ in provs)


def test_stub_calls_are_consumers(tmp_path):
    cons = {(c.contract_id, c.symbol_id) for c in extract_stub_consumers(_ctx(tmp_path))}
    assert ("grpc::route_guide_pb2_grpc::RouteGuide/GetFeature", "client.py::fetch_feature") in cons
    assert ("grpc::route_guide_pb2_grpc::RouteGuide/ListFeatures", "client.py::list_all") in cons


def _run(tmp_path: Path) -> Path:
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


def test_grpc_routes_to_is_extracted_spec_backed(tmp_path):
    db = _run(tmp_path)
    with LadybugStore(db) as s:
        routes = {
            tuple(r)
            for r in s.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) WHERE r.via = 'grpc' "
                "RETURN c.qualified_name, p.qualified_name, r.endpoint, r.confidence"
            )
        }
    assert routes == {
        (
            "client.py::fetch_feature",
            "server.py::RouteGuideServicer.GetFeature",
            "grpc::route_guide_pb2_grpc::RouteGuide/GetFeature",
            "EXTRACTED",
        ),
        (
            "client.py::list_all",
            "server.py::RouteGuideServicer.ListFeatures",
            "grpc::route_guide_pb2_grpc::RouteGuide/ListFeatures",
            "EXTRACTED",
        ),
    }


def test_unimplemented_rpc_is_spec_only_endpoint(tmp_path):
    db = _run(tmp_path)
    cid = "grpc::route_guide_pb2_grpc::RouteGuide/RecordRoute"
    with LadybugStore(db) as s:
        spec_backed = {
            r[0]
            for r in s.query(
                f"MATCH (e:Endpoint) WHERE e.contract_id = '{cid}' RETURN e.spec_backed"
            )
        }
        handlers = list(
            s.query(
                "MATCH (sm:Symbol)-[:HANDLES]->(e:Endpoint) "
                f"WHERE e.contract_id = '{cid}' RETURN sm.qualified_name"
            )
        )
    assert spec_backed == {True}
    assert handlers == []  # spec-only — no servicer located (honest)
