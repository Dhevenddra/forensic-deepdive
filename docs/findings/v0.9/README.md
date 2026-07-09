# v0.9 findings — "The Interactive CLI": does a completion release change the analysis?

Per-repo results from running `forensic extract` (**0.9.0**) over the `C:\Dev\scratch` acceptance
set. Convention per [`../README.md`](../README.md): one folder per release, narrative findings,
evidence mirrored under `examples/<repo>/`.

v0.9 adds four interactive surfaces (`repl`, `browse`, `onboard`, `deepdive`) and removes a class
of dangling reference from emitted output. It changes **no** analysis. So this run is built around
a negative claim and one explicit check:

1. **Nothing moved.** Same routes, same confidence mix, same rankings, on the flagship.
2. **No internal ledger IDs** in *anything* the tool emits — artifacts *and* shims.

Two repos, chosen for the two jobs: **superset** (scale + cross-stack precision) and
**hermes-agent** (a repo the owner knows cold — where a lie would be caught).

## Headline verdict

The analysis is byte-for-byte unchanged, and check (2) **failed on first run** — which is the most
valuable thing in this document.

| Repo | Stack | Src files | Graph | Routes (E / I / A) | vs v0.8 |
|---|---|---|---|---|---|
| **superset** | TS + Python | 3,862 (+9 demoted) | 3,871 f / 18,764 sym / 16,816 calls | **62 (54 / 8 / 0)** | identical |
| **hermes-agent** | Python + TS | 1,340 | 1,256 f / 7,895 e | **36 (0 / 1 / 35)** | identical |

`git diff` over `examples/superset/` and `examples/omi/` is **36 and 30 lines**, and every line is
one of three things: a version footer, a DEC-107 wording de-leak, or a DEC-104 display name. No
count, table row, ranking or confidence tag moved anywhere. That is the evidence for the 0.9.0
CHANGELOG's claim that engine, graph and contract are untouched.

## The finding that mattered — DEC-108

On hermes-agent, a repo first extracted at **0.8.0**, the no-DEC-tokens check passed on the five
artifacts and **failed on two skill shims**. `--refresh-shims`, the documented fix for stale
shims, would not clear them: it gates on a fingerprint string the five `codebase-*/SKILL.md`
bodies have never contained, in any release. Half of its ten targets were unrefreshable.

DEC-107's invariant therefore held on a *fresh* repo and leaked on every *upgrade*. Fixed before
the tag (DEC-108: namespace ownership for the skills), with the regression guard widened from the
five artifacts to all ten emitted targets, and the new test verified failing against the old gate.

**The lesson for the pre-release checklist:** 909 tests passed over this because they all exercise
the emitter on a clean tree. Only pointing the tool at a repo that already carried a *previous
release's* output could expose it. Keep the findings run real, and keep it on an upgraded repo.

## Both v0.8 open findings are closed

- **`<module>` display names (DEC-104).** hermes' cross-stack rule now names
  `scripts.whatsapp-bridge.bridge`; superset's Cypress rows name
  `superset-frontend.cypress-base.cypress.support.e2e`. Zero literal `<module>` remain. The
  `trace --json` payload still carries the raw qualified name — it is the join id.
- **Examples-only source counts (DEC-103).** The headline annotates only where files were
  actually demoted: **4 of 11** example repos (fastapi `75 (+449)`, omi `2,113 (+36)`,
  superset `3,862 (+9)`, ripgrep `81 (+3)`); the other 7 print the plain, unannotated line.
  fastapi is the vindication — its headline previously understated the analyzed surface **6×**.

## `examples/` is now DEC-token-free

All eleven repos regenerated at 0.9.0. The sweep went **211 → 0** tokens across `examples/`.
Every AGENT_BRIEF is under the 5 KB cap (max 1,894 b, superset).

## Interactive surfaces

Not scriptable in CI — they need a real console — so they are exercised by hand per
[`../../v0.9/MANUAL_TEST.md`](../../v0.9/MANUAL_TEST.md). Two properties are worth recording here
because they are architectural, not cosmetic:

- **`browse` loads a bounded snapshot** (`--max-nodes`, default 500). Superset's graph is 50 MB on
  disk; the TUI opens on it at all because it never loads the whole thing.
- **The `deepdive` shell borrows the store** rather than holding it. LadybugDB takes an exclusive
  file lock **on Windows** (a second handle raises; the same open succeeds on Linux). Six of the
  shell's nine commands open their own handle, so a held store would have made them unusable on
  the primary dev platform.

## Files

- [`superset-test.md`](superset-test.md) — the flagship: nothing moved; DEC-103/104 on real code.
- [`hermes-agent-test.md`](hermes-agent-test.md) — the accuracy check, and the DEC-108 bug.
