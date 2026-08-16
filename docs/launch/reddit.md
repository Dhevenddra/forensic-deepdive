# Reddit drafts (DEC-119)

**Status: draft only — not posted.** Owner posts manually with author disclosure
("I built this"). Verify commands/links against the live repo before posting.

Both posts lead with the confidence-tagged code graph, not a feature dump, and both
carry the same Apache-2.0-vs-GitNexus wedge — worded differently per subreddit norms.

---

## r/mcp

**Title:** `forensic-deepdive: an MCP server backed by a confidence-tagged code knowledge graph (Apache-2.0)`

**Body:**

Sharing an MCP server I built: `forensic-deepdive`. It builds a persistent graph of a
codebase (9 languages) — File/Symbol/Module/Commit/Author/**Endpoint** nodes, CALLS/
IMPORTS/EXTENDS/TOUCHED_BY_COMMIT edges, plus cross-boundary HANDLES/CALLS_ENDPOINT/
**ROUTES_TO** edges that unify five protocols (HTTP, MCP tools, registry-dispatch, gRPC,
messaging) through one `Endpoint` join node — then serves it via 9 composite MCP tools:
`impact`, `context`, `archaeology`, `flow`, `query`, `record_insight`,
`recall_insights`, `visualize`, `trace`.

The part I think is actually new for this category: **every edge carries a confidence
tag** — `EXTRACTED` (deterministic AST/git fact), `INFERRED` (a heuristic resolved
cleanly), or `AMBIGUOUS` (multiple candidates surfaced, not silently collapsed). When an
agent calls `impact(symbol, min_confidence=...)` it can filter out the guesses instead
of inheriting them as facts. I haven't seen another MCP code-graph server expose that.

It's also Apache-2.0. GitNexus is the strongest tool in this space and I'd recommend
looking at it too, but it's PolyForm Noncommercial, which is a hard blocker for a lot
of MCP-server use cases (anything behind a company's agent stack). This is the
Apache-2.0 alternative with a similar persistent-graph-plus-MCP shape.

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

Run `forensic extract <repo>` once first to build the graph. Repo + docs:
https://github.com/Dhevenddra/forensic-deepdive

Honest caveat up front since this sub cares about that: it's proven **usable** (a
fresh-agent test confirmed auto-discovery of the generated brief and correct MCP
routing) but **not** proven to make autonomous end-to-end issue resolution measurably
faster — that measurement is still hardware-gated. Details in
[`docs/findings/HONEST.md`](https://github.com/Dhevenddra/forensic-deepdive/blob/main/docs/findings/HONEST.md).

---

## r/ClaudeAI

**Title:** `Built a tool that gives Claude Code a persistent, confidence-tagged map of a codebase (skills auto-install, Apache-2.0)`

**Body:**

If you've ever had Claude Code re-explore the same unfamiliar repo every session, this
might help: `forensic-deepdive` runs once (`forensic extract /path/to/repo`) and writes:

- a `CLAUDE.md` shim pointing at `AGENT_BRIEF.md` (≤5 KB of assertive Never/Always
  rules, so it's cheap context on every session)
- 4 more markdown artifacts (MAP, HOTPATHS, ARCHAEOLOGY, MENTAL_MODEL) for deeper dives
- 5 single-intent Claude skills under `.claude/skills/codebase-{exploring,debugging,
  impact-analysis,refactoring,onboarding}/` and a plugin manifest, so Claude Code
  routes to the right one unprompted
- an MCP server (`forensic serve`) if you want live graph queries instead of static docs

The thing I care most about, and that I haven't seen elsewhere: every fact it emits is
tagged `EXTRACTED` (deterministic — AST or `git log`), `INFERRED` (a heuristic resolved
cleanly), or `AMBIGUOUS` (multiple candidates, shown, not guessed). So when
`AGENT_BRIEF.md` tells Claude something, Claude — and you — can tell how much to trust
it, instead of a wall of confident-sounding prose that's secretly 40% guesswork.

It's Apache-2.0 (the closest comparable tool, GitNexus, is PolyForm Noncommercial —
worth knowing if you're using this at a company).

```bash
uv tool install forensic-deepdive
forensic onboard --repo /path/to/repo   # analyzes + wires up the MCP server, guided
```

Honest note: this is an assisted-analysis tool. A real test confirmed it's usable and
that Claude auto-discovers the brief and picks the right skill. Whether it makes Claude
*resolve issues* measurably faster end-to-end, autonomously, is a claim I'm explicitly
**not** making yet — see
[`docs/findings/HONEST.md`](https://github.com/Dhevenddra/forensic-deepdive/blob/main/docs/findings/HONEST.md)
if you want the unvarnished version.

Repo: https://github.com/Dhevenddra/forensic-deepdive

## Posting notes

- Stagger after Show HN and lobste.rs (per prior v0.8 posting-order convention);
  r/mcp and r/ClaudeAI can go same day since audiences barely overlap.
- Author disclosure on both ("I built this") per subreddit self-promo norms.
