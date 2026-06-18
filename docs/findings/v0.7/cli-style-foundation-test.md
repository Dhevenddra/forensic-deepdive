# CLI style system foundation — v0.7 Step 6 acceptance (DEC-077 + DEC-078)

Track B begins — the publish-facing **styled CLI**, Hermes-inspired, in the project's
**blue / black / white** tones. Step 6 is the *foundation*: the dependency, a themed
Console, the static ASCII banner, and the **data-driven capability panel** (`forensic info`).
Step 7 wires the styled `extract`/`trace`/stats rendering. Presentation keystone (DEC-071
§1b) holds throughout: **Console-only, artifacts byte-identical, no ANSI on machine streams**.

## DEC-077 — the `rich` dependency (honest correction)

DEC-071 assumed `rich` was only transitive (via `typer`) and planned to "promote" it to a
pinned direct dep at `>=14,<15`. **It was already a direct dependency** (`rich>=13.7`), and
`rich` **15.0.0** is installed/locked — so the planned `<15` pin was stale (it would
downgrade). DEC-077 records the reality: `rich` is the load-bearing style dependency, pinned
`>=14,<16` (15.x stays valid; the Console/Theme/Panel APIs we use are stable across 14–15).
`uv lock` re-resolves to the same 15.0.0; `textual` + `pyfiglet` stay deferred — **no new
transitive package**.

## DEC-078 — the `cli/style/` layer

`cli.py` became the `cli/` **package** (`cli/app.py` = the Typer app, re-exported from
`cli/__init__.py` so `forensic_deepdive.cli:app` and `from forensic_deepdive.cli import app`
are unchanged) so `cli/style/` can live where the contract specifies.

- **`console.py`** — one themed Rich `Console` + the `FORENSIC_THEME`. **Brand chrome =
  blue/black/white** (wordmark, borders, headers, labels). **Confidence keeps its semantic
  palette** — EXTRACTED green / INFERRED yellow / AMBIGUOUS red — because that is a universal
  convention and must survive colourblind/pipe use; recolouring it to brand-blue would
  destroy meaning. Confidence is therefore **never colour-alone**: a glyph (`● ◐ ○`) **and
  the word** always travel with the colour (`confidence_label`), with an ASCII letter
  fallback (`[E]`) for non-UTF-8 / plain streams.
- **`banner.py`** — a **static embedded ASCII wordmark** ("DEEPDIVE", no `pyfiglet`) + the
  **data-driven capability panel**: artifacts from the canonical filename tuple, protocols
  from the live `contracts.registry.REGISTRY`, MCP tools introspected from a (cheap, DB-less)
  `make_server(...)._tool_manager.list_tools()` — so the panel **can never drift** from the
  frozen 5-artifact / 5-protocol / 9-tool contract. `forensic info` renders banner + panel.

## Presentation keystone — verified

| check | result |
|---|---|
| colour TTY (`forensic info`) | block wordmark + `●◐○` glyphs + ANSI |
| pipe / non-TTY (`forensic info \| cat`) | plain "DEEPDIVE" title, ASCII box, `[E] EXTRACTED`, **0 ANSI codes**, exit 0 |
| `--plain` / `NO_COLOR` | force no-colour (`get_console().no_color is True`) |
| cp1252 pipe (Windows) | no `█`/`●` written (they crash a cp1252 encode) — ASCII fallback used |
| panel data-driven | protocols == `sorted(REGISTRY)`; artifacts == the 5 contract files; tools == 9 |
| **`cli/style` never imports `emit/`** | guarded by a test scanning every import line |
| goldens | **byte-identical** (Console-only; no extraction/emit/machine-output change) |

A subtle real-world catch the pipe test surfaced: the `●` confidence glyph (and the `█`
wordmark) are **non-ASCII** and *crash a cp1252 Windows pipe* on encode. The fix is the
degrade path — block art only on a UTF-8 colour TTY; ASCII letters (`[E]`) and a plain title
everywhere else — so the styled CLI is genuinely pipe/CI-safe, not just colour-suppressed.

## Keystone / scope

Track B diffs touch only `cli/*` (the package move + the style layer) + `pyproject.toml` —
**never `emit/*` or any machine-output path**. The 5-artifact/9-tool contract is unchanged
(the panel *reads* it). `serve` (MCP stdio / `--ui` HTML) gains no ANSI. Tests:
`tests/test_cli_style.py` (7) + the existing `test_cli.py` unchanged.

## Aesthetic refinement — Hermes-style blue gradient

Per the brief, the wordmark carries a **vertical blue gradient** (light `#7cc7ff` → deep
`#1b5fc9`, per row) echoing Hermes' gold→bronze depth in our palette — truecolor hexes that
Rich auto-degrades to the nearest 256/8-colour blue, and that vanish entirely on the plain
title path. (Reference: `hermes-agent`'s `hermes_cli/banner.py` per-row truecolor rows.)

## Takeaway

The styled surface is in place — a DEEPDIVE block banner and a registry-driven capability
panel in blue/black/white, with the confidence taxonomy preserved and never colour-alone,
degrading cleanly to ASCII on pipes/CI/`--plain`. Step 7 styles the `extract`/`trace`/stats
commands on this foundation.
