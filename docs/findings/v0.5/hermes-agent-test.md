# hermes-agent — v0.5 acceptance (MCP + registry dispatch: "maps how the agent works")

The headline v0.5 run. v0.4's scouting finding
([`../v0.4/hermes-agent-test.md`](../v0.4/hermes-agent-test.md)) predicted the exact
gap v0.5 closes: an agent's control flow is **MCP + dynamic dispatch**, invisible to
static `CALLS` and an HTTP-only cross-boundary layer (→ **1** internal `ROUTES_TO`
across 19k symbols). v0.5 Steps 2 (MCP, DEC-057) + 3 (registry dispatch, DEC-058)
model exactly those. This run tests whether the predictions came true.

## Run summary

| | |
|---|---|
| Date | 2026-06-12 |
| Repo | NousResearch/hermes-agent (`--depth 1` shallow, MIT) |
| Tool version | v0.5 HEAD (all 6 steps, DEC-055 → DEC-062) |
| Symbols | **21,071** · **45,909** CALLS |
| Extract | full graph build (single run) |

## v0.4 → v0.5: the nervous system lights up

| signal | v0.4 | **v0.5** | what it is |
|---|---|---|---|
| internal `ROUTES_TO` (any protocol) | **1** | **35 + the MCP layer** | the agent's actual wiring |
| **MCP tool Endpoints** | — (unmodeled) | **22** | `@mcp.tool()` tools hermes serves |
| **MCP `HANDLES`** | — | **18** | tool handlers located |
| **MCP `CALLS_ENDPOINT`** | — | **5** | `call_tool("name")` literal call sites |
| **registry-dispatch `ROUTES_TO`** | — | **35** | dynamic `registry[key]()` → handler |
| **registry-dispatch Endpoints** | — | **2,384** | the dispatch keyspace |
| **registry-dispatch `HANDLES`** | — | **214** | located registrations |

The 22 MCP tools are real and legible — a sample:
`mcp::channels_list`, `mcp::conversation_get`, `mcp::messages_send`,
`mcp::messages_read`, `mcp::list_windows`, `mcp::get_window_state`,
`mcp::events_wait`, `mcp::health_check`, `mcp::describe_table`, `mcp::list_apps`.
This is the agent's served tool surface — exactly the layer v0.4 was blind to.

## The honest result on MCP `ROUTES_TO` (0 — and why that's correct)

MCP `HANDLES` (18) and `CALLS_ENDPOINT` (5) both materialized, but they **do not
join** into a `ROUTES_TO` — and that is the **honest, correct** outcome, not a miss:

- hermes is an MCP **server** (it *serves* ~18 `@mcp.tool()` tools → 18 `HANDLES`)
  **and** an MCP **client** (it *calls* tools via `ClientSession.call_tool("x")` →
  5 `CALLS_ENDPOINT`). The tools it **serves** and the tools it **calls** are
  **disjoint namespaces**: the called tools live on **external** MCP servers that
  aren't in this repo.
- So those 5 consumer call sites correctly get a `CALLS_ENDPOINT` to an Endpoint
  with **no in-repo `HANDLES`** — the DEC-043 "calls an endpoint we can't locate"
  posture, which is also the cross-repo **federation seam** (an unmatched
  `CALLS_ENDPOINT` is precisely where repo-B's handler would attach).
- A fabricated MCP `ROUTES_TO` here would be **wrong**. 0 is the truthful number.

Only **5** `call_tool` sites keyed (vs the 186 `ClientSession` references v0.4
counted): most `ClientSession` usage is transport/setup wiring, and a
`call_tool(variable)` with a non-literal tool name is **dropped, never guessed**
(DEC-037) — so 5 literal-keyed consumers is the honest floor.

## Registry dispatch — the bigger real-code win (35 `ROUTES_TO`)

The ~3,025 dispatch lines v0.4 flagged now produce **35 materialized
`ROUTES_TO`** edges through `registry[key]()` / `TOOLS[name]()` dispatch, over a
**2,384-key** dispatch space with **214** located registrations. The **fan-out cap
(DEC-058) fired exactly as designed** on the large registries, surfaced honestly via
log — e.g.:

```
registry 'result' dynamic-dispatch fan-out capped at 25 (105 more handler(s) omitted)
registry 'state'  dynamic-dispatch fan-out capped at 25 (18 more handler(s) omitted)
registry 'response' …capped at 25 (4 more omitted) · 'sess' …(1 more omitted)
```

A 25-cap on a 130-handler registry keeps the graph bounded while staying honest
about what was dropped — the AMBIGUOUS-all fan-out never explodes.

## Other v0.5 protocols (correctly 0 here)

`grpc` / `topic` / `queue` `ROUTES_TO` and `INJECTS`/`PERSISTS_TO`/`DbTable` are all
**0** — hermes is a Python agent with no gRPC services, no Kafka/pika messaging, and
no Spring-DI/SQLAlchemy-ORM persistence layer. The extractors firing **nothing** on
a repo that genuinely has none of those shapes is the correct, no-false-positive
result (the same discipline that keeps the goldens byte-identical).

## Caveats (honest)

- **`--depth 1`** shallow clone → empty archaeology layer (no `CO_CHANGES_WITH`), as
  in the v0.4 run. Not a tool limitation; a full clone restores it.
- Extraction on 21k symbols + a 2,384-key registry fan-out is **slow** (a full
  graph build is minutes, not seconds) — the registry-dispatch pass is the new cost;
  the cap bounds the graph size, not the scan time. A perf pass is a v0.6 candidate.

## Takeaway

The v0.4 thesis is **confirmed on real agent code**: modeling MCP + registry
dispatch as `CrossBoundaryEdge` protocols took hermes from **1** internal
`ROUTES_TO` to **22 MCP tool endpoints + 23 MCP edges + 35 registry-dispatch
`ROUTES_TO`** — the agent→tool→handler nervous system v0.4 could not see. And the
keystone held: these all surface through the **unchanged** `trace` / `serve --ui` /
HOTPATHS layer. "Maps the code" → "maps how the agent actually works."
