# omi — v0.8 (largest polyglot; canonical example)

`forensic extract C:/Dev/scratch/omi --force` @ 0.8.0. The biggest breadth test in the set.

- **9 languages in one graph:** 2113 source files — Dart 555, Python 459, TSX 357, Swift 314,
  TypeScript 222, C 101, JavaScript 58, Rust 46, Java 1 → graph 2048 files / **18276 edges**
  (the largest graph in the acceptance set). AGENT_BRIEF 1731 b (≤5 KB) — the cap holds even on
  the biggest repo.
- **Lead language inferred correctly:** MENTAL_MODEL opens "A **Dart** codebase" — Dart is the
  plurality (555 files), which matches omi being a Flutter app with native/edge sidecars.
- **History depth:** 50 contributors over ~2.2 years — rich churn/ownership/co-change signal
  (unlike the thin hermes copy), so the ARCHAEOLOGY + Never rules have real fuel here.
- **Cross-stack:** 3 ROUTES_TO (`[E] 0 / [I] 3 / [A] 0`) — modest, as expected for a
  mobile-first app where most coupling is intra-process / BLE rather than HTTP.

**Verdict:** the polyglot pipeline scales to 9 languages and ~18k edges without breaking the
artifact contract or the 5 KB cap. Regenerated as the canonical `examples/omi/` evidence at
0.8.0 (was last refreshed pre-v0.3).
