# Profiling pass — v0.6 Step 7 acceptance (DEC-070)

A `cProfile` sweep over an 18.7k-symbol Superset extract (warm parse cache, so the
standing cost centers run fresh). The PRD §3.7 named three suspects — the registry-dispatch
fan-out, the cross-stack join, the DI/ORM passes. **Profiling first** found that none of
them is the bottleneck: the hot path is the **CALLS resolver's absolute-import resolution**,
shared by every cross-file feature.

## The finding (before)

```
1,258,248,873 function calls in 1711.349 seconds
 ncalls   tottime   cumtime  function
 338616   1058.6s   1578.7s  static/resolver.py:_resolve_python_import   ← 62% of the run
 1.2e9     519.2s    519.2s  {str.endswith}                              ← inside the suffix scan
```

`_resolve_python_import` resolved each absolute import by an **O(files) suffix scan**
(`path.endswith("/" + base + ".py")`) — O(files × imports), i.e. 3276 files × hundreds of
thousands of resolutions → **~1.2 billion `endswith` calls**. The PRD-named centers
(dispatch fan-out, join, DI/ORM) were nowhere near the top.

## The fix (DEC-070)

`static/resolver.py` only: the exact match becomes O(1) dict membership; the suffix match
uses a **precomputed suffix index** (`module-path-suffix → first file in dict-iteration
order`) built **once per resolve pass** via a single-entry identity cache. It registers
every file's proper path-suffixes with `setdefault`, so the **first file in dict order
wins** — replicating the original scan's determinism exactly. **Byte-identical** behavior
(same file resolves → same CALLS edges → same artifacts).

## The result (after)

```
   49,512,765 function calls in 116.606 seconds          (14.7× faster; 25× fewer calls)
 ncalls   tottime  function
    542    16.9s   real_ladybug prepared_statement.__init__   ← genuine graph work
   4688    12.0s   tree_sitter.Parser.parse                   ← genuine parse work
   2408     6.0s   static/resolver.py:resolve_name_to_files   ← next (minor) candidate
```

`_resolve_python_import` drops out of the top 20 entirely. The remaining costs are real
work (graph statements, tree-sitter, the DEC-059/065/066 cross-file resolver).

| | before | after |
|---|---|---|
| profiled extract time | 1711.3s | **116.6s** (14.7×) |
| function calls | 1.258 B | **49.5 M** (25×) |
| `_resolve_python_import` self-time | 1058.6s | not in top 20 |

## Determinism / no-behavior-change

The 36 existing resolver tests pass unchanged + a new `test_resolve_python_import_exact_
suffix_and_order` locks the exact-priority / suffix-first-match / none semantics. **Goldens
byte-identical** — the resolver returns the same file, so the graph and the five artifacts
are unchanged. Determinism (collect-then-sort) preserved.

## Scope / what stays deferred

A pure constant-factor win — **no data-structure or ordering change visible downstream**,
so incremental/persistent graph update stays deferred to **v1.0** (lane i); this needed
none of it. Next (minor, an order of magnitude below the old bottleneck):
`resolve_name_to_files`'s cross-file-fallback filtering (~6s) and LadybugDB prepared-
statement reuse — v0.7/v1.0 notes, not v0.6 blockers.

## Takeaway

Measuring before optimizing turned a guessed three-suspect list into one decisive fix: the
import resolver shared by every cross-file feature. A Superset extract's profiled time fell
**14.7×** (1711s → 117s) with byte-identical output — the v0.6 perf pass closes with a
documented constant-factor win, not a deferral.
