# Performance pass — v0.7 Step 5 acceptance (DEC-076)

The #5 v0.6 carryover seed. The DEC-070 profiling pass fixed the dominant cost
(`_resolve_python_import`, 62% → indexed) and named two residuals: `resolve_name_to_files`
(~6s) and the LadybugDB statement work (~17s). DEC-076 addresses them — **byte-identical
output**, `static/resolver.py` + the graph adapter only.

## (a) `resolve_name_to_files` suffix/rel_path index — landed (49.7× on the hot path)

`resolve_name_to_files` (the shared cross-file name resolver behind EXTENDS/IMPLEMENTS,
INJECTS, and the Django/JAX-RS route-view resolution) scanned **all** imports on every call
to find the ones declared in the current file — an O(all imports) inner loop per resolved
name, i.e. O(imports × names) over a pass. DEC-076 indexes imports **by `rel_path` once per
pass** (`_imports_by_rel_path`, the DEC-070 single-entry **identity cache** keyed on the
`imports` list's identity), turning each call into an O(imports-in-this-file) lookup.

| measure | result |
|---|---|
| micro-benchmark (600 files, ~4.8k imports, 12k resolutions) | old scan **2.369s** → indexed **0.048s** = **49.7×** |
| result equality (new vs old, every query) | **0 mismatches / 12,000** |

**Byte-identical:** the per-file list preserves the original list order, so the same imports
are visited in the same order and `imp_matches` (hence the resolved files + confidence) is
unchanged. The cross-file fallback tiers (EXTRACTED import / INFERRED unique / AMBIGUOUS
several) are untouched. Proven by the 0-mismatch benchmark, a new order-preservation +
identity-cache-rebuild unit test, and the byte-identical goldens.

## (b) LadybugDB prepared-statement reuse — measured, consciously deferred (deprecated upstream)

The graph adapter's `_batch_execute` re-calls `conn.execute(query, {"rows": chunk})` per
UNWIND chunk. Reusing a prepared statement across chunks **does** help — benchmarked at
**1.28×** on a 30k-row / 30-chunk insert (≈0.32s saved; parse-overhead only, not the genuine
insert work). **But `real_ladybug` (Kuzu) explicitly deprecates the separate prepare +
execute pattern** — its own `DeprecationWarning` steers callers to a single `execute()` call
(which is the path the adapter already uses). Adopting a deprecated upstream API for a
**publish-prep** release trades a small constant-factor gain for future fragility (the API
may be removed), exactly the kind of unsafe win the DEC-070 pass declined. So (b) is
**measured and deferred**: the ~17s LadybugDB time is largely genuine insert work, and the
only available reuse mechanism is deprecated. Promoted to a v0.8 note (revisit if
`real_ladybug` exposes a non-deprecated statement-cache, or if lane-(i) incremental update
makes write volume the bottleneck).

## Real-repo behavior preservation — spring-petclinic

A full extract with the DEC-076 resolver: **143 symbols, 6 INJECTS, 6 PERSISTS_TO**
(extract 2.8s) — exactly the documented v0.5/v0.6 numbers. The INJECTS resolution flows
through `resolve_name_to_files`, so the unchanged counts confirm the index is
behavior-preserving on real code, not just on fixtures.

## Keystone / floor

`static/resolver.py` (the index + identity cache) only for the landed win; **no graph
adapter change** (b deferred). `base.join`/`trace`/emit/`serve` untouched; the 5-artifact /
9-tool contract frozen; **goldens byte-identical**. Incremental/persistent update stays
deferred to v1.0 (this is a pure constant-factor pass). Test:
`test_resolve_name_to_files_indexed_preserves_order_and_tiers` (+ the existing 26 resolver
tests unchanged).

## Takeaway

The named ~6s resolver residual is removed with a byte-identical 49.7×-on-the-hot-path index
(the DEC-070 pattern applied a second time), and the LadybugDB statement candidate is
honestly measured (1.28×) but declined because its only mechanism is deprecated upstream —
a measurable, safe speedup shipped; an unsafe one documented and deferred.
