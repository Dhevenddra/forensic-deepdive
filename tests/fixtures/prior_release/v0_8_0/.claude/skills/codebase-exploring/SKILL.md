---
name: codebase-exploring
description: Orient quickly in this codebase. Use when the user says "walk me through this repo", "where do I start", "how is X organized", "explain the architecture", or opens an unfamiliar file and asks what it does. Reads docs/codebase/MENTAL_MODEL.md (entry points, layers, domains) and docs/codebase/MAP.md (most central files, key definitions). Do NOT use for bug-hunting (use codebase-debugging) or for predicting blast radius of a change (use codebase-impact-analysis).
---

# Codebase exploring

Read-only orientation. Answer 'what is this and how is it laid out' without re-deriving structure by walking files.

## When to use
- User is new to a region of code or the whole repo.
- Question shape: 'what is this', 'how is X organized', 'where does the request flow start', 'what are the main modules'.
- User just opened an unfamiliar file and asks about it.

## When NOT to use
- User reports a bug or unexpected behavior → `codebase-debugging`.
- User wants to change something and asks 'what will break' → `codebase-impact-analysis`.
- User is brand new to the team and wants the broad brief → `codebase-onboarding`.
- Question is code-semantic ('does this handle null') — just read the file.

## How to answer

1. **Always read `docs/codebase/AGENT_BRIEF.md` first** — it's small and pins the never/always rules.
2. Match the question shape:

| Question shape | Artifact |
|---|---|
| 'What are the entry points / domains' | `docs/codebase/MENTAL_MODEL.md` |
| 'Most central / load-bearing files' | `docs/codebase/MAP.md` |
| 'Key definitions in this module' | `docs/codebase/MAP.md` (Key definitions) |
| 'What rules apply when editing X' | `docs/codebase/AGENT_BRIEF.md` |

3. If an MCP server (`forensic serve`) is running, also call `context(symbol)` to get the symbol's neighborhood in one shot.

## Citation rule
Cite `docs/codebase/MAP.md:142-158` or `docs/codebase/AGENT_BRIEF.md:23`. Never paraphrase a fact without a line citation.
