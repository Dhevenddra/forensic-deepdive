# Apache Superset — v0.5 acceptance (the flagship gap, closed: 0 → 61 ROUTES_TO)

The repo that **defined v0.5**. v0.4 scored **0 `ROUTES_TO`** on Superset — its
frontend calls the API only through a `SupersetClient.get/post({ endpoint })` wrapper
(252 sites, matched by none of the seven raw fetch/axios consumers) and its backend is
**Flask-AppBuilder** (`ModelRestApi`/`@expose`, 1 of 276 endpoints located). That single
shortfall was the v0.4 §4.9 gate's only miss (8/9) and the head-of-line for v0.5 Step 1
(DEC-056). This run tests whether the gap is closed on the real codebase.

## Run summary

| | |
|---|---|
| Date | 2026-06-12 |
| Repo | apache/superset (`C:\Dev\scratch`, Apache-2.0) |
| Tool version | v0.5 HEAD (DEC-055 → DEC-062) |
| Symbols | **18,764** · extract **1,283 s** (full graph build) |

## Step 1 — the flagship cross-stack gap, CLOSED

| signal | v0.4 | **v0.5** |
|---|---|---|
| HTTP `ROUTES_TO` (SupersetClient ↔ Flask-AppBuilder) | **0** | **61** |
| → EXTRACTED | — | **54** |
| → INFERRED | — | **7** |
| configured-client Endpoints (`SupersetClient.{get,post,…}({endpoint})`) | — | **32** |
| Flask-AppBuilder provider Endpoints (`ModelRestApi`/`@expose`) | 1 | **200** |

**Real joins materialized** (a sample — frontend consumer → backend handler):

```
ChartList.tsx::handleBulkChartDelete   → ChartRestApi.bulk_delete  DELETE /api/v1/chart        EXTRACTED
CRUD/utils.tsx::handleChartDelete      → ChartRestApi.delete       DELETE /api/v1/chart/{param} EXTRACTED
AnnotationLayer.tsx::fetchAppliedChart → ChartRestApi.get          GET /api/v1/chart/{param}    EXTRACTED
exploreActions.ts::fetchFaveStar       → ChartRestApi.favorite_status  GET …/favorite_status    EXTRACTED
DashboardList.tsx::handleBulkDashboardDelete → DashboardRestApi.bulk_delete  DELETE /api/v1/dashboard  EXTRACTED
```

These are exactly the `SupersetClient` → Flask-AppBuilder cross-stack joins that were
invisible in v0.4 — now a materialized graph with an honest 54/7 EXTRACTED/INFERRED
split (the 7 INFERRED are templated client paths like `/chart/${id}` joining a
`/chart/{param}` route). **The §4.9 gate's one shortfall is resolved: Superset 8/9 → 9/9.**

The two DEC-056 extractors did it with **no fabricated joins** — both built on the
**unchanged** `base.join`/`Endpoint` spine (the keystone held: the diff was two new
extractors + the provider list, no `trace`/emit/`serve` change).

## Step 4 — SQLAlchemy ORM (the DI/ORM tail on Python)

| signal | value |
|---|---|
| `PERSISTS_TO` (model → table) | **210** |
| `DbTable` nodes | **55** |

Real `__tablename__` models → tables: `ab_user`, `ab_role`, `alerts`,
`annotation_layer`, `dashboard_slices`, `css_templates`, `cache_keys`, … — Superset's
full SQLAlchemy persistence layer, materialized. `trace` can now reach a `DbTable`
from a handler through the ORM tail on a real Python codebase.

## Discovery (logged — the next honest refinement)

- **1 of 55 tables mis-tagged `django`** (`table::coremodel`): a class with a `Model`
  base that isn't a Django model was classified by the Django branch instead of
  SQLAlchemy. A ~2 % false-classification on the ORM-framework label (the table + edge
  are still correct — only the `orm` property is wrong). Tightening the Django-vs-other
  `Model`-base disambiguation (require a Django-specific signal: `models.Model` import,
  a `Meta` inner class, or an `app` context) is a clean v0.6 follow-on. Flagged here
  rather than silently accepted — the v0.4 → v0.5 findings-drive-the-next-fix pattern.

## Caveats (honest)

- Full extraction on 18.7k symbols is **~21 min** (the cross-stack join + SQLAlchemy
  passes over a large polyglot repo). A perf pass is a standing v0.6 candidate.

## Takeaway

The repo that exposed v0.4's one gap now passes cleanly: **0 → 61 cross-stack
`ROUTES_TO`** (configured-client ↔ Flask-AppBuilder) **+ 210 `PERSISTS_TO`** over its
SQLAlchemy layer. The v0.5 §4.9 gate reaches **9/9** on its own flagship. The whole arc
was scoped from this repo's v0.4 shortfall — and it is now closed, on the real code,
with an honest confidence split and no fabrication.
