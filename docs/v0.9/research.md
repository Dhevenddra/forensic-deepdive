# research — forensic-deepdive v0.9 · technical grounding (deliberately lean)

> The third leg of the triad. Unlike the v0.8 research (FastContext/PyPI/MCP — large external
> unknowns), v0.9 is a **completion release built on existing internals** (`query/nl.py`,
> `query/lexical.py`, the `LadybugStore`, the 9 MCP tools). It is a *view* over things that already
> work. So this doc is short by design: it grounds the **one genuinely load-bearing fork** (the
> REPL/TUI library choice), records the constraints that fork drags in, and states the deferral
> status of the hardware-gated items. No extended research task was run, and none was needed.

---

## §1 — The one load-bearing decision: the REPL/TUI library stack

The v0.9 headline (owner note, DEFERRED §1) is the **interactive CLI**: a query REPL, a Textual TUI
graph browser, an `onboard` wizard, and a session shell that wraps them. The single expensive-to-
reverse choice is which terminal-UI libraries carry it. The landscape (verified current, mid-2026):

| Library | Best at | Verdict for v0.9 |
|---|---|---|
| **prompt_toolkit** | line editing — history, multiline, completion, key bindings. Powers **IPython** and **pgcli**. | **USE for the query REPL + the session-shell command loop.** This is the "mostly line-editing" case exactly. |
| **Textual** | full-screen interactive apps — widgets, layout, reactive state, mouse, async. The default pick for a *new* interactive project. MIT. Runs macOS/Linux/Windows, over SSH. | **USE for the TUI graph browser** (`browse`) — the terminal sibling of `serve --ui`. |
| click-repl | bolting a REPL onto a Click/Typer app | Rejected — too thin; we want a held-open store + NL/Cypher loop, not just command replay. |
| urwid | veteran full-screen TUI | Rejected — Textual supersedes it for a greenfield build. |
| blessed | terminal primitives only | Rejected — we'd rebuild the widget layer. |

**Decision.** `prompt_toolkit` for the REPL and the shell command loop; `Textual` for the full-screen
graph browser. Both MIT → clean against Apache-2.0.

**The interop caveat that shapes the architecture (DEC-099).** prompt_toolkit and Textual each want to
**own the terminal**. Do **not** try to render a Textual full-screen app *inside* a running
prompt_toolkit prompt. The session shell **dispatches**: it runs the prompt_toolkit REPL for the
command/query loop, and when the user asks for the browser it **suspends the REPL, launches the
Textual `App` as a distinct full-screen mode, and returns to the REPL on exit** (`App.run()` is
blocking and reclaims the terminal cleanly). Same pattern IPython uses to shell out. Design each of
`repl` / `browse` / `onboard` as an independently-runnable command first; the shell is the last step
and only *orchestrates* them — it does not re-implement them.

**Packaging (recommend an `[interactive]` extra).** prompt_toolkit and Textual are heavier than the
agent-first core needs. The primary consumer is an **agent** via `extract` + `serve` + the shims —
that path should stay dependency-lean. So gate the interactive layer behind a
`[project.optional-dependencies] interactive = ["prompt_toolkit>=3", "textual>=0.80"]` extra
(mirroring the existing `graphiti`/`semantic`/`openapi` pattern). `forensic repl`/`browse`/`deepdive`
without the extra should fail with a **precise, friendly** message: *"Interactive mode needs the
`interactive` extra: `pip install forensic-deepdive[interactive]` (or `uv tool install
forensic-deepdive[interactive]`)."* Both deps still need their own `DECISIONS.md` entries (the
"never add a runtime dependency without a DEC" rule applies even to extras).

---

## §2 — Constraints the fork drags in (carry, do not rediscover)

- **Windows / cp1252 + terminal glyphs.** Textual's own maintainer documents that multi-codepoint /
  newer-emoji glyphs render unpredictably across terminals. This is the **same** hazard the DEC-078/080
  ASCII-degrade rule already governs. Carry it verbatim into the interactive layer: `--plain` /
  `NO_COLOR` parity, ASCII fallback for confidence glyphs (`[E]/[I]/[A]`), and stick to safe box/pipe
  characters. Textual runs on Windows, but the cp1252 console is the risk surface — the interactive
  commands must degrade exactly as the styled CLI does.
- **The zero-LLM `src/` floor (DEC-009).** The shell is a *view* over the existing graph + tools. No
  LLM enters any interactive path. NL queries route through the existing lexical/structural
  `query/nl.py` (post-DEC-084), never a model call.
- **The frozen contract.** No new artifact. **No 10th MCP tool.** The REPL/browser/shell surface the
  *existing* 9 tools and the query paths; they add zero to the public tool/artifact contract.

---

## §3 — The persistent-session capability (the actual new thing)

Everything human-facing today re-invokes `uv run forensic …` per command, re-opening the store each
time. The one genuinely new capability in v0.9 is **holding a single `LadybugStore` + lexical index
open across a session** so the REPL/shell answers successive questions without re-load. Establish this
in the REPL step (DEC-096): open on session start, reuse across the loop, close cleanly on exit
(context-manager / explicit teardown; handle Ctrl-C and Ctrl-D). The shell (DEC-099) reuses the same
open-store pattern across `extract`/`query`/`trace`/`impact`/`diagram`. This lifecycle is the load-
bearing implementation detail — get it right once in DEC-096 and the rest compose on it.

---

## §4 — Deferral status (tracked, not planned into the build)

- **FastContext GATE A — Arm B (end-to-end resolution).** Hardware-gated: serving FC-4B-RL + a
  frontier main-agent endpoint needs a ≥~16 GB GPU; the dev box is an RTX 3050 4 GB. **Deferred until a
  capable device is in hand** (owner-confirmed). Reserved as the head-of-line item the moment hardware
  exists; a DEC will be written then. Also scale **Arm A** (seeded localization, which *is* reachable)
  to `--n 50+` when convenient — that can happen on CPU/small-GPU and would strengthen the
  assisted-analysis story without Arm B.
- **DEC-093 protocol carryover** (gRPC Go/Java, AMQP `DROP` + Spring `@QueueBinding`, DRF
  `DefaultRouter` at scale) stays **demand-gated** — pull an item only when a real target repo needs
  it, never speculatively (the non-goal from v0.8).

---

## §5 — What was deliberately *not* researched (and why it was fine to skip)

- **prompt_toolkit / Textual internals** — mature, stable, widely-deployed (IPython, pgcli, k9s-class
  tools); the architectural guidance above is stable knowledge, confirmed current by a mid-2026 source.
- **A NL/graph-query engine** — already built (`query/nl.py` + `query/lexical.py`, hardened in
  DEC-084). The REPL *calls* it.
- **Anything FastContext / packaging / MCP-distribution** — resolved in the v0.8 research; the package
  is shipping. v0.9 adds no new distribution surface (the interactive extra rides the existing wheel).

*If a genuinely new external unknown appears mid-build (it shouldn't), stop and spike it — but the
plan does not assume one exists.*
