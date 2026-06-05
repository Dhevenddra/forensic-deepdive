# PRD_v0.4.md — forensic-deepdive v0.4: "Cross-Stack & Visual" (the wedge)

> **Audience:** Claude Code (Opus 4.8), under `CLAUDE.md` session discipline.
> **Companions:** `KICKOFF_v0.4.md` (operating mode), `research_v0.4.md` (evidence; cited as "research §X").
> **Status:** the v0.4 detail-PRD pass DEC-034 promised — written *now that v0.3 has shipped*, against
> real numbers. Specified to implementation depth. v0.5 / v0.6 / v1.0 remain scoped (per the §0.2
> calibration lesson). The IDE is out of scope for this whole arc.
> **DEC numbering:** v0.3 ended at **DEC-042**. v0.4 starts at **DEC-043**.

---

## 0. The brutal version up front

### 0.1 Where v0.3 left us (the substrate this builds on)
v0.3.0 is tagged (DEC-001→042, 471 tests). The graph has File/Symbol/Module/Commit/Author nodes and
DEFINES/MEMBER_OF/IMPORTS/CALLS/EXTENDS/IMPLEMENTS/TOUCHED_BY_COMMIT/AUTHORED_BY/CO_CHANGES_WITH edges,
9 languages, per-edge confidence, 8 MCP tools, hybrid NL query, Mermaid. **The v0.3 acceptance proved
the wedge is now buildable:** on Superset, one NL query already retrieves *both* the Python SQLAlchemy
models *and* the TS frontend `Dashboard` — both endpoints resolve, the graph just doesn't **join** them.
v0.4 is that join. And the substrate it rides on is solid: `self.`/`this.` receiver resolution landed at
99.9% precise INFERRED on Superset's DAO/model/command layers (Item C), which is exactly the call-site
accuracy a `ROUTES_TO` edge needs at both ends.

### 0.2 The calibration discipline (still governs)
v0.2 planned 8 DECs, shipped 21. v0.3 planned 7, shipped 9 (well-calibrated). v0.4 pre-drafts ~11
(§7). **Budget ~1.5–2× that.** Log every real choice as an append-only DEC. Only v0.4 is line-specced;
v0.5–v1.0 are a ranked, acceptance-bound backlog (§5–§8).

### 0.3 The three durable differentiators (unchanged — do not dilute)
1. **Cross-stack / framework-aware edges** — v0.4 makes this real. Nobody open-source does the
   OpenAPI-shortcut version of it.
2. **Git-archaeology as first-class graph data.**
3. **Per-edge confidence taxonomy** — and v0.4 extends it to a brand-new edge class honestly.

### 0.4 What v0.4 ships (headline)
A **`ROUTES_TO` cross-stack join** (React `fetch`/`axios`/etc. → Spring/FastAPI/Express/… route
handler), built on **one generalizable `CrossBoundaryEdge` abstraction** (so gRPC/topics drop in at
v0.5 for free), with an **OpenAPI/proto/GraphQL/tRPC codegen shortcut** that yields EXTRACTED joins
GitNexus cannot match (research §3) — plus a **`forensic serve --ui`** Sigma.js graph explorer, a
**`trace` MCP tool** (the 9th) for feature-slice traversal, and two quick wins the v0.3 findings
demanded: **TS heritage capture** (fixes the EXTENDS/IMPLEMENTS under-capture) and an **`example`
file-role** (fixes fastapi's 36% AMBIGUOUS noise).

---

## 1. The keystone decision: one CrossBoundaryEdge abstraction (research §1)

Do **not** build a bespoke HTTP system. Build the abstraction GitNexus proved works, then make HTTP its
first instance. This is DEC-043 and it shapes everything else.

**The model.** A *cross-boundary contract* is a `(role, contractId, symbol, confidence, evidence)`
record. `role ∈ {provider, consumer}`. `contractId` is a canonical string built by a per-protocol
`key_builder`. The join pass groups records by `contractId` and emits a cross-link between every
consumer and every provider sharing it.

- HTTP key: `http::<METHOD>::<normalized-path>` (this PRD, v0.4).
- gRPC key: `grpc::<pkg>.<Service>/<Method>` (v0.5).
- Topic key: `topic::<name>` / `queue::<name>` / `event::<name>` (v0.5).

**Graph shape (the join is a node, the cross-link is an edge):**
- New node **`Endpoint`** — the canonical contract. PK = `contractId`. Properties: `protocol`, `method`,
  `normalized_path`, `raw_path_samples` (a few originals, for display), `framework`, `spec_backed: bool`.
- New edge **`HANDLES`** — provider `Symbol` → `Endpoint`. (The handler function exposes this contract.)
- New edge **`CALLS_ENDPOINT`** — consumer `Symbol` → `Endpoint`. (The caller hits this contract.)
- New edge **`ROUTES_TO`** — the *materialized* cross-stack edge, consumer `Symbol` → provider `Symbol`,
  carrying the join confidence + `via` (`http|grpc|topic`) + `endpoint` (the contractId). This is the
  edge agents and the visualizer traverse directly; `HANDLES`/`CALLS_ENDPOINT` are the audit trail.

**Why a join *node* (`Endpoint`) and not just a direct edge:** it lets a consumer with no resolvable
provider still exist in the graph (CALLS_ENDPOINT → Endpoint with no HANDLES — an honest "calls an
endpoint we can't locate"), and it makes the join a natural two-edges-into-one-node graph pattern that
the `trace` tool and Cypher queries read cleanly. It also pre-stages cross-repo federation (v0.5): an
`Endpoint` is the federation seam.

**Determinism:** providers/consumers collected, sorted by `(rel_path, start_byte)`; the join iterates
contractIds in sorted order; ROUTES_TO edges sorted by `(consumer_id, provider_id)`. Golden tests on a
fixture.

---

## 2. v0.4 build order

Quick wins + foundation first (they de-risk and strengthen the wedge's substrate), then the wedge core,
then surfacing, then the visual layer, then acceptance. Each item's tests green before the next.

**A** Stable node-ID scheme (DEC-051) → **B** TS heritage capture (DEC-050) → **C** `example` file-role
(DEC-049) → **D** `CrossBoundaryEdge` abstraction + `Endpoint`/`HANDLES`/`CALLS_ENDPOINT`/`ROUTES_TO`
schema + `ContractPhase` skeleton (DEC-043) → **E** HTTP normalization + contractId (DEC-044) → **F**
provider extractors (DEC-045) → **G** consumer extractors (DEC-046) → **H** the join + confidence model
(DEC-047) → **I** codegen shortcut (DEC-048, the differentiator) → **J** `trace` MCP tool + emit section
(DEC-052) → **K** `serve --ui` Sigma.js explorer (DEC-053, the largest item) → **L** acceptance (§4.9).

Rationale for ordering: A is foundational and cheap and everything benefits (stable IDs are also the
forward-compat seam for v1.0). B and C are independent quick wins that strengthen the TS side and clean
the AMBIGUOUS noise the wedge would otherwise inherit. D–I are the wedge, in dependency order (schema →
key → providers → consumers → join → shortcut). J surfaces it; K visualizes it; L proves it.

---

## 3. v0.4 items in implementation detail

### 3.A Item A — Stable node-ID scheme (DEC-051) [foundation, do first]
**Problem.** Today symbols key on `qualified_name` (DEC-023). That's not stable under overloads
(same-name methods) or edits, which blocks incremental updates and rename tracking (v1.0) — and the
research (§10) flags this as the one forward-compat seam to get right *now* so v1.0 needs no migration.

**Design.** Node ID = `<kind>:<rel_path>:<qualified_name>` plus an **overload disambiguator** when a
`(kind, rel_path, qualified_name)` collides: append `#<n>` by sorted definition order, and on a *content*
collision append `~<short-hash>` of the signature/arity. (GitNexus's scheme, research §10.) The ID is
computed once in a new `ids.py` and used everywhere a node is referenced. `qualified_name` remains a
human-facing property; the ID is the key.

**Files.** `src/forensic_deepdive/static/ids.py` (new: `make_symbol_id`, `make_endpoint_id`,
disambiguation); `graph/schema.py` (PK becomes the ID); `graph/store.py` + `build_graph` (reference by
ID); resolver writes IDs on edges.

**Tests.** `tests/test_ids.py`: two overloaded methods get distinct stable IDs; ID is invariant when an
unrelated line in the file changes (the rename/incremental forward-compat check — a file edit that
doesn't touch the symbol leaves its ID identical); deterministic ordering.

**Acceptance.** All existing 471 tests still green after the key migration (this is a refactor with a
behavior-preserving contract — golden artifacts must be byte-identical except where IDs surface, which
they shouldn't in the 5 artifacts). Note: this item is invisible in output; its whole value is forward-compat.

### 3.B Item B — TS/TSX heritage capture (DEC-050) [quick win]
**Problem.** v0.3 findings: TS `extends`/`implements` under-captured (gitnexus 2 EXTENDS/5 IMPLEMENTS;
superset 1 IMPLEMENTS at 3,871 files). DEC-028's extractor is conservative for TS. React component
hierarchies and the TS side of `ROUTES_TO` lean on this.

**Design (concrete tree-sitter queries, research §7).** Add to the TS/TSX `tags.scm`:
- `class_declaration` → `class_heritage` → `extends_clause` ⇒ `EXTENDS`.
- `class_heritage` → `implements_clause` ⇒ `IMPLEMENTS` (one per interface).
- `interface_declaration` → `extends_type_clause` ⇒ `EXTENDS` (interface→interface).
- Handle `type` aliases and declaration merging where they affect heritage (best-effort; tag INFERRED
  when the heritage target is a computed/aliased type).

**Files.** TS/TSX `tags.scm` in `static/tags.py`; resolver branch for the new captures; `tests/fixtures/
typescript_heritage_sample/`; `tests/test_parse.py`.

**Acceptance.** Re-running gitnexus and superset shows EXTENDS/IMPLEMENTS counts materially up (record
before/after in findings). No regression in Java/Python/Dart heritage.

### 3.C Item C — `example` / `tutorial` file-role (DEC-049, extends DEC-021) [quick win]
**Problem.** v0.3 findings: `docs_src/`-style tutorial dirs redefine the same names across hundreds of
files → fastapi 36% AMBIGUOUS, and tutorial symbols rank as "central" (a `docs_src` `Query` polluted
fastapi's centrality). These are example code, not implementation.

**Design.** Extend the DEC-021 file-role enum `{source, test, fixture, vendored, generated}` with
**`example`**. Classification heuristic (deterministic, conservative): path segment matches
`examples?/`, `docs_src/`, `samples?/`, `tutorials?/`, `demo/` (configurable list). `example`-role files
are **inventoried, parsed, and in the graph** (unlike excluded roles) but the **hybrid-query output
shaping (DEC-038) demotes them** the same way it demotes tests/vendored/generated, and centrality
ranking down-weights them. They are *not* excluded from the graph (an example may legitimately be what a
user asks about) — they're demoted, which is the honest middle path.

**Files.** `inventory.py` (role classification + config); `query/fuse.py` (shaping weight for `example`);
PageRank personalization (down-weight example role, mirroring the test treatment); `tests/test_inventory.py`,
`tests/test_query_fuse.py`.

**Acceptance.** fastapi AMBIGUOUS ratio drops materially from 36% in the *shaped query results* (the raw
graph AMBIGUOUS is unchanged — these are honest same-name collisions; we demote, not delete). fastapi's
top NL-query hits are library symbols, not `tutorial001` duplicates.

### 3.D Item D — CrossBoundaryEdge abstraction + schema + ContractPhase (DEC-043) [wedge core]
**Design.** Implement §1. New package `src/forensic_deepdive/contracts/`:
- `base.py` — `Contract` dataclass `(role, contract_id, symbol_id, confidence, via, evidence)`;
  `KeyBuilder` protocol; the `join(providers, consumers) -> list[CrossLink]` pass (sorted, deterministic).
- `registry.py` — maps `protocol -> (extractor, key_builder)`; HTTP registered in v0.4, gRPC/topic
  stubbed with a clear "v0.5" `NotImplemented` marker so the seam is visible.
- New **`ContractPhase`** in `pipeline/phases.py`, `depends_on=("parse","static")` (needs tags + resolved
  symbols/MEMBER_OF for handler attribution), output `ContractOutput` (providers, consumers, cross-links).
  Phase list becomes `inventory → parse → static → contracts → flatten → history → build_graph → emit`.
- `graph/schema.py` — add `Endpoint` node + `HANDLES`/`CALLS_ENDPOINT`/`ROUTES_TO` edges; `build_graph`
  persists `ContractOutput`.

**Tests.** `tests/test_contracts_base.py`: join groups by contractId; many-consumers-one-provider fan-in;
consumer-with-no-provider yields CALLS_ENDPOINT + Endpoint, no ROUTES_TO; determinism.

### 3.E Item E — HTTP normalization + contractId (DEC-044) [wedge core]
**Design (copy GitNexus's algorithm, research §2).** In `contracts/http/normalize.py`:
- `normalize_provider_path(p)`: strip query → lowercase → drop trailing slash → collapse `:id`, `{id}`,
  `[id]` → `{param}`.
- `normalize_consumer_path(p)`: provider rules **plus** template-literal `${x}` → `{param}`, absolute-URL
  host/scheme stripped (parse to pathname), **numeric segment** `/orders/42` → `/orders/{param}`.
- `http_contract_id(method, normalized_path)` → `http::<METHOD>::<path>`. Wildcard `http::*::<path>` for
  method-agnostic match. Noise filter for health-check / param-only paths.

**Tests.** `tests/test_http_normalize.py`: the full equivalence class `/users/{id}` ≡ `/users/${id}` ≡
`/users/:id` ≡ `/users/42` (consumer) ≡ `f"/users/{id}"` all → `http::GET::/users/{param}`; query strings
and trailing slashes dropped; absolute URL pathname extraction.

### 3.F Item F — Route provider extractors (DEC-045) [wedge core]
**Design.** Per-language tree-sitter pattern extractors in `contracts/http/providers/`, each emitting
provider `Contract`s with the handler `symbol_id`. Cover **GitNexus's set + close its gaps** (research §2):
- Python: **FastAPI** `@app.<verb>`/`@router.<verb>` + `include_router(prefix=...)`; **Flask**
  `@app.route(..., methods=[...])` / `@blueprint.route`; **Django** `urls.py` `path()`/`re_path()`.
- Java: **Spring** `@GetMapping`/`@PostMapping`/… + class `@RequestMapping` prefix + interface→controller
  inheritance; **JAX-RS** `@Path` + `@GET`/`@POST`.
- Node/TS: **Express** `app.<verb>`/`router.<verb>`; **NestJS** `@Controller`+`@Get/@Post` (guarded by
  enclosing `@Controller`).
- (Stretch / config-gated, land if cheap: **Rails** `routes.rb`, **ASP.NET** `[HttpGet]`/`[Route]`.)

A small scanner mirroring GitNexus's `compilePatterns`/`runCompiledPatterns` (compile per-language
queries once, run over each file) keeps this fast and uniform.

**Confidence:** an annotation/decorator with a **literal** path = the provider side is EXTRACTED-grade
(the route definition is syntactic fact); a computed/variable path = INFERRED.

**Tests.** Per-framework fixtures with a known route; assert Endpoint contractId, HANDLES edge to the
right handler symbol, prefix joining (FastAPI `include_router`, Spring class `@RequestMapping`).

### 3.G Item G — Frontend consumer extractors (DEC-046) [wedge core]
**Design.** `contracts/http/consumers/`, emitting consumer `Contract`s with the calling `symbol_id`.
Cover **GitNexus's set + close its gaps** (research §2):
- `fetch()` (no opts → GET; `{method}` → that verb), `axios.<verb>`, `axios({method,url})`, jQuery
  `$.get/$.post/$.ajax`.
- **Gaps to add:** **RTK Query** (`builder.query/mutation` with `query: () => url`), **React Query /
  TanStack** (`useQuery`/`useMutation` wrapping a fetch/axios call), **Angular HttpClient**
  (`http.get/post`), **tRPC** client calls. (tRPC/GraphQL also feed the codegen shortcut, Item I.)
- Python consumers (`requests`/`httpx`) and Java clients (RestTemplate/WebClient/OpenFeign) for
  service-to-service HTTP (pre-stages v0.5 cross-service).

**Confidence:** literal URL string = consumer side strong; template-literal/computed URL = INFERRED;
fully dynamic (variable only) = the consumer is recorded but the *join* will be AMBIGUOUS or absent.

**Tests.** Per-client fixtures; assert CALLS_ENDPOINT to the right Endpoint, method inference (fetch
default GET, `{method:'POST'}`), template-literal normalization end-to-end.

### 3.H Item H — The join + confidence model (DEC-047) [wedge core — the honest heart]
**Design.** The join groups by contractId (§1). Map to **our three tags** (not GitNexus's numbers,
research §2/§12):
- **EXTRACTED** — only when backed by a spec/codegen contract (Item I), OR a *unique* literal-path+method
  match on both sides with both symbols resolved. (Syntactic fact at both ends + unique.)
- **INFERRED** — normalized match (template literal / numeric segment / prefix-joined) with a unique
  provider, OR literal match where one side's symbol is heuristically resolved.
- **AMBIGUOUS** — multiple candidate providers share the contractId (surface *all* candidate ROUTES_TO
  edges, never pick one — consistent with DEC-025/037 philosophy), OR a dynamic/computed URL that
  normalizes to a pattern matching >1 provider.
- **No ROUTES_TO** — consumer whose contractId matches no provider (keep CALLS_ENDPOINT → Endpoint; this
  is the honest "hits an endpoint we can't locate in this repo," and the federation seam for v0.5).

**Tests.** `tests/test_contracts_join.py`: unique literal → EXTRACTED; template-literal unique → INFERRED;
two providers same contractId → 2 AMBIGUOUS ROUTES_TO; unmatched consumer → CALLS_ENDPOINT only.

### 3.I Item I — Codegen shortcut (DEC-048) [the differentiator — research §3]
**Problem/opportunity.** GitNexus has no OpenAPI shortcut for HTTP. When a repo ships a contract spec,
the binding is near-deterministic.

**Design.** A spec-detection pass in `contracts/specs/`:
- **OpenAPI/Swagger** (`openapi.json`, `swagger.yaml`, `openapi.yaml`): parse paths × methods ×
  operationIds → authoritative provider Endpoints (`spec_backed=True`). If a **generated client** marker
  is present (openapi-generator/.openapi-generator, openapi-ts output, NSwag, Kiota), bind generated
  client calls to spec operations 1:1 → **EXTRACTED** ROUTES_TO.
- **`.proto`** (gRPC, also feeds v0.5): enumerate `service`/`rpc` as provider contracts now (cheap,
  pre-stages cross-service).
- **GraphQL SDL** (`.graphql`/schema): operations as contracts.
- **tRPC router**: procedure names as contracts.
- A spec-backed Endpoint is authoritative: a consumer literal matching a spec path is high-confidence
  even when the *handler symbol* isn't found (the spec *is* the provider truth).

**Tests.** `tests/test_specs_openapi.py`: a fixture repo with `openapi.json` + a generated client →
EXTRACTED ROUTES_TO with `spec_backed=True`; spec path matched by a raw fetch with no located handler →
high-confidence Endpoint still emitted.

### 3.J Item J — `trace` MCP tool (9th) + emit section (DEC-052) [surfacing]
**Design.** New MCP tool **`trace(symbol, direction='downstream', max_depth)`** — walks the cross-stack
chain: a frontend component → `CALLS_ENDPOINT` → `Endpoint` → `HANDLES` → handler `Symbol` → (`CALLS`
into) service/repo as far as v0.4 resolution reaches. `direction='upstream'` answers "who calls this
endpoint." Single-call, complete-answer (research §10.4). The DI/ORM tail (service→repo→table) is v0.5;
`trace` returns what's resolvable now and marks the boundary honestly.

This is the **9th MCP tool** → CLAUDE.md coupling rule fires: update all SKILL.md files that enumerate
tools, README ("8 MCP tools" → "9"), the comparison table, the intro line, and the tool-count note.

**Emit:** add a bounded **`## Cross-stack routes`** section to **HOTPATHS.md** (top-N ROUTES_TO edges
with confidence) — a *section*, not a 6th artifact (respects the 5-artifact contract, DEC invariant).
Keep AGENT_BRIEF additions minimal/top-few to stay ≤5kb (a single "this frontend calls these backend
handlers" rule class, confidence-tagged, only if it fits the cap).

**Tests.** `tests/test_trace.py` (chain traversal on a fixture); `tests/test_mcp_tools.py` (9th tool
registered, description ≤200 tokens); golden HOTPATHS section.

### 3.K Item K — `forensic serve --ui` Sigma.js explorer (DEC-053) [the Visual half — largest item]
**Design (research §8).** A local served UI (not static export): `forensic serve --ui` starts the MCP/
HTTP backend plus a graph endpoint that streams a **bounded, filtered** graphology graph to a Sigma.js
(WebGL) React client.
- **Mandatory LOD + filtering** — Superset had 348k CO_CHANGES_WITH edges; **never render all edges**.
  Default view = top-N central nodes + their neighborhoods; filters by edge type (CALLS / ROUTES_TO /
  EXTENDS / CO_CHANGES_WITH …), by confidence (EXTRACTED/INFERRED/AMBIGUOUS), by language/directory.
- **Confidence-aware encoding** — edge style solid/dashed/dotted + color for the three tags; **ROUTES_TO
  edges a distinct color/weight** (the cross-stack story is the headline of the view).
- **Layout** — graphology ForceAtlas2 + Leiden/Louvain community coloring; click-node → source +
  `context`/`trace`; small edge sizes (WebGL has no edge transparency).
- **Build** — keep the React client a thin, vendored, dependency-light bundle; the backend reuses the
  existing LadybugStore. A static HTML export is a **secondary** artifact (nice-to-have), not the primary.

**Tests.** Backend graph-endpoint tests (bounded node/edge counts, filter correctness, deterministic
serialization); a smoke test that the UI bundle builds. (Full UI E2E is out of scope for the unit suite;
acceptance is the real-repo Superset render in §4.9.)

### 3.L Item L — Acceptance (§4.9) [the gate]

---

## 4. Acceptance

### 4.9 v0.4 repo set + gate
**Repos.** Superset (the **staged cross-stack demo** — Flask/SQLAlchemy backend ↔ React frontend; the
v0.3 finding that one query retrieves both ends now becomes a *joined* ROUTES_TO graph); a **purpose-built
Spring+React fixture** (clean, known routes — petclinic is Thymeleaf/JSP server-rendered with no React
fetch, so it's a *provider-only* check, honest about that); **a repo shipping an OpenAPI spec + generated
client** (the Item-I differentiator); re-run **gitnexus** + **superset** for the TS-heritage before/after;
re-run **fastapi** for the `example`-role AMBIGUOUS before/after.

**Gate (all must hold):**
1. `uv run pytest -x` green; ruff clean.
2. **ROUTES_TO on Superset:** React fetch/axios sites join to Flask/API handlers; `trace()` returns the
   component→endpoint→handler chain; confidence honestly tagged (record EXTRACTED/INFERRED/AMBIGUOUS split).
3. **Codegen shortcut:** the OpenAPI-spec repo yields `spec_backed=True` EXTRACTED ROUTES_TO.
4. **TS heritage:** gitnexus/superset EXTENDS+IMPLEMENTS materially up vs v0.3 (record numbers).
5. **`example` role:** fastapi shaped-query AMBIGUOUS materially below 36%; top hits are library, not tutorial.
6. **`serve --ui`:** renders Superset bounded + filtered, confidence-styled, ROUTES_TO highlighted.
7. **Determinism:** byte-identical artifacts (and deterministic ROUTES_TO/Endpoint ordering) across runs;
   golden tests green.
8. **Stable IDs:** an unrelated edit leaves a symbol's ID unchanged (the forward-compat check).
9. **AGENT_BRIEF ≤ 5 kb** on every repo (the cross-stack section must not blow the cap).

**Findings:** `docs/findings/v0.4/<repo>-test.md` + a README cross-repo summary, same shape as v0.3 —
designed to diff. Record the ROUTES_TO confidence split, the codegen-shortcut hit rate, and the TS-heritage
and `example`-role before/afters explicitly.

### 4.8 Expected DECs (calibration buffer applies — budget ~1.5–2×)
DEC-043 CrossBoundaryEdge abstraction + Endpoint/HANDLES/CALLS_ENDPOINT/ROUTES_TO schema + ContractPhase ·
DEC-044 HTTP normalization + contractId · DEC-045 provider extractors · DEC-046 consumer extractors ·
DEC-047 cross-stack confidence model · DEC-048 codegen shortcut · DEC-049 `example` file-role · DEC-050
TS heritage capture · DEC-051 stable node-ID scheme · DEC-052 `trace` 9th MCP tool + emit section ·
DEC-053 Sigma.js `serve --ui`. Expect more (per-framework extractor sub-decisions, spec-format handling,
UI bundle strategy, the ID-migration mechanics).

---

## 5. v0.5 — "Memory & Federation" (SCOPED — gets its own detail pass after v0.4)
- **Cross-service edges** via the *same* `CrossBoundaryEdge` abstraction: gRPC (`.proto` providers +
  per-language client/server signals, research §5) and messaging topics (Kafka/RabbitMQ/NATS/SNS-SQS/Redis,
  key = topic/queue/event). New key-builders, no new join machinery.
- **DI + ORM edges** to complete the traceability matrix: `INJECTS`/`PROVIDES` (Spring `@Autowired`/ctor,
  NestJS/Angular/Guice/Dagger/.NET/FastAPI `Depends`) and `PERSISTS_TO` (JPA `@Entity`, SQLAlchemy, Prisma,
  TypeORM, Django). Then `trace` walks the full component→route→handler→service→repository→table slice.
- **Cross-repo groups / federation** (GitNexus pattern): a registry of repos joined at the `Endpoint` seam,
  with a manifest escape hatch for cross-repo naming mismatches.
- **Portable insight storage** (parallel git ref, Entire pattern) + **Graphiti real-LLM validation** +
  **JSONL→SQLite index** (carried from the v0.3 PRD's v0.5 scope).

## 6. v0.6 — "Performance Core" (SCOPED)
- **Opt-in SCIP ingestion tier** (scip-ts/python/java) → compiler-accurate edges promoted to EXTRACTED;
  pure-static stays default (research §7). The better-than-stack-graphs near-term accuracy path.
- **Rust/PyO3 extraction hot-path** — the real cold-extract ceiling-breaker (v0.3 got Omi 930s→407s via
  incremental+parallel; Superset 486s is tractable but Rust is the next lever). Profile-first.
- **Reconsider tree-sitter-stack-graphs** only if SCIP coverage proves insufficient (bindings still pre-1.0).

## 7. v1.0 — "Scale & Stability" (SCOPED)
- **Incremental *graph* updates + watch-mode daemon** (debounced re-index, per-file staleness banner,
  Merkle-tree change detection — codegraph/Cursor patterns). The stable IDs from v0.4 Item A make this
  possible without migration.
- **Bi-temporal/versioned graph** (`valid_from`/`valid_to` — "what did we know when").
- **Rename tracking** (`git --follow` + stable-ID continuity).
- **Odoo-scale proof + ArcadeDB server-mode hedge**; API freeze; docs hardening.

---

## 8. Deferred-work ledger (v0.4 additions; full ledger lives in PRD_v0.3.md §9)
| Item | Origin | Target |
|---|---|---|
| gRPC / topic cross-service edges | research §5 (scope extension) | v0.5 |
| DI (INJECTS/PROVIDES) + ORM (PERSISTS_TO) | research §6 | v0.5 |
| Cross-repo federation at the Endpoint seam | research §9 (GitNexus groups) | v0.5 |
| Full traceability matrix (component→…→table) | research §6 | v0.5 |
| SCIP opt-in accuracy tier | research §7 | v0.6 |
| Rust/PyO3 hot-path | v0.3 carry | v0.6 |
| tree-sitter-stack-graphs | research §7 | v0.6+ (bindings pre-1.0) |
| Incremental graph + watch daemon + Merkle | research §9/§10 | v1.0 |
| Bi-temporal graph + rename tracking | research §10 | v1.0 (IDs designed v0.4 Item A) |
| Rails/ASP.NET route providers (if not landed) | §3.F stretch | v0.5 |
| GraphQL/tRPC deep modeling beyond contract detection | §3.I | v0.5 |
| **IDE / agent-dev environment** | long-horizon | OUT OF SCOPE this arc |

---

## 9. Cross-version invariants (reaffirmed — never break without a superseding DEC)
1. **5-artifact contract.** The cross-stack data is a *section* in HOTPATHS, never a 6th core artifact.
2. **AGENT_BRIEF ≤ 5 kb** — the cross-stack rule class must fit or overflow to AGENT_BRIEF_DEEP.
3. **Pure-static floor (DEC-009).** ROUTES_TO, specs, heritage, the UI graph endpoint — all work with no
   LLM/network/embeddings. The codegen shortcut reads local spec files only.
4. **Confidence taxonomy is sacred.** ROUTES_TO is EXTRACTED *only* spec-backed or unique-literal; never
   silently upgrade an inferred join.
5. **Determinism survives the new phase.** Collect-then-sort; golden tests on every new edge class.
6. **Apache-2.0; no aider package dep; no un-DEC'd runtime dep** (the Sigma.js client bundle and any spec
   parser each need a DEC).

---

## 10. Forward-compatibility note (toward the agent substrate — NOT an IDE plan)
v0.4 deliberately lays three endgame seams at near-zero cost (research §10): **stable node IDs** (Item A —
the incremental/rename seam), the **`Endpoint` join node** (the federation seam), and **single-call `trace`**
(the agent-context-in-one-call pattern). Do not design the IDE. Just keep these seams clean so the
"graph-as-substrate-for-agents" endgame stays reachable when its arc finally opens.

---

*End of PRD_v0.4.md. v0.4 is build-ready. The wedge lands on the resolved-call-site substrate v0.3 built;
the abstraction is general so v0.5 cross-service is a key-builder, not a rewrite; and the seams for the
eventual environment are laid without building it.*
