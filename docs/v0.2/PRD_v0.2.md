# PRD — forensic-deepdive v0.2

> **Audience:** Claude Code, with Dhevenddra supervising. This document is one of three inputs you receive at session start: the **kickoff prompt** (KICKOFF_v0.2.md), this **PRD** (PRD_v0.2.md), and the **research dossier** (research_v0.2.md). The PRD is the contract. The research dossier is the evidence behind the contract. The kickoff is your operating mode.
>
> **Read all three. Then read CLAUDE.md, DECISIONS.md, PROGRESS.md as the existing v0.1 session protocol mandates. Then start.**
>
> **Status:** v0.1 is shipped (commit `80f143f`-family, tested on Omi 2026-05-23). This document describes v0.2 — the pivot from "structural orienter" to "real code knowledge graph."

---

## 0. The brutal version, up front

forensic-deepdive v0.1 is a working tool but it is not what we set out to build. v0.1 is a structural orienter — file-level dependency edges, PageRank, plain-git archaeology, five markdown artifacts. Useful for orientation. Not useful for impact analysis, call graphs, execution flows, traceability, or any of the things a developer actually needs when handed an unfamiliar repo and told "fix the bug in module X by Friday."

**v0.2 changes the product.** We're building a real code knowledge graph: function-level call graphs, queryable via MCP, polyglot, with confidence tags on every edge, with git archaeology as a first-class layer, with Graphiti as the agent's persistent learning brain across sessions. The competitor to beat is GitNexus (38.7k stars, but PolyForm Noncommercial). Our wedge is Apache-2.0 + git archaeology + cross-stack tracing (deferred to v0.3 but architected in v0.2).

**This is not v0.1+. This is v2 of the product, shipped as a phased upgrade.** Significant rewrite of the graph layer. New persistence (LadybugDB). New schema. New MCP server. Drop Repomix as the primary artifact. The five markdown artifacts stay — they get rebuilt from the graph.

You have full autonomy to install tools, install versions, manage the environment. uv-managed Python, no global pip. If you need Node.js for LadybugDB bindings, install it via the project's preferred installer. If you need Docker for testing alternative graph backends, use it. Log every global install in PROGRESS.md.

---

## 1. Why v0.2 looks like this — context for the contract

### 1.1 What v0.1 actually delivered
- 5 markdown artifacts emitted from Tree-sitter + ported Aider PageRank + plain-git + Repomix.
- Omi test: 1,860 source files, 92.3 s, $0, 100 tests passing, `ruff check` clean.
- Determinism fix in DEC-012 (production-only / language-scoped / local-shadowed) — keep this. It's correct.
- Pure-Python PageRank kernel (DEC-011) — keep this. Stays SciPy-free.
- Three skills (`forensic-deepdive-extract`, `-query`, `-update`) — keep, extend.
- Cache hit at 2.2 s — keep.
- AGENT_BRIEF.md ≤ 5 KB hard cap — keep, hard-enforced in CI.

### 1.2 What v0.1 demonstrated cannot work going forward
- File-level edges with PageRank only — too coarse. Same-name collisions (`fromJson` appearing 4× in Omi) create false centrality. v0.2 must go to function-level.
- In-memory NetworkX graph that dies at process end — not a knowledge layer, just a one-shot report. v0.2 needs persistence.
- Markdown-only output — agents read markdown well, but they can't query it. v0.2 needs MCP.
- No agent feedback loop — when an agent learns "in this repo, `Logger.error` is actually only called from the websocket handler," that knowledge dies with the session. v0.2 introduces Graphiti as the persistent agent brain.
- Only 4 languages (Python/C/Dart/Swift) — the polyglot promise is hollow without TypeScript, Java, Go at minimum. v0.2 takes us to 8+.

### 1.3 The competitive picture (read research_v0.2.md sections 1.1–1.8 for full detail)
- **GitNexus** is the runaway leader: ~38.7k stars, 14 languages, MCP server with 16 tools, LadybugDB, web UI, agent skills. **PolyForm Noncommercial 1.0.0 licensed — every commercial user is locked out.** That's the wedge.
- **CodeGraphContext** (MIT, ~2.2k stars, Python) is already marketing itself as "the MIT alternative to GitNexus." Apache-2.0 alone is not enough; we need substantive feature wedges.
- **Graphify** (MIT) introduced the EXTRACTED/INFERRED/AMBIGUOUS confidence taxonomy. We adopt it.
- **DeepWiki / DeepWiki-Open** are wiki generators, not knowledge graphs. Don't try to compete with them. Different game.
- **Sourcegraph SCIP** is the precision backbone — we ingest it as a confidence-upgrade layer, we don't try to beat it.
- **Glean (Meta)** has the symbol-server-with-cross-language-navigation pattern we steal for the `cross_language_navigate` tool.

The rate-of-change in this space is brutal. Mid-2025 had zero serious OSS entrants in this category. May 2026 has at least seven. By Q3 2026 there will be 3-5 more. **v0.2 needs to ship before the window closes.**

---

## 2. What we're building — the v0.2 product, in one paragraph

A single CLI command (`forensic extract <repo>`) produces a persistent LadybugDB-backed knowledge graph of the codebase: nodes for files, symbols, functions, classes, methods, modules, processes, commits, authors; edges for CALLS, IMPORTS, DEFINES, MEMBER_OF, TOUCHED_BY_COMMIT, AUTHORED_BY — each edge confidence-tagged EXTRACTED, INFERRED, or AMBIGUOUS. An MCP server (`forensic serve`) exposes 5 composite tools (`impact`, `query`, `context`, `flow`, `archaeology`) consumable by Claude Code, Cursor, Codex, Continue, Cline, Windsurf. A Graphiti-backed agent memory layer accumulates session learnings (verified hypotheses, corrected misreads, fixed bugs) and surfaces them as `INFERRED-from-prior-session` edges in future queries. The five markdown artifacts (MAP, HOTPATHS, ARCHAEOLOGY, MENTAL_MODEL, AGENT_BRIEF) are still emitted, now from the graph. Eight Tree-sitter languages supported: Python, C, Dart, Swift, TypeScript, JavaScript, Java, Go (with Rust as stretch). Pure-static mode (no LLM required) ships as the default; Ollama/LM Studio integration is available for narrative artifacts but is never required to build the graph.

That's the product. Everything below is how to build it.

---

## 3. Scenario walkthrough — how a developer actually uses this

Let me write this as a real scenario so the shape of the tool is concrete. **Geetha** is a senior backend engineer who just joined a fintech team. She's been handed a 12,000-file Spring Boot + React monorepo with three years of git history, 47 contributors, and one stale Confluence page that documents the auth flow inaccurately. Her first task: fix a P1 bug — "user session intermittently dies during checkout."

### 3.1 Day 1 morning — first contact with the repo

```bash
cd ~/work/fintech-monorepo
forensic extract .
```

Pipeline runs. Stages stream to stdout with the existing v0.1 progress format:

```
[inventory] 12,447 files (8,209 source, 1,238 test, 3,000 vendored/generated)
[parse]     8,209 source files in 8 languages (Java 4,103, TS 2,887, Python 612...)
[graph]     74,221 symbols / 312,448 edges → .deepdive/graph.lbug
[history]   git log: 18,432 commits, 47 contributors, span 2023-03 → 2026-05
[emit]      MAP.md, HOTPATHS.md, ARCHAEOLOGY.md, MENTAL_MODEL.md, AGENT_BRIEF.md
[shims]     CLAUDE.md, AGENTS.md, .cursor/rules/, .continue/rules/ (skipped — present)
✓ done in 6m 14s · cost $0.00 · graph 287 MB · cache .deepdive/cache/
```

She opens AGENT_BRIEF.md. It tells her:
- 4 module domains (auth, payments, ledger, ui).
- "If you touch `AuthSessionManager`, also touch `RedisSessionStore`, `JwtRefreshFilter` (coupling rule, EXTRACTED from co-change history)."
- "Never modify `LegacyMigrationController` without coordinating with @nishasri — owns 78% of last-6-month commits there."
- Build commands `./gradlew test` and `pnpm test`.

She opens her IDE (Cursor + Claude Code in parallel). Both pick up the `AGENTS.md` / `CLAUDE.md` shims that v0.2's emit stage wrote.

### 3.2 Day 1 afternoon — Claude Code on the bug

She tells Claude Code: *"I have a P1 — user session intermittently dies during checkout. Use forensic to figure out where to look."*

Claude Code reads AGENT_BRIEF.md, sees the auth module callout, and queries the MCP server:

**Tool call**: `flow(entry_point="checkout")`

The MCP server walks the graph from any symbol matching `checkout` in name or annotation. Returns:

```json
{
  "entry_points": [
    {"symbol": "CheckoutController.processOrder", "file": "src/main/java/com/fintech/payments/CheckoutController.java:42", "confidence": "EXTRACTED"},
    {"symbol": "useCheckout", "file": "web/src/hooks/useCheckout.ts:18", "confidence": "EXTRACTED"}
  ],
  "execution_paths": [
    {
      "from": "useCheckout (React)",
      "to": "CheckoutController.processOrder (Spring)",
      "via": "fetch('/api/checkout', POST)",
      "confidence": "INFERRED",
      "note": "URL/method match. OpenAPI spec not present."
    },
    {
      "from": "CheckoutController.processOrder",
      "chain": [
        "AuthSessionManager.validate (EXTRACTED)",
        "RedisSessionStore.get (EXTRACTED)",
        "PaymentGateway.charge (EXTRACTED)",
        "LedgerService.record (EXTRACTED)",
        "OrderConfirmationEmail.send (EXTRACTED)"
      ]
    }
  ]
}
```

Claude Code then calls `archaeology(file="AuthSessionManager.java")`:

```json
{
  "churn": {"commits_total": 87, "last_6mo": 12, "authors_last_6mo": ["nishasri", "umajhanavi"]},
  "co_change": ["RedisSessionStore.java (94% co-occurrence)", "JwtRefreshFilter.java (71%)"],
  "bus_factor": 1,
  "defect_proximity": "0.34 (above repo median 0.18)",
  "recent_changes": [
    {"sha": "abc1234", "date": "2026-05-12", "msg": "fix: race condition in session refresh under load", "author": "nishasri"},
    {"sha": "def5678", "date": "2026-04-28", "msg": "feat: TTL extension for premium tier", "author": "umajhanavi"}
  ]
}
```

That last commit — `def5678` — looks suspicious. Premium tier TTL extension landed 25 days before the P1 was reported.

Claude Code calls `impact(symbol="AuthSessionManager.extendTTL", depth=3)`:

```json
{
  "callers": [
    {"depth": 1, "symbol": "SessionRefreshScheduler.tick", "confidence": "EXTRACTED"},
    {"depth": 1, "symbol": "PremiumUpgradeService.upgrade", "confidence": "EXTRACTED"},
    {"depth": 2, "symbol": "CheckoutController.processOrder", "via": "AuthSessionManager.validate", "confidence": "AMBIGUOUS — virtual dispatch, 3 candidates"}
  ],
  "blast_radius_score": 0.78,
  "tests_covering": [
    {"test": "AuthSessionManagerTest.testExtendTTL", "confidence": "EXTRACTED"},
    {"test": "PremiumUpgradeServiceTest.testUpgradeExtendsTTL", "confidence": "EXTRACTED"}
  ],
  "tests_NOT_covering": [
    "Concurrent extendTTL from two callers (no test found matching pattern)"
  ]
}
```

Now Claude Code has a hypothesis: the `def5678` commit added a TTL extension code path that races with the `SessionRefreshScheduler.tick` cron. No test covers concurrent extension. Geetha reads Claude Code's hypothesis, confirms it manually, writes a failing test, fixes the race condition, ships the patch by 5pm.

**This whole interaction took ~40 minutes. Without forensic-deepdive, finding the suspect commit `def5678` would have meant grep-and-pray across 18,432 commits.**

### 3.3 Day 2 — the Graphiti agent brain

The next morning, Geetha asks Claude Code about a different bug: "checkout email confirmations sometimes fail silently."

Claude Code queries `impact(symbol="OrderConfirmationEmail.send")`. The MCP server returns the static graph view, **but it also returns a `INFERRED-from-prior-session` annotation**:

```json
{
  "callers": [...],
  "prior_session_insights": [
    {
      "session_id": "2026-05-23-checkout-p1",
      "verified_by": "geetha",
      "claim": "OrderConfirmationEmail.send is invoked synchronously from CheckoutController.processOrder. The send() failure mode is logged at WARN, not ERROR, and the calling code does not check the return.",
      "source": "AuthSessionManager.java + observed log output",
      "confidence": "INFERRED-from-prior-session"
    }
  ]
}
```

That insight wasn't in the static graph yesterday. It was **synthesized by Claude Code from the previous session's interaction with Geetha** — and stored in a Graphiti temporal knowledge graph alongside the LadybugDB structural graph. Today, Graphiti surfaces it as a hint: "this same call site has a known logging anti-pattern."

Geetha confirms, finds the swallowed exception, ships a 4-line fix. **Total time: 12 minutes.**

**This is the v0.2 product.** Static structural graph (LadybugDB) + temporal learning graph (Graphiti) + MCP server connecting both to any agent.

---

## 4. Architecture — what to build, layer by layer

This section is the spec. Cite section numbers when writing DEC entries.

### 4.1 Parsing layer

**Tree-sitter primary**, via `tree-sitter-language-pack` (v0.1 already uses this). Grammar priority order for v0.2:
1. Python (existing v0.1, refine)
2. TypeScript (NEW)
3. JavaScript (NEW)
4. Java (NEW)
5. Go (NEW)
6. C (existing, refine)
7. Dart (existing, **fix the catch-all reference query — Omi finding #1/#2**, the headline v0.1 defect)
8. Swift (existing, refine)
9. Rust (stretch — ship if time permits)

For each language, two outputs from the parse phase:
- **Definitions** — what symbols this file defines (function, class, method, interface, struct, enum, module, trait). Already done in v0.1 for the 4 languages.
- **References** — what symbols this file references. Per-language `tags.scm` reference queries. Aider has a reference query for each of these languages already — **borrow Aider's `tags.scm` files verbatim, attribute in NOTICE, refine where they're wrong** (e.g., Dart attribute-call exclusion per Omi finding #1).

LSP integration: **on-demand only**, not primary. Tree-sitter handles 95% of cases at ms-per-file. LSP comes in only when the call-graph builder hits ambiguity it can't resolve (interface dispatch with N implementations and no narrowing). Wire `pylsp`, `tsserver`, `gopls`, `jdtls`, `rust-analyzer` behind a `LspClient` interface; invoke on a single symbol, not as a batch indexer.

SCIP ingestion: **optional, opportunistic**. If `index.scip` exists in the repo root or `scip-typescript` / `scip-java` is on PATH, run them, parse the protobuf, **and upgrade every edge they confirm from INFERRED to EXTRACTED**. This is free precision when the user provides it.

### 4.2 Graph layer

**LadybugDB** (the live Kuzu fork that GitNexus uses) is the embedded persistence. Single-file DB at `.deepdive/graph.lbug`.

**Why LadybugDB and not Neo4j / DuckDB / Postgres**:
- Embedded — no server, no docker, no auth. Matches v0.1's $0 / offline / 92-second story.
- Columnar OLAP — query patterns are read-heavy graph traversals, not transactional writes.
- Cypher dialect — agents already know Cypher; humans can write it.
- LadybugDB is what GitNexus uses; matching gives us interop with their tooling and the `understand-quickly` registry format.

Hedge: abstract behind a `GraphStore` Python interface (DEC-013). Implement `LadybugStore` for v0.2. ArcadeDB (Apache-2.0, multi-model, 97.8% Cypher TCK) becomes the v1.0 server-mode option for huge repos.

**Schema** — keep this in `src/forensic_deepdive/graph/schema.py`:

Nodes:
- `File(path, language, role, sha, loc, last_modified)`
- `Symbol(qualified_name, kind, file_id, line_start, line_end, signature)` where kind ∈ {function, class, method, interface, struct, enum, module, trait, decorator, route}
- `Module(path, language)`
- `Commit(sha, author, date, message, files_touched_count)`
- `Author(email, name_canonical)` (with mailmap dedup)
- `Process(name, entry_point_symbol_id, terminal_symbol_id)` — for execution flows, populated lazily

Edges (all confidence-tagged):
- `CALLS(caller_symbol_id, callee_symbol_id, confidence, evidence)`
- `IMPORTS(file_id, module_id, confidence)`
- `EXTENDS(child_symbol_id, parent_symbol_id, confidence)`
- `IMPLEMENTS(impl_symbol_id, interface_symbol_id, confidence)`
- `DEFINES(file_id, symbol_id)` — always EXTRACTED
- `MEMBER_OF(symbol_id, parent_symbol_id)` — always EXTRACTED
- `TOUCHED_BY_COMMIT(file_id, commit_sha)` — always EXTRACTED
- `AUTHORED_BY(commit_sha, author_id)` — always EXTRACTED
- `CO_CHANGES_WITH(file_id_a, file_id_b, frequency)` — INFERRED, computed from commit history

Defer to v0.3: `HANDLES_ROUTE`, `FETCHES_FROM`, `INJECTS`, `DECLARES_BEAN`, `RENDERS` (framework-aware edges).

### 4.3 Pipeline as DAG of typed phases

The v0.1 5-stage pipeline (inventory → static → flatten → history → emit) was sequential. v0.2 becomes a typed DAG:

```
        inventory
            │
            ├──────► parse (per language, parallel)
            │              │
            │              └──► resolve (symbols, references, MRO)
            │                          │
            ├──────► history ◄─────────┤
            │                          │
            │                          ├──► build_graph
            │                          │         │
            │                          │         └──► persist (LadybugDB)
            │                          │
            │                          ├──► detect_cycles
            │                          │
            │                          └──► co_change_compute (joins history + graph)
            │                                          │
            └──────────────────────────────────────────┴──► emit (5 markdown + graph.json)
```

Each phase declares its inputs and outputs as typed dataclasses. The DAG runner (think a tiny in-process Airflow) topologically sorts and runs. **No external orchestrator** — pure Python.

Why this matters: in v0.3 you'll add Spring resolution and React resolution phases. They plug into the DAG between `resolve` and `build_graph`. v0.4 you'll add traceability matrix as a phase. The DAG is the extension point. **GitNexus uses this exact pattern (12 phases) and it's what lets them ship a new language or framework in one PR.**

### 4.4 Confidence taxonomy — adopt from Graphify, productize

Every edge in the graph carries `confidence ∈ {EXTRACTED, INFERRED, AMBIGUOUS}`. Definitions:

- **EXTRACTED** — deterministic from Tree-sitter AST or git log or LSP/SCIP confirmation. Edge weight 1.0 for ranking purposes.
- **INFERRED** — heuristic match. Receiver type inferred from constructor call. Same-name resolution within a module. String-literal cross-language match. Edge weight 0.6.
- **AMBIGUOUS** — multiple plausible targets with no narrowing context. Interface dispatch with N implementations. Polymorphic method on an unknown receiver type. Edge weight 0.3, surface ALL candidates with their individual confidences.

Every MCP response carries confidence. Every markdown artifact tags claims. Every visual edge (v0.4) is color-coded. **This is genuinely innovative UX vs. GitNexus, which has internal confidence scoring but doesn't surface it consistently.**

### 4.5 MCP server — 5 composite tools

`forensic serve --transport=stdio` starts the MCP server. Five tools at v0.2. **Composite, not endpoint-mirror.** Each tool internally fires multiple graph queries and returns a synthesized payload. The Klavis/Harness/Anthropic guidance is consistent: fewer, richer tools beat many narrow ones for agent ergonomics. Tool descriptions ≤ 200 tokens each.

**Tool 1: `impact(symbol, depth=3, direction="upstream", min_confidence="INFERRED")`**

Returns blast-radius analysis. Forward BFS from the symbol over CALLS / IMPORTS / DEFINES / EXTENDS edges. Depth-grouped buckets. Confidence-weighted score. Tests covering each callee identified by `tests_covering` lookup. Gaps surfaced as `tests_NOT_covering`.

**Tool 2: `query(natural_language=None, cypher=None)`**

Either: a Cypher query (precise, for agents that know what they want), or a natural-language query (compiled internally to BM25 + semantic + structural fusion with RRF, à la GitNexus). Returns a ranked symbol list with confidence and citations.

**Tool 3: `context(symbol)`**

The Glass-style single-call kitchen-sink. Returns: symbol definition + signature, all callers (with confidence), all callees (with confidence), all tests that reference, last 5 commits touching its file, dominant author of those commits, sibling symbols in the same class/module, cross-language hops if applicable. **One tool call = full 360° view.**

**Tool 4: `flow(entry_point, max_depth=10)`**

Walks execution flow from an entry point. Entry-point detection inside the tool (route handlers, event listeners, CLI mains, scheduled jobs, BLE callbacks). DFS along CALLS edges bounded by depth and language. Returns the execution path as a list of (symbol, file, line, confidence) tuples plus any cross-language boundaries crossed.

**Tool 5: `archaeology(file_or_symbol)`**

Returns: churn (commits/month), authors (with %), bus factor, co-change cluster, defect proximity score (frequency of touch in `fix:`/`bug:` commits), refactor history via `git log --follow`, last-touched date. **This is the wedge GitNexus structurally cannot match — they have no git layer.**

Defer to v0.3: `detect_changes(git_diff)`. To v0.4: `trace(requirement_or_ticket)`. To v1.0: `rename(symbol, new_name)`, `cross_language_navigate(symbol)`.

### 4.6 Graphiti — the agent's persistent brain (your specific question)

Yes — Graphiti is used in v0.2 and it's used exactly the way you described.

**Architectural role**: Graphiti is a **second graph**, separate from the LadybugDB structural graph. LadybugDB holds deterministic facts about the code (a CALLS b at line X). Graphiti holds **temporal, agent-derived insights** about the code that change as understanding deepens. Examples:

- Session 1, 2026-05-23: Geetha and Claude Code investigate the checkout P1. Claude Code generates the hypothesis "`AuthSessionManager.extendTTL` races with `SessionRefreshScheduler.tick` because the TTL extension commit `def5678` landed without a concurrency test." Geetha confirms by writing a failing test that reproduces. After the fix lands, Claude Code stores the verified insight as a Graphiti episode tied to `AuthSessionManager.extendTTL`.

- Session 2, 2026-06-04: Madhumitha is investigating a different bug. She queries `context(AuthSessionManager.extendTTL)`. The MCP server returns the structural graph view, **and** Graphiti is queried for any episodes tied to that symbol. The 2026-05-23 episode comes back: "verified concurrency hazard, fix in commit f4a2b1c, see test ConcurrentExtendTtlTest." Madhumitha now knows this code has a known concurrency-sensitivity before she touches it.

**Concrete implementation**:
- `graphiti-core ≥ 0.28` (Apache-2.0). Backend: **Kuzu embedded** (now LadybugDB-compatible — we reuse the same LadybugDB binary, different DB file).
- Two files in `.deepdive/`: `graph.lbug` (structural) and `graphiti.lbug` (temporal).
- A new MCP tool `record_insight(symbol, claim, evidence, verified_by)` lets agents write to Graphiti. Insights are bi-temporal — `valid_from` defaults to `now()`, `valid_until` stays open until contradicted.
- A `context` tool call queries both graphs and merges. Insights surface as `INFERRED-from-prior-session` with the session date.
- Contradicting insights don't delete the old one. Graphiti invalidates: the old episode gets `valid_until=now()`, the new episode is appended. **You can always query "what did we believe about X as of last Tuesday."**

**Threshold for activation**: Graphiti is heavyweight (LLM-dependent for entity extraction at ingestion). Same DEC-005 2-of-5 threshold from v0.1 stays: ≥ 50k LOC, ≥ 25 contributors, ≥ 18 months old, ≥ 200 PRs / 12mo, ≥ 100 issues w/ discussion. Below threshold, `record_insight` writes to a simple JSONL append-log; above threshold, it writes to Graphiti.

**LLM dependency**: Graphiti needs structured output for entity extraction. Cloud-default uses Claude Haiku (cheapest, fastest). Local mode uses Ollama with `qwen2.5-coder:32b` (DEC-009). If structured-output parsing fails on a given episode, skip-and-log; the structural graph remains complete.

**Why this matters for the product**: it's the answer to "is the tool self-updating, does it learn?" The structural graph doesn't learn — it's a deterministic projection of the code. Graphiti is where the system accumulates the human-and-agent-in-the-loop understanding that no static analyzer can ever extract. **Six months from now, on a healthy Spring repo, the Graphiti layer will be the most valuable artifact in the tool.**

### 4.7 Markdown artifacts — same five, regenerated from the graph

Keep the v0.1 contract: `MAP.md`, `HOTPATHS.md`, `ARCHAEOLOGY.md`, `MENTAL_MODEL.md`, `AGENT_BRIEF.md` in `docs/codebase/`. They are now **projections of the LadybugDB graph**, not directly emitted from in-memory NetworkX.

- `MAP.md` — top-N symbols by PageRank-on-graph, languages summary, role summary, test surface.
- `HOTPATHS.md` — dependency hot spots (PageRank on symbol graph, not file graph), cross-file dependencies (with confidence tags now), churn hot spots, churn × centrality (with the v0.1 finding #9 fix — centrality percentile threshold).
- `ARCHAEOLOGY.md` — same content as v0.1 plus the new co-change clusters, plus mailmap-deduped contributors, plus bot-account filter.
- `MENTAL_MODEL.md` — at-a-glance, entry points (now content-checked, not just filename-matched — Omi finding #5 fix), core modules from the graph, directory layers.
- `AGENT_BRIEF.md` — ≤ 5 KB, rule-shaped. Rules derived from:
  - Top centrality symbol → "treat X as load-bearing" rule.
  - Co-change cluster → "if you touch X also touch Y" rule.
  - High-churn-but-low-centrality file → "X is volatile, churn-only" rule.
  - Bus-factor-1 file → "X owned by @author" rule.
  - Defect-proximity > 2× median → "X is fragile" rule.

Cap held at 5 KB. Overflow goes to `AGENT_BRIEF_DEEP.md`. All confidence tags preserved.

### 4.8 Repomix — demoted

DEC-017: drop Repomix as primary artifact. The graph + MCP supersedes the role of "pack-the-repo-for-LLM." Move to `--legacy-repomix` flag in `forensic extract`. Document in CHANGELOG.

### 4.9 Multi-repo registry

GitNexus pattern. `~/.deepdive/registry.json` records every analyzed repo. `forensic list` shows them. `forensic mcp` serves all of them. When an MCP client connects, it queries `gitnexus://repos`-shape resources. Repo selector is optional on tools when only one repo is registered.

### 4.10 Agent skill emission — multi-platform

Every `forensic extract` writes the shims it can:
- `.claude/skills/forensic-deepdive-*.md` — at minimum: `exploring`, `debugging`, `impact-analysis`, `refactoring`, `onboarding`. Each is the kind of focused skill GitNexus emits via `--skills`.
- `.claude-plugin/plugin.json` if Claude Code plugins are present.
- `.cursor/rules/codebase.mdc` — Cursor rules format with `globs: ['**/*']` and `alwaysApply: true`.
- `.continue/rules/codebase.md` — Continue.dev rules format.
- `AGENTS.md` (cross-tool standard per LF AAIF) and `CLAUDE.md` (Anthropic) — never overwrite if present (v0.1 behavior, keep).

### 4.11 Confidence-aware Tree-sitter scope rules (DEC-012 refinement)

v0.1's DEC-012 (production-only / language-scoped / local-shadowed) stays. Add: when a reference resolves to multiple same-language candidates and none is locally shadowed, **emit AMBIGUOUS edges to ALL of them** rather than dropping the reference. This fixes the Omi finding #1/#2 false-edge problem honestly — surface the ambiguity, let the agent (or human) disambiguate.

### 4.12 File-role classification widening

v0.1 had source / test / fixture. v0.2 adds **vendored** and **generated** (Omi findings #3, #4):
- **vendored** — paths matching `vendor/`, `third_party/`, `node_modules/`, embedded version strings (`*-1.2.1*`), recognised library names.
- **generated** — `*.g.dart`, `*.freezed.dart`, `*_pb.py`, `*.generated.*`, files with `// GENERATED — DO NOT EDIT` markers.

Vendored and generated files are inventoried but excluded from PageRank-by-default. A `--include-vendored` flag exists for completeness.

### 4.13 Contributor pipeline fixes (Omi findings #6, #7)

- Read `.mailmap` if present, dedup contributors by canonical name.
- Filter `[bot]` and `*-bot` accounts by default. Surface in a separate "Automation" section.
- Keep raw author counts available in `archaeology.json` for accuracy.

### 4.14 Languages — go from 4 to 8

Add TypeScript, JavaScript, Java, Go. Borrow Aider's `tags.scm` for each (Apache-2.0, attribute in NOTICE). v0.2 acceptance test: each new language has ≥ 1 test fixture in `tests/fixtures/<lang>/` and parses cleanly. **Java for v0.2 is shallow** — get definitions and basic references; deep Spring-annotation resolution is v0.3.

---

## 5. Acceptance criteria for v0.2

These are the gates. **Do not tag v0.2.0 until every box is checked.**

### 5.1 Functional
- [ ] `forensic extract <repo>` produces `.deepdive/graph.lbug` for any repo in the 8 supported languages.
- [ ] All 5 markdown artifacts regenerated from the graph (not from in-memory).
- [ ] AGENT_BRIEF.md ≤ 5 KB hard cap holds on every test repo.
- [ ] `forensic serve --transport=stdio` starts an MCP server.
- [ ] All 5 MCP tools registered and callable. Each tool description ≤ 200 tokens.
- [ ] Every edge in the graph carries `confidence ∈ {EXTRACTED, INFERRED, AMBIGUOUS}`.
- [ ] Every markdown artifact tags claims with confidence.
- [ ] `record_insight` MCP tool writes to Graphiti above threshold, JSONL below.
- [ ] `context(symbol)` surfaces prior-session insights from Graphiti.
- [ ] Multi-repo registry at `~/.deepdive/registry.json` works; `forensic list` shows analyzed repos.
- [ ] Agent skill emission: at least 5 skills in `.claude/skills/`; `.cursor/rules/`, `.continue/rules/`, `AGENTS.md`, `CLAUDE.md` shims written.
- [ ] Repomix moved to `--legacy-repomix` flag.

### 5.2 Performance
- [ ] Omi (1,860 source files) extracts in ≤ 120 s on commodity laptop.
- [ ] GitNexus's own repo (TS-heavy, ~28k files) extracts in ≤ 600 s.
- [ ] `forensic extract` cache hit (no source changes) returns in ≤ 5 s.
- [ ] MCP `context(symbol)` query returns in ≤ 500 ms on Omi-scale graph.
- [ ] MCP `impact(symbol, depth=3)` returns in ≤ 2 s on Omi-scale graph.

### 5.3 Correctness
- [ ] Existing v0.1 test suite (100 tests) still passes.
- [ ] At least 20 new tests covering MCP tool responses, graph schema, confidence propagation, Graphiti integration.
- [ ] On Omi: `impact(Logger)` returns the Dart/Swift Logger as the central symbol with EXTRACTED confidence on its own definitions, INFERRED confidence on the v0.1 false-edge cases (the Dart catch-all), and AMBIGUOUS where multiple defs share a name.
- [ ] On a curated Java repo (suggest `spring-projects/spring-petclinic` — 65 files, well-understood): every `@Controller`/`@Service`/`@Repository` class is inventoried; method references between them produce reasonable INFERRED edges (no false EXTRACTED claims).
- [ ] Determinism: running `forensic extract` twice on the same repo produces byte-identical graph hashes.

### 5.4 Quality gates
- [ ] `uv run pytest -x` green.
- [ ] `uv run ruff check` clean.
- [ ] All new DEC entries (DEC-013 through DEC-020) committed to DECISIONS.md.
- [ ] PROGRESS.md updated at session end every session.
- [ ] CHANGELOG.md entry for v0.2.0.
- [ ] One example repo committed to `examples/spring-petclinic/` with all 5 artifacts.
- [ ] One example repo committed to `examples/gitnexus/` (yes, dogfood the competitor).

### 5.5 The honest-mode acceptance gate
- [ ] **Pure-static mode works end-to-end with no LLM at all.** `forensic extract <repo>` should succeed with no `ANTHROPIC_API_KEY`, no `OPENAI_API_KEY`, no Ollama running, no network. Graphiti is opt-in via `--with-graphiti` flag; default is off.

---

## 6. DEC entries to write before any code

Pre-draft these. Each gets written into DECISIONS.md in your first v0.2 session as you commit the decision. Number them DEC-013 onward, matching the existing log style.

- **DEC-013** — Adopt LadybugDB as embedded graph store, abstract behind `GraphStore` interface.
- **DEC-014** — Pipeline as DAG of typed phases (extends DEC-003 / DEC-012 architectural model).
- **DEC-015** — Confidence taxonomy on every edge: EXTRACTED / INFERRED / AMBIGUOUS (from Graphify, productized).
- **DEC-016** — MCP server with 5 composite tools at v0.2 (not endpoint mirrors).
- **DEC-017** — Drop Repomix as primary, move to `--legacy-repomix` flag.
- **DEC-018** — Multi-repo registry at `~/.deepdive/registry.json` (GitNexus pattern).
- **DEC-019** — Graphiti as the persistent agent-memory layer, gated by the existing DEC-005 2-of-5 threshold.
- **DEC-020** — Languages added in v0.2: TypeScript, JavaScript, Java, Go; Rust deferred to v0.3 stretch.
- **DEC-021** — File-role classification widened from {source, test, fixture} to {source, test, fixture, vendored, generated}.
- **DEC-022** — Contributor pipeline: read `.mailmap`, dedup canonical, filter `[bot]` accounts.

Defer to v0.3 planning (don't write yet): SCIP integration, LSP on-demand, ast-grep framework rule packs, Spring/React resolvers.

---

## 7. Test repos — what to run extract against

In order:
1. **Omi** (existing v0.1 baseline) — re-run, ensure v0.2 still works, regression-test the v0.1 findings have improved.
2. **`spring-projects/spring-petclinic`** — small (~65 files), well-documented, classic Spring Boot. Java grammar shakedown. **The Spring annotations won't be resolved by v0.2 (that's v0.3), but the file/symbol/dependency layer should be clean.**
3. **`abhigyanpatwari/GitNexus`** itself — TypeScript monorepo, the competitor we're benchmarking against. We need to be able to analyze it without crashing. Bonus: dogfood lets us legitimately critique their architecture decisions.
4. **`home-assistant/core`** — Python at massive scale, > 21k contributors, > 12 years of history. Stress-test the contributor pipeline, mailmap parsing, churn-cluster compute. Probably > 30 minutes to extract; document the result.
5. **`tiangolo/fastapi`** — Python web framework, will exercise the eventual v0.3 FastAPI annotation resolver. For v0.2 it's a clean Python check.

Commit example outputs to `examples/<repo>/` for at least Omi and spring-petclinic.

---

## 8. Tooling, installs, environment — you have full autonomy

You have permission to install:
- **uv** (Python project manager — already installed in v0.1, confirm).
- **Node.js + npm/pnpm** (LadybugDB has Python bindings via PyPI but the Node bindings get the most attention from the LadybugDB maintainer; install Node 20+ and pnpm in case you need the Node ecosystem).
- **graphiti-core ≥ 0.28** via pip / uv add.
- **Kuzu / LadybugDB Python bindings** — `pip install kuzu` (the LadybugDB fork is API-compatible; if upstream Kuzu is dead per Apple acquisition, switch to whichever pip package the LadybugDB team publishes).
- **Tree-sitter language pack** — already installed; verify TypeScript, JavaScript, Java, Go grammars present.
- **Docker** — only for testing alternative graph backends (ArcadeDB, FalkorDB) in v1.0 prep. Not required for v0.2.
- **Ollama or LM Studio** — only if you want to test the local-mode Graphiti path. Not required for v0.2 acceptance.
- **`scip-typescript`, `scip-java`** — optional; install if you want to verify the v0.3 SCIP-upgrade plumbing works in v0.2 as a stub.

**Log every global install in PROGRESS.md.** Same rule as v0.1.

**You can web-search.** You have WebSearch (and WebFetch if your CLI version supports it). Use it. Verify versions are current. If LadybugDB has a new release that fixes a bug we're hitting, check the changelog. If GitNexus shipped a feature this week that affects our positioning, know about it. **Do not build from training-data knowledge alone for any tool whose version matters.**

---

## 9. Working style — adhering to the existing v0.1 protocol

Nothing about the v0.1 session protocol changes. Restating because it's load-bearing:

### 9.1 Session start (mandatory)
1. Read `CLAUDE.md`.
2. Read `DECISIONS.md`. You are bound by every Active decision.
3. Read `PROGRESS.md`. The "Next" section is your task list.
4. Read THIS PRD (or its current revision) if v0.2 is in progress.
5. Run `git log --oneline -10`.
6. Confirm in one sentence: "Read all docs. Working on <next>, respecting DEC-<N>."

### 9.2 Session end (mandatory)
1. Append a dated PROGRESS.md entry with ✅ Done / 🚧 In flight / 🚫 Blocked / ⏭ Next.
2. If a non-trivial architectural choice was made, append a DEC-NNN entry.
3. Conventional-commit message.
4. Never push without explicit instruction.

### 9.3 If you disagree with the PRD

The PRD is the contract. But if the research dossier or your own implementation experience reveals that a section here is wrong:
1. Write a new DEC-NNN entry explaining the disagreement and the proposed change.
2. Ping Dhevenddra explicitly: *"I want to deviate from PRD §X.Y because Z. Please review DEC-NNN."*
3. Do not implement the deviation until Dhevenddra accepts.

Do not silently deviate. Do not "interpret creatively." If the spec is wrong, surface it.

### 9.4 If you get stuck

PROGRESS.md `🚫 Blocked: <what>, would be unblocked by <what>`. Don't guess. Dhevenddra is the bus you call.

---

## 10. The build order, for the avoidance of doubt

The phase order matters because some pieces depend on others. Build in this order:

1. **DEC-013 (LadybugDB)** + **GraphStore interface scaffold** + **schema** in code. No graph populated yet. Tests for the schema.
2. **Pipeline DAG runner** (DEC-014) — pull the v0.1 5 stages into the new typed-phase shape. Verify v0.1 behavior is preserved.
3. **Confidence taxonomy plumbing** (DEC-015) — add `confidence` field to every edge type, every artifact emitter, every MCP tool response. Initially everything is EXTRACTED (v0.1 behavior). Tests confirm the field flows through.
4. **Tree-sitter language expansion** (DEC-020) — TypeScript, JavaScript, Java, Go. Test fixtures + golden tests for each.
5. **Dart reference-query precision fix** (Omi finding #1, #2). Critical to clear before MCP launches against Omi again.
6. **File-role widening** (DEC-021) — vendored, generated detection.
7. **Contributor pipeline fixes** (DEC-022) — mailmap, bot filter.
8. **LadybugDB graph build phase** — populate the actual `.deepdive/graph.lbug` from the symbol graph. Multi-repo registry (DEC-018).
9. **5 markdown artifacts regenerated from the graph**, not from in-memory.
10. **MCP server with 5 tools** (DEC-016). `forensic serve` command. Test against Claude Code.
11. **Graphiti integration** (DEC-019). `record_insight` tool. `context` tool surfaces prior-session insights. Threshold gate.
12. **Drop Repomix as primary** (DEC-017). `--legacy-repomix` flag.
13. **Agent skill emission updates** — at least 5 skills, multi-platform shims.
14. **Acceptance test pass** — every box in §5.

15. **Tag v0.2.0**. Update CHANGELOG. Update PROGRESS.md. Update README to reflect the new product shape.

---

## 11. Things that are NOT in v0.2 (do not build)

- Spring annotation resolution (v0.3).
- React component / hook resolution (v0.3).
- Cross-stack tracing (React fetch ↔ Spring @RequestMapping) (v0.3).
- LSP-on-demand integration (v0.3).
- SCIP ingestion (v0.3 stub only, full v0.3).
- ast-grep YAML framework rule packs (v0.3).
- Sigma.js visual viewer (v0.4).
- Traceability matrix (v0.4).
- Merkle-tree incremental indexing (v1.0; for v0.2, full re-extract or cache-hit-if-no-changes is fine).
- `rename` MCP tool (v1.0).
- `cross_language_navigate` MCP tool (v1.0).
- `detect_changes` MCP tool (v0.3).
- `trace` MCP tool (v0.4).
- Web UI (v1.0+).
- Cloud-hosted version (no).
- Wiki generation (no, ever — different product).

If you find yourself drifting toward any of these, stop. Write a note in PROGRESS.md and move on.

---

## 12. The user-experience contract

Once v0.2 is done, the developer experience is:

```bash
# Install once
pipx install forensic-deepdive

# Analyze any repo
cd ~/work/some-repo
forensic extract .                       # builds graph, writes artifacts, emits shims
forensic list                            # shows registered repos
forensic mcp                             # starts MCP server (or: forensic serve)

# Re-analyze after changes
forensic extract . --update              # cache-aware re-extract

# Use from any agent harness
# Claude Code: shims are written, MCP auto-registers via .mcp.json
# Cursor: .cursor/rules/codebase.mdc is written, MCP via cursor/mcp.json
# Codex: AGENTS.md is written, MCP via codex mcp add
# Continue: .continue/rules/codebase.md is written, MCP via config.yaml
```

The agent then queries the graph naturally:

> Geetha to Claude Code: "What does AuthSessionManager do and who owns it?"
>
> Claude Code (under the hood): `context(AuthSessionManager)`.
>
> Geetha: "If I rename `processOrder` to `submitOrder`, what breaks?"
>
> Claude Code: `impact(processOrder, depth=3)`.
>
> Geetha: "Trace what happens when a user clicks Buy."
>
> Claude Code: `flow(entry_point="Buy" or matching route)`.
>
> Geetha: "Who's the right person to ping about the checkout module?"
>
> Claude Code: `archaeology(file="src/checkout/")`.

That's the product. v0.2 makes the four sentences above work end-to-end.

---

## 13. What success looks like

v0.2 is successful if:
1. A developer hands an unfamiliar 5000-file Python or Java repo to Claude Code with forensic-deepdive installed, and Claude Code can answer "where do I start to fix bug X" in 5 tool calls or fewer.
2. The Graphiti layer accumulates ≥ 10 verified insights over a week of dogfooding on a real repo.
3. We can run `forensic extract` on GitNexus's own repo and produce honest, accurate analysis. Bonus if we can ship a polite blog post comparing the two tools.
4. Apache-2.0 + Graphiti agent brain + MCP-with-5-tools + cross-stack-roadmap is a position we can credibly defend against any current OSS competitor.

v0.2 is unsuccessful if:
1. It still feels like "v0.1 plus features." If a developer reads the v0.2 README and the v0.1 README and can't tell them apart, we failed.
2. The MCP server requires more than `pipx install forensic-deepdive && forensic mcp` to use.
3. Graphiti is fragile / requires Docker to be running / breaks on local-only mode. The bar is "Geetha can use this on her laptop with no network."
4. The pure-static mode requires an LLM. It must not.

---

## 14. Closing note — to Claude Code, from Dhevenddra (drafted via Claude)

This is the project I most want to ship in 2026. v0.1 was the proof you could build a thing. v0.2 is the proof you can build the thing.

You have full autonomy on implementation. Disagree with the PRD when the PRD is wrong, but disagree explicitly via DEC entries — don't silently rewrite. Install whatever tools you need. Web-search whatever you need to verify. Don't trust your training data for any version-sensitive question.

I'll be supervising — reviewing commits, checking DEC entries, running the tool on real repos. If you finish a phase early, surface that. If you hit a wall, surface that. If you find a research dossier claim is wrong (the research is dated 2026-05-23, things may have shifted), surface that with a citation.

The competitive window is closing. GitNexus is real, they're shipping fast, and they're PolyForm-Noncommercial — which is our shot. Let's take it.

Go.

---

*PRD version: 1.0 · Date: 2026-05-23 · Companions: KICKOFF_v0.2.md, research_v0.2.md · Source: this conversation*
