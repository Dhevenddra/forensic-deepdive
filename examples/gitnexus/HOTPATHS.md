# HOTPATHS — gitnexus

> The code most other code depends on, and the files that change most.
> **Confidence:** facts are `EXTRACTED` (deterministic from AST and git) unless a section / line says otherwise (DEC-015).

## Dependency hot spots

Symbols with the most inbound `CALLS` edges (DEC-025 resolver). The load-bearing callees — signature changes touch every caller.

| Symbol | Defined in | Callers | Confidence mix |
| --- | --- | --- | --- |
| `syntheticCapture` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 260 | 260 `INFERRED` |
| `findChild` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 96 | 96 `INFERRED` |
| `t` | `gitnexus/src/cli/i18n/index.ts` | 91 | 91 `INFERRED` |
| `findNodeAtRange` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 77 | 77 `INFERRED` |
| `runCompiledPatterns` | `gitnexus/src/core/group/extractors/tree-sitter-scanner.ts` | 69 | 1 `EXTRACTED`, 68 `INFERRED` |
| `extractVarName` | `gitnexus/src/core/ingestion/languages/rust/range-binding.ts` | 68 | 2 `EXTRACTED`, 66 `INFERRED` |
| `compilePatterns` | `gitnexus/src/core/group/extractors/tree-sitter-scanner.ts` | 57 | 57 `INFERRED` |
| `nodeToCapture` | `gitnexus/src/core/ingestion/utils/ast-helpers.ts` | 53 | 53 `INFERRED` |
| `hasKeyword` | `gitnexus/src/core/ingestion/field-extractors/configs/helpers.ts` | 51 | 51 `INFERRED` |
| `unquoteLiteral` | `gitnexus/src/core/group/extractors/tree-sitter-scanner.ts` | 46 | 46 `INFERRED` |
| `cliError` | `gitnexus/src/cli/cli-message.ts` | 36 | 1 `EXTRACTED`, 35 `INFERRED` |
| `hasModifier` | `gitnexus/src/core/ingestion/field-extractors/configs/helpers.ts` | 34 | 34 `INFERRED` |
| `parseSourceSafe` | `gitnexus/src/core/tree-sitter/safe-parse.ts` | 31 | 31 `INFERRED` |
| `capture` | `gitnexus/src/core/ingestion/languages/cobol/captures.ts` | 23 | 23 `EXTRACTED` |
| `findClassBindingInScope` | `gitnexus/src/core/ingestion/scope-resolution/scope/walkers.ts` | 23 | 23 `INFERRED` |

## Cross-file dependencies

File-to-file dependencies aggregated from symbol-level `CALLS` edges (DEC-025 resolver). Self-edges (intra-file calls) excluded.

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

_Confidence: `INFERRED` (DEC-015)._

Files most frequently committed together (DEC-027). The shared-commit count is EXTRACTED from git; the implication 'these should change together' is the derivation.

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

_Confidence: `INFERRED` (DEC-015)._

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

*Generated by forensic-deepdive 0.1.0 on 2026-05-30. Regenerate with `forensic update` — do not hand-edit.*
