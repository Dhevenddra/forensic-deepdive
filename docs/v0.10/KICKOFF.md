# KICKOFF — forensic-deepdive v0.10 · "The Upgrade Path" (integrity release)

> Seeded by `docs/findings/v0.9/DEFERRED.md`. **Read `CLAUDE.md` → `DECISIONS.md` → `PROGRESS.md`
> per the session-start protocol** before any code.
> v0.10 DEC range: **DEC-109 … DEC-116** (+ the standing reserved slot for GATE A Arm B).

---

## §0 — The framing: v0.9 shipped a bug that 909 tests could not see

v0.9 was a completion release and it completed. The interactive CLI landed, the engine was proven
unchanged (superset: 62 routes, 54/8/0, identical to 0.8.0), and the release went out on PyPI + the
MCP Registry with no autonomous overclaim.

Then the findings run found **DEC-108**: `--refresh-shims` was structurally incapable of refreshing
5 of its 10 targets, and had been since DEC-091. The suite was green the whole time.

The reason is the thing v0.10 exists to fix. Every test in the suite writes shims into an empty
`tmp_path`. **Nothing has ever tested what happens when Deepdive runs over a repo that already
carries a previous release's output.** That is not one missed test — it is a blind spot the shape of
the entire upgrade path, and every user who is not running Deepdive for the first time is standing
in it.

So v0.10 is an **integrity** release. Not new surface: the guarantee that the surface we already
ship survives its own second run.

---

## §1 — The verdict (scope, one paragraph)

v0.10 closes the **upgrade path** as a tested, self-announcing, release-enforced property, and then
attacks the one honest performance bottleneck left in the pipeline. Track A makes "a repo that
already has our output" a first-class fixture: a checked-in prior-release surface, a convergence
assertion, a stale-shim advisory so an upgrading user *learns* the flag exists at the moment they
need it, and release-hygiene tests that couple `examples/` to `pyproject.toml` so a stale artifact
directory fails CI instead of being caught mid-release by eye. Track B takes the serial
graph → PageRank → insert tail, where omi burns ~374 s of CPU at ~1.15 GB RSS after the
already-parallel parse. **Inserts are already batched** (DEC-032 — verified, see §4), so the real
targets are PageRank and, if it earns its DEC, incremental extract. No new artifact, no tenth MCP
tool, no new protocol, no LLM in `src/`.

---

## §2 — North star and the honest scope line

**North star (unchanged):** does an AI agent finish real work better because of deepdive?

v0.10 does not move the autonomous-usefulness needle either — that is still GATE A Arm B, still
hardware-gated. What it moves is **trust**: a tool whose output silently rots on upgrade is not a
durable-artifact tool, it is a first-run demo. The 5-artifact contract promises durability across
re-runs; until v0.10 that promise was untested. The honest framing: **v0.10 makes the existing
guarantees real and the pipeline faster on large repos; it makes no new claim.**

---

## §3 — Keystones and hard constraints (each an active DEC; do not breach)

1. **Zero-LLM, zero-network `src/` floor (DEC-009).** Unchanged. Nothing in this release goes near a
   model call.
2. **The contract is frozen.** 5 artifacts, 9 MCP tools, the `Endpoint`/`base.join` keystone,
   AGENT_BRIEF ≤ 5 KB. v0.10 adds no public surface — the stale-shim advisory prints, it does not
   emit.
3. **The advisory must not mutate (DEC-111).** Detecting stale shims on `extract` is a *read*. It
   prints one line and changes nothing on disk. Refresh stays opt-in behind `--refresh-shims`;
   silently rewriting a user's files because we noticed they were old is exactly the clobber that
   write-if-absent exists to prevent.
4. **Ownership stays content-independent where it must be (DEC-108).** `_is_deepdive_owned`
   (`shims.py:447`) claims the editor shims by fingerprint and the 5 skills by namespace. Any new
   detection logic reuses that predicate — it does not grow a second, divergent notion of ownership.
5. **Goldens stay byte-identical.** Nothing in Track A or B may change emitted content. A perf
   optimization that alters one ranking is a **failed** optimization — PageRank output is part of
   the artifact, and determinism is the reason goldens work at all. This is the gate on all of §4.
6. **Never add a runtime dependency without a DEC.** Relevant to the sparse-PageRank seed (`scipy`
   would be a new runtime dep; the pure-Python implementation exists precisely because DEC-011 said
   no to that once already — reopening it needs a superseding argument, not a shrug).
7. **Test alongside; PROGRESS at session end; a DEC per non-trivial choice; never push without
   explicit instruction.**

---

## §4 — What the ledger got right, and the one thing it got wrong

`docs/findings/v0.9/DEFERRED.md` §2 lists three perf seeds "in increasing order of ambition" and
asks, of the third: *"Confirm whether the store writes are already batched; if not, a single UNWIND
per node/edge kind is a cheap constant-factor win."*

**They are already batched.** `ladybug_store.py:603` documents exactly this: one
`UNWIND $rows`-shaped Cypher call per chunk of `_BATCH_SIZE`, per node and edge kind, landed under
DEC-032 with a bench-confirmed batch size. The cheap constant-factor win was taken three releases
ago.

That deletes seed (c) and sharpens the track: the serial tail is **graph construction + PageRank**,
not I/O. Do not re-litigate insert batching. Measure before optimizing the rest — the ledger's
attribution of the ~374 s was never profiled per-phase, only observed in aggregate, and the first
deliverable of Track B is therefore a **profile**, not a patch.

---

## §5 — The tracks

| Track | Name | Delivers | DECs |
|---|---|---|---|
| **A** | **Upgrade integrity** (headline) | prior-release fixture + convergence; stale-shim advisory; release-hygiene coupling tests; in-repo regen script | DEC-109–112 |
| **B** | **The serial tail** | per-phase profile → PageRank optimization → (gated) incremental extract | DEC-113–115 |
| **C** | **Instrument the instrument** | refresh-summary disambiguation; MANUAL_TEST stable-core split | DEC-116 |
| **D** | **Carryover (gated)** | GATE A Arm B (hardware); protocol carryover (demand); `serve --ui` labels (finding-gated) | (reserved) |

Priority: **A > B > C**. Track A is small, high-certainty, and fixes a known-real defect class.
Track B is the larger engineering arc and is **measurement-gated** — if the profile says PageRank is
30 % of the tail rather than 80 %, the plan changes and that is a success, not a setback.

---

## §6 — Build sequence (DEC order ≈ build order)

```
DEC-109  v0.10 scope verdict (this KICKOFF, formalized). No code.
         ──────────────────────────────────────────────── Track A: upgrade integrity
DEC-110  The prior-release fixture + convergence assertion. A checked-in 0.9-era emitted
         surface (stale skills, stale editor shims, stale artifact footers) that the suite
         extracts OVER, asserting: nothing Deepdive-owned is left stale after
         --refresh-shims, and nothing hand-edited is touched. THE root-cause fix for
         DEC-108's whole class.                                        [DEFERRED §1.1]
DEC-111  Stale-shim advisory on `extract` — detect Deepdive-owned targets whose content
         differs from what we'd write, print ONE line naming the count and the flag.
         Read-only; mutates nothing. Reuses _is_deepdive_owned (DEC-108).  [DEFERRED §1.3]
DEC-112  Release-hygiene tests — examples/*/AGENT_BRIEF.md footer version MUST equal
         pyproject.toml's version. One assertion that would have caught the two stale
         example dirs on day one of the v0.9 pre-release.                 [DEFERRED §4.11]
   ▸ (no DEC) scripts/regen_examples.py moved in-repo from C:\Dev\scratch, source root from
     an env var, exit codes separated (extract-failed vs token-found).    [DEFERRED §1.4]
         ──────────────────────────────────────────────── Track B: the serial tail
DEC-113  Per-phase profile of the post-parse tail on a large repo. Deliverable is NUMBERS
         (graph construction vs PageRank vs insert, wall + RSS), committed as a findings
         doc. No optimization lands before this.                          [DEFERRED §2.5]
DEC-114  PageRank optimization, scoped by DEC-113. Pure-Python power iteration today
         (DEC-011 chose that deliberately to avoid SciPy/NumPy). Options: tighter inner
         loop / adjacency prebuild / sparse matvec behind an optional extra. A new runtime
         dep REOPENS DEC-011 and needs a superseding entry.  MUST be output-identical.
DEC-115  Incremental extract — GATED on DEC-113 saying the tail is worth it AND on a
         credible invalidation story. Biggest win, hardest correctness. Persist the graph,
         apply a diff. Do NOT start this before 113/114 land.            [DEFERRED §2.5a]
         ──────────────────────────────────────────────── Track C: instrument the instrument
DEC-116  Refresh-summary disambiguation ("SKILL.md, SKILL.md" → skill names), and the
         MANUAL_TEST split: a stable 5-question scored core (comparable across releases)
         + a per-release delta section.                             [DEFERRED §1.2, §4.10]
         ──────────────────────────────────────────────── Track D: DEFERRED (not built)
(resv.)  GATE A Arm B — HARDWARE-GATED. ≥16 GB GPU + frontier main-agent endpoint.
         Head-of-line when hardware lands. Until it runs, no autonomous claim.  [DEC-087/092]
(resv.)  Protocol carryover — DEMAND-GATED (DEC-106). Build on real-repo need only.
(resv.)  serve --ui raw qualified names — FINDING-GATED (DEC-104). Revisit if a run names it.
```

---

## §7 — Track A in shape (what the fixture actually has to be)

The failure mode being defended against is subtle, so the fixture design matters more than the
assertion count.

- **It must be a *materialized prior surface*, not a mock.** Checked-in copies of what 0.9.0
  actually wrote — a real stale `SKILL.md` with a real old description, a real 0.9.0 artifact
  footer. If the fixture is generated by current code with a field tweaked, it tests current code's
  imagination, not history.
- **It must assert convergence, not equality-to-a-golden.** Extract over the stale surface, then
  assert the *post-state* is what a clean run produces for every Deepdive-owned target — and that
  every hand-edited/foreign file is byte-unchanged. Both halves. DEC-108's fix could have been
  written as "refresh everything," and the second half is what stops that.
- **It must fail against the pre-DEC-108 gate.** The v0.9 fix was accepted only after the key test
  was *verified failing* against the old predicate. Same discipline: a new upgrade test that cannot
  be shown to fail on the bug it describes is decoration.
- **It should generalize past shims.** The class is "fresh is fine, upgrade leaks." Artifacts,
  shims, the registry entry, and the cache are all upgrade surfaces. Start with shims (known
  defect), but shape the fixture so a second surface is cheap to add.

---

## §8 — What's explicitly OUT (non-goals; do not regress)

- **No sixth artifact. No tenth MCP tool. No `protocol ==` branch in the surfacing layer.**
- **No LLM at runtime in `src/`.** `[semantic]` remains an optional retriever.
- **No autonomous-usefulness claim** until GATE A Arm B runs. Unchanged since v0.8.
- **No GUI arc.** Still gated on the interactive CLI being used in anger + the MANUAL_TEST solo run.
- **No perf work before the profile.** DEC-113 gates 114 and 115. "Just add threads" is explicitly
  rejected — the tail is GIL-bound object churn and the store takes an exclusive writable handle.
- **No re-batching of store inserts.** Already done (DEC-032). See §4.
- **No silent rewriting of user files.** The advisory prints; `--refresh-shims` acts.

---

## §9 — Open design questions delegated to Claude Code

1. **Where does the prior-release surface live (DEC-110)?** `tests/fixtures/prior_release/` as
   checked-in files, versus a tarball, versus generated-once-and-frozen. Prefer plain checked-in
   files — greppable, diffable in review, and obvious when they go stale.
2. **How many prior releases does the fixture carry?** One (0.9) is enough to close the known bug.
   Consider whether an N-release matrix is worth the maintenance, or whether "the last release" is
   the honest support boundary. Recommend the latter; document it.
3. **Advisory wording and threshold (DEC-111).** One line, always, when count > 0? Or only on
   `update`/re-extract? It must not become noise on a first run, where the count is 0 by
   construction.
4. **Does the advisory count hand-edited files?** No — they are not stale, they are *theirs*. But
   consider whether staying silent about a diverged shim is itself a surprise.
5. **PageRank optimization boundary (DEC-114).** If sparse matvec wins decisively, is it worth an
   optional extra (`[fast]`) with the pure-Python path as the always-available default? That keeps
   DEC-011's lean-install intent while taking the win where it's installed.
6. **Incremental invalidation (DEC-115).** What actually invalidates a persisted graph — file hash
   is necessary but not sufficient (a deleted file changes others' edges; a renamed symbol changes
   resolution repo-wide). Scope this honestly before committing to it.

---

## §10 — DEC pre-assignment

| DEC | Title (planning) | Track | Gate |
|---|---|---|---|
| 109 | v0.10 scope verdict | — | — |
| 110 | prior-release fixture + upgrade convergence assertion | A | |
| 111 | stale-shim advisory on `extract` (read-only) | A | |
| 112 | release-hygiene coupling tests (`examples/` ↔ `pyproject.toml`) | A | |
| 113 | per-phase profile of the serial tail | B | **gates 114/115** |
| 114 | PageRank optimization (output-identical) | B | 113 |
| 115 | incremental extract (gated, may not land) | B | 113 + 114 |
| 116 | refresh-summary disambiguation + MANUAL_TEST stable core | C | |
| (resv.) | GATE A Arm B (hardware) · protocol carryover (demand) · `serve --ui` labels (finding) | D | |

---

## §11 — Mandatory gates

- **Per-step:** `uv run pytest -x` green, `ruff check` clean, test written alongside, PROGRESS
  appended, a DEC entry for the choice.
- **The DEC-110 discipline:** every upgrade-path test must be demonstrated failing against the
  behavior it protects, before the protection is accepted.
- **Byte-identical goldens across the whole release.** Track A adds tests and one printed line;
  Track B must not move a single count, row, or ranking. Any golden diff in v0.10 is a bug until
  proven otherwise — there is no planned re-baseline this cycle. (v0.9 spent two authorized
  re-baselines; v0.10 should spend zero.)
- **`wc -c AGENT_BRIEF.md` ≤ 5120** on every example. Unchanged.
- **Pre-release (v0.10.0):** version bump in all five places (`pyproject.toml`, `__init__.py`
  fallback, `server.json` ×2, `plugin.json`, `marketplace.json`); CHANGELOG; golden footers;
  `examples/` regen via the now-in-repo script; **findings run against a repo carrying the PREVIOUS
  release's output** (the DEC-108 lesson, now also a test); MANUAL_TEST; then release **with
  explicit user authorization**.

---

*v0.10 in one line: v0.9 proved the engine unchanged and then shipped a flag that had been dead for
half its targets — so v0.10 makes the upgrade path a tested, self-announcing, CI-enforced property,
and then goes after the serial tail with a profiler before a patch.*
