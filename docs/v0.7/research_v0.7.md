# research_v0.7.md — evidence dossier for "Coverage Completion + the CLI Style System"

> The §refs cited by `PRD_v0.7.md` and `KICKOFF_v0.7.md` map to §1–§9 below. Current as of June 2026
> (knowledge cutoff Jan 2026 + live search). Every dependency that would breach the no-un-DEC'd-dep floor
> is flagged. v0.7 is a two-track **publish-prep** release: Track A completes the v0.6 findings-ledger
> seeds; Track B establishes the styled CLI. Favor the concrete shapes/APIs — they are what gets built.

## §0 — TL;DR
- **Track B (the CLI style system) needs ZERO new transitive deps.** `typer` (the project's CLI
  framework) has since 0.12 always installed `rich` + `shellingham` — the install literally reports
  "Successfully installed typer rich shellingham," and the recent PR #1522 makes `typer` *always* require
  `rich` (typer-slim is now a shallow wrapper). So **`rich` is already in the dependency tree**; the only
  discipline action is a DEC promoting the existing transitive `rich` to an **explicit pinned direct
  dependency** (`rich>=14,<15`, MIT). No floor breach.
- **Rich, not Textual, for v0.7.** Rich = styled *output* for command-oriented tools (tables, trees,
  progress bars, panels, syntax) — "you are still writing a script; Rich just makes the output look
  great." Textual = a full interactive *app* framework (async event loop, widgets, mouse, CSS-like
  styling) — what the Hermes screenshot actually is. `forensic` is command-oriented (`forensic extract
  <path>`), not a REPL, so v0.7 adopts the Hermes **look** via Rich and **defers the full interactive
  Textual dashboard to its own later arc** (the documented "Typer for commands, Rich for output, grow
  into Textual later" path).
- **The presentation-layer keystone:** the style system touches the **Console (stdout/stderr) ONLY** —
  the five markdown artifacts stay **byte-identical plain markdown**, never an ANSI code. Rich
  auto-degrades on a non-TTY (pipe/CI) and honors `NO_COLOR`; add an explicit `--plain` too. Goldens
  unaffected; the composable-tools philosophy (pipe `forensic … | x`) is preserved.
- **The signature design hook:** the tool's whole value is per-edge provenance, so the TUI **color-codes
  by confidence** — EXTRACTED green ● / INFERRED yellow ◐ / AMBIGUOUS red ○ — making the confidence
  taxonomy visually legible in `trace`, stats, and the cross-stack route list.
- **Track A is the well-documented v0.6 → v0.7 seed ledger** (Django `include(<variable>)` recursion, CBV
  verbs + DRF `@action`, JAX-RS `@ApplicationPath`/`@Produces`, AMQP literal-key real-repo, memory
  lane-(iii) follow-ons, two perf items) — all extractor/resolver work on the unchanged spine, zero new
  deps. gRPC Go/Java + the `[proto]` extra stays deferred (a v0.8 protocol-coverage item, not publish-prep).

## §1 — Track B: the dependency decision (the load-bearing fact)
`typer` ≥ 0.12 depends on `rich` + `shellingham` by default; PR #1522 (2026) drops the `typer-slim`
split and makes `typer` *always* require both (survey showed <5% used slim; the library is ~25 MB even
with them). Observed install tree on a current resolver: `mdurl, pygments, markdown-it-py, rich
(14.3.2), shellingham (1.5.4), typer (0.22.0)`. **Implication for forensic-deepdive:** since the CLI is
built on `typer`, `rich` is **already a runtime dependency transitively**. Using it directly for the
style system therefore introduces **no new transitive package** — the only correct discipline move is a
DEC that lists `rich` as an **explicit, pinned, direct** dependency (so the project owns the pin rather
than inheriting it from typer), MIT-licensed, pure-Python. **Defer `textual`** entirely (it is the
interactive-app arc). **Escape hatches already exist:** `Console(no_color=…)`, `NO_COLOR` env (Rich
honors it), non-TTY auto-detection, and typer's `TYPER_USE_RICH=0` / `rich_markup_mode=None` for the
help layer.

## §2 — Track B: the aesthetic spec (Hermes-style, Rich-rendered)
The look to match (from the Hermes Agent reference): an ASCII wordmark banner, a structured **capability
panel** (Hermes lists tools + skills; we list artifacts + protocols + MCP tools + the confidence
legend), and a persistent **status line**. forensic-deepdive is command-oriented, so these render at
command start/end, not as a live full-screen app. **The banner is a static embedded ASCII string**
(a module constant — **no `pyfiglet` runtime dep**, floor-clean). Illustrative startup/capability panel
(exact glyphs are Claude Code's call; this fixes the *information design*, not the pixels):

```
┌─ forensic-deepdive ─────────────────────────────── v0.7.0 · 2026-06-14 ─┐
│   forensic · deepdive            forensic understanding of any codebase  │
│                                                                          │
│   Artifacts   MAP · HOTPATHS · ARCHAEOLOGY · MENTAL_MODEL · AGENT_BRIEF  │
│   Protocols   HTTP · MCP · registry · gRPC · messaging            (5)    │
│   MCP tools   trace · record_insight · recall_insights · …        (9)    │
│   Confidence  ● EXTRACTED      ◐ INFERRED      ○ AMBIGUOUS               │
└──────────────────────────────────────────────────────────────────────────┘
```
(MCP-tool names above are illustrative — Claude Code wires the panel to the real registered tool set;
the panel is data-driven from the artifact/protocol/tool registries, never a hardcoded list that can
drift from the frozen contract.) Post-`extract` status line, data-driven from the graph:

```
 repo superset · 18,764 symbols · 24,901 nodes / 41,332 edges
 routes 61 cross-stack · ● 54 EXTRACTED  ◐ 7 INFERRED  ○ 0 AMBIGUOUS · 116.6s
```

**Rich primitives that cover all of this** (no Textual): `Console` (the single rendering surface),
`Panel` (banner + capability box), `Table` (stats, the cross-stack route list), `Tree` (the `trace`
walk), `Progress` (extract phases), `Syntax` (code snippets in `trace`/HOTPATHS echoes), and a `Theme`
holding the confidence palette. **Confidence palette (the signature):** `extracted=green`,
`inferred=yellow`, `ambiguous=red`, plus `dim` for filtered/dropped — applied wherever a `confidence`
property is rendered (the `trace` tree edges, the route table, the stats line).

## §3 — Track B: where it lives, and the presentation-layer keystone
A new `cli/style/` package: `console.py` (one shared `Console` + the `Theme`), `banner.py` (the static
ASCII + the capability panel, data-driven from the registries), `render.py` (the `extract`-phase
`Progress`, the confidence-colored `trace` `Tree`, the stats `Table`). `cli.py` calls into these.
**Invariants that make it keystone-safe:**
- **Console-only.** The style layer writes to the Rich `Console` (stdout/stderr). The five emitted
  artifacts are produced by `emit/*` and stay **byte-identical plain markdown** — the style package
  **never** imports into or touches `emit/`. (This is the Track-B analogue of "don't touch the artifact
  contract.")
- **No 6th artifact, no 10th MCP tool.** The TUI is a rendering of existing `extract`/`trace`/`serve`
  outputs; the 5-artifact + 9-tool public contract is frozen.
- **Degrade cleanly.** Non-TTY (pipe/CI) → Rich emits plain text; `--plain` and `NO_COLOR` force it;
  `serve`/MCP stdio paths are unaffected (machine output must never gain ANSI).
- **Pure-static floor untouched** — presentation is downstream of extraction; it runs no code, hits no
  network/LLM.

## §4 — Track A: Django provider completion (DEC-072) — v0.6 seed #1, #3, #6
v0.6 shipped the Django provider (0 → 125 Endpoints on wagtail, 99 EXTRACTED cross-file HANDLES) with
three documented gaps:
- **`include(<variable>)` recursion** (the #1 seed; the GitNexus #1183 last mile). v0.6 recurses only
  string `include('app.urls')`; a variable mount `path("api/", include(api_urls))` is treated as a root,
  so its routes emit at **bare paths missing the parent prefix** (wagtail: 9 endpoints collapsed on a
  shared path). **Fix:** resolve the variable to its bound `urlpatterns` list (extends the include-graph
  root detection, **not** the join) — bind `api_urls` to its assignment/`import`, recurse, concatenate
  the prefix. **Confidence:** EXTRACTED when the variable resolves to a literal `urlpatterns` list;
  INFERRED if resolved only by cross-file same-name fallback.
- **CBV per-method verbs** (#6): `MyView.as_view()` currently yields a method-agnostic `http::*::/path`;
  read the class's `get`/`post`/`put`/`delete`/`patch` method definitions to emit specific verbs
  (`http::GET::/path` etc.). DRF `APIView`/`ViewSet` method names map the same way. EXTRACTED (literal
  method defs).
- **DRF `@action`** (#6): `@action(detail=True, methods=['post'])` on a ViewSet adds a non-CRUD route
  (`/prefix/{pk}/<action>/`); parse the decorator's `detail`/`methods` to extend the router expansion.
  EXTRACTED-by-convention. **Deep view paths** (`pkg.sub.views.fn`) → resolve the full dotted path, not
  just the trailing name (v0.6 was trailing-name best-effort) — INFERRED→EXTRACTED where the module
  resolves. **Keystone:** `providers/django.py` + the shared resolver only; `base.join`/`trace`/emit/
  `serve` untouched.

## §5 — Track A: JAX-RS completion (DEC-073) — v0.6 seed #5
v0.6 shipped sub-resource locators (jersey bookstore 0 → 1 EXTRACTED). Remaining JAX-RS surface:
- **`@ApplicationPath("/api")`** — the app-level prefix that prepends to every resource path (like the
  NestJS module prefix). Parse the `Application` subclass annotation; concatenate. EXTRACTED.
- **`@Produces`/`@Consumes`** (`MediaType.APPLICATION_JSON`) — content-type negotiation; carry as
  **Endpoint properties** (not part of the key), mirroring how SEP-1575 `version` was handled (DEC-057).
- **Interface/abstract-return locator impl selection** — v0.6 leaves these AMBIGUOUS-unmatched (honest);
  a single intra-repo `implements`-resolution would promote some to INFERRED (the DI ladder precedent,
  DEC-059). Lower priority — keep AMBIGUOUS unless a real repo demands it. **Keystone:** `providers/
  jaxrs.py` + resolver only.

## §6 — Track A: AMQP literal-key real-repo acceptance (DEC-074) — v0.6 seed #2
The v0.6 `amqp_binding_matches` matcher (exact→EXTRACTED / wildcard→INFERRED / non-match→DROP / multi→
AMBIGUOUS) is fixture-proven but the rabbitmq-tutorials compute keys from `sys.argv` → all INFERRED on
the real run. **Need a real topic-exchange app with LITERAL routing keys** to exercise the EXTRACTED and
DROP paths on real code. Candidates (MIT/Apache, literal keys): a `celery`/`kombu`-using app with named
topic bindings; a Spring AMQP `@RabbitListener(bindings=@QueueBinding(... key="orders.*"))` sample; a
`pika` tutorial fork with hardcoded keys. Mostly an acceptance-matrix addition (validation), with any
small matcher edge-case fixes (e.g. `#` zero-word at string boundaries) as they surface. **Keystone:**
matcher/reconcile only.

## §7 — Track A: memory lane-(iii) follow-ons (DEC-075) — v0.6 seed #7, #8
v0.6 hardened lane (iii) (FTS5/BM25 recall + content-hash dedup + git shadow-ref + dogfooding). Follow-ons:
- **`[semantic]` ONNX RRF fusion over insights** — recall is FTS5/BM25-only today; fuse the existing
  opt-in ONNX embedding path via the existing RRF (DEC-038) for semantic insight recall. Opt-in, behind
  the existing `[semantic]` extra — **no new dep, floor-clean** (the LLM-free local ONNX path).
- **Decay/staleness score** — a recency/importance weight on recall, kept **off the LLM path**. **Hand-
  roll a simple Ebbinghaus/half-life decay (stdlib math) rather than add `py-fsrs`** — FSRS is excellent
  but a dep we don't need for a recall weight; the floor discipline favors the stdlib formula. (Note
  `py-fsrs`, MIT, exists if a richer scheduler is ever wanted — deferred.)
- **Explicit shadow-ref push** — v0.6 syncs the local `refs/forensic-deepdive/insights` ref; add a
  **`forensic insights push` / `--push` flag** to publish it to a remote. **Never automatic** — pushing
  any ref stays an explicit user action (CLAUDE.md's never-push discipline extends to the insight ref).
- **Keystone:** the existing `recall_insights` backend + `insights/*` only; no signature/tool change.

## §8 — Track A: performance (DEC-076) — v0.6 seed #9, #10
v0.6's profiling pass already won 14.7× (1711s → 117s) by fixing `_resolve_python_import`. The two named
next hot spots:
- **`resolve_name_to_files` cross-file-fallback filtering** (~6s on Superset) — apply the same precomputed
  suffix-index trick the import resolver got (DEC-070), with identical determinism (first file in dict
  order wins). Byte-identical output.
- **LadybugDB prepared-statement reuse** (~17s on Superset) — cache/reuse prepared statements across the
  repeated graph writes instead of re-preparing per call. A graph-layer constant-factor win; **must stay
  byte-identical** (same statements, same order). **Incremental/persistent update stays deferred to
  v1.0** (lane i) — these are constant-factor only. **Keystone:** `resolver.py` + the graph adapter only.

## §9 — Competitive & dependency ledger
**Competitive (light recheck — unchanged since the v0.6 dossier §7 unless noted):** GitNexus still
PolyForm-Noncommercial (we are Apache-2.0); its open #1183 (FastAPI prefix nesting) is the exact shape
Track A §4's `include(<variable>)` + CBV-verb work hardens against on the Django side. Graphify still
MIT but **LLM-required** (not pure-static), no cross-boundary join. The styled CLI is a presentation
differentiator neither ships. (No new findings change the differentiation; a full recheck is a v0.8
dossier item.)

**Dependency-discipline ledger:**
| Feature | New dep? | Behind extra? | Breaches floor? |
|---|---|---|---|
| CLI style system (Rich) | **none new** — `rich` already transitive via `typer`; DEC promotes it to explicit pinned direct dep (`rich>=14,<15`, MIT) | no (core UX) | **NO** |
| Banner | none (static embedded ASCII string — no `pyfiglet`) | no | **NO** |
| Interactive Textual TUI | would add `textual` | **DEFERRED** (its own arc) | n/a (not built) |
| Django completion | existing tree-sitter-python | no | **NO** |
| JAX-RS completion | existing tree-sitter-java | no | **NO** |
| AMQP literal acceptance | existing | no | **NO** |
| Memory: semantic RRF | ONNX (existing `[semantic]`, DEC-042) | exists | **NO** |
| Memory: decay | none (stdlib math; `py-fsrs` declined) | no | **NO** |
| Memory: shadow-ref push | none (git plumbing) | no | **NO** |
| Perf (resolver + LadybugDB) | none (`cProfile` stdlib + existing graph adapter) | no | **NO** |

**The only dependency action in v0.7 is promoting the already-present transitive `rich` to an explicit
pinned direct dependency (DEC-077).** No new transitive package enters the tree; `[proto]` and `textual`
stay deferred.
