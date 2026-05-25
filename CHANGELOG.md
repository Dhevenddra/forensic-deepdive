# Changelog

All notable changes to `forensic-deepdive`. Format roughly follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions
follow [SemVer](https://semver.org/).

## [Unreleased] — staging for v0.2.0

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
| Omi (BasedHardware/omi) | 2103 src across 8 langs | ~18k | 930s | TBD | 146ms | 289ms |
| spring-petclinic | 30 Java | ~1.5k | 125s | TBD | TBD | TBD |
| tiny_fixture (v0.1) | 2 (Python+Dart) | small | 2.2s | <1s | <50ms | <50ms |

Notes:
- MCP query budgets (≤500ms for `context`, ≤2s for `impact`) are
  comfortably met today.
- Cold-extract budget on Omi (PRD §5.2: 120s) is **8× over**.
  Remaining gaps: sequential parse phase (8 langs × ~5500 files) and
  per-batch MATCH+CREATE cost on a growing table. Threading the
  parse phase is the next perf lever, scoped for v0.3.

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
