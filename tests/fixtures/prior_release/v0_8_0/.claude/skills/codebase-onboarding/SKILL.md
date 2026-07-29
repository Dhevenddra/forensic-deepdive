---
name: codebase-onboarding
description: Brief a new engineer on this codebase. Use when the user says "I just joined this team", "onboard me to this repo", "I'm new here — what should I know", "give me the first-day brief". Reads all five artifacts in order (docs/codebase/AGENT_BRIEF.md → MENTAL_MODEL → MAP → HOTPATHS → ARCHAEOLOGY) and surfaces ownership / bus-factor data from ARCHAEOLOGY. Do NOT use for specific bug-hunting (use codebase-debugging), targeted orientation (use codebase-exploring), or change-planning (use codebase-impact-analysis or codebase-refactoring).
---

# Codebase onboarding

The first-day brief. One pass through all five artifacts, ordered for a new engineer.

## When to use
- User explicitly signals they are new to this codebase / team.
- Question shape: 'onboard me', 'what should I know', 'give me the first-day brief', 'I'm new here'.

## When NOT to use
- User has a specific task (bug, feature, refactor) → use the targeted skill.
- User is mid-task and asks a focused question → use `codebase-exploring` or `codebase-debugging`.

## How to answer — read in this order

1. **`docs/codebase/AGENT_BRIEF.md` (≤ 5 KB)** — the never/always rules, the load-bearing symbol, the coupling rules. This is the floor; everything else is depth.
2. **`docs/codebase/MENTAL_MODEL.md`** — entry points, layers, domains. The 'what is this product' answer.
3. **`docs/codebase/MAP.md`** — most central files, key definitions. Where the weight is.
4. **`docs/codebase/HOTPATHS.md`** — hot spots, cross-file dependencies, churn × centrality. What's actively changing.
5. **`docs/codebase/ARCHAEOLOGY.md`** — top contributors with share %, bus factor, recent commits. **Who to ask about what.**

## Surface ownership
After the read-through, name the top 3 contributors by share % from ARCHAEOLOGY.md and what they own (most-touched files). Bus-factor warnings go up front. A new engineer needs to know whose code they're about to step on.

## Citation rule
Cite every artifact line: `docs/codebase/AGENT_BRIEF.md:12`, `docs/codebase/ARCHAEOLOGY.md:34`. The brief should be navigable, not a paraphrase.

## What to report back
- One-paragraph 'what is this product' summary from MENTAL_MODEL.
- 5 named load-bearing files with one-line descriptions from MAP.
- Top 3 contributors with share % and the files they own from ARCHAEOLOGY.
- Every 'Always' rule from docs/codebase/AGENT_BRIEF.md, verbatim.
- Suggested next-step skill: 'for a specific bug, switch to `codebase-debugging`; for a change, `codebase-impact-analysis`.'
