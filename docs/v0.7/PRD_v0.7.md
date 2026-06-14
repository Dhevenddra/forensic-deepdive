# PRD_v0.7.md — "Coverage Completion + the CLI Style System" (the contract)

> The contract `KICKOFF_v0.7.md` points at. Cites `research_v0.7.md` as *research §1–§9*. Binds with
> `CLAUDE.md`. v0.6 shipped at **9/9 gate** (DEC-001→070; v0.6.0, 740 tests). `DECISIONS.md` ends at
> **DEC-070**; v0.7 starts at **DEC-071**.

---

## §0 — TL;DR
v0.7 is a deliberately **two-track, publish-prep** release. **Track A (engine)** completes the v0.6
findings-ledger seeds — Django provider completion, JAX-RS completion, AMQP literal-key real-repo
acceptance, memory lane-(iii) follow-ons, two perf wins — each an extractor/resolver/reconcile change on
the **unchanged** `Endpoint`/`base.join`/`trace`/emit/`serve` spine. **Track B (presentation)**
establishes a **Hermes-style styled CLI** built on **Rich** (already in the dependency tree via `typer`),
with the tool's confidence taxonomy color-coded (EXTRACTED green / INFERRED yellow / AMBIGUOUS red).
**Zero new transitive deps** (the only dependency action is promoting the transitive `rich` to an
explicit pinned direct dep). The full interactive **Textual** TUI and **gRPC Go/Java + `[proto]`** stay
deferred to their own later arcs. v0.7 is the version that makes forensic-deepdive **feel ready for
others to use** without changing what it extracts.

## §1 — The two keystones (both non-negotiable)
**(1a) The extraction keystone (unchanged).** Reuse the `Endpoint` node for every protocol; `trace()`/
HOTPATHS/`serve --ui` query `Endpoint`/`HANDLES`/`CALLS_ENDPOINT`/`ROUTES_TO` generically with no
`protocol==` filter; the DI/ORM `DbTable` (DEC-059) is the one DEC'd node exception; `base.join` is never
touched for a new match shape. Track A refinements are confined to `contracts/*`, `contracts/http/
providers/*`, the shared `static/resolver.py`, and `base.reconcile_*`.

**(1b) The presentation keystone (new, for Track B).** **The style system styles the Console
(stdout/stderr) ONLY.** The five emitted markdown artifacts (`emit/*`) stay **byte-identical plain
markdown** — the `cli/style/` package never imports into or touches `emit/`, and no ANSI code ever
reaches an artifact file or the MCP/`serve` machine-output paths. The TUI adds **no 6th artifact and no
10th MCP tool** — it renders existing `extract`/`trace`/`serve`/stats outputs. It **degrades cleanly** on
a non-TTY (pipe/CI), under `--plain`, and under `NO_COLOR`. **If a style change would alter an artifact
byte or a machine-output stream, stop — you broke the presentation keystone.**

## §2 — Scope verdict (the spine — recorded as DEC-071, write first)
**(A) Track A = complete the v0.6 findings ledger** (research §4–§8): Django `include(<variable>)`
recursion + CBV verbs + DRF `@action` + deep view paths; JAX-RS `@ApplicationPath`/`@Produces`/
`@Consumes` (+ the interface-return note); AMQP literal-key real-repo acceptance; memory lane-(iii)
follow-ons (semantic RRF over insights, a stdlib decay score, an explicit shadow-ref push); two perf wins
(resolver suffix index, LadybugDB prepared-statement reuse). **(B) Track B = the styled CLI** (research
§1–§3): a Rich presentation layer — banner + data-driven capability panel + confidence color-coding +
styled `extract`/`trace`/stats — Console-only, artifacts plain. **(C) Dependency:** promote the
transitive `rich` to an explicit pinned direct dep; **no new transitive package; `textual` and `[proto]`
deferred.** **(D) Distinguish from the deferred GUI/IDE arc:** a styled CLI/TUI is **publish-prep polish
of the existing terminal surface** (one-shot command output, consumes `extract`/`trace`/`serve`, needs no
incremental update); the graphical/near-live **GUI/IDE and the full interactive Textual app remain
deferred** to their own research arcs (the Textual app is the documented "grow into Textual later" path,
enabled — like the IDE — once v1.0 lands incremental update). **(E) Invariants §8 apply, plus the
presentation keystone §1b and the §8.10 dogfood practice (continued).**

**DEC budget:** DEC-071 → ~DEC-079 (scope + ~8 steps; the established ~1.5× ratio).

## §3 — Build order (do not reorder) + per-step spec
Engine first (Track A, settled behavior), presentation last (Track B, polish wraps settled output):
**0** scope verdict (DEC-071, write first) → **1** Django provider completion (DEC-072, the warm-up:
the #1 documented seed) → **2** JAX-RS completion (DEC-073) → **3** AMQP literal-key real-repo acceptance
(DEC-074) → **4** memory lane-(iii) follow-ons (DEC-075) → **5** perf (DEC-076) → **6** CLI style system
foundation (DEC-077 dep + DEC-078 layer) → **7** styled command rendering (DEC-079). One step at a time,
tests green before moving on, a DEC per non-trivial choice, PROGRESS.md + the insight store (§8.10)
updated each session end.

**Why Django first (warm-up):** it is the #1 documented v0.7 seed (the wagtail `include(<variable>)`
prefix collapse), a contained resolver/provider change, and re-runs an existing acceptance repo — the
v0.6 Step-1 warm-up discipline (a coverage/correctness closer before the new axis). **Why Track B last:**
the presentation layer must render *settled* engine behavior; styling output that then changes wastes the
polish. The CLI is the publish-facing headline but the lowest-risk-when-last.

### §3.1 — Step 1: Django provider completion (DEC-072) — research §4
`contracts/http/providers/django.py` + the shared `static/resolver.py` only. (a) **`include(<variable>)`
recursion:** resolve the variable to its bound `urlpatterns` list (assignment/import binding), recurse,
concatenate the parent prefix — extends the include-graph root detection, **not** the join; EXTRACTED
when the variable resolves to a literal `urlpatterns`, else INFERRED. (b) **CBV per-method verbs:** read
`get`/`post`/`put`/`delete`/`patch` method defs on `View`/`APIView`/`ViewSet` classes to emit specific
verbs instead of `http::*::/path`; EXTRACTED. (c) **DRF `@action(detail=,methods=)`:** parse the
decorator → extend router expansion with the non-CRUD route; EXTRACTED-by-convention. (d) **Deep view
paths** (`pkg.sub.views.fn`): resolve the full dotted path, not the trailing name. **Acceptance:**
re-run wagtail → the 9 collapsed endpoints now carry correct parent prefixes (`include(<variable>)`
resolved); CBV verbs specific; a DRF-default-router repo's `@action` routes appear. **No fabrication:**
an unresolvable variable/view → honest unmatched Endpoint, never a synthetic prefix or `symbol_id`.

### §3.2 — Step 2: JAX-RS completion (DEC-073) — research §5
`contracts/http/providers/jaxrs.py` + resolver only. **`@ApplicationPath("/api")`:** prepend the app
prefix to every resource path (EXTRACTED). **`@Produces`/`@Consumes`:** carry content-type as an Endpoint
**property**, never part of the key (the DEC-057 `version`-property precedent). **Interface/abstract-
return locators:** keep AMBIGUOUS-unmatched (honest) unless a single intra-repo `implements` resolution
is cheap → then INFERRED (the DI ladder precedent). **Acceptance:** a repo with `@ApplicationPath` + a
`@Produces` resource → prefixed routes with the content-type property; no regression on bookstore.

### §3.3 — Step 3: AMQP literal-key real-repo acceptance (DEC-074) — research §6
Mostly a **matrix addition** (validation), not new architecture. Run the v0.6 `amqp_binding_matches`
matcher on a **real topic-exchange app with literal routing keys** (a `kombu`/`celery` named-binding app,
a Spring AMQP `@QueueBinding(key=)` sample, or a `pika` fork with hardcoded keys) to exercise the
**EXTRACTED** (exact) and **DROP** (provable non-match) paths the dynamic rabbitmq-tutorials couldn't.
Fix any small matcher edge case that surfaces (e.g. `#` zero-word at string boundaries). **Keystone:**
matcher/`reconcile_amqp` only. **Acceptance:** at least one EXTRACTED exact-key topic join + one dropped
provable-non-match on real code.

### §3.4 — Step 4: memory lane-(iii) follow-ons (DEC-075) — research §7
`insights/*` + the existing `recall_insights` backend only (no tool/signature change). (a) **`[semantic]`
ONNX RRF over insights:** fuse the opt-in local ONNX embedding path with FTS5/BM25 via the existing RRF
(DEC-038) for semantic recall — opt-in, behind the existing `[semantic]` extra, **LLM-free**. (b)
**Decay score:** a stdlib Ebbinghaus/half-life recency weight on recall, **off the LLM path** — hand-
rolled (no `py-fsrs` dep). (c) **`forensic insights push` / `--push`:** publish the local
`refs/forensic-deepdive/insights` ref to a remote — **explicit only, never automatic** (the never-push
discipline extends to the insight ref). **Floor:** held (existing `[semantic]` + stdlib + git plumbing,
zero runtime LLM). **Acceptance:** semantic recall surfaces an insight with no lexical overlap (opt-in);
decay reorders by recency; `--push`/`--no-push` round-trips the ref to a test remote.

### §3.5 — Step 5: performance (DEC-076) — research §8
`static/resolver.py` + the LadybugDB graph adapter only, **byte-identical output**. (a) **`resolve_name_
to_files` suffix index** — the DEC-070 precomputed-suffix-index trick (first file in dict order wins,
identical determinism), targeting the ~6s residual. (b) **LadybugDB prepared-statement reuse** — cache/
reuse prepared statements across repeated writes (the ~17s item), same statements/order. **Incremental
update stays deferred to v1.0** (constant-factor only). **Acceptance:** a measurable speedup on the
Superset extract with **goldens byte-identical** and the resolver/determinism tests green.

### §3.6 — Step 6: CLI style system foundation (DEC-077 + DEC-078) — research §1–§3
**DEC-077 (dependency):** promote the transitive `rich` to an **explicit pinned direct dependency**
(`rich>=14,<15`, MIT) in `pyproject.toml` — no new transitive package; `textual` not added. **DEC-078
(the layer):** new `cli/style/` package — `console.py` (one shared Rich `Console` + a `Theme` carrying
the **confidence palette**: `extracted=green`, `inferred=yellow`, `ambiguous=red`, `dim` for dropped/
filtered); `banner.py` (the **static embedded ASCII** wordmark — no `pyfiglet` — + the **data-driven
capability panel**: artifacts/protocols/MCP-tools/confidence legend, read from the registries so it can
**never drift from the frozen contract**). **Presentation keystone (§1b):** Console-only; `emit/*`
untouched; `--plain` + `NO_COLOR` + non-TTY auto-degrade; machine output (`serve`, MCP stdio) never gains
ANSI. **Acceptance:** the banner + capability panel render on a TTY; piping to a file/CI yields plain
text; the panel's tool/protocol/artifact lists are read from the registries, not hardcoded; goldens
byte-identical.

### §3.7 — Step 7: styled command rendering (DEC-079) — research §2
`cli/style/render.py` + `cli.py` call sites only. **`extract`:** a Rich `Progress` over the pipeline
phases (parse → symbols → contracts → join → emit) + a post-run status line (symbols, nodes/edges,
cross-stack route count, the **confidence split colored**, elapsed). **`trace`:** render the cross-stack
walk as a Rich `Tree` with **confidence-colored edges** (green/yellow/red) and the `via` protocol
labeled. **stats/summary:** a Rich `Table` for the cross-stack route list (consumer → handler, key,
confidence). **Presentation keystone:** all to the Console; `trace`'s underlying data/JSON output mode
stays plain for piping. **Acceptance:** `forensic extract`/`trace` render the styled views on a TTY and
plain when piped; the confidence colors match the taxonomy; no artifact/machine-output change.

## §4 — The acceptance gate (§4.9, publish-prep posture)
`pytest -x` green; `ruff` clean; **goldens byte-identical** (every Track A refinement is graph-only;
Track B is Console-only — neither touches `python_sample`/`tiny_fixture` artifacts); `AGENT_BRIEF ≤5kb`;
the 5-artifact + 9-MCP-tool contract unchanged. **Per-step keystone proof:** Track A diffs touch only
`contracts/*`/`providers/*`/`resolver.py`/`reconcile_*`/`insights/*`/the graph adapter — never `trace`/
emit/`serve` query logic; **Track B diffs touch only `cli/style/*` + `cli.py` + `pyproject.toml` — never
`emit/*` or any machine-output path.** **Real-repo acceptance (matrix):** Step 1 → wagtail prefix
collapse resolved + a DRF-default-router repo's `@action`; Step 2 → an `@ApplicationPath`+`@Produces`
repo; Step 3 → a literal-key topic-exchange repo (EXTRACTED + DROP on real code); Step 4 → semantic
recall + decay + `--push` round-trip; Step 5 → Superset speedup, byte-identical; Steps 6–7 → TTY-styled /
pipe-plain on the acceptance repos, palette matches taxonomy. Findings under `docs/findings/v0.7/`. As
ever, an honest single-repo shortfall (reported, never fabricated) is an acceptable pass with the gap
promoted to v0.8 — v0.7 is expected to seed v0.8.

## §5 — Memory lanes (status after v0.7)
- **Lane (i) incremental/persistent graph update → v1.0** (unchanged; the v0.6 + v0.7 perf passes confirm
  no constant-factor win needs it). The last load-bearing fundamental for Terminal-complete v1.0, and the
  enabling prerequisite for both the future interactive Textual TUI and the GUI/IDE.
- **Lane (ii) temporal/Graphiti → opt-in-later** (unchanged; the single opt-in temporal backend).
- **Lane (iii) agent-facing write-back → extended in v0.7** (§3.4): semantic RRF (opt-in), a stdlib decay
  score, explicit shadow-ref push — all LLM-free.

## §6 — Surfaces (status after v0.7)
- **CLI (terminal):** styled in v0.7 (Track B) — the publish-facing surface, command-oriented.
- **`serve --ui` (web):** unchanged; machine/HTML output, no ANSI.
- **MCP server (9 tools):** unchanged; machine output, no ANSI.
- **Interactive Textual TUI (full-screen app):** **deferred** to its own arc (the "grow into Textual"
  path) — enabled, like the GUI/IDE, by v1.0 incremental update.
- **GUI/IDE (graphical/near-live):** **deferred** to its own research arc (v1.0+).

## §8 — Invariants (apply unchanged, plus §8.11 / §8.12)
1–10. As DEC-063 §8 (reuse `Endpoint`; confidence sacred; pure-static floor; no un-DEC'd dep; `symbol_id`
via `_parent_chain`; `base.join` untouched for new match shapes; no fabrication; graph-only edges /
byte-identical goldens / `AGENT_BRIEF ≤5kb`; frozen 9-tool/5-artifact contract; §8.10 dogfood lane-iii).
11. **The presentation keystone (§1b):** the style layer is Console-only; artifacts stay byte-identical
    plain markdown; no ANSI on any machine-output stream; degrade on non-TTY/`--plain`/`NO_COLOR`; no 6th
    artifact / 10th tool. The capability panel is **data-driven from the registries**, never a hardcoded
    list that could drift from the contract.
12. **No new transitive dependency.** v0.7's only dependency action is promoting the already-present
    transitive `rich` to an explicit pinned direct dep. `textual` and `[proto]` stay deferred.

## §9 — DEC pre-draft (the v0.7 ledger)
- **DEC-071** — v0.7 scope verdict (the two-track spine; §2). Write FIRST.
- **DEC-072** — Step 1 Django provider completion (§3.1).
- **DEC-073** — Step 2 JAX-RS completion (§3.2).
- **DEC-074** — Step 3 AMQP literal-key real-repo acceptance (§3.3).
- **DEC-075** — Step 4 memory lane-(iii) follow-ons (§3.4).
- **DEC-076** — Step 5 performance (§3.5).
- **DEC-077** — Step 6a `rich` promoted to explicit pinned direct dependency (§3.6).
- **DEC-078** — Step 6b the CLI style layer (`cli/style/`, palette, banner, capability panel) (§3.6).
- **DEC-079** — Step 7 styled command rendering (`extract`/`trace`/stats) (§3.7).

## §10 — Surfacing proof (the keystones held)
No extraction-surfacing change in v0.7: `trace`/HOTPATHS/`serve --ui` render the completed Django/JAX-RS
routes, the literal-key AMQP joins, and the enriched insights **for free** (all `Endpoint`/`ROUTES_TO`).
The only `mcp_server` touch remains the lane-(iii) `recall_insights` backend (§3.4 extends it, no
signature/tool change). Track B adds a parallel **presentation** surface (`cli/style/`) that *reads* the
graph and *renders* to the Console — it changes no extraction, no artifact, no machine output. The
interactive Textual TUI and the GUI/IDE stay deferred to their own arcs.

---

*A styled CLI is publish-prep polish of the existing terminal surface — not the deferred GUI/IDE, and not
the deferred full-screen Textual app. v0.7 adopts the Hermes **look** (banner + capability panel +
confidence-colored output via Rich) over command-oriented output; the interactive Textual app and the
graphical GUI/IDE wait for their own arcs, enabled by v1.0 incremental update. Style settled behavior;
don't start the interactive-TUI or GUI build yet.*
