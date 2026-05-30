# research_v0.3.md — Competitive & Technical Research Dossier

> Evidence base for `PRD_v0.3.md`. Read this when a PRD item cites "research §X".
> Compiled 2026-05-30 from primary sources (GitHub repos, official docs, founder
> announcements, benchmark posts). Recommendations are woven in deliberately — this
> is decision-grade, not neutral survey. Where a competitor is ahead on one of our
> six soft spots, it says so plainly.

---

## 0. The one-paragraph version

The market has converged on **forensic-deepdive's exact architecture** — Tree-sitter →
embedded graph DB → MCP server with an `impact`/`context`/`query` tool surface → agent
skills + hooks. GitNexus, CodeGraphContext, suatkocar/codegraph, and we all independently
landed there; GitNexus even uses the same LadybugDB/Kuzu backend. So "we build a code
graph for agents" is **no longer a differentiator**. The durable wedge is the three things
almost nobody ships well: **(1) cross-stack / framework-aware edges**, **(2) git-archaeology
as a first-class graph layer**, and **(3) a per-edge confidence taxonomy**. We should borrow
aggressively on the six soft spots (where competitors are clearly ahead) and double down on
those three.

---

## 1. Corrections to the brief (primary-source verified)

Two premises in the original framing were wrong. Correcting them changes what we borrow.

- **Entire.io is NOT a code-graph competitor.** It is a **git-native agent-session-capture
  platform** built by **Thomas Dohmke** (GitHub CEO 2021–Aug 2025). $60M seed at a ~$300M
  valuation, Felicis-led, announced **2026-02-10** — billed as the largest seed ever for a
  devtools startup. Its lessons for us are *architectural and evidentiary*, not feature-competitive.
- **codag.ai is NOT a Rust code-graph CLI.** It is a **log-compression tool** (compresses infra
  logs into cited "incident capsules" for agents). The Rust extraction cores actually worth
  studying are **codegraph-rust**, **suatkocar/codegraph**, and **MonsieurBarti/code-graph-ai**.

---

## 2. Entire.io — what to borrow (it's an architecture lesson, not a threat)

**What it is.** First product **Checkpoints** (MIT, Go CLI): hooks into git, captures the full
AI-agent session — prompts, responses, tool calls, diffs, token usage, line attribution — and
stores it as structured metadata on a **parallel git branch** (`entire/checkpoints/v1`) plus
commit trailers (`Entire-Checkpoint`, `Entire-Attribution`). Never pollutes the working branch.
Supports Claude Code, Codex, Cursor, Gemini CLI, Copilot CLI, etc. Stated full vision: a
git-compatible database unifying code + intent + reasoning, a "universal semantic reasoning
layer" (context graph) giving agents persistent shared memory, and an AI-native SDLC. They
explicitly **integrate with models/agents rather than build them**.

**Borrow #1 — store agent context as data on a parallel git branch.** This is a clean,
distributed, sync-friendly alternative to our single-directory DB for the *insight layer*. Our
JSONL insight store should be able to live on (or mirror to) a parallel git ref so insights
travel with the repo and sync via normal `git push`. Directly relevant to validating the
Graphiti memory layer. → **PRD v0.5, portable insight storage.**

**Borrow #2 — `entireio/pgr` (MIT, Rust) is the single most useful artifact for our NL-query work.**
It's an experimental stateless MCP code-search server wrapping ripgrep that **re-ranks and shapes**
output for agents. Their published finding, derived from hundreds of thousands of *real* captured
agent sessions: **faster search alone barely helps; better-ranked results are what improve
first-query retrieval and cut redundant search loops.** This is hard evidence that our hybrid-query
upgrade must prioritize *ranking and output shaping* over raw speed — boost implementations,
de-prioritize tests. → **PRD v0.3 Item E.**

**Borrow #3 — human-vs-agent line attribution per commit** is a natural extension of our existing
archaeology layer. → **PRD v0.5 / archaeology backlog.**

**Positioning note.** Entire is the clearest credible example of "graph-as-substrate-for-agents"
thinking — a layer *above* the IDE. It validates our long-horizon thesis without competing on
the code-graph layer itself. Watch their "semantic reasoning layer" and the `pgr` repo; if they
ship a code-structure graph, treat it as confirmation, not threat.

---

## 3. The real Rust extraction cores (codag.ai correction)

| Tool | Stack | Borrowable lesson | Caveat |
|---|---|---|---|
| **suatkocar/codegraph** | Native Rust, 32 langs, 44 tools | **"Sync core, async only at the MCP boundary."** Tree-sitter + rusqlite synchronous; Tokio only for stdio transport. Native (not WASM) grammars, statically linked. **rayon** parallel parse. **SHA-256 incremental.** Hybrid FTS5 + sqlite-vec + **RRF k=60**. Embeddings = **Jina v2 Base Code (768-dim, ONNX, local)**. | "Sub-second indexing" benchmarked on a **54-file toy repo** (230ms). Unproven at scale. v0.2.5, ~1★. |
| **Jakedismo/codegraph-rust** | 100% Rust, SurrealDB + HNSW | **Tiered indexing: `fast` (AST + core edges, no LSP) / `balanced` (LSP symbols) / `full` (dataflow).** Maps perfectly onto our confidence taxonomy. | No published throughput. "FastML" is just pattern-based AST enrichment, not a model. |
| **MonsieurBarti/code-graph-ai** | Rust 2024 | **petgraph** in-memory graph; **bincode** disk cache for near-instant cold starts; **oxc_resolver** for import resolution (path aliases, barrel files, workspaces); embedded file-watcher daemon, changed-files-only re-parse. | Early. |
| **colbymchenry/codegraph** (~550★) | **TypeScript/Node, NOT Rust** | Benchmark framing: "~92% fewer tool calls, ~71% faster exploration"; indexed Swift compiler (25,874 files → 272,898 nodes) in <4 min; native FSEvents/inotify watcher, 2s debounce. | README internally inconsistent on the headline metric (94/77 vs 92/71). |

**Net lesson for us:** the Rust path is real and high-ceiling, but it is a **Stage-3 fix** (v0.6),
to be done *after* incremental + parallel land and *after profiling*, moving only the hot path
(parse+extract loop) behind PyO3/maturin. Do not start it in v0.3.

---

## 4. Known competitors — drift since 2026-05-23

**GitNexus** (~38k★, now ~v1.6.4; some star inflation from a crypto-token-name scam the
maintainer disclaimed; effectively single-maintainer, **PolyForm Noncommercial** — commercial use
needs a paid license). Shipped features **we lack**:
- **Incremental indexing** (changed-files-only).
- **AST decorator detection** (`@Controller`, `@Get`).
- **Constructor-inferred type resolution + self/this receiver mapping** — i.e. they **partially
  solved our soft spot #2**. This is our interim method-resolution recipe; see PRD Item C.
- **Framework route recognition across 14 languages.**
- **Leiden community detection** → auto-generates per-module SKILL.md.
- **Sigma.js WebGL web UI**; multi-file rename; hybrid retrieval; parse worker pool (`--workers`, cores−1, cap 16).

→ Our **Apache-2.0 license is a genuine commercial/enterprise wedge** vs their Noncommercial.
If they relicense permissively, that wedge evaporates — see PRD trigger thresholds.

**CodeGraphContext** (MIT, "the MIT alternative to GitNexus"; ~1.1k–2.2k★; 14–20 langs). Has:
- **Live file watching** (`cgc watch`), dual CLI/MCP, 18 MCP tools.
- **Pluggable backend** (FalkorDB Lite default; also KuzuDB, **LadybugDB**, Neo4j).
- **Opt-in SCIP indexer** (`SCIP_INDEXER=true`) for compiler-accurate calls/inheritance on some langs.

→ Both the **SCIP-ingestion path** and the **pluggable-backend** approach are borrowable (PRD v0.6).

---

## 5. Technique deep-dives → mapped to our six soft spots

### Soft spot #1 — cold-extract is slow (930s / 1,860 files ≈ 0.5s/file)
State of the art is a **three-layer stack**, all borrowable:
- **Incremental-first (Cursor / suatkocar / code-graph-ai):** Merkle tree of per-file SHA-256;
  re-parse only changed files; content-addressed cache of parsed output (bincode/SQLite). Makes the
  930s a **one-time** cost. **Highest impact, lowest risk. Do this first.** → PRD Item A.
- **Parallel parse (GitNexus / rayon / our DEC-033 lever):** ProcessPoolExecutor now (GIL-free),
  rayon later. → PRD Item B.
- **Rust/PyO3 hot-path (Ruff / Polars / tokenizers playbook):** Ruff's own docs claim 10–100× over
  Flake8/Black; scip-typescript reports ~10× in Sourcegraph CI. Those are *different workloads* and
  won't transfer 1:1 — our Tree-sitter parse is already native C, so the win depends on how much
  time sits in **Python AST-walking/extraction** vs the C parse. **Profile before committing.** → PRD v0.6.
- Realistic target: incremental + parallel should bring a warm re-extract to **seconds** and a cold
  extract on Omi well under our relaxed 1200s budget, likely toward the low hundreds; Rust later
  closes the rest.

### Soft spot #2 — method-call resolution drops dotted calls → AMBIGUOUS
- **Deterministic answer: GitHub stack-graphs / tree-sitter-stack-graphs** (Rust + bindings).
  Resolves name bindings (incl. dotted/method refs) **file-incrementally**, on the same Tree-sitter
  substrate we already run; SQLite-backed. Powers GitHub's precise nav at scale. **Caveat (their own
  issues):** cross-file module resolution (e.g. Python `module.foo`) needs careful per-language ruleset
  work — budget ~weeks per language. → **PRD v0.4 accuracy upgrade.**
- **Interim heuristic for v0.3 (GitNexus recipe), all tagged INFERRED:** `self.`/`this.` → resolve
  against enclosing class members (we already have MEMBER_OF from DEC-023); `x = Foo()` then `x.bar()`
  → infer `x: Foo`, resolve against `Foo`'s members; `Foo.bar()` static → resolve against `Foo`. This
  alone kills the bulk of the AMBIGUOUS noise in OO code. → **PRD Item C.**

### Soft spot #3 — NL query is substring-only
- **Solved pattern: BM25 (lexical) + dense embeddings (semantic) + Reciprocal Rank Fusion.** RRF and
  its **k=60 default** are from Cormack, Clarke & Büttcher, SIGIR 2009, now the default in
  Elasticsearch/OpenSearch/Weaviate/Qdrant/Azure AI Search. suatkocar/codegraph ships exactly this
  locally (FTS5 + sqlite-vec + RRF k=60, Jina v2 Base Code ONNX).
- **Plus output shaping** (Entire `pgr` evidence): ranking beats speed; boost implementations,
  de-prioritize tests/vendored/generated. → **PRD Item E.** Must stay **offline** (local ONNX, no API)
  and **graceful** (FTS5/BM25 floor when embeddings absent — honors DEC-009 pure-static guarantee).

### Soft spot #4 — Graphiti memory wired but unvalidated
- **Pattern is converging on temporal knowledge graphs (Graphiti/Zep):** bi-temporal edges with
  validity intervals, non-lossy updates, hybrid semantic+keyword+graph search. Our wiring is
  architecturally right. The gap is **end-to-end validation against a real LLM** + adopting Entire's
  portable parallel-branch storage. → **PRD v0.5.**

### Soft spot #5 — cross-stack tracing (the intended wedge) — WIDE OPEN
- **No surveyed static code-graph tool does true frontend↔backend call tracing well.** Closest:
  framework-route recognition (GitNexus/codegraph link URL patterns to handlers across 13–14
  frameworks). The observability world (OpenTelemetry, W3C trace-context) solves it **dynamically at
  runtime**, not statically — leaving a real static-analysis opening.
- **Achievable v0.4 wedge:** parse Spring `@RequestMapping`/`@GetMapping`/`@Controller`/`@Service`/
  `@Repository` on one side and `fetch()`/`axios`/route literals on the React side, then **join on
  (URL pattern, HTTP method)** to emit an implicit `ROUTES_TO` edge (new edge type, INFERRED/AMBIGUOUS).
  Requires Item C method-resolution to land first. → **PRD v0.4.**

### Soft spot #6 — no visual layer
- **Mermaid is the cheapest high-value win** (LLM-, PR-, Notion-friendly; bounded subgraphs).
  codegraph exports Mermaid; GitNexus ships Sigma.js WebGL; blarify/potpie lean on Neo4j Browser.
  → **PRD Item F (Mermaid, v0.3); Sigma.js interactive explorer v0.4.**

---

## 6. Adjacent tools worth a borrowed idea each

- **Sourcegraph SCIP** (+ scip-python/-typescript/-java): language-agnostic Protobuf index, human-
  readable symbol IDs, successor to LSIF. Borrow: **SCIP ingestion** for compiler-accurate indexes
  where they exist (CodeGraphContext already does). Note: Cody free tier discontinued (Jun 2025);
  Amp spun out as an independent agentic-coding company (Dec 2025) — standalone code-intelligence is
  being absorbed into agents/IDEs. → PRD v0.6.
- **Aider repo-map** (we already ported PageRank): match the full design — **personalization vectors**
  (50× chat files, 10× mentioned identifiers, 0.1× private names), √-scaled reference counts, mtime
  SQLite tag cache, binary-search token-budget fit. Borrow: **query-adaptive personalization.** → PRD Item E / v0.4.
- **blarify** (LSP+Tree-sitter→Neo4j): builds edges from **LSP calls** (compiler-accurate) and uses
  **SCIP for up to 330× faster reference resolution than LSP**. Borrow: an **optional LSP/SCIP
  resolution tier** above the fast Tree-sitter tier. → PRD v0.6.
- **potpie.ai** (Apache-2.0): Neo4j KG + **Celery async parsing** + an **Agent Router**; ingests
  tickets/logs/docs, not just code. Borrow: async background parsing, multi-source context. → backlog.
- **graphify** (NetworkX + Leiden + Tree-sitter, 25 langs): "honest about what it **found vs guessed**"
  — a confidence-taxonomy parallel. Borrow: this **framing validates our taxonomy as a marketable
  trust feature** — lead with it.

---

## 7. Forward-compatible choices (toward the agent substrate — NO IDE plan here)

Patterns that recur across Entire, potpie, Graphiti, and the tiered-Rust cores point to choices that
keep our graph viable as an agent substrate later, made now at near-zero cost:
1. **Agent context/insights as first-class, version-controlled, portable data** (Entire parallel-branch),
   not a local-only blob.
2. **Bi-temporal memory** (Graphiti) so the graph can answer "what did we know when" — needed for
   learning loops and auditability.
3. **Stable, typed tool surface with confidence metadata** so multiple agents can collaborate over one
   graph and trust/own different confidence tiers (our taxonomy already is this).
4. **Tiered extraction** (fast/balanced/full) so one graph serves a fast interactive agent and a deep
   batch analysis.
5. **Incremental, content-addressed updates** so the graph stays live under continuous agent edits.

---

## 8. Caveats (read before trusting any number above)
- **Many competitor numbers are self-reported / unaudited.** suatkocar (1★, v0.2.5) "sub-second" =
  54-file toy. colbymchenry README inconsistent. GitNexus ~38k★ partly inflated. Treat all "Xx faster"
  and tool-call-reduction claims as **directional, not audited**.
- **Rust speedups (Ruff 10–100×, scip-typescript ~10×) are different workloads** and will not transfer
  1:1 to a Tree-sitter pipeline whose parse is already native C. Profile first.
- **stack-graphs cross-file module resolution has known rough edges** and per-language ruleset cost.
- Star counts / versions / licenses are as of **late May 2026** and drift fast in this category.

---

## 9. Source index (primary)
- Entire.io launch + funding: entire.io/news, geekwire.com, implicator.ai (2026-02-10).
- Entire Checkpoints + `pgr`: github.com/entireio (MIT).
- codag.ai: codag.ai (log compression — premise correction).
- Rust cores: github.com/suatkocar/codegraph, github.com/Jakedismo/codegraph-rust,
  github.com/MonsieurBarti/code-graph-ai, github.com/colbymchenry/codegraph.
- GitNexus: github repo + releases (PolyForm Noncommercial, ~v1.6.4).
- CodeGraphContext: github repo + PyPI (MIT; SCIP_INDEXER; pluggable backends incl. LadybugDB).
- stack-graphs: github.com/github/stack-graphs (+ issue #430 on cross-file module resolution).
- SCIP: sourcegraph.com/blog/announcing-scip, /announcing-scip-typescript.
- RRF: Cormack, Clarke & Büttcher, SIGIR 2009.
- Rust-for-perf precedent: docs.astral.sh/ruff (Ruff speed claims).
- Cursor indexing (Merkle): cursor.com/blog/secure-codebase-indexing.
- blarify: pypi.org/project/blarify.
