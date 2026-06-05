# gitnexus — v0.4 real-repo test (TS-heritage before/after)

Re-run of the v0.3 carryover to measure **Item B / DEC-050** (TS/TSX heritage
capture). GitNexus is a TypeScript-heavy monorepo (and itself a code-graph tool
on LadybugDB) — the right stress test for `extends`/`implements` recovery. The
v0.3 finding flagged "low EXTENDS/IMPLEMENTS (2/5) for a TS codebase" as a
tracked follow-on; v0.4 Item B is that follow-on.

## Run summary

| | |
|---|---|
| Date | 2026-06-05 |
| Repo | [abhigyanpatwari/GitNexus](https://github.com/abhigyanpatwari/GitNexus) (same checkout as v0.3, `f5915ca9`) |
| Tool version | v0.4 HEAD (`a5b3e02`) |
| OS | Windows 11 |
| cold `extract --force` | **36.9 s** |

### Inventory & graph (v0.4)

- **719** files (TS/TSX/JS/Py) · **4,109** Symbols — unchanged vs v0.3 (no new
  files; the deltas below are pure capture improvements on the same corpus).
- **AGENT_BRIEF 1,630 B** (≤5120 ✓).

## The TS-heritage story (Item B / DEC-050) — gate #4

| heritage edges | v0.3 (`8ad4110`) | v0.4 (`a5b3e02`) | Δ |
|---|---|---|---|
| EXTENDS | 2 | **21** | **+19 (10.5×)** |
| IMPLEMENTS | 5 | 5 | — |
| **total** | **7** | **26** | **+271 %** |

EXTENDS jumps **2 → 21** — DEC-050 closed the four silent drops in
`inheritance._ts_js_extract`: `abstract_class_declaration` (a distinct node from
`class_declaration`), `interface_declaration > extends_type_clause`
(interface→interface, never previously visited), `generic_type` targets
(`extends Base<T>`), and `member_expression` targets (`extends React.Component`).
The capture is **additive** (simple `class A extends B` cases are byte-identical),
so the +19 is genuine recovery, not churn. Confidence stays resolution-assigned
(external supertypes drop; intra-repo single-match → INFERRED).

IMPLEMENTS holds at 5: gitnexus leans on `extends` (incl. interface-extends) far
more than `implements` clauses, so the heritage gain lands almost entirely in
EXTENDS — consistent with the codebase's actual shape, not a capture gap.

## Cross-stack (Items F/G) — honest zero ROUTES_TO

v0.4's provider extractors now detect **22 Endpoints + 21 HANDLES** in gitnexus's
server code, but there are **0 CALLS_ENDPOINT and 0 ROUTES_TO**: the in-repo
frontend doesn't call those routes through a shape the consumer extractors match
(server and client are decoupled here). The cross-stack layer reports this
honestly — endpoints surface as provider-side facts, no fabricated joins. One
endpoint is documented-but-unlocated (no resolvable handler).

## CALLS by confidence (Item-C carry, unchanged)

| confidence | count |
|---|---|
| EXTRACTED | 2,435 |
| INFERRED | 2,438 |
| AMBIGUOUS | **183 (3.6 %)** |

Identical to v0.3 — Item B touched only the heritage extractor (`PARSER_VERSION`
bump invalidated the parse cache), not call resolution. Still the cleanest
AMBIGUOUS ratio of the set.

## Assessment

- **Gate #4 (TS heritage materially up): ✅** EXTENDS+IMPLEMENTS **7 → 26**
  (+271 %), driven by the DEC-050 abstract-class / interface-extends / generic /
  member-expression captures.
- AGENT_BRIEF ≤5kb ✅. Determinism unaffected (re-run byte-identical). The
  remaining IMPLEMENTS conservatism is a true reflection of the codebase, not an
  extractor gap.
