# ripgrep — v0.3 real-repo test (the Rust acceptance)

First **real Rust repo** run — the §4.7 gate check #6 ("Rust fixture + one
real Rust repo parsed correctly"). Exercises Item D (DEC-040 Rust support)
wired into Item C (DEC-037 receiver-type method resolution) from day one.

## Run summary

| | |
|---|---|
| Date | 2026-05-30 |
| Repo | [BurntSushi/ripgrep](https://github.com/BurntSushi/ripgrep) (2,149 commits, 9.6 MB) |
| Tool version | v0.3 HEAD (`8ad4110`) |
| OS | Windows 11 |

### Timings

| Run | Time |
|---|---|
| cold `extract --force` | **5.5 s** |
| warm re-extract (cache hit) | **0.04 s** |

### Inventory & graph

- **84** Rust files · **3,077** Symbols · 242 Modules · 2,149 Commits · 475 Authors.
- Edges: **2,950 CALLS** · 1,624 MEMBER_OF · 342 IMPORTS · **0 EXTENDS** · **111 IMPLEMENTS** · 1,216 CO_CHANGES_WITH.
- **AGENT_BRIEF 1,275 B** (≤5120 ✓).

### The Rust-specific wins (DEC-040)

- **`impl` methods attribute to their type** — 1,624 MEMBER_OF edges. The
  non-lexical `impl_item` → `type:` binding (the load-bearing introspection
  finding) works at scale: methods land under `SearchWorker`, `LineBuffer`,
  `HiArgs`, etc., not as free functions.
- **`impl Trait for Type` ⇒ IMPLEMENTS** — 111 edges. **0 EXTENDS** is correct
  (Rust has no struct inheritance) — the taxonomy isn't manufacturing edges.

### CALLS by confidence (the Item-C metric)

| confidence | count |
|---|---|
| EXTRACTED | 1,361 |
| INFERRED | 1,212 |
| AMBIGUOUS | 377 |

### CALLS by `via` — **the headline**

| via | count | meaning |
|---|---|---|
| `bare` | 1,422 | DEC-025 bare-name calls |
| `self` | **517** | `self.method()` → impl member (DEC-037 rule 1) |
| `static` | **1,011** | `Type::new()` Rust associated calls (DEC-040 + DEC-037 rule 2) |

**1,528 method-call edges** (`self` + `static`) that **v0.2 would have dropped
entirely** (`_drop_method`). This is soft-spot #2 closed on real Rust: the call
graph is no longer mostly-missing for method-heavy code. The 1,212 INFERRED +
377 AMBIGUOUS are exactly those recovered edges, honestly tagged (AMBIGUOUS =
cross-file `Type::assoc()` with 2+ candidate owner types).

## ✅ What worked

1. **Hybrid NL query** `"search matcher line buffer"` (offline) returns the
   right implementation symbols, all **EXTRACTED** (exact-identifier hits) with
   `[lexical, structural]` provenance:
   - `core/main.rs::search`, `core/search.rs::SearchWorker<W>.search`,
     `searcher/src/line_buffer.rs::LineBuffer.buffer`,
     `core/flags/hiargs.rs::HiArgs.matcher`.
2. **Generic types survive** in qualified names (`SearchWorker<W>.search`) —
   the resolver keys on the type and the member cleanly.
3. **Mermaid** central flowchart renders bounded (12 nodes).

## Notes / honest failures

- **`new` is everywhere** — the `--central` Mermaid sample is dominated by
  `new` constructors (many `impl` blocks each define `fn new`). Honest but
  low-signal; a future centrality tie-break on qualified name (not leaf) would
  read better. Tracked, not a correctness bug.
- **`mod` / `macro_rules!` are not symbolized** (DEC-040 deferral) — ripgrep
  uses macros sparingly, so call-graph impact is small here; Cargo-aware module
  resolution is v0.6.
- 377 AMBIGUOUS (12.8% of CALLS) — cross-crate associated calls where the same
  `fn new`/`fn build` exists on multiple types. The taxonomy surfaces every
  candidate rather than guessing (DEC-037), which is the intended behavior.

**Gate check #6: PASS** — real Rust repo parsed correctly, impl methods
attributed, IMPLEMENTS edges present, `self`/`static` method calls resolved.
