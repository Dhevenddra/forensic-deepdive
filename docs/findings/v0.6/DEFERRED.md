# v0.6 → v0.7 carryover ledger (the seeds)

The honest shortfalls + deferrals v0.6 surfaced (reported, never fabricated) — the raw
material for the v0.7 plan, mirroring how `../v0.5/DEFERRED.md` seeded v0.6. Each is an
extractor/resolver-level item on the **unchanged** five-protocol spine unless noted.

## Findings-driven (surfaced by real-repo runs)

1. **Django `include(<variable>)` recursion** (DEC-065). Only string `include('app.urls')`
   recurses; a variable-bound mount (`include(api_urls)`) is treated as a root, so its
   routes emit at **bare paths missing the parent prefix**. On wagtail, 9 endpoints
   collapsed on a shared path (routes/handlers still correct, prefix dropped). Fix:
   resolve the variable to its bound `urlpatterns` list (extends the include-graph root
   detection, not the join). *This is the GitNexus #1183 shape's last mile.*
2. **AMQP literal-key real repo** (DEC-067). The matcher (exact→EXTRACTED / wildcard→
   INFERRED / non-match→DROP / multi→AMBIGUOUS) is fixture-proven; the rabbitmq-tutorials
   use **dynamic** `sys.argv` keys → all INFERRED (honest). A real topic app with literal
   routing keys would exercise the EXTRACTED/DROP paths on real code.
3. **A DRF default-router real repo** (DEC-065). wagtail uses a custom `WagtailAPIRouter`
   (correctly not CRUD-expanded). The DRF `DefaultRouter`/`SimpleRouter` CRUD expansion is
   fixture-proven; a real DRF app would stress it at scale.

## Protocol-coverage deferrals

4. **gRPC Go / Java** servicer/stub shapes + the **wire-path equivalence**
   `/<package>.<Service>/<Method>` (DEC-068, the recorded CAVEAT — INFERRED, would need the
   deferred `[proto]` extra). Stubs bound as attributes (`self.stub = …`) also deferred.
5. **JAX-RS** interface/abstract-return locator impl selection (DEC-066, stays
   AMBIGUOUS-unmatched); `@ApplicationPath` app-prefix; `@Produces`/`@Consumes`.
6. **Django** class-based-view per-method (`get`/`post`) verb extraction; deep
   `pkg.sub.views.fn` view paths (DEC-065, best-effort trailing-name only); DRF `@action`
   detail/list routes.

## Memory (lane-iii follow-ons)

7. **`[semantic]` ONNX RRF fusion over insights** (DEC-069 — the optional layer; recall is
   FTS5/BM25-only today) + an **FSRS-style decay score** (deferred, off the LLM path).
8. **Auto-push the shadow-ref** to a remote (DEC-069 syncs the local ref only).

## Performance (DEC-070 follow-ons)

9. **`resolve_name_to_files` cross-file-fallback filtering** — the next profiling hot spot
   (~6s on Superset, an order of magnitude below the old `_resolve_python_import`
   bottleneck) could take a similar suffix index.
10. **LadybugDB prepared-statement reuse** (~17s on Superset) — a graph-layer perf item.

## The two v1.0 fundamentals (unchanged placement)

- **Lane (i) incremental/persistent graph update → v1.0** — the last load-bearing
  fundamental for Terminal-complete v1.0; DEC-051's line-free `node_id` is its
  no-migration seam. The v0.6 perf pass confirmed it isn't needed for constant-factor wins.
- **GUI/IDE → its own complete research arc** once the foundations are strong. The v0.5/v0.6
  seams (five-protocol coverage hardened, the data-layer reach) are laid clean — build
  nothing on them until that arc.

## Non-goals (do not regress)

- No sixth protocol without real-repo demand. No new node type (DbTable/DEC-059 is the one
  exception). The 5-artifact + 9-MCP-tool contract is frozen. Pure-static, zero-LLM floor.
  Keystone: reuse `Endpoint`; never touch `base.join`/`trace`/emit/`serve` for a refinement.
