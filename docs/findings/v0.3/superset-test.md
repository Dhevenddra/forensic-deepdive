# Apache Superset — v0.3 real-repo test (the primary polyglot stress)

The headline v0.3 target (PRD §4.7): a large Python + TypeScript + React
codebase that exercises the hybrid query and **pre-stages the v0.4 cross-stack
wedge** (Flask/SQLAlchemy backend ↔ React frontend). The biggest, most
polyglot repo run to date by file count.

## Run summary

| | |
|---|---|
| Date | 2026-05-30 |
| Repo | [apache/superset](https://github.com/apache/superset) (20,031 commits, 1.2 GB clone) |
| Tool version | v0.3 HEAD (`8ad4110`) |
| OS | Windows 11 |

### Timings

| Run | Time |
|---|---|
| cold `extract --force` | **486.2 s** |
| warm re-extract (cache hit) | **1.90 s** |

486 s cold on 3,871 files + a 20k-commit git-archaeology pass — under the
1200 s budget. Warm **1.90 s** (cache hit, single-digit seconds ✓). Parse cache
+ parallel parse (Items A+B) keep this tractable at a scale that would have
blown well past v0.2's sequential parse.

### Inventory & graph

- **3,871** files — **TypeScript 1,405 · Python 1,328 · TSX 1,077 ·
  JavaScript 61**. A genuine three-language polyglot, ~equal Python/TS mass.
- **18,764** Symbols · 3,858 Modules · 20,031 Commits · 1,536 Authors.
- Edges: **16,816 CALLS** · 4,906 MEMBER_OF · 21,322 IMPORTS · 1,166 EXTENDS ·
  1 IMPLEMENTS · **348,118 CO_CHANGES_WITH**.
- **AGENT_BRIEF 1,663 B** (≤5120 ✓).

### Method recovery (Item C, DEC-037)

| via | count |
|---|---|
| `bare` (= v0.2 graph) | 14,897 |
| `self` | 1,025 |
| `this` | 413 |
| `static` | 440 |
| `module` | 41 |

**Item C recovered 1,919 method/module calls** v0.2 dropped — **1,917 precise
INFERRED + only 2 AMBIGUOUS**. The Python `self.` and TS `this.` receivers
resolve almost perfectly cleanly here (well-structured DAO/model/command
layers), so method recovery added **essentially zero ambiguity**. The
v0.2-equivalent bare-name AMBIGUOUS is 3,205 (19 %); total v0.3 AMBIGUOUS 3,207.

## ✅ What worked

1. **Hybrid NL query is the cross-stack showcase.**
   `"dashboard chart query database connection"` (pure-static, offline,
   `degraded=True`) returns Superset's **core domain models, all EXTRACTED**,
   spanning the Python backend and the TS frontend:
   - `superset-core/.../common/models.py::Chart` / `::Dashboard` / `::Database`
   - `superset-core/.../queries/models.py::Query`
   - `superset-core/.../common/daos.py::BaseDAO.query`
   - `superset-frontend/.../utils/vizPlugins.ts::Dashboard` (the TS side)

   The query pulls the SQLAlchemy models *and* the frontend `Dashboard` from one
   natural-language phrase — exactly the cross-stack retrieval the v0.4 wedge
   will join with `ROUTES_TO` edges. The structural tier (proximity +
   in-degree) lifts the `superset-core` models above the long tail.
2. **348k CO_CHANGES_WITH** — the archaeology layer scales to a 20k-commit
   history; the co-change graph is dense enough to surface real feature
   coupling (backend model ↔ frontend view).
3. **1,166 EXTENDS** — Python class hierarchies + TS `extends` both captured.
4. **AGENT_BRIEF 1.66 KB** at ~19k symbols — the ≤5 KB cap holds with ease.

## Notes / honest failures

- **The repo restructured into `superset-core/` packages** — the top hits live
  under `superset-core/src/superset_core/...`, reflecting Superset's recent
  monorepo-ization. The tool follows the real layout with no special-casing.
- **`--central` Mermaid is low-signal** here too (dominated by `useTheme`, `t`,
  `onChange`, `ensureIsArray` — ubiquitous React/i18n helpers). Centrality
  honestly reflects that these are the most-called symbols; a "most-central
  *type*" view would read better for orientation. → tracked (same note as
  ripgrep).
- **1 IMPLEMENTS** — TS `implements` is under-captured (same DEC-028 TS
  conservatism noted in the gitnexus run).
- **Cross-stack `ROUTES_TO` is explicitly v0.4** — this run captures both ends
  (Python handlers, TS `fetch`/route literals exist in the graph as symbols)
  but does **not** join them; that's the wedge DEC-034 sequenced into v0.4,
  for which Item C (landed here) is the prerequisite. Superset is now the
  staged demo repo for it.
