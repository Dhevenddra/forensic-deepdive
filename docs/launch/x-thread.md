# X/Twitter thread draft (DEC-119)

**Status: draft only — not posted.** Owner posts manually. Verify commands/links
against the live repo before posting. Character counts below are approximate (drafted
for the ~280-char limit); tighten at post time if any tweet runs long.

---

**1/5**
Your AI coding agent re-discovers your codebase's architecture every single session.

`forensic-deepdive` builds a persistent knowledge graph + MCP server once, so it
doesn't have to. Apache-2.0.

🧵

---

**2/5**
The problem with most code-graph tools: they resolve a symbol call across files by
guessing, and hand the agent the guess as if it were a fact.

`forensic-deepdive` tags every single edge:
🟢 EXTRACTED — deterministic (AST / git log)
🟡 INFERRED — a heuristic resolved cleanly
🔴 AMBIGUOUS — multiple candidates, all shown

---

**3/5**
So an agent (or you) can filter: `impact(symbol, min_confidence="EXTRACTED")` and get
only what's actually true, not what's plausible.

Nothing else I've found in this category tags confidence at the edge level.

---

**4/5**
GitNexus is the strongest tool in this space — and it's PolyForm Noncommercial, which
locks out every commercial user.

`forensic-deepdive` is the Apache-2.0 alternative: same persistent-graph + MCP shape,
plus git archaeology, agent memory, and 5 committed markdown artifacts as a fallback
for agents that don't speak MCP.

---

**5/5**
No API key required to run it — pure static analysis by default.

```
uv tool install forensic-deepdive
forensic extract /path/to/repo
```

9 languages. 9 MCP tools. 989 tests.

https://github.com/Dhevenddra/forensic-deepdive

## Posting notes

- Post as a single thread, tweet 1 pinned for the day.
- Author disclosure not needed on X (own account = implicit), but don't overclaim: no
  "autonomous agent" language anywhere in the thread — that claim is explicitly not made
  (see `docs/findings/HONEST.md`).
