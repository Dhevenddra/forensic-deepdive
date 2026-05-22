# forensic-deepdive

> Five committed artifacts, not a chat. Your codebase, understood — on Day 1.

`forensic-deepdive` produces five durable markdown artifacts that give any AI coding agent (Claude Code, Cursor, Continue, Aider, Codex CLI) forensic understanding of an unfamiliar codebase:

- **`MAP.md`** — what's where, ranked by importance (Tree-sitter + PageRank).
- **`HOTPATHS.md`** — critical user-journey traces through the code.
- **`ARCHAEOLOGY.md`** — why the code looks the way it does (git history + PR/issue forensics).
- **`MENTAL_MODEL.md`** — the doc the original author *would* write to onboard a new hire.
- **`AGENT_BRIEF.md`** — ≤5kb of assertive Never/Always rules. Drop-in `CLAUDE.md` for any project.

## Status

🚧 v0.1 in active development. Target ship: weekend of May 24-25, 2026.

## Quick start (after v0.1 ships)

```bash
# install
uv tool install forensic-deepdive          # or: pipx install forensic-deepdive

# run on any repo
cd ~/some/repo
forensic extract . --output ./docs/codebase/

# five artifacts appear; CLAUDE.md / AGENTS.md / .cursor/rules / .continue/rules
# are written as thin shims pointing at AGENT_BRIEF.md
```

## Why not just use [Graphify / Aider / DeepWiki / Sourcegraph]?

Different tools, different jobs.

| | forensic-deepdive | Graphify | Aider repo-map | DeepWiki | Sourcegraph |
|---|---|---|---|---|---|
| Durable committed artifacts | ✅ 5 markdown files | ✅ graph + report | ❌ ephemeral | partial | ❌ |
| AGENT_BRIEF.md (rules-shaped) | ✅ headline output | ❌ | ❌ | ❌ | ❌ |
| Git archaeology / temporal queries | ✅ plain-git default; Graphiti above threshold | ❌ | ❌ | ❌ | partial |
| Hot path tracing | ✅ first-class | ❌ | ❌ | partial | ❌ |
| Multi-modal (PDFs, videos, images) | ❌ by design | ✅ | ❌ | partial | ❌ |
| Local-only | ✅ co-equal in v0.2 | ✅ | partial | partial | ❌ |
| License | Apache-2.0 | MIT | Apache-2.0 | proprietary (open: MIT) | partial |

**Graphify gives your agent a map. We give it a rulebook. Run both.**

## Architecture

See `docs/ARCHITECTURE.md` for the full design. TL;DR: Tree-sitter parses 305 languages, NetworkX builds a symbol graph, ported Aider PageRank ranks importance, Repomix flattens for prose synthesis, plain `git log` does archaeology (below threshold) or Graphiti does it temporally (above threshold), Jinja2 templates emit the five artifacts.

## Local development

```bash
git clone https://github.com/dhevenddra/forensic-deepdive
cd forensic-deepdive
uv sync
uv run forensic --version
uv run pytest -x
```

Read `CLAUDE.md` and `DECISIONS.md` before making changes. This repo dogfoods its own pattern.

## License

Apache-2.0. See `LICENSE`.

## Acknowledgments

- **Aider** (Paul Gauthier) for the PageRank-on-Tree-sitter repo-map pattern. Algorithm ported with attribution.
- **Graphify** (safishamsi) for the confidence-tagging idea (EXTRACTED / INFERRED / AMBIGUOUS).
- **Anthropic** for the Skills format and Claude Code.
- **Astral** for `ty` and `ruff`.
- **Repomix** (yamadashy) and **yek** (bodo-run) for repo flattening.
- **Zep / getzep** for Graphiti.
