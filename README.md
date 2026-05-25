# forensic-deepdive

> A persistent code knowledge graph + MCP server for AI coding agents. Five durable markdown artifacts as the human-readable projection. Apache-2.0.

`forensic-deepdive` analyzes any codebase (8 languages, polyglot) and produces:

1. **A persistent embedded graph** at `<repo>/.deepdive/graph.lbug` — File, Symbol, Module, Commit, Author nodes plus DEFINES, MEMBER_OF, IMPORTS, CALLS, EXTENDS, IMPLEMENTS, TOUCHED_BY_COMMIT, AUTHORED_BY, CO_CHANGES_WITH edges. **Every edge carries a confidence tag** (`EXTRACTED` / `INFERRED` / `AMBIGUOUS`) — no hidden heuristics.
2. **An MCP server** (`forensic serve`) exposing **7 composite tools** (`impact`, `context`, `archaeology`, `flow`, `query`, `record_insight`, `recall_insights`) consumable by Claude Code, Cursor, Codex, Continue, Cline, Windsurf — and any other MCP-aware agent.
3. **Five durable markdown artifacts** under `<repo>/docs/codebase/`, regenerated from the graph on every extract:
   - **`MAP.md`** — what's where, ranked by centrality.
   - **`HOTPATHS.md`** — the dependency hot spots, with a per-row confidence-mix column so you see exactly how cleanly each symbol resolves.
   - **`ARCHAEOLOGY.md`** — why the code looks the way it does (git history, top authors with %, bus factor, co-change clusters, defect proximity).
   - **`MENTAL_MODEL.md`** — the doc the original author *would* write to onboard a new hire.
   - **`AGENT_BRIEF.md`** — ≤5 KB of assertive Never/Always rules with per-rule confidence tags. Drop-in `CLAUDE.md` for any project.
4. **Ten shims into the target repo** — 4 editor rule files (`CLAUDE.md`, `AGENTS.md`, `.cursor/rules/codebase.mdc`, `.continue/rules/codebase.md`), 5 single-intent Claude skills under `.claude/skills/codebase-{exploring,debugging,impact-analysis,refactoring,onboarding}/`, and a `.claude-plugin/plugin.json` manifest. All write-if-absent — hand-edited files are never overwritten.
5. **An agent-insight layer** — `record_insight` / `recall_insights` MCP tools backed by `<repo>/.deepdive/insights.jsonl` by default (zero dependencies, human-readable, git-friendly). The optional `[graphiti]` extra upgrades to a temporal knowledge graph backend above a 2-of-5 repo-size threshold.

## Status

**v0.2.0** — the persistent graph + MCP product. Tagged locally; tested on Omi (BasedHardware/omi: 2,103 src files across 8 languages, ~18 k commits) and spring-petclinic.

## Quick start

```bash
# install (uv-managed)
uv tool install forensic-deepdive

# run on any repo
cd ~/some/repo
forensic extract .

# graph lands at .deepdive/graph.lbug
# 5 markdown artifacts at docs/codebase/
# 10 shims at .claude/, .cursor/, .continue/, root

# query the graph as an MCP server
forensic serve

# inspect every repo you've analyzed
forensic list
```

## The 8 supported languages

Python, C, Dart, Swift, TypeScript, JavaScript, Java, Go. Rust deferred to v0.3.

## The 7 MCP tools

| Tool | What it does |
|---|---|
| `impact(symbol, depth, direction, min_confidence)` | Blast-radius BFS over CALLS edges, depth-bucketed, confidence-filterable. |
| `context(symbol)` | Single-call kitchen sink: definition + callers + callees + parent/siblings/members + extends/implements + recent commits + dominant author + recent insights. |
| `archaeology(file_or_symbol)` | Churn, top authors with %, bus factor, co-change cluster, defect proximity, recent commits. |
| `flow(entry_point, max_depth)` | DFS over CALLS with cycle detection. |
| `query(cypher \| natural_language)` | Raw Cypher or substring discovery. |
| `record_insight(symbol, claim, evidence, verified_by)` | Persist a verified learning. |
| `recall_insights(symbol, since, limit)` | Newest-first substring match against stored insights. |

Tool descriptions are individually ≤200 tokens so the 7-tool envelope stays comfortably inside Anthropic's per-turn skill metadata budget.

## The confidence taxonomy

Every edge and every emitted claim carries `EXTRACTED` / `INFERRED` / `AMBIGUOUS`:

- **`EXTRACTED`** — deterministic from AST or `git log`. Facts.
- **`INFERRED`** — a heuristic resolved cleanly (import-graph walk, receiver-type inference, single same-name candidate cross-file). High-trust but derived.
- **`AMBIGUOUS`** — multiple candidates surfaced; the resolver couldn't disambiguate. **You see every candidate**, not a silent guess.

HOTPATHS shows a per-row confidence-mix column so at a glance you can tell `Logger` (4 EXTRACTED + 1458 INFERRED — mostly clean) from `ChatToolResponse` (449 AMBIGUOUS — same-name cross-file collision).

## Honest-mode (pure-static, zero LLM, zero network)

`forensic extract` works end-to-end with **no `ANTHROPIC_API_KEY`, no `OPENAI_API_KEY`, no Ollama, no network**. Graphiti is opt-in via the `[graphiti]` PyPI extra plus a 2-of-5 repo-size threshold (≥50 k LOC, ≥25 contributors, ≥18 mo old, ≥200 PRs/12 mo, ≥100 issues with discussion). The `JsonlInsightStore` is the always-available floor.

## Why this and not [GitNexus / CodeGraphContext / DeepWiki / Sourcegraph]

| | forensic-deepdive | GitNexus | CodeGraphContext | DeepWiki | Sourcegraph |
|---|---|---|---|---|---|
| License | **Apache-2.0** | PolyForm Noncommercial | MIT | proprietary (open variant: MIT) | partial |
| Persistent code knowledge graph | ✅ LadybugDB | ✅ LadybugDB | partial | ❌ | partial |
| MCP server | ✅ 7 composite tools | ✅ 16 tools | partial | ❌ | ❌ |
| Per-edge confidence taxonomy | ✅ EXTRACTED / INFERRED / AMBIGUOUS | ❌ | ❌ | ❌ | ❌ |
| Git archaeology as a first-class layer | ✅ | ❌ | ❌ | ❌ | partial |
| Durable committed markdown artifacts | ✅ 5 files | partial | partial | ✅ (wiki) | ❌ |
| Agent-insight layer (`record_insight` / `recall_insights`) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Multi-platform skill emission | ✅ 10 shims | partial | partial | ❌ | ❌ |
| Local-only (no cloud required) | ✅ co-equal | ✅ | ✅ | ❌ | ❌ |

**GitNexus is the runaway leader — but the PolyForm Noncommercial license locks every commercial user out.** That's the wedge: Apache-2.0 + honest confidence + git archaeology + persistent agent memory + the 5 markdown artifacts as a fallback for any agent that doesn't speak MCP.

## Local development

```bash
git clone https://github.com/dhevenddra/forensic-deepdive
cd forensic-deepdive
uv sync
uv run forensic --version
uv run pytest -x          # 394 tests at v0.2.0
uv run ruff check src/ tests/
uv run forensic extract tests/fixtures/tiny_fixture
```

Read `CLAUDE.md`, `DECISIONS.md` (33 active DECs), and `PROGRESS.md` before making changes. This repo dogfoods its own pattern: every session starts with the protocol in `CLAUDE.md`, every architectural choice is captured as a `DEC-N` entry, and the artifact-name contract (`MAP`, `HOTPATHS`, `ARCHAEOLOGY`, `MENTAL_MODEL`, `AGENT_BRIEF`) is part of the public API.

## Acknowledgments

- **Aider** (Paul Gauthier) for the PageRank-on-Tree-sitter repo-map pattern. Algorithm ported with attribution; we do not depend on `aider` as a package.
- **Graphify** (safishamsi) for the EXTRACTED / INFERRED / AMBIGUOUS confidence taxonomy. Productized in DEC-015 across every emitter.
- **GitNexus** (abhigyanpatwari) for the multi-repo registry pattern (`~/.deepdive/registry.json`, DEC-018), the composite-MCP-tool shape, and being the licensing wedge that makes this project's Apache-2.0 differentiation matter.
- **Kuzu** (now Apple-archived) for the embedded graph engine; **LadybugDB** for the live community fork that v0.2 ships against (DEC-013).
- **Zep / getzep** for **Graphiti** — the temporal knowledge graph that powers the above-threshold insight backend (DEC-019).
- **Anthropic** for the Skills format, Claude Code, and the MCP protocol that makes this whole product shape possible.
- **Astral** for `uv` and `ruff`.
- **Repomix** (yamadashy) for the original v0.1 flatten-the-repo pattern, now demoted to `--legacy-repomix` (DEC-017) but still available for legacy use cases.

## License

Apache-2.0. See `LICENSE`.
