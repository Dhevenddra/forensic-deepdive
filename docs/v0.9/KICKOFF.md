# KICKOFF — forensic-deepdive v0.9 · "The Interactive CLI" (completion release)

> Companion docs: `PRD.md` (per-step build spec + acceptance gates) and `research.md` (the one
> load-bearing REPL/TUI decision + constraints + deferral status). **Read all three, then
> `CLAUDE.md` → `DECISIONS.md` → `PROGRESS.md` per the session-start protocol** before any code.
> v0.9 DEC range: **DEC-095 … DEC-103** (+ a reserved slot for GATE A Arm B when hardware arrives).

---

## §0 — The framing: this is a *completion* release, not an exploration one

v0.8 shipped honestly as an **assisted-analysis** tool: the precision work held up on real code
(superset — 62 routes, **0 AMBIGUOUS**; the tier fires only on genuine ambiguity), `ARCHITECTURE.md`
and the Obsidian vault landed as separate surfaces with the 5-artifact contract intact, and it went
to PyPI making **no autonomous-execution claim**. The one thing v0.8 could not do — the FastContext
end-to-end proof (GATE A Arm B) — was **hardware-blocked, not failed**, and is deferred to real GPU.

So v0.9 does not chase anything new. It **finishes what we started**: the interactive CLI that the
v0.8 DEFERRED ledger names as the headline v0.9 theme (owner note, 2026-06-22), plus the two
reporting-precision findings and the cosmetic ergonomics that the v0.8 acceptance run surfaced.
Discipline first: no new protocol, no new artifact, no 10th MCP tool, no LLM in `src/`.

---

## §1 — The verdict (scope, one paragraph)

v0.9 turns `forensic` from a **command-runner** (correct and complete for the agent-first path —
`extract` → 5 artifacts → `serve` MCP, exits) into *also* an **interactive surface** for humans: a
persistent Deepdive session you launch inside a repo and drive without re-invoking `uv run forensic …`
per command. Built in four additive steps — an interactive **query REPL** (the biggest ergonomic win,
holds one open store), a **Textual TUI graph browser** (terminal sibling of `serve --ui`), a guided
**`onboard` wizard**, and the **session shell** that wraps all three — on `prompt_toolkit` (REPL) +
`Textual` (TUI), behind an `[interactive]` extra so the agent install stays lean. Alongside it, two
**reporting-side precision fixes** (the examples-only "3 source files" undercount; the `<module>`
display-name placeholder) and two **cosmetic ergonomics** (`mcp-config --dev`, `list --prune`). The
interactive layer is a **view** over the existing graph + 9 tools — it adds nothing to the frozen
contract. FastContext Arm B and the demand-gated protocol carryover stay deferred.

---

## §2 — North star and the honest scope line

**North star (unchanged):** does an AI agent finish real work better because of deepdive? v0.9's
interactive CLI is primarily a **human** ergonomic — it does not itself move the autonomous-usefulness
needle (that's Arm B, hardware-gated). So the honest framing of the release: **v0.9 makes the
assisted-analysis tool pleasant to drive by hand and fixes the reporting rough edges; it makes no new
autonomous claim.** That honesty is the release's integrity, same as v0.8.

---

## §3 — Keystones and hard constraints (each an active DEC; do not breach)

1. **Zero-LLM, zero-network `src/` floor (DEC-009).** The REPL/browser/shell are **views** over the
   existing graph + tools. No model call on any interactive path; NL queries route through the
   existing `query/nl.py` (DEC-084), never an LLM.
2. **The contract is frozen.** No new artifact (the 5 + ARCHITECTURE.md as its separate surface stand).
   **No 10th MCP tool.** The interactive commands *surface* the existing 9 tools + the query paths —
   they add zero to the public tool/artifact API. A new interactive CLI command is fine; a new *MCP
   tool* is not.
3. **The 5-artifact goldens stay byte-identical** — **except** where DEC-100/101 (the reporting fixes)
   *intentionally* change emitted content, which re-baselines once at GATE B. The interactive layer
   emits **no** artifacts, so it is byte-identical trivially.
4. **ASCII-degrade + `--plain`/`NO_COLOR` parity, Windows cp1252-safe (DEC-078/080)** — carried into
   **every** interactive glyph path (the REPL prompt, the Textual widgets, the wizard). Textual runs on
   Windows but the cp1252 console is the risk surface; degrade exactly as the styled CLI does.
5. **Never add a runtime dependency without a DEC** — `prompt_toolkit` + `textual` each get an entry,
   and land behind the `[interactive]` extra (not the lean default install).
6. **`prompt_toolkit` and `Textual` must not be nested** (research §1). The shell dispatches: REPL loop
   in prompt_toolkit; the Textual `App` is *launched* full-screen (suspend → run → return), never
   rendered inside the prompt.
7. **The `Endpoint`/`base.join` keystone (DEC-043/055)** governs the deferred protocol carryover
   (DEC-103): a new protocol = a `KeyBuilder` + provider/consumer extractors only, never a change to
   `trace`/emit/`serve`. No new node type.
8. **Honest reporting, never fabrication.** The reporting fixes make the counts *truer*, not prettier.
   Never push/publish without explicit instruction; test alongside; PROGRESS + a DEC each session.

---

## §4 — The tracks

| Track | Name | Delivers | DECs |
|---|---|---|---|
| **A** | **The interactive CLI** (headline) | query REPL → Textual TUI browser → `onboard` wizard → session shell | DEC-096–099 |
| **B** | **Reporting-precision fixes** | examples-only source-count clarity; `<module>` display-name resolution | DEC-100, DEC-101 |
| **C** | **Cosmetic ergonomics** | `mcp-config --dev`; `list --prune` | DEC-102 |
| **D** | **Carryover (gated)** | protocol carryover (demand-gated); GATE A Arm B (hardware-gated, reserved) | DEC-103, (reserved) |

Priority: **A > B > C**, with **D not planned into this cycle** (pulled only if a target repo demands
a protocol, or when GPU hardware lands). Suggested order interleaves the small B fixes as warm-ups
before the larger A steps, but A is the spine.

---

## §5 — Build sequence (DEC order ≈ build order)

```
DEC-095  v0.9 scope verdict (this KICKOFF, formalized). No code.
         ──────────────────────────────────────────────── warm-up: the reporting fixes (small, high-clarity)
DEC-100  Examples-only source-count clarity — annotate the headline when files are demoted to
         ROLE_EXAMPLE (DEC-049), e.g. "3 source / 117 in graph (114 demoted as examples/)".
         Reporting only; the classification is CORRECT and unchanged.                  [v0.8 DEFERRED §2]
DEC-101  `<module>` qualified-name display — resolve module-scope symbols to a readable name
         (module dotted-path / file stem) instead of the literal `<module>` in routes + AGENT_BRIEF
         rules. The join is already correct; this is display-name only.                [v0.8 DEFERRED §2]
   ▸ GATE B: DEC-100/101 change emitted artifact CONTENT — re-baseline the 5 goldens ONCE with the
     diff documented in the DECs, then freeze again. Every later step is byte-identical.
         ──────────────────────────────────────────────── Track A: the interactive CLI
DEC-096  Interactive query REPL — `forensic repl` (behind [interactive]): open ONE LadybugStore +
         lexical index, loop on Cypher + NL queries (reuse query/nl.py + query/lexical.py),
         history + completion + confidence-styled output, clean teardown on Ctrl-C/Ctrl-D.
         Establishes the persistent-open-store lifecycle everything else reuses.
DEC-097  Textual TUI graph browser — `forensic browse`: full-screen App; browse Symbol/File/
         Endpoint nodes; filter by edge type / confidence / language; jump to impact/context/flow.
         Loopback-free (no browser, no server). Launched blocking; cp1252/--plain parity.
DEC-098  Guided `forensic onboard` wizard — walk a newcomer: extract → read AGENT_BRIEF → wire the
         MCP server, surfacing the `--project`/`--repo` gotcha and the restart-and-approve step.
         Prints the correct client snippet (reuse the DEC-102 mcp-config output).
DEC-099  Session shell — `deepdive` (alias): launch inside a repo (or pick from the registry),
         run extract/query/trace/impact/diagram/serve as in-session commands with shared state +
         history over ONE open store. Wraps 096–098: prompt_toolkit loop; DISPATCHES the Textual
         browser (suspend → run → return); never nests the two.
         ──────────────────────────────────────────────── Track C: cosmetic ergonomics
DEC-102  CLI ergonomics — `mcp-config --dev` emits the from-source `uv run --project <dir> forensic
         serve --repo …` form (the current uvx form is post-publish-correct but can't launch an
         unpublished pkg); `list --prune` drops registry entries whose `graph.lbug` no longer exists. [v0.8 usability review]
         ──────────────────────────────────────────────── Track D: DEFERRED (not built this cycle)
DEC-103  Protocol carryover — DEMAND-GATED. gRPC Go/Java; AMQP DROP + Spring @QueueBinding; DRF
         DefaultRouter at scale. Reuse Endpoint; KeyBuilder + extractors only. Pull per real-repo need. [DEC-093]
(resv.)  GATE A Arm B — HARDWARE-GATED. FC-4B-RL end-to-end on ≥16 GB GPU; scale Arm A to --n 50+.
         DEC written when a capable device is in hand. Head-of-line, not scheduled.    [DEC-087/092]
```

---

## §6 — The interactive CLI, in shape (what each step is and isn't)

- **REPL (DEC-096)** — the natural first step and biggest ergonomic win. A line-editing loop
  (prompt_toolkit) over **one open store**. It is *not* a TUI; it's a smarter prompt. Proves the
  session-lifecycle pattern the shell depends on.
- **TUI browser (DEC-097)** — a full-screen Textual app, the terminal sibling of `serve --ui`, for
  **exploring the graph visually without a browser**. It is *not* a web server and not the REPL; it's
  a distinct full-screen mode.
- **Wizard (DEC-098)** — a **linear guided flow** for first-time setup (extract → brief → wire MCP),
  surfacing the exact gotchas the manual-test history recorded. It is *not* a general shell; it's a
  one-shot onboarding path.
- **Shell (DEC-099)** — the **umbrella**. Launch `deepdive`, and the REPL, the browser, the wizard, and
  the command-runner subcommands all live in one session with shared state + history. It **orchestrates
  the other three; it does not re-implement them.** This is why they're built standalone first.

All four are **additive** — the `forensic <cmd>` command-runner stays exactly as-is for
scripting/CI/agents. The interactive layer is opt-in (`[interactive]` extra) and human-facing.

---

## §7 — What's explicitly OUT (non-goals; do not regress)

- **No GUI.** The v0.7 usability gate blocked UI work until autonomous value is proven; even so, a GUI
  is explicitly *not on the horizon* (DEFERRED §1). The interactive CLI is the deliberate,
  terminal-native answer that comes **before** any GUI.
- **No 10th MCP tool, no new artifact, no new node type, no LLM in `src/`, no sixth protocol** without
  real-repo demand. The contract is frozen.
- **No incremental/persistent graph update** — still the v1.0 fundamental; v0.9 stays full-extract. (The
  interactive session holds a store open *within a session*; it does not persist an incrementally-
  updated graph across sessions.)
- **No FastContext Arm B build** — hardware-gated, deferred.
- **No re-classification of `examples/` demotion** — DEC-049 is correct; DEC-100 fixes only the
  *reporting*, never the classification.

---

## §8 — Open design questions delegated to Claude Code

1. **`[interactive]` extra vs default (DEC-096).** Recommend the extra (agent install stays lean).
   Confirm, and make the missing-extra error message precise and actionable.
2. **REPL command grammar (DEC-096).** How are Cypher vs NL distinguished at the prompt — a prefix
   (`:cypher …` / `?nl …`), auto-detect, or a mode toggle? Pick the least surprising; document it.
3. **TUI browser scope (DEC-097).** Start read-only (browse + filter + jump-to-tool-output); defer any
   in-TUI graph mutation. Bound the node set (reuse the DEC-039 node-cap + summarize-and-truncate) so a
   huge repo (omi, 18k edges) doesn't choke the widget.
4. **`<module>` resolution target (DEC-101).** What's the readable name for a module-scope symbol —
   the module dotted-path (`apiapp.deep.handlers`), the file stem, or `module:<file>`? Pick one, apply
   consistently across routes + AGENT_BRIEF + trace, and keep it deterministic (goldens).
5. **Shell store lifecycle across `extract` (DEC-099).** If the user runs `extract` inside a live
   session, the open store must be invalidated/reopened cleanly. Define that transition.
6. **`deepdive` alias wiring (DEC-099).** A second `[project.scripts]` entry (`deepdive = …`) vs a
   documented shell alias. Prefer the real entry point so it works post-`pip install`.

---

## §9 — Mandatory gates

- **Per-step:** `uv run pytest -x` green, `ruff check` clean, test written alongside, PROGRESS
  appended, a DEC entry for the choice.
- **GATE B (after DEC-100/101):** the reporting fixes change emitted content — re-baseline the 5
  goldens **once** with the diff documented in the DECs, then freeze. Every A/C step is byte-identical
  against the new baseline; `wc -c AGENT_BRIEF.md` ≤ 5120 still holds.
- **Interactive-layer testing:** prompt_toolkit REPL logic is unit-tested via its testing utilities
  (feed input, assert output); Textual has an official async test harness (`App.run_test()` + `Pilot`)
  — use it, don't leave the TUI untested. cp1252/`--plain` parity asserted for every new glyph path.
- **Pre-release (v0.9.0):** version bump; CHANGELOG; the 5 golden footers; the `[interactive]` extra
  installs cleanly on Linux/macOS-arm64/Windows; `MANUAL_TEST.md` re-run for `repl`/`browse`/`onboard`/
  `deepdive`; then release **with explicit user authorization**, `uv publish` via the existing OIDC
  flow.

---

## §10 — DEC pre-assignment

| DEC | Title (planning) | Track | Gate |
|---|---|---|---|
| 095 | v0.9 scope verdict | — | — |
| 096 | interactive query REPL (`forensic repl`, prompt_toolkit, open-store lifecycle) | A | |
| 097 | Textual TUI graph browser (`forensic browse`) | A | |
| 098 | guided `forensic onboard` wizard | A | |
| 099 | session shell (`deepdive`, wraps 096–098) | A | |
| 100 | examples-only source-count clarity (reporting) | B | **B** |
| 101 | `<module>` qualified-name display resolution | B | **B** |
| 102 | CLI ergonomics — `mcp-config --dev` + `list --prune` | C | |
| 103 | protocol carryover (demand-gated; not scheduled) | D | |
| (resv.) | GATE A Arm B (hardware-gated; DEC written when GPU lands) | D | |

---

## §11 — The UI trajectory (build the complete console now; earn the desktop later)

v0.9 is the **complete** interactive experience, not a placeholder. `forensic info` is the static
panel; the real surface is `deepdive` (the session shell) + the full Textual browser + the REPL. The
reference class is **k9s / lazygit / pgcli** — a polished, keyboard-driven power-user console over the
graph. Build it to that bar, not to a minimum-viable one.

Three directives that keep the ambition on the rails:

1. **Console, not chat agent (the identity line).** Codex and Claude Code are **LLM chat agents**;
   deepdive is the **zero-LLM context tool those agents consume** (via MCP). The interactive CLI
   borrows their *interface polish and terminal-native feel* — never their LLM loop. An LLM in any
   interactive path is a DEC-009 breach and erases the Apache-2.0 differentiator. Agents stay agents
   (e.g. `hermes-agent` sits *on top of* deepdive via MCP); deepdive stays the console.

2. **Build desktop-serve-ready (the trajectory, for free).** Textual apps run in the terminal **and**
   serve to a browser/desktop window via `textual serve` with no rewrite. So the DEC-097 browser and
   the DEC-099 shell must be built so nothing precludes `textual serve` — no terminal-only escape
   hatches, no direct stdin/stdout hacks that break under the web transport, state on the `App` not in
   module globals. Building the complete TUI now **is** the groundwork for the desktop-ish version.

3. **The native-desktop GUI stays gated (honor the gate we set).** A true native desktop app remains
   gated on the autonomous-usefulness proof (the v0.7/v0.8 gate) — it is **not** v0.9. Shipping a GUI
   on an unproven autonomous core is exactly what that gate prevents. The path is: complete TUI in v0.9
   → `textual serve` for a desktop-ish surface any time → the native-desktop arc opens when GATE A Arm B
   lands (hardware permitting), as its own research arc with a superseding DEC. Revisiting the gate
   earlier is a deliberate decision (a superseding DEC + an argument), never a drift.

---

*v0.9 in one line: we proved the graph is trustworthy in v0.8; now we make it a pleasure to drive by
hand — a complete, polished Deepdive console (REPL → TUI → wizard → shell) on top of the same zero-LLM
graph, built desktop-serve-ready — finishing the tool properly before the hardware-gated autonomous
proof and any native GUI.*
