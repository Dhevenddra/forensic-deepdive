# KICKOFF — forensic-deepdive v0.2

Paste this verbatim as your first message to Claude Code when starting the v0.2 build.

---

## The prompt (paste from here)

```
You are starting v0.2 of forensic-deepdive. v0.1 shipped May 23, 2026.
v0.2 is the BIG recut: from structural orienter to real code knowledge
graph. This is not v0.1+. It's v2 of the product, shipped as a phased
upgrade.

# Session-start protocol (mandatory — do NOT write code first)

Read these documents in this exact order, then confirm in one
sentence what you understand:

1. CLAUDE.md — your operating manual (existing).
2. DECISIONS.md — every Active DEC is binding (existing, DEC-001..012).
3. PROGRESS.md — see the v0.1 PROGRESS at the bottom; v0.2 work starts
   at the top.
4. PRD_v0.2.md — the v0.2 contract. This is what you're building.
5. research_v0.2.md — the competitive landscape and architectural
   evidence behind the PRD. Treat as evidence, not directive. If a
   PRD claim contradicts the research, the PRD wins by default but you
   may raise it via a new DEC entry.

Then: git log --oneline -10.

Confirm in ONE sentence:
"Read all five docs. v0.1 status: <tag>. Starting v0.2 phase 1 (DEC-013
LadybugDB scaffold per PRD §10), respecting DEC-011 (pure-Python
PageRank) and DEC-012 (graph scoping)."

Do NOT begin implementation before that sentence.

# Operating autonomy

You have full freedom. Install whatever tools, whatever versions.
The PRD §8 lists what's expected; you can add more.

You can web-search and web-fetch. USE THEM. Do not build from training
data alone on any version-sensitive question. Specifically: verify
LadybugDB / Kuzu fork status, graphiti-core current API, tree-sitter
language pack version, GitNexus current state.

If you install something globally, log it in PROGRESS.md under
"🛠 Tooling installed globally" for that session.

# What you're building (in one sentence)

A LadybugDB-backed persistent code knowledge graph with MCP server,
confidence-tagged edges, git archaeology, and Graphiti as the
agent's persistent learning brain — emitted to the existing 5
markdown artifacts, queryable from Claude Code / Cursor / Codex /
Continue / Cline.

# Working rules (summary — full version in CLAUDE.md and PRD §9)

- Apache-2.0 throughout.
- Python 3.11+, uv-managed.
- Pure-static mode (no LLM) MUST work end-to-end. Graphiti is opt-in.
- Three skills retained (extract / query / update); update them as
  v0.2 capabilities grow.
- Five artifacts retained (MAP / HOTPATHS / ARCHAEOLOGY /
  MENTAL_MODEL / AGENT_BRIEF). They get regenerated from the graph.
- AGENT_BRIEF.md ≤ 5 KB enforced in CI.
- Never push without explicit ask.
- Conventional commits.
- Tests before merge.

# Disagreement protocol

The PRD is the contract. If you disagree:
1. Write a new DEC-NNN entry explaining the proposed deviation.
2. Ping Dhevenddra: "I want to deviate from PRD §X.Y because Z."
3. Do NOT implement until Dhevenddra accepts.

Do not silently deviate.

# Session-end protocol (mandatory)

1. PROGRESS.md entry with ✅ / 🚧 / 🚫 / ⏭ sections, dated.
2. New DEC entry if non-trivial architectural choice was made.
3. Conventional-commit message.
4. Tell me what you did, what's next, what (if anything) you hit.
5. Do NOT push without explicit instruction.

# First task (after the confirmation sentence)

From PRD §10 (the build order), start with item 1:

1. DEC-013 (LadybugDB) + GraphStore interface scaffold + schema in
   code. No graph populated yet. Tests for the schema.

Show me:
- The DEC-013 entry you append to DECISIONS.md.
- The GraphStore Python interface (src/forensic_deepdive/graph/store.py).
- The LadybugStore implementation skeleton (methods raise
  NotImplementedError, types are correct).
- The schema (src/forensic_deepdive/graph/schema.py) with Node and
  Edge dataclasses including the `confidence` field.
- A passing test that LadybugStore() can be instantiated, can connect
  to a temp .lbug file, and can round-trip a single Symbol node.

Stop after that. We decide whether to continue to item 2 in the same
session or break.

# What NOT to do in the first session

- Do not start populating the graph from real code yet (that's items
  2-8).
- Do not write the MCP server (item 10).
- Do not touch Graphiti yet (item 11).
- Do not delete the existing v0.1 in-memory NetworkX graph yet — both
  paths coexist until the migration completes.
- Do not be clever. The plan is the plan.

# How I supervise

I review every DEC entry. I run the tool on real repos. I challenge
deviations. If I'm not responsive for hours, keep working on items
within the established architecture — don't wait.

Go.
```

(end of prompt)

---

## Anti-patterns to watch for in v0.2

- **Claude wants to add a dependency not in PRD §8.** Push back. Either we don't need it, or it gets a new DEC entry first.
- **Claude wants to use NumPy/SciPy for graph math.** Block. DEC-011 stays Active. Pure-Python kernels.
- **Claude wants to make the LLM mandatory.** Block. PRD §13 says pure-static mode is non-negotiable.
- **Claude wants to ship the MCP server before the graph is populated.** Block. PRD §10 order is the order.
- **Claude wants to silently rewrite the 5-artifact contract.** Block. PRD §4.7 is the contract.
- **AGENT_BRIEF.md emitted at >5kb.** That's a bug. File and fix.

## When to invoke each skill (unchanged from v0.1)

- `forensic-deepdive-extract` — first time on a repo.
- `forensic-deepdive-query` — answering questions from existing artifacts.
- `forensic-deepdive-update` — refreshing stale artifacts.

v0.2 adds MCP tool calls as a fourth path — agents talk to the running `forensic serve` server directly. Skills remain the documented onboarding interface.

## Closing — to Claude Code

This project matters. Take it seriously. Don't sandbag. Don't over-engineer. Ship.
