# v0.4 "Cross-Stack & Visual" — acceptance findings (Item L)

Real-repo acceptance for the v0.4 arc. The wedge: cross-language **ROUTES_TO**
joins (frontend call → `Endpoint` → backend handler), the **OpenAPI codegen
shortcut** (spec-backed EXTRACTED), TS-heritage capture, the `example` file-role,
and the **`forensic serve --ui`** Sigma.js explorer. All runs: Windows 11,
`forensic-deepdive` v0.4 HEAD (`a5b3e02`), pure-static (no LLM / network /
embeddings — `degraded=True` on every NL query).

## Repo set (PRD §4.9)

| repo | role | what it proves |
|---|---|---|
| [**superset**](superset-test.md) | flagship / scale | TS-heritage + Item-I spec coverage at scale + the 348k `serve --ui` LOD proof; **surfaces the ROUTES_TO gap** |
| [**spring-react-demo**](spring-react-demo-test.md) | purpose-built | clean **TS→Java ROUTES_TO**, the EXTRACTED/INFERRED split |
| [**openapi-shop**](openapi-shop-test.md) | purpose-built | the **committed-spec codegen shortcut** (templated client → EXTRACTED) |
| [**gitnexus**](gitnexus-test.md) | carryover | **TS-heritage** before/after (EXTENDS 2→21) |
| [**fastapi**](fastapi-test.md) | carryover | the **`example` role** before/after (shaped AMBIGUOUS 0 %) |

The purpose-built repos are local (`C:/Dev/scratch/`), not committed. spring-petclinic
(v0.3) remains the provider-only Spring check; spring-react-demo adds the React side.

**Exploratory (not a gate repo):** [`hermes-agent`](hermes-agent-test.md) — a
forward-looking v0.5 scouting run on a real AI-agent codebase (NousResearch). It
confirms the tool captures an agent's static skeleton excellently (19,375 symbols,
**1.7 % AMBIGUOUS**, 282 endpoints, 121 outbound API calls) but **not** its
dynamic control flow (186 MCP `ClientSession` + 27 `FastMCP` + registry dispatch →
1 internal `ROUTES_TO`). It defines the v0.5 thesis: **model MCP + tool-registry
dispatch as the next `CrossBoundaryEdge` protocol.**

## Cross-repo summary

| repo | files | symbols | EXTENDS | endpoints (spec-backed) | ROUTES_TO (split) | AGENT_BRIEF |
|---|---|---|---|---|---|---|
| superset | 3,871 | 18,764 | 1,320 | 277 (276) | **0** (gap, v0.5) | 1,663 B |
| spring-react-demo | 4 | 15 | 0 | 4 (0) | **4** (2 EXT / 2 INF) | 1,560 B |
| openapi-shop | 2 | — | 0 | 3 (3) | **2** (2 EXT) | 1,291 B |
| gitnexus | 719 | 4,109 | 21 | 22 (0) | 0 | 1,630 B |
| fastapi | 524 | 1,986 | 87 | 93 (0) | 14 (14 AMB) | 1,644 B |

## §4.9 acceptance gate — assessment

1. **pytest -x green; ruff clean** — ✅ 643 passed, 1 skipped; `ruff check`/`format` clean.
2. **ROUTES_TO joins + `trace` + honest confidence split** — ✅ on the clean
   cross-stack repos (**spring-react-demo**: 4 TS→Java joins, **2 EXTRACTED / 2
   INFERRED**, `trace` walks the chain; **openapi-shop**: spec-backed EXTRACTED).
   ❌ **on Superset specifically: 0 ROUTES_TO** — its `SupersetClient` frontend
   wrapper (252 call sites) + Flask-AppBuilder backend are outside v0.4's generic
   extractor coverage. The join machinery is validated; Superset defines the
   concrete v0.5 extractor work (see its finding). **No fabricated joins.**
3. **Codegen shortcut → spec_backed EXTRACTED** — ✅ **openapi-shop** upgrades
   templated-client joins to EXTRACTED via the committed spec; **superset** ingests
   276 documented operations (1 located / 275 unlocated — the honest spec-coverage
   metric at scale).
4. **TS heritage materially up** — ✅ gitnexus EXTENDS **2→21** (10×, total heritage
   7→26); superset EXTENDS **1,166→1,320** (+154). DEC-050 captures confirmed.
5. **`example` role: fastapi shaped AMBIGUOUS < 36 %, top hits library** — ✅
   **0.0 %** shaped-result AMBIGUOUS, top-10 all library `source`; 449 of 524 files
   demoted source→example.
6. **`serve --ui` renders Superset bounded + filtered** — ✅ 348,118 CO_CHANGES_WITH
   in-graph → default view **114 nodes / 116 edges** (co-change opt-in OFF); bounded
   under every filter combination. (ROUTES_TO highlighting shown on the clean repos,
   since Superset has none.)
7. **Determinism: byte-identical artifacts across runs** — ✅ re-extract diff clean.
8. **Stable IDs: unrelated edit leaves a symbol's ID unchanged** — ✅ `getUser`
   `node_id` constant while its line shifted 9→14 after an unrelated insertion.
9. **AGENT_BRIEF ≤ 5 kb everywhere** — ✅ max 1,663 B (superset).

**Verdict:** **8 of 9 gate items fully green.** Gate #2 is met on the clean
cross-stack repos and **honestly short on Superset** — the cross-stack *capability*
works; Superset reveals that real-world custom client/framework abstractions
(`SupersetClient`, Flask-AppBuilder) are the next extractor frontier. This is the
same honest-failure→next-version pattern as v0.3 (fastapi's AMBIGUOUS finding →
v0.4's `example` role).

## The headline v0.5 work (defined by this gate + the hermes scouting run)

0. **MCP + tool-registry dispatch as a `CrossBoundaryEdge` protocol** (from
   [`hermes-agent`](hermes-agent-test.md)) — the biggest new opening. Agents are
   *defined* by dynamic tool dispatch (MCP `@mcp.tool()`/`FastMCP` providers +
   `ClientSession.call_tool` consumers; registry dispatch), which static `CALLS`
   can't see. Apply the v0.4 HTTP playbook to MCP: Tool nodes + `CALLS_TOOL`, and
   `trace` walks agent → tool → handler.
1. **`SupersetClient`-style configured-client consumer extractor** —
   `<Client>.get/post/put/delete({ endpoint|url: … })`, reusing the axios-object
   path. (Superset: 252 call sites.)
2. **Flask-AppBuilder provider extractor** — `ModelRestApi` / `@expose`. (Superset:
   275 documented-but-unlocated.)
3. The already-deferred **NestJS / Django `urls.py` / JAX-RS** providers (DEC-045 §7).
4. ~~`example`-role precision on Java packages~~ — **fixed in v0.4** (`7d78ef4`,
   DEC-054): `samples`/`example`/`demo` under a `src/main/<lang>/` root no longer
   demote (spring-petclinic 0→30 source files restored).
5. **Keep spec-generated clients in the graph** (demoted like `example`) so the
   codegen shortcut fires even on `// AUTO-GENERATED … DO NOT EDIT` clients
   (discovered in openapi-shop).
