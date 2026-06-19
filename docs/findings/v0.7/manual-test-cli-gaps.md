# Manual-test CLI gaps — v0.7 usability gate (DEC-080)

First real run of `docs/v0.7/MANUAL_TEST.md` by the user, solo, as the usability gate
demands. The test instrument did its job: driving every command end-to-end surfaced
**three CLI-surface gaps** that the automated suite never caught because no test exercised
the *invocation surface* the way a human (or an onboarded agent) does. All three are now
fixed with regression guards. None touch the engine, the graph, or the DEC-043/055 Endpoint
keystone — they are CLI-ergonomics and generated-doc-accuracy fixes.

Environment: Windows 11, cp1252 console, `uv run`, repo `C:/Dev/scratch/spring_react_demo`.

## Gap 1 — `serve --repo` was a positional argument (the one the user hit)

`forensic serve --ui --repo <path>` failed with `No such option '--repo'`. `serve`'s `repo`
parameter was a `typer.Argument` (positional), while the two sibling graph-consuming
commands `trace` and `graph` both expose it as a `--repo` `typer.Option`. MANUAL_TEST §7 and
the §8 MCP-config snippet (`"args": [..., "serve", "--repo", ...]`) both assume the option
form — so **agent onboarding via the MCP server would have failed identically**, not just the
UI step.

**Fix:** `serve`'s `repo` is now a `--repo` option (default `Path(".")`, so bare
`forensic serve` still works), matching `trace`/`graph`. `cli/app.py`.
**Guard:** `test_cli_serve_accepts_repo_option`, `test_cli_serve_repo_option_in_help`.

## Gap 2 — piped `--help` crashed on a cp1252 console (UnicodeEncodeError)

`forensic --help | …` and `forensic trace --help | …` raised
`UnicodeEncodeError: 'charmap' codec can't encode character '→'`. The `trace` docstring
contained `→` (U+2192); Typer/Click render command help through a printer that honours the
Windows console code page, and the top-level help embeds each subcommand's short-help — so
trace's arrow crashed **both** the top-level and the `trace` help when stdout was a pipe.

This is the same cp1252 principle the Step-6 style finding established
(`cli-style-foundation-test.md`), but on a path that finding did **not** cover: the
**Typer/Click help printer** is separate from the styled Rich console, so the style layer's
ASCII degrade path never protected it. Note the distinction confirmed during triage:

| path | piped on cp1252 |
|---|---|
| `trace … --json`, styled trace tree, `graph`, `info \| cat`, `extract \| cat` | safe (rc=0) — Rich console degrade |
| `forensic --help`, `trace --help` (pre-fix) | **crash** — Typer/Click help printer, non-ASCII docstring |

`—` (em-dash) and `…` (ellipsis) are cp1252-encodable, so only the `→`/`←`-class glyphs were
at fault — narrower than first feared.

**Fix:** the `trace` docstring first line is now ASCII (`->`), with a comment explaining the
constraint. `cli/app.py`.
**Guard:** `test_help_text_is_cp1252_safe` — introspects every command's docstring +
option-help and encodes to cp1252 (deterministic, cross-platform; targets the body text, not
the Rich panel borders which the real piped/non-TTY path drops).

## Gap 3 — generated onboarding shims undercounted the MCP tools (5, not 9)

`emit/shims.py` told every onboarded repo (via the generated `CLAUDE.md`/`AGENTS.md`) that
the MCP server exposes "five composite tools (`impact`, `context`, `flow`, `archaeology`,
`query`)". The server registers **nine** `@server.tool()`s — the original five plus
`record_insight`/`recall_insights` (DEC-019), `visualize` (DEC-039), `trace` (DEC-052). An
onboarded agent was therefore told a stale, incomplete capability set — a direct hit to
MANUAL_TEST Q4 ("does an agent get told the tool / outputs / capabilities?").

The drift was confined to **static text**: the live `forensic info` panel is data-driven and
already reported 9 (`cli-style-foundation-test.md`: "tools == 9"). Two more static stragglers
of the same vintage were corrected for accuracy: the `mcp_server/__init__.py` module
docstring ("Five composite tools").

**Fix:** shim text + module docstring now list all nine. `emit/shims.py`,
`mcp_server/__init__.py`.
**Guard:** `test_editor_shim_lists_all_nine_mcp_tools`.

## Verification

- Full suite green (was 772 pre-session); +4 new guards across `test_cli.py` / `test_shims.py`.
- `ruff check` clean.
- Real piped `forensic --help` / `forensic trace --help`: rc=0, no UnicodeEncodeError.
- `forensic serve --ui --repo C:/Dev/scratch/spring_react_demo`: binds 127.0.0.1, HTTP 200.
- `spring_react_demo` re-extracted post-fix — generated `CLAUDE.md` now lists nine tools.

## Takeaway

The usability gate paid for itself on the first run: every gap was on the **invocation /
onboarding surface**, invisible to a suite that tests functions rather than the way a human or
agent first touches the tool. The contract (5 artifacts / 5 protocols / 9 tools), the engine,
and the Endpoint keystone are untouched. Remaining manual-test questions (Q1–Q4 scorecard)
are still the user's to answer; these fixes only remove the friction that blocked a clean run.
