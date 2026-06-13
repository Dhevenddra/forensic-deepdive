# Django decoupled-route provider — v0.6 Step 2 acceptance (DEC-065)

DEC-062(C) deferred Django because a `urls.py` is a **decoupled routing table** — the
route and its handler live in different files — unlike the decorator-on-handler shape of
every other provider. Step 2 ships it with real cross-file view resolution, `include()`
prefix recursion, and DRF router expansion, over the **unchanged** Endpoint/`base.join`
spine.

## What landed (the keystone held)

`git diff` (non-test src) = new `contracts/http/providers/django.py` + the one-line
`PROVIDER_EXTRACTORS` append + the `resolve_name_to_files` move from `pipeline/phases.py`
to `static/resolver.py` (so a contract-layer extractor can reuse the DEC-059 ladder
without a `phases` import cycle; the two existing callers — inheritance, DI — re-import
it). **`base.join` / `registry.py` / `trace` / emit / `serve` untouched.**

## Fixture acceptance (`tests/fixtures/django_routes_sample/`)

A root URLconf `include('myproject.api.urls')` under `api/v1/`, an app URLconf with five
entries, cross-file views, a DRF `DefaultRouter`, and a TS fetch consumer. Full-pipeline
run → graph. Results (`tests/test_django_routes.py`, 6 tests):

| route shape | path (with include prefix) | HANDLES → handler (cross-file) | confidence |
|---|---|---|---|
| `path('vets/', views.vet_list)` | `http::*::/api/v1/vets` | `api/views.py::vet_list` | EXTRACTED |
| `path('vets/<int:pk>/', VetDetail.as_view())` | `http::*::/api/v1/vets/{param}` | `api/views.py::VetDetail` | EXTRACTED |
| `re_path(r'^pets/(?P<id>\d+)/$', legacy_view)` | `http::*::/api/v1/pets/{param}` | `api/views.py::legacy_view` | INFERRED (regex) |
| DRF `router.register('owners', OwnerViewSet)` | `http::{GET,POST}::/api/v1/owners` + `http::{GET,PUT,PATCH,DELETE}::/api/v1/owners/{param}` | `api/views.py::OwnerViewSet` | EXTRACTED-by-convention |
| `path('missing/', views.does_not_exist)` | `http::*::/api/v1/missing` | **none** (unresolvable view) | — |

**Cross-stack ROUTES_TO** (consumer → Django view, materialized):
- `client.ts::loadVets` → `api/views.py::vet_list` via `http::GET::/api/v1/vets` —
  **INFERRED** (a method-agnostic function view; the GET consumer joins through the
  DEC-047 method-wildcard fallback, the Spring bare-`@RequestMapping` precedent).
- `client.ts::createOwner` → `api/views.py::OwnerViewSet` via `http::POST::/api/v1/owners`
  — **EXTRACTED** (the DRF `create` route exact-matches the literal POST consumer).

This exercises every PRD §3.2 shape: the **`include()` prefix** concatenation (the
GitNexus #1183 fix), a **DRF router** CRUD expansion, **cross-file** handler binding
(bare + module-qualified + `as_view()` + submodule-import resolution), `re_path` regex
normalization, and the **no-fabrication** posture (unresolvable view → real Endpoint, no
synthetic HANDLES).

## Confidence discipline (DEC-065 / invariant 2)

EXTRACTED only for a literal `path()` + a resolved view, or a default-router CRUD set;
`re_path` (regex-derived path) and unknown router classes → INFERRED; a view resolved
only by the cross-file same-name fallback → its resolver confidence (INFERRED/AMBIGUOUS);
an unresolvable view is dropped (Endpoint kept, HANDLES filtered) — never a synthetic
`symbol_id`.

## Real-repo acceptance — `wagtail/wagtail` (the cross-file-scale stress, PRD matrix)

Shallow-cloned into `C:\Dev\scratch\wagtail` (a real Django CMS, ~707 Python + a React
admin; 962 files analyzed). v0.5 had **no Django provider** → 0 Django Endpoints; v0.6:

| signal | v0.5 | **v0.6** |
|---|---|---|
| Django `Endpoint` nodes | 0 | **125** |
| cross-file `HANDLES` (route → handler in another file) | 0 | **99, all EXTRACTED** |
| endpoints with a located handler | 0 | **83 / 125** (66 %) |
| distinct handler files bound | 0 | **29** |
| endpoints with >1 handler (the `include(variable)` collapse) | — | 9 |

The 99 HANDLES are all cross-file and all EXTRACTED — e.g. `http::*::/account` →
`wagtail/admin/views/account.py::AccountView` (route declared in
`wagtail/admin/urls/__init__.py`, handler resolved in a different file), `/aging-pages` →
`wagtail/admin/views/reports/aging_pages.py::AgingPagesView`. Module-qualified views
(`home.error_test`), bare `Klass.as_view()`, and module-qualified `home.HomeView.as_view()`
all resolve. The **42 unlocated** endpoints are honest (`handler=None`, no HANDLES, never a
synthetic symbol): `include(<variable>)` mounts (see below), `registry.as_view("index")`
instances (an object method, not a class view), and views that resolve to a non-`def`
symbol. 3 cross-stack `ROUTES_TO` materialized (wagtail's React admin mostly calls its own
client layer, so the frontend-join surface is small — expected for a CMS).

## Honest shortfall / v0.7 seed (reported, not fabricated)

- **`include(<variable>)` is not recursed** — only `include('app.urls')` (string) is.
  Wagtail mounts most sub-URLconfs as `path("api/", include(api_urls))` where `api_urls`
  is an imported list. Those modules are then treated as **roots** (emitted at their bare
  paths, missing the parent prefix), which is why 9 endpoints collapse onto a shared path
  with >1 handler (e.g. two apps' `add/` routes → `/multiple/add`). The routes + handlers
  are still correct and located; only the cross-module prefix is dropped. Resolving an
  `include(<variable>)` to the variable's bound urlpatterns list is a clean v0.7 follow-on
  (it extends the include-graph root detection, not the join). The **DRF default-router
  CRUD + string-`include()` prefix + cross-stack ROUTES_TO** are fully covered by the
  fixture e2e above; wagtail uses a *custom* `WagtailAPIRouter` (not Simple/Default), so
  its API routes aren't CRUD-expanded — correctly (an unknown router class → not expanded,
  no fabrication). A real DRF-default-router repo is a nice-to-have addition to the matrix.

## Takeaway

Django joins the cross-boundary join as a pure `providers/` add: a decoupled `urls.py`
table now binds to its view handlers **across files at real-repo scale** (wagtail: 0 →
125 Endpoints, 99 EXTRACTED cross-file HANDLES across 29 files) and lights up
`trace`/HOTPATHS/`serve --ui` for free — the keystone held, with honest confidence, a
documented `include(<variable>)` limitation (a v0.7 seed), and no fabrication.
