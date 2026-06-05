# KICKOFF_v0.4.md — operating mode for v0.4 "Cross-Stack & Visual"

> Paste the block in §8 as your first message to Claude Code in the repo. Everything above compresses
> into it. Binds with `CLAUDE.md`; points at `PRD_v0.4.md` (the contract) and `research_v0.4.md` (§refs).

## 1. What you're building (one breath)
v0.3 shipped (DEC-001→042, 471 tests, tagged). v0.4 is **the wedge**: a `ROUTES_TO` cross-stack join
(React `fetch`/`axios` → Spring/FastAPI/Express/… route handler), built on **one generalizable
`CrossBoundaryEdge` abstraction** so gRPC/topics drop in at v0.5 for free — plus an **OpenAPI/codegen
shortcut** that GitNexus lacks (our differentiator), a **`forensic serve --ui`** Sigma.js explorer, a
**`trace`** MCP tool (9th), and two v0.3-finding quick wins: **TS heritage capture** and an **`example`
file-role**.

## 2. The keystone you must internalize before any code
Do **not** build a bespoke HTTP linker. Build the abstraction GitNexus proved (research §1): a contract
is `(role, contractId, symbol, confidence)`; the join groups by `contractId`; HTTP is the first instance
(`http::GET::/users/{param}`). gRPC (`grpc::Svc/Method`) and topics reuse it in v0.5. The graph shape:
`Endpoint` node (PK=contractId) + `HANDLES` (provider Symbol→Endpoint) + `CALLS_ENDPOINT` (consumer
Symbol→Endpoint) + the materialized `ROUTES_TO` (consumer Symbol→provider Symbol, confidence-tagged).
This is **DEC-043**, write it first. (Full design: PRD §1.)

## 3. Session-start protocol (with CLAUDE.md's)
1. `CLAUDE.md` → `DECISIONS.md` → `PROGRESS.md` → `git log --oneline -10`.
2. Read `PRD_v0.4.md` §0–§4 fully, §5–§10 skim. Keep `research_v0.4.md` for §refs.
3. State in one sentence: *"Working on v0.4 Item <X> (<name>), respecting DEC-<N> about <Y>."*
4. `DECISIONS.md` ends at **DEC-042**; v0.4 starts at **DEC-043**.

## 4. Build order (do not reorder)
**A** stable node-IDs (DEC-051) → **B** TS heritage (DEC-050) → **C** `example` role (DEC-049) → **D**
abstraction+schema+ContractPhase (DEC-043) → **E** HTTP normalization (DEC-044) → **F** provider
extractors (DEC-045) → **G** consumer extractors (DEC-046) → **H** join+confidence (DEC-047) → **I**
codegen shortcut (DEC-048) → **J** `trace` 9th tool + emit section (DEC-052) → **K** Sigma.js `serve
--ui` (DEC-053, largest) → **L** acceptance (§4.9). A/B/C are independent quick wins + the forward-compat
seam; D–I are the wedge in dependency order; J surfaces, K visualizes, L proves. Finish v0.4 and ship its
findings before touching v0.5; write the v0.5 detail-PRD pass then, not now.

## 5. The five rules that catch most mistakes here
1. **One abstraction, not three.** HTTP is an instance of `CrossBoundaryEdge`. If you find yourself
   writing HTTP-only join logic that gRPC couldn't reuse, stop and generalize. The gRPC/topic seams are
   stubbed `NotImplemented` in `registry.py` on purpose.
2. **ROUTES_TO confidence is sacred.** EXTRACTED only when spec-backed (Item I) or a *unique*
   literal-path+method match with both symbols resolved. Template/numeric/prefix-normalized unique →
   INFERRED. Multiple candidate providers → emit *all* as AMBIGUOUS, never pick one (DEC-025/037
   philosophy). Unmatched consumer → keep CALLS_ENDPOINT to the Endpoint, no ROUTES_TO (honest "hits an
   endpoint we can't locate").
3. **Pure-static floor (DEC-009).** ROUTES_TO, spec parsing, heritage, the UI graph endpoint — all work
   with no LLM/network/embeddings. The codegen shortcut reads local spec files only.
4. **Copy GitNexus's *normalization*, set your *own* confidence numbers.** `:id`/`{id}`/`[id]`→`{param}`,
   lowercase, strip query+trailing-slash; consumer also collapses template literals and numeric segments
   (research §2). Their 0.8/0.7 numbers are an implementation detail — map to our three tags.
5. **9th MCP tool + new HOTPATHS section fire the coupling rule.** Update all tool-enumerating SKILL.md
   files, README (8→9 tools, the comparison table, intro), the tool count. The cross-stack data is a
   *section* in HOTPATHS — never a 6th core artifact (5-artifact contract holds). Keep AGENT_BRIEF ≤5kb.

## 6. The differentiator, stated plainly
GitNexus is ahead on cross-stack and visualization and has more frameworks wired. **Our edge is the
OpenAPI/proto/GraphQL/tRPC codegen shortcut (Item I, research §3) — it has none for HTTP.** When a repo
ships a spec + generated client, emit EXTRACTED `spec_backed=True` joins it can't reach. Plus Apache-2.0
(GitNexus is PolyForm Noncommercial — commercial use prohibited) and per-edge provenance on the new
ROUTES_TO class. Build the shortcut well; it's the reason to choose us.

## 7. What "done" means (the §4.9 gate)
pytest -x green; ruff clean; ROUTES_TO joins Superset's React↔Flask with `trace()` returning the chain
and an honest confidence split; the OpenAPI-spec repo yields EXTRACTED spec-backed joins; TS
EXTENDS/IMPLEMENTS materially up; fastapi shaped-query AMBIGUOUS materially below 36%; `serve --ui`
renders Superset bounded+filtered with ROUTES_TO highlighted; byte-identical/deterministic; a symbol's ID
survives an unrelated edit; AGENT_BRIEF ≤5kb everywhere; findings under `docs/findings/v0.4/` with the
ROUTES_TO split, codegen hit-rate, and the two before/afters. Superset is the staged demo (petclinic is
JSP-server-rendered → provider-only, be honest about it). The supervisor will test across more repos and
report back — make the findings diffable.

## 8. The paste-able kickoff block
```
Read CLAUDE.md, DECISIONS.md, PROGRESS.md, and `git log --oneline -10`. Then read
docs/v0.4/PRD_v0.4.md (§0–§4 fully, §5–§10 skim) and docs/v0.4/KICKOFF_v0.4.md;
keep docs/v0.4/research_v0.4.md for the §refs.

v0.3 shipped (DEC-001→042). We are building v0.4 "Cross-Stack & Visual" — the wedge.

FIRST: write DEC-043 — the CrossBoundaryEdge abstraction (a contract is
(role, contractId, symbol, confidence); the join groups by contractId; HTTP is the
first instance; graph shape Endpoint node + HANDLES + CALLS_ENDPOINT + materialized
ROUTES_TO) per PRD §1. gRPC/topic key-builders are stubbed NotImplemented (v0.5 seam).
Do not write other wedge code until DEC-043 is committed.

THEN build v0.4 in order A→B→C→D→E→F→G→H→I→J→K→L (PRD §3), one item at a time, tests
green before moving on, a DEC for every non-trivial choice (expect ~1.5–2× the §4.8
pre-draft), PROGRESS.md updated each session end. Honor every invariant in PRD §9 —
especially: one abstraction not three; ROUTES_TO EXTRACTED only when spec-backed or
unique-literal; the pure-static floor; copy GitNexus's normalization but set our own
confidence tags; the 9th tool + HOTPATHS section coupling rule; AGENT_BRIEF ≤5kb.

The differentiator is the OpenAPI/codegen shortcut (Item I) — build it well.

Confirm understanding in one sentence, write DEC-043, then begin Item A (stable node-IDs
— the forward-compat seam). Do not push to remote. Do not touch v0.5+ until v0.4 passes
its §4.9 gate.
```

---

*The IDE is out of scope. v0.4 lays three endgame seams at near-zero cost — stable IDs (incremental/
rename), the Endpoint join node (federation), single-call `trace` (agent-context-in-one-call) — so the
environment arc stays reachable. Lay the seams clean; don't build on them yet.*
