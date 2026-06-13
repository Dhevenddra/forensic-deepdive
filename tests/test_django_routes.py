"""Django decoupled-route provider (DEC-065, v0.6 Step 2).

A Django ``urls.py`` maps paths to views in *other* files; this provider does
cross-file view resolution (the shared DEC-059 ladder + Python submodule
resolution) and recurses ``include()`` prefixes. Routes join existing fetch
consumers via ROUTES_TO over the unchanged Endpoint/base.join spine.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.contracts.http.providers.django import (
    _parse_route_call,
    _regex_to_path,
    _scan_urlpatterns,
)
from forensic_deepdive.graph import LadybugStore
from forensic_deepdive.pipeline import PipelineRunner, default_phases
from forensic_deepdive.pipeline.runner import ExtractConfig
from forensic_deepdive.static.parse import parse_source

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = "django_routes_sample"


# --- pure parsing (no cross-file resolution) --------------------------------


def _parse(src: str):
    return parse_source(src.encode(), "python").root_node, src.encode()


def test_regex_to_path_collapses_groups():
    assert _regex_to_path(r"^pets/(?P<pet_id>[0-9]+)/$") == ("pets/{param}/", True)
    assert _regex_to_path(r"^owners/(\d+)/$") == ("owners/{param}/", True)


def test_scan_urlpatterns_classifies_entries():
    src = (
        "from django.urls import path, include, re_path\n"
        "urlpatterns = [\n"
        "    path('vets/', views.vet_list),\n"
        "    path('vets/<int:pk>/', VetDetail.as_view()),\n"
        "    re_path(r'^pets/(?P<id>[0-9]+)/$', legacy_view),\n"
        "    path('api/', include('myproject.api.urls')),\n"
        "]\n"
        "urlpatterns += router.urls\n"
    )
    root, data = _parse(src)
    entries = _scan_urlpatterns(root, data)
    kinds = [(e.kind, e.prefix) for e in entries]
    assert ("route", "vets/") in kinds
    assert ("route", "vets/<int:pk>/") in kinds
    assert ("route", "pets/{param}/") in kinds  # re_path normalized
    assert ("module_include", "api/") in kinds
    assert ("router_include", "") in kinds  # urlpatterns += router.urls


def _first_call(root):
    stack = [root]
    while stack:
        n = stack.pop()
        if n.type == "call":
            return n
        stack.extend(n.children)
    raise AssertionError("no call node")


def test_parse_route_call_reads_view_refs():
    root, data = _parse("path('vets/', views.vet_list)\n")
    entry = _parse_route_call(_first_call(root), data)
    assert entry is not None and entry.kind == "route"
    assert entry.view is not None and (entry.view.module, entry.view.member) == (
        "views",
        "vet_list",
    )

    root, data = _parse("path('x/', OwnerDetail.as_view())\n")
    entry = _parse_route_call(_first_call(root), data)
    assert entry.view is not None and (entry.view.module, entry.view.member) == ("", "OwnerDetail")


# --- full-pipeline acceptance (HANDLES across files + ROUTES_TO) -------------


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


def _handles(store) -> set[tuple[str, str]]:
    return {
        (r[0], r[1])
        for r in store.query(
            "MATCH (e:Endpoint)<-[:HANDLES]-(s:Symbol) RETURN e.contract_id, s.qualified_name"
        )
    }


def test_handles_bind_views_across_files_with_include_prefix(tmp_path):
    db_path = _build(tmp_path)
    with LadybugStore(db_path) as s:
        handles = _handles(s)
    views_file = "myproject/api/views.py"
    # include('myproject.api.urls') prefix 'api/v1/' concatenates onto app routes,
    # and the handler resolves cross-file into views.py.
    assert ("http::*::/api/v1/vets", f"{views_file}::vet_list") in handles
    assert ("http::*::/api/v1/vets/{param}", f"{views_file}::VetDetail") in handles
    assert ("http::*::/api/v1/pets/{param}", f"{views_file}::legacy_view") in handles
    # DRF DefaultRouter CRUD expansion, prefixed by the include().
    assert ("http::POST::/api/v1/owners", f"{views_file}::OwnerViewSet") in handles
    assert ("http::GET::/api/v1/owners/{param}", f"{views_file}::OwnerViewSet") in handles


def test_unresolvable_view_is_honest_unmatched(tmp_path):
    """``views.does_not_exist`` resolves to no symbol → the Endpoint exists (we see
    the route) but there is no HANDLES edge (no synthetic handler — no fabrication)."""
    db_path = _build(tmp_path)
    with LadybugStore(db_path) as s:
        endpoints = {r[0] for r in s.query("MATCH (e:Endpoint) RETURN e.contract_id")}
        handled = {
            r[0] for r in s.query("MATCH (e:Endpoint)<-[:HANDLES]-(:Symbol) RETURN e.contract_id")
        }
    assert "http::*::/api/v1/missing" in endpoints
    assert "http::*::/api/v1/missing" not in handled


def test_routes_to_joins_consumer_to_django_views(tmp_path):
    db_path = _build(tmp_path)
    with LadybugStore(db_path) as s:
        routes = {
            (r[0], r[1], r[2], r[3])
            for r in s.query(
                "MATCH (c:Symbol)-[r:ROUTES_TO]->(p:Symbol) "
                "RETURN c.qualified_name, p.qualified_name, r.endpoint, r.confidence"
            )
        }
    views_file = "myproject/api/views.py"
    # Method-agnostic function view: GET consumer joins via the DEC-047 wildcard
    # fallback → INFERRED.
    assert (
        "client.ts::loadVets",
        f"{views_file}::vet_list",
        "http::GET::/api/v1/vets",
        "INFERRED",
    ) in routes
    # DRF create: literal POST consumer exact-matches the EXTRACTED provider.
    assert (
        "client.ts::createOwner",
        f"{views_file}::OwnerViewSet",
        "http::POST::/api/v1/owners",
        "EXTRACTED",
    ) in routes
