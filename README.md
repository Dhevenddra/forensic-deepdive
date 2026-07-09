# forensic-deepdive

<!-- mcp-name: io.github.Dhevenddra/forensic-deepdive -->

> A persistent code knowledge graph + MCP server for AI coding agents. Five durable markdown artifacts as the human-readable projection. Apache-2.0.

`forensic-deepdive` analyzes any codebase (9 languages, polyglot) and produces:

1. **A persistent embedded graph** at `<repo>/.deepdive/graph.lbug` — File, Symbol, Module, Commit, Author, **Endpoint**, and **DbTable** nodes plus DEFINES, MEMBER_OF, IMPORTS, CALLS, EXTENDS, IMPLEMENTS, TOUCHED_BY_COMMIT, AUTHORED_BY, CO_CHANGES_WITH, and the cross-boundary HANDLES / CALLS_ENDPOINT / **ROUTES_TO** / INJECTS / PERSISTS_TO edges. **Every edge carries a confidence tag** (`EXTRACTED` / `INFERRED` / `AMBIGUOUS`) — no hidden heuristics. The single `Endpoint` join node unifies **five cross-boundary protocols** (HTTP, MCP tools, registry-dispatch, gRPC, messaging/AMQP), so a frontend call resolves to its backend handler across the stack as one `ROUTES_TO` edge.
2. **An MCP server** (`forensic serve`) exposing **9 composite tools** (`impact`, `context`, `archaeology`, `flow`, `query`, `record_insight`, `recall_insights`, `visualize`, `trace`) consumable by Claude Code, Cursor, Codex, Continue, Cline, Windsurf — and any other MCP-aware agent.
3. **Five durable markdown artifacts** under `<repo>/docs/codebase/`, regenerated from the graph on every extract:
   - **`MAP.md`** — what's where, ranked by centrality.
   - **`HOTPATHS.md`** — the dependency hot spots, with a per-row confidence-mix column so you see exactly how cleanly each symbol resolves.
   - **`ARCHAEOLOGY.md`** — why the code looks the way it does (git history, top authors with %, bus factor, co-change clusters, defect proximity).
   - **`MENTAL_MODEL.md`** — the doc the original author *would* write to onboard a new hire.
   - **`AGENT_BRIEF.md`** — ≤5 KB of assertive Never/Always rules with per-rule confidence tags. Drop-in `CLAUDE.md` for any project.
4. **Ten shims into the target repo** — 4 editor rule files (`CLAUDE.md`, `AGENTS.md`, `.cursor/rules/codebase.mdc`, `.continue/rules/codebase.md`), 5 single-intent Claude skills under `.claude/skills/codebase-{exploring,debugging,impact-analysis,refactoring,onboarding}/`, and a `.claude-plugin/plugin.json` manifest. All write-if-absent — hand-edited files are never overwritten.
5. **An agent-insight layer** — `record_insight` / `recall_insights` MCP tools backed by `<repo>/.deepdive/insights.jsonl` by default (zero dependencies, human-readable, git-friendly). The optional `[graphiti]` extra upgrades to a temporal knowledge graph backend above a 2-of-5 repo-size threshold.

Extract also regenerates **`ARCHITECTURE.md`** — a system-level Mermaid view of the cross-boundary graph (ROUTES_TO / INJECTS / PERSISTS_TO, confidence-styled), a *separate human-validation surface* (not one of the five contract artifacts, exactly like `forensic visualize` and `serve --ui`). Regenerate it on its own with `forensic diagram --repo <repo>`. Use it to sanity-check the graph — a wrong edge there is a wrong edge everywhere.

Add **`--emit-vault`** to also write an [Obsidian](https://obsidian.md)-friendly vault under `<output>/vault/` — every artifact gets `summary:`/`tags:` frontmatter, cross-references become `[[wikilinks]]`, and an `INDEX.md` MOC ties them together (with a `.obsidian/` config). A local-first second brain for humans (graph view, backlinks) and agents (triage by `summary:` without opening files, a traversable index). Opt-in; off by default.

## Status

**v0.8.0 "USABLE → USEFUL + public release"** — the first public PyPI release. Builds on the frozen five-protocol cross-boundary graph (HTTP/MCP/registry/gRPC/messaging on one `Endpoint` join node) with a precision pass (honest call-graph confidence, distinct-caller counts, low-history/solo-repo guards), a human-validation **`ARCHITECTURE.md`** diagram surface, distribution (PyPI + MCP Registry + a Claude Code plugin), and an opt-in **`--emit-vault`** Obsidian export. The 5-artifact + 9-MCP-tool contract is frozen.

**What's proven, and what isn't (honest framing).** v0.8 is an **assisted-analysis** tool: a real fresh-agent onboarding test confirmed it's **usable** and that an agent **auto-discovers** `AGENT_BRIEF.md` and routes to the right skill unprompted, and a grounded [MCP tool review](docs/findings/v0.7/mcp-tool-review.md) found the git-archaeology + curated briefs are the high-trust core. The **autonomous end-to-end** question — does deepdive-seeding make an agent *resolve* real issues measurably faster — is **not yet proven**: a model-free localization **pilot** is recorded ([`experiments/fastcontext/RESULTS.md`](experiments/fastcontext/RESULTS.md) — the static seed is a *weak* prior), and the end-to-end measurement is **deferred to v0.9** (it needs a GPU + a frontier main-agent endpoint). No autonomous-execution claims are made. Accepted across real repos including Apache Superset, wagtail (Django), spring-petclinic, ripgrep, fastapi, and Iris-Nearby (Flutter/Dart) — see [`docs/findings/`](docs/findings/).

## Quick start

```bash
# install from PyPI (puts `forensic` on PATH); or run ephemerally with uvx
uv tool install forensic-deepdive
forensic info            # banner + capability panel
forensic extract /path/to/repo

# …or from source for development:
git clone https://github.com/Dhevenddra/forensic-deepdive && cd forensic-deepdive
uv sync --all-extras

# what can it do? (banner + capability panel: artifacts, protocols, MCP tools, confidence legend)
uv run forensic info

# guided setup: analyze a repo, then wire it up as an MCP server
# (--yes takes every default: scriptable, and the one mode that needs no extra)
uv run forensic onboard --repo /path/to/repo

# run on any repo
uv run forensic extract /path/to/repo

# graph lands at <repo>/.deepdive/graph.lbug
# 5 markdown artifacts at <repo>/docs/codebase/
# 10 shims at <repo>/.claude/, .cursor/, .continue/, root

# trace a cross-stack feature slice (frontend call -> endpoint -> handler -> tail)
uv run forensic trace <symbol> --repo /path/to/repo

# interactive query REPL over one held-open store (needs the [interactive] extra)
# bare text = natural-language query (no LLM) · :cypher <q> = raw Cypher · :help · Ctrl-D exits
uv run forensic repl --repo /path/to/repo

# full-screen terminal graph browser — the loopback-free sibling of serve --ui
# 1/2/3 = Symbols/Files/Endpoints · type to filter · c/e/l = confidence/edge/language · Enter = context · i/f = impact/flow
uv run forensic browse --repo /path/to/repo

# the session shell: all of the above over ONE held-open graph, with history
# in-session: extract · query · trace · impact · flow · diagram · browse · onboard · serve
uv run deepdive --repo /path/to/repo

# query the graph as an MCP server (point it at the analyzed repo)
uv run forensic serve --repo /path/to/repo

# inspect every repo you've analyzed
uv run forensic list
```

## Install from PyPI

Published as **[`forensic-deepdive`](https://pypi.org/project/forensic-deepdive/)** —
no clone needed:

```bash
uv tool install forensic-deepdive        # puts `forensic` on PATH
forensic extract /path/to/repo

# …or run ephemerally, no install:
uvx forensic-deepdive extract /path/to/repo
```

Optional extras: `uv tool install "forensic-deepdive[semantic]"` (offline ONNX NL
query), `[interactive]` (the `forensic repl` query console, the `forensic browse`
TUI graph browser, and the `deepdive` session shell), `[openapi]` (YAML spec
parsing), `[graphiti]` (temporal insight backend).
`pip install forensic-deepdive` works too if you're not on `uv`.

## Use it as an MCP server

`forensic serve` is a stdio MCP server exposing the 9 composite tools to any
MCP-aware agent (Claude Code, Cursor, VS Code/Copilot, Codex, Continue, Cline,
Windsurf). First build the graph once (`forensic extract <repo>`), then wire the
server. Three ways, easiest first:

**1. Claude Code plugin (self-hosted marketplace — no PyPI step):**

```shell
/plugin marketplace add Dhevenddra/forensic-deepdive
/plugin install forensic-deepdive@dhevenddra
```

**2. From the [MCP Registry](https://registry.modelcontextprotocol.io)** — indexed as
`io.github.Dhevenddra/forensic-deepdive`, so registry-aware clients and discovery hubs
(PulseMCP, MCPJungle, the VS Code `@mcp` index) can find and install it directly.

**3. Manual config** — generate a client snippet with `forensic mcp-config`, or paste:

```json
{
  "mcpServers": {
    "forensic-deepdive": {
      "command": "uvx",
      "args": ["forensic-deepdive", "serve", "--repo", "."]
    }
  }
}
```

Per-client copy-paste blocks (Cursor, VS Code, Codex, the `uvx`-not-found GUI gotcha)
are in **[docs/install.md](docs/install.md)**.

## The 9 supported languages

Python, C, Dart, Swift, TypeScript, JavaScript, Java, Go, Rust.

## The 9 MCP tools

| Tool | What it does |
|---|---|
| `impact(symbol, depth, direction, min_confidence)` | Blast-radius BFS over CALLS edges, depth-bucketed, confidence-filterable. |
| `context(symbol)` | Single-call kitchen sink: definition + callers + callees + parent/siblings/members + extends/implements + recent commits + dominant author + recent insights. |
| `archaeology(file_or_symbol)` | Churn, top authors with %, bus factor, co-change cluster, defect proximity, recent commits. |
| `flow(entry_point, max_depth)` | DFS over CALLS with cycle detection. |
| `query(cypher \| natural_language)` | Raw Cypher, or hybrid NL retrieval (FTS5/BM25 + structural graph signal + opt-in offline semantic, RRF-fused and shaped) with per-hit provenance + confidence. |
| `record_insight(symbol, claim, evidence, verified_by)` | Persist a verified learning. |
| `recall_insights(symbol, since, limit)` | Newest-first substring match against stored insights. |
| `visualize(target, format, depth, max_nodes, ...)` | Bounded Mermaid diagram of a symbol/file neighborhood (or `central`); edge dash style encodes confidence. |
| `trace(symbol, direction, max_depth)` | Cross-stack feature slice across the `Endpoint` join node: `downstream` walks frontend call → `CALLS_ENDPOINT` → endpoint → `HANDLES` → handler → CALLS tail; `upstream` answers "who calls this endpoint". |

Tool descriptions are individually ≤200 tokens so the 9-tool envelope stays comfortably inside Anthropic's per-turn skill metadata budget.

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
| MCP server | ✅ 9 composite tools | ✅ 16 tools | partial | ❌ | ❌ |
| Per-edge confidence taxonomy | ✅ EXTRACTED / INFERRED / AMBIGUOUS | ❌ | ❌ | ❌ | ❌ |
| Git archaeology as a first-class layer | ✅ | ❌ | ❌ | ❌ | partial |
| Durable committed markdown artifacts | ✅ 5 files | partial | partial | ✅ (wiki) | ❌ |
| Agent-insight layer (`record_insight` / `recall_insights`) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Multi-platform skill emission | ✅ 10 shims | partial | partial | ❌ | ❌ |
| Local-only (no cloud required) | ✅ co-equal | ✅ | ✅ | ❌ | ❌ |

**GitNexus is the runaway leader — but the PolyForm Noncommercial license locks every commercial user out.** That's the wedge: Apache-2.0 + honest confidence + git archaeology + persistent agent memory + the 5 markdown artifacts as a fallback for any agent that doesn't speak MCP.

## Local development

```bash
git clone https://github.com/Dhevenddra/forensic-deepdive
cd forensic-deepdive
uv sync --all-extras
uv run forensic --version
uv run pytest -x          # 830 tests at v0.8.0
uv run ruff check src/ tests/
uv run forensic extract tests/fixtures/tiny_fixture
```

Read `CLAUDE.md`, `DECISIONS.md` (81 active DECs), and `PROGRESS.md` before making changes. This repo dogfoods its own pattern: every session starts with the protocol in `CLAUDE.md`, every architectural choice is captured as a `DEC-N` entry, and the artifact-name contract (`MAP`, `HOTPATHS`, `ARCHAEOLOGY`, `MENTAL_MODEL`, `AGENT_BRIEF`) is part of the public API.

## Acknowledgments

- **Aider** (Paul Gauthier) for the PageRank-on-Tree-sitter repo-map pattern. Algorithm ported with attribution; we do not depend on `aider` as a package.
- **Graphify** (safishamsi) for the EXTRACTED / INFERRED / AMBIGUOUS confidence taxonomy. Productized in DEC-015 across every emitter.
- **GitNexus** (abhigyanpatwari) for the multi-repo registry pattern (`~/.deepdive/registry.json`, DEC-018), the composite-MCP-tool shape, and being the licensing wedge that makes this project's Apache-2.0 differentiation matter.
- **Kuzu** (now Apple-archived) for the embedded graph engine; **LadybugDB** for the live community fork that v0.2 ships against (DEC-013).
- **Zep / getzep** for **Graphiti** — the temporal knowledge graph that powers the above-threshold insight backend (DEC-019).
- **Anthropic** for the Skills format, Claude Code, and the MCP protocol that makes this whole product shape possible.
- **Astral** for `uv` and `ruff`.
- **Repomix** (yamadashy) for the original v0.1 flatten-the-repo pattern, now demoted to `--legacy-repomix` (DEC-017) but still available for legacy use cases.

## Contributing

Contributions are welcome — see **[CONTRIBUTING.md](CONTRIBUTING.md)** for the dev
setup, the verification gate, and the architectural invariants (the 5-artifact contract,
the `Endpoint` keystone, the confidence taxonomy). By contributing you agree your work
is licensed under Apache-2.0.

## License

Apache-2.0. See [`LICENSE`](LICENSE).

If you redistribute, modify, or build on this project, the Apache-2.0 terms apply: you
must **retain the copyright notice, the `LICENSE` text, and the `NOTICE` file**, and
**state any changes you made** (License §4). Attribution is required; the project is
Copyright 2026 Dhevenddra (see [`NOTICE`](NOTICE)). The boilerplate header in the
`LICENSE` appendix (`Copyright [yyyy] [name of copyright owner]`) is a *template* for
applying the license to source files — it is not itself a requirement, and the `LICENSE`
file is kept verbatim as the official Apache-2.0 text.
