# Show HN draft (DEC-119)

**Status: draft only — not posted.** Owner posts manually, with the standard HN
disclosure (submitting as the author). Verify every command in this draft against the
live repo immediately before posting — a flag name or count can drift between when this
was written and when it goes out.

## Submission

- **Title:** `Show HN: forensic-deepdive – Apache-2.0 code knowledge graph + MCP server for AI agents`
- **URL:** https://github.com/Dhevenddra/forensic-deepdive

Per HN convention, the title stays plain and non-editorializing (no "I built", no
superlatives) and the URL is the repo, not a landing page. The pitch goes in the first
self-comment, posted immediately after submission.

## First comment (the pitch)

> Author here. `forensic-deepdive` analyzes a codebase (9 languages — Python, C, Dart,
> Swift, TypeScript, JavaScript, Java, Go, Rust) and builds a persistent knowledge graph
> plus an MCP server, so a coding agent (Claude Code, Cursor, Codex, Continue, Cline,
> Windsurf) doesn't re-derive your architecture from scratch every session.
>
> The reason I built it instead of using GitNexus, which is the strongest tool in this
> space right now: GitNexus is PolyForm Noncommercial-licensed, which rules out any
> commercial use. This is Apache-2.0.
>
> The other thing I haven't seen elsewhere: every edge in the graph, and every claim in
> the emitted docs, carries a confidence tag — `EXTRACTED` (deterministic, from the AST
> or `git log`), `INFERRED` (a heuristic resolved cleanly), or `AMBIGUOUS` (multiple
> candidates, all shown, none silently picked). A code-graph tool that resolves symbol
> `X` across five files by guessing and tells you it guessed is worth more to an agent
> than one that guesses silently.
>
> Concretely it produces: a persistent embedded graph (LadybugDB, an embedded Kuzu
> fork) with File/Symbol/Module/Commit/Author/Endpoint nodes; an MCP server exposing 9
> composite tools (impact, context, archaeology, flow, query, record_insight,
> recall_insights, visualize, trace); and five durable markdown artifacts
> (MAP/HOTPATHS/ARCHAEOLOGY/MENTAL_MODEL/AGENT_BRIEF) committed to the repo so any
> agent, MCP-aware or not, gets the same context.
>
> Honest framing, because I'd rather undersell than oversell: this is an
> **assisted-analysis** tool. A real fresh-agent test confirmed it's usable and that an
> agent auto-discovers `AGENT_BRIEF.md` unprompted. Whether seeding an agent with this
> graph makes it resolve real issues measurably faster, end-to-end, autonomously — that
> is **not proven yet**, and I say so in the README rather than imply otherwise. Details
> in [`docs/findings/HONEST.md`](https://github.com/Dhevenddra/forensic-deepdive/blob/main/docs/findings/HONEST.md).
>
> Try it: `uv tool install forensic-deepdive && forensic extract /path/to/repo`. 989
> tests, Apache-2.0, no LLM key required to run it (Graphiti is an opt-in extra above a
> size threshold). Happy to answer questions about the `Endpoint` join-node design,
> the confidence-resolution heuristics, or why LadybugDB over a plain SQLite/JSON
> graph.

## Posting notes

- Weekday, US morning (per prior HN-timing convention used for the v0.8 launch wave).
- Do not edit the first comment after early replies land — HN treats edits post-engagement
  as bad form.
- Link failure modes honestly if asked (GATE A / autonomous claim, hardware-gated).
