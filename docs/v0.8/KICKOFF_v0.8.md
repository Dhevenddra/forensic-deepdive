# KICKOFF — forensic-deepdive v0.8 · "USABLE → USEFUL + Public Release"

> Companion docs in this folder: `PRD.md` (per-step build spec + acceptance gates) and
> `research.md` (FastContext internals, PyPI/uv/hatchling flow, MCP distribution, Obsidian).
> **Read all three before writing code. Then read `CLAUDE.md` → `DECISIONS.md` → `PROGRESS.md`
> per the session-start protocol.** This KICKOFF is the binding scope; the PRD is the binding spec.

---

## §0 — Read-first (the session protocol still governs)

This release does **not** suspend any standing discipline. Before any code:

1. `CLAUDE.md` (the invariants).
2. `DECISIONS.md` — **you are bound by every `Status: Active` DEC through DEC-081.** Disagree only by
   writing a superseding entry first.
3. `PROGRESS.md` — know what's done and what's next.
4. `git log --oneline -10`.
5. Confirm in one sentence: *"Working on <next PRD step>, respecting DEC-N about <X>."*

The v0.8 DEC range is **DEC-082 … DEC-094** (pre-assigned in §11; split/merge as the build demands,
but never reuse or skip a committed number).

---

## §1 — The verdict (scope, in one paragraph)

v0.8 is the release that turns the honest v0.7 gate result — *usable and onboarding-proven, but
**autonomous end-to-end usefulness UNPROVEN*** (DEC-081, the publish blocker) — into a **measured
"USEFUL" result** and then ships forensic-deepdive as a real, installable public package. The spine
is a **FastContext-grounded usefulness experiment** (Microsoft's MIT-licensed repository-exploration
subagent — see `research.md` Thread 1) that gives us, for the first time, a published baseline, a real
multi-author cross-stack benchmark harness (SWE-bench Multilingual/Pro under Mini-SWE-Agent), and a
head-to-head number: *does seeding/augmenting an exploration agent with deepdive's graph make it
localize and resolve real issues measurably better?* Around that spine we **earn the trust the number
needs** (graph-precision work from the DEFERRED ledger), **add the human-facing validation surface**
(an `ARCHITECTURE.md` diagram output + CLI round-out), and **build the distribution machinery** (PyPI
via uv + hatchling, the official MCP Registry, a Claude Code plugin). The public release act is the
**last** step and is **gated on the usefulness proof landing green** — exactly as DEC-081 mandates.

---

## §2 — North star and the single gate

**North star:** every choice is judged against one question — *does an AI agent finish real
end-to-end work better (faster / fewer tokens / safer / more accurately localized) **because of**
deepdive?*

**The one gate that unlocks publish (DEC-081):** a dedicated autonomous-execution measurement on a
large, multi-author, statically-typed, cross-stack repo set — **not** a solo BLE app. v0.8 satisfies
this by adopting FastContext's own evaluation harness and measuring deepdive-seeded exploration
against the published FastContext-alone baseline (`research.md` Thread 1e). Until that measurement
exists and is positive (or honestly negative-and-documented), **`uv publish` does not run.**

---

## §3 — Keystones and hard constraints (do not violate; each is an active DEC)

These are non-negotiable. A change that needs to break one needs a superseding DEC and an explicit
argument — not a quiet edit.

1. **The pure-static, zero-LLM, zero-network floor (DEC-009).** `forensic extract` and every shipped
   tool work with no API key, no Ollama, no network. **This is the identity of the product and the
   single biggest constraint on the FastContext work.** Consequence for v0.8: **the LLM lives in the
   *experiment harness*, never in deepdive's runtime.** deepdive's contribution to FastContext is a
   *pure-static graph-derived string* (hotpaths, candidate files, symbol locations, the cross-stack
   trace); the model endpoint that consumes it is external and lives only in `experiments/` /
   `benchmark/`. **Adding an LLM call to any `src/forensic_deepdive/` runtime path is a floor breach.**

2. **The 5-artifact contract is frozen and is the public API (CLAUDE.md "Sacred abstractions").**
   `MAP` / `HOTPATHS` / `ARCHAEOLOGY` / `MENTAL_MODEL` / `AGENT_BRIEF` — names, count, order. The new
   `ARCHITECTURE.md` (§6) is **NOT a sixth artifact.** It is a *separate on-demand surface*, exactly
   as DEC-039 (Mermaid `visualize`) and DEC-053 (`serve --ui`) are separate surfaces — the five
   artifact goldens stay **byte-identical** when the diagram is added.

3. **AGENT_BRIEF.md ≤ 5 kb hard cap.** The diagram, the vault, nothing new spends this budget.
   `ARCHITECTURE.md` is read by humans, not folded into AGENT_BRIEF.

4. **The `Endpoint` / `base.join` keystone (DEC-043/055).** Five protocols share **one** `Endpoint`
   join node + the protocol-blind `base.join`. The architecture diagram **reads** this graph; it must
   not add a `protocol==` branch to any surfacing layer, and must not touch `trace`/emit/`serve`. The
   `DbTable` node (DEC-059) remains the one DEC'd new-node exception — **no new node types in v0.8.**

5. **Confidence taxonomy on every edge and every emitted claim (DEC-015).** EXTRACTED / INFERRED /
   AMBIGUOUS, never colour-alone (DEC-078). The architecture diagram **must** carry it (it is the
   human-validation lever); the precision work **must** preserve it.

6. **Determinism + byte-identical goldens.** Every step that isn't *meant* to change emitted artifacts
   proves it with byte-identical goldens (the v0.7 discipline). The diagram gets its **own** golden;
   the five stay frozen.

7. **Honest reporting, never fabrication (the project's load-bearing value).** A negative FastContext
   result is reported as a negative result and reshapes the plan — it is **not** massaged into a win.
   A precision fix that doesn't pan out is documented and deferred. This is the value that the whole
   confidence taxonomy exists to serve; the publish decision depends on it.

8. **Never push without explicit instruction. Never merge without `uv run pytest -x` green + `ruff`
   clean. Append to PROGRESS at session end; write a DEC for every architectural choice.**

---

## §4 — The five tracks

| Track | Name | What it delivers | DECs |
|---|---|---|---|
| **A** | **Prove USEFUL** (the gate) | FastContext harness + deepdive-seeded exploration + the head-to-head Q2 number | DEC-087 |
| **B** | **Earn the trust** | Graph-precision fixes from the DEFERRED ledger so the graph deepdive feeds is trustworthy, not just suggestive | DEC-083–086 |
| **C** | **Human validation surface** | `ARCHITECTURE.md` diagram output + `forensic diagram` + CLI round-out | DEC-090, DEC-091 |
| **D** | **Ship it** | PyPI (uv + hatchling, OIDC), MCP Registry, Claude Code plugin, CWD-independent `uvx serve` | DEC-088, DEC-089, DEC-092 |
| **E** | **Carryover + stretch** | Protocol seeds (gRPC Go/Java, AMQP DROP + Spring `@QueueBinding`, DRF at scale) + optional Obsidian vault | DEC-093, DEC-094 |

Priority order is **A > B > D-engineering > C > D-release > E**, but the *build sequence* (§5) puts
**B before A** deliberately: a precision win is what makes the seeding experiment fair and the result
believable. Track B's first pass is the well-specified, already-diagnosed DEFERRED items; a second
precision backlog falls out of what the experiment reveals and seeds v0.9.

---

## §5 — Build sequence (DEC order ≈ build order)

Each step is one focused session: a DEC entry, the implementation, the test, the PROGRESS append.
The PRD gives the full spec + acceptance gate per step. **Gates** below are hard stops.

```
DEC-082  Scope verdict (this KICKOFF, formalized). No code.
         ──────────────────────────────────────────────── Track B: precision foundation
DEC-083  impact() precision — stop promoting same-file co-occurrence to CALLS;
         separate "references" from true call edges; let callers cap by confidence.   [DEFERRED 7a, 3-part of 4]
DEC-084  NL query() lexical ranking — exact function-name substring must outrank
         unrelated symbols; surface degraded:true at the point of use.                [DEFERRED 7b]
DEC-085  Metric honesty — reconcile/define the "inbound calls" count to a verifiable
         number (or label it an estimate); dedupe symbol rows + collapse self-cycles
         in the surfacing layer.                                                       [DEFERRED 7c, 4]
DEC-086  Low-history / solo-repo quality — gate AGENT_BRIEF Never/Always rules below a
         history/contributor threshold, demote theme/constant hubs, suppress empty
         ARCHAEOLOGY ownership, warn on shallow (`--depth 1`) clones.                  [DEFERRED 1, 2]
   ▸ GATE B: precision suite green; goldens for the 5 artifacts re-baselined ONCE with
     a documented diff (these steps intentionally change emitted content) and frozen again.
         ──────────────────────────────────────────────── Track A: the proof (the publish gate)
DEC-087  FastContext usefulness experiment — clone fastcontext (MIT) into experiments/;
         stand up an FC-4B-RL OpenAI-compatible endpoint; run Mini-SWE-Agent + a
         SWE-bench Multilingual subset; baseline FastContext-alone vs deepdive-SEEDED
         (Option 1: graph-derived query/system-prompt seeding — research.md Thread 1g).
         Measure file-level localization F1, end-to-end resolution, main-agent tokens.
   ▸ GATE A (THE PUBLISH GATE): a written, reproducible result. If seeding measurably
     helps → Q2 answered positive → publish unblocked, and graduate toward Option 2
     (deepdive as a 4th FastContext tool) as a v0.8 stretch or v0.9 head-of-line.
     If neutral/negative → document honestly; publish proceeds on the ASSISTED-analysis
     value (the strong Q1/Q4 result) with NO autonomous-execution overclaim, and the
     seeding backlog moves to v0.9. Either way the gate is *satisfied by a real measurement*.
         ──────────────────────────────────────────────── Track D: distribution machinery (publish act deferred)
DEC-088  Packaging — [project.scripts] forensic entrypoint; [project.optional-dependencies]
         extras; hatchling force-include for the vendored Sigma.js/graphology/CSS/HTML;
         importlib.resources runtime access; TestPyPI dry-run; cross-platform wheel
         validation (Linux / macOS-arm64 / Windows); the uv tool install / uvx
         CWD-independent `serve --repo` path.                                          [DEFERRED 6]
DEC-089  MCP distribution — official MCP Registry server.json + mcp-publisher + README
         mcp-name marker; Claude Code plugin (.claude-plugin/plugin.json + .mcp.json);
         copy-paste install docs for Claude Code / Cursor / VS Code / Codex.           [DEFERRED 6]
         ──────────────────────────────────────────────── Track C: human validation surface
DEC-090  ARCHITECTURE.md emitter + `forensic diagram` — a SEPARATE surface (not the 6th
         artifact), regenerated on extract, reusing the DEC-039 Mermaid engine + the
         Endpoint/ROUTES_TO/INJECTS/PERSISTS_TO/DbTable cross-stack graph, confidence-
         styled, with its OWN golden. The 5 artifact goldens stay byte-identical.
DEC-091  CLI round-out — close the remaining ergonomics gaps (shim --refresh-shims,
         tool applicability self-notes, mcp-config helper, any DEFERRED ergonomics).   [DEFERRED 7-shims, 6, 7d]
         ──────────────────────────────────────────────── Track D: the release act (gated)
DEC-092  v0.8.0 public release — version bump, CHANGELOG, golden footers, tag, and
         `uv publish` via OIDC; register in the MCP Registry; submit the plugin.
   ▸ HARD PRECONDITION: GATE A satisfied (a real Q2 measurement exists) AND the full
     suite green at 0.8.0 AND TestPyPI dry-run passed AND wheels validated on 3 platforms.
         ──────────────────────────────────────────────── Track E: stretch (capacity-gated)
DEC-093  Protocol carryover — gRPC Go/Java servicer/stub shapes; AMQP DROP co-located
         pair + Spring AMQP @RabbitListener/@QueueBinding; DRF DefaultRouter at scale.  [DEFERRED 9, 10, 11]
DEC-094  Obsidian vault emission — opt-in `--emit-vault`: frontmatter (summary:/tags:),
         normalized wikilinks, .obsidian/ default config, a MOC index. Small transform. [research.md Thread 4]
```

---

## §6 — The three new feats (how each is scoped, and why)

### FastContext — integrate, do **not** reverse-engineer (Track A, DEC-087)
FastContext is MIT-licensed (repo + weights), Python 3.12+, and exposes a generic list-driven
`ToolSet`, an OpenAI-compatible CLI/library/subprocess contract, and a `system_prompt` override seam
(`research.md` Thread 1). It is **not** an MCP server — it calls a model endpoint and returns
`<final_answer>` file:line citations. Reverse-engineering it means retraining a 4–30B RL model (their
moat) and putting an LLM in our core (floor breach). So we **integrate**, lowest-effort path first:

- **Option 1 (DEC-087, the build):** deepdive generates a pure-static, graph-derived **seed string**
  (hotpaths + candidate files + symbol locations + the cross-stack `trace`) and injects it via the
  FastContext **query** and/or **`system_prompt` override**. This tests the core hypothesis with zero
  fork and zero floor risk.
- **Option 2 (stretch / v0.9):** add a `DeepdiveQueryTool(Tool)` to FastContext's `ToolSet([...])`
  list so the explorer can *call* deepdive's graph mid-exploration. Only if Option 1's number is
  positive.

The LLM/endpoint/Docker/SWE-bench all live in `experiments/fastcontext/` (or `benchmark/`), isolated
from `src/`. deepdive stays zero-LLM. The dogfood: run deepdive **on** the fastcontext repo while
using fastcontext's **methodology** on deepdive.

### Architecture diagrams — a 6th *output*, never a 6th *artifact* (Track C, DEC-090)
The 5-artifact contract is frozen (§3.2), and DEC-039/DEC-053 set the exact precedent: diagrams and
the graph UI are **separate on-demand surfaces** that leave the five goldens byte-identical.
`ARCHITECTURE.md` follows that precedent precisely — a human-facing, system-level Mermaid view
(services, Endpoints, the cross-boundary ROUTES_TO/INJECTS/PERSISTS_TO edges, DbTable stores),
confidence-styled (the DEC-039 dash mapping), regenerated on every `extract`, with its **own** golden
and test. It is explicitly a **trust / validation** surface: a reviewable architecture is precisely
how a human catches the graph lying (the impact() false-positives, the inflated counts) — so it
*serves* the north star, it isn't decoration. Comcast's narrower internal version is the demand
signal. The engine is mostly DEC-039 already.

### Obsidian brain — real seam, third priority, scope-controlled (Track E, DEC-094)
The seam is genuine and cheap: artifacts are already markdown, DECISIONS.md already uses `[[wikilink]]`
syntax, and the insight layer (DEC-019) is already backlink-shaped. Research confirms it is a **small
transform**, not a feature (`research.md` Thread 4e): frontmatter + normalized wikilinks + `.obsidian/`
+ a MOC index, behind an opt-in `--emit-vault`. But it is a *human knowledge-management* surface — the
least connected of the three to "does an agent finish real work better" — so it lands **only after** A,
B, D, C, and slides to v0.9 without guilt if the cycle fills.

---

## §7 — What's explicitly OUT (non-goals; do not regress, per DEFERRED)

- **No sixth protocol** without real-repo demand. **No new node type** (DbTable/DEC-059 remains the one
  exception). The **5-artifact + 9-MCP-tool contract is frozen.**
- **No LLM, no network in `src/` runtime.** Pure-static floor holds. (The experiment harness is not
  `src/`.)
- **No GUI/IDE build.** The v0.7 usability gate explicitly blocks UI work until autonomous value is
  demonstrated; even if GATE A is positive, the IDE is its own complete research arc (DEFERRED v1.0
  fundamentals), not v0.8.
- **No incremental/persistent graph update** — that is the v1.0 fundamental (DEC-051's line-free
  node_id is its seam); v0.8 stays full-extract.
- **No dependency on a deprecated upstream API** — the LadybugDB prepared-statement reuse stays
  deferred (DEC-076 / DEFERRED 12).
- The cp1252 ASCII-degrade rule (DEC-078/080) covers **every** new console glyph path the diagram or
  CLI round-out introduces.

---

## §8 — Open design questions delegated to Claude Code

These are genuinely open; decide them during the build and record the call as a DEC.

1. **Seed shape (DEC-087).** What exactly goes in the FastContext seed string, and in the query vs the
   `system_prompt` override? Start minimal (top-N hotpaths + the candidate files for the issue text)
   and ablate. How is the issue text mapped to a deepdive query without an LLM (lexical? the NL
   query() path post-DEC-084?)?
2. **Benchmark subset size (DEC-087).** SWE-bench Multilingual is 300 instances; pick a subset that is
   statistically meaningful but runnable on available compute, and state the n and the seed.
3. **`ARCHITECTURE.md` altitude (DEC-090).** System-level only (services + Endpoints + data stores), or
   a layered set (system + per-service)? Default to one bounded system diagram + a textual legend;
   keep it Mermaid so it renders in GitHub/Claude Code/Obsidian. Node-cap + summarize-and-truncate per
   DEC-039 (never silent-drop).
4. **Diagram location (DEC-090).** `docs/codebase/ARCHITECTURE.md` (sibling to the five, clearly marked
   not-part-of-the-contract) vs a distinct path. Pick the one that least invites contract confusion;
   document it in the DEC and the README.
5. **Packaging fallback (DEC-088).** If LadybugDB lacks a macOS-arm64 or Windows wheel, make the graph
   engine an optional extra with a degraded pure-markdown default so `pip install forensic-deepdive`
   never fails on a platform. Verify wheels **before** hard-depending (`research.md` Thread 2g).
6. **Obsidian agent-friendliness (DEC-094).** If built, every page gets a `summary:` frontmatter field
   and provenance links to source file:line (the agent-friendly delta from `research.md` Thread 4d).

---

## §9 — Mandatory gates (carried discipline + the publish gate)

- **Per-step:** `uv run pytest -x` green, `ruff check` clean, the test written alongside, PROGRESS
  appended, a DEC entry for the architectural choice.
- **GATE B (after DEC-086):** the precision steps *intentionally* change emitted content — re-baseline
  the 5 goldens **once**, with the diff documented in the DEC, then freeze again. Every later step is
  byte-identical against the new baseline.
- **GATE A (after DEC-087) — THE PUBLISH GATE:** a written, reproducible Q2 measurement exists. This is
  the DEC-081 blocker; nothing in Track D-release proceeds without it.
- **Pre-release (DEC-092):** TestPyPI dry-run passed; wheels validated on Linux / macOS-arm64 /
  Windows; full suite green at 0.8.0; CHANGELOG + golden footers bumped; `MANUAL_TEST.md` re-run for
  the new `forensic diagram` command + the install path. Then, and only then, `uv publish` — **with
  explicit user authorization for the push/publish, as always.**

---

## §10 — DEC pre-assignment

| DEC | Title (planning) | Track | Gate |
|---|---|---|---|
| 082 | v0.8 scope verdict | — | — |
| 083 | impact() precision — same-file co-occurrence demotion; references vs calls | B | |
| 084 | NL query() lexical ranking + degraded-at-point-of-use | B | |
| 085 | metric honesty (inbound count) + dedupe/self-cycle collapse | B | |
| 086 | low-history/solo-repo brief + archaeology quality + shallow-clone warn | B | **B** |
| 087 | FastContext usefulness experiment (Option-1 seeding; SWE-bench harness) | A | **A (publish gate)** |
| 088 | packaging — PyPI build wiring + uvx CWD-independent serve | D | |
| 089 | MCP distribution — registry + plugin + install docs | D | |
| 090 | ARCHITECTURE.md + `forensic diagram` (separate surface) | C | |
| 091 | CLI round-out / ergonomics | C | |
| 092 | v0.8.0 public release (version, CHANGELOG, tag, publish) | D | **pre-release** |
| 093 | stretch — protocol carryover (gRPC Go/Java; AMQP DROP + @QueueBinding; DRF at scale) | E | |
| 094 | stretch — Obsidian vault emission `--emit-vault` | E | |

---

*The thesis of v0.8 in one line: Microsoft just published that repository exploration is the
bottleneck and that offloading it makes agents measurably better — deepdive's job is to prove its
precomputed, confidence-tagged, git-archaeology-rich graph makes that offload **better**, and then to
ship so anyone can `uvx forensic-deepdive` it. Prove it, earn the trust, build the rails, ship.*
