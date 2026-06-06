# KICKOFF_v0.5.md — operating mode for v0.5 "Cross-Boundary Protocols"

> Paste the block in §8 as your first message to Claude Code in the repo. Everything above compresses
> into it. Binds with `CLAUDE.md`; points at `PRD_v0.5.md` (the contract) and `research_v0.5.md`
> (cited as *research §1–§7*, its seven Key-Findings sections).

## 1. What you're building (one breath)
v0.4 shipped at **8/9 gate** (DEC-001→054; v0.4.0 tagged & released). v0.5 **lights up the
seams DEC-043 already cut**: it extends the one `CrossBoundaryEdge` abstraction past HTTP to four more
protocols — **MCP** tool dispatch (the headline: agents mapping agents), **tool-registry dynamic
dispatch**, **gRPC + messaging**, plus the **DI/ORM traceability tail** — and first **closes the v0.4
flagship gap** (Superset's `SupersetClient` wrapper + Flask-AppBuilder backend → `0 ROUTES_TO`). It is
**not** new architecture; it reuses the `Endpoint` node so `trace`/`serve --ui`/emit work on every new
protocol for free. True cross-repo federation and the memory/temporal layers wait for their own arcs.

## 2. The keystone you must internalize before any code
**Reuse the `Endpoint` node for every new protocol. Do NOT invent `Tool`/`Service`/`Channel` nodes.**
`Endpoint` carries a `protocol` property; `ROUTES_TO` carries `via`. `trace()`, the HOTPATHS
`## Cross-stack routes` section, and `serve --ui` all query `Endpoint`/`HANDLES`/`CALLS_ENDPOINT`/
`ROUTES_TO` **generically, with no `protocol='http'` filter**. So an MCP tool modeled as
`Endpoint(protocol='mcp', contract_id='mcp::<tool>')` with `via='mcp'` edges lights up trace, emit,
and the UI **with zero surfacing-layer changes**. The only per-protocol work is a `KeyBuilder` + a
provider extractor + a consumer extractor. If you catch yourself adding a `protocol==` branch to
`trace`/emit/`serve`, **stop and generalize** — the abstraction already handles it. (Full design:
PRD §1. The one DEC'd new-node exception is the DI/ORM `Table` node — PRD §3.4.)

## 3. Session-start protocol (with CLAUDE.md's)
1. `CLAUDE.md` → `DECISIONS.md` → `PROGRESS.md` → `git log --oneline -10`.
2. Read `PRD_v0.5.md` §0–§4 fully, §5–§10 skim. Keep `research_v0.5.md` for §refs.
3. State in one sentence: *"Working on v0.5 Step <N> (<name>), respecting DEC-<M> about <Y>."*
4. `DECISIONS.md` ends at **DEC-054**; v0.5 starts at **DEC-055**.

## 4. Build order (do not reorder)
**0** scope decision (DEC-055, write first) → **1** close the flagship gap: configured-client consumer
+ Flask-AppBuilder provider (DEC-056) → **2** MCP as a `CrossBoundaryEdge` protocol (DEC-057, the
headline + the keystone proof) → **3** tool-registry dynamic dispatch (DEC-058, the honest-confidence
hard part) → **4** DI/ORM traceability tail (DEC-059, the committed `trace` promise) → **5**
service-to-service gRPC + messaging (DEC-060/061) → **6** framework breadth NestJS/Django/JAX-RS
(DEC-061+, the coverage track). Step 1 turns 8/9 → 9/9 and is the warm-up; 2–3 are the headline; 4
pays a debt; 5–6 widen coverage. Finish v0.5 and ship its findings (`docs/findings/v0.5/`) before
touching v0.6+.

## 5. The five rules that catch most mistakes here
1. **Reuse `Endpoint`, never a new node type** (except the DI/ORM `Table`, DEC'd). The keystone proof
   is a `git diff` for Step 2 that touches `contracts/` + `registry.py` + tests **only** — not the
   `trace`/emit/`serve` query logic. If those files change for a new protocol, you broke the keystone.
2. **Confidence stays sacred.** EXTRACTED only spec-backed (`.proto`/OpenAPI) or unique-literal-
   both-sides. MCP `call_tool("x")` ↔ `@mcp.tool(name="x")` literal+unique → EXTRACTED;
   `call_tool(var)` → drop or wildcard, never guess one. Dynamic registry dispatch → AMBIGUOUS-all
   (emit every registered handler, capped). Interface→multi-impl injection → AMBIGUOUS-all (Spring
   itself fails closed here — mirror it).
3. **Pure-static floor (DEC-009).** Never run the agent, hit a live MCP server, run protoc, or touch
   the network/LLM. Everything is AST-only.
4. **No un-DEC'd runtime dep.** The `.proto` AST parser (`proto-schema-parser` pulls
   `antlr4-python3-runtime`) goes behind an opt-in `[proto]` extra + its own DEC, like `[openapi]`+
   pyyaml. Default to the **zero-dep tree-sitter/regex proto floor** for the EXTRACTED subset.
5. **`symbol_id` via `_parent_chain` or the edge is filtered.** Every new provider/consumer/injection
   extractor must compose `<rel_path>::<qn_local>` with the *same* `_parent_chain` the symbol graph
   uses, or `valid_symbol_qns` silently drops the edge — the #1 way a new extractor emits nothing.
   Registration is run-time idempotent (`register_<proto>_extractors()` in `ContractPhase.run`), never
   an import side-effect.

## 6. The differentiator, stated plainly (research §2)
GitNexus is still **PolyForm-Noncommercial** (we are Apache-2.0) and their cross-boundary issue **#306
is still Open** — they lose the boundary at `fetch('/api/login')` → backend route. We ship the only
materialized cross-boundary join + the OpenAPI codegen shortcut + per-edge provenance. v0.5 widens
that from **one** protocol (HTTP) to **five** (HTTP, MCP, registry-dispatch, gRPC, messaging) on the
*same* abstraction. The headline is **MCP** — the project exists to give agents forensic understanding
of code, and hermes proved the static layer is blind to how agents actually wire themselves (186
`ClientSession`, 27 `FastMCP`, ~3,025 dispatch lines → 1 internal `ROUTES_TO`). Build MCP well; it is
"maps the code" → "maps how the agent works."

## 7. What "done" means (the §4.9 gate)
`pytest -x` green; `ruff` clean. **Step 1:** Superset yields `ROUTES_TO` (8/9 → 9/9), honest split,
`trace` walks it. **Step 2:** hermes yields `mcp` `ROUTES_TO`; `trace` walks agent→tool→handler; the
HOTPATHS section + `serve --ui` show `mcp` edges with **zero surfacing-layer change** (the keystone
diff). **Step 3:** bounded AMBIGUOUS fan-out on hermes registries, cap holds, deterministic. **Step
4:** `trace` reaches a `Table` node via service→inject→repo→table on spring-petclinic (JPA) + Superset
(SQLAlchemy), honest ladder, `boundary` note updated. **Step 5:** gRPC stub↔`.proto` EXTRACTED
spec-backed join + publish↔subscribe join, no new base-env dep (proto floor). **Step 6:**
NestJS/Django/JAX-RS routes located. Byte-identical/deterministic artifacts; `AGENT_BRIEF ≤5kb`
everywhere; findings under `docs/findings/v0.5/` with per-protocol confidence splits + the keystone
zero-diff evidence. As in v0.4, an honest single-repo shortfall (reported, never fabricated) is an
acceptable pass with the gap promoted to the next arc.

## 8. The paste-able kickoff block
```
Read CLAUDE.md, DECISIONS.md, PROGRESS.md, and `git log --oneline -10`. Then read
docs/v0.5/PRD_v0.5.md (§0–§4 fully, §5–§10 skim) and docs/v0.5/KICKOFF_v0.5.md;
keep docs/v0.5/research_v0.5.md for the §refs (its seven Key-Findings sections).

v0.4 shipped at 8/9 gate (DEC-001→054). We are building v0.5 "Cross-Boundary Protocols"
— lighting up the seams DEC-043 already cut, NOT new architecture.

FIRST: write DEC-055 — the v0.5 scope decision: spine = "extend the CrossBoundaryEdge
abstraction past HTTP," MCP-led; "Memory" splits into three lanes (incremental→v1.0,
temporal/Graphiti→opt-in-later, agent-write-back→already exists, only hardening is
v0.5-sized); federation = lighter within-repo service-to-service in scope, true
cross-repo deferred to its own arc (PRD §2). Do not write other v0.5 code until DEC-055
is committed.

THE KEYSTONE (internalize, PRD §1): reuse the Endpoint node for every new protocol —
do NOT invent Tool/Service node types. trace()/serve --ui/the HOTPATHS cross-stack
section all query Endpoint/HANDLES/CALLS_ENDPOINT/ROUTES_TO generically with no
protocol filter, so Endpoint(protocol='mcp', contract_id='mcp::<tool>', via='mcp')
lights up trace/emit/UI for free. The only per-protocol work is a KeyBuilder + provider
extractor + consumer extractor. The one DEC'd new-node exception is the DI/ORM Table
node.

THEN build v0.5 in order 1→2→3→4→5→6 (PRD §3), one step at a time, tests green before
moving on, a DEC for every non-trivial choice (expect ~1.5–2× the §9 pre-draft, ending
~DEC-068), PROGRESS.md updated each session end. Honor every invariant in PRD §8 —
especially: reuse Endpoint (no new node types bar the DI/ORM Table); confidence sacred
(EXTRACTED only spec-backed or unique-literal; dynamic dispatch → AMBIGUOUS-all, emit
all never guess one); pure-static floor (never run the agent / live MCP server / protoc
/ network / LLM); no un-DEC'd runtime dep (the .proto AST parser goes behind an opt-in
[proto] extra + its own DEC — default to the zero-dep tree-sitter/regex floor);
symbol_id via _parent_chain or the edge is filtered; run-time idempotent registration.

Step 1 (DEC-056): close the v0.4 flagship gap — a configured-client consumer extractor
(<Client>.get/post({endpoint|url:...}), guarded by the object-literal shape NOT a
SupersetClient allowlist) + a Flask-AppBuilder provider extractor (ModelRestApi/@expose,
modeled like the Spring class-prefix+method-route provider). Acceptance: Superset
(252 client calls, 275 documented-but-unlocated handlers) → ROUTES_TO materializes,
8/9 → 9/9.

The headline is Step 2 (MCP) and its keystone proof: the git diff lands ROUTES_TO for
MCP while touching contracts/ + registry.py + tests ONLY — not trace/emit/serve query
logic. Key on the bare tool name (mcp::<tool>), normalizing . / - to _ ; server-
qualified keying is a future INFERRED enhancement, not v0.5.

Confirm understanding in one sentence, write DEC-055, then begin Step 1. Do not push to
remote. Do not touch v0.6+ or the IDE until v0.5 passes its §4.9 gate.
```

---

*The IDE is out of scope. v0.5 lays three endgame seams at near-zero cost — protocol generality proven
across five instances (federation/IDE-context substrate), the DI/ORM tail + `Table` node (data-layer
reach), and agent-dispatch modeling (the tool serving the agents it maps). Lay the seams clean; don't
build on them yet.*
