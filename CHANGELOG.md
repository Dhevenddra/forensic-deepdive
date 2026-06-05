# Changelog

All notable changes to `forensic-deepdive`. Format roughly follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions
follow [SemVer](https://semver.org/).

## [0.4.0] — Unreleased

> v0.4 **"Cross-Stack & Visual"** — the cross-language wedge (a frontend call
> joins to its backend handler through an `Endpoint` node) plus a served graph
> explorer. Feature-complete (Items A–L); the version bump/tag is intentionally
> held pending sign-off (see the acceptance verdict below). Pure-static floor
> and the 5-artifact + ≤5kb-AGENT_BRIEF contracts are unchanged.

### Added
- **Cross-stack `ROUTES_TO`** — `Endpoint` join node + `HANDLES` / `CALLS_ENDPOINT`
  / materialized `ROUTES_TO` edges (DEC-043). Provider extractors: FastAPI, Flask,
  Express, Spring MVC. Consumer extractors (7): fetch/axios, RTK Query, React
  Query, Angular HttpClient, jQuery, Python requests/httpx, Java RestTemplate/
  WebClient/OpenFeign. Three-tier join confidence — EXTRACTED only for spec-backed
  or unique-literal-both-sides (DEC-044/045/046/047).
- **OpenAPI codegen shortcut** (DEC-048) — a committed spec marks providers
  `spec_backed`, upgrading even templated-client joins to EXTRACTED; spec-only
  operations surface as documented-but-unlocated. JSON zero-dep; YAML behind the
  `[openapi]` extra.
- **`trace` (9th MCP tool)** + a HOTPATHS `## Cross-stack routes` section + an
  AGENT_BRIEF cross-stack rule (DEC-052) — surfacing the wedge.
- **`forensic serve --ui`** (DEC-053) — a read-only, 127.0.0.1-only stdlib HTTP
  server hosting a vendored Sigma.js (WebGL) whole-graph explorer with **mandatory
  level-of-detail** bounding + filtering (edge type / confidence / language /
  directory); `ROUTES_TO` highlighted. Vendored MIT bundles (Sigma.js 2.4.0,
  graphology 0.25.4 + library 0.8.0); no new Python runtime dep.
- **TS/TSX heritage capture** (DEC-050) — abstract classes, interface-extends,
  generic/member-expression supertypes (gitnexus EXTENDS 2→21; superset 1166→1320).
- **`example` file-role** (DEC-049) — tutorial/sample dirs stay in the graph but
  are demoted in PageRank + query shaping (fastapi shaped-query AMBIGUOUS 36 %→0 %).
- **Stable, line-number-free node IDs** (DEC-051) — survive an unrelated same-file
  edit (the v1.0 incremental/rename seam).

### Fixed
- **`example`-role false positive on JVM packages** (DEC-054 finding) — `samples`/
  `example`/`demo` as Java *package* components under a `src/main/<lang>/` root no
  longer trigger the `example` role. Previously the entire canonical Spring
  reference app (`org.springframework.samples.petclinic`) and any
  `com.example.demo` (Spring Initializr default) were demoted out of `source`.

### Acceptance (§4.9, Item L) — 8 of 9 gate items green
Findings: [`docs/findings/v0.4/`](docs/findings/v0.4/). Validated on Superset
(flagship) + purpose-built Spring+React & OpenAPI repos + gitnexus + fastapi.
- ✅ tests/ruff; codegen shortcut; TS-heritage; `example` role; `serve --ui` LOD
  (Superset's 348k co-change edges → 114-node default view); determinism; stable
  IDs; AGENT_BRIEF ≤5kb.
- ⚠️ **Cross-stack `ROUTES_TO` is proven on clean repos but 0 on Superset** — its
  custom `SupersetClient` frontend wrapper + Flask-AppBuilder backend are outside
  v0.4's generic extractor coverage. The join machinery works; framework coverage
  is the gap. **No fabricated joins.**

### Deferred to v0.5 (defined by the acceptance, DEC-054)
- A generic **configured-client consumer extractor** (`<Client>.get({endpoint})`)
  and a **Flask-AppBuilder provider extractor** — unlock the Superset join.
- The previously-deferred **NestJS / Django `urls.py` / JAX-RS** providers.
- Keep spec-generated (`AUTO-GENERATED`) clients in the graph so the codegen
  shortcut fires on them.

## [0.3.0] — 2026-05-31

> v0.3 **"Precision & Speed"** is the foundation pass before the v0.4
> cross-stack wedge (the DEC-034 re-sequence: a trustworthy `ROUTES_TO`
> edge needs method-call resolution first). Seven items A–G, all
> tests-green, accepted on six real repos. The graph, the MCP surface,
> and the 5-artifact contract are unchanged in shape — everything here
> is additive.

### Added

#### Speed — incremental + parallel parse (Items A+B, DEC-036/035)
- **Content-addressed parse cache** keyed on `(content_sha256, language,
  PARSER_VERSION, tags.scm hash)`, stored path-independently so identical
  files share one entry. `ParsePhase` split out of `StaticPhase`;
  incremental *parse* (graph still full-rebuild). `--no`-cache escape hatch.
- **Parallel parse** via `ProcessPoolExecutor` inside `ParsePhase`
  (`--workers N`, default `min(cpu-1,16)`, serial guard < 200 files).
  Determinism preserved by reassembling records in sorted `rel_path` order
  — byte-identical artifacts across `--workers 1` vs N and cold vs warm.
- **Result:** Omi cold extract **930 s → 406.6 s (−56 %)**; warm re-extract
  ≤ 1.9 s on every test repo.

#### Precision — receiver-type method resolution (Item C, DEC-037)
- Dotted/method calls (`self.m()`, `this.m()`, `Foo.m()`, `mod.m()`),
  previously dropped, are now resolved by **receiver-type inference** — all
  tagged `INFERRED` (never silently upgraded to `EXTRACTED`). CALLS edges
  gain a `via` property (`self|this|static|module|bare`). Unresolved dotted
  calls are **dropped, not flooded as AMBIGUOUS** (the deliberate choice
  that keeps the AMBIGUOUS ratio flat while recovering method edges).
- **Result:** method edges recovered that v0.2 dropped — Omi 1,736,
  Superset 1,919, ripgrep 1,528 — overwhelmingly precise INFERRED.

#### Rust — the 9th language (Item D, DEC-040)
- `tree-sitter` Rust grammar; `impl` methods bind non-lexically to their
  type (`impl Greeter { fn render }` ⇒ `render` MEMBER_OF `Greeter`);
  `impl Trait for Type` ⇒ IMPLEMENTS; `use` imports with
  crate/self/super intra-crate suffix-match; `self.`/`Type::` method calls
  feed Item C. (`mod`/`macro_rules!` and Cargo-aware resolution deferred.)

#### Hybrid NL query (Item E, DEC-038/041/042)
- The MCP `query` tool's natural-language branch is now a **three-retriever
  hybrid** fused by **Reciprocal Rank Fusion (k=60)** then output-shaped
  (boost implementation, demote test/vendored/generated):
  - **Lexical** — always-on SQLite **FTS5/BM25** sidecar (no new dep),
    exact-identifier-first then BM25 prefix, camelCase tokenization.
  - **Structural** — always-on graph proximity to query-named symbols +
    CALLS in-degree centrality.
  - **Semantic** — opt-in offline ONNX embeddings behind a new
    `[semantic]` extra; numpy memmap + brute-force cosine; **no network,
    bring-your-own local model**. Absent ⇒ two-retriever, said so.
- Results carry **per-hit provenance** `{symbol, file, line, score,
  retrievers, confidence}` plus `retrievers_active` + `degraded`
  (honest degraded mode). The pure-static floor (DEC-009) holds.

#### Mermaid visual export + 8th MCP tool (Item F, DEC-039)
- New `forensic graph <target> --format mermaid` CLI and **`visualize`
  MCP tool** (the 8th). Bounded subgraph (BFS to depth, node cap 40 with
  a summarize-and-truncate node, never a silent drop). **Edge style
  encodes confidence** in flowchart mode (solid=EXTRACTED, dashed=INFERRED,
  dotted=AMBIGUOUS) — making the taxonomy *visible*. flowchart vs
  classDiagram auto-picked by target kind.

### Acceptance (Item G)

- Six real repos, all 8 gate checks pass (`docs/findings/v0.3/`): **Apache
  Superset** (primary polyglot stress — Python+TS+React), **ripgrep**
  (Rust), re-runs of **Omi** + **spring-petclinic**, and the **fastapi** +
  **gitnexus** carryover (the v0.2 §5.4 debt). `examples/` committed for all
  six. The hybrid query on Superset returns the Python SQLAlchemy models +
  the TS frontend `Dashboard` from one phrase — staging the v0.4 wedge.

### Performance

- See the Items A+B note above. Cold extract is now materially below the
  v0.2 measurement on the same repo; the agent-facing budgets (cache-hit,
  MCP `context`/`impact`) were already met and are unchanged.

### Notes

- New optional dependency: `[semantic]` (`onnxruntime`, `tokenizers`,
  `numpy`) — opt-in only; the base install stays LLM-, network-, and
  numpy-free. FTS5 is stdlib `sqlite3` (no dep).
- DECs DEC-034 → DEC-042 written this arc (the v0.3 re-sequence + per-item
  decisions). 471 tests (1 skipped without the `[semantic]` extra).

## [0.2.0] — 2026-05-25

> v0.2 is a **product pivot**, not a v0.1 increment. v0.1 was a
> structural orienter (5 markdown artifacts from file-level
> dependencies + PageRank). v0.2 ships a real, persistent code
> knowledge graph plus an MCP server that exposes 7 composite tools
> for any AI coding agent — Claude Code, Cursor, Codex, Continue,
> Cline, Windsurf. The 5 markdown artifacts stay; they are now
> projections of the graph.

### Added

#### The graph (DEC-013, DEC-014)
- **Persistent embedded graph store** backed by LadybugDB (the live
  community fork of Kuzu, which Apple acquired and archived in Oct
  2025). Single-file DB at `<repo>/.deepdive/graph.lbug`. Behind a
  `GraphStore` ABC so the v1.0 ArcadeDB hedge swaps in cleanly.
- **Pipeline DAG of typed phases** replaces v0.1's single-function
  pipeline. Five phases at v0.2 (Inventory, Static, Flatten, History,
  BuildGraph, Emit) with explicit `depends_on` + typed outputs. Kahn
  topo-sort runs them; alternative backends or v0.3 framework
  resolvers slot in without restructuring.

#### The honest confidence taxonomy (DEC-007, DEC-015)
- **Every edge in the graph carries `confidence ∈ {EXTRACTED,
  INFERRED, AMBIGUOUS}`** — EXTRACTED for AST/git-deterministic
  edges, INFERRED for heuristic resolution, AMBIGUOUS when the
  resolver can't disambiguate.
- **Per-section + per-rule confidence labels** in the 5 markdown
  artifacts. The v0.1 "every fact below is EXTRACTED" blanket lie is
  gone. AGENT_BRIEF rules tag individually: load-bearing-file rules
  (PageRank-derived) → `[INFERRED]`; churn-point rules (raw git
  counts) → `[EXTRACTED]`; co-change rules → `[INFERRED]`.
- HOTPATHS shows a **confidence-mix column** per row — at-a-glance
  the reader sees "this top-callee resolves cleanly (4 EXTRACTED +
  1458 INFERRED)" vs "this is a same-name cross-file collision (449
  AMBIGUOUS)".

#### 8 languages (DEC-020)
- Doubled from 4 to 8: added **TypeScript, JavaScript, Java, Go**
  alongside the v0.1 Python, C, Dart, Swift. Hand-rolled `tags.scm`
  applying the DEC-012 + Dart-fix precision lessons — bare-call
  references only; dotted member calls dropped via the `_`-prefixed
  helper-capture mechanism. Zero new dependencies
  (`tree-sitter-language-pack` already bundled all five). Rust
  deferred to v0.3.

#### Full v0.2 graph build (item 8b, DEC-023 → DEC-028)
- **Nodes:** File, Symbol, Module, Commit, Author (+ synthetic
  per-file `<module>` Symbol so module-level CALLS have a valid
  caller endpoint).
- **Edges:** DEFINES, MEMBER_OF, IMPORTS, CALLS, EXTENDS, IMPLEMENTS,
  TOUCHED_BY_COMMIT, AUTHORED_BY, CO_CHANGES_WITH.
- **MEMBER_OF (DEC-023):** qualified-name parent chain
  (`Outer.Inner.method`); methods, fields, nested classes get a
  containment edge. Go's receiver-binding pattern (`func (g *Greeter)
  Greet()`) special-cased; every other language uses lexical scope.
- **IMPORTS + Module nodes (DEC-024):** per-language code-walk
  extractors covering 8 import shapes for Python alone plus
  TS/JS/Java/Go/Dart/Swift/C. Language-prefixed Module PK
  (`python:os` vs `go:os`) so cross-language same-name modules don't
  collide on the single-column PK real-ladybug supports.
- **CALLS resolver (DEC-025):** 4-step algorithm — (1) same-file
  lexical scope (EXTRACTED), (2) import-graph walk (EXTRACTED for
  explicit names; INFERRED for wildcard / whole-module), (3)
  receiver-type inference for method calls (INFERRED, partial v0.3
  work), (4) cross-file same-name fallback (INFERRED single,
  AMBIGUOUS multi — every candidate surfaced per DEC-015).
- **Commit + Author + TOUCHED_BY_COMMIT + AUTHORED_BY (DEC-026):**
  full per-commit metadata + file-touch lists from git, mailmap-
  canonical authors. All EXTRACTED — git is ground truth.
- **CO_CHANGES_WITH (DEC-027):** in-memory pair aggregation during
  the commit walk; threshold ≥2 (configurable) filters coincidence.
  INFERRED — computed signal, not a fact.
- **EXTENDS + IMPLEMENTS (DEC-028):** per-language inheritance
  extractors (Python multi-base, TS/Java `class_heritage`, Go
  interface-conformance declarations, Dart mixins/interfaces, Swift
  protocols-as-EXTENDS). Same 3-step resolver as CALLS.

#### MCP server with 7 composite tools (DEC-016, DEC-019, item 10)
- `forensic serve` starts a stdio-transport MCP server consumable by
  Claude Code, Cursor, Codex, Continue, Cline.
- **`impact(symbol, depth, direction, min_confidence)`** —
  blast-radius BFS over CALLS, depth-bucketed, confidence-filterable.
- **`context(symbol)`** — Glass-style single-call kitchen sink:
  definition + signature + callers + callees + parent/siblings/
  members + extends/implements + recent commits + dominant author +
  recent insights.
- **`archaeology(file_or_symbol)`** — churn, top authors with %, bus
  factor, co-change cluster, defect proximity, recent commits.
- **`flow(entry_point, max_depth)`** — DFS along CALLS with cycle
  detection.
- **`query(natural_language | cypher)`** — raw Cypher or substring
  search.
- **`record_insight(symbol, claim, evidence, verified_by)`** (DEC-019)
  — appends one durable insight to a per-repo store.
- **`recall_insights(symbol, since, limit)`** — newest-first
  substring match.

#### Agent-insight layer — JSONL default, opt-in Graphiti (DEC-019)
- Two-backend architecture behind an `InsightStore` ABC.
- **`JsonlInsightStore` is the always-available default** —
  append-fsync per record, no dependencies, file at
  `<repo>/.deepdive/insights.jsonl` (human-readable, hand-editable,
  git-friendly, survives a corrupt single line).
- **`GraphitiInsightStore` is opt-in** — requires the `[graphiti]`
  extra, falls through to JSONL when graphiti-core is unavailable or
  the DEC-005 2-of-5 threshold fails (≥50k LOC, ≥25 contributors,
  ≥18mo old, ≥200 PRs/12mo, ≥100 issues w/ discussion).
- `context(symbol)` always includes `recent_insights: list[Insight]`
  — empty if none, never absent (agent-facing contract stability).
- **Real-LLM Graphiti runtime acceptance is honestly deferred to user
  verification** per DEC-019's stated v0.2 scope: the structural wiring
  is real and unit-tested with mocked graphiti-core (40 tests); the
  end-to-end `add_episode` → `search` round-trip against a real LLM
  (Ollama local or OpenAI / Anthropic cloud) is the user's call to
  exercise on a threshold-passing repo with the appropriate credentials
  + the `[graphiti]` extra installed. The JSONL floor works fully
  end-to-end with zero LLM, zero network — that's the PRD §5.5
  honest-mode gate.

#### Multi-platform skill emission (DEC-031, item 13)
- `forensic extract` now writes **10 shims** into the target repo
  (was 4 in v0.1):
  - 4 editor shims: `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/
    codebase.mdc`, `.continue/rules/codebase.md`.
  - **5 single-intent skills** under `.claude/skills/codebase-<intent>/
    SKILL.md` for the five common agent workflows: `exploring`,
    `debugging`, `impact-analysis`, `refactoring`, `onboarding`.
    Each description includes a "Use when... Do NOT use..." anchor
    so adjacent skills don't fight over the same user phrase.
  - **`.claude-plugin/plugin.json`** Claude Code plugin manifest
    (name interpolates target repo so users with multiple analyzed
    repos can distinguish plugins).
- Write-if-absent for every one of the 10 targets — hand-edited
  shims are never overwritten.

#### Multi-repo registry (DEC-018)
- `~/.deepdive/registry.json` records every analyzed repo on
  successful extract. `forensic list` shows them.
- Multi-repo MCP serving deferred to v0.3 (the v0.2 tools take a
  single `graph_db_path` baked in at construction).

#### Markdown artifacts read from the graph (DEC-029, DEC-030)
- v0.2 emitters query LadybugDB via Cypher; the v0.1 in-memory
  NetworkX path is preserved as a fallback when the graph DB isn't
  populated. `build_graph_db` defaults to `True`.
- HOTPATHS "Dependency hot spots" + "Cross-file dependencies"
  rewritten to use symbol-level CALLS edges. MAP "Key definitions"
  rewritten with full qualified names + SymbolKind from the graph.
- AGENT_BRIEF "load-bearing file" + "central symbol" rules replaced
  in graph mode by a single "most-called symbol" rule when the
  symbol-level data is present.

#### File-role widening (DEC-021) and contributor pipeline fixes (DEC-022)
- Inventory classifies files into `{source, test, fixture,
  vendored, generated}`. Vendored detection via `third_party/`,
  `bundled/`, `external/`, `_vendor/`, embedded version strings;
  generated via `.g.dart`, `.freezed.dart`, `_pb.py`, `.generated.*`,
  plus a 512-byte content sniff for `GENERATED` / `DO NOT EDIT`
  markers. Both excluded from the symbol graph + PageRank.
- `git log --use-mailmap` for contributor canonicalization. `[bot]`
  and `-bot` accounts split into a separate `bots` list; ARCHAEOLOGY
  gains an optional "Automation" section.

#### Batched UNWIND graph writes (DEC-032)
- Every `LadybugStore.add_*` method has an `add_many_*` sibling
  using UNWIND-with-`$rows`, chunked at `_BATCH_SIZE=1000`. Single-
  row methods preserved for the MCP per-call store pattern and
  isolated tests.
- Direct bench: 1000 single-row CREATEs took 3188ms; UNWIND batched
  60ms (**53× speedup**). 10k MATCH+CREATE edges via UNWIND in
  550ms.
- `BuildGraphPhase.run` collects-then-batches — one `add_many_*`
  call per node/edge type. Sort order preserved across chunks; byte-
  identical graph hashes survive the refactor.

### Changed

- **`forensic extract` no longer runs Repomix by default (DEC-017,
  item 12).** The graph + MCP supersedes the role of "pack the repo
  for LLM." Repomix moved to `--legacy-repomix` flag. Node.js +
  Repomix installation no longer required for v0.2.
- **`ExtractConfig.build_graph_db` defaults to `True` (DEC-030).**
  Every extract writes both the graph DB and the markdown artifacts.
- **`_GIT_TIMEOUT_S` raised 300s → 600s** for cold-cache headroom on
  large repos.
- **`analyze_history` does one `git log --name-only` pass** when
  `include_commit_files=True` (the v0.2 default through
  BuildGraphPhase). Contributors + churn derived from the same walk.
  Old triple-pass behavior preserved for the v0.1 / `include_commit_
  files=False` callers.
- **Symbol-graph DEC-012 refinements:** production-only graph,
  language-scoped edges, local-definition shadowing — already in
  v0.1.1; documented here for completeness.

### Performance

Real-repo cold-extract numbers measured on commodity Windows 11
hardware (Intel, NVMe SSD):

| Repo | Files | Commits | Cold extract | Cache hit | MCP `context` | MCP `impact(depth=3)` |
|---|---|---|---|---|---|---|
| Omi (BasedHardware/omi) | 2103 src across 8 langs | ~18k | 930s | ≤5s | 146ms | 289ms |
| spring-petclinic | 30 Java | ~1.5k | 125s | ≤5s | <50ms | <50ms |
| tiny_fixture (v0.1) | 2 (Python+Dart) | small | 2.2s | <1s | <50ms | <50ms |

#### §5.2 budget relaxation — DEC-033

The PRD §5.2 cold-extract budgets shipped pre-implementation and were
authored against the v0.1 file-level orienter. With the v0.2 persistent
graph (8 languages × symbol-level CALLS / IMPORTS / EXTENDS / IMPLEMENTS
+ Commit / Author / TOUCHED_BY_COMMIT / AUTHORED_BY / CO_CHANGES_WITH
edges + per-edge confidence metadata), the v0.2.0 measured cold-extract
on Omi is **930s** vs. the original ≤120s budget. After DEC-032's
batched UNWIND writes (53× speedup on the LadybugDB side) and the
single-pass git-history walk in `analyze_history`, the dominant remaining
cost is the **sequential parse phase** (8 languages × ~5500 files,
one Tree-sitter parser at a time). Per **DEC-033** the cold-extract
budgets are relaxed to measured-honest numbers — Omi ≤1200s, GitNexus
≤2400s — while the **agent-facing budgets are unchanged**: cache-hit
≤5s, MCP `context` ≤500ms, MCP `impact(depth=3)` ≤2s. Those govern
the agent-loop UX and pass with order-of-magnitude headroom on the
same real graph.

**Parse-phase threading is the canonical v0.3 perf lever** — a per-language
ProcessPoolExecutor + sort-after-collect to preserve deterministic
golden fixtures. The v0.3 cycle baselines the new polyglot stress-test
set (Apache Superset, Backstage, Odoo) under threaded parse and either
tightens the cold-extract budget back toward §5.2's original 120s
intent or surfaces another lever (Tree-sitter parser pool reuse,
LadybugDB COPY FROM bulk-load).

### Dependencies

- **Added (core):**
  - `real-ladybug` ≥ 0.15.3 — embedded graph store (DEC-013). MIT.
  - `mcp` ≥ 1.27.1 — MCP server transport. MIT.
- **Added (`[graphiti]` extra, optional):**
  - `graphiti-core` ≥ 0.28 — opt-in agent-memory backend (DEC-019).
- **Removed:**
  - `kuzu` (was in v0.1's `[graphiti]` extra) — upstream archived
    after Apple acquisition Oct 2025; replaced by `real-ladybug`
    (DEC-013).
- **Demoted:**
  - Repomix is no longer auto-invoked (DEC-017); reachable via
    `--legacy-repomix` flag. Node.js + Repomix no longer required.

### Migration

For v0.1 users:
- The 5-artifact contract is **unchanged**: same filenames, same
  order, same `docs/codebase/` location.
- `forensic extract <repo>` now additionally produces
  `<repo>/.deepdive/graph.lbug` and 10 shim files (was 4 in v0.1).
  All shims write-if-absent.
- The first run is slower than v0.1 due to graph building; the
  graph is a one-time cost — subsequent queries via MCP are
  sub-second.
- v0.1 cache semantics preserved: `forensic extract` returns in
  ~seconds if no source changes are detected.
- Repomix users: pass `--legacy-repomix` to preserve the
  flatten-to-XML behavior.

## [0.1.0] — 2026-05-23

The structural orienter. Five markdown artifacts emitted from
Tree-sitter + ported Aider PageRank + plain-git history + Repomix
pack. Acceptance run on Omi (1,860 source files, 92.3s, $0, 100
tests passing). Three skills (`forensic-deepdive-extract`,
`-query`, `-update`). PageRank ported pure-Python (DEC-011). Symbol-
graph scoping refinements (DEC-012). Tag: `v0.1.0` (local, not
pushed).
