# KICKOFF_v0.7.md — operating mode for v0.7 "Coverage Completion + the CLI Style System"

> Paste the block in §8 as your first message to Claude Code in the repo. Everything above compresses
> into it. Binds with `CLAUDE.md`; points at `PRD_v0.7.md` (the contract) and `research_v0.7.md`
> (cited as *research §1–§9*). §9 delegates the TUI *craft* to Claude Code; §10 mandates the end-of-v0.7
> manual-test playbook.

## 1. What you're building (one breath)
v0.6 shipped at **9/9 gate** (DEC-001→070; v0.6.0, 740 tests). v0.7 is a **two-track, publish-prep**
release. **Track A (engine)** completes the v0.6 findings-ledger seeds — Django provider completion,
JAX-RS completion, AMQP literal-key real-repo acceptance, memory lane-(iii) follow-ons, two perf wins —
each a pure extractor/resolver/reconcile change on the **unchanged** `Endpoint`/`base.join`/`trace`/emit/
`serve` spine. **Track B (presentation)** establishes a **Hermes-style styled CLI** on **Rich** (already
in the tree via `typer`), with the confidence taxonomy **color-coded** (EXTRACTED green / INFERRED
yellow / AMBIGUOUS red). **Zero new transitive deps.** The full interactive **Textual** TUI and **gRPC
Go/Java + `[proto]`** stay deferred. v0.7 makes the tool **feel ready for others** without changing what
it extracts.

## 2. The two keystones you must internalize
**(2a) Extraction keystone (unchanged):** reuse the `Endpoint` node; `trace`/HOTPATHS/`serve --ui` query
generically with no `protocol==` filter; `base.join` is never touched for a new match shape; the DI/ORM
`DbTable` is the one DEC'd node exception. Track A is confined to `contracts/*`, `contracts/http/
providers/*`, `static/resolver.py`, `base.reconcile_*`, `insights/*`, and the graph adapter.
**(2b) Presentation keystone (NEW):** the style system styles the **Console (stdout/stderr) ONLY**. The
five markdown artifacts stay **byte-identical plain markdown** — `cli/style/` never imports into or
touches `emit/`, and **no ANSI ever reaches an artifact file or a machine-output stream** (`serve`, MCP
stdio). It degrades on non-TTY / `--plain` / `NO_COLOR`, adds **no 6th artifact / 10th MCP tool**, and the
capability panel is **data-driven from the registries** (never a hardcoded list that can drift). If a
style change alters an artifact byte or a machine stream, you broke it — fix the layering, not the test.

## 3. Session-start protocol (with CLAUDE.md's)
1. `CLAUDE.md` → `DECISIONS.md` → `PROGRESS.md` → `git log --oneline -10`.
2. Read `PRD_v0.7.md` §0–§4 fully, §5–§10 skim. Keep `research_v0.7.md` for §refs.
3. State in one sentence: *"Working on v0.7 Step <N> (<name>), respecting DEC-<M> about <Y>."*
4. `DECISIONS.md` ends at **DEC-070**; v0.7 starts at **DEC-071**.

## 4. Build order (do not reorder) — engine first, presentation last
**0** scope verdict (DEC-071, write first) → **1** Django provider completion (DEC-072, warm-up: the #1
documented seed) → **2** JAX-RS completion (DEC-073) → **3** AMQP literal-key real-repo acceptance
(DEC-074) → **4** memory lane-(iii) follow-ons (DEC-075) → **5** perf (DEC-076) → **6** CLI style system
foundation (DEC-077 dep + DEC-078 layer) → **7** styled command rendering (DEC-079). Engine refinements
settle behavior first; the presentation layer wraps *settled* output last (styling output that then
changes wastes the polish). The CLI is the publish-facing headline but the lowest-risk-when-last.

## 5. The rules that catch most mistakes here
1. **Two keystones, two zero-diff proofs.** Track A's per-step `git diff` never touches `trace`/emit/
   `serve` query logic; **Track B's never touches `emit/*` or any machine-output path** (only `cli/
   style/*` + `cli.py` + `pyproject.toml`).
2. **Confidence stays sacred** (and now *visible*): EXTRACTED only deterministic/literal; Django
   `include(<variable>)` resolved-to-literal → EXTRACTED, same-name fallback → INFERRED; JAX-RS interface/
   abstract return → AMBIGUOUS-unmatched; AMQP exact → EXTRACTED, wildcard → INFERRED, provable non-match
   → DROP, multi → AMBIGUOUS. The TUI palette must **match the taxonomy exactly** and must **not encode
   confidence by color alone** (carry a glyph/letter too, for `--plain` + colorblind safety).
3. **Pure-static floor + no new transitive dep.** Track A adds none; Track B's only dependency action is
   promoting the already-transitive `rich` to an explicit pinned direct dep (`rich>=14,<15`, MIT).
   **`textual` and `[proto]` stay deferred.** Banner = a static embedded ASCII string (no `pyfiglet`).
   Memory decay = stdlib math (no `py-fsrs`). Semantic insight recall = the existing `[semantic]` ONNX
   path (LLM-free), opt-in.
4. **No fabrication.** Unresolvable Django variable/view, JAX-RS `Object` return, AMQP non-match → honest
   unmatched Endpoint / dropped edge, never a synthetic prefix/`symbol_id`/guessed route.
5. **Never automatic side effects.** The shadow-ref push is `--push`/explicit only (the never-push
   discipline extends to the insight ref). The styled output never writes ANSI to files or pipes.

## 6. The differentiator, stated plainly (research §9)
GitNexus is still PolyForm-Noncommercial (we are Apache-2.0) and ships the open #1183 FastAPI prefix-
nesting bug — the same shape Track A §3.1's `include(<variable>)` + CBV-verb work hardens against on the
Django side. Graphify is MIT but **LLM-required** (not pure-static), no cross-boundary join. And the
styled, confidence-colored CLI is a presentation differentiator neither ships — forensic-deepdive remains
the only pure-static, materialized cross-boundary join, now with a publish-grade terminal surface and an
LLM-free agent-memory layer.

## 7. What "done" means (the §4.9 gate, publish-prep posture)
`pytest -x` green; `ruff` clean; **goldens byte-identical** (Track A graph-only, Track B Console-only);
`AGENT_BRIEF ≤5kb`; 5-artifact + 9-tool contract unchanged; both per-track keystone diffs clean.
**Real-repo acceptance:** Step 1 → wagtail's 9 collapsed endpoints carry correct prefixes + a DRF-default-
router repo's `@action`/CBV verbs; Step 2 → an `@ApplicationPath`+`@Produces` repo, no bookstore
regression; Step 3 → a literal-key topic-exchange repo exercises EXTRACTED + DROP on real code; Step 4 →
semantic recall + decay reorder + `--push` round-trip; Step 5 → Superset speedup, byte-identical; Steps
6–7 → TTY-styled / pipe-plain on the acceptance repos, palette matches taxonomy, capability panel
registry-driven. Findings under `docs/findings/v0.7/`. An honest single-repo shortfall (reported, never
fabricated) is an acceptable pass with the gap promoted to v0.8. **Then do §10** (the manual-test
playbook). As in v0.6, do **not** push to remote (a separate explicit instruction, never implied).

## 8. The paste-able kickoff block
```
Read CLAUDE.md, DECISIONS.md, PROGRESS.md, and `git log --oneline -10`. Then read
docs/v0.7/PRD_v0.7.md (§0–§4 fully, §5–§10 skim) and docs/v0.7/KICKOFF_v0.7.md;
keep docs/v0.7/research_v0.7.md for the §refs.

v0.6 shipped at 9/9 gate (DEC-001→070; v0.6.0, 740 tests). We are building v0.7
"Coverage Completion + the CLI Style System" — a TWO-TRACK, publish-prep release.
Track A (engine) COMPLETES the v0.6 findings-ledger seeds; Track B (presentation)
establishes a Hermes-style styled CLI on Rich. NOT a new protocol, NOT new
architecture. The full interactive Textual TUI and gRPC Go/Java + [proto] stay
DEFERRED to their own arcs. GUI/IDE stays deferred.

FIRST: write DEC-071 — the v0.7 scope verdict: (A) Track A = complete the ledger
(Django include(<variable>) recursion + CBV verbs + DRF @action + deep view paths;
JAX-RS @ApplicationPath/@Produces/@Consumes + the interface-return note; AMQP
literal-key real-repo acceptance; memory lane-(iii) follow-ons = semantic RRF over
insights + a stdlib decay score + an explicit shadow-ref push; two perf wins =
resolver suffix index + LadybugDB prepared-statement reuse); (B) Track B = a Rich
styled CLI (banner + data-driven capability panel + confidence color-coding +
styled extract/trace/stats), CONSOLE-ONLY; (C) dependency = promote the transitive
rich to an explicit pinned direct dep, NO new transitive package, textual + [proto]
deferred; (D) a styled CLI is publish-prep polish of the existing terminal surface,
DISTINCT from the deferred GUI/IDE and the deferred full-screen Textual app. Do NOT
write other v0.7 code until DEC-071 is committed.

TWO KEYSTONES (internalize, PRD §1): (2a) extraction — reuse the Endpoint node, query
generically, never touch base.join for a new match shape (Track A confined to
contracts/*, providers/*, static/resolver.py, base.reconcile_*, insights/*, the graph
adapter). (2b) presentation — the style layer styles the Console (stdout/stderr) ONLY;
the five markdown artifacts stay BYTE-IDENTICAL plain markdown; NO ANSI on any
machine-output stream (serve, MCP stdio); degrade on non-TTY/--plain/NO_COLOR; NO 6th
artifact / 10th MCP tool; the capability panel is data-driven from the registries (never
hardcoded). If a refinement makes you edit trace/emit/serve (Track A) or emit/* or a
machine stream (Track B), STOP and re-layer.

THEN build v0.7 in order 1→2→3→4→5→6→7 (PRD §3), one step at a time, tests green before
moving on, a DEC per non-trivial choice (ending ~DEC-079), PROGRESS.md + the lane-(iii)
insight store (§8.10 dogfood) updated each session end. Honor every invariant in PRD §8
— especially: confidence sacred AND now visible (the palette matches the taxonomy
EXACTLY and never encodes confidence by color alone — carry a glyph/letter for --plain +
colorblind safety); pure-static floor; NO new transitive dep (rich promoted to explicit
pinned direct dep is the only dependency action; textual + [proto] deferred; banner =
static ASCII, no pyfiglet; decay = stdlib math, no py-fsrs); no fabrication; the
shadow-ref push is --push/explicit only.

YOU OWN THE TUI CRAFT (KICKOFF §9): the information design + the two keystones are fixed;
the rendering craft (exact Rich primitives, glyphs, layout, palette values, the
capability-panel trigger points, the trace-tree shape, the progress style, whether to add
a `forensic info`/`status` subcommand) is YOURS to orchestrate within the constraints.
Resolve the §9 open questions during Steps 6–7; surface to the user ONLY the few that
change default UX. Default to terminal-portable, accessible, pipe-safe choices.

Step 1 (DEC-072, the warm-up): Django provider completion — resolve include(<variable>)
to its bound urlpatterns and recurse (the wagtail prefix-collapse fix, the GitNexus #1183
last mile); read CBV get/post/... method defs for specific verbs; parse DRF
@action(detail=,methods=); resolve deep dotted view paths. Acceptance: wagtail's 9
collapsed endpoints carry correct parent prefixes; a DRF-default-router repo's @action +
CBV verbs appear. No fabrication (unresolvable → honest unmatched Endpoint).

AT THE END (KICKOFF §10), after v0.7 passes its §4.9 gate: produce docs/v0.7/MANUAL_TEST.md
— a guided, copy-pasteable manual-test playbook (real commands + the real MCP tool names +
the acceptance repos) — and walk the user through it interactively, covering BOTH the CLI
path and the manual/MCP path (see §10). Fill in the exact subcommands/paths from the real
CLI surface.

Confirm understanding in one sentence, write DEC-071, then begin Step 1. Do NOT push to
remote. Do NOT touch v0.8+, the interactive Textual TUI, or the GUI/IDE until v0.7 passes
its §4.9 gate.
```

## 9. TUI craft delegated to Claude Code (you orchestrate — resolve during Steps 6–7)
The **information design** and the **two keystones** above are fixed. The **rendering craft is yours** —
own it, make tasteful, terminal-portable, accessible, pipe-safe choices, and surface back to the user
only the decisions that change default UX. Open questions to resolve (decide, implement, note in the DEC):

1. **Banner** — wordmark text + tagline, single static ASCII string, weight/width. Detect 8-color vs
   256-color/truecolor terminals and pick a palette that degrades gracefully. (No `pyfiglet`.)
2. **Capability panel trigger** — when does it render? Proposed: on bare `forensic` (no args) and on a
   `forensic info` subcommand, plus a compact one-line header on `extract`. You decide the trigger points;
   the panel must be **data-driven from the artifact/protocol/MCP-tool registries**.
3. **Confidence encoding** — exact glyphs (e.g. `● ◐ ○`) vs letters (`[E] [I] [A]`) vs both; ensure it
   reads under `--plain`/`NO_COLOR` (info must not live in color alone — colorblind + pipe safety).
4. **`trace` rendering** — a Rich `Tree` with confidence-colored, `via`-labeled edges on a TTY, **plus a
   preserved plain/`--json` machine mode** for piping (confirm the existing machine output is untouched).
5. **`extract` progress** — a per-phase `Progress` bar (parse→symbols→contracts→join→emit) vs a spinner +
   phase log; pick based on whether phase sizes are known up front. End with a one-line confidence-split
   status.
6. **A `forensic info` / `forensic status` subcommand?** — show the capability panel + (if a graph exists)
   the last extract's stats. This is a CLI convenience (allowed — **not** a 6th artifact or 10th MCP
   tool). You decide whether to add it and its name.
7. **Status line** — end-of-command summary (recommended; we are command-oriented) vs persistent. Not a
   live full-screen app (that's the deferred Textual arc).
8. **Flags/precedence** — `--plain` / `--no-color` global option, `NO_COLOR` env, non-TTY auto-detection;
   define precedence and confirm `serve` / MCP stdio never emit ANSI.

**Questions you (Claude Code) should ask the user only if they materially change UX:** the wordmark/tagline
wording; whether to add `forensic info`; whether the `extract` header panel is on by default or behind a
flag. Everything else: decide and document.

## 10. End-of-v0.7 manual-test playbook (produce + walk the user through)
After the §4.9 gate passes, **produce `docs/v0.7/MANUAL_TEST.md`** — a guided, copy-pasteable playbook
with the **real** subcommands, the **real** 9 MCP tool names, and the acceptance repos — then **walk the
user through it interactively** (one section at a time, waiting for them to confirm before moving on).
Cover **both** paths:

**A. Install & smoke** — `uv sync --all-extras`; `forensic --version`; `forensic info` → the user sees
the banner + capability panel.
**B. CLI extraction** — `forensic extract <repo>` on a small known repo (e.g. spring-petclinic) → the
user watches the styled phase progress + the end status line (symbols, nodes/edges, cross-stack routes,
the colored confidence split) → opens the five artifacts → reads `AGENT_BRIEF.md` (≤5kb).
**C. `trace` walkthrough** — `forensic trace <symbol> --downstream` → the user sees the confidence-colored
tree (green/yellow/red, `via` labeled) and a cross-stack route; then the plain/`--json` mode for piping.
**D. Per-protocol real-repo checks** — reproduce the headline numbers on the acceptance repos: Django
(wagtail — prefixes now correct), JAX-RS (jersey bookstore), gRPC (grpc-examples — 68 genuine AMBIGUOUS,
26 EXTRACTED), AMQP (rabbitmq-tutorials + the new literal-key repo), MCP + registry dispatch (hermes-agent
— 22 tools, 35 registry `ROUTES_TO`). Tell the user the expected figures so they can confirm.
**E. Confidence visual check** — green/yellow/red on a TTY; `--plain` / `NO_COLOR=1` still legible via
glyph/letter.
**F. Pipe / CI safety** — `forensic extract <repo> | cat` and `NO_COLOR=1 forensic …` → plain text, no
ANSI; artifacts on disk are plain markdown.
**G. Memory (lane iii)** — `record_insight` → `recall_insights` (lexical; then semantic if `[semantic]`
installed) → delete the index → it rebuilds from the JSONL → clone the repo + fetch the shadow-ref →
insight survives → `forensic insights push --dry-run`.
**H. Manual / MCP path** — wire the MCP server into an MCP client (Claude Desktop or Claude Code — give
the exact config snippet and `forensic serve` command), then call the **9 tools** by hand and verify the
same `trace` / contracts / insights the CLI showed. This is the "use it the way an agent uses it" check.
**I. Web UI** — `forensic serve --ui` → open the graph, confirm the cross-stack routes render.
**J. A tick-box checklist** the user can mark as they go, ending with "publish-ready? y/n" notes for v0.8.

Produce it, then start walking the user through section A.

---

*A styled CLI is publish-prep polish of the existing terminal surface — not the deferred GUI/IDE and not
the deferred full-screen Textual app. Adopt the Hermes look via Rich over command-oriented output; the
interactive Textual app and the GUI/IDE wait for their own arcs, enabled by v1.0 incremental update. You
own the rendering craft within the two keystones; style settled behavior; end by walking the user through
the manual-test playbook. And "publish-prep" never implies pushing to remote.*
