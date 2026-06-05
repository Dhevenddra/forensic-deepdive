# fastapi — v0.4 real-repo test (`example`-role before/after)

Re-run of the v0.3 carryover to measure **Item C / DEC-049** (the `example`
file-role). The v0.3 finding diagnosed FastAPI's **36 % AMBIGUOUS** as almost
entirely a `docs_src/` artifact — hundreds of tutorial files each redefining the
same names (`read_item`, `get_db`, `dependency_a`…) across `tutorial001`,
`tutorial001_an`, … — and logged "classify `docs_src/`-style examples as a
non-source role" for v0.4. Item C is that fix.

## Run summary

| | |
|---|---|
| Date | 2026-06-05 |
| Repo | [fastapi/fastapi](https://github.com/fastapi/fastapi) (same checkout as v0.3, `ee22a4b8c`) |
| Tool version | v0.4 HEAD (`a5b3e02`) |
| OS | Windows 11 |
| cold `extract --force` | **50.4 s** |

## The `example`-role story (Item C / DEC-049) — gate #5

### File reclassification

| role | v0.3 | v0.4 |
|---|---|---|
| source | 524 (all) | **75** |
| example | 0 | **449** |

**449 of 524 files (86 %)** are now classified `example` — the `docs_src/`
tutorials. They stay *in the graph* (graph corpus = source ∪ example, so the
2,986-symbol graph is unchanged) but are demoted two ways: PageRank teleport
weight 0.1 and query-shaping `_ROLE_FACTOR["example"] = 0.4`.

### The shaped-query result (the actual gate)

The raw CALLS AMBIGUOUS ratio is **still 36.1 %** — by design: DEC-049 demotes
examples in *ranking*, it doesn't delete their edges. The gate is about what the
agent actually *sees*. Re-running the v0.3 baseline query
`"create application route dependency injection"` (offline, `degraded=True`,
lexical+structural):

| metric | v0.3 | v0.4 |
|---|---|---|
| top-10 hits | core `routing.py` lifted, but `docs_src/` in the tail | **all 10 library `source`** |
| role split (25 hits) | tutorial-heavy tail | **20 source / 5 example** (examples only in positions 13–25) |
| **AMBIGUOUS % of shaped results** | — | **0.0 %** |

Top hits, v0.4:

```
EXTRACTED  fastapi/routing.py::APIRouter.route
INFERRED   fastapi/routing.py::APIRouter
INFERRED   fastapi/routing.py::APIRouter.api_route
INFERRED   fastapi/routing.py::APIRouter.include_router
INFERRED   fastapi/dependencies/utils.py::SolvedDependency
INFERRED   fastapi/routing.py::APIRouter.websocket_route
…
```

The `_ROLE_FACTOR` demotion pushes every `docs_src/` tutorial below the library
implementation — **top hits are library, not tutorial**, and the shaped results
carry **zero AMBIGUOUS** (the ambiguity lives in the demoted example tail).

## Cross-stack (Items F/G) — internal routes, honestly AMBIGUOUS

FastAPI's own test/example apps define many routes, so v0.4 finds **93 Endpoints,
406 HANDLES, 8 CALLS_ENDPOINT (7 EXTRACTED / 1 INFERRED), and 14 ROUTES_TO — all
AMBIGUOUS**. The all-AMBIGUOUS ROUTES_TO is correct: the example apps reuse the
same paths (`/items/{id}`, `/users/`) across dozens of tutorial files, so each
consumer matches multiple providers → AMBIGUOUS-all (DEC-047), never a fabricated
unique join. One endpoint is documented-but-unlocated. No spec files → 0
spec-backed (the Item-I shortcut is showcased on a dedicated repo, not here).

## CALLS by confidence (unchanged)

| confidence | count |
|---|---|
| EXTRACTED | 694 |
| INFERRED | 536 |
| AMBIGUOUS | 694 (36.1 %) |

## Assessment

- **Gate #5 (`example` role): ✅** Shaped-result AMBIGUOUS **0.0 %** (materially
  below the 36 % bar); **top-10 hits all library**, tutorials demoted to the
  tail. 449 files reclassified source→example.
- AGENT_BRIEF **1,644 B** ≤5120 ✅. The raw 36.1 % CALLS ratio is preserved (and
  documented) — DEC-049 fixes *what the agent ranks*, not the underlying
  honestly-ambiguous edges.
