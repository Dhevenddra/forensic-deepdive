# MANUAL_TEST.md — v0.10 delta ("The Upgrade Path")

> **Run this first, then score the five stable questions in
> [`../MANUAL_TEST_CORE.md`](../MANUAL_TEST_CORE.md).** This file covers only what v0.10 changed;
> the core is the instrument and does not move between releases (DEC-116).
>
> Nothing here edits your code. Deepdive reads, and writes artifacts under `docs/codebase/` plus
> agent-onboarding shims — all regenerable.

**Shell note (Windows, carried from v0.9):** the interactive surfaces (`repl`, `browse`,
`onboard`, `deepdive`) need a real console — **PowerShell or cmd.exe, not Git Bash/MinTTY**
(`isatty()` lies there). The steps below are non-interactive and are fine in Git Bash.

---

## What v0.10 changed

v0.10 adds almost no surface on purpose. Two of the three things to test are **behaviours on a
second run** — the path that had never been tested before this release.

- **§1** — `extract --timings`, per-phase wall clock.
- **§2** — the **stale-shim advisory**, and the upgrade path converging. *This is the release.*
- **§3** — shim summary rows naming the skill.
- **§4** — release hygiene (mostly a CI concern; one thing worth eyeballing).

---

## §1 — `--timings`  ⏱️ ~3 min

```bash
uv run forensic extract <a repo you have> --force --timings
```

- [ ] A `Timings` block prints after the summary, slowest phase first, with a total.
- [ ] Sub-steps are indented under `build_graph` and `static`.
- [ ] Percentages are plausible and **sum to roughly 100 %**.
- [ ] No row says `OVERLAP`. (If one does, that's a real bug — sub-steps are double-counting.)
- [ ] On a **large** repo, `store_write` dominates. On this machine it was 79 % (Superset) and
      87 % (Omi) — see [`../findings/v0.10/PROFILE.md`](../findings/v0.10/PROFILE.md).

**Notes:**
> 

**The question behind it:** if you were told to make Deepdive twice as fast, does this output tell
you where to go? (It should say `store_write`, loudly. It should *not* let you waste a day on
PageRank, which is 0.04 %.)

---

## §2 — The upgrade path ⭐ *the headline*  ⏱️ ~10 min

Use a repo that **already has Deepdive output from an older release** — ideally one you extracted
during the v0.8 or v0.9 testing. If you don't have one, that's fine: extract once with 0.9.0
installed, then upgrade to 0.10.0 and continue.

### 2a. The advisory tells you, unprompted

```bash
uv run forensic extract <that repo> --force
```

- [ ] A **`Stale`** line appears naming a count and `--refresh-shims`.
- [ ] **Nothing on disk changed** — the stale files are still stale. Check one:
      `grep -c "DEC-0" <repo>/.claude/skills/codebase-refactoring/SKILL.md`
- [ ] The advisory did **not** appear for any file you had hand-edited.

**The question behind it:** before v0.10 there was no way to learn `--refresh-shims` existed at the
moment it mattered. Did this line arrive at the right time, and did it make you want to act?

### 2b. Refresh converges

```bash
uv run forensic extract <that repo> --force --refresh-shims
```

- [ ] A **`Refreshed`** line names the files — and skills appear as
      `codebase-refactoring/SKILL.md`, **not** a row of identical `SKILL.md`s (§3).
- [ ] Re-run plain `extract --force`: the `Stale` line is **gone**.
- [ ] No internal ledger IDs survive anywhere:
      ```bash
      grep -rn "DEC-[0-9]" <repo>/docs/codebase <repo>/CLAUDE.md <repo>/AGENTS.md \
                           <repo>/.claude <repo>/.cursor <repo>/.continue <repo>/.claude-plugin
      ```
      Expected: **no matches.**

### 2c. Restraint — it left your work alone

Before the run above, hand-edit something Deepdive owns (add a line to `CLAUDE.md`), then re-run
with `--refresh-shims`.

- [ ] Your edit **survived**.
- [ ] A skill file you replaced with your own (`name: my-own-skill`) also survived.

**Notes:**
> 

**This is Q5 in the core.** If anything here scores badly, say so plainly — the whole release is
this behaviour.

---

## §3 — Shim rows name the skill  ⏱️ ~1 min

- [ ] In §2b's `Refreshed` line (and the `Shims` line on a fresh repo), skills read as
      `codebase-<name>/SKILL.md`.
- [ ] You can tell **which** skills were touched without opening a directory.

---

## §4 — Release hygiene  ⏱️ ~2 min

Mostly enforced by CI now, but one thing is worth a human glance:

- [ ] Pick two `examples/*/AGENT_BRIEF.md`. Both footers say **0.10.0**, and both files are
      under 5 KB.
- [ ] Neither cites a `DEC-NNN`.

---

## §5 — Regression sweep (must not have moved)  ⏱️ ~5 min

v0.10 claims the engine is unchanged. Spot-check rather than trust:

- [ ] Cross-stack routes on a repo you tested in v0.9 report the **same counts and the same
      confidence split**.
- [ ] The five artifacts are all present and readable.
- [ ] `forensic repl` / `browse` / `onboard` / `deepdive` still start (PowerShell, not Git Bash).
- [ ] `forensic serve` still exposes nine tools.

**Notes:**
> 

---

## Scorecard

Now score the five stable questions in [`../MANUAL_TEST_CORE.md`](../MANUAL_TEST_CORE.md), and
copy the row into its history table.

| Question | Score 1–5 | One line of why |
|---|---|---|
| Q1 usable | | |
| Q2 honest | | |
| Q3 useful to an agent | | |
| Q4 worth the cost | | |
| **Q5 durable** ⭐ | | |

**Anything that surprised, annoyed, or delighted you that the questions didn't ask about:**
> 

---

*If Q5 lands below 4, that is v0.10's most important finding and belongs at the top of the v0.11
deferred ledger, whatever else scored well.*
