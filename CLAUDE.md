# CLAUDE.md — forensic-deepdive

<!-- Read this file every session. ≤5kb hard limit. -->
<!-- Mirror in AGENTS.md (same content, kept in sync via single-source: this file). -->

## What this project is
`forensic-deepdive` produces five durable markdown artifacts giving any AI coding agent forensic understanding of an unfamiliar codebase. Distillation over retention. Codified rules over vague summaries. Composable tools.

Five artifacts: `MAP.md`, `HOTPATHS.md`, `ARCHAEOLOGY.md`, `MENTAL_MODEL.md`, `AGENT_BRIEF.md`. AGENT_BRIEF is headline — ≤5kb, assertive Never/Always rules.

## Stack
- Python 3.11+ (uv-managed); `typer` CLI; `tree-sitter-language-pack` (305 grammars); `networkx`; `pygithub`; `httpx`; `pydantic` v2.
- Optional extras: `graphiti-core` ≥0.28 (v0.2), `kuzu` ≥0.11 (v0.2 default backend), `mcp` (v0.2).
- License: Apache-2.0.

## Critical commands
```bash
uv sync                           # install
uv run forensic --version         # smoke test
uv run forensic extract examples/tiny_fixture
uv run pytest tests/ -x           # tests must pass before any merge
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

## Session start protocol (MANDATORY)
1. Read `CLAUDE.md` (this file).
2. Read `DECISIONS.md` — **never contradict an active decision** without writing a superseding entry first.
3. Read `PROGRESS.md` — know what's done and what's next.
4. Glance at `git log --oneline -10` to see the last 10 commits.
5. Confirm understanding in one sentence before writing any code: "Working on <next item from PROGRESS>, respecting DEC-N about <X>."

## Session end protocol (MANDATORY)
1. Append to `PROGRESS.md` under today's date: what was done, what's in flight, what's blocked.
2. If a non-trivial architectural choice was made, write a new `DECISIONS.md` entry.
3. Stage and commit with a conventional-commit message (`feat:`, `fix:`, `chore:`, `docs:`, `test:`).
4. **Never** push without explicit user instruction.

## Sacred abstractions (do not refactor casually)
- **The 5-artifact contract.** MAP / HOTPATHS / ARCHAEOLOGY / MENTAL_MODEL / AGENT_BRIEF. Names, count, and order are part of the public API.
- **AGENT_BRIEF.md ≤5kb hard cap.** Beyond this, instruction-following degrades. If it overflows, overflow into `AGENT_BRIEF_DEEP.md`.
- **PageRank port from Aider** — the algorithm, not the dependency. `src/forensic_deepdive/static/pagerank.py` must remain dependency-free of aider itself.
- **Skill descriptions are the load-bearing selector.** Three skills, three single-intent descriptions. Don't merge them.
- **Confidence tags on emitted rules** (EXTRACTED / INFERRED / AMBIGUOUS). Stolen from Graphify (MIT). Trust depends on this.

## Never
- Never push to remote without explicit user instruction.
- Never merge without all tests passing locally.
- Never bypass `DECISIONS.md` — if disagreeing with an active decision, write a superseding entry and explain.
- Never add a runtime dependency without a `DECISIONS.md` entry justifying it.
- Never let AGENT_BRIEF.md exceed 5kb.
- Never depend on `aider` as a package. Port what we need.
- Never commit `.forensic-deepdive/cache/` or `graphify-out/` (already in `.gitignore`).
- Never break the artifact-file-name contract.

## Always
- Always run `uv run pytest -x` before claiming a feature is done.
- Always write the test alongside (or before) the implementation.
- Always append to `PROGRESS.md` at session end.
- Always cite file:line in PR descriptions and commits when referencing existing code.
- Always prefer composing existing OSS over writing new tooling.

## Where to add things
| Adding... | Touch... |
|---|---|
| New language support | `src/forensic_deepdive/static/tags.py` (add tags.scm) + `tests/fixtures/<lang>_sample/` + test in `tests/test_parse.py` |
| New emitter section | `src/forensic_deepdive/emit/<artifact>_md.py` + golden-file fixture in `tests/fixtures/expected_emit/` |
| New CLI subcommand | `src/forensic_deepdive/cli.py` + `tests/test_cli.py` |
| New skill | `.claude/skills/<name>/SKILL.md` + add to `docs/SKILLS.md` index |
| New decision | `DECISIONS.md` (append-only, never edit historical) |
| New real-repo findings | `docs/findings/v<X.Y>/<repo>-test.md` (one folder per release; see `docs/findings/README.md`) |
| New real-repo examples | `examples/<repo>/` (the 5 emitted artifacts; updated alongside the findings doc) |

## Coupling rules ("if you touch X, also touch Y")
- Change the artifact-name contract → update the SKILL.md files for all three skills.
- Change `RepoMap` algorithm → update `DECISIONS.md` with rationale.
- Add a new artifact → update `cli.py`, all three SKILL.md files, README, and `examples/omi/` outputs.

## Verification (never stop at "it compiles")
1. `uv run pytest -x` passes.
2. `uv run ruff check` clean.
3. `uv run forensic extract tests/fixtures/tiny_fixture` produces 5 files in `docs/codebase/`.
4. `wc -c docs/codebase/AGENT_BRIEF.md` returns ≤5120.

## When this file goes stale
Bump `pyproject.toml`; update relevant sections; commit.
