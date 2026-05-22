# RESEARCH.md

> Landscape research conducted May 20, 2026. The opinionated findings that produced the architecture. Decisions derived from this research live in `/DECISIONS.md`; this file holds the reasoning depth in case any decision needs to be revisited.

## TL;DR

Skill+CLI hybrid built on Tree-sitter + ported Aider PageRank repo-map + Repomix `--compress`, emitting five durable markdown artifacts. Graphiti deferred behind a concrete 2-of-5 threshold. MCP-as-primary rejected because durable artifacts beat a running daemon for cross-tool adoption.

## Layer 1 — Static extraction

**Adopt: Tree-sitter via `tree-sitter-language-pack` (PyPI v1.8.0).** 305 pre-compiled grammars covering every Omi-stack language (Dart, Python, C, Swift, Rust, TS, Kotlin, Objective-C). Coverage is no longer the constraint.

**Adopt: Aider's repo-map + PageRank algorithm — port, do not depend.** Walk the repo with Tree-sitter `tags.scm` queries, build a NetworkX graph (files = nodes, identifier cross-references = edges), run PageRank with personalization vector seeded by chat files / mentioned identifiers, binary-search the ranked list to fit a token budget. The well-known weakness (symbol-name uniqueness collapse on monorepos, documented by Meetsmore engineering) gets a v0.2 fix with `ImportFloodStrategy` as a second strategy.

**Adopt: ast-grep for HOTPATHS.md tracing.** Rust binary, MIT, Tree-sitter-native, Node/Python bindings for programmatic AST queries. Right tool for cross-language hot-path tracing (BLE characteristic UUIDs, FastAPI route registrations, `run_blocking_sync` offload sites).

**Adopt as Python-specific optional enricher: Astral's `ty` (Beta, Dec 16 2025).** Per Astral's launch blog: *"Without caching, ty is consistently between 10x and 60x faster than mypy and Pyright."* On Home Assistant: 2.19s ty vs 45.66s mypy. Critically, ty's diagnostic system is *"designed from the ground up with both humans and agents in mind"*. If a repo is ≥30% Python LOC, run `ty check` and surface diagnostics as a type-debt sidecar in MAP.md.

**Skip: semgrep.** Security tool with 30+ languages and a restrictive Rules License. Per ast-grep's maintainer on HN: *"ast-grep is for development; Semgrep is for security."*

**Skip: LSP indexers (pyright, rust-analyzer) as batch extractors.** Too heavy for our use case. ty + ruff cover the Python enrichment we need.

**Defer to v2.0: SCIP / LSIF.** Sourcegraph moved LSIF→SCIP in v4.5; LSIF reading removed in v4.6. SCIP indexers exist for ~10 languages but each requires per-language build integration (Gradle/Maven/sbt for scip-java, etc.). Gate behind `--precise` flag in v2.0.

**Dead — skip entirely: GitHub stack-graphs.** Repo archived September 9, 2025, with notice: *"This repository is no longer supported or updated by GitHub. If you wish to continue to develop this code yourself, we recommend you fork it."* The idea was elegant (Tree-sitter + DSL for name binding) but only Python, JavaScript, TypeScript, and Java had production grammars. Don't depend.

**Optional enricher for JS/TS: dependency-cruiser.** Solid for JS/TS-only dependency graphs.

## Layer 2 — Repo flattening

**Adopt as default: Repomix (`yamadashy/repomix`, 24.6k stars as of May 2026).** `--compress` uses Tree-sitter to extract key code elements (class/function signatures, drop bodies). Secretlint integration prevents `.env`/API-key leaks. `.gitignore`, `.repomixignore` respected. AI-friendly XML and Markdown output.

**Adopt as v0.2 `--fast` backend: yek (Rust, ~230× faster than Repomix on Next.js per its README benchmark: 5.19s vs 22.24min).** Uses git history to weight files (more-recently-touched files appear later, where LLMs attend most). Configurable via `yek.yaml`.

**Skip as built-in (document as compatible): code2prompt, gitingest, files-to-prompt.** Either redundant with Repomix or slower with no compensating advantage.

**Competitive frame, not dependency: DeepWiki / DeepWiki-Open.** DeepWiki indexed >50,000 public GitHub repos per Cognition's launch blog. DeepWiki-Open self-hosts (MIT, FastAPI + Next.js, supports Ollama for fully local operation with `nomic-embed-text` embeddings). Their architectural bet (RAG over chunked code with embeddings) is different from ours (deterministic PageRank over symbol graph, no embeddings). We're not consuming them; we're disagreeing.

## Layer 3 — Temporal archaeology

**Plain-git default for v0.1.** `git log --follow`, `git log --grep`, `git shortlog -sn`, GitHub REST API for PRs/issues. Sufficient for "who owns X", "when was X introduced", "which PR broke Y".

**Adopt: Graphiti (`getzep/graphiti`) for v0.2 above threshold.** Stable `graphiti-core` ≥0.28, Apache-2.0. Backends: Neo4j 5.26, FalkorDB 1.1.2, Kuzu 0.11.2 (embedded — no server!), Amazon Neptune. Bi-temporal model: every edge has explicit (`valid_from`, `valid_until`) plus ingestion time. Hybrid retrieval (cosine + BM25 + graph traversal) at P95 ~300ms per FalkorDB benchmarks. Conflicts resolved by invalidation, preserving full history. Per the Zep paper (Rasmussen et al., arXiv 2501.13956, Jan 2025): 94.8% on Deep Memory Retrieval vs MemGPT's 93.4%; up to 18.5% accuracy gain and 90% latency reduction on LongMemEval.

**Concrete threshold to invoke Graphiti — 2 of these 5 must be true:**

| Signal | Threshold |
|---|---|
| LOC | ≥ 50,000 |
| Unique contributors (all-time) | ≥ 25 |
| Repo age | ≥ 18 months |
| Merged PRs (last 12 months) | ≥ 200 |
| Closed issues with discussion | ≥ 100 |

Below 2-of-5, plain-git is sufficient. Omi meets all five; most small projects meet zero or one.

**Rejected alternatives:** Neo4j with hand-rolled schema (no temporal model, no hybrid search — you're rebuilding Graphiti). Memgraph (no Graphiti driver — same problem).

## Layer 4 — Agent orchestration

The 2025–2026 ecosystem converged on **markdown rules files + skills + MCP**.

- **Claude Code stack:** `CLAUDE.md` (always-on), Agent Skills (announced October 2025, published as open standard December 18, 2025), subagents (`.claude/agents/*.md`), MCP servers.
- **Cursor:** `.cursor/rules/*.mdc` with YAML frontmatter. Also reads `AGENTS.md` as fallback.
- **Continue.dev:** `.continue/rules/*.md` or YAML in `config.yaml`.
- **Aider:** `CONVENTIONS.md` + `.aider.conf.yml`.
- **Codex CLI:** native `AGENTS.md`.
- **AGENTS.md is a standard** — per the Linux Foundation's December 9, 2025 Agentic AI Foundation press release: *"AGENTS.md has already been adopted by more than 60,000 open source projects and agent frameworks including Amp, Codex, Cursor, Devin, Factory, Gemini CLI, GitHub Copilot, Jules and VS Code among others."*

**Capacity constraint on AGENT_BRIEF.md:** HumanLayer's published analysis states frontier LLMs reliably follow ~150–200 instructions; Claude Code's system prompt consumes ~50; *"as instruction count increases, instruction-following quality decreases uniformly."* Hard cap: ≤5kb / 300 lines.

## Distribution decision — skill+CLI hybrid

Five reasons MCP-as-primary loses:

1. **Daemon overhead.** "Run `forensic .`, five files commit" beats "configure your MCP client to point at port 9876."
2. **Per-tool surface area.** Each MCP client (Claude Desktop, Cursor, Continue, Cline, Codex CLI, Claude Code) has its own JSON config. Artifacts are read natively by all of them.
3. **Skill installation is one line.**
4. **CLI is load-bearing for non-Claude users.** Aider, Cursor, Continue, Cline, Codex CLI, hand-coders — all benefit from `forensic .` regardless of harness.
5. **MCP is right for query-after-ingest.** A thin MCP server (`query_map`, `query_hotpath`, `read_brief`, etc.) is legitimate v0.2 secondary. Not primary.

## Skill split — three skills

Anthropic's skill-authoring docs: *"The description is critical for skill selection: Claude uses it to choose the right Skill from potentially 100+ available Skills."* A multi-intent description loses to three sharp single-intent descriptions.

- `forensic-deepdive-extract` — triggered by "analyze this repo", "onboard me to X", "deep-dive this codebase".
- `forensic-deepdive-query` — triggered when artifacts exist and the user asks navigational questions.
- `forensic-deepdive-update` — triggered after significant code churn.

## Graphify — separately reviewed (May 20, 2026)

Real, MIT-licensed, two months old (`safishamsi/graphify` on GitHub, `graphifyy` on PyPI). Overlaps with our system but doesn't replace it.

**Overlap:** Tree-sitter AST extraction, NetworkX graph, "replace raw source files as AI context" thesis, Claude Code skill + CLI distribution.

**Divergence:**
- They cluster (Leiden community detection); we rank (Aider PageRank). Different question.
- They emit one knowledge graph + report; we emit five rules-shaped artifacts with AGENT_BRIEF.md as headline.
- They are multi-modal (PDFs, videos, images); we are code/git only by design.
- They have no temporal layer; we have plain-git default + Graphiti above threshold.
- They have no hot path tracing; we make HOTPATHS.md a first-class artifact.
- They have no AGENT_BRIEF.md / rules synthesis; we make it our whole point.

**One good idea stolen with attribution:** Confidence-tagged edges (EXTRACTED / INFERRED / AMBIGUOUS). The most underrated part of their design — trust depends on it. Logged as DEC-007.

**Optional `--with-graphify` backend in v0.2** (DEC-008): if the user has `graphify-out/graph.json`, we consume their semantic edges to enrich our symbol graph. Free multi-modal coverage when available.

**Positioning sharpened to:** *"Graphify gives your agent a map. We give it a rulebook. Run both."*

## Reading list (curated, ordered by relevance)

1. Anthropic — *Equipping agents for the real world with Agent Skills* (Oct 2025) — skill design philosophy.
2. Aider docs — `aider.chat/docs/repomap.html` — the PageRank approach this system ports.
3. Zep / getzep — Graphiti README + arXiv 2501.13956 — temporal KG architecture.
4. HumanLayer — *Writing a good CLAUDE.md* — instruction capacity constraints.
5. Linux Foundation — December 9, 2025 AAIF press release — AGENTS.md as standard.
6. Astral — *ty: An extremely fast Python type checker and language server* — diagnostic-quality bar.
7. yamadashy/repomix — README — default Layer-2 backend.
8. safishamsi/graphify — README + Towards AI writeup — competitive analysis context.

## Dying / dead tools — explicit "do not touch" list

- **stack-graphs** (GitHub, archived Sep 9, 2025) — read-only, no future updates.
- **LSIF** (Sourcegraph deprecated in favor of SCIP) — replaced.
- **semgrep** for understanding tooling — wrong category.
- **Sourcegraph self-hosted Cody for personal use** — cloud-default, enterprise-priced.

## What changes these recommendations

- If Graphiti's local-mode structured-output failure rate exceeds 30% on Qwen2.5-Coder-32B during v0.2 week 2 benchmark: degrade Graphiti to cloud-only in v0.2 and ship plain-git as the local default.
- If user testing in v1.0 shows AGENT_BRIEF.md being ignored more than 1 in 5 sessions: shrink hard cap to <3kb and split into AGENT_BRIEF_CORE.md + AGENT_BRIEF_DEEP.md.
- If Tree-sitter symbol-uniqueness collapse causes <60% precision on Omi's MAP.md: bring `ImportFloodStrategy` forward into v0.1.
- If `forensic-deepdive` PyPI name is taken: fall back to `forensic-cli`.
