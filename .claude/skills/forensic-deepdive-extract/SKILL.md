---
name: forensic-deepdive-extract
description: Run a full forensic deep-dive on an unfamiliar codebase, producing five durable markdown artifacts (MAP.md, HOTPATHS.md, ARCHAEOLOGY.md, MENTAL_MODEL.md, AGENT_BRIEF.md). Use when the user says "analyze this repo", "onboard me to X", "I just joined a new team", "deep-dive this codebase", or clones/opens a repo they haven't worked in before. Do NOT use if the repo already has fresh artifacts under docs/codebase/ less than 7 days old — use forensic-deepdive-query instead.
---

# Forensic Deep-Dive — Extract

Runs the full extraction pipeline once per new codebase. Produces five markdown artifacts in `docs/codebase/`.

## When to use
- First time analyzing this codebase.
- Repo has no `docs/codebase/` directory.
- Existing artifacts are >7 days old AND >100 commits behind HEAD.

## When NOT to use
- Artifacts exist and are <7 days old → use `forensic-deepdive-query`.
- Only some files changed since last run → use `forensic-deepdive-update`.
- User is asking about a single file or function → just read it.

## How to run

1. Verify CLI is installed:
   ```bash
   forensic --version
   ```
   If missing: `uv tool install forensic-deepdive` or `pipx install forensic-deepdive`.

2. From the repo root:
   ```bash
   forensic extract . --output ./docs/codebase/
   ```

3. Defaults:
   - Cloud mode (uses `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`).
   - Plain `git log` archaeology (no Graphiti).
   - Repomix `--compress` for flattening.

4. Flags:
   - `--local` — use Ollama / LM Studio on localhost (v0.2).
   - `--with-graphiti` — enable temporal KG (v0.2; only if repo meets 2-of-5 threshold).
   - `--fast` — use yek instead of Repomix (v0.2).
   - `--force` — ignore cache, regenerate everything.

## Pipeline stages

| Stage | Flag | Typical time |
|---|---|---|
| Inventory | `--stage=inventory` | <10s |
| Layer 1 (Tree-sitter + PageRank) | `--stage=static` | 30s–5min |
| Layer 2 (Repomix --compress) | `--stage=flatten` | 10s–2min |
| Layer 3 (plain-git / Graphiti) | `--stage=history` | 30s plain / 5-15min Graphiti |
| Layer 4 (emit 5 artifacts) | `--stage=emit` | 10–60s |

Earlier stages cache to `.forensic-deepdive/cache/`.

## What to report back to the user

After the run completes:

1. **Five-bullet summary**: "Top entry points are X, Y, Z. Hot paths are A, B. The repo's hidden weight-bearing abstraction is C."
2. **Cost report**: read `.forensic-deepdive/last_run.json` and report actual token cost.
3. **Three suggested first-tasks** based on ARCHAEOLOGY.md (e.g., "PR #1234 was reverted; underlying bug may still exist in module M").
4. **Exact paths** of the five artifacts.
5. **Shim status**: confirm `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/codebase.mdc`, `.continue/rules/codebase.md` were written.

## Non-Claude harness fallback

If the user's harness is Codex CLI / Cursor / Continue / Aider:
- Tell them to run `forensic extract . --output ./docs/codebase/` in their shell.
- Every harness can drive a CLI. Do not assume MCP tools are available.

## Pitfalls

- ❌ Don't regenerate MENTAL_MODEL.md more than once a week without `--force`. New hires depend on its stability.
- ❌ Don't commit `.forensic-deepdive/cache/` (already in `.gitignore` template).
- ❌ Don't run on a repo with uncommitted changes you care about — tool only reads, but `--with-graphiti` may spin up Docker.
- ❌ Don't assume the AGENT_BRIEF.md ≤5kb cap is "guidance" — it's enforced in CI.
