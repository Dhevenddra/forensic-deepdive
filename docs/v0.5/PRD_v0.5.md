# PRD_v0.5.md — "Cross-Boundary Protocols" (the contract)

> The implementation contract for v0.5. Binds with `CLAUDE.md`; the operating mode is
> `KICKOFF_v0.5.md`; the evidence dossier is `research_v0.5.md` (cited here as *research §N*,
> mapping to its seven Key-Findings sections). `DECISIONS.md` ends at **DEC-054**; v0.5 starts
> at **DEC-055**. Read §0–§4 fully; §5–§10 are scoped-beyond + invariants + forward-compat.
>
> **Calibration:** ~1.5–2× the pre-drafted DEC count (DEC-055→DEC-061 are drafted = 7;
> budget ~11–14 actual, ending ~DEC-068). A DEC for every non-trivial choice, as always.

---

## §0 — Context, and what v0.5 is

v0.4 shipped at **8/9 §4.9 gate green** (DEC-054). Its real achievement was not HTTP `ROUTES_TO` —
it was proving **DEC-043's protocol-agnostic spine**: a `Contract(role, contract_id, symbol_id,
confidence, via, evidence)` record, grouped by a per-protocol `KeyBuilder`, joined by a
**protocol-blind** `base.join()`, materialized as an `Endpoint` node (PK = `contract_id`, carries a
`protocol` property) + `HANDLES` / `CALLS_ENDPOINT` / `ROUTES_TO` (the last carrying `via` +
`confidence`). HTTP was merely the **first instance**. The gRPC (`grpc::<pkg>.<Svc>/<Method>`) and
topic/queue/event key-builders sit in `registry.py` as **visible `NotImplementedError` stubs** —
the seams the abstraction was built to fill.

**So v0.5 builds almost no new architecture. It lights up the seams DEC-043 already cut.** It closes
the one v0.4 shortfall (Superset's custom client/framework → `0 ROUTES_TO`), then extends the same
`Endpoint`/join machinery to **how agents wire themselves** (MCP tool dispatch, tool-registry
dynamic dispatch) and **how services talk** (gRPC/topic, plus the DI/ORM traceability tail) — reusing
the `Endpoint` node so `trace()`, `serve --ui`, and the HOTPATHS `## Cross-stack routes` section work
on every new protocol **for free**. True cross-repo federation and the memory/temporal layers wait
for their own arcs (§5, §6).

### §0.1 — The one-sentence spine (internalize before any code)
> v0.5 doesn't build new architecture — it lights up the seams DEC-043 already cut: close the HTTP
> flagship gap, then extend the same `Endpoint`/join machinery to how agents wire themselves (MCP,
> registry dispatch) and how services talk (gRPC/topic, DI/ORM tail), reusing the `Endpoint` node so
> `trace`/`serve --ui`/emit work on every new protocol for free — while true cross-repo federation and
> the memory/temporal layers wait for their own arcs.

### §0.2 — The differentiator, still accurate (research §2)
GitNexus remains **PolyForm-Noncommercial 1.0.0** (commercial use prohibited; we are Apache-2.0) and
their issue **#306** ("Cross-Repo HTTP API Bridge") is **still Open as of June 2026** — they capture
call chains *within* each repo but lose the HTTP boundary at `fetch('/api/login')` → backend route.
forensic-deepdive is the only one of the two that ships a materialized cross-boundary join + an
OpenAPI codegen shortcut + per-edge provenance. v0.5 widens that lead from one protocol (HTTP) to
**five** (HTTP, MCP, registry-dispatch, gRPC, messaging) on the *same* abstraction — depth, not a
bag of bespoke linkers. The headline new edge is **MCP**: the project exists to give *agents*
forensic understanding of code, and hermes-agent proved the static layer is **blind to how agents
actually work** (186 `ClientSession` + 27 `FastMCP` + ~3,025 dynamic-dispatch lines → **1** internal
`ROUTES_TO` across 19,375 symbols). "Maps the code" → "maps how the agent works" is the v0.5 story.

---

## §1 — THE KEYSTONE DESIGN CALL (lead with this; it shapes every step)

**Reuse the `Endpoint` node for every new protocol. Do NOT invent `Tool`/`Service`/`Channel` node
types.** `Endpoint` already carries a `protocol` property and `ROUTES_TO` already carries `via`. The
surfacing layer — `trace()` (`mcp_server/server.py`), the HOTPATHS `## Cross-stack routes` section
(`emit/hotpaths_md.py`), and `serve --ui`'s `ROUTES_TO` highlighting (`serve/graph_api.py`) — all
query `Endpoint`/`HANDLES`/`CALLS_ENDPOINT`/`ROUTES_TO` **generically, with no `protocol='http'`
filter**. Therefore:

- An MCP tool modeled as `Endpoint(protocol='mcp', contract_id='mcp::<tool>')` with `via='mcp'` edges
  **lights up `trace`, emit, and the UI with zero changes to the surfacing layer.**
- A registry-dispatch site modeled as `Endpoint(protocol='registry', contract_id='registry::<id>::<key>')`
  does the same — and the dynamic-key fan-out reuses **DEC-047's `match_keys` wildcard mechanism**
  (a dynamic dispatch key matches `registry::<id>::*` → AMBIGUOUS-all to every registered handler).
- A gRPC method `Endpoint(protocol='grpc', contract_id='grpc::pkg.Svc/Method')`, a Kafka topic
  `Endpoint(protocol='topic', contract_id='topic::<name>')` — same.

**The only per-protocol work is a `KeyBuilder` + a provider extractor + a consumer extractor.** This
is the single biggest leverage point in v0.5 and it is invisible from outside the repo. If you find
yourself adding a `protocol` branch to `trace`/emit/`serve`, **stop** — the abstraction already
handles it; the branch is the smell.

**The one genuine new-node exception is the DI/ORM tail (§3.4):** `INJECTS`/`PROVIDES` are
`Symbol→Symbol` edges (the `EXTENDS`/`IMPLEMENTS` family, not the `Endpoint` family), and
`PERSISTS_TO` targets a minimal new **`Table`** node (`PK = table::<name>`) because a persisted
table is genuinely not an endpoint. That exception is deliberate and DEC'd (DEC-059); it is **not**
license to invent `Tool`/`Service` nodes for the protocols above.

---

## §2 — Scope decision (DEC-055, write it FIRST after the session-start protocol)

**DEC-055 records the v0.5 scope verdict** so later DECs don't relitigate it:

**(A) The spine = "extend the `CrossBoundaryEdge` abstraction past HTTP," MCP-led.** Framework
breadth folds in as a *coverage track* (§3.6), not a tentpole. Agent-dispatch (MCP + registry) is the
differentiating headline.

**(B) "Memory" is NOT the spine — it splits into three lanes, each assigned:**
- *(i) incremental / persistent graph update* → **v1.0** (PRD §7; DEC-051's line-free `node_id` was
  laid as its no-migration seam — pulling it forward wastes that sequencing).
- *(ii) temporal / Graphiti* → **opt-in-later** (gated behind DEC-005's 2-of-5 threshold, carries LLM
  cost — not a tentpole, not pure-static).
- *(iii) agent-facing write-back* → **already exists** (`JsonlInsightStore`, `record_insight` /
  `recall_insights`, DEC-019, live in `mcp_server/server.py`). The only v0.5-sized win is **hardening**
  (portable git-ref storage + a JSONL→SQLite index) — a small additive enhancement (§5), explicitly
  **not** the headline.

**(C) Federation depth: the lighter within-repo / within-monorepo service-to-service join is in v0.5's
reach** (§3.5 — gRPC/topic are just more `CrossBoundaryEdge` instances; the Java HTTP clients already
pre-staged service-to-service). **True multi-repo federation** (one `Endpoint` shared across repo
boundaries — frontend in repo A → backend in repo B) is **its own later arc** (§6): it needs a repo
registry, cross-repo `node_id` namespacing, and a manifest escape-hatch for naming mismatches — new
architecture. The `Endpoint` node is already its seam (an unmatched `CALLS_ENDPOINT` is the honest
federation hook), but the machinery is deferred.

DEC-055 also re-affirms the §8 invariants apply unchanged.

---

## §3 — The build (six steps, in dependency order — do not reorder)

Each step: *what · the DEC · implementation depth · confidence rules · acceptance repo · deferred.*
The build order is **1 → 2 → 3 → 4 → 5 → 6**. Step 1 turns the gate **8/9 → 9/9** and is the warm-up;
Steps 2–3 are the headline (agent dispatch); Step 4 pays a committed debt; Steps 5–6 widen coverage.

### §3.1 — Step 1: Close the flagship gap (DEC-056) — **start here**

**What.** v0.4 scored `0 ROUTES_TO` on Superset from two independent custom-abstraction gaps
(DEC-054): the frontend calls its API only through a `SupersetClient.get/post/put/delete({ endpoint })`
wrapper (**252 call sites**, matched by none of the seven raw fetch/axios consumer extractors → 1
`CALLS_ENDPOINT`), and the backend is **Flask-AppBuilder** (`ModelRestApi`/`@expose`, **1 of 276**
spec endpoints located). Close both; land the flagship `ROUTES_TO` graph.

**Implementation depth.**
- **(a) Configured-client consumer extractor** — `contracts/http/consumers/configured_client.py`.
  Generalize the existing axios-object path: `scan.js_object_string_prop` already reads
  `axios({method, url})`. Extend to `<Client>.get/post/put/delete({ endpoint|url|path: '...' , method? })`.
  **The false-positive guard is the SHAPE, not a `SupersetClient` allowlist** (no one-repo hacks):
  fire only when the call is `<recv>.<http-verb>(...)` **and** the first argument is an *object literal*
  with a string-valued `endpoint`/`url`/`path` key. Caller `symbol_id` via `_parent_chain` (the
  load-bearing anti-drift rule). Method from the verb (`.get` → GET) or the object's `method` key.
- **(b) Flask-AppBuilder provider extractor** — `contracts/http/providers/flask_appbuilder.py`.
  Harder than `@app.route` because it is class-/convention-driven. Detect `class X(ModelRestApi)` /
  `class X(BaseApi)` subclasses; route prefix from the class `resource_name`/`base_route` attribute
  (fallback: derive from class name, FAB convention); method routes from `@expose("/path", methods=[...])`.
  **Model it like the existing Spring provider** (class-level prefix + method-level route join already
  lives in `providers/`) — reuse that join shape, don't reinvent it. Marker pre-filter bytes:
  `b"ModelRestApi"` / `b"BaseApi"` / `b"@expose"` / `b"flask_appbuilder"`.

**Confidence rules.** Literal `endpoint` string → EXTRACTED-grade consumer; templated → INFERRED
(DEC-046 unchanged). FAB provider routes are syntactic facts → EXTRACTED-grade provider; the
class-name-derived prefix fallback (when no explicit `base_route`) is INFERRED. `ROUTES_TO`
confidence stays the join's job (DEC-047): unique-literal-both-sides → EXTRACTED.

**Acceptance repo.** **Superset** (both numbers already measured: 252 client calls, 275
documented-but-unlocated handlers). Gate: `ROUTES_TO` materializes on Superset (8/9 → 9/9), with an
honest EXTRACTED/INFERRED split, `trace()` walking the chain, no fabricated joins.

**Deferred.** Non-object-literal configured-client calls (positional URL string only — falls back to
the existing fetch/axios path); FAB nested API namespaces beyond one prefix level.

### §3.2 — Step 2: MCP as a `CrossBoundaryEdge` protocol (DEC-057) — **the headline**

**What.** Model MCP tool dispatch as the next protocol instance: a `@mcp.tool()` handler is a
*provider*, a `ClientSession.call_tool("name")` is a *consumer*, joined through an
`Endpoint(protocol='mcp')`. Pure-static — **never run the agent or hit a live MCP server** (DEC-009).

**Implementation depth (research §1 — zero new runtime deps; `mcp` 1.27.2 / `fastmcp` 3.4.0 are
detection targets, not imports).**
- New subpackage `contracts/mcp/` mirroring `contracts/http/`: `register.py`
  (`register_mcp_extractors()`, idempotent, called from `ContractPhase.run`), `providers/mcp_tools.py`,
  `consumers/client_session.py`. Reuse `contracts/http/scan.py`'s re-parse-with-marker-prefilter
  pattern (markers: `b"FastMCP"`, `b"@mcp.tool"`, `b".tool("`, `b"call_tool"`, `b"Server("`,
  `b"list_tools"`).
- **Key-builder** — register a `"mcp"` protocol in `registry.py`: `mcp_contract_id(tool_name)` →
  `mcp::<tool>`. **Keying decision (RESOLVED, research §1): key on the bare tool name.** A
  `ClientSession` is 1:1 with one transport/server so server identity *is* statically recoverable, but
  only via dataflow (binding `session` back through the `async with` to a server_params/URL), and MCP
  has **no official cross-server name-collision standard** (SEP-986 is only "SHOULD be unique within a
  server"). Bare-tool keying is a single-AST-node, pure-static extraction that makes both sides share
  one literal namespace → EXTRACTED joins with no inference. **Normalize separators before keying**
  (`. / -` → `_`) because model APIs sanitize names and multi-server clients prefix them
  (`mcp_<server>_<tool>`); normalizing avoids false-negative joins. Treat `mcp::<server>::<tool>`
  server-qualified keying as a **future INFERRED enhancement** once session→server dataflow exists —
  not a v0.5 requirement (§10).
- **Provider extractor** (`providers/mcp_tools.py`): detect `@mcp.tool()` / bare `@mcp.tool` /
  `@mcp.tool(name="x")` / `@server.tool(...)` decorated functions, and the low-level `Server(...)` +
  `@server.call_tool()` shape (tool names are string literals inside the handler body — a dispatch
  table, hand to Step 3's detector). Tool name = the `name=` kwarg when present (**authoritative**),
  else the function name. Handler `symbol_id` via `_parent_chain`. Also detect `FastMCP("name")`
  construction to attribute server identity as an `Endpoint` property (not the key).
- **Consumer extractor** (`consumers/client_session.py`): detect `await session.call_tool("name",
  arguments=...)` (and `.call_tool(name="x", ...)`). Tool name from the literal first/`name=` arg →
  `CALLS_ENDPOINT(via='mcp')`. Caller `symbol_id` via `_parent_chain` (enclosing named callable, else
  `<module>`). `base.join` is reused **unchanged**.

**Confidence rules.** `@mcp.tool(name="x")` ↔ `call_tool("x")` both literal, unique → **EXTRACTED**.
`call_tool(variable)` (name not statically resolvable) → the consumer is unjoinable on a literal key;
record it against the wildcard `mcp::*` only if a bounded candidate set exists, else **drop** (DEC-037
posture) — never guess one. Derived/f-string names → **INFERRED**.

**Acceptance repo.** **NousResearch/hermes-agent** (MIT, already cloned). Gate: `HANDLES` /
`CALLS_ENDPOINT` / `ROUTES_TO` materialize against its `ClientSession` (186), `FastMCP` (27), and
`@mcp.tool()` (~18) usage; `trace('<agent-entry>', downstream)` walks **agent → MCP tool → handler**;
the HOTPATHS section and `serve --ui` show the `mcp` edges **with no surfacing-layer change** (the
keystone proof). Use a `--depth 1` clone caveat note for the empty archaeology layer (as the v0.4
hermes finding did).

**Deferred.** Server-qualified keying (`mcp::<server>::<tool>`, INFERRED, needs session→server
dataflow); MCP *resources*/*prompts* (tools only in v0.5); SEP-1575 tool `version` as anything beyond
an `Endpoint` property (never part of the key — research §1 caveat).

### §3.3 — Step 3: Tool-registry dynamic dispatch (DEC-058) — **the honest-confidence hard part**

**What.** Model the `registry[name]()` / decorator-registration / `getattr` dispatch pattern — the
~3,025 lines hermes showed, the pattern *every* agent framework uses — as a **bounded, confidence-
tagged fan-out**. This is where the DEC-025/037 "bound-or-drop, never guess-one" philosophy earns its
keep.

**Implementation depth (research §3).** Model dispatch through the `Endpoint` node too (keystone):
`Endpoint(protocol='registry', contract_id='registry::<registry-id>::<key>')`.
- **Registration sites → providers (`HANDLES`).** Detect: `@register(...)` / `@registry.register("name")`
  decorators; `registry[name] = fn` dict assignment; dict-literal `TOOLS = {"name": fn, ...}` mapping
  names→callables. Build a `name → handler symbol_id` table per registry object. Registry identity
  (`<registry-id>`) = the registry variable's `qualified_name`. Handler `symbol_id` via `_parent_chain`.
- **Dispatch sites → consumers (`CALLS_ENDPOINT`).** Detect: `registry[key]()`, `TOOLS[name](...)`,
  `getattr(obj, name)()`, `registry.get(key)()`. Key = literal when present, else the dispatch
  variable (dynamic).
- **The fan-out, via DEC-047's `match_keys` (reuse, do not reinvent):** a **literal-key** dispatch
  matches the exact `registry::<id>::<key>` → one provider → **INFERRED** (the registry indirection is
  real but the binding is a name match, not a direct call). A **dynamic-key** dispatch matches the
  wildcard `registry::<id>::*` → **every** registered handler as **AMBIGUOUS-all** (emit all, never
  collapse to one guess). **Cap the fan-out** (reuse the `trace`/`flow` BFS cap) so a giant registry
  can't explode the graph; when capped, surface the cap honestly (`...and N more`).

**Confidence rules.** Dict-literal/decorator registration with a literal-key dispatch → INFERRED.
Dynamic-key dispatch over multiple registered handlers → AMBIGUOUS-all. A registration whose name is
itself dynamic (computed) → the handler joins the registry but is unkeyed → only reachable via the
wildcard fan-out.

**Acceptance repo.** **hermes-agent** again (the ~3,025 dispatch lines). Gate: a representative
registry's registration + dispatch sites produce a bounded AMBIGUOUS fan-out `trace` can walk; the cap
holds on the largest registry; determinism (sorted fan-out).

**Deferred.** Cross-module registry population where the registry is imported and mutated in N files
(best-effort: union the registrations we can see, note incompleteness); class-method registries via
metaclass magic.

### §3.4 — Step 4: The DI/ORM traceability tail (DEC-059) — **a committed promise**

**What.** `trace()`'s `boundary` field literally says *"the service→repository→table (DI/ORM) tail is
v0.5."* Deliver it. New edges: **`INJECTS`/`PROVIDES`** (`Symbol→Symbol`) and **`PERSISTS_TO`**
(`Symbol→Table`), then extend `trace`'s `_calls_tail` to walk past the handler:
`handler →CALLS→ service →INJECTS(resolve to impl)→ impl →CALLS→ repository →PERSISTS_TO→ table`.

**Implementation depth (research §4).**
- **DI extraction** (`static/injection.py`, a new sibling to `static/inheritance.py`): detect
  - Spring `@Autowired` (field/setter/ctor) + constructor injection (single public ctor args
    auto-wired);
  - FastAPI `Depends(callable)` in param defaults and `Annotated[T, Depends(provider)]`;
  - NestJS `@Injectable()` class + constructor-param-type injection + `@Inject('TOKEN')` /
    `@InjectRepository(X)`;
  - Angular/Guice/Dagger constructor-param-type + `@Inject` (same shape family).
  Edge: `INJECTS` from the injection-site Symbol to the provider/impl Symbol; `PROVIDES` is its
  inverse for the registered provider where useful.
- **Interface→impl resolution = Spring's own ladder (research §4):** annotation/ctor injection of a
  concrete type → **EXTRACTED**; injection of an interface with **exactly one** intra-repo impl →
  **INFERRED**; interface with **multiple** impls → **AMBIGUOUS-all** (Spring itself fails closed here
  with `NoUniqueBeanDefinitionException` — we mirror it: emit all candidates). `@Qualifier`/`@Primary`
  disambiguation upgrades a multi-impl case to INFERRED when resolvable.
- **ORM extraction** (`static/persistence.py`): minimal new **`Table`** node (`PK = table::<name>`,
  property `orm`, `framework`). Detect:
  - SQLAlchemy `class X(Base)` with `__tablename__ = "users"` (+ `Column`/`mapped_column`);
  - JPA `@Entity` + `@Table(name="...")`;
  - TypeORM `@Entity()` / `@Entity("name")`;
  - Django `class Meta: db_table` (else derived `app_model`);
  - Prisma `@@map("table")`.
  Edge: `PERSISTS_TO` from the model Symbol to the `Table` node. Literal `__tablename__`/`@Table(name=)`
  → EXTRACTED; derived/convention table name → INFERRED.
- **`trace` extension:** extend `_calls_tail` to traverse `INJECTS` (resolving interface→impl by the
  ladder above) and terminate at `PERSISTS_TO → Table`. **Update the `boundary` note** once the tail
  lands (remove the "v0.5" deferral text).

**Acceptance repos.** **spring-petclinic** (Apache-2.0; canonical `@Autowired`/`@Entity`/`@Table`) for
the JPA + DI path; **Superset** (SQLAlchemy `__tablename__`) for the Python PERSISTS_TO path. Gate:
`trace('<controller-method>', downstream)` reaches a `Table` node through the
service→inject→repo→table chain with the honest confidence ladder; multi-impl injection emits
AMBIGUOUS-all.

**Deferred.** Bean-config-driven providers (`@Configuration`/`@Bean` factories) beyond annotation/ctor;
SQLAlchemy `Table()` imperative mapping; relationship/foreign-key edges between tables (a `RELATES_TO`
table-to-table edge is a future arc — v0.5 stops at model→table).

### §3.5 — Step 5: Service-to-service — the light federation (DEC-060)

**What.** Wire the two stubbed key-builders. gRPC and messaging are **just more `CrossBoundaryEdge`
instances** within a repo/monorepo (the Java HTTP clients already pre-staged HTTP service-to-service;
this adds the non-HTTP transports). Same `Endpoint` reuse → `trace`/UI/emit free.

**Implementation depth (research §5).**
- **gRPC** (`contracts/grpc/`): `Endpoint(protocol='grpc', contract_id='grpc::<pkg>.<Svc>/<Method>')`.
  Provider = a `.proto` `service X { rpc M(Req) returns (Resp) }` definition; consumer = the
  per-language generated-stub **call site** (`stub.Method(request)` where `stub =
  <pkg>_pb2_grpc.<Svc>Stub(channel)` in Python; `client.Method(ctx, req)` in Go; generated `Grpc`
  classes in Java). Mark proto-defined endpoints `spec_backed=True` (the `.proto` *is* the contract —
  the same posture as OpenAPI in DEC-048) so stub-call joins are **EXTRACTED**.
  - **`.proto` parsing — DEPENDENCY DECISION (research §5; needs its own DEC, e.g. DEC-061):** the
    **zero-dep floor is a tree-sitter-proto grammar or a tight regex** extracting `service`/`rpc`
    nodes + the call-site `<Svc>Stub`/`stub.Method(` shapes — **no new runtime dep**, covers the
    EXTRACTED subset. Full-fidelity AST via `proto-schema-parser` (MIT, healthy) is viable **but pulls
    `antlr4-python3-runtime>=4.13.0`** → if taken, it goes behind an **opt-in `[proto]` extra with its
    own DEC**, exactly as OpenAPI YAML went behind `[openapi]`+pyyaml (DEC-048). **Default to the
    zero-dep floor for v0.5; only add `[proto]` if a real repo shows the floor missing real RPCs.**
- **Messaging** (`contracts/messaging/`): `Endpoint(protocol='topic'|'queue'|'event',
  contract_id='topic::<name>' | 'queue::<name>' | 'event::<name>')`. Provider = a
  publisher/subscriber declaration; consumer = the counterpart. Shapes:
  - Kafka `producer.send('topic', ...)` / `@KafkaListener(topics="...")` → `topic::`;
  - RabbitMQ/pika `channel.basic_publish(routing_key='q')` / `basic_consume(queue='q')` /
    `queue_declare('q')` → `queue::`;
  - Redis `publish('chan')` / `subscribe('chan')`, NATS `nc.publish/subscribe(subject)`,
    AWS SNS/SQS boto3 `.publish(TopicArn=)`/`.receive_message(QueueUrl=)` → `event::`/`topic::`.
  Name = string literal → EXTRACTED; constant/config reference → INFERRED; multiple candidate
  names → AMBIGUOUS. **publish↔subscribe is the join** (publisher = provider-ish, subscriber =
  consumer-ish — pick one orientation in the DEC and hold it; `ROUTES_TO` then reads
  publisher→subscriber).

**Acceptance repos.** gRPC: `grpc/grpc-go` `examples/route_guide` (Apache-2.0) or
`grpc/grpc` `examples/python/route_guide` (proto + stubs + call sites). Messaging:
`rabbitmq/rabbitmq-tutorials` (pika pub/sub) or a Spring `@KafkaListener` sample. Gate: gRPC
`ROUTES_TO` joins a stub call to its `.proto` rpc (EXTRACTED, spec-backed); a publish joins a subscribe
on the same topic; determinism; no new **base-env** runtime dep (proto floor) — and if `[proto]` is
taken, loud degradation when absent (DEC-048 pattern).

**Deferred.** OpenAPI-3 `servers[].url` analog for proto packages; gRPC streaming-direction nuance;
cross-language stub variance beyond Python/Go/Java; messaging consumer-group/partition semantics.

### §3.6 — Step 6: Framework breadth (DEC-061+) — the coverage track

**What.** The DEC-045 §7 deferrals, each a **pure addition to `contracts/http/providers/`** (no new
machinery) to reach GitNexus route-detection parity while `ROUTES_TO` keeps the cross-boundary
differentiator. Treat as a continuous backfill, **not a tentpole** — each is a small commit, possibly
sharing one DEC.

**Implementation depth (research §6).**
- **NestJS** (`providers/nestjs.py`): `@Controller('prefix')` class + method decorators
  `@Get('path')`/`@Post()`/`@Put(':id')`/`@Delete()`. Route = controller-prefix + method-path.
  **Guard: only treat method decorators as routes when enclosed by `@Controller`** (the same
  enclosing-class guard as Spring/JAX-RS). `RouterModule.register([{path, module}])` adds module
  prefixes (best-effort).
- **Django** (`providers/django.py`): `urls.py` `path('route/', view)` / `re_path(r'^...$', view)` /
  `include('app.urls')` (nested prefixes); function- and class-based views (`.as_view()`); DRF
  `router.register(r'prefix', ViewSet)`.
- **JAX-RS / Jakarta REST** (`providers/jaxrs.py`): `@Path("resource")` class + `@GET`/`@POST`/`@PUT`/
  `@DELETE` methods (`jakarta.ws.rs.*`); `@ApplicationPath` app prefix; class `@Path` + method `@Path`
  concatenate (enclosing-class guard).

**Acceptance repos.** NestJS: the `sample/` dir in `nestjs/nest` (MIT) or a `CatsController` scaffold.
Django: DRF tutorial app or `django/django` examples. JAX-RS: `eclipse-ee4j/jersey` examples
(`HelloWorldResource`) or `mkyong/jax-rs`. Gate per framework: provider routes located; where a
matching consumer exists, `ROUTES_TO` joins with the honest split.

**Deferred.** Framework-specific middleware/guard route rewrites; Django class-based generic-view URL
inference beyond `as_view()`.

---

## §4 — Acceptance gate (§4.9 for v0.5)

The project discipline holds: **same abstraction + tests + at least one real repo per step.** Make
findings diffable under `docs/findings/v0.5/`. The gate is green when:

1. **`pytest -x` green; `ruff check`/`format` clean.** (Budget: the v0.4 suite + per-step tests; expect
   the suite to grow well past 645 — the v0.4 release baseline.)
2. **Step 1 — flagship gap closed:** Superset yields `ROUTES_TO` (8/9 → **9/9** on the v0.4 gate),
   honest EXTRACTED/INFERRED split, `trace` walks it, **no fabricated joins**.
3. **Step 2 — MCP protocol:** hermes-agent yields `mcp` `HANDLES`/`CALLS_ENDPOINT`/`ROUTES_TO`;
   `trace` walks agent→tool→handler; **the HOTPATHS section + `serve --ui` show `mcp` edges with ZERO
   surfacing-layer changes** (the keystone proof — verify by `git diff` touching only
   `contracts/` + `registry.py` + tests, not `trace`/emit/`serve` query logic).
4. **Step 3 — registry dispatch:** a bounded AMBIGUOUS fan-out on hermes's registries; the cap holds;
   literal-key → INFERRED, dynamic-key → AMBIGUOUS-all; deterministic ordering.
5. **Step 4 — DI/ORM tail:** `trace` reaches a `Table` node through service→inject→repo→table on
   spring-petclinic (JPA) and Superset (SQLAlchemy); confidence ladder honest; multi-impl →
   AMBIGUOUS-all; the `trace` `boundary` note updated.
6. **Step 5 — service-to-service:** gRPC stub↔`.proto` `ROUTES_TO` (EXTRACTED, spec-backed) on a real
   gRPC repo; publish↔subscribe join on a messaging repo; **no new base-env runtime dep** (proto
   floor), or `[proto]` loud-degrades when absent.
7. **Step 6 — framework breadth:** NestJS/Django/JAX-RS provider routes located on a real repo each;
   `ROUTES_TO` where a consumer exists.
8. **Determinism:** byte-identical artifacts across runs (every new edge class is graph-only — see §8).
9. **AGENT_BRIEF ≤ 5 kb everywhere.**
10. **Findings written** under `docs/findings/v0.5/` with per-protocol confidence splits, the keystone
    "zero surfacing-layer change" diff evidence, and the honest deferrals.

As in v0.4, an honest shortfall on a single repo (reported, not fabricated) is an acceptable
gate-pass with the gap promoted to the next arc — but a *fabricated* join is never acceptable.

---

## §5 — Memory (scoped-beyond; the only v0.5-sized item is optional hardening)

Per DEC-055(B), the three "memory" lanes are assigned and **not** the spine. The **single v0.5-sized
win**, if taken, is hardening lane (iii) — the already-live `JsonlInsightStore` (DEC-019):

- **Optional DEC (low priority, e.g. DEC-062):** portable **git-ref storage** for insights (so the
  agent-written memory travels with the repo) + a **JSONL→SQLite index** for fast `recall_insights`
  at scale. Both already named in the original PRD §5. Pure-static-compatible (no LLM). This is
  additive, optional, and explicitly **not** a headline — take it only if the step-1–6 budget allows.

Lanes (i) incremental/persistent → **v1.0**; (ii) temporal/Graphiti → **opt-in-later** (DEC-005
threshold, LLM cost). Do not pull either forward.

---

## §6 — Federation (deferred to its own arc)

True multi-repo federation (one `Endpoint` shared across repo boundaries) is **not** v0.5. The seam is
already laid: an unmatched `CALLS_ENDPOINT → Endpoint` (no `HANDLES`) is exactly where repo A's
frontend call waits for repo B's backend handler. The deferred machinery: a **repo registry**,
**cross-repo `node_id` namespacing** (the DEC-051 line-free id is the seam), and a **manifest
escape-hatch** for naming mismatches (GitNexus's "groups" concept). Record this in DEC-055(C) so it is
a visible future arc, not a forgotten gap.

---

## §7 — v1.0 endgame seams (what v0.5 lays at near-zero cost)

Consistent with v0.4 laying three seams (stable IDs, the `Endpoint` join node, single-call `trace`),
v0.5 lays:
- **Protocol generality proven across 5 instances** — the `KeyBuilder`/`Endpoint` abstraction is no
  longer "HTTP + stubs"; it is demonstrably multi-protocol, which is the federation + IDE-context
  substrate.
- **The DI/ORM tail + `Table` node** — the data-layer reach an IDE-grade "trace this request to the
  table it writes" needs.
- **Agent-dispatch modeling (MCP + registry)** — the thing that makes the tool *itself* useful to the
  agents it serves, and the seam for any future "explain this agent" surface.

The IDE remains the post-v1.0 endgame. Lay the seams clean; don't build on them yet.

---

## §8 — Invariants the v0.5 PRD carries forward (preserve verbatim; non-negotiable)

1. **One abstraction, not many.** Every new protocol is a `KeyBuilder` + extractors over the *same*
   `Endpoint`/`base.join` machinery. If `trace`/emit/`serve` need a `protocol==` branch, you've
   generalized wrong.
2. **Reuse the `Endpoint` node** for MCP, registry-dispatch, gRPC, messaging — no `Tool`/`Service`
   node types. (The DI/ORM `Table` node is the single DEC'd exception, §3.4.)
3. **Every new edge class is graph-only → the 5 golden fixtures emit no MCP/dispatch/gRPC/messaging/DI
   markers, so the 5 artifacts stay byte-identical** (the same contract that held for `ROUTES_TO` in
   v0.4). `AGENT_BRIEF ≤ 5 kb` unchanged.
4. **Pure-static floor (DEC-009) is non-negotiable.** MCP/dispatch/DI/proto extraction is **AST-only**
   — never by executing the agent, hitting a live MCP server, running protoc, or any network/LLM.
5. **Confidence taxonomy stays sacred (DEC-015).** Dynamic dispatch is AMBIGUOUS/INFERRED, **never**
   silently EXTRACTED. Multiple candidates → emit **all**, never pick one (DEC-025/037). EXTRACTED only
   for spec-backed (`.proto`/OpenAPI) or unique-literal-both-sides.
6. **No un-DEC'd runtime dep.** A `.proto` AST parser (`proto-schema-parser`+antlr4) needs its own DEC
   + opt-in `[proto]` extra, exactly like `[openapi]`+pyyaml. The base-env floor stays zero-dep.
7. **`symbol_id = <rel_path>::<qn_local>` via `_parent_chain`, or the edge is filtered against
   `valid_symbol_qns`.** This is the single most common way a new extractor silently emits nothing —
   reuse `_parent_chain`, never re-derive the qn.
8. **Run-time idempotent extractor registration** (not import side-effects), per DEC-045 — each new
   protocol's `register_<proto>_extractors()` is called in `ContractPhase.run`.
9. **Determinism via collect-then-sort** on every new pass; the fan-out cap (Step 3) and any
   enumeration sorted by stable keys.
10. **The 9 MCP tools + the 5-artifact contract.** New protocols surface through the *existing*
    `trace` tool and the *existing* HOTPATHS `## Cross-stack routes` section — **never** a 10th tool or
    a 6th artifact for a new protocol. (A genuinely new *capability* — not a protocol — may warrant a
    tool, with the coupling rule fired, but that is not in v0.5 scope.)

---

## §9 — DEC budget & calibration

Pre-drafted (write each as you reach its step):
- **DEC-055** — v0.5 scope decision (§2: spine = abstraction-extension MCP-led; Memory lanes;
  federation depth). **Write first.**
- **DEC-056** — Step 1: configured-client consumer + Flask-AppBuilder provider (the flagship gap).
- **DEC-057** — Step 2: MCP as a `CrossBoundaryEdge` protocol (`mcp::<tool>` keying, the keystone
  proof).
- **DEC-058** — Step 3: tool-registry dynamic dispatch (`registry::` Endpoint + wildcard fan-out).
- **DEC-059** — Step 4: DI/ORM tail (`INJECTS`/`PROVIDES`/`PERSISTS_TO` + the `Table` node + `trace`
  extension).
- **DEC-060** — Step 5: gRPC + messaging key-builders (the publish/subscribe orientation call).
- **DEC-061** — `.proto` parsing strategy (zero-dep floor vs opt-in `[proto]` extra) **and/or** the
  framework-breadth providers (NestJS/Django/JAX-RS). Likely splits.

Expect ~1.5–2× → additional DECs are normal and *expected* for: the `registry`-as-Endpoint modeling
choice; the `Table` node introduction; the MCP separator-normalization rule; per-framework provider
nuances; any documented PRD divergence (the DEC-035/037/051 precedent — diverge honestly, in a
superseding entry, never silently). Budget DEC-055→~DEC-068.

---

## §10 — Forward-compat notes (cheap seams, do not build on them)

- **`mcp::<server>::<tool>` server-qualified keying** — wired conceptually (session is 1:1 with a
  server), realized later as an INFERRED enhancement once session→server dataflow exists. v0.5 ships
  bare-tool keying; the `Endpoint` carries server identity as a property so the upgrade is additive.
- **`RELATES_TO` table-to-table edges** — the `Table` node (§3.4) is the seam; FK/relationship edges
  are a future data-layer arc.
- **Cross-repo `Endpoint` sharing** (§6) — the unmatched `CALLS_ENDPOINT` is the federation hook; the
  registry/namespacing machinery is its own arc.
- **`.proto`/GraphQL-SDL/tRPC as spec-backed contracts** — gRPC's `.proto` joins OpenAPI as a
  spec-backed source; GraphQL SDL / tRPC routers are the next codegen-shortcut candidates after v0.5.

*The differentiator is depth on one abstraction. Five protocols on the same `Endpoint`/join machinery
beats five bespoke linkers — build each protocol as an instance, prove the keystone's "zero
surfacing-layer change," and the breadth follows without going shallow.*
