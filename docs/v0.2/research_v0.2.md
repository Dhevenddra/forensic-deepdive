# forensic-deepdive — Competitive Landscape, Hybrid Architecture, and v0.2 → v1.0 Roadmap

## TL;DR

- **You are not too late, but the window is closing fast.** Between mid-2025 and May 2026 the "code knowledge graph + MCP" category went from zero named tools to at least seven serious OSS entrants (GitNexus, CodeGraphContext, Understand-Anything, Graphify, codemap, DeepWiki-Open, plus Cognition's proprietary DeepWiki). GitNexus is the runaway leader at roughly 19–25k stars, single-maintainer, and crucially **PolyForm Noncommercial 1.0.0** — meaning the entire commercial market is currently unserved by the category leader. **That is your wedge.**
- **Build forensic-deepdive as the Apache-2.0, polyglot-bridging, git-archaeology-first, framework-aware competitor to GitNexus** — same MCP shape and graph depth, but commercial-safe, with two things GitNexus structurally cannot match: Spring/JSP/React cross-stack tracing (their own open issue #1225 admits this gap) and git archaeology as a first-class layer. Skip building yet another wiki generator (DeepWiki-Open already won that), skip vector-only RAG (Continue.dev is deprecating it for a reason), and do not try to beat Sourcegraph at compiler-precise indexing — **embed SCIP as a confidence-upgrade layer on top of Tree-sitter** instead.
- **Four-phase recut roadmap, no time estimates.** v0.2 is the big one (LadybugDB swap, 8+ language Tree-sitter, pipeline-DAG, 5 MCP tools, drop Repomix as primary). v0.3 adds Spring annotation resolution + React-to-API tracing + optional SCIP/LSP. v0.4 adds the Sigma.js viewer + traceability matrix. v1.0 hardens incremental indexing, ships the rename + cross_language_navigate tools, and adds optional Spring Actuator runtime augmentation. **If you can't ship v0.2 in the next quarter, reconsider** — at the current rate of entry there will be three to five more competitors by then.

---

## DELIVERABLE 1 — Competitive Landscape

### Tier 1 — Direct Competitors (deep dive)

#### GitNexus (abhigyanpatwari/GitNexus) — the one to beat

- **What it does well.** TypeScript monorepo with a Vite/React thin client; Tree-sitter parsing of 14 languages; a strict 12-phase ingestion DAG (`scan → structure → parse → routes/tools/orm → crossFile → mro → communities → processes`); LadybugDB (Kuzu fork) as the embedded graph backend; MCP server exposing 16 tools (`impact`, `query`, `context`, `cypher`, `detect_changes`, `rename`, `wiki`, etc.); Claude Code PreToolUse hooks that auto-enrich grep/glob/bash output; multi-repo registry at `~/.gitnexus/registry.json`; hybrid retrieval (BM25 + semantic + RRF); confidence scoring; community detection; AST decorator detection for `@Controller`, `@Get`, etc.; scope-resolution refactor (RFC #909) currently rolling Java, C, PHP, and C++ onto a registry-primary path. Velocity is real: 1.6.5 → 1.6.6 in weeks, 61 commits from 23 contributors (15 first-time). There is an "understand-quickly" public registry of code-knowledge graphs where gitnexus@1 is a first-class format.
- **Where it fails.** Licensed under **PolyForm Noncommercial 1.0.0** — every commercial user is locked out unless they buy an Akon Labs license that is not publicly priced; every analysis piece flags the licensing as the primary barrier to enterprise adoption. Single-maintainer bus factor (Abhigyan Patwari) flagged by every analysis piece. No git archaeology layer. No real framework-aware Spring analysis — their own open issue #1225 ("Improve analysis for Java projects built with Spring and Spring Boot") explicitly admits GitNexus may miss important relationships that determine how a Spring application actually behaves. No React-to-backend bridging. Browser WASM mode is memory-bounded for large repos. Incremental indexing only arrived in 1.6.5.
- **What we should steal.** Pipeline-as-DAG-of-phases shape; multi-repo registry pattern; MCP tool surface (`impact` / `query` / `context` / `cypher` / `detect_changes` / `rename`); Claude Code hook integration; the `gitnexus setup` editor-autodetect command; agent-skill emission; the `understand-quickly` registry idea.
- **License**: PolyForm Noncommercial 1.0.0.
- **Maturity signals**: 14 languages; LadybugDB; high commit velocity; the project even ships a published anti-impersonation notice about a cryptocurrency token using its name — that signals visibility, but also single-founder fragility.

#### Graphify (safishamsi/graphify) — the LLM-extraction-heavy alternative

- **What it does well.** NetworkX + Leiden clustering (graspologic) + Tree-sitter + vis.js; 20+ languages; multimodal ingestion (code, PDFs, screenshots, video via faster-whisper). The PyPI package is named **`graphifyy` (double-y)**. Most importantly: **EXTRACTED / INFERRED / AMBIGUOUS confidence tags** baked into every edge — this is genuinely innovative provenance UX. Ships as a "skill" loaded into Claude Code, Codex, Cursor, Aider, etc. Penpax is the upcoming commercial layer.
- **Where it fails.** LLM-heavy ingestion is expensive per repo and not deterministic; vis.js renderer is dated; no MCP server, no impact analysis, no call-graph rigor at function level. Optimized for "find the why" (NOTE/WHY/HACK extraction, god nodes, surprising connections), not refactor-safety.
- **What we should steal.** **The confidence taxonomy verbatim** (EXTRACTED/INFERRED/AMBIGUOUS). Rationale extraction from comments. The "graphs that teach" framing.
- **License**: MIT (per third-party coverage; confirm in repo).

#### Aider repo-map (aider.chat)

- Apache-2.0. The PageRank-on-Tree-sitter pattern you already ported. One-shot context packer; not a persistent graph. Continue.dev's `repo-map` provider was explicitly inspired by it. Nothing new to steal — you already have it.

#### DeepWiki (Cognition AI)

- Proprietary SaaS. Confirmed by Cognition to have indexed **"over 50,000 of the top public GitHub repos"** at launch per their own announcement. (Earlier circulating figures of a specific $300K compute cost were unverified by primary sources — treat as folklore.) Replaces `github.com` with `deepwiki.com` in URLs to read a generated wiki. Excellent for understanding, not for analyzing — no call graph, no impact analysis, no MCP, no local mode, closed source. Free for public repos, paid for private (Devin account required). Your data passes through their servers.
- **What to steal**: nothing architecturally. But the wiki-as-onboarding-document framing was validated to 50k+ repos. The market exists.

#### DeepWiki-Open (AsyncFuncAI/deepwiki-open)

- MIT, FastAPI + Next.js, roughly 15.7k stars per issue #96. Docker + Ollama mode (`Dockerfile-ollama-local`, defaults to `nomic-embed-text` + `qwen3:1.7b`). Supports GitHub/GitLab/Bitbucket. Generates Mermaid flow/sequence/architecture diagrams via LLM. RAG-based.
- **Where it fails.** Open issue #96 (May 2025) confirms it still does not support local-filesystem or self-hosted-Git repos. Vector-RAG only; no call graph; no impact analysis; no MCP server; no incremental indexing.
- **What to steal.** The Ollama-local pattern (`DEEPWIKI_EMBEDDER_TYPE=ollama`, two-Dockerfile split, curated small-model list).

#### Sourcegraph SCIP — the precision backbone we shouldn't try to beat

- Apache-2.0. **Transitioning to independent governance with a Core Steering Committee including engineers from Uber and Meta**, with a formal SCIP Enhancement Proposal (SEP) RFC process. LSIF → SCIP migration completed in Sourcegraph 4.6. Indexers exist for roughly 10 languages: `scip-typescript`, `scip-java` (Gradle/Maven/sbt auto-detect, ~108 stars, 30 contributors per Scaladex), `scip-python`. Designed for compiler-accurate precise navigation across repos.
- **Where it fails (for our use case).** SCIP is not a knowledge graph — it's a Protobuf symbol/reference index. No MCP server, no framework-awareness (scip-java treats `@Autowired` as a plain annotation), no impact analysis, no git archaeology.
- **What to steal.** **Ingest SCIP optionally as a confidence-upgrade layer.** When `index.scip` exists or `scip-*` is on PATH, mark every edge it confirms as `EXTRACTED` instead of `INFERRED`. Massive precision boost for free.

#### Semgrep / OpenGrep

- Pattern-based cross-language scanning, security-first. OpenGrep is the community fork escaping Semgrep's licensing friction. Excellent for "find this pattern across N languages" but not a graph — no edges, only hits. **Skip**, unless you want to embed Semgrep rules as a secondary signal later.

#### CodeQL (GitHub)

- Datalog-flavored QL over compiled databases. AST + CFG + DFG + type info + call graphs for C/C++/C#/Go/Java/Kotlin/JavaScript/TypeScript/Python/Ruby/Swift/Rust. Ships `SpringController`, `SpringRequestMappingMethod`, `SpringBean`, `SpringComponent` in `java/ql/lib/semmle/code/java/frameworks/spring/`. **License is restrictive for non-OSS commercial use**; OSS use is free via GitHub Advanced Security. Heavy build-integration overhead.
- **What to steal**: **the Spring annotation modeling in the CodeQL `frameworks/spring/` library is MIT-licensed**. Read it as a spec and replicate the classifier logic in Tree-sitter queries + ast-grep rules.

### Tier 2 — The Field We Found Beyond the Brief

#### CodeGraphContext (CodeGraphContext/CodeGraphContext) — your real competitor

- **MIT, ~2,200 stars**, Python, MCP + CLI. Default backend **KuzuDB embedded**, with FalkorDB Lite (Unix/macOS) and Neo4j as alternative backends. Live `watchdog` updates. Markets itself explicitly as *"the MIT-licensed alternative to GitNexus."*
- **Implication: Apache-2.0 alone is not differentiation.** CodeGraphContext beat you to "the MIT alternative." Your wedge must be substantive features.
- **Where it fails.** Python (slower than TS for large repos), shallower MCP tool set than GitNexus, no git archaeology, no framework-awareness, no React-to-backend bridging.

#### Understand-Anything (Lum1104/Understand-Anything) — the visual-dashboard leader

- MIT, around 15k stars by May 2026. Claude Code plugin (also Cursor, Codex, Gemini, Copilot, Antigravity). 5-agent multi-pipeline. Output is `.understand-anything/knowledge-graph.json` consumed by a React Flow dashboard. **Token-expensive on initial scan** (calls Claude per significant file).
- **What to steal.** React Flow dashboard quality; the "graphs that teach, not graphs that impress" framing; guided architecture tours ordered by dependency; `--language` localization; **JSON-as-output decoupling between indexer and viewer.**

#### codemap (grahambrooks/codemap)

- MIT Rust binary derivative of Colby McHenry's `codegraph`. Demonstrates that Rust-compiled MCP binaries deploy more cleanly than Node.js MCPs.

#### Continue.dev codebase indexing

- Apache-2.0, ~30.5k stars. DFS walker → tree-sitter chunking → LanceDB embeddings + SQLite metadata. Their `repo-map` provider was explicitly inspired by Aider's. Local-by-default via `transformers.js` (JetBrains gap noted). **`@Codebase` is being deprecated in favor of a new codebase-awareness API** — Continue is migrating away from the pure-embedding approach, which is the most important signal in the entire landscape: **vector-only RAG is being abandoned in favor of structural retrieval.**
- **What to steal.** Local `transformers.js`; LanceDB as embedded vector store (alternative to LadybugDB FTS); the deprecation as a tactical confirmation.

#### Cursor `@codebase`

- Closed source; architecture is public. Local Merkle-tree-of-hashes chunking (around 3.2 MB metadata for 50,000 files). Upload chunks to server. Embeddings via OpenAI / proprietary model. **Turbopuffer remote vector DB.** Periodic 5-minute resync. Cached on AWS by chunk hash. Path obfuscation by encrypting URL segments. Pure vector RAG, no graph.
- **What to steal.** The Merkle-tree-of-hashes pattern for cheap incremental indexing.

#### Glean (facebookincubator/Glean)

- BSD. Meta's open code-indexing system. Designed around an efficient storage model for facts about source code. **Glass** is the symbol-server layer above Glean providing language-agnostic API including cross-language navigation (RPC, FFI). At Meta covers C++/Python/PHP/JavaScript/Rust/Erlang/Thrift/Haskell. **Hard to build** (Folly + RocksDB + GHC). Not turnkey.
- **What to steal.** The Glass-style "single API call returns symbol with definitions + references + cross-language hops" abstraction — bake into our `context` MCP tool. The cross-language navigation framing where RPC and FFI are first-class edges.

#### ast-grep

- Apache-2.0, Rust, Tree-sitter native structural search and rewrite. Custom language registration. Latest is 0.42.3 from May 2026. There is an `ast-grep-mcp` server.
- **What to steal.** **Use ast-grep YAML rules as the framework-awareness DSL.** Spring annotation detection ("any class with `@RestController` is a route handler") expressed as YAML rules shipped as data — adding framework support becomes a data PR, not a code PR.

#### Sourcetrail — DEAD, but with active forks

- Archived by Coati Software end of 2021. **petermost** fork has releases as late as 2025.6.19; Quarkslab's **NumbatUI** fork repurposes it for reverse engineering. **Skip building anything inspired by its desktop Qt UI directly.** But the three-pane Graph/Code/Search model is timeless, and Understand-Anything's React Flow dashboard is a modern reimagining.

#### Understand (SciTools) — commercial, ~$195+/license, 70+ languages. Not an OSS-space competitor.

### Spring / Java framework-awareness (gap is real)

- **Jasmine** (SpringJasmine/Jasmine) — ASE'22 research artifact, Soot-based, resolves Spring DI + AOP into synthesized methods. No LICENSE file. Activity dropped after 2023. ~40 stars.
- **ArchUnit** (TNG/ArchUnit) — Apache-2.0, ~3.6k stars, bytecode-based architecture-rule tester. Reads annotations but tests architecture; doesn't emit a graph.
- **archunit-spring** (rweisleder/archunit-spring) — Apache-2.0, ~150 stars. Predefined Spring rules with meta-annotation/alias resolution (`@GetMapping` recognized as `@RequestMapping`).
- **OpenRewrite FindCallGraph + rewrite-spring** — Apache-2.0, ~530 stars on rewrite-spring. `org.openrewrite.FindCallGraph` recipe emits method-call data tables over the LST. rewrite-spring contains hundreds of Spring-aware recipes (Boot 1→2→3 migrations, profile splits, bean renaming).
- **Spring Sentinel** (pagano-antonio/SpringSentinel) — Apache-2.0, new in 2025, linter-class, finds `@Autowired` field injection / eager JPA / N+1 patterns.
- **CodeQL Spring library** — MIT, classifier spec.
- **scip-java does NOT have Spring resolvers.**
- **spring-graph / soot-spring / WALA-Spring extensions** do NOT exist as OSS projects. SpringInsight was a defunct VMware/Pivotal commercial product.

### React-to-Spring API tracing — the biggest gap

**There is no widely-adopted OSS tool that statically links a React `fetch()`/`axios` call to a Spring `@RequestMapping`-annotated method.** Closest neighbors:
- **scip-typescript** (Apache-2.0, ~330 stars) — cross-repo symbol navigation, but no URL ↔ controller resolution.
- **OpenAPI Generator** + **springdoc-openapi** (Apache-2.0, ~22k stars) — the de facto bridge, requires the OpenAPI spec.
- **orval** (MIT) — TS-first React Query hook generation from OpenAPI.
- **Restler** (excelsior-oss/restler, Apache-2.0) — runtime Spring-annotation → client generator.
- **EndpointFinder** (ettic-team) — pen-test recon JS endpoint extractor.
- Academic precedent: **Wittern et al. 2017 "Statically Checking Web API Requests in JavaScript"** — no maintained 2024–2026 successor. **Build this.**

### JSP / JSF static analysis — confirmed dying

- **static-jsfexpression-validator** (holyjak, MIT/Apache, semi-dormant since 2020) — only OSS that statically resolves JSF EL.
- **Nablarch JSP Static Analysis Tool** — Apache-2.0, still released in 2024–2025; enforces allowed taglibs / EL.
- **Apache Tomcat Jasper** — Apache-2.0, the parsing backbone everyone reuses.
- **OpenRewrite `JakartaFacesXhtmlEE10`** — text-level migration recipe.
- **Don't invest in deep JSP support.** Tree-sitter has a JSP grammar — use it for shallow file → handler-class extraction and stop there.

### Traceability matrix (underserved adjacent category)

- **OpenFastTrace (OFT)** — **GPL-3.0** (Apache-2.0 incompatible for bundling), ~140 stars, mature. `req~name~1`, `feat~name~1`, `impl~name~1`, `utest~name~1` markers; Markdown / RST / ReqIF. Used in safety-critical projects.
- **StrictDoc** — Apache-2.0, ~750 stars, very active. SDoc DSL + ReqIF round-trip + Sphinx pipeline + web UI. The OSS-friendly upgrade from Doorstop.
- **Doorstop** — LGPL-3.0, ~576 stars, Python YAML-per-item.
- **Sphinx-Needs** (useblocks) — MIT, ~600+ stars; their FAQ confirms real ISO 26262 automotive use.
- **mlx.traceability** (Melexis fork) — GPL-3.0, `:fulfilled_by:` / `:tested_by:` directives.
- **Eclipse Capra** — EPL-2.0, ISO 26262 / ASPICE / IEC 62304 grade, ships adapters for Java/C/Python/Mylyn/Jenkins/EMF/UML/SysML/AADL/Capella/ReqIF.
- **No code-knowledge-graph product integrates a traceability matrix today.** Unclaimed wedge.

### Graph DB landscape — critical update

- **Kuzu was acquired by Apple in October 2025 and the GitHub repo was archived the same day.** The acquisition surfaced via an EU Digital Markets Act filing, spotted by AppleInsider and reported by MacRumors on Feb 11, 2026 (`macrumors.com/2026/02/11/apple-acquires-new-database-app/`). **LadybugDB** (founded by Arun Sharma) is the live community fork; **Vela Partners** maintains a separate fork at `Vela-Engineering/kuzu` with concurrent-write support (claims roughly 374x faster than Neo4j on their benchmarks). GitNexus and CodeGraphContext already use LadybugDB. Kuzu's original license was MIT.
- **Neo4j** — Cypher reference but ingestion roughly 18x slower than Kùzu on around 100K nodes and 2.5M edges per Prashanth Rao's published Sep 9, 2023 benchmark on The Data Quarry.
- **FalkorDB** — source-available (not OSI-approved), GraphBLAS-backed, HNSW vectors, strong GraphRAG positioning.
- **Memgraph** — BSL 1.1, roughly $25K/year commercial; documented stability issues.
- **ArcadeDB** — **Apache-2.0, multi-model (graph/document/KV), Cypher TCK pass rate around 97.8%, BOLT protocol compatibility with Neo4j drivers, no data caps.** Real Apache-2.0 alternative for server-mode deployment.
- **DuckDB-graph** — extension exists but immature for our use.
- **Recommendation: LadybugDB embedded by default**, matching GitNexus, but architect the graph layer behind a `GraphStore` interface so swap to ArcadeDB (server-mode for huge repos) is plumbing, not surgery.

### Rate-of-change signal

From mid-2025 to May 2026 the category went from zero to seven serious OSS entrants with roughly 70k+ combined stars. Cursor and Anthropic both shipped MCP standardization in March 2025; MCP was donated to the Linux Foundation Agentic AI Foundation in December 2025 with OpenAI and Block backing. **This is accelerating, not plateauing.** Expect 3–5 more entries by Q3 2026. **The window for forensic-deepdive to claim "the Apache-2.0 polyglot one with Spring + git archaeology" is roughly the next two release cycles.**

---

## DELIVERABLE 2 — Hybrid Architecture (v0.2 → v1.0)

Every layer below names the tool we learn from and what we change.

### Parsing layer
- **Tree-sitter primary**, grammar priority: TypeScript → JavaScript → Python → Java → Go → Rust → C/C++ → Ruby → C# → Kotlin → Swift → Dart → JSP (shallow) → SQL → YAML/JSON (for `application.yml`, OpenAPI, `package.json`, `pom.xml`, `build.gradle`).
- **LSP integration** (tsserver, pyright/pylsp, gopls, jdtls, rust-analyzer) — **on-demand only** during call resolution when Tree-sitter has ambiguity. Don't make LSP the primary path; that's how Sourcetrail died (heavyweight Clang index up-front).
- **SCIP ingestion**: if `index.scip` exists or `scip-typescript`/`scip-java` is on PATH, optionally invoke and merge. Use SCIP edges to upgrade `INFERRED` → `EXTRACTED`. **This is the precision wedge we get for free.**
- **ast-grep YAML rules**: framework detection (Spring, React, FastAPI, Express, Rails, Django) is shipped as YAML packs in `frameworks/<name>/*.yml` — adding framework support is a data PR, not a code PR.
- **Tree-sitter WASM web mode**: optional, deferred to v1.0.

### Graph layer
- **LadybugDB embedded by default** (matching GitNexus, KuzuDB-derived, MIT). Vectorized OLAP, columnar, schemaful, single-file deploy, embedded FTS and vector indexes.
- **Schema** — nodes: `File`, `Symbol`, `Function`, `Class`, `Method`, `Interface`, `Module`, `Route`, `Bean`, `Component`, `Process`, `Requirement`, `Test`, `Commit`, `Author`. Edges: `CALLS`, `IMPORTS`, `EXTENDS`, `IMPLEMENTS`, `DEFINES`, `MEMBER_OF`, `HANDLES_ROUTE`, `INJECTS`, `DECLARES_BEAN`, `RENDERS`, `HANDLES_EVENT`, `SCHEDULED_BY`, `FETCHES_FROM`, `TESTED_BY`, `COVERS_REQUIREMENT`, `TOUCHED_BY_COMMIT`, `AUTHORED_BY`, `STEP_IN_PROCESS`.
- **Adapter pattern**: `GraphStore` interface so we can swap to ArcadeDB / Neo4j / DuckDB later. GitNexus locked into Lbug; we won't.
- **Persistence**: `.deepdive/lbug` per-repo, `~/.deepdive/registry.json` global multi-repo, `~/.deepdive/cache/` parse cache hashed by file SHA + grammar version (Cursor pattern).

### Search layer
- **Tri-modal retrieval**: BM25 (LadybugDB FTS) + semantic (LadybugDB vector index, embeddings via `transformers.js` locally à la Continue.dev with `nomic-embed-text` default) + structural (Cypher) — fused via Reciprocal Rank Fusion as GitNexus does.
- **Fourth ranking signal — commit recency / hotness from git archaeology.** GitNexus has no git archaeology. A "recently changed by many authors" node should boost.

### Call-graph construction
- **Tree-sitter extract phase** emits `INFERRED` edges using receiver-type heuristics (constructor inference, `self`/`this` mapping, import resolution, MRO traversal — borrow GitNexus's MRO phase verbatim from their published architecture doc).
- **LSP/SCIP refine phase** upgrades `INFERRED` → `EXTRACTED`.
- **Framework resolution phase**:
  - **Spring**: parse `@Autowired`, `@Component`/`@Service`/`@Controller`/`@RestController`, `@Bean`, `@RequestMapping`/`@GetMapping`/`@PostMapping`/`@PutMapping`/`@DeleteMapping`/`@PatchMapping`, `@EventListener`, `@Scheduled`, `@ConfigurationProperties`, `@Transactional`. Emit `INJECTS`, `DECLARES_BEAN`, `HANDLES_ROUTE`, `HANDLES_EVENT`, `SCHEDULED_BY`, `BINDS_PROPERTY` edges. **Replicate classifier logic from CodeQL's MIT-licensed `java/ql/lib/semmle/code/java/frameworks/spring/` library.** Bridge IoC by routing virtual dispatch through declared `@Service` impls.
  - **React**: parse hooks (`useEffect`, `useQuery`, `useMutation`), component composition, `fetch(...)`, `axios.{get,post,put,delete}`, generated OpenAPI clients (`orval`-style hooks), `next/router`, `react-router`, Next.js app router. Emit `FETCHES_FROM` edges with URL pattern + method.
  - **JSP**: shallow only — extract `<%@ page import=…>`, `useBean`, taglib usage; emit `FILE` → `CLASS` `RENDERED_BY` edges.
- **Cross-language joiner** — match `FETCHES_FROM("/api/users", GET)` against `HANDLES_ROUTE("/api/users", GET)` and emit `CALLS` with `confidence=INFERRED`. Upgrade to `EXTRACTED` when OpenAPI spec confirms. **This is the polyglot wedge no OSS competitor has.**

### Polyglot strategy
- String-literal coincidence is the baseline (URLs, RPC names, FFI symbol names).
- OpenAPI / AsyncAPI / Protobuf / Thrift specs upgrade to `EXTRACTED`.
- SCIP cross-repo symbol references upgrade further.
- For RPC/FFI: Glean/Glass framing — `cross_language_navigate` MCP tool returning the symbol on the other side of the boundary.

### Impact analysis algorithm
- Forward BFS from selected symbol over `CALLS` / `IMPORTS` / `DEFINES` / `HANDLES_ROUTE` / `FETCHES_FROM`. Depth-grouped buckets (1-hop / 2-hop / 3+hop). Confidence-weighted blast radius: `EXTRACTED` contributes 1.0, `INFERRED` 0.6, `AMBIGUOUS` 0.3. **Add commit-archaeology dimension**: which authors most recently touched each blast-radius node = who to assign the PR review to.

### Execution flow tracing
- Entry-point detection: HTTP routes (Spring/Express/FastAPI/Django/Rails/Next.js), event listeners (Spring `@EventListener`, Node EventEmitter, BLE callbacks for Omi), CLI (`main`, `if __name__ == '__main__'`), Lambda handlers, cron/scheduled.
- DFS through `CALLS` bounded by depth and language boundaries; breadth pruning at >10 callees.

### Traceability matrix
- **Requirement markers**: scan for **OpenFastTrace-compatible** `req~name~1` / `feat~name~1` / `impl~name~1` / `utest~name~1` in commit messages, docstrings, comments, and Markdown. Plus ticket references (`Closes #123`, `JIRA-456`, `Refs PROJ-789`) — de-facto requirements in most codebases.
- **Test ↔ code**: parse test files, link by import + naming convention + coverage-file ingestion (`coverage.xml`, `lcov.info`).
- Emit `TRACEABILITY.md` + `traceability.json`. We are Apache-2.0; OFT is GPL-3.0, so we don't bundle their code, we match their grammar.

### MCP server design
- **5 tools at v0.2**, growing to 9 by v1.0. **Keep tool count low** — Harness MCP v2 lesson, Klavis "Less is More" analysis, Anthropic context-budget concerns: Cursor + Claude Code already eat 5–10% of context on tool metadata before a prompt.
  - v0.2: `impact(symbol, depth)`, `query(cypher | natural_language)`, `context(symbol)` (Glass-style single-call returns def + callers + callees + tests + commits + authors), `flow(entry_point)`, `archaeology(file_or_symbol)`.
  - v0.3: `+ detect_changes(git_diff)` (GitNexus shape).
  - v0.4: `+ trace(requirement_or_ticket)`.
  - v1.0: `+ rename(symbol, new_name)`, `+ cross_language_navigate(symbol)`.
- Composite-not-mirror design. Tool descriptions ≤ 200 tokens each.
- stdio transport primary; HTTP-SSE for the web UI.

### Visual viewer
- **Sigma.js + graphology** (WebGL, scales to 10k+ nodes — Sigma.js's own homepage demos BGP-internet-scale graphs). Cytoscape.js only as fallback when a specific Cytoscape layout is needed.
- Client-side rendering of pre-computed layouts emitted by the indexer as JSON.
- Three-pane Sourcetrail layout (Graph / Code / Search) reborn in Understand-Anything's React Flow dashboard — copy this shape.
- ForceAtlas2 pre-computed during indexing with hash-seeded determinism. Communities (Leiden via `graphology-communities-louvain`) collapse to super-nodes by default.

### Agent integration (multi-platform skill emission)
- On `analyze`, emit:
  - `.claude/skills/forensic-deepdive-*.md` (Exploring, Refactoring, Debugging, Reviewing-PR, Onboarding, Tracing, Spring, React)
  - `.claude-plugin/plugin.json` + Claude Code hooks
  - `.cursor/rules/*.mdc`
  - `AGENTS.md` and `CLAUDE.md`
  - `.continue/config.yaml`
  - `.copilot-plugin/plugin.json` (VS Code Copilot v1.108+)
- Steal Understand-Anything's broad-platform framing: one tool, many editors. Steal GitNexus's `setup` auto-detect.

### Git archaeology — first-class differentiator
- Per-file and per-symbol churn (commits/month, authors, last-touched)
- Co-change clusters (files frequently committed together = implicit modules)
- Authorship/expertise graph (recent commits → owner)
- Bus factor per symbol
- Refactor history via `git log --follow`
- Defect proximity (files frequently touched in commits mentioning `fix`/`bug`/`regression`)
- Surface via `archaeology` MCP tool and `ARCHAEOLOGY.md` artifact.
- Algorithm: incremental git-log walk; on-disk cache keyed by HEAD-SHA delta.

### Persistence and incremental indexing
- **Merkle-tree-of-hashes** (Cursor pattern). Sync walks only branches where hashes differ.
- Embedding cache keyed by chunk content hash.
- Skip re-index when `lastCommit == HEAD` (GitNexus pattern).
- Multi-repo registry at `~/.deepdive/registry.json`.
- Optional `deepdive publish` to the `understand-quickly` registry (gitnexus@1 is already a first-class format there — same format = free interop).

### Confidence taxonomy (graphify pattern, productized)
- **EXTRACTED** — Tree-sitter + LSP/SCIP/compiler confirmation, or explicit framework annotation. Edge weight 1.0.
- **INFERRED** — Tree-sitter heuristic or string-literal cross-language match. Edge weight 0.6.
- **AMBIGUOUS** — Multiple possible targets (interface dispatch with N implementations and no narrowing context). Edge weight 0.3, surface all candidates.
- Every MCP response carries confidence; every visual edge is color-coded; every markdown artifact tags claims with confidence.

### Local-only mode (mandatory for v1.0)
- Ollama and LM Studio via OpenAI-compatible endpoints (DeepWiki-Open pattern: `DEEPDIVE_EMBEDDER_TYPE=ollama`, two-Dockerfile split).
- Curated default models:
  - Embeddings: `nomic-embed-text` (Continue/DeepWiki-Open default), `Snowflake/snowflake-arctic-embed-xs` (384-dim, fast).
  - Generation (only for narrative artifacts): `qwen3:1.7b` (DeepWiki-Open default), `llama3.1:8b`, `gpt-oss-120b` if available.
- Structured output via constrained-JSON decoding (Ollama `format=json`, LM Studio `response_format`).
- **Mandatory pure-deterministic mode**: index → graph → MCP without any LLM. LLM is optional and only used for narrative artifacts. This is what makes us defensible vs. Graphify (LLM-heavy) and DeepWiki-Open (LLM-required).

### Five-artifact contract (recut)
- Keep markdown artifacts for human/agent consumption: `MAP.md`, `HOTPATHS.md`, `ARCHAEOLOGY.md`, `MENTAL_MODEL.md`, `AGENT_BRIEF.md`.
- Add structured artifacts: `graph.lbug` (binary), `graph.json` (portable export), `TRACEABILITY.md` + `traceability.json` (v0.4), `architecture.svg` (Sigma.js pre-rendered fallback for PR review).
- **Drop Repomix as a primary output.** Move to `--legacy-repomix` flag.

### Wedges (where we beat the field, not parity)
1. **Apache-2.0** — beats GitNexus (PolyForm Noncommercial), beats CodeQL (restrictive non-OSS commercial), beats DeepWiki (SaaS only). **Necessary but not sufficient.**
2. **Git archaeology as a first-class layer.** Nobody in the OSS code-graph category has this. CodeScene has it but is closed and SaaS.
3. **Cross-stack polyglot (React → Spring, etc.) via OpenAPI + string-literal + SCIP joiner.** Does not exist as an OSS tool. Genuinely new ground.
4. **Spring/JSP framework-awareness as ast-grep YAML rule packs** — extensible by users.
5. **Confidence taxonomy on every edge and every response** — Graphify has the idea; we make it product-grade and queryable (`query: edges where confidence=AMBIGUOUS`).
6. **Traceability matrix integrated with the code graph** — OpenFastTrace/StrictDoc are standalone; we're first to integrate.
7. **Deterministic pure-static mode** at full feature parity with the LLM-augmented mode. Graphify and Understand-Anything cannot do this.
8. **Local-first AND MCP-first AND viewer AND skills.** Most competitors pick two or three.

---

## DELIVERABLE 3 — Recut Roadmap (v0.2 → v1.0)

No time estimates per your spec. Each phase ends in a measurable, testable artifact.

### v0.2 — "From orienter to knowledge layer" (the big phase)

**What's added**
- Replace existing graph backend with LadybugDB (embedded, schemaful).
- Tree-sitter grammars: add TypeScript, JavaScript, Java, Go, Rust to existing Python/C/Dart/Swift (8+ languages baseline).
- Pipeline-as-DAG-of-typed-phases (GitNexus shape) with phase-plugin interface for future framework rule packs.
- Confidence taxonomy on every edge (EXTRACTED / INFERRED / AMBIGUOUS).
- MCP server with 5 tools: `impact`, `query`, `context`, `flow`, `archaeology`.
- Agent skill emission: `AGENTS.md`, `CLAUDE.md`, `.claude/skills/*.md` (minimum 5 skills).
- Five markdown artifacts retained, refactored to read from the graph.
- `graph.json` portable export.
- Repomix moved to `--legacy-repomix` flag.
- Multi-repo registry at `~/.deepdive/registry.json`.

**Deferred** — Spring/React framework-awareness (v0.3), visual viewer (v0.4), traceability matrix (v0.4), Merkle-tree incremental indexing (v1.0), LSP/SCIP integration (v0.3).

**Acceptance criteria**
- Index Omi (1,860 files) in ≤ 120s on commodity laptop.
- Index GitNexus's own repo (TS-heavy) successfully.
- MCP server with 5 tools registers in Claude Code, Cursor, Codex via standard `mcp add` commands.
- `impact(symbol, depth=3)` returns ranked blast radius with confidence labels.
- `archaeology(file)` returns churn, authors, co-change cluster, last-touched commit.
- All 5 markdown artifacts regenerate from graph deterministically.
- **Pure-static mode (no LLM) produces all of the above.**

**DEC entries**: DEC-013 (LadybugDB), DEC-014 (Pipeline-DAG), DEC-015 (Confidence taxonomy), DEC-016 (MCP tool surface), DEC-017 (Drop Repomix as primary), DEC-018 (Multi-repo registry).

**Risks and mitigations**
- *LadybugDB single-maintainer risk* — abstract behind `GraphStore` so ArcadeDB or DuckDB swap is mechanical.
- *Tree-sitter Java grammar fidelity on Spring code* — accept INFERRED in v0.2; refine in v0.3.
- *MCP context-window budget* — 5 tools, ≤ 200 tokens each.

**Test repos**: Omi (Python/C/Dart), GitNexus repo itself (TS), `tiangolo/fastapi` (Python web framework).

### v0.3 — "Framework-aware polyglot"

**What's added**
- Spring annotation resolution (full `@Component`/`@Service`/`@Controller`/`@RestController`/`@Bean`/`@Autowired`/`@RequestMapping`-family/`@EventListener`/`@Scheduled`/`@ConfigurationProperties`/`@Transactional`) as ast-grep YAML rule packs replicating CodeQL Spring library classifier logic.
- React component composition + hook detection (`useEffect`, `useQuery`, `useMutation`, `axios.*`, `fetch(...)`).
- OpenAPI spec ingestion (springdoc, swagger-codegen output, native FastAPI specs).
- **Cross-language joiner**: React `FETCHES_FROM` ↔ Spring `HANDLES_ROUTE` → `CALLS` edges with confidence chain.
- LSP integration on-demand: tsserver, pyright, gopls, jdtls, rust-analyzer.
- SCIP ingestion when `index.scip` present or `scip-*` on PATH.
- Add languages: full C/C++, C#, Kotlin, Ruby.
- New MCP tool: `detect_changes(git_diff)`.

**Deferred**: visual viewer (v0.4), traceability matrix (v0.4).

**Acceptance criteria**
- On `spring-projects/spring-petclinic`, `impact(SomeController.method)` correctly identifies frontend pages calling it within ≤ 2 hops.
- On a React+Spring monorepo, `FETCHES_FROM(/api/X)` ↔ `HANDLES_ROUTE(/api/X)` join produces ≥ 90% recall on routes documented in OpenAPI; ≥ 60% recall on undocumented `fetch()` calls.
- SCIP ingestion upgrades ≥ 95% of edges in repos with SCIP dumps.
- ast-grep YAML rule packs loadable from `~/.deepdive/frameworks/` (user-extensible).

**DEC entries**: DEC-019 (ast-grep YAML as framework DSL), DEC-020 (SCIP optional ingestion), DEC-021 (Cross-language join), DEC-022 (OpenAPI/AsyncAPI primary contract source), DEC-023 (LSP on-demand only).

**Risks**
- *Spring meta-annotation resolution* — use archunit-spring as reference + CodeQL Spring lib as spec.
- *React routing diversity* (react-router v5/v6/v7, Next.js app router, Remix, TanStack) — ship rule packs per-router; accept partial coverage; expand in v1.0.

**Test repos**: `spring-projects/spring-petclinic`, Next.js examples, a curated React + Spring monorepo (e.g., okta-spring-boot examples), `home-assistant/core`.

### v0.4 — "See it and trace it"

**What's added**
- Visual viewer: Sigma.js + graphology, WebGL, Vite/React, three-pane Graph/Code/Search.
- ForceAtlas2 pre-computed; Leiden community collapse; hash-seeded determinism.
- Pre-rendered SVG export (`architecture.svg`) for GitHub PR review.
- **Traceability matrix** (OpenFastTrace-compatible markers, ticket references, coverage ingestion).
- New MCP tool: `trace(requirement_or_ticket)`.

**Acceptance**
- Viewer loads 5,000-node graph in ≤ 3s on commodity laptop; pan/zoom interactive at 60fps.
- Traceability matrix links ≥ 80% of `Closes #X` PRs to merged test files in a curated reference repo.
- Confidence color-coding visible on every edge.

**DEC entries**: DEC-024 (Sigma.js + graphology), DEC-025 (OpenFastTrace marker compatibility), DEC-026 (Pre-rendered SVG for PR review).

**Test repos**: spring-petclinic, `itsallcode/openfasttrace` itself (self-traceability), plus v0.2/v0.3 repos.

### v1.0 — "Production"

**What's added**
- Merkle-tree-of-hashes incremental indexing (Cursor pattern); embedding cache by chunk hash.
- `deepdive publish` to `understand-quickly` registry (opt-in via env var, like GitNexus).
- `rename(symbol, new_name)` MCP tool (multi-file refactor planner; returns diff, doesn't write).
- `cross_language_navigate(symbol)` MCP tool (Glass-style RPC/FFI hop).
- Production Spring coverage: AOP advice resolution, third-party starter auto-registration, `@ConditionalOnX` evaluation, classpath scanning.
- JSP shallow extraction (taglib, useBean, scriptlets).
- 15+ languages.
- Docker images (`Dockerfile` + `Dockerfile-ollama-local`).
- HTTP MCP transport for remote / team mode.

**Acceptance**
- Incremental re-index after a 10-file change completes in ≤ 5s on a 10,000-file repo.
- Spring Boot reference repo's static graph matches the runtime ApplicationContext bean graph at ≥ 90% precision and recall against Spring Actuator `/beans` ground truth.
- MCP server handles 9 tools while keeping tool-description tokens ≤ 3,500 (Harness v2 envelope).
- Multi-repo monorepo: index 5-service Spring monorepo and resolve cross-service edges.

**DEC entries**: DEC-027 (Merkle tree incremental), DEC-028 (Registry publish), DEC-029 (rename tool semantics), DEC-030 (Optional Actuator runtime augmentation).

**Risks**
- *Feature creep* — explicitly defer GraphRAG-style chat-with-repo. We are not a wiki.
- *Spring AOP correctness* — accept INFERRED; document limitations honestly.

**Test repos**: spring-petclinic, curated enterprise Java monorepo, `home-assistant/core` (Python scale), `microsoft/vscode` (TS scale), `golang/go` (Go scale).

---

## DELIVERABLE 4 — DECISIONS.md Entries (DEC-013 → DEC-030)

**DEC-013 — Adopt LadybugDB as the embedded graph backend**
- *Date*: v0.2 planning. *Status*: Accepted.
- *Context*: Need an embedded, schemaful, vectorized OLAP graph DB scaling to ~10k–500k nodes with sub-second multi-hop queries. Kuzu was acquired by Apple in October 2025 and the GitHub repo archived; LadybugDB is the live community fork that GitNexus and CodeGraphContext already use.
- *Decision*: Use LadybugDB; wrap behind a `GraphStore` interface to allow later swap to ArcadeDB (Apache-2.0, multi-model, 97.8% Cypher TCK) or DuckDB-graph.
- *Rationale*: Matches the de-facto category choice; embedded (no server ops); openCypher; FTS + vector indexes built-in.
- *Consequences*: Bound to a single-maintainer fork; abstraction adds modest overhead; future migration path preserved.

**DEC-014 — Pipeline as a DAG of typed phases**
- *Status*: Accepted.
- *Context*: GitNexus's 12-phase pipeline (`scan → structure → parse → routes/tools/orm → crossFile → mro → communities → processes`) is the industry-converging shape.
- *Decision*: Adopt the same shape with a phase-plugin interface for framework rule packs.
- *Rationale*: Topological-sort validation; type-safe phase outputs; testable in isolation; future-proof.
- *Consequences*: Higher upfront design cost; pays back at v0.3.

**DEC-015 — Confidence taxonomy on every edge (EXTRACTED / INFERRED / AMBIGUOUS)**
- *Status*: Accepted.
- *Context*: Graphify proved the model. GitNexus has internal confidence scoring but does not surface it consistently.
- *Decision*: Every edge carries a confidence enum; every MCP response includes confidence; viewer color-codes by confidence.
- *Rationale*: Honest provenance is a wedge; agents make better decisions with confidence-aware context.
- *Consequences*: Schema + UI overhead; every framework rule must declare default confidence.

**DEC-016 — MCP server with composite tools, not endpoint mirrors**
- *Status*: Accepted.
- *Context*: Harness MCP v2 lesson on context budget; Cursor/Claude Code already eat 5–10% on tool metadata before a prompt.
- *Decision*: 5 tools at v0.2, 9 by v1.0; tool descriptions ≤ 200 tokens each.
- *Rationale*: Fewer, richer tools beat many narrow tools at agent ergonomics.
- *Consequences*: Each tool internally orchestrates several graph queries.

**DEC-017 — Drop Repomix as primary artifact**
- *Status*: Accepted. *Rationale*: Repomix is a context-packer; the graph + MCP supersedes that role. *Consequences*: Document migration for early users.

**DEC-018 — Multi-repo registry at `~/.deepdive/registry.json`**
- *Status*: Accepted. *Rationale*: GitNexus pattern works; enables MCP to serve multiple repos. *Consequences*: Cross-repo symbol-name conflict resolution required.

**DEC-019 — ast-grep YAML rule packs as the framework DSL**
- *Status*: Accepted (v0.3).
- *Context*: Framework-awareness must be extensible without recompiling; ast-grep already proved the rule-pack model.
- *Decision*: Framework support shipped as `frameworks/<name>/*.yml` ast-grep rule files with a small extension declaring graph-edge emissions.
- *Rationale*: Community can contribute frameworks; transparent; reproducible.
- *Consequences*: Extend ast-grep's rule schema or wrap; ship a contributor guide.

**DEC-020 — SCIP ingestion as a confidence-upgrade layer (optional)**
- *Status*: Accepted (v0.3). *Rationale*: Don't compete with SCIP; ride it. When SCIP dumps exist, bulk-upgrade INFERRED → EXTRACTED. *Consequences*: Optional dependency on `scip-*` indexers; clearly documented as precision upgrade.

**DEC-021 — Cross-language join algorithm (FETCHES_FROM × HANDLES_ROUTE)**
- *Status*: Accepted (v0.3). *Decision*: String + method matching at URL/method granularity, with OpenAPI preferred when present. *Rationale*: No OSS tool does this today; primary wedge. *Consequences*: False positives possible; confidence enforces honesty.

**DEC-022 — OpenAPI/AsyncAPI as primary API contract source**
- *Status*: Accepted. *Rationale*: De-facto standard widely emitted by Spring (springdoc), Express (swagger-jsdoc), FastAPI (built-in), Go (gin-swagger). *Consequences*: Fall back to annotation parsing when absent.

**DEC-023 — LSP integration on-demand only, never primary**
- *Status*: Accepted. *Rationale*: LSP is heavy; Tree-sitter is fast. Use LSP to confirm ambiguity, not to parse from scratch. *Consequences*: Some precision left without LSP; SCIP fills the gap.

**DEC-024 — Sigma.js + graphology for the visual viewer**
- *Status*: Accepted (v0.4). *Decision*: WebGL renderer (Sigma), graph datastructure + algorithms (graphology + graphology-layout-forceatlas2 + graphology-communities-louvain). *Rationale*: Scales to 10k+ nodes; BGP-internet-scale demo on Sigma.js homepage. *Consequences*: Custom node rendering harder than D3; acceptable.

**DEC-025 — OpenFastTrace marker syntax compatibility**
- *Status*: Accepted (v0.4). *Decision*: Recognize `req~name~1` / `feat~name~1` / `impl~name~1` / `utest~name~1` in code, comments, commits, MD. *Rationale*: Compatible with existing safety-critical workflows; we match grammar, don't import GPL-3 code. *Consequences*: We link, we don't validate completeness; document scope.

**DEC-026 — Pre-rendered SVG architecture export for PR review**
- *Status*: Accepted (v0.4). *Rationale*: GitHub renders SVG; reviewers see the graph in PRs without running the tool.

**DEC-027 — Merkle-tree incremental indexing**
- *Status*: Accepted (v1.0). *Rationale*: Cursor pattern works; about 3.2 MB metadata for 50k files. Embedding cache by chunk hash.

**DEC-028 — Registry publication via `understand-quickly` format**
- *Status*: Accepted (v1.0). *Rationale*: Free distribution; cross-tool interop; opt-in (no env token = no-op).

**DEC-029 — `rename` MCP tool semantics**
- *Status*: Accepted (v1.0). *Decision*: Plans the rename, dry-runs across the graph, returns a diff; does not write files. Agent applies via its Edit tool. *Rationale*: Safer; agent and human stay in the loop.

**DEC-030 — Optional runtime augmentation via Spring Actuator**
- *Status*: Accepted (v1.0). *Decision*: If `deepdive analyze --actuator-url http://localhost:8080/actuator`, ingest `/beans` and `/mappings` to confirm static inference. *Rationale*: Static-vs-runtime divergence is a common Spring failure mode; surfacing it is differentiated value. *Consequences*: Pure-static mode remains the default.

---

## DELIVERABLE 5 — Positioning + Competitive Wedge

### README positioning paragraph

> **forensic-deepdive** is the open-source (Apache-2.0) code knowledge layer for polyglot codebases — especially the enterprise reality of TypeScript/React frontends talking to Spring Boot Java backends, with JSPs still lingering in the corners. It builds a function-level knowledge graph (calls, impact, execution flows), traces requests across language boundaries (React `fetch` ↔ Spring `@RequestMapping`), maintains a first-class git archaeology layer (who owns this, what changes with what, where the bus factor lives), and ships a traceability matrix linking code to tests to requirements/tickets. It exposes the whole layer to AI agents via MCP and to humans via an interactive Sigma.js graph viewer. It runs fully local (Ollama / LM Studio), or fully deterministic (no LLM at all).
>
> **Compared to GitNexus**: same MCP shape and graph depth, but Apache-2.0 (commercial-safe), with framework-aware Spring/React tracing and git archaeology as first-class. **Compared to CodeGraphContext**: deeper polyglot, framework-aware, with traceability + git archaeology. **Compared to Graphify**: deterministic-first (no LLM required to build the graph), function-level call-graph rigor, MCP-native. **Compared to DeepWiki / DeepWiki-Open**: we don't write wikis; we let agents query structure. **Compared to Aider repo-map**: persistent, queryable, multi-language, agent-served. **Compared to Sourcegraph SCIP**: we use SCIP when present; we don't try to replace compiler-precise indexers — we wrap them in an agent-ready, framework-aware, archaeology-aware graph. **Compared to CodeQL**: not security-first, not GitHub-bound; we read CodeQL's Spring library as a spec rather than competing with QL.

### The 3–5 user populations we serve better than anyone

1. **Enterprise Java/Spring Boot teams with a React frontend** — completely unserved by GitNexus (no framework awareness, no cross-stack tracing), CodeGraphContext (Python, shallow), and CodeQL (security-first). The full-stack impact question — *"if I rename this Spring service method, which React components and which test cases break?"* — is genuinely missing.
2. **OSS maintainers and consultancies who can't depend on PolyForm Noncommercial tools** — sponsors, consultants, dual-licensed library authors. Apache-2.0 unlocks client work.
3. **AI-coding-agent teams building on Claude Code, Cursor, Codex, Continue, Cline** — want a shared, deterministic, license-clean knowledge layer rather than re-rolling embeddings.
4. **Auditors and SRE archaeologists** — git archaeology + traceability + impact analysis in one tool. CodeScene has it but is closed and SaaS.
5. **Polyglot monorepos** — anyone with TS + Python + Go + Java who is tired of three different tools each missing the other languages.

### Positioning sentence (tighter than "DeepWiki but rules-shaped")

> **forensic-deepdive: the Apache-2.0 code knowledge graph that crosses language boundaries.**

### Three candidate taglines

1. **"From source to graph to agent — Apache-2.0, no cloud, no asterisks."**
2. **"Cross the language line. Trace the impact. Own the license."**
3. **"The code knowledge layer for codebases that don't speak one language."**

---

## Caveats and Honest Red Flags

- **Star counts cited (GitNexus 19–25k, DeepWiki-Open ~15.7k, CodeGraphContext ~2.2k, Understand-Anything ~15k, Continue ~30.5k, ArchUnit ~3.6k, OpenAPI Generator ~22k) come from third-party blogs and search snippets, not direct GitHub API checks.** Verify before quoting in marketing. GitNexus's number varies between roughly 17k and 25k+ across sources within a two-month window.
- **GitNexus velocity is serious** (61 commits, 23 contributors, 15 first-time, between 1.6.4 and 1.6.5). The "single maintainer" framing is increasingly misleading — Patwari is coordinating real OSS work. **If they ship a permissive-license tier**, our license wedge weakens dramatically. Plan for that contingency: substantive features (Spring / React / archaeology / traceability) must carry the product, not license alone.
- **Kuzu acquisition** is publicly confirmed via an EU Digital Markets Act filing spotted by AppleInsider and reported by MacRumors on Feb 11, 2026 (`macrumors.com/2026/02/11/apple-acquires-new-database-app/`); acquisition date was October 10, 2025; repo was archived the same day. LadybugDB's longevity depends on a small commercial entity (Vela Partners maintains a separate fork). **Hedge with the `GraphStore` interface from day one.**
- **SCIP transitioning to independent governance** with a Core Steering Committee including Uber + Meta engineers is a positive — it's becoming a real cross-vendor standard. Safe to bet on.
- **MCP donated to the Linux Foundation Agentic AI Foundation** (December 2025, OpenAI + Block backing) — no longer a single-vendor risk. Safe to build on.
- **Spring Boot static graph completeness is fundamentally bounded** without runtime info — accept ≤ 95% precision in v1.0, document honestly, offer optional Actuator augmentation.
- **The Graphify PyPI package is `graphifyy` (double-y)**, not `graphify`. Easy to get wrong in docs.
- **One reason NOT to build this**: if Anthropic ships a first-party Claude Code "knowledge graph" plugin in the next quarter, the category gets oxygenated upward by a much larger force. As of May 2026 the `anthropics/claude-code/plugins` tree contains PR-review, design-pattern, plugin-dev, and similar plugins — **no first-party code-graph plugin yet**. Monitor that path; if it ships, pivot toward integration (be the engine Anthropic's plugin runs on) rather than competition.
- **Don't try to be DeepWiki.** That race is run — DeepWiki-Open has 15k+ stars on the same problem. Wikis are a derivable artifact of the graph; let users plug `deepwiki-open` into your `graph.json` if they want one.
- **Don't try to be Sourcegraph.** Compiler-accurate indexing across 50k repos with cloud infrastructure is not a one-person project. Ride SCIP instead.
- **The real risk is being a "second CodeGraphContext"** — a Python MIT-licensed shallower clone of GitNexus. Differentiate via Spring/React/archaeology/traceability, or this project has no reason to exist.