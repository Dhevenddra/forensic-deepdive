# Findings — v0.6 "Findings-Driven Refinements"

v0.5 proved the DEC-043 `CrossBoundaryEdge`/`Endpoint` abstraction generalizes across
**five protocols on one spine** (HTTP, MCP, registry-dispatch, gRPC, messaging). v0.6 does
**not** add a sixth protocol or expand the public surface — it **hardens** that abstraction
against the four real-repo failure modes the v0.5 acceptance runs surfaced + ships the
deferred Django provider + hardens lane-(iii) memory + a profiling pass. Every refinement is
a `KeyBuilder` / provider / consumer / resolver / `reconcile_*` change over the **unchanged**
`base.join`/`Endpoint`/`trace`/emit/`serve` machinery (DEC-063 scope verdict).

See [`../README.md`](../README.md) for the findings convention.

## What shipped (DEC-063 → DEC-070)

| Step | DEC | Refinement | Real-repo acceptance | Keystone |
|---|---|---|---|---|
| 0 | 063 | scope verdict (harden, not expand) | — | — |
| 1 | 064 | ORM Django/SQLAlchemy disambiguation | apache/superset **54/55 → 55/55** ORM tags | held (a pure `orm`-property fix) |
| 2 | 065 | Django decoupled-route provider | wagtail **0 → 125** Endpoints, **99 EXTRACTED cross-file HANDLES** / 29 files | held (`providers/` add + shared resolver) |
| 3 | 066 | JAX-RS sub-resource locators | jersey `bookstore-webapp` **0 → 1** cross-file EXTRACTED | held (`providers/` extension) |
| 4 | 067 | AMQP topic-exchange + binding topology | rabbitmq-tutorials **0 → 3** exchange ROUTES_TO | held (exchange key + `reconcile_amqp`) |
| 5 | 068 | gRPC module/directory-qualified keying | grpc-examples **~975 → 68** AMBIGUOUS (cartesian resolved) + 26 EXTRACTED | held (more-specific key, same join) |
| 6 | 069 | lane-(iii) FTS5 memory + shadow-ref | round-trip + rebuild + dedup + survives-a-clone + **dogfood** | the one sanctioned `mcp_server` touch (existing tool's backend) |
| 7 | 070 | profiling pass | Superset extract **1711s → 117s (14.7×)**, byte-identical | held (`resolver.py` only) |

Per-refinement detail: [superset-orm](superset-orm-test.md) · [django-routes](django-routes-test.md)
· [jaxrs-subresource](jaxrs-subresource-test.md) · [amqp-topic](amqp-topic-test.md) ·
[grpc-keying](grpc-keying-test.md) · [memory-recall](memory-recall-test.md) ·
[profiling](profiling-test.md).

## The keystone — concrete evidence it held

Every protocol refinement (Steps 1–5) was a pure extractor/resolver change: the per-step
`git diff` over `mcp_server/server.py` (`trace`), `emit/hotpaths_md.py`, and
`serve/graph_api.py` is **empty**. `base.join` was never touched for a new match shape —
the two trickiest cases proved the rule:
- **AMQP wildcard matching** (Step 4) re-keys onto the shared-literal *exchange* so `join`
  matches by exact key, then refines in a contract-layer `base.reconcile_amqp` prune
  (the DEC-060 precedent) — never in `join`.
- **gRPC cartesian collision** (Step 5) is fixed by a *more-specific key*
  (`grpc::<module>::<Svc>/<Method>`) on the same exact-match join — not a new join.

Step 6's only `mcp_server` change is the sanctioned `recall_insights` **backend** swap (no
signature change, no 10th tool); Step 7 touches `resolver.py` only. The five surfacing
queries (`trace` / HOTPATHS `## Cross-stack routes` / `serve --ui`) light up every new
Django/JAX-RS/AMQP/gRPC route **for free**, with zero `protocol==` branch.

## Honesty (reported, never fabricated)

v0.6 surfaced its own v0.7 seeds rather than papering over them:
- **Django `include(<variable>)` is not recursed** (only string `include()`); wagtail's
  variable-mounts emit their routes at bare paths (9 endpoints collapse without the parent
  prefix) — routes/handlers still correct, prefix dropped. (DEC-065)
- **AMQP dynamic routing keys** (the rabbitmq tutorials compute keys from `sys.argv`) →
  **INFERRED** on the shared exchange, never a fabricated EXTRACTED. (DEC-067)
- **gRPC** route_guide's genuine sync+async dual servicer (and helloworld's 5 server
  variants) **stay AMBIGUOUS** — real multiple implementations, never one guessed. (DEC-068)
- **JAX-RS** `Object`/unresolvable locator returns → an honest unmatched Endpoint, never a
  guessed sub-route. (DEC-066)

## §4.9 gate (publish-prep posture)

| gate item | status |
|---|---|
| `pytest -x` green | ✅ **740 passed** (710 → +30 across Steps 1–7) |
| `ruff check` / `format` clean | ✅ |
| goldens byte-identical | ✅ (every refinement graph-only; `python_sample`/`tiny_fixture` carry no new markers) |
| `AGENT_BRIEF ≤ 5kb` | ✅ (no emitter touched) |
| 5-artifact + 9-MCP-tool contract unchanged | ✅ (lane-iii improves an existing tool's backend only) |
| per-step keystone zero-diff | ✅ (Steps 1–5 never touch `trace`/emit/`serve`) |
| no new base-env runtime dep | ✅ (gRPC keying from generated-Python AST; FTS5 = stdlib `sqlite3`; `[proto]` stays deferred) |
| real-repo acceptance | ✅ superset / wagtail / jersey / rabbitmq / grpc-examples + dogfood + Superset profile |

## Takeaway

The four v0.5 real-repo findings are fixed, the deferred Django provider shipped, the
agent-memory layer hardened (zero-LLM), and the extract sped up 14.7× — each on the
**unchanged** five-protocol spine, each validated on real upstream code, with honest
confidence and no fabrication. forensic-deepdive remains the only shipped, pure-static,
materialized cross-boundary join — now hardened against the real world.
