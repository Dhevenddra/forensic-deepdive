---
name: codebase-debugging
description: Find the right place to look when something is broken. Use when the user reports an error, regression, crash, flaky test, or unexpected behavior and says "why is X broken", "trace this failure", "where does this exception come from", "what changed that could cause this". Reads docs/codebase/HOTPATHS.md (dependency hot spots, churn × centrality) and docs/codebase/ARCHAEOLOGY.md (recent commits, defect proximity). Do NOT use for greenfield design or pure orientation — use codebase-exploring.
---

# Codebase debugging

Triangulate a bug to its likely region without re-reading the whole repo.

## When to use
- User reports an error / regression / flake / unexpected output.
- Question shape: 'why is X broken', 'where does this exception originate', 'what changed that could cause this', 'this used to work'.

## When NOT to use
- User is orienting / learning, not fixing → `codebase-exploring`.
- User is planning a refactor → `codebase-refactoring`.
- Question is about correctness of a single function → just read it.

## How to answer

1. **Always read `docs/codebase/AGENT_BRIEF.md` first** — the never/always rules often pin the load-bearing call site.
2. Match the question shape:

| Question shape | Artifact |
|---|---|
| 'What are the hot spots / where is most activity' | `docs/codebase/HOTPATHS.md` (Dependency hot spots) |
| 'What changed recently around X' | `docs/codebase/ARCHAEOLOGY.md` (Recent commits, churn) |
| 'What's the defect-proximity neighborhood' | `docs/codebase/ARCHAEOLOGY.md` |
| 'What co-changes with this file' | `docs/codebase/HOTPATHS.md` (Co-change clusters) |

3. If `forensic serve` is running, call `archaeology(file_or_symbol)` for the full git-history view in one call — recent commits, dominant author, defect proximity, co-change cluster.

## Citation rule
Cite `docs/codebase/HOTPATHS.md:42` or `docs/codebase/ARCHAEOLOGY.md:78`. If a graph-mode HOTPATHS shows AMBIGUOUS-confidence edges around the suspect symbol, surface that — agents and humans both need to know the resolver wasn't sure.
