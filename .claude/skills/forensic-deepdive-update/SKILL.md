---
name: forensic-deepdive-update
description: Incrementally refresh forensic-deepdive artifacts after the codebase has changed. Use when MAP.md or HOTPATHS.md is stale (>7 days or >50 commits old), or after a significant refactor when the user wants artifacts to reflect reality. Do NOT use for first-time analysis (use forensic-deepdive-extract) or simple lookups (use forensic-deepdive-query).
---

# Forensic Deep-Dive — Update

Incrementally refresh artifacts. In v0.1 this is a stub that calls `forensic extract --force` (full re-run). In v0.2 it becomes truly incremental.

## When to use
- Artifacts >7 days old AND >50 commits behind HEAD.
- User explicitly asks to refresh.
- Major refactor just landed.

## When NOT to use
- First time on this repo → use `forensic-deepdive-extract`.
- Just answering a question → use `forensic-deepdive-query`.
- Artifacts are fresh (<7 days, <50 commits behind) → no refresh needed.

## How to run

```bash
forensic update . --since=last-extract
```

This (in v0.2):
1. Reads `.forensic-deepdive/cache/last_run.json` for previous commit SHA.
2. Computes changed files via `git diff --name-only <sha>..HEAD`.
3. Re-parses only changed files (Tree-sitter), incrementally updates the symbol graph.
4. Re-runs PageRank (under 1s for 100k symbols).
5. Per-artifact staleness:
   - **MAP.md** if any top-50 PageRank node changed.
   - **HOTPATHS.md** if any active ast-grep query's match-set changed.
   - **ARCHAEOLOGY.md** appends new commits/PRs/issues since last run.
   - **MENTAL_MODEL.md** skipped unless `--force` or ≥20% symbol churn.
   - **AGENT_BRIEF.md** regen if dependency manifest, CI workflow, or top-10 file changed.
6. Updates the `<!-- generated -->` header on each touched artifact.

In v0.1, this calls `forensic extract --force` (full re-run). Document the limitation.

## Caveats
- Major directory restructure → prefer full `forensic extract --force`.
- New subsystem merged → use `--force-mental-model` to refresh that one artifact.

## What to report back
- Which artifacts were refreshed and which were skipped (with reason).
- Diff summary if non-trivial: "MAP.md added 3 new top-50 nodes: A, B, C."
- Cost report from `.forensic-deepdive/last_run.json`.
