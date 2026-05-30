# HOTPATHS — ripgrep

> The code most other code depends on, and the files that change most.
> **Confidence:** facts are `EXTRACTED` (deterministic from AST and git) unless a section / line says otherwise (DEC-015).

## Dependency hot spots

Symbols with the most inbound `CALLS` edges (DEC-025 resolver). The load-bearing callees — signature changes touch every caller.

| Symbol | Defined in | Callers | Confidence mix |
| --- | --- | --- | --- |
| `parse_low_raw` | `crates/core/flags/parse.rs` | 545 | 545 `EXTRACTED` |
| `SearcherBuilder.new` | `crates/searcher/src/searcher/mod.rs` | 123 | 123 `INFERRED` |
| `RegexMatcher.new` | `crates/searcher/src/testutil.rs` | 113 | 7 `INFERRED`, 106 `AMBIGUOUS` |
| `RegexMatcher.new` | `crates/pcre2/src/matcher.rs` | 106 | 106 `AMBIGUOUS` |
| `RegexMatcher.new` | `crates/regex/src/matcher.rs` | 106 | 106 `AMBIGUOUS` |
| `StandardBuilder.new` | `crates/printer/src/standard.rs` | 86 | 86 `INFERRED` |
| `printer_contents` | `crates/printer/src/standard.rs` | 78 | 78 `EXTRACTED` |
| `SearcherTester.new` | `crates/searcher/src/testutil.rs` | 55 | 55 `INFERRED` |
| `wfile` | `crates/ignore/src/walk.rs` | 41 | 41 `EXTRACTED` |
| `wfile` | `crates/ignore/src/dir.rs` | 33 | 33 `EXTRACTED` |
| `assert_paths` | `crates/ignore/src/walk.rs` | 30 | 30 `EXTRACTED` |
| `StandardImpl<'a, M, W>.config` | `crates/printer/src/standard.rs` | 25 | 25 `INFERRED` |
| `Match.new` | `crates/matcher/src/lib.rs` | 24 | 24 `INFERRED` |
| `IgnoreBuilder.new` | `crates/ignore/src/dir.rs` | 23 | 23 `INFERRED` |
| `WalkBuilder.new` | `crates/ignore/src/walk.rs` | 22 | 22 `INFERRED` |

## Cross-file dependencies

File-to-file dependencies aggregated from symbol-level `CALLS` edges (DEC-025 resolver). Self-edges (intra-file calls) excluded.

| From | To | Calls | Top callee |
| --- | --- | --- | --- |
| `crates/core/flags/defs.rs` | `crates/core/flags/parse.rs` | 545 | `parse_low_raw` |
| `crates/printer/src/standard.rs` | `crates/searcher/src/searcher/mod.rs` | 89 | `SearcherBuilder.new` |
| `crates/printer/src/standard.rs` | `crates/pcre2/src/matcher.rs` | 80 | `RegexMatcher.new` |
| `crates/printer/src/standard.rs` | `crates/regex/src/matcher.rs` | 80 | `RegexMatcher.new` |
| `crates/printer/src/standard.rs` | `crates/searcher/src/testutil.rs` | 76 | `RegexMatcher.new` |
| `crates/searcher/src/searcher/glue.rs` | `crates/searcher/src/testutil.rs` | 60 | `SearcherTester.new` |
| `crates/printer/src/summary.rs` | `crates/pcre2/src/matcher.rs` | 18 | `RegexMatcher.new` |
| `crates/printer/src/summary.rs` | `crates/regex/src/matcher.rs` | 18 | `RegexMatcher.new` |
| `crates/printer/src/summary.rs` | `crates/searcher/src/searcher/mod.rs` | 18 | `SearcherBuilder.new` |
| `crates/printer/src/summary.rs` | `crates/searcher/src/testutil.rs` | 18 | `RegexMatcher.new` |
| `crates/ignore/src/dir.rs` | `crates/ignore/src/gitignore.rs` | 15 | `Gitignore.empty` |
| `crates/core/flags/defs.rs` | `crates/core/flags/lowargs.rs` | 12 | `ContextMode.default` |
| `crates/printer/src/standard.rs` | `crates/matcher/src/lib.rs` | 11 | `Match.new` |
| `crates/globset/src/lib.rs` | `crates/globset/src/glob.rs` | 10 | `Glob.new` |
| `crates/ignore/src/gitignore.rs` | `crates/ignore/src/pathutil.rs` | 10 | `strip_prefix` |

## Co-change clusters

_Confidence: `INFERRED` (DEC-015)._

Files most frequently committed together (DEC-027). The shared-commit count is EXTRACTED from git; the implication 'these should change together' is the derivation.

| File A | File B | Shared commits |
| --- | --- | --- |
| `crates/printer/src/standard.rs` | `crates/printer/src/util.rs` | 14 |
| `crates/printer/src/standard.rs` | `crates/printer/src/summary.rs` | 13 |
| `crates/globset/src/glob.rs` | `crates/globset/src/lib.rs` | 12 |
| `crates/regex/src/config.rs` | `crates/regex/src/matcher.rs` | 12 |
| `crates/printer/src/json.rs` | `crates/printer/src/standard.rs` | 11 |
| `crates/printer/src/json.rs` | `crates/printer/src/summary.rs` | 11 |
| `crates/printer/src/summary.rs` | `crates/printer/src/util.rs` | 11 |
| `crates/printer/src/lib.rs` | `crates/printer/src/standard.rs` | 10 |
| `crates/printer/src/lib.rs` | `crates/printer/src/summary.rs` | 10 |
| `crates/regex/src/literal.rs` | `crates/regex/src/matcher.rs` | 10 |

## Change hot spots

Files touched by the most commits (git churn).

| File | Commits |
| --- | --- |
| `Cargo.lock` | 476 |
| `CHANGELOG.md` | 289 |
| `Cargo.toml` | 233 |
| `README.md` | 177 |
| `src/args.rs` | 162 |
| `src/app.rs` | 123 |
| `tests/tests.rs` | 118 |
| `ignore/src/types.rs` | 114 |
| `crates/ignore/src/default_types.rs` | 97 |
| `src/main.rs` | 88 |
| `tests/regression.rs` | 69 |
| `crates/grep/Cargo.toml` | 60 |
| `doc/rg.1.md` | 60 |
| `ignore/Cargo.toml` | 59 |
| `src/printer.rs` | 59 |

## Churn × centrality

_Confidence: `INFERRED` (DEC-015)._

Files that are **both** highly depended-on and frequently changed — the riskiest edits in the repo. Commit counts are EXTRACTED; the centrality column and the risk framing are the derivation.

| File | Centrality | Commits |
| --- | --- | --- |
| `crates/ignore/src/default_types.rs` | 0.0093 | 97 |

---

*Generated by forensic-deepdive 0.1.0 on 2026-05-30. Regenerate with `forensic update` — do not hand-edit.*
