# research_v0.5.md — evidence dossier for "Cross-Boundary Protocols"

> The §refs cited by `PRD_v0.5.md` and `KICKOFF_v0.5.md` map to §1–§7 below. Current as of June 2026
> (knowledge cutoff Jan 2026 + live search). Every dependency that would breach the no-un-DEC'd-dep
> floor is flagged. Favor the concrete API/decorator/call shapes — they are what the extractors parse.

## §0 — TL;DR
- **MCP fits the v0.4 abstraction with ZERO new runtime deps.** The Python SDK (`mcp` 1.27.2, May 29
  2026, MIT, ≥3.10, namespace `mcp.server.fastmcp`) and standalone `fastmcp` (3.4.0, Jun 3 2026,
  Apache-2.0, ≥3.10) expose statically-detectable `@mcp.tool()` / `@mcp.tool(name=)` / `FastMCP(...)` /
  `Server`+`@server.call_tool` provider shapes and `ClientSession.call_tool("name", args)` consumer
  shapes. A `ClientSession` is 1:1 with one transport/server, so server identity *is* recoverable — but
  bare-tool keying (`mcp::<tool>`) is the right v0.5 default.
- **Pure-Python `.proto` parsing exists but pulls antlr4** → gRPC AST parsing goes behind an opt-in
  `[proto]` extra with its own DEC; a zero-dep tree-sitter/regex floor covers the EXTRACTED subset.
- **GitNexus is still PolyForm-Noncommercial; issue #306 (cross-boundary HTTP) is still Open** → the
  Apache-2.0 + the-only-shipped-cross-boundary-join differentiator holds.

## §1 — MCP as a static contract protocol (the keystone)
Two surfaces share the shapes you detect: official SDK `mcp` **1.27.2** (May 29 2026, MIT, ≥3.10,
`mcp.server.fastmcp`) and standalone `fastmcp` **3.4.0** (Jun 3 2026, Apache-2.0, ≥3.10), which the
fastmcp PyPI page says "powers 70% of MCP servers" and is "downloaded a million times a day."

**Provider (→ `HANDLES`):**
- `FastMCP("name")` / `FastMCP("name", json_response=True, host=, port=)` — server construction.
  Verbatim quickstart: `from mcp.server.fastmcp import FastMCP` / `mcp = FastMCP("Demo")` / `@mcp.tool()`.
- `@mcp.tool()` and bare `@mcp.tool` (fastmcp 3.x) — function name = default tool name.
- `@mcp.tool(name="get_info")` — explicit name **wins over the function name**.
- `@mcp.tool(name="x", version="1.0.0")` / `mcp.add_tool(fn, name="x", version=)` — SEP-1575 versioning
  (FastMCP-implemented, proposal-stage in spec). `name` is the key; `version` is a property.
- Low-level `Server("name")` + `@server.list_tools()` / `@server.call_tool()` — tool names are string
  literals inside the handler bodies (a dispatch table → hand to §3). Handlers in
  `Server._request_handlers` keyed `"tools/list"`/`"tools/call"`.

**Consumer (→ `CALLS_ENDPOINT`):**
- `await session.call_tool("tool-name", arguments={...})` on a `ClientSession` — the canonical call
  site; first/`name=` arg is a literal in the vast majority of cases (EXTRACTED), a variable →
  AMBIGUOUS.
- Wiring: `async with stdio_client(params) as (r,w): async with ClientSession(r,w) as session:`
  (stdio); `streamablehttp_client(url)` / `sse_client(url)` (HTTP; SSE deprecated).

**Keying decision — RESOLVED: key on the bare tool name (`mcp::<tool>`).** A `ClientSession` wraps
exactly one transport/server (1:1), so server identity is statically recoverable — *but only via
dataflow* (binding `session` back through the `async with` to a server_params/URL), and MCP has **no
official cross-server name-collision standard** (SEP-986 is only "SHOULD be unique within a server";
Discussion #291 confirms). Multi-server clients prefix the exposed name instead: hermes-agent uses
`mcp_<server>_<tool>` (single underscore, hyphen/dot→underscore), LangChain-JS `mcp__<server>__<tool>`
(double underscore), LangChain-Python `<server>_<tool>` (off by default). **Bare-tool keying is a
single-AST-node, pure-static extraction; both sides share one literal namespace → EXTRACTED with no
inference.** Normalize `. / -` → `_` before keying (model APIs sanitize; multi-server clients prefix) to
avoid false-negative joins. `mcp::<server>::<tool>` is a future INFERRED enhancement (needs
session→server dataflow), not a v0.5 requirement.

**2025–2026 spec changes:** spec now at **2025-11-25** (prior 2025-06-18, 2025-03-26); donated to the
Linux Foundation's Agentic AI Foundation Dec 9 2025. Streamable HTTP is production transport.
**SEP-986** ("tool name format") is in the 2025-11-25 "Major changes": charset `A-Z a-z 0-9 _ - . /`,
1–64 chars, case-sensitive, SHOULD-be-unique-within-server (SDK PR #1655 validates). Model APIs are
stricter (Anthropic `^[a-zA-Z0-9_-]{1,64}$`, OpenAI `^[a-zA-Z0-9_-]+$`) → dotted/slashed names get
underscored in practice. Server metadata moving to `.well-known/mcp` cards (SEP-1649).

**Acceptance: NousResearch/hermes-agent** (MIT) — confirmed live; consumes MCP servers (tools prefixed
`mcp_<server>_<tool>`), serves over stdio via `hermes mcp serve`; 186 `ClientSession`, 27 `FastMCP`,
~18 `@mcp.tool()`.

## §2 — GitNexus current state (differentiator)
- **License unchanged: PolyForm Noncommercial 1.0.0** (commercial use prohibited; we are Apache-2.0).
  Docker packaging is separately GPL-v3, but upstream is Noncommercial.
- **Issue #306** ("Cross-Repo HTTP API Bridge…") opened Mar 16 2026, **still Open** — their graph ends
  at `fetch('/api/login')` and restarts at the backend `@PostMapping`; exactly the gap ROUTES_TO closes.
  No shipped OpenAPI shortcut or ROUTES_TO-equivalent.
- GitNexus IS MCP-native (ships an MCP server, 7 tools + 2 prompts) and has `routes`/`tools`/`orm`
  pipeline phases (so they detect routes + have an ORM phase) but **no cross-boundary protocol join**.
  Ships a vendored `tree-sitter-proto` grammar gated behind `GITNEXUS_SKIP_OPTIONAL_GRAMMARS=1`
  (confirms proto parsing is feasible but treated as heavy/optional).

## §3 — Tool-registry dynamic dispatch shapes
Name→handler table + dispatch shapes to detect (for the AMBIGUOUS bounded fan-out):
- **LangChain/LangGraph:** `@tool` / `@tool("name", return_direct=True)`; list literals `tools=[a,b]`;
  `llm.bind_tools(tools)` / `create_agent(model, tools)`; `MultiServerMCPClient({...}).get_tools()`.
- **OpenAI Agents SDK:** `@function_tool` + `Agent(..., tools=[fn1, fn2])`.
- **CrewAI:** `@tool("Name")` (`crewai.tools`) or `class T(BaseTool)` with `name`/`_run`; `tools=[...]`.
  (Version churn — pin `crewai_tools` 0.32.x.)
- **AutoGen:** function-schema dicts via `llm_config={"functions":[...]}` / `register_function`.
- **MCP SDK low-level:** `Server._request_handlers` dict keyed `"tools/list"`/`"tools/call"`.
- **Generic Python:** `@register(...)` decorators; `registry[name] = fn`; dict-literal
  `TOOLS = {"name": fn}`; dispatch `registry[key]()`, `TOOLS[name](...)`, `getattr(obj, name)()`.
- **Confidence:** dict-literal/decorator registration + literal-key dispatch = EXTRACTED-ish/INFERRED;
  runtime-variable dispatch over multiple registered handlers = AMBIGUOUS-all. hermes: ~3,025 lines.

## §4 — DI / ORM static extraction (the traceability tail)
**DI shapes:** Spring `@Autowired` (field/setter/ctor) + ctor injection (single public ctor auto-wired);
FastAPI `Depends(callable)` / `Annotated[T, Depends(provider)]`; NestJS `@Injectable()` + ctor-param-type
+ `@Inject('TOKEN')` / `@InjectRepository(X)`; Angular/Guice/Dagger ctor-param + `@Inject`.
**Resolution ladder (Spring's own, mirror it):** concrete-type injection = **EXTRACTED**; interface →
single intra-repo impl = **INFERRED**; interface → multiple impls = **AMBIGUOUS-all** (Spring throws
`NoUniqueBeanDefinitionException` "expected single matching bean but found 2" unless `@Qualifier`/
`@Primary` — emit all candidates, mirroring the fail-closed posture).
**ORM entity→table (PERSISTS_TO):** SQLAlchemy `__tablename__ = "users"` (+ `Column`/`mapped_column`);
JPA `@Entity`+`@Table(name=)`; TypeORM `@Entity()`/`@Entity("name")`; Django `class Meta: db_table`
(else derived `app_model`); Prisma `@@map("table")`. Literal name = EXTRACTED; derived = INFERRED.

## §5 — gRPC/protobuf + messaging
**gRPC shape:** `service Greeter { rpc SayHello (HelloRequest) returns (HelloReply) {} }` (provider);
Python stubs in `_pb2_grpc.py` → `GreeterStub`/`GreeterServicer`; **call sites `stub.SayHello(request)`**
where `stub = helloworld_pb2_grpc.GreeterStub(channel)`. Go `pb.NewGreeterClient(conn)` +
`client.SayHello(ctx, req)`; Java generated `GreeterGrpc`. Key `grpc::pkg.Svc/Method`.
**`.proto` parser options:**
- **`proto-schema-parser`** (criccomini, **MIT**, pure-Python, ≥3.9, latest Nov 5 2025, "Healthy"
  maintenance) supports `service`/`rpc`/`stream`, proto2/3+editions — **BUT declares
  `antlr4-python3-runtime>=4.13.0`** (a transitive runtime dep → breaches the floor).
- `proto-parser` (Apache-2.0, sparse); `py-proto-parser` (MIT, pre-alpha).
- **tree-sitter-proto grammars** (mitchellh, Clement-Jean, coder3101, 90-008 **MIT**) — tree-sitter is
  already the parsing substrate → the most architecturally-consistent **zero-dep** path (query
  `service`/`rpc` nodes + call-site `<Svc>Stub`/`stub.Method(`).
- `grpcio-tools`/`protoc` — heavyweight C++ toolchain, wrong for a static floor.
- **RECOMMENDATION:** zero-dep tree-sitter/regex floor for the EXTRACTED subset; scope
  `proto-schema-parser`+antlr4 behind opt-in `[proto]` + its own DEC (the `[openapi]`+pyyaml precedent)
  only if the floor misses real RPCs.
**Messaging shapes:** Kafka `producer.send('topic', ...)` / `@KafkaListener(topics=)` → `topic::`;
RabbitMQ/pika `channel.basic_publish(routing_key='q')` / `basic_consume(queue='q')` /
`queue_declare('q')` → `queue::`; Redis `publish('chan')`/`subscribe('chan')`, NATS
`nc.publish/subscribe(subject)`, boto3 SNS/SQS `.publish(TopicArn=)`/`.receive_message(QueueUrl=)` →
`event::`/`topic::`. Literal name = EXTRACTED; constant-ref = INFERRED; multiple = AMBIGUOUS.

## §6 — Framework breadth
- **NestJS:** `@Controller('prefix')` class + `@Get('path')`/`@Post()`/`@Put(':id')`/`@Delete()` methods;
  route = prefix+path; **guard: method decorators count only inside `@Controller`**.
  `RouterModule.register([{path, module}])` adds module prefixes.
- **Django:** `urls.py` `path('route/', view)` / `re_path(r'^...$', view)` / `include('app.urls')`;
  function + class-based views (`.as_view()`); DRF `router.register(r'prefix', ViewSet)`.
- **JAX-RS / Jakarta REST:** `@Path("resource")` class + `@GET`/`@POST`/… methods (`jakarta.ws.rs.*`);
  `@ApplicationPath` app prefix; class `@Path`+method `@Path` concatenate (enclosing-class guard).

## §7 — Candidate acceptance repos (diffable, MIT/Apache)
- **gRPC:** `grpc/grpc-go` `examples/route_guide` (Apache-2.0); `grpc/grpc` `examples/python/route_guide`
  + `helloworld` (Python `stub.Method`); `itsksaurabh/go-grpc-examples` (MIT, all 4 RPC types).
- **Messaging:** `rabbitmq/rabbitmq-tutorials` (pika pub/sub); a Spring `@KafkaListener` sample.
- **NestJS:** `nestjs/nest` `sample/` (MIT, TypeORM + controllers); a `nest new` CatsController scaffold.
- **Django:** `django/django` + DRF tutorial apps (any `urls.py` with `path()`/`re_path()`/`include()`).
- **JAX-RS:** `eclipse-ee4j/jersey` examples (`HelloWorldResource`); `mkyong/jax-rs`; Open Liberty
  `guide-rest-intro`.
- **Spring + JPA (DI/ORM tail):** `spring-projects/spring-petclinic` (Apache-2.0, canonical
  `@Autowired`/`@Entity`/`@Table`); Baeldung `tutorials` for `@Qualifier` multi-impl examples.

## §8 — Dependency-discipline ledger (what needs a DEC)
- MCP detection — **zero new deps** (pure AST/tree-sitter). No DEC needed for deps.
- gRPC full AST via `proto-schema-parser` — **needs `antlr4-python3-runtime>=4.13.0` → opt-in `[proto]`
  extra + DEC.** The tree-sitter/regex floor = no DEC.
- Registry dispatch, messaging, DI, ORM, framework routes — pure AST/tree-sitter against existing
  grammars = **no new runtime deps**.

## §9 — Caveats
- SEP-1575 tool versioning is proposal-stage (FastMCP implements `version=` today); treat `version` as
  an `Endpoint` property, never part of the key.
- `mcp::<tool>` vs `mcp::<server>::<tool>` rests on a real tension (server identity recoverable but only
  via dataflow; no official collision standard) — bare-tool is pragmatic, not theoretically complete.
- GitNexus star/"viral" figures are secondary-source and vary (~19k–29k) — treat as approximate; the
  license + issue-#306 facts are primary GitHub sources and reliable.
- `proto-schema-parser` star count is low (~28) but maintenance is healthy and MIT-clean; the antlr4
  transitive dep is the blocker, not maintenance risk.
- CrewAI tool-registration APIs have churned (0.150.0 regression) — pin `crewai_tools` 0.32.x; treat
  CrewAI shapes as lower-stability than LangChain/OpenAI Agents SDK.
- SEP-986's charset is broader than model APIs accept; normalize separators before keying.
- Acceptance-repo scale figures are qualitative — confirm exact counts at fixture-selection time.
