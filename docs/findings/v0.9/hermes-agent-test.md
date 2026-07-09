# hermes-agent — v0.9 (the owner's repo: the accuracy check, and the bug it caught)

`forensic extract C:/Dev/scratch/hermes-agent --force` @ **0.9.0**. Run on a repo the owner knows
cold, so lies would be caught. This one earned its place: **the findings step found a real defect
that the whole test suite missed**, and it was fixed before the tag.

- **Scale/shape:** 1,340 files (Python 661, TS 381, TSX 240, JS 49, Rust 9), graph
  **1,256 files / 7,895 edges**, 36 routes (`[E] 0 / [I] 1 / [A] 35`). AGENT_BRIEF 1280 b.

## Result 1 — the analysis is unchanged from v0.8

Every v0.8 assertion re-verified, identically:

| Metric | v0.8.0 | v0.9.0 | |
|---|---|---|---|
| Files / graph | 1340 · 1256 f / 7895 e | same | ✅ |
| Routes (E / I / A) | 36 (0 / 1 / 35) | same | ✅ |
| Most-called symbol | `load_config`, 258 distinct callers | same | ✅ |
| Never rules | `_(none derived)_` | same | ✅ |

The **DEC-086 low-history honesty** still holds on a fresh working copy: the repo reads as one
contributor over under a day of history, so the churn-driven **Never** rules stay *suppressed*
rather than fabricated. AGENT_BRIEF moved 1265 → 1280 b, which nets out exactly: the DEC-104
dotted path is longer than the placeholder it replaced, the DEC-107 parentheticals are gone.

## Result 2 — the v0.8 `<module>` finding is closed

The v0.8 doc filed this cross-stack Always-rule as the one display gap:

> *"`_send_whatsapp` calls backend `<module>` over `http::POST::/send`."*

At 0.9.0 the same rule reads:

> `_send_whatsapp` calls backend **`scripts.whatsapp-bridge.bridge`** over `http::POST::/send`
> (+35 more) `[INFERRED]`

Zero literal `<module>` strings remain anywhere in `docs/codebase/`. The edge, the endpoint key
and the `INFERRED` tag are untouched — DEC-104 changed the display name, never the join identity.

## Result 3 — **the bug**: `--refresh-shims` could never refresh a skill (→ DEC-108)

The explicit no-DEC-tokens check this release exists to pass, run against every surface Deepdive
writes into a target repo — not just the five artifacts:

```bash
grep -rn "DEC-[0-9]" $R/docs/codebase/            # PASS — no matches
grep -rn "DEC-[0-9]" $R/.claude/ $R/CLAUDE.md …   # !! LEAK, 2 files
```

```
.claude/skills/codebase-impact-analysis/SKILL.md:34:  … `AMBIGUOUS` (DEC-015). …
.claude/skills/codebase-refactoring/SKILL.md:31:     … (DEC-012's language-scoped rule) …
```

**These were stale files from the v0.8 extract** (mtime 2026-06-05), not fresh output — shims are
write-if-absent, and `--force` re-runs the *analysis*, not the shims. That is exactly what
`--refresh-shims` is for. So we ran it. It refreshed `CLAUDE.md`, `codebase.mdc`, `codebase.md`
— **and left both skills alone.**

Root cause: DEC-091 gates a refresh on `_SHIM_FINGERPRINT ("forensic-deepdive") in existing`.

| target | contains the fingerprint? | refreshable before the fix |
|---|---|---|
| `CLAUDE.md`, `AGENTS.md`, `.cursor/…`, `.continue/…` | yes | ✅ |
| `.claude-plugin/plugin.json` | yes | ✅ |
| the 5 `codebase-*/SKILL.md` | **no — never, in any release** | ❌ |

So `--refresh-shims` was structurally dead for **half its ten targets**, and DEC-107's invariant
("no `DEC-NNN` token in anything the tool emits") held on a *fresh* repo but leaked on every
*upgrade* — with no documented command able to clear it.

**Why the suite missed it.** DEC-107's regression guard
(`test_emit.py::test_no_internal_dec_ids_in_any_emitted_artifact`) swept the five markdown
artifacts and nothing else. The shims are a consumer-facing emitted surface too. The guard is now
widened to all ten targets, and the refresh path has three ownership tests. The skill-refresh test
was **verified failing** against the old gate (`refreshed=[]`) before the fix was accepted.

**The fix (DEC-108):** the five skills are claimed by **namespace** rather than fingerprint — the
file must sit at `.claude/skills/<name>/SKILL.md` for one of our five names *and* declare that
same `name:` in its YAML frontmatter. Both must agree, so a user's own skill parked in our
directory is still never clobbered. Adding the fingerprint to the bodies instead would have helped
only repos extracted *after* the fix — precisely the population that was never broken.

After the fix, on this repo:

```
Refreshed  SKILL.md, SKILL.md
=== DEC tokens anywhere Deepdive wrote into hermes-agent ===
PASS: zero DEC tokens in every emitted surface
```

## Minor: the refresh summary prints bare basenames

`Refreshed  SKILL.md, SKILL.md` — two different skills, indistinguishable. Cosmetic; the styled
summary should disambiguate (parent dir, or the skill name). Filed for v0.10; not touched during
the release freeze.

## Verdict

Accurate where it asserts, honest where the signal is thin (still no invented Never rules), and
the one v0.8 display finding is closed. More importantly: **the findings run did its job.** A
defect that every one of 909 tests passed over — because they all tested the emitter, never the
upgrade path — surfaced the moment the tool was pointed at a repo carrying a previous release's
output. That is the argument for keeping this step in the pre-release, and for it being a *real*
run against a *real* upgraded repo rather than a fixture.
