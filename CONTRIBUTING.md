# Contributing to forensic-deepdive

Thanks for your interest. This project favors **distillation over retention, codified
rules over vague summaries, and composing existing OSS over writing new tooling**. The
guidelines below keep contributions aligned with that and with the public API contract.

## Licensing of contributions

By submitting a contribution (pull request, patch, or otherwise) you agree that your
work is licensed under the **Apache License, Version 2.0** — the same license as the
project (see [`LICENSE`](LICENSE)). No separate CLA is required; the Apache-2.0
inbound-equals-outbound model applies. If you add a third-party component, record its
license and attribution in [`NOTICE`](NOTICE) (and a `DECISIONS.md` entry if it becomes
a runtime dependency).

## Development setup

Python 3.11+ with [`uv`](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/Dhevenddra/forensic-deepdive
cd forensic-deepdive
uv sync --all-extras          # installs runtime + dev (ruff/pytest) extras
uv run forensic --version     # smoke test
```

## Before you open a PR

Run the full verification gate — all four must pass:

```bash
uv run pytest -x                              # tests must be green
uv run ruff check src/ tests/                 # lint clean
uv run ruff format src/ tests/                # formatted
uv run forensic extract tests/fixtures/tiny_fixture   # produces 5 artifacts
```

And confirm the headline cap: `AGENT_BRIEF.md` must stay **≤5 KB**
(`wc -c docs/codebase/AGENT_BRIEF.md` ≤ 5120).

- **Write the test alongside (or before) the implementation.** Untested behavior won't
  be merged.
- **Goldens are byte-exact.** Emitter changes must update the fixtures under
  `tests/fixtures/expected_emit/` deliberately, never incidentally.

## Architectural rules (read before changing structure)

This repo records every non-trivial choice in `DECISIONS.md` (append-only). **Never
contradict an active decision without first writing a superseding entry** that explains
why. A few load-bearing invariants:

- **The 5-artifact contract** — `MAP` / `HOTPATHS` / `ARCHAEOLOGY` / `MENTAL_MODEL` /
  `AGENT_BRIEF`. Names, count, and order are public API. Don't break them.
- **The `Endpoint` keystone** — five cross-boundary protocols share one `Endpoint` join
  node and the protocol-blind `base.join`. A new protocol is a `KeyBuilder` + extractors
  only; it must **not** touch `trace`/emit/`serve`. If you find yourself adding a
  `protocol ==` branch to the surfacing layer, you generalized wrong.
- **Confidence tags** (`EXTRACTED` / `INFERRED` / `AMBIGUOUS`) on every emitted edge and
  rule. Trust depends on never silently guessing — surface every candidate.
- **No `aider` dependency.** The PageRank repo-map algorithm is ported, not imported.

See [`CLAUDE.md`](CLAUDE.md) → "Where to add things" for the exact files to touch for
each kind of change (new language, protocol, HTTP provider, emitter section, CLI
subcommand, skill).

## Commits and pull requests

- **Conventional commits**: `feat:`, `fix:`, `chore:`, `docs:`, `test:`.
- **Cite `file:line`** when a commit or PR references existing code.
- Keep PRs focused — one logical change per PR is far easier to review.
- Describe *why*, not just *what*; link the relevant `DEC-N` if one applies.

## Reporting bugs / requesting features

Open a [GitHub issue](https://github.com/Dhevenddra/forensic-deepdive/issues). For bugs,
include: the command you ran, the repo characteristics (language mix, size), what you
expected, and what happened. A minimal reproducing fixture is the fastest path to a fix.

## Questions

Open a discussion or issue. Substantive design conversations end up as `DECISIONS.md`
entries so the rationale is never lost.
