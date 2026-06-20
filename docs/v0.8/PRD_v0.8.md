# PRD — forensic-deepdive v0.8 · build specification

> Binding spec for the build sequence in `KICKOFF.md §5`. Each step = one focused session producing
> one DEC. Every step states: **Goal · Keystone guard · Touch · Approach · Acceptance · Tests ·
> Done-gate.** "Touch" lists the only files a step should change — a diff outside it is a smell.
> Grounded in `DECISIONS.md` (through DEC-081), `docs/findings/v0.7/DEFERRED.md`, and `research.md`.

**Conventions.** "Byte-identical goldens" = the 5 artifact golden fixtures are unchanged unless the
step is explicitly in Track B (which re-baselines once at GATE B). "Keystone guard" names the
invariant the step must not breach. All paths are under `src/forensic_deepdive/` unless noted.

---

## Track B — Earn the trust (precision foundation)

The graph deepdive feeds to FastContext (and renders in `ARCHITECTURE.md`) must be precise, or the
usefulness number is unbelievable. These four steps are the already-diagnosed DEFERRED items — well
specified, independently correct, do first.

### DEC-083 — impact() precision: stop promoting same-file co-occurrence to CALLS
- **Goal.** `impact()` is high-recall / low-precision: on Iris-Nearby it returned 80 "upstream"
  symbols for `Message`, including `settings_screen` functions with **zero** `Message` references,
  because depth-2/3 buckets promote same-file co-occurrence to a CALLS edge (DEFERRED 7a;
  `mcp-tool-review.md`). Make it trustworthy as a *final* set, not just a candidate generator.
- **Keystone guard.** Confidence taxonomy (DEC-015) preserved; no new node type; `base.join`/`trace`
  untouched. This is a resolver/edge-quality change, not a schema change.
- **Touch.** `static/resolver.py` (or wherever CALLS edges are built — the same-file fallback tier);
  the surfacing layer for `impact` in `mcp_server/server.py`; `tests/`.
- **Approach.** Separate **"references"** (same-file co-occurrence, name-coincidence) from **true call
  edges**. Either (a) stop creating a CALLS edge from same-file co-occurrence and instead tag it a
  distinct lower-confidence relationship the surfacing layer can *optionally* include, or (b) keep the
  edge but mark it AMBIGUOUS and let `impact(min_confidence=…)` cap it out by default. Prefer (a) if it
  doesn't ripple into the join; (b) if it does. **The caller must be able to ask for the precise set
  (EXTRACTED/INFERRED true calls only) and get no settings_screen-class false positives.** Dart is the
  worst case (dynamic dispatch → class-to-class "CALLS" are really "references") — the fix should
  improve Dart specifically (DEFERRED 5, 7-Dart) without a full Dart resolver pass (that stays a v0.9
  seed).
- **Acceptance.** On the Iris-Nearby fixture (or a distilled regression fixture capturing the
  pattern), `impact(Message, min_confidence=INFERRED)` returns **zero** symbols with no real `Message`
  reference; the wide candidate set is still reachable at a lower confidence floor (recall preserved,
  precision recoverable). The two framings ("generate a blast-radius candidate set" vs "trust as final
  set") are both available and documented.
- **Tests.** A regression fixture asserting the false-positive class is gone at the default floor and
  recoverable below it; determinism preserved.
- **Done-gate.** Suite green; ruff clean; the precision claim is asserted, not narrated.

### DEC-084 — NL query() lexical ranking: exact name hits must win
- **Goal.** With `[semantic]` absent (`degraded:true`), `query("where are messages encoded/decoded")`
  returned theme/notification junk and **missed** `_encode/_decodeMessageWithMedia` — whose names
  literally contain "encode" (DEFERRED 7b; `mcp-tool-review.md`). For discovery there, grep beat the
  tool. Fix the lexical fallback and make the degraded state visible at the point of use.
- **Keystone guard.** DEC-038 (RRF fusion) / DEC-041 (FTS5/BM25) shape preserved; `recall`/`query`
  tool signatures unchanged; pure-static floor (the `[semantic]` tier stays opt-in, DEC-042).
- **Touch.** the NL query path (`query` shaping / ranking in `mcp_server/server.py` + the lexical
  index reader); `tests/`.
- **Approach.** An **exact function/symbol-name substring hit must outrank** unrelated symbols in the
  lexical+structural ranking — a name-match boost that floats `_encodeMessageWithMedia` above
  `ThemeProvider.toggleTheme` for a query containing "encode". Keep RRF for the rest. Surface
  `degraded:true` **at the point of use** (in the result payload's human-facing note), not only as a
  flag — "semantic tier not installed; lexical+structural only" so the caller knows when to distrust.
- **Acceptance.** The "encode/decode" probe (as a fixture) returns the real `_encode/_decode…` symbols
  in the top results in degraded mode; the degraded state is stated in the response.
- **Tests.** Fixture probe asserting exact-name hits rank first in degraded mode; the degraded note is
  present; semantic-on path (where available) still fuses via RRF.
- **Done-gate.** Suite green; ruff clean.

### DEC-085 — metric honesty + dedupe/self-cycle collapse
- **Goal.** Two honesty defects: (i) "AppColors: 383 inbound calls" vs 271 literal grep usages (~40%
  over) — the conclusion (most-central) is right, the **number isn't quotable** (DEFERRED 7c); (ii)
  `impact()`/`context()` returned the same symbol multiple times (`NearbyService ×4`) and `flow()`
  showed a `Message→Message` self-cycle artifact (DEFERRED 4).
- **Keystone guard.** Surfacing-layer change only; graph schema + confidence untouched; goldens for the
  5 artifacts handled at GATE B (HOTPATHS centrality wording may shift).
- **Touch.** the inbound-count computation + its emitter (likely `emit/hotpaths_md.py` or the centrality
  metric); the surfacing dedupe in `mcp_server/server.py`; `tests/`.
- **Approach.** Either **reconcile** the inbound count to a verifiable definition (count distinct
  call-sites / distinct caller symbols, matching what a grep would show) **or** label it explicitly an
  estimate ("≈383, structural in-degree incl. inferred"). Prefer reconcile if cheap. **Dedupe by
  `node_id`** in the surfacing layer (DEC-051's stable id is the key); **collapse trivial self-cycles**
  (`X→X`) in `flow()`.
- **Acceptance.** The inbound number matches its stated definition on a fixture (or is labelled an
  estimate); no duplicate `node_id` rows in `impact`/`context` output; no trivial self-cycle in
  `flow`.
- **Tests.** Count-definition fixture; dedupe assertion; self-cycle collapse assertion.
- **Done-gate.** Suite green; ruff clean.

### DEC-086 — low-history / solo-repo brief + archaeology quality
- **Goal.** On solo / low-history repos: AGENT_BRIEF's top "Always" rule was a centrality artifact
  (`AppColors`, a theme constant with 383 inbound — true but low-insight) and "Never" leaned on
  near-empty git signal (DEFERRED 1); ARCHAEOLOGY ownership/bus-factor is **vacuous at bus factor 1**
  (DEFERRED 2). The rules earn their keep only with real history + multiple authors.
- **Keystone guard.** AGENT_BRIEF ≤5kb (DEC-015 cap); confidence taxonomy; the 5-artifact contract
  (content changes, names/count/order do not). GATE B re-baselines goldens.
- **Touch.** `emit/agent_brief_md.py` (rule gating/re-ranking), `emit/archaeology_md.py` (ownership
  suppression + shallow-clone warning), the brief rule-ranking logic; `tests/`.
- **Approach.** (1) **Gate or re-rank** brief Never/Always rules below a history/contributor threshold;
  **prefer business-logic centrality over pure call-count**; **demote theme/constant hubs** (a hub
  that is a colour/constant table is low-insight even at high in-degree). (2) **Suppress or compress**
  the ARCHAEOLOGY ownership section below a contributor threshold (bus factor 1 → say so briefly,
  don't fabricate "who to ask"). (3) **Detect a shallow `.git`** (`--depth 1` collapses churn to 1)
  and **warn explicitly** in ARCHAEOLOGY rather than reporting degenerate churn as signal.
- **Acceptance.** On a solo/low-history fixture: the brief no longer surfaces a theme-constant hub as
  the headline Always rule; ARCHAEOLOGY states bus factor 1 honestly without a vacuous ownership table;
  a shallow clone produces a visible warning. AGENT_BRIEF still ≤5kb.
- **Tests.** Solo-repo fixture asserting hub demotion + ownership suppression + shallow-clone warning;
  `wc -c AGENT_BRIEF.md` ≤ 5120.
- **Done-gate.** Suite green; ruff clean. **▸ GATE B:** re-baseline the 5 goldens once with the diff
  documented in DEC-083…086's consequences; freeze again.

---

## Track A — Prove USEFUL (the publish gate)

### DEC-087 — FastContext usefulness experiment
- **Goal.** Produce the DEC-081 publish-blocker answer: a written, reproducible measurement of whether
  deepdive-seeded exploration localizes/resolves real issues measurably better than FastContext-alone,
  on a multi-author cross-stack benchmark. This is the spine of v0.8.
- **Keystone guard — the floor (DEC-009).** **No LLM, no network, no model dependency enters
  `src/forensic_deepdive/`.** Everything in this step lives under `experiments/fastcontext/` (or
  `benchmark/`) and is excluded from the wheel (DEC-088). deepdive's only contribution is a
  **pure-static, graph-derived seed string** built from existing graph queries. If you find yourself
  importing `openai` into `src/`, stop — that's the breach.
- **Touch.** NEW `experiments/fastcontext/` (harness, runners, the seed-builder that calls deepdive's
  *existing* graph API and emits a string); NO change to `src/` except possibly a thin, pure-static
  public helper that returns the seed payload (graph-only — hotpaths, candidate files, symbol
  locations, the `trace` slice) if one doesn't already compose from existing tools. `pyproject.toml`
  gets a `benchmark`/`experiment` dependency group (NOT a runtime dep, NOT shipped).
- **Approach (research.md Thread 1).**
  1. Clone `microsoft/fastcontext` (MIT) into `experiments/fastcontext/vendor/` or pin it as a
     `benchmark`-group git dep. Confirm the LICENSE in-tree.
  2. Stand up an OpenAI-compatible endpoint for **FC-4B-RL** (SGLang/vLLM:
     `--tool-call-parser qwen --context-length 262144 --dtype bfloat16`); set `BASE_URL`/`MODEL`/
     `API_KEY`. (4B is the intended deployment target; FC-4B-RL ties/beats FC-4B-SFT end-to-end.)
  3. Harness = **Mini-SWE-Agent** + a **SWE-bench Multilingual** subset (n chosen in §8 Q2; state n +
     seed). Needs Docker + a main-agent endpoint.
  4. **Two arms:** (A) FastContext-alone (the published baseline path —
     `bench_mini_swe_agent.py … --agent-config prompts/…-fc.yaml`); (B) **deepdive-seeded** — extract
     the target repo with deepdive first, build the seed string, inject it via the FastContext
     **query** and/or a **`system_prompt` override** (`make_fastcontext_agent(system_prompt=…)`).
  5. **Metrics:** file-level localization F1 (their standalone metric), end-to-end resolution rate, and
     main-agent token consumption (their headline +5.5 / −60.3% are the figures to complement/beat).
  6. **Build against `--citation`** (the shipped flag), not the doc's `--format concise` (a known
     doc/code discrepancy — research.md Thread 1 caveats). Don't assume literal tool-call concurrency.
- **Acceptance.** A committed `experiments/fastcontext/RESULTS.md` with: the n + seed, both arms'
  numbers, the seed-string spec, the exact reproduce command, and an honest verdict. **A positive,
  neutral, or negative result all satisfy the gate** — what's required is a *real measurement*, not a
  win. (Honest reporting, KICKOFF §3.7.)
- **Tests.** The seed-builder (pure-static) is unit-tested in the normal suite; the harness itself is
  experiment code (reproducibility documented, not CI-gated — the established CI-untested-by-design
  pattern for model-dependent paths, cf. DEC-042/075 semantic tier).
- **Done-gate. ▸ GATE A (THE PUBLISH GATE).** RESULTS.md exists and reproduces. If positive →
  publish unblocked + Option 2 (4th tool) becomes a v0.8 stretch / v0.9 head-of-line. If
  neutral/negative → documented; publish proceeds on assisted-analysis value with **no
  autonomous-execution overclaim**; seeding backlog → v0.9. Either way: write the DEC capturing the
  verdict and its consequence for the release claim.

---

## Track D — Distribution machinery (publish act deferred to DEC-092)

### DEC-088 — packaging: PyPI build wiring + CWD-independent serve
- **Goal.** Make `forensic-deepdive` install like any package (`uv tool install` / `uvx` / `pipx` /
  `pip`) with the `forensic` binary on PATH, the vendored UI assets in the wheel, extras working, and
  `serve --repo` runnable from any directory. (DEFERRED 6.)
- **Keystone guard.** DEC-010 (name `forensic-deepdive`, binary `forensic`); no runtime behavior
  change; experiment code excluded from the wheel.
- **Touch.** `pyproject.toml`; possibly `mcp_server`/`serve` asset-loading to use
  `importlib.resources`; CI workflow files; docs.
- **Approach (research.md Thread 2).**
  - `[project.scripts] forensic = "forensic_deepdive.cli:app"`.
  - `[project.optional-dependencies]` for `graphiti` / `semantic` / `openapi` / `dev` (+ a
    `benchmark`/`experiment` group that is **not** shipped).
  - hatchling `[tool.hatch.build.targets.wheel.force-include]` (or `artifacts`) mapping the vendored
    Sigma.js/graphology/CSS/HTML (and any data files) into the package; load at runtime via
    `importlib.resources.files("forensic_deepdive") / …` (not `__file__` path math).
  - **Verify wheel availability** for LadybugDB + `tree-sitter-language-pack` on **Linux / macOS-arm64
    / Windows** *before* hard-depending. **Fallback (§8 Q5):** if LadybugDB lacks a platform wheel,
    make the graph engine an optional extra with a degraded pure-markdown default so `pip install`
    never fails.
  - TestPyPI dry-run; inspect the **built wheel** contents (don't trust editable installs — the
    hatchling force-include regression #1130 hides in editable mode).
  - The CWD-independent serve: document `uvx forensic-deepdive serve --repo <path>` and
    `uv tool install forensic-deepdive` (puts `forensic` in `~/.local/bin`); `--repo` makes the target
    explicit so CWD never matters.
- **Acceptance.** `uv build` produces an sdist + wheel; the wheel contains the UI assets (verified);
  a TestPyPI install in a clean env exposes `forensic` on PATH and `forensic info` runs; extras install
  cleanly; wheels validated on the 3 platforms (or the documented fallback engaged).
- **Tests.** A packaging smoke test (assets resolve via `importlib.resources`; entry point imports);
  CI matrix builds/installs on the 3 platforms.
- **Done-gate.** Build + TestPyPI dry-run pass; suite green; ruff clean. **No `uv publish` to real
  PyPI here** — that is DEC-092, gated on GATE A.

### DEC-089 — MCP distribution: registry + plugin + install docs
- **Goal.** Make the MCP server discoverable and one-command installable across the major agents.
  (DEFERRED 6.)
- **Keystone guard.** The 9-tool contract frozen (the registry/plugin *advertise* it, don't change it);
  DEC-031 (skill emission + plugin manifest) extended, not contradicted.
- **Touch.** NEW `server.json` (MCP Registry); README (the `mcp-name` marker); NEW
  `.claude-plugin/plugin.json` + a plugin `.mcp.json`; install docs (README or `docs/install.md`); CI
  (OIDC for `mcp-publisher` if automated).
- **Approach (research.md Thread 3).**
  - Add `<!-- mcp-name: io.github.<user>/forensic-deepdive -->` to the README (proves PyPI ownership to
    the registry).
  - `mcp-publisher init` → edit `server.json`
    (`packages: [{registryType:"pypi", identifier:"forensic-deepdive", version, transport:{type:"stdio"}}]`)
    → `mcp-publisher login github` → `publish`. (Run **after** DEC-092 puts the package on PyPI.)
  - Claude Code plugin: `.claude-plugin/plugin.json` (only `name` required) at the plugin root, with a
    **separate** `.mcp.json` referencing `command:"uvx", args:["forensic-deepdive","serve","--repo","."]`
    (inline `mcpServers` in plugin.json has a known bug — use the separate file). Component dirs are
    siblings of `.claude-plugin/`, not inside it.
  - Copy-paste install blocks for **Claude Code** (`claude mcp add` + `.mcp.json`), **Cursor**
    (`.cursor/mcp.json`), **VS Code** (`servers` key), **Codex** (`config.toml`) — all using
    `uvx forensic-deepdive serve --repo <path>`. Document the absolute-path fallback for GUI apps
    (Claude Desktop) that don't inherit shell PATH (a common ENOENT cause).
- **Acceptance.** `server.json` validates; the plugin installs in a real Claude Code session and
  registers all 9 tools; the per-client install blocks are copy-paste-correct (spot-checked).
- **Tests.** A `server.json` schema/lint check; the plugin manifest validated; docs reviewed.
- **Done-gate.** Suite green; ruff clean. Registry **publish** action deferred until the package is on
  PyPI (post-DEC-092).

---

## Track C — Human validation surface

### DEC-090 — ARCHITECTURE.md emitter + `forensic diagram`
- **Goal.** A human-facing, system-level architecture view that updates on every extract and lets a
  person **validate** the graph (catch the false-positives/inflated counts the precision work targets).
  The new feat, scoped as a **separate surface, not a 6th artifact** (KICKOFF §6).
- **Keystone guard — the big one.** The **5-artifact contract is frozen** (CLAUDE.md sacred
  abstraction). `ARCHITECTURE.md` is **NOT** one of the five: their goldens stay **byte-identical**;
  AGENT_BRIEF ≤5kb is untouched (the diagram is not folded in); `base.join`/`trace`/`serve`/`emit/*`
  for the five are untouched. No `protocol==` branch in any surfacing layer (DEC-043/055). No new node
  type. This mirrors DEC-039 (Mermaid `visualize`) and DEC-053 (`serve --ui`) precisely.
- **Touch.** NEW `emit/architecture_md.py` (the system diagram renderer) reusing `emit/mermaid.py`
  (DEC-039) for the confidence→dash mapping + node-cap; `cli/app.py` (`forensic diagram` + wiring into
  `extract` to regenerate it); a NEW golden fixture for `ARCHITECTURE.md`; `tests/`. README (document
  the new surface + that it is not part of the contract).
- **Approach.** Render a **bounded system-level Mermaid** from the existing graph: **services /
  modules** as clusters, **Endpoints** as the cross-boundary join nodes, the **ROUTES_TO / INJECTS /
  PERSISTS_TO** edges, **DbTable** stores — confidence-styled via the DEC-039 dash mapping (EXTRACTED
  solid / INFERRED dashed / AMBIGUOUS dotted), with a legend. Node-cap + **summarize-and-truncate**
  (never silent-drop, DEC-039). **Altitude default (§8 Q3):** one bounded system diagram + a textual
  legend; layered per-service is a follow-on. **Location (§8 Q4):** decide and document; mark the file
  clearly as not-part-of-the-5-contract wherever it lands. Regenerated on `extract` like the five, but
  separately golden-tested. cp1252 ASCII-degrade applies to any new console output (DEC-078/080).
- **Acceptance.** `forensic diagram --repo <r>` and `forensic extract <r>` both produce
  `ARCHITECTURE.md`; it renders in GitHub/Claude Code/Obsidian; it carries confidence styling + legend;
  it bounds + summarizes large graphs; the **5 artifact goldens are byte-identical**; the new file has
  its own golden.
- **Tests.** `tests/test_architecture.py`: golden for a small cross-stack fixture (spring_react_demo
  class), confidence→dash mapping asserted, node-cap summarize-and-truncate, determinism (two renders
  byte-identical); a guard asserting the 5 artifact goldens are unchanged.
- **Done-gate.** Suite green; ruff clean; `wc -c AGENT_BRIEF.md` ≤ 5120 (unchanged).

### DEC-091 — CLI round-out / ergonomics
- **Goal.** Close the remaining onboarding/ergonomics gaps so the published CLI is clean. (DEFERRED
  7-shims, 6, 7d.)
- **Keystone guard.** CLI-surface only; engine/graph/contract untouched; cp1252 degrade rule on every
  new glyph path (DEC-078/080).
- **Touch.** `cli/app.py`, `emit/shims.py`, possibly `cli/style/`; `tests/`.
- **Approach.** (1) **`--refresh-shims`** (or a content-hash check) so a stale Deepdive-generated
  `CLAUDE.md`/`AGENTS.md` is rewritten instead of surviving write-if-absent (DEFERRED 7-shims).
  (2) A **`forensic mcp-config <repo>`** helper that prints the correct client snippet (DEFERRED 6).
  (3) **Per-tool applicability self-notes** — e.g. `trace` self-noting "no HTTP/ORM endpoints in this
  graph" on a P2P/non-web repo so it isn't dead-weight noise (DEFERRED 7d).
- **Acceptance.** Stale shims refresh on demand; the mcp-config helper prints a valid snippet; `trace`
  self-notes inapplicability on a non-web fixture.
- **Tests.** Shim-refresh regression; mcp-config output validity; trace self-note assertion.
- **Done-gate.** Suite green; ruff clean.

---

## Track D — The release act (gated)

### DEC-092 — v0.8.0 public release
- **Goal.** Ship to PyPI + register the MCP server + submit the plugin.
- **HARD PRECONDITION.** **GATE A satisfied** (a real Q2 measurement exists, DEC-087) **AND** full
  suite green at 0.8.0 **AND** TestPyPI dry-run passed (DEC-088) **AND** wheels validated on Linux /
  macOS-arm64 / Windows **AND** `MANUAL_TEST.md` re-run for `forensic diagram` + the install path.
- **Keystone guard.** Never push/publish without explicit user authorization (CLAUDE.md). Goldens
  byte-identical except the version footers (the DEC-081 precedent: bump the 5 golden-emit footers to
  track the shipped version).
- **Touch.** `pyproject.toml` (version 0.7.0 → 0.8.0) + the `__init__.py` source-tree fallback;
  the 5 golden-emit footers; `CHANGELOG.md` (`[0.8.0]`); README status line; the release CI workflow.
- **Approach (research.md Thread 2a–b, f).** Tag-triggered GitHub Actions release (`environment: pypi`,
  `permissions: id-token: write`, `astral-sh/setup-uv`, `uv build` → `uv publish` via **OIDC Trusted
  Publishing**, no tokens). SemVer; git tag `v0.8.0`; CHANGELOG entry. After PyPI lands:
  `mcp-publisher publish` the `server.json` (DEC-089); submit the Claude Code plugin to the marketplace.
- **Acceptance.** `pip install forensic-deepdive` from real PyPI in a clean env exposes `forensic`,
  runs `forensic info`, and `uvx forensic-deepdive serve --repo .` starts; the server appears in the
  MCP Registry; the release claim matches the GATE A verdict (no Q2 overclaim if neutral/negative).
- **Tests.** Post-publish smoke (clean-env install + `forensic info` + `serve` bind).
- **Done-gate.** Released with explicit user authorization; PROGRESS + a DEC capturing the release +
  the GATE A verdict + what was/wasn't claimed.

---

## Track E — Stretch (capacity-gated; only after A/B/D/C land)

### DEC-093 — protocol carryover
- **Goal.** Clear the open protocol seeds, real-repo-demand-gated. (DEFERRED 9, 10, 11.)
- **Keystone guard.** **Reuse the `Endpoint` node; a new protocol = a `KeyBuilder` + provider/consumer
  extractors only — never touch `trace`/emit/`serve`** (DEC-043/055). No new node type.
- **Touch.** `contracts/<proto>/` + `contracts/registry.py` + the register-wire in
  `pipeline/phases.py::ContractPhase.run` + `tests/`.
- **Approach.** (a) **gRPC Go/Java** servicer/stub shapes + the wire-path equivalence
  `/<package>.<Service>/<Method>` (needs the deferred `[proto]` extra; attribute-bound stubs) —
  DEC-068 CAVEAT. (b) **AMQP DROP** co-located non-match pair + **Spring AMQP `@RabbitListener` /
  `@QueueBinding(key=)`** extraction (currently only `@KafkaListener` + pika) — DEC-074 / DEFERRED 10.
  (c) **DRF `DefaultRouter`/`SimpleRouter` at scale** on a real repo — DEFERRED 11.
- **Acceptance.** Each landed sub-item is fixture-proven + real-repo-validated with confidence tags,
  or honestly deferred again with the finding recorded. Pick by real-repo demand; don't add all three
  speculatively (non-goal: no sixth protocol without demand).
- **Done-gate.** Per landed sub-item: suite green; ruff clean; findings doc under
  `docs/findings/v0.8/`.

### DEC-094 — Obsidian vault emission (`--emit-vault`)
- **Goal.** Opt-in emission of the existing artifacts as an Obsidian-friendly vault — local-first
  markdown brain for humans + agents. (research.md Thread 4; KICKOFF §6.)
- **Keystone guard.** Opt-in only (no default behavior change); the 5 artifact goldens byte-identical
  when the flag is off; no new runtime dependency (pure markdown transform).
- **Touch.** NEW `emit/vault.py` (the transform); `cli/app.py` (`--emit-vault` flag); `tests/`.
- **Approach (research.md Thread 4b, d, e).** A serialization pass over existing outputs: add
  `.obsidian/` (default config), give every page **YAML frontmatter** (`summary:` + `tags:` +
  `status:`), normalize existing `[[wikilink]]`s to real page names, add a **MOC index** page, and —
  for agent-friendliness — a `summary:` on every page + **provenance links to source file:line**.
  Optionally a `.canvas`. Small effort (a few days); defer to v0.9 without guilt if the cycle is full.
- **Acceptance.** `forensic extract --emit-vault <r>` produces a folder that opens cleanly in Obsidian
  (graph view populated from wikilinks; frontmatter parses; MOC traversable); the flag-off path is
  byte-identical to today.
- **Tests.** Vault-emission fixture (frontmatter parses, wikilinks resolve to real pages, MOC links
  valid); flag-off byte-identical guard.
- **Done-gate.** Suite green; ruff clean.

---

## Appendix — DEFERRED ledger → DEC mapping (traceability)

| DEFERRED item | Addressed by |
|---|---|
| 1 (brief Never/Always thin on low-history) | DEC-086 |
| 2 (archaeology ownership empty solo; shallow-clone) | DEC-086 |
| 3 (serialization-boundary blind spot) | partial in DEC-083 (references vs calls); full heuristic = v0.9 seed |
| 4 (dup rows + self-cycles) | DEC-085 |
| 5 (Dart mostly INFERRED) | partial in DEC-083; full Dart resolver pass = v0.9 seed |
| 6 (MCP launch ergonomics; uv tool install; mcp-config helper) | DEC-088 + DEC-089 + DEC-091 |
| 7 (shim regen no force) | DEC-091 |
| 7a (impact over-scopes) | DEC-083 |
| 7b (NL lexical ranking misses obvious) | DEC-084 |
| 7c (inbound-count opaque/inflated) | DEC-085 |
| 7d (per-tool applicability hints) | DEC-091 |
| 8 (autonomous usefulness Q2 — THE publish gate) | **DEC-087** |
| 9 (gRPC Go/Java) | DEC-093 |
| 10 (AMQP DROP + Spring @QueueBinding) | DEC-093 |
| 11 (DRF DefaultRouter at scale) | DEC-093 |
| 12 (LadybugDB prepared-statement reuse) | stays deferred (deprecated upstream; DEC-076) |
| v1.0 lane (i) incremental update | stays v1.0 (out of scope, KICKOFF §7) |
| v1.0 GUI/IDE | stays v1.0+ (gated on GATE A even if positive) |

*New v0.8 work not in the v0.7 DEFERRED ledger (the feats brought to the v0.8 ideation): FastContext
integration (DEC-087, frames the answer to ledger item 8), `ARCHITECTURE.md` (DEC-090), public PyPI +
MCP distribution (DEC-088/089/092), Obsidian vault (DEC-094).*
