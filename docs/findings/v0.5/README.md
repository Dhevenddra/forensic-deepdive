# Findings — v0.5 "Cross-Boundary Protocols"

v0.5 extends the DEC-043 `CrossBoundaryEdge`/`Endpoint` abstraction past HTTP to
**five protocols on one spine** (HTTP, MCP, registry-dispatch, gRPC, messaging) +
the DI/ORM traceability tail. The headline is **agents**: v0.4's hermes-agent
scouting run ([`../v0.4/hermes-agent-test.md`](../v0.4/hermes-agent-test.md))
proved the static layer was *blind to how agents wire themselves* (186 `ClientSession`
+ 27 `FastMCP` + ~3,025 dispatch lines → **1** internal `ROUTES_TO`). v0.5 closes
exactly that gap.

See [`../README.md`](../README.md) for the findings convention (one folder per
release, one file per repo, narrative commentary; `examples/<repo>/` holds the
emitted artifacts).

## What shipped (build complete — DEC-055 → DEC-062)

| Step | DEC | Protocol / capability | Keystone |
|---|---|---|---|
| 1 | 056 | HTTP flagship gap (configured-client consumer + Flask-AppBuilder) | held (HTTP coverage add) |
| 2 | 057 | **MCP** (`mcp::<tool>`) — the headline | **PROVEN** (zero surfacing diff) |
| 3 | 058 | **registry dispatch** (`registry::<id>::<key>` + `::*` wildcard) | **PROVEN** |
| 4 | 059 | **DI/ORM tail** — `INJECTS`/`PERSISTS_TO` + `DbTable` node + `trace` ext | the **one** DEC'd new-node exception |
| 5 | 060/061 | **gRPC** (`grpc::<Svc>/<Method>`) + **messaging** (`topic::`/`queue::`) | held |
| 6 | 062 | framework breadth (NestJS + JAX-RS providers) | held (HTTP coverage add) |

The **keystone** (DEC-055(D)): every new protocol reuses the `Endpoint` node so
`trace` / `serve --ui` / the HOTPATHS `## Cross-stack routes` section light up for
free — the per-protocol git diff touches only `contracts/` + `registry.py` + tests
(MCP and registry-dispatch are the strict zero-surfacing-diff proofs; the DI/ORM
tail is the **one** sanctioned exception, adding the `DbTable` node + extending
`trace`). Verified per step via byte-identical goldens and the fixture e2es.

## §4.9 gate — local items (all green)

- `pytest` green (705 → +5 Step 6) · `ruff check`/`format` clean.
- Every new edge class is **graph-only** → the 5 golden artifacts are
  **byte-identical** across the arc (the golden fixtures carry no
  MCP/dispatch/gRPC/messaging/DI/NestJS/JAX-RS markers).
- `AGENT_BRIEF.md ≤ 5 kb` unchanged.
- Per-protocol fixture e2es prove the join + the honest confidence split (below).

## Per-protocol confidence model (proven on the fixtures)

| protocol | EXTRACTED | INFERRED | AMBIGUOUS / dropped |
|---|---|---|---|
| MCP | `call_tool("x")` ↔ `@mcp.tool(name="x")` literal+unique | — | `call_tool(var)` → **dropped** (never guessed) |
| registry | — | literal-key dispatch → 1 handler | dynamic-key → **AMBIGUOUS-all** (capped fan-out) |
| DI | concrete-type injection | interface → single intra-repo impl | interface → multiple impls → **AMBIGUOUS-all** (mirrors `NoUniqueBeanDefinition`) |
| ORM | literal `__tablename__`/`@Table(name=)` | convention-derived table name | — |
| gRPC | stub↔servicer (`.proto` spec-backed) | — | — |
| messaging | unique subscriber + literal channel | — | several subscribers on a channel → **AMBIGUOUS** fan-out |

## Real-repo acceptance (runnable; the remaining gate items)

The fixture e2es prove each join + confidence rule; the real-repo runs are the
final §4.9 evidence, recorded here as they land:

- **Superset** — Step 1 (`SupersetClient` + Flask-AppBuilder → `ROUTES_TO`, 8/9 → 9/9)
  + Step 4 (SQLAlchemy `__tablename__` → `PERSISTS_TO`).
- **NousResearch/hermes-agent** — Step 2 (MCP `HANDLES`/`CALLS_ENDPOINT`/`ROUTES_TO`
  against its 186 `ClientSession` / 27 `FastMCP` / ~18 `@mcp.tool()`) + Step 3
  (registry dispatch over the ~3,025 dispatch lines). The v0.4 finding's predictions,
  now testable.
- **spring-petclinic** — Step 4 (`@Autowired` + `@Entity`/`@Table` → the DI/ORM tail
  reaching a `DbTable`).
- **grpc-python route_guide** + **rabbitmq-tutorials** — Step 5.
- **nestjs/nest** sample + **eclipse-ee4j/jersey** examples — Step 6.

An honest single-repo shortfall (reported, never fabricated) is an acceptable
gate-pass with the gap promoted to the next arc — the v0.4 → v0.5 pattern.

## Deferred (honest, logged for v0.6+)

- **Django** route provider (decoupled `urls.py`→view table needs cross-file view
  resolution — DEC-062).
- gRPC Go/Java servicers + stubs; package-qualified `mcp::<server>::<tool>` /
  `grpc::<pkg>.<Svc>` keying; Redis/NATS/SNS-SQS messaging; NestJS/Angular/Guice DI;
  TypeORM/Prisma ORM; `PROVIDES` edge; FK `RELATES_TO` table-to-table edges.
- True multi-repo federation (the unmatched `CALLS_ENDPOINT` is its seam — its own arc).
