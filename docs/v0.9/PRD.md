# PRD — forensic-deepdive v0.9 · build specification

> Binding spec for the build sequence in `KICKOFF.md §5`. Each step = one focused session → one DEC.
> Every step states: **Goal · Keystone guard · Touch · Approach · Acceptance · Tests · Done-gate.**
> "Touch" lists the only files a step should change — a diff outside it is a smell. Grounded in
> `DECISIONS.md` (through DEC-094), the v0.8 findings (`docs/findings/v0.8/`), and `research.md`.

**Conventions.** "Byte-identical goldens" = the 5 artifact golden fixtures are unchanged unless the
step is DEC-100/101 (which re-baseline once at GATE B). The interactive layer (DEC-096–099, DEC-102)
emits **no** artifacts, so it is byte-identical trivially. All paths under `src/forensic_deepdive/`
unless noted.

---

## Track B — Reporting-precision fixes (warm-ups; do first)

Two v0.8 acceptance findings, both **reporting/display only** — the underlying analysis is already
correct. Small, high-clarity, and they're the only steps that touch emitted artifact content, so land
them first and re-baseline the goldens once at GATE B before the interactive work begins.

### DEC-100 — examples-only source-count clarity
- **Goal.** On an examples-*only* repo, the headline reads "Source files: 3" while the graph is 117
  files / 94 routes — because DEC-049 demotes `examples/`-segment files to `ROLE_EXAMPLE` (correct for
  a library shipping demos, misleading when `examples/` *is* the repo). Make the headline
  un-misreadable **without changing the classification** (`grpc-examples-test.md`; v0.8 DEFERRED §2).
- **Keystone guard.** **Do NOT touch `inventory.py::_EXAMPLE_SEGMENTS` / DEC-049 classification** — it
  is correct. This is a *reporting* change only. Confidence taxonomy + graph untouched.
- **Touch.** the extract-summary renderer (`cli/style/render.py`) + `emit/map_md.py` (the "Source
  files" line); `tests/`. Possibly a small read-only helper to count in-graph files vs counted-source.
- **Approach.** When demoted files exist, annotate the count: `Source files: 3  (+114 in graph,
  demoted as examples/)` or `3 source / 117 in graph`. Pick one wording, apply it in **both** the CLI
  summary and MAP.md consistently. When there are zero demotions, the line is unchanged (so most repos'
  goldens don't move).
- **Acceptance.** On the grpc-examples fixture (or a distilled examples-only fixture), the headline
  shows both numbers and names the demotion reason; on a normal repo (no demotions) the line is
  byte-identical to today.
- **Tests.** Examples-only fixture asserts the annotated line; a no-demotion fixture asserts the line
  is unchanged.
- **Done-gate.** Suite green; ruff clean. (Golden re-baseline handled at GATE B.)

### DEC-101 — `<module>` qualified-name display resolution
- **Goal.** Module-scope route handlers/consumers render their name as the literal `<module>` (e.g.
  `"_send_whatsapp calls backend <module> over http::POST::/send"`, and fastapi module-level call
  sites). The **join is correct**; only the *display name* of a module-scope symbol degrades
  (`hermes-agent-test.md`, `precision-revalidation.md`; v0.8 DEFERRED §2).
- **Keystone guard.** No edge/join change — the ROUTES_TO/HANDLES edges are already right. Display-name
  only. Determinism preserved (goldens). No new node type.
- **Touch.** the qualified-name/display-name derivation for module-scope symbols (likely in the
  symbol-naming path used by `emit/*` + the route/trace rendering); `tests/`.
- **Approach.** Resolve a module-scope symbol to a **readable, deterministic** name instead of
  `<module>` — the decision (KICKOFF §8 Q4) is the module dotted-path vs file stem vs `module:<file>`;
  pick one and apply it **consistently** across routes, AGENT_BRIEF rules, and `trace` output. It must
  be stable across runs (goldens) and cp1252-safe.
- **Acceptance.** The hermes-agent-class fixture renders a real module name in the cross-stack rule
  instead of `<module>`; fastapi module-level consumers likewise; the same name appears identically in
  routes, AGENT_BRIEF, and trace.
- **Tests.** A module-scope-symbol fixture asserts the resolved name in all three surfaces + across two
  runs (determinism).
- **Done-gate.** Suite green; ruff clean. **▸ GATE B:** DEC-100/101 change emitted content — re-baseline
  the 5 goldens **once**, diff documented in both DECs, then freeze. `wc -c AGENT_BRIEF.md` ≤ 5120.

---

## Track A — The interactive CLI (the headline)

All four steps are **additive** and live behind the `[interactive]` extra. They are **views** over the
existing graph + 9 tools + query paths — **zero** new artifact, **zero** new MCP tool, **no LLM**.
Build standalone-first (REPL → browser → wizard), then the shell wraps them.

### DEC-096 — interactive query REPL (`forensic repl`)
- **Goal.** The biggest ergonomic win and the natural first step: ask the graph questions (Cypher + NL)
  in a loop over **one open store**, instead of re-invoking `uv run forensic …` per question. Also
  establishes the **persistent-open-store lifecycle** the shell reuses (research §3).
- **Keystone guard.** Zero-LLM floor (NL routes through `query/nl.py`, DEC-084 — never a model);
  contract frozen (no new MCP tool); cp1252/`--plain`/`NO_COLOR` parity (DEC-078/080). New runtime dep
  (`prompt_toolkit`) → its own DEC entry + `[interactive]` extra.
- **Touch.** NEW `cli/interactive/repl.py`; `cli/app.py` (register `forensic repl`); `pyproject.toml`
  (`[interactive]` extra + `prompt_toolkit` dep); `tests/test_interactive.py`. Reuse `query/nl.py` +
  `query/lexical.py` + the `LadybugStore` (no changes to them).
- **Approach.** Open the `LadybugStore` + lexical index **once** on entry; loop with a prompt_toolkit
  `PromptSession` (history file under `~/.deepdive/`, tab-completion of symbol/command names,
  confidence-styled results via the existing render helpers). **Command grammar (KICKOFF §8 Q2):** a
  prefix scheme (e.g. `:cypher …` for raw Cypher, bare text → NL) or a documented mode toggle — pick
  the least surprising, document it in `--help` and the README. Clean teardown on Ctrl-C (cancel
  current) / Ctrl-D (exit) — close the store in a `finally`. Missing extra → the precise install
  message (research §1). Non-TTY / piped → refuse gracefully (a REPL needs a TTY) or fall back to
  reading one query from stdin; do not hang.
- **Acceptance.** `forensic repl --repo <r>` opens a session, answers successive Cypher + NL queries
  against one held-open store, shows confidence styling on a TTY and `[E]/[I]/[A]` under `--plain`,
  and exits cleanly; without the extra it prints the actionable install line and exits non-zero.
- **Tests.** prompt_toolkit testing utilities (feed scripted input, assert output) for: NL query
  routes through `query/nl.py`; Cypher path returns rows; the store is opened once (not per query);
  `--plain` degrade; clean exit. Import-safety without the extra (the module imports; invocation errors
  with the message).
- **Done-gate.** Suite green; ruff clean; goldens byte-identical (no artifact emission).

### DEC-097 — Textual TUI graph browser (`forensic browse`)
- **Goal.** A full-screen terminal graph browser — the loopback-free sibling of `serve --ui` (Sigma.js)
  — to explore Symbol/File/Endpoint nodes, filter, and jump into `impact`/`context`/`flow` without a
  browser or a server.
- **Keystone guard.** Zero-LLM; contract frozen (surfaces existing tools, no new one); cp1252/glyph
  discipline (Textual runs on Windows but the cp1252 console is the risk surface — safe glyphs, ASCII
  fallback, honor `--plain`/`NO_COLOR`). New runtime dep (`textual`) → its own DEC + the `[interactive]`
  extra. **Do not nest** with prompt_toolkit — `browse` is launched blocking, standalone.
- **Touch.** NEW `cli/interactive/browser.py` (the Textual `App` + widgets); `cli/app.py` (register
  `forensic browse`); `pyproject.toml` (`textual` in `[interactive]`); `tests/test_interactive.py`
  (Textual `run_test()` + `Pilot`).
- **Approach.** A Textual `App` reading the existing graph (read-only): a node list/tree (Symbol / File
  / Endpoint) with filters by **edge type / confidence / language**; selecting a node shows its
  `context()`; key-bindings to jump to `impact`/`flow` output for the selection. **Bound the node set**
  (KICKOFF §8 Q3) with the DEC-039 node-cap + summarize-and-truncate so omi (18k edges) doesn't choke
  the widget — never silent-drop; show "showing N of M". **Read-only in v0.9** (defer any in-TUI
  mutation). Confidence encoded not-by-colour-alone (glyph + style), consistent with the taxonomy.
- **Acceptance.** `forensic browse --repo <r>` opens a full-screen browser on a real graph; filters
  work; selecting a node shows context and can jump to impact/flow; a huge graph is bounded with a
  visible truncation note; quits cleanly and restores the terminal; missing extra → the install line.
- **Tests.** Textual `App.run_test()` + `Pilot`: app boots on a fixture graph; a filter narrows the
  list; a selection renders context; the node-cap engages on an oversized fixture with the truncation
  note; teardown restores the terminal. Import-safety without the extra.
- **Done-gate.** Suite green; ruff clean; goldens byte-identical.

### DEC-098 — guided `forensic onboard` wizard
- **Goal.** A linear guided flow that walks a newcomer from nothing to a wired MCP server: `extract` →
  read `AGENT_BRIEF` → wire the MCP server — surfacing the exact gotchas the manual-test history
  recorded (the `--project`/`--repo` gotcha, the restart-and-approve step).
- **Keystone guard.** Zero-LLM; contract frozen (orchestrates existing commands); cp1252/`--plain`
  parity. Reuse the DEC-102 `mcp-config` output (one source of truth for the snippet) — don't
  re-hardcode the config.
- **Touch.** NEW `cli/interactive/onboard.py`; `cli/app.py` (register `forensic onboard`);
  `tests/test_interactive.py`. Reuse the existing `extract` path + the `mcp-config` renderer.
- **Approach.** A prompt_toolkit-driven linear wizard: confirm the repo → run `extract` (show the
  summary) → point at `AGENT_BRIEF.md` and the 5 artifacts → detect the client (or ask) and print the
  **correct** `mcp-config` snippet (dev form pre-publish via `--dev`, uvx form post-publish) →
  explicitly state the restart-and-approve step. Idempotent + re-runnable; every prompt has a sane
  default; fully scriptable/non-interactive via flags for CI (`--yes`/defaults) so it's testable.
- **Acceptance.** `forensic onboard --repo <r>` (with `--yes`/defaults) runs extract, reports the
  artifacts, and prints a valid client config + the restart-and-approve note; re-running is safe;
  missing extra → the install line.
- **Tests.** Scripted/non-interactive run asserts: extract invoked, artifacts reported, a valid
  `mcp-config` snippet emitted (matches DEC-102's output), restart note present, idempotent re-run.
- **Done-gate.** Suite green; ruff clean; goldens byte-identical.

### DEC-099 — session shell (`deepdive`)
- **Goal.** The umbrella: launch `deepdive` inside a repo (or pick from the multi-repo registry) and
  run `extract`/`query`/`trace`/`impact`/`diagram`/`serve` as **in-session commands with shared state +
  history over one open store** — wrapping the REPL, the browser, and the wizard into one surface.
- **Keystone guard.** Zero-LLM; contract frozen (no new tool/artifact); cp1252/`--plain` parity.
  **prompt_toolkit ↔ Textual must not nest (research §1):** the shell runs a prompt_toolkit command
  loop and **dispatches** `browse` by suspending the loop, launching the Textual `App` blocking, and
  returning on exit. Reuses the DEC-096 open-store lifecycle; **does not re-implement** the REPL /
  browser / wizard — it orchestrates them.
- **Touch.** NEW `cli/interactive/shell.py` (the umbrella loop + dispatch); `cli/app.py` +
  `pyproject.toml` (a `deepdive` `[project.scripts]` entry point — KICKOFF §8 Q6);
  `tests/test_interactive.py`. Imports `repl.py`/`browser.py`/`onboard.py` — no duplication.
- **Approach.** Launch → resolve the repo (cwd, `--repo`, or a picker over the registry) → open the
  store once → a prompt_toolkit loop dispatching in-session commands to the **existing** command
  implementations, sharing the open store + a shared history. `browse` → suspend/run/return (never
  nested). `extract` inside a live session → **invalidate + reopen the store cleanly** (KICKOFF §8 Q5;
  define and test this transition). `serve` from the shell → the usual stdio MCP server. Exit closes
  the store in a `finally`.
- **Acceptance.** `deepdive` (or `deepdive --repo <r>`) opens a session; in-session `query`/`trace`/
  `impact`/`diagram` all run against one held-open store; `browse` launches the TUI and returns to the
  prompt; an in-session `extract` reopens the store without a stale handle; exit is clean; missing
  extra → the install line; `--plain` parity holds.
- **Tests.** Scripted session: multiple commands against one store (store opened once), the
  extract→reopen transition, the browse suspend/return path (via the Textual test harness stub),
  clean teardown. The `deepdive` entry point imports and launches.
- **Done-gate.** Suite green; ruff clean; goldens byte-identical.

---

## Track C — Cosmetic ergonomics

### DEC-102 — `mcp-config --dev` + `list --prune`
- **Goal.** Two v0.8-usability-review cosmetics. (1) `mcp-config` emits the post-publish `uvx` form,
  which a **pre-publish / from-source** user can't launch; add `--dev` for the
  `uv run --project <dir> forensic serve --repo …` form. (2) `list` accumulates stale registry entries
  (temp/smoke paths from prior runs); add `--prune` to drop entries whose `graph.lbug` no longer
  exists. (`cli-usability-review.md` notes 2 & 3.)
- **Keystone guard.** CLI-surface only; engine/graph/contract untouched; cp1252/`--plain` parity. The
  `mcp-config` output stays the **single source of truth** the `onboard` wizard (DEC-098) reuses.
- **Touch.** `cli/app.py` (`mcp-config --dev` branch; `list --prune` flag); the registry reader
  (`~/.deepdive/registry.json`, DEC-018) for the prune predicate; `tests/test_cli.py`.
- **Approach.** `--dev` selects the `uv run --project` command shape (correct for from-source users)
  vs the default `uvx` shape (correct post-publish); document both in `docs/install.md`. `--prune`
  removes registry entries whose `graph.lbug` path is gone; default `list` is unchanged (prune is
  opt-in, non-destructive by default). Print what was pruned.
- **Acceptance.** `mcp-config --dev` emits a launchable from-source snippet; `list --prune` removes
  only dead entries and reports them; bare `list` is unchanged.
- **Tests.** `--dev` snippet shape asserted; prune removes a fixture dead entry and keeps a live one;
  bare-`list` output unchanged.
- **Done-gate.** Suite green; ruff clean; goldens byte-identical.

---

## Track D — Deferred (NOT built this cycle; documented for continuity)

### DEC-103 — protocol carryover (demand-gated)
- **Status.** **Not scheduled.** Pull an item only when a real target repo needs it (the v0.8 non-goal:
  no protocol without real-repo demand).
- **Keystone guard (when pulled).** **Reuse the `Endpoint` node; a new protocol = a `KeyBuilder` +
  provider/consumer extractors only — never touch `trace`/emit/`serve`** (DEC-043/055). No new node
  type. Fixture-proven + real-repo-validated with confidence tags, or honestly re-deferred with the
  finding recorded under `docs/findings/v0.9/`.
- **Items.** gRPC **Go/Java** servicer/stub shapes + the `/<package>.<Service>/<Method>` wire-path
  equivalence (attribute-bound stubs; the deferred `[proto]` extra) — note gRPC **Python** already
  works (grpc-examples: 94 ROUTES_TO). AMQP **DROP** co-located pair + Spring **`@RabbitListener` /
  `@QueueBinding`**. DRF **`DefaultRouter`/`SimpleRouter` at real-repo scale**. (DEC-093.)

### (reserved) GATE A Arm B — hardware-gated
- **Status.** **Not scheduled — hardware-blocked.** Serving FC-4B-RL end-to-end + a frontier main-agent
  endpoint needs a ≥~16 GB GPU; the dev box is an RTX 3050 4 GB. A DEC is written the moment a capable
  device is in hand; until then this is the reserved head-of-line item.
- **When unblocked.** Run Arm B (end-to-end resolution with a main agent) on the SWE-bench subset from
  DEC-087; scale **Arm A** (seeded localization — reachable on modest hardware) to `--n 50+` in the
  meantime to strengthen the assisted-analysis evidence. The keystone from DEC-087 holds absolutely:
  **the LLM lives in `experiments/`, never in `src/`.**

---

## Appendix — v0.8 finding → v0.9 DEC mapping (traceability)

| v0.8 finding / ledger item | Addressed by |
|---|---|
| DEFERRED §1 — interactive CLI (REPL / TUI / onboard / shell) | **DEC-096–099** (the headline) |
| DEFERRED §2 — examples-only "3 source files" undercount (grpc-examples) | DEC-100 |
| DEFERRED §2 — `<module>` qualified-name placeholder (hermes-agent, fastapi) | DEC-101 |
| usability-review note 2 — `mcp-config` pre-publish form | DEC-102 (`--dev`) |
| usability-review note 3 — `list` stale registry clutter | DEC-102 (`--prune`) |
| usability-review note 1 — `graph --central` hollow diagram | already fixed in v0.8 (regression-guarded) — no v0.9 action |
| DEFERRED §3 — DEC-093 protocol carryover | DEC-103 (demand-gated, not scheduled) |
| DEFERRED §3 — GATE A Arm B + Arm A `--n 50+` | (reserved; hardware-gated) |
| DEFERRED §4 — MANUAL_TEST before flipping public | run pre-release (KICKOFF §9), owner-solo |

*No new external unknowns in v0.9 — every step is a view over existing internals or a reporting-side
clarification. The one library fork (prompt_toolkit for the REPL, Textual for the browser, never
nested; both MIT; behind an `[interactive]` extra) is settled in `research.md §1`.*
