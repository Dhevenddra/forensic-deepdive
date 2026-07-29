---
name: codebase-impact-analysis
description: Predict the blast radius before changing code. Use when the user proposes "rename X", "remove Y", "change the signature of Z", "deprecate this function", "what depends on this", "safe to delete". If MCP server is running, calls impact(symbol, direction='upstream') and context(symbol). Otherwise reads docs/codebase/HOTPATHS.md (cross-file dependencies) and docs/codebase/AGENT_BRIEF.md (coupling rules). Do NOT use for orientation or pure debugging — use codebase-exploring or codebase-debugging.
---

# Codebase impact analysis

Predict downstream effects of a change BEFORE making it. Never recommend a rename / removal / signature change without first surfacing callers and co-change neighbors.

## When to use
- User proposes a rename, signature change, removal, deprecation, or split.
- Question shape: 'what depends on this', 'safe to delete X', 'where is Y called from', 'what breaks if I change Z'.

## When NOT to use
- User is reading code to understand it → `codebase-exploring`.
- User is hunting a bug → `codebase-debugging`.
- User is restructuring with full knowledge of callers → `codebase-refactoring`.

## How to answer

1. **Always read `docs/codebase/AGENT_BRIEF.md` first** — coupling rules ('if you touch X also touch Y') often pre-answer the question.
2. **If MCP server is running** (`forensic serve`):
   - `impact(symbol, depth=3, direction='upstream')` — every caller, depth-bucketed, with confidence per edge.
   - `context(symbol)` — definition + callers + callees + parent + siblings + members + recent commits in one call.
3. **If MCP isn't running:**

| Question shape | Artifact |
|---|---|
| 'Cross-file dependencies' | `docs/codebase/HOTPATHS.md` (Cross-file dependencies) |
| 'Coupling rules for this file' | `docs/codebase/AGENT_BRIEF.md` (Always rules) |
| 'Co-change cluster' | `docs/codebase/HOTPATHS.md` (Co-change clusters) |

## Confidence discipline
The graph tags every edge `EXTRACTED` / `INFERRED` / `AMBIGUOUS` (DEC-015). When recommending a change, **call out AMBIGUOUS callers explicitly** — the resolver was unsure, so the human should double-check.

## Citation rule
Cite `docs/codebase/HOTPATHS.md:42` or the MCP tool output verbatim. Never say 'X is safe to delete' without showing the caller list (even when empty — 'no callers found in docs/codebase/HOTPATHS.md and impact() returned 0 upstream').
