# v0.7 → v0.8 carryover ledger (the seeds)

The honest shortfalls + deferrals v0.7 surfaced (reported, never fabricated) — the raw
material for the v0.8 plan, mirroring how `../v0.6/DEFERRED.md` seeded v0.7. The 5-artifact +
9-MCP-tool contract is frozen; the DEC-043/055 `Endpoint` keystone is untouched. Most items
below are emitter/graph-quality or ergonomics, not new protocols.

## Findings-driven (surfaced by the usability gate — MANUAL_TEST + the agent A/B/C + live MCP)

1. **AGENT_BRIEF Never/Always rules are thin on low-history / solo repos** (DEC-080 finding).
   On Iris-Nearby the top "Always" rule was a centrality artifact (`AppColors`, a theme
   constant with 383 inbound calls — true but low-insight), and the "Never" leaned on near-empty
   git signal. The rules earn their keep only with real history + multiple authors. Seed: gate
   or re-rank brief rules below a history/contributor threshold; prefer business-logic centrality
   over pure call-count; demote theme/constant hubs.
2. **ARCHAEOLOGY ownership/bus-factor is empty on single-author repos** (DEC-080 finding). The
   "who owns what / who to ask" half is vacuous at bus factor 1 (the agent correctly flagged it,
   but there's nothing to surface). Seed: suppress or compress the ownership section below a
   contributor threshold; note shallow-clone degradation explicitly (a `--depth 1` clone
   collapses churn to 1 — Deepdive should warn when it detects a shallow `.git`).
3. **The symbol graph is blind to hand-rolled serialization boundaries** (the "silent breakers").
   `impact()`/the graph count `Message(...)` calls but not `_messageToJson` / `_encodeMessageWithMedia`
   — the functions where a model-field change actually breaks persistence/wire-format silently.
   Every agent (by-hand and MCP) had to grep to find them. Seed: a heuristic to flag
   serialize/encode/`toJson`/`fromJson`/`@HiveField`-adjacent functions as a model's risk surface.
4. **Duplicate symbol rows + self-cycles in graph query output.** `impact()`/`context()` returned
   the same symbol multiple times (e.g. `NearbyService` ×4) and `flow()` showed a `Message→Message`
   self-cycle artifact. Honest but noisy. Seed: dedupe by `node_id` in the surfacing layer; collapse
   trivial self-cycles.
5. **Dart confidence is mostly INFERRED** (dynamic dispatch limits AST certainty). A language-coverage
   caveat the agent named correctly; the depth-2/3 `impact()` buckets are "check these," not "these
   break." Seed: a Dart-specific resolver pass (or document the ceiling per language).
6. **MCP launch ergonomics** (DEC-080 / §8 doc fix). `uv run forensic serve` fails from a foreign
   CWD (`program not found`) — the documented config needed `--project <forensic-deepdive dir>`.
   Plus the restart-and-approve gate (project-scoped `.mcp.json`). Seed: ship a `uv tool install`
   path so the MCP command is just `forensic serve --repo …` (on PATH, CWD-independent), and a
   one-line `forensic mcp-config <repo>` helper that prints the correct snippet.
7. **Shim regeneration is write-if-absent with no force.** A stale `CLAUDE.md`/`AGENTS.md` (e.g. an
   old "five tools" shim) survives a re-`extract`; the user must delete it by hand. Seed: a
   `--refresh-shims` flag (or a content-hash check that rewrites Deepdive-generated, non-hand-edited
   shims).

## MCP tool quality (from the grounded stress-test — `mcp-tool-review.md`)

7a. **`impact()` over-scopes (precision).** On Iris-Nearby it returned 80 "upstream" symbols for
    `Message`, including `settings_screen` functions with **zero** `Message` references — depth-2/3
    buckets were largely INFERRED noise (same-file co-occurrence promoted to a CALLS edge). It's
    high-recall, low-precision: right for *generating* a blast-radius candidate set, wrong to *trust*
    as the final set. Seed: don't promote same-file co-occurrence to CALLS; separate "references"
    from true call edges (esp. on Dart); let callers cap by confidence/precision.
7b. **NL `query()` lexical ranking misses the obvious.** With `[semantic]` absent (`degraded:true`),
    "where are messages encoded/decoded" returned theme/notification junk and missed
    `_encode/_decodeMessageWithMedia` — whose names literally contain "encode." Seed: an exact
    function-name substring hit must outrank unrelated symbols; surface the missing-`[semantic]`
    state at the point of use, not just as a flag.
7c. **The "inbound calls" metric is opaque/inflated.** "AppColors: 383 inbound calls" vs 271 literal
    grep usages (~40% over). The conclusion (most-central) is right; the number isn't quotable. Seed:
    reconcile the count to a verifiable definition, or label it an estimate.
7d. **Per-tool applicability hints.** `trace` (endpoint→handler→ORM) is dead weight on a P2P/non-web
    repo — honest but noise. Seed: a tool self-note like "no HTTP/ORM endpoints in this graph."

## The headline open question (publish gate)

8. **Autonomous usefulness (Q2) is unproven.** v0.7 confirmed *usable* and proved onboarding
   auto-discovery + skill routing + MCP value for *assisted analysis* — but no agent completed a
   real **end-to-end change** measurably faster/safer *because of* Deepdive. This is the one thing
   that must be true before publish. Seed: a dedicated autonomous-execution test on a multi-author,
   real-history, cross-stack repo (not a solo BLE app), measuring task completion vs a cold agent.

## Protocol / coverage carryover (still open from v0.6)

9. **gRPC Go / Java** servicer/stub shapes + the wire-path equivalence
   `/<package>.<Service>/<Method>` (v0.6 DEC-068 CAVEAT — needs the deferred `[proto]` extra);
   attribute-bound stubs (`self.stub = …`).
10. **AMQP DROP co-located non-match pair** + **Spring AMQP `@QueueBinding`** (promoted from v0.7
    DEC-074 — no single real repo had a co-located non-matching pair to prove the DROP path on
    real code; the federation seam).
11. **A DRF `DefaultRouter`/`SimpleRouter` real repo at scale** (v0.6 carryover; CRUD expansion is
    fixture-proven, wagtail used a custom router).

## Performance

12. **LadybugDB prepared-statement reuse** (~measured 1.28×) stays **deferred** — Kuzu deprecates
    the separate prepare+execute API; don't ship a dependency on a deprecated path (DEC-076).

## The two v1.0 fundamentals (unchanged placement)

- **Lane (i) incremental / persistent graph update → v1.0** — the last load-bearing fundamental for
  a Terminal-complete v1.0; DEC-051's line-free `node_id` is its no-migration seam.
- **GUI / IDE → its own complete research arc**, gated on the Q2 autonomous-usefulness answer above.
  Build nothing on the styled-CLI/MCP seams until that arc — the v0.7 usability gate explicitly
  blocks UI work until autonomous value is demonstrated.

## Non-goals (do not regress)

- No sixth protocol without real-repo demand. No new node type (DbTable/DEC-059 is the one
  exception). The 5-artifact + 9-MCP-tool contract is frozen. Pure-static, zero-LLM floor.
  Keystone: reuse `Endpoint`; never touch `base.join`/`trace`/emit/`serve` for a refinement.
  The cp1252 ASCII-degrade rule (DEC-078/080) covers **every** console glyph path — Typer help,
  one-off success marks, the style layer — not just the banner.
