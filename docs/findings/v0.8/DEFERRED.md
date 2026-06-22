# v0.8 → v0.9 deferred ledger (the v0.9 PRD is written from this)

Mirrors `docs/findings/v0.7/DEFERRED.md`. Everything here is **out of scope for the v0.8.0
public release** and seeds the v0.9 PRD (written at v0.9 kickoff, per the session protocol).
v0.8 ships as an **assisted-analysis** tool — artifacts + MCP + agent onboarding — and makes no
claim beyond that. Nothing below makes a current v0.8 claim false; each is **additive**.

## 1. The interactive CLI — the headline v0.9 theme (before any GUI)

**Today (v0.8):** `forensic` is a **command-runner** (typer): `forensic extract <path>` does the
work and exits. This is the *correct, complete* shape for "analyze a repo → write 5 artifacts →
serve MCP" (cf. git / ruff / uv), and the primary consumer is an **agent** via the 9 MCP tools +
the onboarding shims. It is **not** a launched interactive app.

**v0.9 vision (owner, 2026-06-22):** a real interactive CLI — launch `forensic` (alias
`deepdive`) inside a folder and get a **persistent Deepdive shell session** where the tools and
commands are part of one interactive surface, instead of re-invoking `uv run forensic …` per
command. This is **additive on top of** the command-runner (which stays for scripting/CI/agents),
not a replacement. Build order: **interactive CLI BEFORE a GUI** (a GUI is explicitly *not* on
the horizon).

Concrete sub-features (scope the PRD around these):
- **Interactive `query` REPL** — ask the graph questions (Cypher + NL) in a loop, holding one
  open `LadybugStore`/lexical-index, without re-invoking. The biggest ergonomic win and the
  natural first step (reuses `query/nl.py` + `query/lexical.py`).
- **Textual-based TUI graph browser** — a terminal sibling of `serve --ui` (Sigma.js): browse
  Symbol/File/Endpoint nodes, filter by edge type / confidence / language, jump to `impact`/
  `context`/`flow`. Loopback-free, no browser.
- **Guided `forensic onboard` wizard** — walks a newcomer from `extract` → read `AGENT_BRIEF` →
  wire the MCP server, surfacing the `--project` gotcha and the restart-and-approve step.
- **Session shell** — the umbrella: launch `deepdive`, pick a repo (from the multi-repo
  registry / cwd), and run `extract / query / trace / impact / diagram / serve` as in-session
  commands with shared state + history. Wraps the three above.

Design constraints to carry in: keep the zero-LLM `src/` floor (DEC-009); the shell is a *view*
over the existing graph + tools, adds no new artifact and no 10th MCP tool (contract frozen);
ASCII-degrade + `--plain`/`NO_COLOR` parity as everywhere else; Windows cp1252-safe.

## 2. v0.8 precision findings (reporting-side polish)

- **Examples-only repos under-count "source files."** DEC-049 demotes `examples/`-segment files
  to `ROLE_EXAMPLE` (correct for libraries); on an examples-*only* repo (grpc-examples) the
  headline reads "3 source files" while the graph is 117 files / 94 routes. Fix is reporting:
  show the graph count alongside, or annotate "(N demoted as examples/)". See
  `grpc-examples-test.md`.
- **`<module>` qualified-name placeholder.** Module-scope route handlers/consumers render their
  name as `<module>` (the join is correct, only the display name degrades). Seen in fastapi
  consumers + the hermes-agent cross-stack rule. See `hermes-agent-test.md`.

## 3. Carryover from earlier versions

- **GATE A — end-to-end / Arm B** (DEC-087/092). Hardware-gated: needs a ≥~16 GB GPU to serve
  FC-4B-RL + a frontier main-agent endpoint (dev box is RTX 3050 4 GB). Scale Arm A to `--n 50+`
  too. This is the v0.9 head-of-line; the v0.8 release is scoped to assisted-analysis precisely
  because this is unproven.
- **DEC-093 protocol carryover** (demand-gated): gRPC Go/Java, AMQP `DROP` + Spring
  `@QueueBinding`, DRF `DefaultRouter` at real-repo scale.

## 4. Process

- **MANUAL_TEST** (`docs/v0.8/MANUAL_TEST.md`, local-only, untracked) — the owner runs it solo;
  recommended **before flipping the repo public** (PyPI publish doesn't require it). It's the
  "would a stranger find this usable + honest" check.
