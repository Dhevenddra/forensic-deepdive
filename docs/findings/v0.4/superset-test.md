# superset — v0.4 real-repo test (the staged cross-stack target + scale)

The flagship v0.4 repo: a large Flask/SQLAlchemy backend ↔ React/TypeScript
frontend. The v0.3 plan was "the one query that retrieves both ends now becomes a
*joined* ROUTES_TO graph." Re-run with v0.4 HEAD, Superset delivers the **scale**
proofs (Item-I spec coverage, Item-B heritage, Item-K LOD) — and **honestly
surfaces the cross-stack join's next frontier**: Superset's two custom
abstractions (a `SupersetClient` frontend wrapper + a Flask-AppBuilder backend)
that v0.4's generic extractors don't yet cover.

## Run summary

| | |
|---|---|
| Date | 2026-06-05 |
| Repo | [apache/superset](https://github.com/apache/superset) (same checkout as v0.3, `f17e4de9cd`) |
| Tool version | v0.4 HEAD (`a5b3e02`) |
| Files | **3,871** · Symbols **18,764** · CALLS 16,816 |

## Gate #4 — TS heritage at scale ✅

| heritage | v0.3 | v0.4 | Δ |
|---|---|---|---|
| EXTENDS | 1,166 | **1,320** | **+154** |
| IMPLEMENTS | 1 | 1 | — |

+154 EXTENDS from the DEC-050 TS captures (abstract classes, interface-extends,
generic/member-expression supertypes) applied across Superset's large TS
frontend. (IMPLEMENTS stays 1 — Superset's TS uses `extends` far more than
`implements`; the gain lands in EXTENDS, as on gitnexus.)

## Gate #3 — Item-I spec coverage at scale ✅ (and the located-handler gap)

Superset commits an OpenAPI spec at `docs/static/resources/openapi.json`. The
codegen detector found it and produced **277 Endpoints, 276 `spec_backed=True`**.
The spec-coverage metric, at scale:

| | count |
|---|---|
| spec operations (documented) | **276** |
| located handlers | **1** |
| documented-but-unlocated | **275** |

This is the *honest* large-repo version of the openapi-shop showcase: the spec is
fully ingested (276 EXTRACTED, documented endpoints), but only **1** resolves to
an in-code handler — because Superset's backend is **Flask-AppBuilder**
(class-based `ModelRestApi` / `@expose`), which v0.4's plain-`@app.route`/`@router`
Flask provider extractor does not match. The 275 unlocated endpoints are surfaced,
not hidden (`trace … unlocated=True`).

## Gate #2 — ROUTES_TO on Superset: **the honest shortfall** ❌→ v0.5

**0 ROUTES_TO** on Superset, from two independent custom-abstraction gaps:

1. **Frontend (consumer side).** Superset calls its API exclusively through a
   wrapper: **`SupersetClient.get/post/put/delete({ endpoint: '/api/v1/…' })`** —
   **252 call sites** (119 get / 64 post / 40 delete / 29 put). None are raw
   `fetch`/`axios`, so v0.4's seven consumer extractors match **0** of them →
   **1 CALLS_ENDPOINT total**.
2. **Backend (provider side).** Flask-AppBuilder, not bare Flask — **1 of 276**
   handlers located (above).

Both ends are invisible to the generic extractors, so no join materializes. This
is **not a silent failure** — the 276 documented endpoints are present, and the
tool reports 0 joins rather than fabricating any. It is the precise, concrete
definition of the v0.5 cross-stack work:

> **v0.5 head-of-line (this finding):** a **`SupersetClient`-style configured-client
> consumer extractor** (`.get/.post({endpoint|url})`, reusing the axios-object
> path) + a **Flask-AppBuilder provider extractor** (`ModelRestApi`/`@expose`).
> With both, Superset's 252 call sites would join its located handlers and the
> flagship ROUTES_TO graph lands. Joins the already-deferred NestJS/Django/JAX-RS
> gap-fillers (DEC-045 §7).

The cross-stack **capability itself is validated** on the clean
[`spring-react-demo`](spring-react-demo-test.md) (4 TS→Java joins, 2 EXTRACTED / 2
INFERRED) and [`openapi-shop`](openapi-shop-test.md) (spec-backed EXTRACTED) repos
— Superset shows the join is gated by *framework coverage*, not by the join
machinery.

## Gate #6 — `serve --ui` renders Superset (the 348k LOD proof) ✅

Superset's graph carries **348,118 `CO_CHANGES_WITH`** edges — the exact figure
that made mandatory level-of-detail non-negotiable (DEC-053). The served graph
endpoint holds the line:

| view | nodes | edges | notes |
|---|---|---|---|
| default (`/api/graph`) | **114** | **116** | CALLS+EXTENDS; CO_CHANGES_WITH **opt-in, OFF** → 348k never sent |
| all edge types forced on | 192 | 316 | still bounded by the node/edge caps |

The browser never receives more than the caps allow, regardless of filter
combination — the structural LOD guarantee. (ROUTES_TO highlighting can't be shown
*on Superset* since it has none; that encoding is demonstrated on the clean
cross-stack repos.)

## Gate #9 — AGENT_BRIEF ✅

**1,663 B** at 18,764 symbols (≤5120). CALLS AMBIGUOUS **19.1 %** (unchanged vs
v0.3 — Item C path untouched).

## Assessment

- **Strong:** TS-heritage (+154 EXTENDS), Item-I spec coverage at scale (276
  documented, 1 located — honestly), and the **348k → 114-node** `serve --ui` LOD
  proof all land on the flagship repo.
- **Honest shortfall (gate #2):** 0 ROUTES_TO on Superset specifically, because
  its `SupersetClient` wrapper + Flask-AppBuilder backend are outside v0.4's
  generic extractor coverage. The wedge is proven on clean repos; Superset defines
  the concrete v0.5 extractor work. No fabricated joins — the gap is reported.
