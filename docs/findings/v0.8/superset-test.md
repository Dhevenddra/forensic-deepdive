# superset — v0.8 (flagship cross-stack + scale)

`forensic extract C:/Dev/scratch/superset --force` @ 0.8.0.

- **Scale:** 3862 source files (TS 1405, Python 1319, TSX 1077, JS 61) → graph of 3276 files /
  **10215 edges**. Completed in a couple of minutes; AGENT_BRIEF 1850 b (≤5 KB).
- **Cross-stack:** **62 ROUTES_TO** — `[E] 54 / [I] 8 / [A] 0`. This is the headline precision
  result: on the flagship, the AMBIGUOUS tier (DEC-083) stays **empty** because the React/RTK
  fetch calls resolve to unique Flask/Flask-AppBuilder handlers. (Context: v0.4 found 0
  ROUTES_TO here, v0.5 fixed it to 61; v0.8 holds at 62 with 54 cleanly EXTRACTED.)
- **Centrality is believable:** PageRank puts the i18n singleton
  (`TranslatorSingleton.ts` — `t`/`tn`), the theme provider (`theme/index.tsx` — `useTheme`),
  and `superset/utils/core.py` at the top — the genuinely load-bearing cross-cutting modules.
- **DEC-085 distinct-callers:** `t` shows **237 distinct callers / 1381 edges**; `transaction`
  **96 / 98 EXTRACTED**. The column is distinct callers, the mix is edges — the honesty fix is
  visible at scale.
- **History:** first commit 2015-07-02 → 2026-05-30 (~11 years), deep churn/ownership signal.

**Verdict:** the flagship passes — scale handled, cross-stack precise, ARCHITECTURE.md renders
the ROUTES_TO/INJECTS/PERSISTS surface. No fabrication observed. This is the strongest single
piece of evidence that the v0.8 precision work is correct on real, large, polyglot code.
