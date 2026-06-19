# MCP tool review — grounded stress-test on Iris-Nearby (v0.7 usability gate)

An unbiased, claim-by-claim review of the nine MCP tools, produced by a fresh agent (opus-4-8)
that **cross-checked every MCP answer against the actual files** rather than vibes-rating it.
Repo: Iris-Nearby (Flutter/Dart P2P BLE chat — 35 files, 1 author, 28 days). This is the most
useful single artifact from the gate for steering v0.8 tool-quality work, so it's recorded
verbatim-in-substance (not paraphrased away).

## Probe results (MCP claim vs ground truth)

| Probe | MCP claim | Ground truth | Verdict |
|---|---|---|---|
| Node counts (Cypher) | 318 Symbol, 71 Module, 35 File, 35 Commit, 1 Author | matches repo | ✅ exact |
| Git archaeology | main 11 / nearby 8 commits, co-change clusters, bus factor 1 | matches `git log` | ✅ reliable |
| `impact(Message)` upstream | 80 symbols, incl. `settings_screen` toggles + onboarding | `settings_screen` has **0** `Message` refs; onboarding's hits are `_buildFloatingMessages` UI, not the model | ❌ false positives |
| `query(NL)` "where are messages encoded/decoded" | `ThemeProvider.toggleTheme`, notification channels, `_formatDuration` | the real hit is `_encode/_decodeMessageWithMedia` (nearby_service.dart:321,559) — literally has "encode" in the name | ❌ missed the obvious hit |
| `trace(sendMessage)` | empty chains + honest boundary note | correct — no HTTP/ORM in a P2P app | ✅ honest, but ⚪ irrelevant here |
| "AppColors: 383 inbound calls" | 383 | 271 literal `AppColors.` usages via grep | ⚠️ directionally right, magnitude inflated ~40% |

## Where it earns its keep (high-trust)

- **Git archaeology is the standout** — churn, co-change clusters, bus factor, author share: accurate, verifiable, and the fastest way to learn "where risk lives." The main ↔ nearby ↔ storage ↔ chat_screen co-change spine was a real insight.
- **Pre-baked briefs** (AGENT_BRIEF, central-files ranking) gave a correct one-read orientation.
- **Cypher / structural queries are exact** — precise question, precise correct answer. `context()` is a good one-call starter.
- **Honest about uncertainty** — `EXTRACTED` vs `INFERRED` tags, `degraded:true`, empty `trace` with a boundary explanation. It signals when to distrust it, which matters more than raw accuracy.

## Where it's weak or misleading

1. **`impact()` over-scopes (precision).** 80 "upstream" symbols for `Message` included `settings_screen` functions with zero `Message` references — depth-2/3 buckets are largely INFERRED noise (same-file co-occurrence resolved as a CALLS edge). Treat output as a *candidate list to verify*, not a blast radius. A careless agent would "fix" files that don't need touching.
2. **NL `query()` underdelivers.** The `[semantic]` tier isn't installed (`degraded:true` → lexical+structural only), and even the lexical fallback missed a query whose answer has the search term *in the function name*. For discovery here, plain grep beat it.
3. **Dart degrades the call graph.** Dynamic dispatch → most edges INFERRED; class-to-class "CALLS" are really "references"; `flow()` emitted a `Message→Message` self-cycle artifact. The structural layer is softer than it looks on a typed-but-dynamic language.
4. **Some tools are dead weight for this repo.** `trace` (endpoint→handler→ORM) targets web/backend stacks; honest, but inapplicable to an offline P2P app.
5. **Opaque metrics.** "383 inbound calls" can't be reconciled with 271 literal usages; the conclusion (AppColors is most central) is right, but the number shouldn't be quoted as fact.

## Net assessment (the reviewer's rank-ordering)

- **High / trust it:** git archaeology, Cypher structural queries, the pre-generated briefs.
- **Medium / verify it:** `context()`, `impact()`, `flow()` — fast lead generators, but edges are noisy enough that every consequential claim needed cross-checking (several didn't hold).
- **Low / skip here:** NL `query()`, `trace` — grep and the code outperform them on this repo.

> The honest one-liner: **a fast lead-generator and an excellent git-risk lens, not an authoritative source of truth.** Its biggest real value is the archaeology and the curated briefs, not the graph (which Dart degrades). Used as "where should I look and what's risky" it's a net positive; used as "what definitely breaks if I change X" it over-scopes. Keep a verify-the-claim discipline and it pays off.

## Important caveat on generalizing this

This is a 35-file, single-author, 28-day-old **Dart** repo. The archaeology layer is thin by nature (small history), and several graph weaknesses are Dart-specific (dynamic dispatch). On a larger, longer-lived, statically-typed codebase the call-graph precision and co-change signal would both likely be stronger — do **not** over-generalize "impact() is noisy" to every project. This is also why the publish gate's Q2 test must run on a richer repo.

## Reconciliation with the earlier (rosier) MCP run

The first MCP pass framed `impact()` as "beating" the by-hand answer (it caught real depth-2/3 ripple the manual pass missed). This stress-test shows the other half of the same coin: that wider net is **high-recall, lower-precision** — it caught real ripple *and* false positives (settings_screen). Both are true. The fair synthesis: `impact()` maximizes recall at the cost of precision; it's the right tool to *generate* a blast-radius candidate set, the wrong tool to *trust* as the final set. The scorecard delight was tempered accordingly.

## v0.8 seeds this produced (also in DEFERRED.md)

- `impact()` precision: suppress same-file co-occurrence promoted to CALLS; separate "references" from true call edges (esp. Dart); let callers cap by confidence.
- Lexical NL ranking: an exact function-name substring match must outrank unrelated symbols; ship/clearly flag the `[semantic]` tier's absence at the point of use.
- Reconcile/define the "inbound calls" metric so it matches a verifiable count (or label it an estimate).
- Per-tool applicability hint (e.g. `trace` self-noting "no HTTP/ORM endpoints in this graph").
