# fastapi — v0.3 real-repo test (v0.2 carryover)

The §5.4 v0.2 debt (DEC-033 deferred `examples/fastapi/`), paid in v0.3. Pure
Python at moderate scale — a clean read on the Python method-resolution path
and the hybrid query.

## Run summary

| | |
|---|---|
| Date | 2026-05-30 |
| Repo | [fastapi/fastapi](https://github.com/fastapi/fastapi) (7,203 commits, 88 MB) |
| Tool version | v0.3 HEAD (`8ad4110`) |
| OS | Windows 11 |

### Timings

| Run | Time |
|---|---|
| cold `extract --force` | **16.2 s** |
| warm re-extract (cache hit) | **0.34 s** |

### Inventory & graph

- **524** files (520 Python, 4 JavaScript) · **1,986** Symbols · 179 Modules · 7,203 Commits · 911 Authors.
- Edges: **1,924 CALLS** · 210 MEMBER_OF · 1,301 IMPORTS · **87 EXTENDS** · 0 IMPLEMENTS · 892 CO_CHANGES_WITH.
- **AGENT_BRIEF 1,476 B** (≤5120 ✓).

### CALLS by confidence (the Item-C metric)

| confidence | count |
|---|---|
| EXTRACTED | 694 |
| INFERRED | 536 |
| AMBIGUOUS | 694 |

By `via`: 1,878 `bare` + 26 `self` + 20 `this`. Python's call sites are mostly
bare/module-qualified, so Item C's incremental method recovery is small here
(46 edges) — the bulk of resolution is the DEC-025 bare-name path. 87 EXTENDS
captures Python class inheritance (`class Foo(Bar)`).

## ✅ What worked

1. **Hybrid NL query** `"create application route dependency injection"`
   (offline) ranks `APIRouter.route` **EXTRACTED** first, then `APIRouter`
   INFERRED — the right core abstractions:
   - `fastapi/routing.py::APIRouter.route` — EXTRACTED `[lexical, structural]`
   - `fastapi/routing.py::APIRouter` — INFERRED
2. **Structural tier** lifts the two core `routing.py` symbols above the long
   tail of `docs_src/` tutorial examples (which are lexical-only hits) — the
   proximity/centrality signal doing its job.
3. **AGENT_BRIEF stays tiny** (1.5 KB) even at ~2k symbols.

## Notes / honest failures (the AMBIGUOUS story)

- **694 AMBIGUOUS (36% of CALLS)** is the highest ratio in the v0.3 set, and
  it's almost entirely an artifact of `docs_src/` — FastAPI ships **hundreds of
  tutorial files** that each redefine the same names (`dependency_a`,
  `read_item`, `get_db`, `app = FastAPI()` …) across `tutorial001`,
  `tutorial001_py310`, `tutorial001_an`, … So a bare call to `read_item`
  legitimately has dozens of same-name cross-file candidates → AMBIGUOUS by
  DEC-025. This is **honest, not wrong** — the resolver surfaces every
  candidate rather than picking one.
- **Finding → v0.4 scope:** `docs_src/` is documentation/example code, not
  library implementation. Classifying `docs_src/`-style "examples" dirs as a
  non-`source` role (extending DEC-021) would pull them out of the production
  graph and collapse most of this AMBIGUOUS count — the same move DEC-012/021
  made for tests/fixtures/vendored. The hybrid query's **output shaping**
  already demotes test/vendored/generated; teaching the inventory an `example`
  role would let shaping demote these too. Logged for v0.4.
- The 4 JavaScript files are doc-site assets — correctly inventoried, low
  signal.
