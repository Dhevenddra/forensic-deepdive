# hermes-agent — v0.4 exploratory test (understanding how agents are built)

Not a §4.9 gate repo — a **forward-looking scouting run** suggested for v0.5. Since
forensic-deepdive exists to give *agents* forensic understanding of a codebase,
running it on a serious agent codebase is doubly useful: it stresses the
extractors **and** tells us what an agent's architecture looks like (so we know
what to model next). [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
(MIT) is a self-improving multi-platform AI agent — TUI + gateway
(Telegram/Discord/Slack/WhatsApp/Signal), MCP servers + clients, a skill-learning
loop, subagents, cron, and a dozen LLM provider adapters.

## Run summary

| | |
|---|---|
| Date | 2026-06-05 |
| Repo | NousResearch/hermes-agent (`--depth 1` shallow clone, MIT) |
| Tool version | v0.4 HEAD (`a5b3e02` + the DEC-054 inventory fix) |
| Files | **1,340** source (python-dominant; + js/ts/tsx/rust) · **19,375** Symbols |

## What the tool captured well (the static skeleton)

| signal | value | note |
|---|---|---|
| CALLS | **41,188** | EXTRACTED 33,943 / INFERRED 6,548 / **AMBIGUOUS 697 (1.7 %)** |
| EXTENDS / IMPLEMENTS | 162 / 1 | Python class hierarchies |
| HTTP endpoints (providers) | **282** | the gateway + ACP server routes (199 HANDLES, 83 unlocated) |
| outbound API calls (consumers) | **121** `CALLS_ENDPOINT` | 20 EXTRACTED / 101 INFERRED |

**1.7 % AMBIGUOUS is the cleanest ratio of any repo tested** (gitnexus was 3.6 %,
superset 19 %) — Python with disciplined imports resolves almost perfectly. The
**121 outbound calls are a highlight**: the tool maps every external service the
agent talks to — `_fetch_anthropic_account_usage → /api/oauth/usage`,
`_fetch_codex_oauth_context_lengths → /backend-api/codex/models`,
`_query_local_context_length → /v1/models` (OpenAI-compatible). For an agent,
"every API this thing calls" is genuinely valuable, and it falls out for free.

One **internal cross-language `ROUTES_TO`** materialized, and it's a good one:
`tools/send_message_tool.py::_send_whatsapp → scripts/whatsapp-bridge/bridge.js`
— a Python tool calling its JS WhatsApp bridge over HTTP, joined across languages.

## What the tool CANNOT yet understand (the v0.5 opening)

Only **1 internal `ROUTES_TO`** across a 19k-symbol agent — not because the join
machinery failed, but because **an agent's internal control flow is not HTTP**. It
is dynamic dispatch, and that is exactly what static `CALLS` (and an HTTP-only
cross-boundary layer) can't traverse:

| agent pattern in hermes | count | why it's invisible |
|---|---|---|
| **MCP client sessions** (`ClientSession`) | **186** | agent→tool calls over the MCP **stdio** protocol — a cross-boundary edge we don't model |
| **MCP servers** (`FastMCP`) | **27** | tools exposed over MCP — the provider side of that boundary |
| `stdio_client` transports | 12 | the MCP transport itself |
| `@mcp.tool()` registrations | ~18 | tools registered dynamically into a server |
| dynamic dispatch / registry / RPC lines | ~3,025 | tool/skill invocation through registries + `getattr`, not static calls |
| LLM provider adapters | 12+ files | model routing is config-driven, chosen at runtime |

So the tool sees the agent's **bones** (every symbol, call, HTTP endpoint, external
API) but not its **nervous system** (the agent → tool → result loop that *is* the
product). This is the precise, repo-evidenced case for the next cross-boundary
protocol.

## Feature proposals for v0.5 (logged from this run)

1. **MCP as a `CrossBoundaryEdge` protocol** — the exact move v0.4 made for HTTP,
   applied to MCP: a provider extractor for `@mcp.tool()` / `FastMCP` server tools
   (→ `Endpoint`-like *Tool* nodes keyed by tool name) and a consumer extractor for
   `ClientSession.call_tool(...)` / `stdio_client` wiring (→ `CALLS_TOOL`). Then
   `trace` walks **agent → MCP tool → handler** the same way it walks HTTP today.
   Hermes alone has 186 client sessions + 27 servers to join.
2. **Tool/skill-registry dispatch edges** — model the dynamic `registry[name]()` /
   decorator-registration pattern (a bounded, confidence-tagged INFERRED edge from
   the dispatch site to each registered handler) so the agent→tool fan-out is
   visible without false precision.
3. **A first-class "external API surface" view** — the 121 outbound calls already
   identify every third-party service an agent depends on; surfacing that as a
   dedicated artifact section (or `serve --ui` filter) is high-value for agent
   audits ("what can this agent reach?").

## Caveats (honest)

- **0 CO_CHANGES_WITH** — the `--depth 1` shallow clone has no history, so the
  archaeology layer is empty. A full clone would restore it; not a tool limitation.
- The DEC-054 `example`-role inventory fix landed before this run — hermes has no
  JVM packages, so it was unaffected, but all 1,340 files correctly classify as
  `source`.

## Takeaway

forensic-deepdive already gives an agent-builder a strong static map of hermes
(19k symbols, 1.7 % AMBIGUOUS, every external API). The **v0.5 thesis writes
itself**: agents are *defined* by their dynamic tool/MCP dispatch, and modeling
MCP (+ registry dispatch) as the next `CrossBoundaryEdge` protocol is how Deepdive
goes from "maps the code" to "maps how the agent actually works." Understanding
hermes told us what to build next — which is the point of running it.
