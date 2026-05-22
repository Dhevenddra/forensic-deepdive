# AGENTS.md

This file mirrors `CLAUDE.md`. Single source of truth lives in `CLAUDE.md`; this file is provided for cross-tool compatibility (Codex CLI, Cursor, Continue, Aider, Factory Droid, Gemini CLI, GitHub Copilot CLI, Jules, VS Code) since the Linux Foundation's Agentic AI Foundation (December 2025) standardized on `AGENTS.md`.

**Read both this file and `CLAUDE.md`. If they ever drift, `CLAUDE.md` wins.**

## Cross-edit obligation
- Change `CLAUDE.md` → also update this file in the **same commit**.
- A `scripts/sync-agents-md.sh` script (added in v0.2) will enforce this with a pre-commit hook.

## Mandatory reading order at session start
1. `CLAUDE.md` — operating manual
2. `DECISIONS.md` — architectural decisions you cannot violate
3. `PROGRESS.md` — current state and next steps
4. `git log --oneline -10`

## Mandatory action at session end
1. Append a dated entry to `PROGRESS.md`.
2. If a non-trivial decision was made, append a `DEC-NNN` entry to `DECISIONS.md`.
3. Conventional-commit message (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).
4. Never push without explicit user instruction.

---

(For the full operating manual, see `CLAUDE.md`.)
