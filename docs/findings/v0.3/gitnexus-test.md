# gitnexus — v0.3 real-repo test (v0.2 carryover)

The other §5.4 v0.2 debt (DEC-033 deferred `examples/gitnexus/`), paid in v0.3.
GitNexus is itself a code-graph tool built on LadybugDB — a pleasing meta-test:
forensic-deepdive analyzing the category's prior art. TypeScript-heavy monorepo.

## Run summary

| | |
|---|---|
| Date | 2026-05-30 |
| Repo | [abhigyanpatwari/GitNexus](https://github.com/abhigyanpatwari/GitNexus) (1,003 commits, 79 MB) |
| Tool version | v0.3 HEAD (`8ad4110`) |
| OS | Windows 11 |

### Timings

| Run | Time |
|---|---|
| cold `extract --force` | **13.3 s** |
| warm re-extract (cache hit) | **0.76 s** |

### Inventory & graph

- **719** files (657 TypeScript, 30 TSX, 18 JavaScript, 14 Python) · **4,109** Symbols · 848 Modules · 1,003 Commits · 146 Authors.
- Edges: **5,056 CALLS** · 275 MEMBER_OF · 2,928 IMPORTS · 2 EXTENDS · 5 IMPLEMENTS · **10,279 CO_CHANGES_WITH**.
- **AGENT_BRIEF 1,630 B** (≤5120 ✓).

### CALLS by confidence (the Item-C metric)

| confidence | count |
|---|---|
| EXTRACTED | 2,435 |
| INFERRED | 2,438 |
| AMBIGUOUS | **183** |

Only **3.6% AMBIGUOUS** — the cleanest ratio of the polyglot set. By `via`:
4,787 `bare` + **238 `this`** + 29 `self` + 2 `static`. The **238 `this.`
method calls** are TypeScript receiver-resolved by Item C (DEC-037 rule 1) —
edges v0.2 dropped entirely. INFERRED ≈ EXTRACTED (2,438 vs 2,435): half the
call graph is now method/receiver-resolved heuristic edges, honestly tagged.

## ✅ What worked

1. **Hybrid NL query** `"parse graph node symbol relationship"` (offline)
   surfaces the domain core across the monorepo's `gitnexus-shared` and
   `gitnexus` packages:
   - `gitnexus-shared/src/graph/types.ts::GraphRelationship`, `::GraphNode`
   - `…/ingestion/workers/parse-worker.ts::ParsedSymbol`, `::ParsedRelationship`
   - `…/scope-resolution/graph-bridge/node-lookup.ts::buildGraphNodeLookup`
   All INFERRED (multi-word query, no single exact-identifier match) — the
   lexical BM25 + camelCase tokenization pulling `GraphNode`/`ParsedSymbol`
   from the query words.
2. **TSX handled** alongside TS (30 `.tsx` files) — the React component files
   parse without special-casing.
3. **10,279 CO_CHANGES_WITH** — a dense co-change signal over a tightly-coupled
   monorepo; the archaeology layer scales.

## Notes / honest failures

- **Low EXTENDS/IMPLEMENTS (2 / 5)** for a TS codebase — TypeScript `interface`
  / `implements` and `extends` are under-captured relative to the language's
  use of them. The DEC-028 inheritance extractor is conservative for TS; richer
  TS interface/heritage-clause capture is a tracked follow-on (not a v0.3 gate
  item).
- The 14 Python files (tooling/scripts) are correctly inventoried and don't
  pollute the TS graph (language-scoped edges, DEC-012).
- A code-graph tool analyzing a code-graph tool: forensic-deepdive's
  per-edge confidence taxonomy + git-archaeology layer are exactly the two
  wedges GitNexus lacks (README competitive table) — visible here in the
  honest INFERRED/AMBIGUOUS split and the 10k co-change edges.
