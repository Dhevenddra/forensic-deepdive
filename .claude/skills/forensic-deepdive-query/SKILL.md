---
name: forensic-deepdive-query
description: Answer questions about the current repo by querying its existing forensic-deepdive artifacts (MAP.md, HOTPATHS.md, ARCHAEOLOGY.md, MENTAL_MODEL.md, AGENT_BRIEF.md). Use when the user asks "where does X live", "who owns Y", "how did Z evolve", "what should I touch to add a new W" — AND the repo already has these artifacts under docs/codebase/. Do NOT use for code-semantic questions like "does this handle null correctly" — just read the file.
---

# Forensic Deep-Dive — Query

Answer from precomputed artifacts instead of re-reading the codebase.

## When to use
- `docs/codebase/MAP.md` exists.
- Question is navigational: "where", "who owns", "how did", "what are entry points", "blast radius of editing X".

## When NOT to use
- Artifacts >30 days old AND ≥50 commits since last extract → trigger `forensic-deepdive-update` first.
- Question is code-semantic ("does this function handle null") → just read the file.
- User wants to verify a specific implementation detail → read the source.

## How to answer

1. **Always read `docs/codebase/AGENT_BRIEF.md` first** — it's small and contains the rules.
2. Match the question shape:

| Question shape | Artifact to grep |
|---|---|
| "Where does X live" / "who owns" | `docs/codebase/MAP.md` |
| "How did X evolve" / "when was X introduced" / "who wrote X" | `docs/codebase/ARCHAEOLOGY.md` |
| "Critical path through feature X" / "trace request lifecycle" | `docs/codebase/HOTPATHS.md` |
| "Explain X" / "what's the architecture" | `docs/codebase/MENTAL_MODEL.md` |
| "What rules apply when editing X" | `docs/codebase/AGENT_BRIEF.md` |

3. Only if none answer, run:
   ```bash
   forensic query "<question>"
   ```
   (v0.2 — uses MCP server if installed, otherwise greps the artifacts.)

## Citation rule

Always cite: `docs/codebase/MAP.md:142-158`. Never paraphrase without a line citation. If you can't find a citation, say so — don't fabricate.

## What to report back

- The answer, with file:line citations from the artifacts.
- If multiple artifacts contain related context, link them all.
- If the artifact seems stale (date in `<!-- generated -->` header > 14 days old), warn the user and offer to run `forensic-deepdive-update`.
