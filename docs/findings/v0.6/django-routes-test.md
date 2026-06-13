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

## Honest shortfall (reported, not fabricated)

No Django repo is in the local stress set (`C:\Dev\scratch` currently holds the Step
3/4/5 repos: jersey, rabbitmq, grpc). The capability is **fixture-proven end to end**
across all the PRD-named shapes; the **real-repo stress matrix** (a DRF tutorial app for
the primary `include()`+router target, `django/django` and wagtail for cross-file scale)
is the pending acceptance item, to run when a Django repo is added to the stress set. Per
the v0.4/v0.5 findings discipline this is an acceptable pass with the real-repo run
flagged as the next step — not a defect.

## Takeaway

Django joins the cross-boundary join as a pure `providers/` add: a decoupled `urls.py`
table now binds to its view handlers across files and lights up `trace`/HOTPATHS/`serve
--ui` for free — the keystone held, with honest confidence and no fabrication.
