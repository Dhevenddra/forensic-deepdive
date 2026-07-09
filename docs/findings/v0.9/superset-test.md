# superset — v0.9 (the flagship: does the interactive release change the analysis?)

`forensic extract C:/Dev/scratch/superset --force` @ **0.9.0**. Superset is the scale + cross-stack
flagship (TS/TSX frontend against a Python Flask-AppBuilder backend). v0.9 is a *completion*
release — it adds four interactive surfaces and removes a class of dangling reference from the
emitted artifacts. The single most important question this run answers is therefore a **negative**
one: *did any of that move the analysis?*

- **Scale/shape:** 3,862 source files (Typescript 1405, Python 1319, Tsx 1077, Javascript 61),
  graph **3,871 files / 18,764 symbols / 16,816 `CALLS` edges**, **1,078 Endpoints**.
  AGENT_BRIEF 1894 b (cap 5120).

## Result 1 — the analysis is unchanged (the headline)

| Metric | v0.8.0 | v0.9.0 | |
|---|---|---|---|
| Cross-stack routes (`ROUTES_TO`) | 62 | **62** | ✅ |
| Confidence mix (E / I / A) | 54 / 8 / 0 | **54 / 8 / 0** | ✅ |
| Symbol-graph files | 3276 | 3276 | ✅ |
| Dependency edges | 10215 | 10215 | ✅ |

Queried straight off the graph, not off the (top-N truncated) HOTPATHS table:

```cypher
MATCH ()-[r:ROUTES_TO]->() RETURN r.confidence, count(r)
-- [['EXTRACTED', 54], ['INFERRED', 8]]
```

**0 AMBIGUOUS** still holds on the flagship — the DEC-083 precision result from v0.8 is not a
fluke of that build. The `git diff` over `examples/superset/` is 36 lines, and *every one* is
either a version footer, a DEC-107 wording change, or a DEC-104 display name. No count, table
row, ranking, or confidence tag moved. That is the evidence behind the 0.9.0 CHANGELOG's claim
that engine, graph and contract are untouched.

## Result 2 — no internal ledger IDs in emitted output (DEC-107), verified

The explicit check this release exists to pass:

```bash
grep -rn "DEC-[0-9]" C:/Dev/scratch/superset/docs/codebase/   # → no matches (exit 1)
grep -rn "DEC-[0-9]" examples/                                # → no matches, all 11 repos
```

Before this run `examples/superset/` alone carried **24** `DEC-NNN` tokens across its five
artifacts (`DEC-012/015/021/022/025/027/043/049`). `DECISIONS.md` is gitignored and never ships,
so each was a **dangling reference for every consumer** — an agent reading superset's AGENT_BRIEF
would have been pointed at a ledger it can never resolve. The sweep across all of `examples/`
now reports **0 tokens** (was 211 at the start of the arc).

The provenance survived the de-leak as self-contained English. HOTPATHS went from
*"structural in-degree; DEC-025 resolver"* to *"structural in-degree; the call-graph resolver"* —
the reader still learns **where the claim comes from**, without a key to a book they don't have.

## Result 3 — DEC-104 fires here, on real code

Superset is the repo that exercises the `<module>` display fix. Its Cypress support module makes
module-scope HTTP calls, so the cross-stack table used to read:

| before (0.8.0) | after (0.9.0) |
|---|---|
| `superset-frontend/cypress-base/cypress/support/e2e.ts::<module>` | `superset-frontend.cypress-base.cypress.support.e2e` |

…for four rows against `ChartRestApi.bulk_delete` / `.delete` / `DashboardRestApi.bulk_delete` /
`.delete`, plus `AnnotationLayer.tsx::<module>` → `superset-frontend.src.explore.components.
controls.AnnotationLayerControl.AnnotationLayer`. **Zero** literal `<module>` strings remain in
HOTPATHS or AGENT_BRIEF.

Crucially the *joins are identical*: same handler, same endpoint key (`http::DELETE::/api/v1/chart`),
same `EXTRACTED` tag. Display changed; identity did not. `forensic trace --json` still emits the
raw qualified name, because that is the join id agents key off.

## Result 4 — DEC-103 fires here too (unexpectedly)

MAP's headline now reads:

> **Source files:** 3,862 (+9 in graph, demoted as examples/)

Superset has nine `examples/`-segment files. At v0.8 the line read a bare `3,862` and they vanished
from the headline with no trace. The annotation is small here (9 of 3,871), but it is the same
mechanism that made grpc-examples report "3 source files" for a 117-file repo.

Across the eleven example repos, **4 are annotated and 7 print the plain, unannotated line** — so
the change is genuinely conditional on `example_file_count > 0`, not a blanket reformat:

| annotated | plain |
|---|---|
| fastapi `75 (+449)` · omi `2,113 (+36)` · superset `3,862 (+9)` · ripgrep `81 (+3)` | gitnexus · grpc-route-guide · hermes-agent · jersey-helloworld · nestjs-cats-app · rabbitmq-tutorials · spring-petclinic |

**fastapi is the case that vindicates DEC-103**: 75 "source" files against **449** demoted ones.
Its headline previously understated the analyzed surface by 6×.

## Interactive surfaces at this scale

Not scriptable in CI (they need a real console), so they are checked by hand per
`docs/v0.9/MANUAL_TEST.md` §11. What *is* asserted here: superset's graph is 50 MB on disk, and
`forensic browse` loads a **bounded snapshot** (`--max-nodes`, default 500) rather than the whole
graph, which is why the TUI opens on a repo this size at all. The `deepdive` shell holds one
store open across NL queries and **borrows** it around `trace`/`impact`/`flow` — on a 50 MB
LadybugDB with a Windows exclusive lock, a held handle would have made 6 of the shell's 9
commands unusable.

## Verdict

The flagship confirms v0.9 as a true completion release: **62 routes, 54/8/0, unchanged**; the
artifacts no longer reference a ledger their readers cannot see; and the two v0.8 reporting
findings (`<module>` names, examples-only counts) are closed on the very repo that motivated
them. Nothing regressed. Nothing was silently re-tuned to make the numbers look better.
