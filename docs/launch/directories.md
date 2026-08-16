# MCP directory submission metadata (DEC-119)

**Status: draft reference only — nothing submitted from this file.** Most MCP hubs
(PulseMCP, Glama, mcp.so, MCPJungle) auto-ingest from the official MCP Registry entry
(`io.github.Dhevenddra/forensic-deepdive`) once it's published — there is usually no
per-hub submission form to fill in, only an optional **claim** step (prove ownership of
the `io.github.Dhevenddra/*` namespace via GitHub OAuth) to unlock an editable listing.
This doc exists so the same copy is reused everywhere instead of drifting per-hub, and
so the owner isn't improvising the pitch at claim time.

## Canonical fields (reuse verbatim across hubs)

- **Name:** `forensic-deepdive`
- **MCP Registry ID:** `io.github.Dhevenddra/forensic-deepdive`
- **Tagline** (≤60 chars): `Confidence-tagged code knowledge graph for AI agents`
- **Short description** (≤160 chars): `Persistent code knowledge graph + MCP server.
  Every edge tagged EXTRACTED/INFERRED/AMBIGUOUS. 9 languages, 9 tools, Apache-2.0.`
- **Long description:**

  > `forensic-deepdive` analyzes a codebase (Python, C, Dart, Swift, TypeScript,
  > JavaScript, Java, Go, Rust) and builds a persistent embedded knowledge graph
  > (File/Symbol/Module/Commit/Author/Endpoint nodes; CALLS/IMPORTS/EXTENDS/
  > TOUCHED_BY_COMMIT and cross-boundary HANDLES/CALLS_ENDPOINT/ROUTES_TO edges spanning
  > HTTP, MCP, registry-dispatch, gRPC, and messaging). Every edge and every emitted
  > claim carries a confidence tag — EXTRACTED (deterministic), INFERRED (a heuristic
  > resolved cleanly), or AMBIGUOUS (multiple candidates, all surfaced) — so an agent
  > knows what to trust before acting on it. The MCP server exposes 9 composite tools
  > (impact, context, archaeology, flow, query, record_insight, recall_insights,
  > visualize, trace) over the graph, and `forensic extract` also writes five durable
  > markdown artifacts (MAP, HOTPATHS, ARCHAEOLOGY, MENTAL_MODEL, AGENT_BRIEF) as a
  > fallback for agents that don't speak MCP. Apache-2.0 — the license-compatible
  > alternative to GitNexus (PolyForm Noncommercial) for commercial use.
  >
  > This is an assisted-analysis tool: proven usable with real agent auto-discovery,
  > not yet proven to make autonomous end-to-end issue resolution measurably faster.
  > See `docs/findings/HONEST.md` in the repo.

- **Category / tags:** `code-analysis`, `knowledge-graph`, `static-analysis`,
  `developer-tools`, `ai-agents`
- **License:** Apache-2.0
- **Repo:** https://github.com/Dhevenddra/forensic-deepdive
- **PyPI:** https://pypi.org/project/forensic-deepdive/
- **MCP Registry entry:** https://registry.modelcontextprotocol.io (search
  `io.github.Dhevenddra/forensic-deepdive`)
- **Install (uvx, no local install):**

  ```json
  {
    "mcpServers": {
      "forensic-deepdive": {
        "command": "uvx",
        "args": ["forensic-deepdive", "serve", "--repo", "."]
      }
    }
  }
  ```

- **Tool count:** 9 composite MCP tools (see README `## The 9 MCP tools` table for the
  full list + descriptions — reuse that table verbatim if a hub wants a tool listing).
- **Contact / author:** Dhevenddra (GitHub: `Dhevenddra`)

## Per-hub notes

- **PulseMCP** — auto-ingests from the Registry; claim via GitHub OAuth if an editable
  listing is wanted. No separate submission form as of the last check (v0.8 launch
  session) — reverify at claim time, hub UIs move.
- **Glama** — same auto-ingest pattern. Glama has historically also surfaced a quality/
  activity score computed from the repo itself (stars, CI status, recency) — nothing to
  submit for that, it's derived.
- **mcp.so** — same auto-ingest pattern; historically the lightest-weight of the three
  (mostly a registry mirror with search).
- **Smithery** — **not auto-ingest** as of the last check; Smithery has traditionally
  wanted its own `smithery.yaml` in the repo root describing the server's tools/config
  schema for their hosted deployment flow. **Not added by this pass** — deployment-flow
  scope creep, deliberately deferred. If pursuing Smithery, that's a small follow-up
  DEC of its own (a new file, no engine change), not something to fold into a docs pass.

All hub UI/claim-flow details are inherently perishable — reverify against the live
site before actually submitting anything, this file is a copy source, not a runbook.
