# PRD_v0.3.md — forensic-deepdive: the road from v0.2 to v1.0

> **Audience:** Claude Code (Opus 4.8), operating under `CLAUDE.md` session discipline.
> **Companion files:** `KICKOFF_v0.3.md` (operating mode), `research_v0.3.md` (evidence base).
> **Status:** contract for the next build arc. v0.3 is specified to implementation depth.
> v0.4 is specified to substantial depth. v0.5 / v0.6 / v1.0 are scoped (clear deliverables +
> acceptance + deferred decisions), and each gets its own detailed PRD pass when its turn comes —
> because v0.2 taught us a real lesson (see §0.2). The IDE is **out of scope** for this entire arc.

---

## 0. The brutal version up front

### 0.1 What v0.2 actually is now
A LadybugDB-backed persistent code knowledge graph. Tree-sitter across 8 languages.
Symbol-level `CALLS`/`MEMBER_OF`/`IMPORTS`/`EXTENDS`/`IMPLEMENTS`, a full git-history layer
(`Commit`/`Author`/`TOUCHED_BY_COMMIT`/`AUTHORED_BY`/`CO_CHANGES_WITH`), a 7-tool MCP server,
a per-edge EXTRACTED/INFERRED/AMBIGUOUS confidence taxonomy, a JSONL insight floor with opt-in
Graphiti, a multi-repo registry, and 10 emitted shims. 394 tests green. v0.2.0 tagged.

### 0.2 The lesson v0.2 taught us, which governs this PRD
v0.2 was planned as 8 decisions (DEC-013→020) and shipped **21** (DEC-013→033). That's a **2.5×
calibration miss** — not because the plan was wrong, but because real architectural granularity only
surfaces *during* the build. **Consequence for this PRD:** only v0.3 is specified line-by-line.
Everything past it is scoped on purpose. When you finish v0.3, you will know enough to write the
v0.4 detail pass that we cannot honestly write today. Do not treat the v0.5–v1.0 sections as
implementation specs; treat them as a ranked, acceptance-bound backlog.

### 0.3 The three things that make this product matter (do not dilute)
1. **Cross-stack / framework-aware edges** (React `fetch()` ↔ Spring route). Nobody does this well.
2. **Git-archaeology as first-class graph data** (bus factor, defect proximity, co-change).
3. **Per-edge confidence taxonomy** — reframed as a *trust* feature ("honest about found vs guessed").

Everything else in this PRD is either a prerequisite for #1 or table-stakes parity. The market has
converged on our architecture (research §0); these three are the moat.

### 0.4 The six soft spots this arc closes
| # | Soft spot | Closed in |
|---|---|---|
| 1 | Cold extract ~930s / 1,860 files | v0.3 (incremental + parallel), v0.6 (Rust) |
| 2 | Dotted/method calls dropped → AMBIGUOUS | v0.3 (heuristic), v0.4 (stack-graphs) |
| 3 | NL query substring-only | v0.3 (BM25/FTS5 + embeddings + RRF) |
| 4 | Graphiti unvalidated end-to-end | v0.5 |
| 5 | Cross-stack tracing absent | v0.4 (the wedge) |
| 6 | No visual layer | v0.3 (Mermaid), v0.4 (Sigma.js) |

---

## 1. The re-sequencing decision (READ — this reverses the prior roadmap)

**Prior roadmap:** v0.3 = Spring/React cross-stack; v0.4 = Sigma.js; v1.0 = incremental + rename.

**This PRD proposes:** v0.3 = **Precision & Speed (foundation)**; v0.4 = **Cross-Stack & Visual
(the wedge)**; v0.5 = Memory & Federation; v0.6 = Performance Core; v1.0 = Scale & Stability.

**Why the wedge moves from v0.3 to v0.4 (dependency-ordering, not just research preference):**
- You cannot emit a trustworthy `ROUTES_TO` edge until you can **resolve the call site at both
  ends**. Today dotted calls are dropped (DEC-025). The React `fetch()` site and the Spring handler
  invocation are exactly the kind of calls we currently lose. **Item C (method resolution) is a hard
  prerequisite for the wedge.**
- Framework resolvers sit on top of solid import + call resolution; building them on a substring-query,
  AMBIGUOUS-heavy, 930s-extract base means shipping the differentiator on sand (research §5.5).
- The bleeding gaps (#1, #2, #3) hurt *every* repo; the wedge helps *polyglot web apps*. Fix the
  common path first, then build the moat on solid ground.

**This is a roadmap change → it must be recorded as a DEC** (DEC-034, see §4.8) before any v0.3 code.
If the supervisor (Dhevenddra) wants a momentum demo, see §4.10 for an optional thin cross-stack
slice that does **not** violate the dependency ordering.

---

## 2. Roadmap at a glance

| Version | Theme | Headline deliverables | Closes soft spots |
|---|---|---|---|
| **v0.3** | Precision & Speed | Incremental extract; parallel parse; heuristic method resolution; Rust language; hybrid NL query; Mermaid export | #1 (partial), #2 (heuristic), #3, #6 (Mermaid) |
| **v0.4** | Cross-Stack & Visual | Spring/React framework resolvers; `ROUTES_TO` cross-stack edges; stack-graphs accuracy upgrade; Sigma.js interactive viewer; traceability matrix | #2 (precise), #5, #6 (interactive) |
| **v0.5** | Memory & Federation | Graphiti real-LLM validation; portable insight storage (parallel git branch); cross-repo federation; multi-repo MCP serving; JSONL→SQLite index | #4 |
| **v0.6** | Performance Core | Rust/PyO3 extraction hot-path; SCIP ingestion tier; tiered extraction (fast/balanced/full); maturin wheels | #1 (ceiling) |
| **v1.0** | Scale & Stability | True incremental *graph* updates; rename tracking; Odoo-scale (~50k files); ArcadeDB server-mode hedge; API freeze | — (hardening) |

---

## 3. Cross-version invariants (NEVER break, any version)

These extend `CLAUDE.md`'s "Sacred abstractions". A change to any of these requires a superseding DEC.
1. **The 5-artifact contract** — MAP / HOTPATHS / ARCHAEOLOGY / MENTAL_MODEL / AGENT_BRIEF. Names,
   count, order are public API. New data extends artifacts; it does not rename or reorder them.
2. **AGENT_BRIEF.md ≤ 5 kb.** Overflow goes to `AGENT_BRIEF_DEEP.md`.
3. **Pure-static guarantee (DEC-009).** The tool must produce all 5 artifacts with **no LLM, no
   network, no embeddings**. Every enrichment (Graphiti, embeddings, SCIP) is opt-in and degrades
   gracefully to the deterministic floor.
4. **Confidence taxonomy on every emitted edge/rule** (EXTRACTED / INFERRED / AMBIGUOUS). New
   resolvers must tag their output. Never silently upgrade INFERRED to EXTRACTED.
5. **Determinism.** Same repo + same commit ⇒ byte-identical artifacts. Parallelism and caching must
   preserve this (sort-after-collect). Golden-file fixtures enforce it.
6. **Apache-2.0, no `aider` package dependency, no un-DEC'd runtime deps.**
7. **No push without explicit instruction; no merge without `uv run pytest -x` green.**

---

## 4. v0.3 — "Precision & Speed" (FULL IMPLEMENTATION DETAIL)

### 4.0 v0.3 thesis & order of work
Make the common path fast and accurate so the v0.4 wedge has solid ground. Build in this order
(each item's tests green before the next): **A → B** (perf pair) → **C** (resolution) → **D** (Rust
language) → **E** (query) → **F** (Mermaid) → **G** (acceptance). A and B are co-designed; C depends
on DEC-023 members already in the graph; E and F are independent and can interleave.

---

### 4.1 Item A — Incremental extraction (content-addressed parse cache)

**Problem.** Cold extract is 930s on Omi; the existing `.forensic-deepdive/cache/` fingerprint is
coarse (whole-extract). A one-file change re-parses 5,500 files.

**Design.**
- Split the parse half out of `StaticPhase` into a new **`ParsePhase`** (DEC-014 foreshadowed this).
  `ParsePhase` is the only phase that touches Tree-sitter and emits per-file `Tags` + `Imports` +
  `enclosing_scope` dataclasses.
- Introduce a **`ParseCache`** keyed by `(rel_path, content_sha256, parser_version, tags_scm_version)`.
  Value = serialized list of `Tag`/`Import`/scope records for that file. Store under
  `.forensic-deepdive/cache/parse/` as one file per content-hash (content-addressed; identical files
  across the repo share a cache entry). Serialize with `msgspec` or stdlib `json` over dataclass
  `asdict` (no pickle — must be inspectable and version-portable).
- Build a **Merkle manifest**: `manifest.json` = `{rel_path: content_sha256}` for all analyzed source
  files (post-inventory, post-DEC-012/021 exclusions). On extract, diff current manifest vs cached
  manifest → `{changed, added, removed}`. Only `changed ∪ added` are parsed; `removed` drop their
  cached entries and graph rows.
- **Cache invalidation:** any bump of `parser_version` or a file's `tags.scm` invalidates that
  language's entries (the key includes both). A schema-version bump (`DEC-013` graph schema) does a
  full rebuild.

**v0.3 scope boundary (important):** v0.3 does **incremental *parse*** (skip re-parsing unchanged
files), then **rebuilds the symbol graph from the union of cached + fresh Tags**. It does **not** do
incremental *graph diffing* (invalidating only affected edges) — that is v1.0. This captures ~all of
the win (parsing is the bottleneck per DEC-033) without the hard graph-diff problem.

**Files.**
- `src/forensic_deepdive/pipeline/phases.py` — add `ParsePhase`; `StaticPhase` keeps symbol-graph +
  PageRank only (rename internally if clearer, but keep the phase list ordering deterministic).
- `src/forensic_deepdive/static/parse_cache.py` — new: `ParseCache.get/put`, `ContentHash`, manifest
  diff.
- `src/forensic_deepdive/static/parse.py` — `ParsePhase` calls `ParseCache` before invoking Tree-sitter.
- `src/forensic_deepdive/pipeline/runner.py` — wire the manifest diff into `Context`.

**Tests.** `tests/test_parse_cache.py`: cold miss populates cache; warm hit skips parse (assert
Tree-sitter not invoked via a spy/counter); one changed file ⇒ exactly one parse; removed file ⇒ rows
gone; `parser_version` bump ⇒ full re-parse; byte-identical artifacts cold vs warm (golden compare).

**Acceptance.** Warm re-extract on Omi after a 1-file change parses ≤ a handful of files and the run
completes in **single-digit seconds** (DB build dominates). Cold still correct and deterministic.

---

### 4.2 Item B — Parse-phase parallelism (ProcessPoolExecutor) — the DEC-033 lever

**Problem.** The sequential parse loop (8 langs × thousands of files) is the cold-extract bottleneck.
GIL-bound Python AST-walking dominates; threads won't help the extraction half.

**Design.**
- Parallelize **inside `ParsePhase`** with `concurrent.futures.ProcessPoolExecutor`. Each worker is
  given `(rel_path, abs_path, language)`, does parse **and** extract, and returns **plain dataclasses**
  (`Tag`/`Import`/scope) — never a Tree-sitter `Tree` (unpicklable). Workers also write their own
  `ParseCache` entries (so parallel + incremental compose).
- **Worker init:** each process constructs its own Tree-sitter parsers once (`initializer=`), since
  parsers aren't shareable across processes.
- **Determinism (new DEC-035):** workers may finish out of order. The parent **collects all results,
  then sorts by `(rel_path, start_byte, kind, name)`** before handing to the symbol-graph builder.
  This is the contract that preserves byte-identical golden fixtures regardless of worker count.
- **Worker count:** default `min(os.cpu_count() - 1, 16)` (GitNexus's cap); `--workers N` CLI override;
  `--workers 1` forces the serial path (used by the golden-fixture test to prove parity).
- **Small-repo guard:** below a file-count threshold (e.g. < 200 files) run serial — process spawn
  overhead dominates on tiny repos and fixtures.

**Files.**
- `src/forensic_deepdive/static/parse.py` — pool orchestration, `_parse_one(path, lang) -> ParseResult`.
- `src/forensic_deepdive/cli.py` — `--workers` flag on `extract`/`update`.
- `src/forensic_deepdive/pipeline/runner.py` — thread `workers` through `ExtractConfig`.

**Tests.** `tests/test_parse_parallel.py`: artifacts from `--workers 1` and `--workers 4` are
byte-identical on the `omi`/`spring-petclinic` fixtures; tiny fixture uses serial path; worker
exception surfaces with the offending file path (no silent drop).

**Acceptance.** Cold extract on Omi drops materially from 930s (target: comfortably within the
1200s budget with clear headroom; record the measured number in `PROGRESS.md` and `docs/findings/v0.3/`).
Combined with Item A, warm re-extract is seconds.

---

### 4.3 Item C — Method-call resolution (heuristic receiver-type inference)

**Problem (soft spot #2).** DEC-025's resolver is bare-name only; `_drop_method` discards dotted
calls (`obj.foo()`, `Cls.foo()`). This is why Omi shows 449-caller `AMBIGUOUS` `ChatToolResponse`
rows and why `log` resolves via a fragile bare-name path. The wedge (v0.4) cannot exist without this.

**Design — re-enable dotted-call capture, then resolve the receiver heuristically. All output
tagged `INFERRED`** (the receiver type is inferred, not proven). Unresolved dotted calls become
`AMBIGUOUS` (with candidate list) or are dropped per a config flag — default: keep as AMBIGUOUS so
the taxonomy stays honest.

Resolution rules, in priority order (this is the GitNexus recipe, research §5.2):
1. **`self.foo()` / `this.foo()` / Python `self.foo`** → resolve `foo` against the **enclosing class's
   members** via the existing `MEMBER_OF` edges (DEC-023). High-confidence INFERRED.
2. **Local constructor inference:** within a scope, if `x = Foo(...)` / `x = new Foo(...)` /
   `x: Foo = ...` is seen, bind `x → Foo`; then `x.foo()` resolves `foo` against `Foo`'s members.
   INFERRED.
3. **Static / class-qualified:** `Foo.foo()` where `Foo` is a known type in scope → resolve against
   `Foo`'s members. INFERRED.
4. **Module-qualified:** `mod.foo()` where `mod` matches an `IMPORTS` alias → resolve against the
   imported module's top-level symbols (suffix-match like DEC-026). INFERRED.
5. **Otherwise** → `AMBIGUOUS` with up to N candidate definitions of `foo` (the current behavior for
   bare names), or dropped if `--drop-unresolved-methods`.

**Scope of inference (keep it honest and bounded):** intra-function/intra-method local binding only
(no interprocedural dataflow, no generics, no field-type tracking across files). That's v0.4/stack-graphs
territory. Document the boundary in the resolver docstring and `DECISIONS.md`.

**Files.**
- `src/forensic_deepdive/static/resolver.py` — new `ReceiverTypeResolver`; extend the call-ref capture
  to retain the receiver expression (remove/repurpose `_drop_method`).
- `src/forensic_deepdive/static/tags.py` — ensure `tags.scm` for each language captures the receiver
  node of a method call (`@call.receiver`) alongside `@call.name`.
- `src/forensic_deepdive/graph/schema.py` — no new node types; `CALLS` edges gain a `via` property
  (`self|ctor|static|module|bare`) for debuggability + confidence rationale.

**Tests.** `tests/test_resolver_methods.py` per language: a fixture class with `self.helper()`, a
local `x = Foo(); x.bar()`, a static `Foo.baz()`, and a genuinely ambiguous `unknown.qux()`. Assert
the resolved target + the `via` + the confidence tag for each. Assert the Omi-style case: a method
defined on one class resolves to that class, not to N homonyms.

**Acceptance.** On Omi, the count of `AMBIGUOUS` CALLS edges drops substantially vs v0.2 (record
before/after in findings). `self.`-style calls in spring-petclinic resolve to the owning class. No
regression in EXTRACTED bare-name resolution.

---

### 4.4 Item D — Rust language support (the DEC-020 deferral)

**Problem.** 8 languages today; Rust deferred. Adding it is cheap and removes a credibility gap (a
code-graph tool that can't read Rust is awkward in 2026), and we need Rust fixtures anyway for v0.6.

**Design.** Follow the "New language support" row in `CLAUDE.md`'s "Where to add things" table.
- `tree-sitter` Rust grammar via `tree-sitter-language-pack`.
- `tags.scm` capturing: `fn`/`struct`/`enum`/`trait`/`impl`/`mod`/`macro_rules!`; method calls
  (`receiver.method()`), associated calls (`Type::method()`), `use` declarations.
- `_PARENT_DEF_TYPES`: Rust **`impl` blocks** are the parent-binding pattern — `impl Foo { fn bar() }`
  binds `bar` to `Foo` (like Go receivers). `impl Trait for Foo` → also emit `IMPLEMENTS(Foo, Trait)`.
- `_SCOPE_DEF_TYPES`, `_IMPORT_NODE_TYPES` (`use_declaration`), `LANG_BY_EXT['.rs'] = 'rust'`.
- Module resolution: `use crate::a::b::Thing` — v0.3 does suffix-match (DEC-026) + external-only for
  `std`/crates. Cargo-aware resolution (parse `Cargo.toml`) is **v0.6** (with the build-system parsing
  work); note it, don't build it.

**Files.** `src/forensic_deepdive/static/tags.py` (+ `tags.scm` resource), `tests/fixtures/rust_sample/`,
`tests/test_parse.py` (add Rust), resolver `_PARENT_DEF_TYPES`/`IMPLEMENTS` for `impl ... for`.

**Tests.** Parse a small Rust fixture: a `struct` with an `impl` block, a `trait` + `impl Trait for`,
a `mod`, a `use`. Assert `MEMBER_OF` (method→struct), `IMPLEMENTS`, `IMPORTS`, and an `impl`-method
call resolving via Item C's receiver rules.

**Acceptance.** `MAP.md` for a Rust repo lists Rust in the language census with correct symbol counts;
`impl` methods attribute to their type, not to a free-function bucket.

---

### 4.5 Item E — Hybrid NL query (BM25/FTS5 + embeddings + RRF)

**Problem (soft spot #3).** `query(natural_language=...)` is substring over `qualified_name`.

**Design — three retrievers fused by RRF (k=60), with output shaping. Pure-static floor preserved.**

- **Lexical (always on, no extra deps):** a sidecar **SQLite FTS5** index over each symbol's
  `name + signature + leading_comment/docstring + qualified_name`. (LadybugDB has no full-text search;
  a sidecar SQLite file under `.forensic-deepdive/index/lexical.db` is the suatkocar pattern.) BM25 is
  FTS5's native ranking. This **alone** replaces substring and is the deterministic floor for query.
- **Structural (always on):** PageRank centrality + graph proximity to any symbols named in the query.
  Reuse the existing centrality scores; this is the "what's important / what's connected" signal.
- **Semantic (opt-in, offline):** embed each symbol's text with a **local ONNX model** (default:
  a small code embedding model, e.g. Jina v2 Base Code 768-dim per research §3, or a
  `sentence-transformers` MiniLM as a lighter default). Store vectors in the sidecar (sqlite-vec or a
  flat `numpy` memmap + brute-force cosine for v0.3 — HNSW is a later optimization). Gate behind an
  extra: `pip install forensic-deepdive[semantic]` and a `--semantic` flag / `serve` capability probe.
  **No network, no API** (honors DEC-009). If the extra/model is absent, the fusion runs with two
  retrievers and says so in the response metadata.
- **Fusion: Reciprocal Rank Fusion, k=60** (Cormack et al. 2009; research §5.3). `score(d) = Σ_r
  1/(k + rank_r(d))` over the retrievers that ran. Deterministic given fixed inputs.
- **Output shaping (Entire `pgr` evidence, research §2/§5.3):** after fusion, **boost implementation
  files, de-prioritize test/vendored/generated** (we already classify these — DEC-012/021). Ranking
  matters more than raw recall for agent behavior; this is the highest-leverage half of this item.

**MCP surface.** Keep the existing `query` tool signature (`cypher` OR `natural_language`); the NL
branch now returns fused, shaped, **confidence-tagged** results with per-hit provenance
(`{symbol, file, line, score, retrievers: [lexical|structural|semantic], confidence}`). Add a
response field stating which retrievers were active (honesty about degraded mode).

**Files.**
- `src/forensic_deepdive/query/` — new package: `lexical.py` (FTS5), `semantic.py` (ONNX, opt-in),
  `fuse.py` (RRF + shaping), `nl.py` (orchestrator).
- `src/forensic_deepdive/mcp_server/server.py` — wire the NL branch to `query/nl.py`.
- `pyproject.toml` — `[project.optional-dependencies] semantic = [...]` (DEC required for any new dep).

**Tests.** `tests/test_query_lexical.py` (FTS5 ranks exact-identifier matches first; offline,
deterministic); `tests/test_query_fuse.py` (RRF math with synthetic ranked lists, k=60; shaping
demotes a `_test.py` hit below an impl hit of equal base rank); `tests/test_query_semantic.py`
(skipped if extra absent; when present, a paraphrase query retrieves the semantically-right symbol;
fusion gracefully drops to 2 retrievers when semantic disabled).

**Acceptance.** A query like "where do we handle websocket reconnection" on Omi returns the relevant
implementation symbol(s) ranked above tests, with provenance, in pure-static mode — no API key, no
network.

---

### 4.6 Item F — Mermaid visual export (soft spot #6, the cheap win)

**Problem.** No visual layer. Mermaid is LLM-, PR-, and Notion-friendly, renders inline in Claude
Code, and is bounded-output-safe if we cap node counts.

**Design.**
- New CLI: `forensic graph <target> --format mermaid [--depth N] [--max-nodes M] [--direction
  in|out|both]`. `<target>` = a symbol, a file, or `--central` (top-N central symbols).
- New MCP tool **`visualize(target, format='mermaid', depth, max_nodes)`** returning a fenced
  ```mermaid block. (Eighth MCP tool — update the tool count + skill docs; this touches the
  artifact/skill contract per `CLAUDE.md` coupling rules.)
- Render a **bounded subgraph**: neighborhood of `target` to `depth`, capped at `max_nodes` (default
  40 — Mermaid degrades past ~50-60 nodes). Node label = short symbol name; edge label = edge type;
  **edge style encodes confidence** (solid = EXTRACTED, dashed = INFERRED, dotted = AMBIGUOUS). This
  makes the taxonomy *visible* — a differentiator made tangible.
- Two diagram modes: `flowchart` (CALLS/IMPORTS neighborhood) and `classDiagram` (MEMBER_OF/EXTENDS/
  IMPLEMENTS for a type). Auto-pick by target kind; `--diagram` overrides.
- Determinism: sorted nodes/edges; stable IDs.

**Files.** `src/forensic_deepdive/emit/mermaid.py`; `cli.py` (`graph` subcommand); `mcp_server/server.py`
(`visualize` tool); update all three SKILL.md files + README + tool count (coupling rule).

**Tests.** `tests/test_mermaid.py`: golden Mermaid for a small fixture neighborhood; node cap
enforced (summarize-and-truncate node when exceeded, not silent drop); confidence→edge-style mapping;
deterministic ordering.

**Acceptance.** `forensic graph Logger --format mermaid` on Omi yields a readable, bounded diagram
with confidence-styled edges that renders in a Markdown viewer.

---

### 4.7 Item G — Acceptance on an expanded repo set

**Carryover (the §5.4 v0.2 debt):** commit `examples/gitnexus/` and `examples/fastapi/` (the 5
artifacts each) alongside their findings docs.

**New v0.3 targets** (chosen to exercise the new items and pre-stage the v0.4 wedge):
- **Apache Superset** — Python + TypeScript + React polyglot; exercises hybrid query and pre-stages
  cross-stack (Flask API ↔ React frontend). Primary v0.3 stress repo.
- **A Rust repo** (e.g. `ripgrep` or `tokio`) — exercises Item D.
- Re-run **Omi** and **spring-petclinic** for regression + the before/after AMBIGUOUS-edge metric.

**Each findings doc records:** cold + warm extract time, file/symbol/edge counts, AMBIGUOUS-edge
count before/after Item C, top hybrid-query examples with provenance, and any honest failure.
Location: `docs/findings/v0.3/<repo>-test.md` (per `CLAUDE.md`).

**Acceptance gate for v0.3 as a whole (all must hold):**
1. `uv run pytest -x` green; `ruff check`/`format` clean.
2. Warm re-extract on Omi in single-digit seconds; cold extract materially below 930s with headroom
   under the 1200s budget (record the number).
3. AMBIGUOUS CALLS edges on Omi reduced measurably vs v0.2.
4. Hybrid NL query returns shaped, provenance-tagged, confidence-tagged results offline.
5. Mermaid export renders, bounded, confidence-styled.
6. Rust fixture + one real Rust repo parsed correctly.
7. Byte-identical artifacts across `--workers 1` vs `--workers N` and cold vs warm.
8. `AGENT_BRIEF.md` still ≤ 5 kb on every test repo.

### 4.8 v0.3 expected DECs (calibration buffer applied)
Pre-drafted set — **budget ~2–3× this count** per §0.2. Write each as a real append-only entry when
you make the choice; never reverse the §1 re-sequence without a superseding DEC.
- **DEC-034** — Roadmap re-sequence: foundation (v0.3) before wedge (v0.4). Rationale = dependency
  ordering (Item C is a wedge prerequisite) + research §5.5.
- **DEC-035** — Parallel-parse determinism: parse-and-extract in workers, return dataclasses,
  collect-then-sort; `--workers` semantics; small-repo serial guard.
- **DEC-036** — Content-addressed `ParseCache` key + `ParsePhase` split from `StaticPhase`;
  incremental-parse (not incremental-graph) boundary for v0.3.
- **DEC-037** — Receiver-type heuristic resolver: rule order, INFERRED tagging, intra-scope-only
  inference boundary, `via` property on CALLS.
- **DEC-038** — Hybrid query architecture: sidecar SQLite FTS5, opt-in offline ONNX embeddings, RRF
  k=60, output shaping; degraded-mode honesty.
- **DEC-039** — Mermaid emitter + `visualize` MCP tool (8th tool); confidence→edge-style mapping;
  node-cap behavior.
- **DEC-040** — Rust language support: `impl`-block parent binding, `impl Trait for` ⇒ IMPLEMENTS,
  suffix-match module resolution (Cargo-aware deferred to v0.6).
- Expect 3–8 more to surface (semantic model choice, FTS5 schema, cache eviction, etc.).

### 4.9 v0.3 dependency/extra additions (each needs its own DEC)
- `[semantic]` extra: an ONNX runtime + a local code-embedding model + (optionally) `sqlite-vec`.
- FTS5 is in stdlib `sqlite3` (no new dep). `msgspec` for cache serialization is optional (stdlib
  `json` is acceptable if you'd rather avoid the dep — your call, DEC it).

### 4.10 OPTIONAL momentum slice (only if the supervisor asks)
If a cross-stack *demo* is wanted in v0.3 without violating dependency ordering: emit **standalone
framework nodes** — recognize Spring `@RequestMapping`/`@GetMapping` route definitions and React
`fetch()`/route literals as **annotated nodes** (`Route`, `FetchSite`), tagged INFERRED, **without**
the `ROUTES_TO` join. This shows the data is captured and previews the wedge, while the actual
join + accuracy work stays in v0.4 where Item C / stack-graphs support it. Do **not** build this
unless explicitly requested — it adds surface area to an already-full v0.3.

---

## 5. v0.4 — "Cross-Stack & Visual" (SUBSTANTIAL DETAIL — the wedge)

> Gets its own implementation-depth PRD pass after v0.3 ships. Scoped here so the v0.3 choices
> stay forward-compatible.

**5.1 Framework-aware resolvers.**
- **Spring/Java:** detect `@Controller`/`@RestController`/`@Service`/`@Repository`/`@Component`,
  `@RequestMapping`/`@GetMapping`/`@PostMapping`/etc. Emit `Route` nodes (path + HTTP method +
  handler symbol) and dependency-injection edges (`@Autowired`/constructor injection →
  `INJECTS`/`PROVIDES`). (GitNexus's AST-decorator-detection, research §4, is the precedent.)
- **React/TS:** detect components, hooks, and HTTP call sites (`fetch`, `axios`, generated clients);
  emit `FetchSite` nodes (URL pattern + method + calling component).
- These build on Item C resolution + Item D-style language wiring; they are why foundation came first.

**5.2 `ROUTES_TO` cross-stack edge (the differentiator).**
- New edge type joining `FetchSite` ↔ `Route` on **(normalized URL pattern, HTTP method)**. Handle
  path params (`/users/{id}` ↔ `/users/${id}`), prefixes, and base URLs. Tag **INFERRED** (literal
  match) or **AMBIGUOUS** (multiple candidate routes / dynamic URL). Never EXTRACTED — these are
  framework-implicit, not syntactic.
- New artifact section (likely in HOTPATHS or a new `CROSSSTACK.md` — decide via DEC; respect the
  5-artifact contract, so prefer a *section* over a 6th core artifact unless strongly justified) and
  a `traceability` MCP tool: "given this React component, what backend handlers does it ultimately
  hit, and through which route."

**5.3 stack-graphs accuracy upgrade (promote Item C heuristic → precise).**
- Integrate `tree-sitter-stack-graphs` rulesets for deterministic name binding incl. dotted calls,
  starting with the languages that have mature rulesets (Python, TS, Java). Promote resolved edges
  from INFERRED to EXTRACTED where stack-graphs proves the binding. Budget per-language ruleset work
  (research §5.2 caveat). Keep the v0.3 heuristic as the fallback tier for languages without rulesets.

**5.4 Sigma.js interactive viewer (the original v0.4 plan).**
- A `forensic serve --ui` (or static-export) WebGL graph explorer over the LadybugDB graph; filter by
  confidence/edge-type/centrality; click-through to source. Mermaid (v0.3) remains the lightweight
  inline option; Sigma.js is the deep interactive one. (GitNexus precedent, research §4.)

**5.5 Traceability matrix.** Component → route → handler → service → repository → table chains, with
confidence per hop. This is the "agent understands the whole feature, not one file" payoff.

**v0.4 acceptance (preview):** on a Spring+React repo (Superset or a petclinic-react variant), a query
"what backend code does the user-profile page depend on" returns the cross-stack chain with per-hop
confidence; stack-graphs upgrades a measurable fraction of v0.3's INFERRED method edges to EXTRACTED.

---

## 6. v0.5 — "Memory & Federation" (SCOPED)

Closes soft spot #4 and makes insights portable + multi-repo.
- **6.1 Graphiti end-to-end validation** against a **local** LLM (Ollama + a code model, e.g.
  Qwen2.5-Coder) — prove the persistent-memory loop: record insight → store with bi-temporal validity
  → recall across sessions → it actually improves a downstream agent answer. No cloud dependency.
- **6.2 Portable insight storage (Entire pattern, research §2).** Mirror the JSONL insight store to a
  **parallel git ref** (e.g. `refs/forensic/insights`) + optional commit trailers, so insights travel
  with the repo and sync via `git push`. Opt-in; JSONL-on-disk remains the floor.
- **6.3 Cross-repo insight federation** via the existing registry (DEC-018 extension): an insight
  learned in repo A surfaces in repo B when relevant (e.g. shared library symbols).
- **6.4 Multi-repo MCP serving (the DEC-018 v0.3 deferral):** repo-selector argument on MCP tools;
  serve a registry of graphs from one `forensic serve`.
- **6.5 JSONL → SQLite index** for 10k+ insights (the §11 deferral): keep JSONL as source of truth,
  add a SQLite index for fast recall at scale.

**v0.5 acceptance (preview):** a recorded insight persists across two `serve` sessions via Graphiti
*and* via the git-ref path; multi-repo `query` works against ≥2 registered repos; 10k synthetic
insights recalled in well under a second.

---

## 7. v0.6 — "Performance Core" (SCOPED)

Closes soft spot #1's ceiling. **Profile-first — do not start until v0.3 incremental+parallel land.**
- **7.1 Rust/PyO3 extraction hot-path.** Profile the parse+extract loop; move only the hottest part
  (AST-walking/extraction) into Rust via PyO3/maturin, **one batched call** (avoid per-symbol FFI
  cost, research §5.1), Python API unchanged, ship pip **wheels** via maturin in CI. Realistic target:
  another large multiple on cold extract on top of v0.3's gains.
- **7.2 SCIP ingestion tier (CodeGraphContext/blarify precedent, research §4/§6).** Optionally consume
  a SCIP index where one exists (scip-python/-typescript/-java) → compiler-accurate calls/inheritance,
  promoted to EXTRACTED. Opt-in; Tree-sitter remains the no-toolchain floor.
- **7.3 Tiered extraction (Jakedismo pattern, research §3):** `--tier fast|balanced|full` mapping
  cleanly onto the confidence taxonomy (fast = AST + core edges; balanced = + heuristic resolution;
  full = + SCIP/stack-graphs). One graph, selectable depth.
- **7.4 Build-system parsing** (the §11 deferral): parse `Cargo.toml`/`go.mod`/`package.json`/`pom.xml`
  to replace the suffix-match import heuristic with real module resolution; Cargo-aware Rust resolution
  lands here.

**v0.6 acceptance (preview):** Rust hot-path shows a measured speedup over the pure-Python v0.3 path on
Omi (record it); `--tier full` with SCIP raises EXTRACTED-edge share on a Python repo; wheels install
cleanly on Linux/macOS/Windows.

---

## 8. v1.0 — "Scale & Stability" (SCOPED)

The original v1.0 intent: incremental + rename + scale + API freeze.
- **8.1 True incremental *graph* updates** (beyond v0.3's incremental parse): edge invalidation /
  subgraph diffing on file change, file-watcher daemon mode (`forensic watch`), so the graph stays
  live under continuous edits (the daemon model everyone converges on, research §3/§6).
- **8.2 Rename tracking:** `git log --follow` + symbol-identity continuity across renames, so archaeology
  and co-change survive file moves.
- **8.3 Scale proof:** Odoo (~50k Python files) or comparable; if LadybugDB embedded struggles, the
  **ArcadeDB server-mode hedge** (DEC-013 named this) is the fallback backend for huge repos.
- **8.4 API freeze + stability:** lock the MCP tool surface, artifact contract, and CLI; semver
  guarantees; the "understand-quickly registry" interop reserved in DEC-028.
- **8.5 Docs + packaging hardening** for a real 1.0 release.

**v1.0 acceptance (preview):** edit-one-file updates the graph in sub-second without full re-extract;
renames preserve archaeology; a 50k-file repo completes within a documented budget; public API frozen.

---

## 9. Deferred-work ledger (every prior deferral → target version)

Consolidated so nothing is lost. Sourced from DEC-013/018/020/023/025/033 and the v0.2 §11 list.

| Deferred item | Origin | Target |
|---|---|---|
| Parse-phase threading | DEC-033 | **v0.3 Item B** |
| Receiver-type inference / dotted calls | DEC-025 | **v0.3 Item C** (heuristic), **v0.4** (precise) |
| Rust language support | DEC-020 | **v0.3 Item D** |
| BM25 + semantic + RRF NL fusion | DEC-016 | **v0.3 Item E** |
| Visual graph layer (Mermaid→Sigma.js) | roadmap | **v0.3** (Mermaid), **v0.4** (Sigma.js) |
| Incremental extraction | roadmap/competitors | **v0.3** (parse), **v1.0** (graph) |
| Spring/React framework resolvers | roadmap | **v0.4** |
| Cross-stack `ROUTES_TO` tracing | roadmap (the wedge) | **v0.4** |
| stack-graphs precise resolution | research | **v0.4** |
| Traceability matrix | roadmap | **v0.4** |
| Graphiti real-LLM acceptance | DEC-019 | **v0.5** |
| Portable insight storage (git ref) | research (Entire) | **v0.5** |
| Cross-repo insight federation | §11 | **v0.5** |
| Multi-repo MCP serving | DEC-018 | **v0.5** |
| JSONL→SQLite index (10k+ insights) | §11 | **v0.5** |
| Rust/PyO3 extraction core | research | **v0.6** |
| SCIP ingestion tier | research | **v0.6** |
| Tiered extraction (fast/balanced/full) | research | **v0.6** |
| Build-system parsing (Cargo/go.mod/pom) | §11 | **v0.6** |
| Go/Swift off external-only resolution | §11 | **v0.6** (with build-system parsing) |
| True incremental graph + watch daemon | roadmap | **v1.0** |
| Rename tracking | roadmap | **v1.0** |
| Odoo-scale + ArcadeDB hedge | DEC-013 | **v1.0** |
| Human-vs-agent line attribution | research (Entire) | archaeology backlog (v0.5+) |
| Leiden community detection / per-module SKILL.md | research (GitNexus) | backlog (consider v0.4) |
| `examples/gitnexus` + `examples/fastapi` commit | §5.4 | **v0.3 Item G** |
| **IDE / agent-dev environment** | long-horizon | **OUT OF SCOPE this entire arc** |

---

## 10. Forward-compatibility checklist (toward the agent substrate — NOT an IDE plan)

Make these cheap choices now so the graph can become an agent substrate later (research §7). Each is
already implied by the items above; this is the cross-cutting reminder:
1. Insights are **portable, version-controlled data** (v0.5 git-ref) — never a local-only blob.
2. Memory is **bi-temporal** (Graphiti) — answers "what did we know when."
3. The MCP tool surface is **typed + confidence-tagged** so multiple agents can collaborate over one
   graph and trust different tiers.
4. Extraction is **tiered** (v0.6) — one graph serves fast-interactive and deep-batch agents.
5. Updates are **incremental + content-addressed** (v0.3→v1.0) so the graph stays live under edits.

Do not design the IDE. Just don't foreclose it.

---

## 11. Operating discipline for this arc (binds with CLAUDE.md + KICKOFF)

- **One item at a time, tests green before moving on.** v0.3 order: A→B→C→D→E→F→G.
- **DEC before divergence.** The §1 re-sequence is DEC-034; do not undo it without a superseding DEC.
- **Honest mode always.** New resolvers tag confidence; degraded query mode says so; findings docs
  record real failures and real numbers, not aspirations.
- **Determinism is non-negotiable.** Every parallel/cached path proves byte-identical output via a
  `--workers 1` / cold-vs-warm golden test.
- **Calibration honesty.** Expect v0.3 to surface ~2–3× the pre-drafted DECs (§4.8). Log each in
  `DECISIONS.md`; update `PROGRESS.md` every session end.
- **Stay in the pure-static guarantee.** If a feature can't degrade gracefully without LLM/network/
  embeddings, it's opt-in or it's wrong.
- **Test surface widens this arc** — the supervisor will run v0.3 against more repos and report back.
  Make findings docs and acceptance numbers easy to read and compare.

---

*End of PRD_v0.3.md. v0.3 is build-ready. v0.4 gets its detail pass once v0.3 ships. The IDE is the
horizon, not this arc — but every choice here is made so the horizon stays reachable.*
