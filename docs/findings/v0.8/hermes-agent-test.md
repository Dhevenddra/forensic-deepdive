# hermes-agent — v0.8 (owner's repo: the accuracy check)

`forensic extract C:/Dev/scratch/hermes-agent --force` @ 0.8.0. Run on a repo the owner knows
cold, so lies would be caught.

- **Scale/shape:** 1340 files (Python 661, TS 381, TSX 240, JS 49, Rust 9), graph 1256 files /
  **7895 edges**, 36 routes (`[E] 0 / [I] 1 / [A] 35`). AGENT_BRIEF 1265 b.
- **Most-called symbol:** `load_config` — 258 distinct callers (DEC-025 resolver). Believable
  for a config-driven agent; signature changes there would ripple widely. `[INFERRED]`.
- **Low-history honesty (DEC-086) works:** the repo reads as 1 contributor / "under a day" of
  history (a fresh working copy), so the churn-driven **Never** rules are *suppressed*:
  `### Never — _(none derived)_`. The tool declines to invent risk rules from thin git signal
  instead of fabricating them. This is the DEC-086 behavior landing on a real solo/low-history
  repo — the exact v0.7 DEFERRED item.

## Finding: `<module>` handler placeholder

The cross-stack Always-rule reads: *"`_send_whatsapp` calls backend `<module>` over
`http::POST::/send`."* The consumer→endpoint join is correct, but the **handler symbol name
degraded to `<module>`** — a module-scope target whose qualified name renders as the literal
`<module>` rather than the function. Same placeholder shows up as a *consumer* name on fastapi
module-level call sites. The edge is right; the display name of a module-scope symbol is the
gap. Filed to v0.9 (cosmetic/clarity, not a wrong edge).

**Verdict:** accurate where it asserts, honest where the signal is thin (no invented Never
rules), one display-name polish item. Nothing hallucinated.
