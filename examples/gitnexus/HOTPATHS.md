# HOTPATHS — gitnexus

> The code most other code depends on, and the files that change most.
> **Confidence:** facts are `EXTRACTED` (deterministic from AST and git) unless a section / line says otherwise.

## Dependency hot spots

Symbols ranked by **distinct callers** — the count of distinct symbols with a `CALLS` edge into them (structural in-degree; the call-graph resolver). The load-bearing callees — signature changes touch every caller. The confidence mix is over the underlying call edges (a callee may have more edges than callers).

| Symbol | Defined in | Callers | Confidence mix |
| --- | --- | --- | --- |
| `syntheticCapture` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 53 | 260 `AMBIGUOUS` |
| `hasKeyword` | `gitnexus/src/core/ingestion/field-extractors/configs/helpers.ts` | 41 | 51 `AMBIGUOUS` |
| `nodeToCapture` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 38 | 53 `AMBIGUOUS` |
| `parseSourceSafe` | `gitnexus/src/core/tree-sitter/safe-parse.ts` | 28 | 31 `AMBIGUOUS` |
| `hasModifier` | `gitnexus/src/core/ingestion/field-extractors/configs/helpers.ts` | 22 | 34 `AMBIGUOUS` |
| `runCompiledPatterns` | `gitnexus/src/core/group/extractors/tree-sitter-scanner.ts` | 20 | 1 `EXTRACTED`, 68 `AMBIGUOUS` |
| `findNodeAtRange` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 19 | 77 `AMBIGUOUS` |
| `isClassLike` | `gitnexus/src/core/ingestion/scope-resolution/scope/walkers.ts` | 18 | 6 `EXTRACTED`, 15 `AMBIGUOUS` |
| `LocalBackend.ensureInitialized` | `gitnexus/src/mcp/local/local-backend.ts` | 17 | 17 `INFERRED` |
| `t` | `gitnexus/src/cli/i18n/index.ts` | 16 | 91 `AMBIGUOUS` |
| `compilePatterns` | `gitnexus/src/core/group/extractors/tree-sitter-scanner.ts` | 16 | 57 `AMBIGUOUS` |
| `findChild` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 16 | 96 `AMBIGUOUS` |
| `isClassLike` | `gitnexus/src/core/ingestion/languages/cpp/user-defined-conversions.ts` | 15 | 15 `AMBIGUOUS` |
| `extractVarName` | `gitnexus/src/core/ingestion/languages/rust/range-binding.ts` | 15 | 2 `EXTRACTED`, 66 `AMBIGUOUS` |
| `defineLanguage` | `gitnexus/src/core/ingestion/language-provider.ts` | 14 | 16 `AMBIGUOUS` |

## Cross-file dependencies

File-to-file dependencies aggregated from symbol-level `CALLS` edges (the call-graph resolver). Self-edges (intra-file calls) excluded.

| From | To | Calls | Top callee |
| --- | --- | --- | --- |
| `gitnexus/src/core/ingestion/languages/javascript/captures.ts` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 53 | `syntheticCapture` |
| `gitnexus/src/core/group/extractors/http-patterns/python.ts` | `gitnexus/src/core/group/extractors/tree-sitter-scanner.ts` | 44 | `compilePatterns` |
| `gitnexus/src/core/ingestion/languages/ruby/captures.ts` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 43 | `syntheticCapture` |
| `gitnexus/src/core/ingestion/type-extractors/jvm.ts` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 39 | `findChild` |
| `gitnexus/src/core/ingestion/languages/cpp/captures.ts` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 38 | `findNodeAtRange` |
| `gitnexus/src/core/ingestion/languages/kotlin/captures.ts` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 30 | `syntheticCapture` |
| `gitnexus/src/core/ingestion/type-extractors/dart.ts` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 27 | `findChild` |
| `gitnexus/src/core/group/extractors/http-patterns/java.ts` | `gitnexus/src/core/group/extractors/tree-sitter-scanner.ts` | 26 | `unquoteLiteral` |
| `gitnexus/src/core/ingestion/languages/php/captures.ts` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 25 | `syntheticCapture` |
| `gitnexus/src/core/ingestion/languages/typescript/captures.ts` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 25 | `syntheticCapture` |
| `gitnexus/src/core/ingestion/scope-resolution/passes/compound-receiver.ts` | `gitnexus/src/core/ingestion/scope-resolution/scope/walkers.ts` | 25 | `findClassBindingInScope` |
| `gitnexus/src/core/lbug/lbug-adapter.ts` | `gitnexus/src/core/lbug/lbug-config.ts` | 21 | `closeLbugConnection` |
| `gitnexus/src/cli/index.ts` | `gitnexus/src/cli/lazy-action.ts` | 19 | `createLbugLazyAction` |
| `gitnexus/src/core/group/extractors/http-patterns/node.ts` | `gitnexus/src/core/group/extractors/tree-sitter-scanner.ts` | 19 | `runCompiledPatterns` |
| `gitnexus/src/core/ingestion/languages/csharp/captures.ts` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 19 | `syntheticCapture` |

## Co-change clusters

_Confidence: `INFERRED`._

Files most frequently committed together. The shared-commit count is EXTRACTED from git; the implication 'these should change together' is the derivation.

| File A | File B | Shared commits |
| --- | --- | --- |
| `gitnexus/src/core/ingestion/parsing-processor.ts` | `gitnexus/src/core/ingestion/workers/parse-worker.ts` | 56 |
| `gitnexus/src/core/ingestion/call-processor.ts` | `gitnexus/src/core/ingestion/workers/parse-worker.ts` | 42 |
| `gitnexus/src/core/ingestion/call-processor.ts` | `gitnexus/src/core/ingestion/parsing-processor.ts` | 41 |
| `gitnexus/src/core/ingestion/call-processor.ts` | `gitnexus/src/core/ingestion/pipeline.ts` | 34 |
| `gitnexus/src/core/ingestion/call-processor.ts` | `gitnexus/src/core/ingestion/import-processor.ts` | 28 |
| `gitnexus/src/core/ingestion/import-processor.ts` | `gitnexus/src/core/ingestion/parsing-processor.ts` | 28 |
| `gitnexus/src/cli/analyze.ts` | `gitnexus/src/cli/index.ts` | 27 |
| `gitnexus/src/core/ingestion/call-processor.ts` | `gitnexus/src/core/ingestion/tree-sitter-queries.ts` | 27 |
| `gitnexus/src/core/ingestion/call-processor.ts` | `gitnexus/src/core/ingestion/type-env.ts` | 26 |
| `gitnexus/src/core/ingestion/parsing-processor.ts` | `gitnexus/src/core/ingestion/pipeline.ts` | 26 |

## Change hot spots

Files touched by the most commits (git churn).

| File | Commits |
| --- | --- |
| `gitnexus/package-lock.json` | 116 |
| `gitnexus/package.json` | 108 |
| `gitnexus/src/core/ingestion/workers/parse-worker.ts` | 86 |
| `gitnexus/src/core/ingestion/call-processor.ts` | 85 |
| `README.md` | 84 |
| `gitnexus/src/core/ingestion/parsing-processor.ts` | 70 |
| `gitnexus/src/mcp/local/local-backend.ts` | 61 |
| `gitnexus/src/cli/analyze.ts` | 59 |
| `gitnexus/src/core/ingestion/pipeline.ts` | 58 |
| `AGENTS.md` | 53 |
| `gitnexus/src/cli/index.ts` | 52 |
| `gitnexus-web/package-lock.json` | 49 |
| `gitnexus/src/core/ingestion/tree-sitter-queries.ts` | 49 |
| `gitnexus-web/package.json` | 48 |
| `gitnexus/src/core/ingestion/import-processor.ts` | 46 |

## Churn × centrality

_Confidence: `INFERRED`._

Files that are **both** highly depended-on and frequently changed — the riskiest edits in the repo. Commit counts are EXTRACTED; the centrality column and the risk framing are the derivation.

| File | Centrality | Commits |
| --- | --- | --- |
| `gitnexus/src/mcp/local/local-backend.ts` | 0.0036 | 61 |
| `gitnexus/src/core/ingestion/call-processor.ts` | 0.0015 | 85 |
| `gitnexus/src/core/ingestion/workers/parse-worker.ts` | 0.0011 | 86 |
| `gitnexus/src/core/ingestion/import-processor.ts` | 0.0010 | 46 |
| `gitnexus/src/cli/analyze.ts` | 0.0009 | 59 |
| `gitnexus/src/cli/index.ts` | 0.0009 | 52 |
| `gitnexus/src/core/ingestion/parsing-processor.ts` | 0.0009 | 70 |
| `gitnexus/src/core/ingestion/pipeline.ts` | 0.0009 | 58 |
| `gitnexus/src/core/lbug/lbug-adapter.ts` | 0.0009 | 42 |
| `gitnexus/src/server/api.ts` | 0.0009 | 43 |

---

*Generated by forensic-deepdive 0.9.0 on 2026-07-09. Regenerate with `forensic update` — do not hand-edit.*
