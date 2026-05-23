# v0.2 — What's Left

> **Living doc.** Updated at the end of each v0.2 session. Read at session
> start (before touching code) so the next picks up cleanly. Source of
> truth for sequencing; the PRD is the source of truth for *what* each
> item means.

## Current state (snapshot)

- **Branch:** `main`. Tree clean. Never pushed.
- **Tests:** 157 passing. `ruff check` + `ruff format` clean.
- **PRD §10 progress:** 7 of 14 done (items 1, 2, 4, 5, 6, 7, 8).
- **Latest commit:** `6536da3 feat: BuildGraphPhase populates LadybugDB
  with File+Symbol+DEFINES (DEC-013)`.
- **Active DECs:** DEC-001 → DEC-014, DEC-020, DEC-021, DEC-022.
  (DEC-015, DEC-016, DEC-017, DEC-018, DEC-019 reserved per PRD §6 for
  the items below.)
- **Languages:** 8 (Python, C, Dart, Swift, TypeScript, JavaScript, Java,
  Go). TSX grammar wired but not exhaustively fixture-tested.
- **Persistent graph:** opt-in via `ExtractConfig.build_graph_db=True`.
  Writes File + Symbol + DEFINES. CALLS / IMPORTS / Module / Commit /
  Author deferred.

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

### Item 3 — Confidence taxonomy plumbing through emitters  **(small)**

**Unlocks:** DEC-015 (already reserved). Every emitted fact tagged
`EXTRACTED` / `INFERRED` / `AMBIGUOUS`. Today only the schema layer
carries it; the markdown emitters still use a global banner. MCP
responses (item 10) also need confidence on every node/edge they
return.

**Complexity:** small / mechanical when item 9 is done. The new
graph-reading emitters naturally carry confidence per edge (it's a
column in the DDL).

**Touchpoints:**
- All five emit/*.py — replace the single banner with per-line
  `[EXTRACTED]` / `[INFERRED]` markers (AGENT_BRIEF already does this).
- The new graph reads in item 9 already get `confidence` as a column.

**DEC:** DEC-015 (reserved). Write when work lands.

**Order note:** do item 9 first so item 3 has a real target. Doing them
together in one session is fine — item 3 is ~30 min once item 9 is in.

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

### Item 13 — Agent skill emission updates  **(medium)**

**Unlocks:** at least 5 skills in `.claude/skills/`, plus
`.claude-plugin/plugin.json`, `.cursor/rules/codebase.mdc`,
`.continue/rules/codebase.md`. The "one tool, every editor" wedge.

**Touchpoints:**
- `src/forensic_deepdive/emit/shims.py` — currently writes 4 thin
  files. Expand to write 5+ skills, each focused (PRD §4.10): Exploring,
  Debugging, Impact-Analysis, Refactoring, Onboarding.
- Each skill's description is the load-bearing selector (CLAUDE.md
  "Sacred abstractions"). Single-intent each.

**Traps:** the existing 3 skills (`forensic-deepdive-extract`,
`-query`, `-update`) at `.claude/skills/` are the ones the project
itself uses internally. The new emitted skills go into the **target
repo**'s `.claude/skills/`. Don't conflate.

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

## Extending BuildGraphPhase (not a PRD item, but blocks items 10, 11)

The v0.2 phase-1 build writes only `File + Symbol + DEFINES`. Items 10
and 11 want more:

- **CALLS edges** — needs symbol-level resolution. Not just v0.1's name
  matching; we need to know that `app.py:foo()` calls
  `greeter.py::Greeter.greet`. This is the real v0.3 work but a v0.2
  minimal version that emits `AMBIGUOUS` CALLS for every plausible
  candidate (per DEC-015) would be enough for `impact()` to do
  something.
- **IMPORTS edges** — extract `from X import Y` / `import { Z } from
  './y'` / `import "fmt"` etc. Each language needs an `imports.scm` or
  an extension to the existing query.
- **Module nodes** — populated from imports.
- **Commit + Author nodes + TOUCHED_BY_COMMIT + AUTHORED_BY edges** —
  blocks `archaeology()` MCP tool. Implement before item 10. Plumbed
  via a new sub-phase or by extending BuildGraphPhase to accept
  `HistoryPhase` output as a dep.
- **CO_CHANGES_WITH edges** — computed from `TOUCHED_BY_COMMIT` joins.

Suggested sequencing for v0.2: do Commit/Author/TOUCHED_BY_COMMIT
**before** item 10 starts (it's a 30-60 min extension of BuildGraphPhase
once the schema work is already done). Defer CALLS resolution to v0.3 —
v0.2's MCP `impact()` returns `tests_NOT_covering` lists based on
DEFINES + naming convention until a real resolver lands.

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
Read CLAUDE.md, DECISIONS.md, PROGRESS.md, docs/v0.2/PRD_v0.2.md, and
docs/v0.2/REMAINING.md (the forward-looking roadmap). Confirm in one
sentence what you understand, then pick up at the supervisor-chosen
next item:

* If item 9 (markdown from graph): start by reading
  src/forensic_deepdive/emit/* to scope the rewrite, then EmitPhase
  in pipeline/phases.py. Flipping build_graph_db default to True is
  the success signal.
* If item 10 (MCP server): start by extending BuildGraphPhase to emit
  Commit + Author + TOUCHED_BY_COMMIT (the archaeology MCP tool
  depends on these). Then write src/forensic_deepdive/mcp/server.py
  with the 5 composite tools (DEC-016).
* Anything else: cite the REMAINING.md item before starting.

Working autonomy: same as v0.2 kickoff — full freedom to install
tools and web-search version-sensitive facts, but write a DEC for any
deviation from PRD or REMAINING.md and ping Dhevenddra before
implementing the deviation.

Session-end protocol unchanged: PROGRESS.md entry, new DEC if
applicable, conventional-commit messages, never push.
```
