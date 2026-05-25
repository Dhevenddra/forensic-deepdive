# v0.2 — What's Left

> **Living doc.** Updated at the end of each v0.2 session. Read at session
> start (before touching code) so the next picks up cleanly. Source of
> truth for sequencing; the PRD is the source of truth for *what* each
> item means.

## Operating discipline (load-bearing — read first)

forensic-deepdive is a **real product**, not a prototype. The bar
across every remaining item:

- **Never ship half-baked code or code with compromised functionality.**
  Spend the time. Write the custom algorithm. Read the upstream
  grammar. Dig into the AST. Don't accept "kinda works."
- **Before deferring a sub-feature, ask: does the parent feature work
  without it?** If MCP `impact()` needs CALLS edges, finish CALLS
  before shipping `impact()`. Don't ship a tool whose own success
  metric is gated on missing data.
- **NotImplementedError with a PRD-pointing message** for surface area
  the current scope doesn't claim to support is fine. Silent
  half-functionality is not.
- **Explicit deferrals to a clearly-scoped future version** (per PRD
  §11) are scope decisions, not compromises. Document them honestly.
- **PRD §5 acceptance gates are floors, not ceilings.** Determinism,
  sub-second `context()`, byte-identical graph hashes — aim past them.

This rules out: emitter cutovers that fall back to in-memory NetworkX
for "the cases that don't work yet"; AGENT_BRIEF rules that mark
everything EXTRACTED because INFERRED branches are unwritten; an MCP
server whose `impact()` returns placeholder AMBIGUOUS edges because
the real resolver is "future work."

This explicitly **adjusts the deferrals in item 8 below**: CALLS /
IMPORTS / Commit / Author / TOUCHED_BY_COMMIT edges are part of v0.2,
not "PRD §10 future." They land before the MCP server, because the
MCP server depends on them.

## Current state (snapshot)

- **Branch:** `main`. Tree clean at HEAD. Never pushed.
- **Tests:** 322 passing. `ruff check` + `ruff format` clean.
- **PRD §10 progress:** 13 of 14 done (items 1, 2, 3, 4, 5, 6, 7, 8,
  8b, 9, 10, 12, 13). Item 8b — the extension that completes item 8's
  graph — is **DONE** (all 6 steps).
- **Latest commit:** `7cdbd66 docs: REMAINING.md -- items 8b/9/10/12
  + DEC-018 done, next session opens at items 13/11/3/14/15`
  (DEC-031 commit will follow this session).
- **Active DECs:** DEC-001 → DEC-018, DEC-020 → DEC-031. (Only
  DEC-019 — Graphiti — of the originally-reserved set remains
  unwritten.)
- **Item 9 COMPLETE** (phases 1 + 2): markdown artifacts read from
  graph; default flipped True.
- **Item 10 COMPLETE (DEC-016, headline v0.2):** MCP server with 5
  composite tools live. `forensic serve` works.
- **Item 12 COMPLETE (DEC-017):** Repomix demoted to
  `--legacy-repomix`.
- **Item 13 COMPLETE (DEC-031):** 5 emitted skills
  (`codebase-exploring` / `-debugging` / `-impact-analysis` /
  `-refactoring` / `-onboarding`) + `.claude-plugin/plugin.json` +
  refreshed editor shims; all write-if-absent.
- **DEC-018 done:** registry + `forensic list`. Multi-repo MCP
  serving deferred to v0.3.
- **Languages:** 8 (Python, C, Dart, Swift, TypeScript, JavaScript,
  Java, Go).
- **Persistent graph: FEATURE-COMPLETE for v0.2.** Opt-in via
  `ExtractConfig.build_graph_db=True`. Writes File + Symbol + Module +
  Commit + Author nodes; DEFINES + MEMBER_OF + IMPORTS + CALLS +
  EXTENDS + IMPLEMENTS + TOUCHED_BY_COMMIT + AUTHORED_BY +
  CO_CHANGES_WITH edges; all confidence-tagged honestly per DEC-015.
  Every `LadybugStore.add_*` method is implemented (no
  NotImplementedError surface left).

## Remaining PRD §10 items, in suggested order

### Item 9 — Markdown artifacts regenerated from the graph  **(next)**

**Unlocks:** flip `build_graph_db` to `True` by default. Every
`forensic extract` produces a queryable `.lbug` *and* writes the 5
markdown artifacts. Closes the gap between "v0.1 still ships markdown"
and "v0.2 graph is the source of truth."

**Complexity:** medium-large. Touches emit/* and the EmitPhase wiring.

**Touchpoints:**
- `src/forensic_deepdive/emit/{map,hotpaths,archaeology,mental_model,agent_brief}_md.py`
  — each emitter needs a v0.2 path that pulls from `LadybugStore`
  (Cypher) instead of from `static.symbol_graph` (NetworkX).
- `src/forensic_deepdive/pipeline/phases.py::EmitPhase.depends_on`
  gains `build_graph` and chooses graph vs in-memory based on
  `ctx.get(BuildGraphPhase).enabled`.
- `tests/fixtures/expected_emit/*.md` — regenerate via `UPDATE_GOLDEN=1`.
- `src/forensic_deepdive/pipeline/extract.py::run_extract` — flip
  `build_graph_db` default to `True`. The
  `test_public_run_extract_does_not_build_graph_by_default` test
  inverts.

**Traps:**
- PageRank currently runs on the file-level NetworkX graph (DEC-003).
  v0.2 wants symbol-level centrality — but the LadybugDB currently has
  no CALLS edges, so symbol PageRank has nothing to rank. Either keep
  file-level ranking (read File nodes from the graph) or punt
  symbol-level PageRank to v0.3.
- AGENT_BRIEF rules are derived from PageRank output today. Keep them
  working at file level for v0.2; symbol-level rules wait for CALLS.

**DEC needed:** maybe a small one capturing the file-vs-symbol PageRank
decision. Or fold into DEC-009/DEC-011 family if scope is small.

---

### Item 3 — Confidence taxonomy plumbing through emitters  **DONE — DEC-015**

Shipped 2026-05-25. The v0.1 blanket "every fact below is EXTRACTED"
banner replaced with per-section / per-rule honest labels. MAP's
PageRank sections, ARCHAEOLOGY's bot-classification section, and
MENTAL_MODEL's heuristic sections all carry `INFERRED` notes.
AGENT_BRIEF rules carry per-rule confidence tags — git facts stay
`EXTRACTED`, ranking derivations become `INFERRED`. 5 golden fixtures
regenerated. 13 new tests verify section-level and rule-level
honesty.

---

### Item 10 — MCP server with 5 composite tools  **(headline)**

**Unlocks:** DEC-016. The whole "code knowledge layer for AI agents"
pitch. Without this, the LadybugDB is just a local file. With it,
Claude Code / Cursor / Codex / Continue / Cline can query the graph.

**Complexity:** large. New `forensic serve` subcommand, MCP stdio
transport, 5 tools.

**Tools (PRD §4.5):**
- `impact(symbol, depth=3, direction="upstream", min_confidence="INFERRED")`
- `query(natural_language=None, cypher=None)`
- `context(symbol)`  — Glass-style single-call kitchen-sink
- `flow(entry_point, max_depth=10)`
- `archaeology(file_or_symbol)`

**Touchpoints:**
- `src/forensic_deepdive/mcp/server.py` (new). Use the `mcp` PyPI
  package (already in the `[mcp]` extra).
- Each tool: composite — internally fires multiple Cypher queries +
  optional history join.
- `cli.py::serve` command — currently a stub.
- New tests under `tests/mcp/`. Mock the stdio transport.

**Traps:**
- Tool descriptions ≤ 200 tokens each (DEC-016 / Harness lesson).
- `flow` and `archaeology` need git data joined with graph data — the
  graph doesn't yet have Commit / Author / TOUCHED_BY_COMMIT edges.
  Either: (a) implement those nodes/edges in BuildGraphPhase before
  item 10 starts, or (b) let `archaeology` read from `HistoryPhase`
  output directly (won't work cross-session — graph persists, history
  doesn't). Recommendation: **add Commit + Author + TOUCHED_BY_COMMIT
  to BuildGraphPhase as a preamble to item 10**.
- `query(natural_language=...)` needs BM25 + semantic + structural
  fusion. Punt the semantic part to v0.3 — v0.2 ships natural-language
  as substring + Cypher fallback.

**DEC:** DEC-016 (reserved). Plus possibly a small DEC for the v0.2
NL-query simplification.

---

### Item 11 — Graphiti integration  **(optional, gated)**

**Unlocks:** DEC-019. The agent's persistent learning brain across
sessions. **The "self-updating tool" story.** What makes v0.2
defensibly different from CodeGraphContext.

**Complexity:** medium. Heavy dependency footprint but a focused code
surface.

**Touchpoints:**
- `src/forensic_deepdive/graphiti_brain/store.py` (new) — wraps
  `graphiti-core ≥ 0.28`.
- A new MCP tool `record_insight(symbol, claim, evidence, verified_by)`.
- `context(symbol)` tool extended to merge structural + temporal
  insights.
- Threshold gate from DEC-005 (≥50k LOC, ≥25 contributors, ≥18 months
  old, ≥200 PRs/12mo, ≥100 issues w/ discussion — 2 of 5).
- Below threshold: JSONL append-log fallback.

**Traps:**
- Graphiti needs an LLM for entity extraction. Local mode = Ollama
  (Qwen2.5-Coder-32B per DEC-009). Cloud mode = Claude Haiku.
- Pure-static mode must still work end-to-end (DEC-019 honest-mode
  acceptance — PRD §5.5).
- LadybugDB / Graphiti share the same Kuzu-fork engine — two `.lbug`
  files in `.deepdive/`. Verify version compatibility on install.

**DEC:** DEC-019 (reserved).

**Order note:** Can ship before or after item 10. Probably *after* —
the headline `record_insight` MCP tool needs item 10's server.

---

### Item 12 — Drop Repomix as primary  **(small)**

**Unlocks:** DEC-017 (reserved). `forensic extract` no longer runs
Repomix by default; the graph + MCP supersedes the role of "pack the
repo for LLM."

**Complexity:** small. CLI flag rename + emit-shim deletion.

**Touchpoints:**
- `cli.py` — add `--legacy-repomix` flag (default off).
- `pipeline/phases.py::FlattenPhase` — only runs when the new flag is on.
- `pipeline/runner.py::ExtractConfig.flatten` — default flips to `False`.
- README + CHANGELOG entry.

**Traps:** none significant — the FlattenPhase is already best-effort.

---

### Item 13 — Agent skill emission updates  **DONE — DEC-031**

Shipped 2026-05-25. `emit/shims.py` now writes 10 targets per extract:
the 4 v0.1 editor shims, 5 single-intent skills under
`<target>/.claude/skills/codebase-{exploring,debugging,impact-analysis,
refactoring,onboarding}/SKILL.md`, and a `.claude-plugin/plugin.json`
manifest listing them. All write-if-absent. The internal 3 skills
(`forensic-deepdive-{extract,query,update}` in this project's
`.claude/skills/`) are untouched — different namespace, different
purpose.

---

### Item 14 — Acceptance test pass  **(large by elapsed time, small by code)**

**Unlocks:** PRD §5 sign-off. Required before tagging v0.2.0.

**The gates (PRD §5.1 – §5.5):**
- Every box in §5.1 functional list.
- Performance (§5.2): Omi ≤ 120s, GitNexus repo ≤ 600s, cache hit
  ≤ 5s, MCP `context` ≤ 500ms, MCP `impact(depth=3)` ≤ 2s.
- Correctness (§5.3): existing 100-test v0.1 suite still passes,
  ≥ 20 new tests, Omi `impact(Logger)` returns sensible confidence
  labels, spring-petclinic produces reasonable INFERRED edges for
  `@Controller`/`@Service`/`@Repository`, byte-identical graph hashes
  across runs.
- Quality gates (§5.4): `uv run pytest -x` green, `uv run ruff
  check` clean, all DEC entries committed, PROGRESS up to date,
  CHANGELOG entry, examples committed for spring-petclinic and
  gitnexus.
- Honest-mode (§5.5): pure-static (no LLM, no network) works end-to-end.

**Traps:**
- spring-petclinic Java parses but the v0.2 query is shallow — Spring
  annotations not resolved (that's v0.3). Acceptance §5.3 wording is
  "produce reasonable INFERRED edges" — set expectations honestly.
- GitNexus repo is TS-heavy and large; the 600s budget needs profiling
  first time.

---

### Item 15 — Tag v0.2.0

**Process:**
1. Verify §5 acceptance.
2. Bump `pyproject.toml` version to `0.2.0`.
3. Update `CLAUDE.md` + `AGENTS.md` "When this file goes stale" section.
4. Update README to reflect v0.2 product shape (the v0.1 README is
   about the structural orienter, v0.2 README is about the knowledge
   graph + MCP).
5. Commit `chore: bump to 0.2.0`.
6. `git tag v0.2.0`. **Never push without explicit ask.**

## Item 8b — Extending BuildGraphPhase to full v0.2 scope  **(blocks 9, 10, 11)**

The phase-1 build (commit `6536da3`) writes only `File + Symbol +
DEFINES`. Under the "no half-baked" discipline above, the rest of v0.2
**must** land before the consumers that need them:

- **CALLS edges** — symbol-level resolution. v0.2 ships a real resolver,
  not an AMBIGUOUS placeholder. Algorithm:
  1. **Same-file lexical scope** — calls to names defined in the same
     file resolve to that file's Symbol (`EXTRACTED`).
  2. **Import-graph walk** — extract IMPORTS from each file (see below),
     resolve calls to imported names against the imported module's
     symbols (`EXTRACTED` when the import is unambiguous, `INFERRED`
     when import is a wildcard / re-export).
  3. **Receiver-type inference for method calls** — constructor-call
     return type (`new Greeter(...)` → `Greeter`), simple typed-param
     declarations (TS / Java / Go signatures), `self` / `this` →
     enclosing class. Confidence `INFERRED`.
  4. **Cross-file same-name fallback** — only when 1-3 fail and exactly
     one same-language file in the repo defines the name; otherwise
     `AMBIGUOUS` with all candidates surfaced (per DEC-015).
  This is real work — a small custom resolver per language family. Do
  not ship `impact()` without it.
- **IMPORTS edges + Module nodes** — each language gets an
  `imports.scm` query alongside its `tags.scm`. Python `import x.y`
  and `from x import y`; TS / JS `import {Z} from './y'` and
  `require('y')`; Java `import pkg.Class;`; Go `import "pkg"`; Dart
  `import 'package:foo/bar.dart';`; Swift `import Foo`; C
  `#include "x.h"`. Module nodes populated from these. Confidence
  `EXTRACTED` — imports are AST-deterministic.
- **Commit + Author nodes + TOUCHED_BY_COMMIT + AUTHORED_BY edges** —
  HistoryPhase already produces this data; the build phase writes it.
  Required for the `archaeology()` MCP tool.
- **CO_CHANGES_WITH edges** — computed from `TOUCHED_BY_COMMIT` joins,
  threshold ≥ 3 co-occurrences (Aider's heuristic). `INFERRED` by
  default (DEC-013 schema). Required for the "if you touch X also
  touch Y" rules in AGENT_BRIEF.
- **MEMBER_OF edges** — for class methods → their class, struct fields
  → their struct. AST-deterministic during the tag-extraction pass —
  capture `name.definition.method` with its parent class name.
  `EXTRACTED`.
- **EXTENDS / IMPLEMENTS edges** — `class A extends B`, `class A
  implements I`, Java `extends` / `implements`, Go interface
  satisfaction (only the declared kind — structural Go interface
  satisfaction is v0.3 stretch). `EXTRACTED` from AST.

Implementation order:
1. ✅ **MEMBER_OF** (DEC-023, commit `96a50eb`). Tag.parent + Symbol
   qualified-name parent chain + MEMBER_OF edges across all 8 langs
   including Go's receiver pattern.
2. ✅ **IMPORTS + Module nodes** (DEC-024, commit `2b820a8`).
   Per-language code-walk extractors, language-prefixed Module PK
   (`python:os` vs `go:os`) to dodge real-ladybug's single-column-PK
   limitation. All 8 langs covered.
3. ⏭ **CALLS resolver** (next session — REMAINING priority). The
   4-step algorithm above. Each language gets its own per-language
   receiver-type inferer; the import-graph walk is shared. Uses
   MEMBER_OF (step 1) for `this.method()` → `EnclosingClass.method`
   resolution and IMPORTS (step 2) for cross-file walks. Likely the
   biggest single chunk of v0.2. DEC-025 captures the algorithm.
4. **Commit / Author / TOUCHED_BY_COMMIT / AUTHORED_BY** —
   HistoryPhase data into the graph.
5. **CO_CHANGES_WITH** — derived from #4.
6. **EXTENDS / IMPLEMENTS** — AST extraction per language.

This is substantial. It is the actual v0.2 work — items 9, 10, 11 are
mostly *consumers* of this graph. Do not start items 9–11 before this
is real. Probably 1–2 more sessions of focused work to finish item 8b.

## Deferred to v0.3 (do NOT do in v0.2)

Per PRD §11. Restated so I don't drift:
- Spring annotation resolution.
- React component / hook resolution.
- Cross-stack tracing (React fetch ↔ Spring @RequestMapping).
- LSP-on-demand integration.
- SCIP ingestion (v0.3 stub only).
- ast-grep YAML framework rule packs.
- Sigma.js visual viewer.
- Traceability matrix.
- Merkle-tree incremental indexing (v1.0).
- `rename`, `cross_language_navigate`, `detect_changes`, `trace` MCP tools.
- Web UI, cloud hosting, wiki generation.

## DEC-018 — Multi-repo registry (small, can be done any session)

`~/.deepdive/registry.json`. GitNexus pattern. `forensic list` shows
analyzed repos. `forensic serve` serves all of them. Small, mechanical;
can be folded into item 10 or done as a standalone commit.

## Next-session kickoff prompt

```
Read CLAUDE.md, DECISIONS.md, PROGRESS.md (the 2026-05-25 entry
titled "v0.2 item 3: confidence threading + DEC-015"),
docs/v0.2/PRD_v0.2.md, and docs/v0.2/REMAINING.md (the
"Operating discipline" section is load-bearing). Confirm in one
sentence what you understand.

**Items 3, 8b, 9, 10, 12, 13, DEC-018 are DONE.** The graph is
complete; the MCP server is live; Repomix demoted; multi-repo
registry in place; the 5 emitted skills + plugin manifest ship per
extract; confidence labels are honest at section and rule level.

**Remaining v0.2 work, in suggested priority:**

1. **Item 11 — Graphiti integration (DEC-019)** (large). The
   persistent agent-memory layer. Optional gated install (DEC-005
   threshold). Adds the cross-session "what did we learn last
   time" graph. Real differentiator vs. CodeGraphContext.
2. **Item 14 — acceptance gates** (large, blocking v0.2.0 tag).
   Real-repo runs: Omi (re-verify post-graph), spring-petclinic
   (Java + Spring, no annotation resolution yet — INFERRED edges),
   GitNexus repo itself (dogfood the competitor), fastapi.
3. **Item 15 — tag v0.2.0**. Bump pyproject, update README,
   CHANGELOG, commit `chore: bump to 0.2.0`, `git tag v0.2.0`,
   **never push without explicit ask**.

Working autonomy: full freedom to install tools and web-search
version-sensitive facts. Spend time on hard problems — write custom
algorithms, read upstream grammars, dig into ASTs. Don't ship
half-baked. If the work doesn't fit one session, finish it across
multiple — under-baked single sessions are the failure mode.

Session-end protocol unchanged: PROGRESS.md entry, new DEC if
applicable, conventional-commit messages, never push.
```
