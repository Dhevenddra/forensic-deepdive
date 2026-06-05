# research_v0.4.md — Cross-Stack & Visual: research dossier

> Evidence base for `PRD_v0.4.md`. Read when a PRD item cites "research §X".
> Compiled 2026-05-31 from primary sources (GitNexus source @ `main`, framework docs,
> microservice-recovery academic work, Sigma.js/graphology docs). Decision-grade, not neutral:
> where a competitor is ahead, it says so; where there's a borrow, it says exactly what to take.

---

## 0. The one-paragraph version
The v0.4 wedge is the **ROUTES_TO cross-stack join**, and the architecture to copy is **GitNexus's
contract-extractor pattern**: every cross-boundary edge (HTTP, gRPC, topic) is a provider/consumer
pair keyed on a canonical `contractId` (`http::GET::/users/{param}`, `grpc::auth.AuthService/Login`),
joined by exact match on that key. This "join on a shared key" abstraction generalizes URL+method
(HTTP), service+rpc (gRPC), and topic/queue (messaging) into one mechanism — adopt it as a single
`CrossBoundaryEdge` abstraction with per-protocol key-builders, not three bespoke systems. It maps
cleanly onto our EXTRACTED/INFERRED/AMBIGUOUS model. GitNexus is **ahead of us on cross-stack and
visualization**; we are **ahead on the pure-static guarantee, per-edge provenance, and Apache-2.0**
(GitNexus is PolyForm Noncommercial — commercial use prohibited). Our biggest exploitable gap in
GitNexus: **it has no OpenAPI/codegen shortcut for HTTP** — shipping one gives us near-deterministic
EXTRACTED joins it cannot match.

---

## 1. The contract-extractor pattern (the architectural keystone — §A)
GitNexus's cross-boundary model, read from source: sync-time extractors walk the repo and emit
**contracts** — provider or consumer records keyed by a canonical `contractId`. A matching pass joins
providers and consumers sharing a `contractId` and emits the cross-link. The *same* abstraction serves
HTTP, gRPC, and messaging topics. **Adopt this directly.** One `CrossBoundaryEdge` abstraction, a
pluggable `key_builder` per protocol, one join pass. ROUTES_TO (HTTP) is the v0.4 instance; gRPC and
topics reuse the mechanism in v0.5.

---

## 2. HTTP route extraction — exactly how GitNexus does it (§A/§B, the borrow)
**ContractId:** `http::<METHOD>::<normalized-path>`, method uppercased.

**Provider normalization (`normalizeHttpPath`):** strip query string → lowercase → drop trailing
slash → collapse all three param syntaxes to one `{param}` token: `:id` (Express), `{id}`
(FastAPI/Spring), `[id]` (Next.js) all → `{param}`. So `/Users/{ID}` → `/users/{param}`. **This is the
answer to our normalization problem** (`/users/{id}` ↔ `/users/${id}` ↔ `/users/:id` ↔ `f"/users/{id}"`
all collapse to `/users/{param}`). Copy it.

**Consumer normalization (`normalizeConsumerPath`) is more aggressive:** template literals `${x}` →
`{param}`; absolute URLs get host/protocol stripped via `new URL().pathname`; **numeric segments**
`/orders/42` → `/orders/{param}` (providers do NOT collapse numerics — only consumers).

**Provider patterns (per-language tree-sitter queries):**
- Python — FastAPI `@app.<verb>` / `@router.<verb>` (get/post/put/delete/patch), `include_router(prefix=...)`
  prefix joining. **No Flask, no Django — gaps to close.**
- Node/TS — NestJS `@Controller`+`@Get/@Post...` (only if enclosing class has `@Controller`), Express
  `app.<verb>`/`router.<verb>`. Compiled vs JS/TS/TSX grammars.
- Java — Spring `@GetMapping`/`@PostMapping`/etc. + class-level `@RequestMapping` prefix, with cross-file
  interface→controller route inheritance. **No JAX-RS `@Path` — gap.**

**Consumer patterns:** Python `requests`/`httpx`; Node `fetch()` (no opts → GET; `{method}` → that verb),
`axios.<verb>`, `axios({method,url})`, jQuery `$.get/$.ajax`; Java OpenFeign, RestTemplate, WebClient,
OkHttp, Java HttpClient, Apache HttpClient. **No RTK Query, React Query/TanStack, generated OpenAPI
clients, tRPC, Angular HttpClient — gaps to close.**

**Confidence (GitNexus's two regimes):** graph-assisted (reads pre-computed route/fetch edges) = flat
0.9; source-scan fallback = providers 0.8 / consumers 0.7, Java client outliers 0.65–0.75; a matched
cross-link = 1.0 `matchType:"exact"`. The matcher supports method-agnostic wildcard `http::*::<path>`
and filters health-check / param-only noise paths. **Don't copy their numbers — map to our three tags
(below); their scheme is an implementation detail, not a standard.**

---

## 3. The OpenAPI/codegen shortcut — GitNexus's gap, our wedge (§B/§C)
GitNexus has **no OpenAPI spec detection, no codegen-aware HTTP shortcut** (confirmed in source + their
open issue #306). Its gRPC path *does* parse `.proto` as a definitive provider source (0.85) — but HTTP
has no spec equivalent. **This is the single biggest differentiator available to us.** When a repo ships
an `openapi.json`/`swagger.yaml`, a generated client (OpenAPI Generator / openapi-ts / NSwag / Kiota
markers), a GraphQL SDL, a `.proto`, or a tRPC router, the frontend↔backend binding is
near-deterministic — operationId/path/method map 1:1 — so we emit **EXTRACTED** joins that pure
call-site matching can never reach. Academic precedent: SafeRESTScript and similar statically validate
REST consumers against OpenAPI specs. Detect spec → treat as authoritative provider list; detect
generated-client marker → 1:1 EXTRACTED join.

---

## 4. Prior art on full-stack static linking (§B/§D, academic + industry)
Signature-matching is a settled technique in microservice-architecture recovery. The **Prophet** engine
(behind Bushong et al., "Microvision," arXiv:2207.02974) does static analysis of Spring Boot / Java EE
via JavaParser + Neo4j and "matches the calls to system endpoints based on the relative endpoint URL,
the HTTP method, and parameters" — literally ROUTES_TO. The canonical two-phase recipe (Applied
Sciences 14(22):10725, MDPI 2024): phase 1 **Inter-service Detection** extracts endpoint declarations +
requests via static analysis; phase 2 **Signature Matching** uses a regex-like match on path +
parameters + HTTP method. Standard provider detection = annotation matching (Spring `@RequestMapping`,
JAX-RS); standard consumer detection = HTTP-client-class detection (`RestTemplate`, `HttpClient`).
**Caveat:** the JS call-graph literature documents real recall problems for client-side call graphs in
React/Angular — dynamic/computed URLs will legitimately fall to INFERRED/AMBIGUOUS. Don't over-promise
EXTRACTED on framework call sites without a spec.

---

## 5. Cross-service edges — gRPC / queues / events (§C, the scope extension → v0.5)
**gRPC (GitNexus, two passes):** (1) parse every `.proto` → provider `grpc::<pkg>.<Service>/<Method>`
@ 0.85; (2) per-language client/server signals — Go `pb.RegisterXxxServer`/`pb.NewXxxClient`, Java
`extends XxxImplBase`/`newBlockingStub`, Python `add_XxxServicer_to_server`/`XxxStub`, NestJS
`@GrpcMethod`/`@GrpcClient`. Provider 0.8 (with proto)/0.65; consumer 0.75/0.55; `@GrpcMethod` fixed
0.8. Matching lowercases pkg/service, case-sensitive on method (wire path is), service-only wildcard
`grpc::pkg.Svc/*`. Manifest escape hatch (`config.links` in `group.yaml`) for cross-repo naming
mismatches. **Messaging:** topic-extractor; join key = topic/queue/event-name (Kafka producer↔
`@KafkaListener`, RabbitMQ, NATS, SNS/SQS, Redis pub/sub). **All the same shared-key join** — the
`CrossBoundaryEdge` abstraction (§1) absorbs them with new key-builders. Ship in **v0.5**, not v0.4.

---

## 6. DI & ORM edges for the end-to-end traceability matrix (§D → v0.5)
The full slice — React component → fetch → ROUTES_TO → controller → service → repository → entity →
table — needs DI + persistence edges. Spring stereotypes (`@Service`/`@Repository`/`@Component`) +
injection points (`@Autowired`, constructor injection) → `INJECTS`/`PROVIDES` edges; `@Repository`→
`@Entity`→table closes the persistence end (JPA `@Entity`/`@Table`, SQLAlchemy, Prisma, TypeORM,
Django). GitNexus already ships an `orm` pipeline phase emitting QUERIES edges (Prisma, Supabase). The
self./this. receiver resolution v0.3 nailed (Superset 99.9% precise INFERRED on DAO/model/command
layers) is the substrate this chain rides on. Add `INJECTS`/`PROVIDES`/`PERSISTS_TO` in **v0.5**. Other
DI to model: NestJS providers, Angular DI, Guice, Dagger, .NET DI, FastAPI `Depends`.

---

## 7. Precise resolution upgrade (Item-C heuristic → EXTRACTED) (§E)
- **tree-sitter-stack-graphs:** Rust; Python bindings exist (`stack-graphs-python-bindings`, v0.0.14,
  May 2025) but explicitly "work in progress, API subject to change" — immature. Rulesets (`.tsg`) for
  Python/TS/Java exist but authoring/maintaining is substantial. File-incremental (attractive for the
  endgame). **Verdict: DEFER to v0.6+** — binding immaturity + ruleset cost too high for v0.4.
- **SCIP optional tier (better near-term path, → v0.6):** scip-typescript (built on the TS typechecker),
  scip-python, scip-java, etc. emit protobuf ingestible as an **opt-in** high-accuracy tier (edges →
  EXTRACTED), pure-static stays default. blarify *claims* SCIP is "up to 330× faster reference
  resolution than LSP" with "identical accuracy" (vendor claim, unverified). CodeGraphContext exposes
  `SCIP_INDEXER=true`.
- **TS heritage capture (the v0.3 under-capture → fix in v0.4, quick win):** concrete tree-sitter
  queries — `class_declaration` > `class_heritage` > `extends_clause` (extends); `implements_clause`
  (interface impl); `interface_declaration` > `extends_type_clause` (interface→interface). Add type-alias
  + declaration-merging handling. GitNexus emits unified `@heritage.extends` tags across languages.
  React component hierarchies and the TS side of ROUTES_TO depend on this.

---

## 8. Interactive visualization — the "Visual" half (§F)
- **Sigma.js + graphology (WebGL) is the stack** — what GitNexus uses (React 18 + Sigma.js +
  graphology). Reality check (Linkurious/Ogma comparison): Sigma renders ~100k edges with default styles
  but "struggles with 5k nodes with icons," and its force layout "falls beyond 50,000 edges." Superset
  had **348k CO_CHANGES_WITH** edges → **level-of-detail + aggressive filtering are mandatory; never
  render all edges at once.** WebGL has no edge transparency — use small edge sizes to mimic it.
- **Architecture: ship `forensic serve --ui` (local server), not a static export.** Served UI routes
  queries through the existing backend (GitNexus pattern: `serve` + thin React client over HTTP), allows
  live filtering on the full graph, reuses the confidence model. Static HTML export is a fine secondary
  artifact but caps on browser memory. (The 5 markdown artifacts already cover the offline case.)
- **Encoding:** EXTRACTED/INFERRED/AMBIGUOUS as edge style (solid/dashed/dotted + color); ROUTES_TO as
  a distinct color/weight; graphology Leiden/Louvain communities + ForceAtlas2 layout. Mermaid (shipped
  v0.3) stays the per-query lightweight view; Sigma.js is the whole-graph explorer. Cytoscape.js/D3/
  react-force-graph weaker at this scale; pyvis (vis.js) slower.

---

## 9. Competitive re-scan (§G)
- **GitNexus** (PolyForm Noncommercial 1.0.0 — *not* OSI open source, commercial use prohibited; ~37–39k
  stars, partly inflated per their own crypto-scam disclaimer; single maintainer; LadybugDB-backed like
  us). Category leader, closest competitor. Ships cross-repo "groups" with gRPC/HTTP/topic contract
  extractors, contract-bridge cross-impact, Leiden communities, MCP tools (`route_map`, `api_impact`,
  `shape_check`), Sigma.js UI. **Ahead of us on cross-stack + visualization.** Exploitable weaknesses:
  the license, no OpenAPI shortcut, no incremental indexing, single-maintainer bus factor, LadybugDB
  lock-in (shared).
- **CodeGraphContext** (MIT): 20 langs, multi-backend (incl. LadybugDB), live file-watch, opt-in SCIP —
  model for our SCIP tier + watch-mode.
- **codegraph** (Colby McHenry): SQLite, 19+ langs, 13–14 web-framework route detection, debounced
  file-watcher + per-file staleness banner + connect-time reconciliation — reference for v1.0 incremental.
- **blarify** (LSP/SCIP, Neo4j): source of the SCIP-330× claim; graceful incremental updates.
- **Moderne/OpenRewrite** (Lossless Semantic Trees — type-attributed, format-preserving, serializable;
  OpenRewrite core Apache-2.0, scale needs Moderne license). Their **Prethink** recipes generate
  "multi-repo, trusted context for AI agents" + a system-level component/dependency map — mature players
  are now emitting agent-facing graphs. **Correction:** Prethink docs do NOT use the
  EXTRACTED/INFERRED/AMBIGUOUS provenance vocabulary verbatim (that's the `graphify` tool) — our per-edge
  provenance remains a genuine differentiator.
- **Entire** (Thomas Dohmke): **$60M seed @ $300M valuation, Feb 10 2026** (largest dev-tool seed per
  lead investor Felicis). One open-source release — **Checkpoints** (git-native capture of agent
  reasoning on every commit). The "semantic reasoning layer" is announced vision, not shipped — it's
  session-context capture, complementary to a code graph, not competing. Monitor; don't react.
- **Cursor/Windsurf:** Merkle-tree incremental *embedding* indexes (AST chunks → vector DB, re-sync
  ~5–10 min), a RAG approach — do NOT copy the approach, DO borrow the Merkle change-detection for v1.0.

---

## 10. The IDE / agent-dev-environment endgame — forward-compat flags (§H, do NOT build yet)
Get these right now, cheaply, so the endgame stays reachable:
1. **Stable node identity across edits.** GitNexus: `generateId` + qualified-name keyspace + arity/
   type-hash overload suffixes (`Method:file:Class.method#1` vs `#2`, `~type` on collision). Prerequisite
   for incremental + rename. **Design the ID scheme in v0.4** (we already have qualified_name from
   DEC-023; add overload disambiguation) so v1.0 needs no migration.
2. **Bi-temporal/versioned graph** ("what did we know when"). Flag a `valid_from`/`valid_to` dimension
   now; implement v1.0.
3. **Watch-mode/daemon** with debounced incremental re-index + per-file staleness banners (codegraph) so
   an agent never gets a silent wrong answer between edit and re-sync. v1.0.
4. **Single-call tool responses** — return a complete blast-radius/trace answer in one call, not 10 graph
   queries (GitNexus design thesis; we already precompute PageRank/communities).
5. **Graph as shared memory for multiple agents** — Apache-2.0 + MCP + stable IDs positions us well;
   embedded LadybugDB is fine single-machine; federation is the v0.5 theme.

---

## 11. Borrow / adopt / defer (the one-table summary)
| Idea | Source | Action | Milestone |
|---|---|---|---|
| Provider/consumer contract keyed on canonical contractId | GitNexus | Adopt as `CrossBoundaryEdge` core | v0.4 |
| `http::METHOD::/path/{param}` normalization (`:id`/`{id}`/`[id]`→`{param}`; consumer also numeric+template) | GitNexus source | Adopt | v0.4 |
| Map join confidence to EXTRACTED/INFERRED/AMBIGUOUS | ours + GitNexus | Adopt our tags | v0.4 |
| Provider extractors: Spring/FastAPI/Express/NestJS **+ Flask/Django/JAX-RS/Rails/ASP.NET** | GitNexus + docs | Adopt + close gaps | v0.4 |
| Consumer extractors: fetch/axios/jQuery **+ RTK Query/TanStack/Angular/tRPC/generated clients** | GitNexus + ecosystem | Adopt + close gaps | v0.4 |
| **OpenAPI/proto/GraphQL/tRPC codegen shortcut** | GitNexus's gap | Adopt — primary wedge | v0.4 |
| TS heritage queries (extends/implements/interface) | tree-sitter-ts | Adopt — fixes v0.3 under-capture | v0.4 |
| `example`/`tutorial` file-role | v0.3 finding (DEC-021 ext) | Adopt — fixes fastapi 36% AMBIGUOUS | v0.4 |
| Sigma.js+graphology WebGL `serve --ui` (LOD/filter/confidence/ROUTES_TO encoding) | GitNexus UI | Adopt | v0.4 |
| Stable node-ID + overload disambiguation | GitNexus IDs | Design now (forward-compat) | v0.4 |
| gRPC `.proto` + client/server signals; topic extractor | GitNexus | Adopt (same abstraction) | v0.5 |
| DI (INJECTS/PROVIDES) + ORM (PERSISTS_TO) | Spring/ORM + GitNexus orm phase | Adopt — completes matrix | v0.5 |
| Cross-repo groups / federation + manifest escape hatch | GitNexus | Adopt | v0.5 |
| SCIP opt-in high-accuracy tier | blarify, CGC | Adopt (pure-static stays default) | v0.6 |
| Rust extraction hot-path | roadmap | Defer | v0.6 |
| tree-sitter-stack-graphs | github/stack-graphs | Defer (bindings pre-1.0) | v0.6+ |
| Incremental/watch daemon + staleness + Merkle | codegraph/CGC/Cursor | Adopt | v1.0 |
| Bi-temporal graph + rename tracking | engram | Implement (IDs from v0.4) | v1.0 |

---

## 12. Caveats
- GitNexus values are from `main` HEAD (very active, ~1000+ commits, releases ~v1.6.5) — current but may
  drift. Its two-regime confidence (graph-assisted flat 0.9 vs source-scan literals) is an implementation
  detail, **not** a standard — set our own thresholds calibrated to our three tags.
- Self-reported/unverified: blarify "330× vs LSP", engram "89% token reduction", GitNexus star count
  (crypto-scam-inflated). Directional only.
- **Client-side JS call-graph recall is known-hard** — dynamic/computed frontend URLs legitimately land
  INFERRED/AMBIGUOUS; don't over-promise EXTRACTED without a spec.
- **LadybugDB lock-in** is a shared long-horizon risk (custom engine, small ecosystem, bus factor).
- stack-graphs Python bindings explicitly pre-1.0 — the v0.6 deferral is risk management; revisit if they
  stabilize.
- Entire is early (one release); its semantic-reasoning layer is vision, not shipped — monitor.

## 13. Source index (primary)
GitNexus source + ARCHITECTURE.md + microservices-grpc guide + issue #306 (github.com/abhigyanpatwari/
GitNexus); Prophet/Microvision arXiv:2207.02974; MDPI Applied Sciences 14(22):10725; JS call-graph
recall arXiv:2205.06780; Sigma.js v4 docs + Linkurious/Ogma comparison; tree-sitter-typescript grammar;
github/stack-graphs + stack-graphs-python-bindings (PyPI); scip-typescript/-python/-java; blarify
(github.com/blarApp/blarify); CodeGraphContext (PyPI); codegraph (github.com/colbymchenry/codegraph);
Moderne LST + Prethink docs; Entire launch (entire.io, TechCrunch 2026-02-10).
