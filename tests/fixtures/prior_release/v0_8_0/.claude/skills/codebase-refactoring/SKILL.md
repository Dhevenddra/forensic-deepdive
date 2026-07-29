---
name: codebase-refactoring
description: Run a refactor with awareness of coupling and co-change patterns. Use when the user says "refactor X", "extract method", "split this class", "consolidate duplicated logic", "move this to its own module". Reads docs/codebase/AGENT_BRIEF.md coupling rules and docs/codebase/HOTPATHS.md co-change clusters; calls MCP context(symbol) and impact(symbol) when available. Do NOT use for single-file renames (just edit), bug-hunting (use codebase-debugging), or pure exploration (use codebase-exploring).
---

# Codebase refactoring

Coordinate multi-file structural changes against the codebase's coupling rules and co-change history. A refactor is not 'rename + reformat' — it's 'move responsibility while preserving every caller's contract.'

## When to use
- User wants to extract / inline / split / consolidate code across files.
- Question shape: 'refactor X to do Y', 'extract method', 'split this class into A and B', 'consolidate this duplicated logic'.

## When NOT to use
- Change is contained in one file → just do the edit.
- User is investigating a bug → `codebase-debugging`.
- User is reading to understand → `codebase-exploring`.

## How to answer

1. **Read `docs/codebase/AGENT_BRIEF.md` first.** The 'if you touch X also touch Y' rules pre-encode the co-change neighborhood — refactors that ignore them break things in adjacent files.
2. **Read `docs/codebase/HOTPATHS.md` 'Co-change clusters' section.** Files that historically co-change with the target should be reviewed in the same PR.
3. **If MCP server is running:**
   - `context(target_symbol)` — full neighborhood (callers, callees, parent class, siblings, members, recent commits).
   - `impact(target_symbol, direction='upstream')` — every caller that will need to compile after the change.
4. **Surface the dominant author from ARCHAEOLOGY.md** if the target file has one — they own the historical context.

## Pitfalls
- Don't refactor a symbol with AMBIGUOUS callers without listing them first — the human should resolve the ambiguity.
- Don't refactor a symbol whose co-change cluster includes files the user didn't mention — flag those files, ask if they should be in scope.
- Don't auto-rename across a polyglot graph (DEC-012's language-scoped rule) without checking that the symbol's other-language references are intentional.

## Citation rule
Cite every coupling rule (`docs/codebase/AGENT_BRIEF.md:23`) and every co-change pair (`docs/codebase/HOTPATHS.md:78`). Never propose a multi-file refactor without first showing the impact list.
