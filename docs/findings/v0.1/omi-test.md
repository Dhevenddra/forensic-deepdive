# Omi — v0.1 real-repo test

First external real-repo test of forensic-deepdive v0.1.0.

## Run summary

| | |
|---|---|
| Date | 2026-05-23 |
| Repo | [BasedHardware/omi](https://github.com/BasedHardware/omi) |
| Clone | `git clone --depth 200 --quiet` (139.9 s, 652 MB) |
| Tool version | `forensic-deepdive 0.1.0` (`80f143f` + `c84c173`) |
| OS | Windows 11 |
| Commands tested | `extract`, `update`, `query`, cache-hit re-`extract` |
| Generated artifacts | committed to `examples/omi/` |

### Timings

| Command | Run | Time |
|---|---|---|
| `extract` | cold | **92.3 s** (budget ≤15 min) |
| `update`  | re-extract `--force` | 75.8 s |
| `extract` | unchanged → cache hit | **2.2 s** |
| `query "Logger"` | searches 5 artifacts | < 1 s, 16 hits |

### Inventory the tool saw

- **5,717** files total / **652 MB** on disk after shallow clone.
- **1,860** source files inventoried (Dart 566, C 513, Python 464, Swift 317).
- **257** test files (DEC-012 classified them — excluded from the graph).
- ~350 files in **unsupported languages** (TypeScript 231, JS 54, Rust 46,
  Kotlin 14, Java 1) — invisible to the static layer; flatten + history
  still cover them.
- Repomix flatten produced a 99 MB / **31.9 M-token** pack (no `--compress`
  was passed; that's a v0.1 caller decision).

### Symbol graph

- **1,758 nodes / 42,854 edges** — by far the largest scale we've tested.
- PageRank (pure-Python power iteration) finished comfortably inside the
  92 s total — no scaling crisis at this size.

## ✅ What worked

1. **End-to-end run succeeded** on a 1,860-file polyglot repo, exit 0.
2. **Centrality identifies real architectural anchors** —
   `app/lib/utils/logger.dart` #1 (502 inbound edges),
   `desktop/Desktop/Sources/Logger.swift` #2,
   `app/lib/l10n/app_localizations.dart` #4 (i18n),
   `app/lib/services/services.dart` #6 (DI), `backend/database/cache_manager.py`
   #11. These are genuinely load-bearing files.
3. **Real cross-file dependency edges are accurate** —
   `backend/routers/* → backend/utils/* → backend/database/*`,
   `app/lib/pages/* → app/lib/providers/*`. A reader can use this to plan a
   refactor's blast radius.
4. **Cache hit is instant at scale** (2.2 s on a 1,860-file repo) — re-runs
   are essentially free.
5. **AGENT_BRIEF stays under cap** (1.3 KB on a huge repo) — the section
   packer holds.
6. **Shims behaved correctly** — Omi's existing `CLAUDE.md` / `AGENTS.md`
   were *skipped*, only the missing `.cursor` / `.continue` shims were
   written.
7. **Multi-language analysis** worked in one run — Dart, C, Python, Swift
   all parsed; language-scoped edges (DEC-012) kept their sub-graphs from
   cross-polluting.
8. **Determinism holds at scale** — `update` produced the same node/edge
   counts as `extract`. The DEC-012 sort fix is sound.
9. **`query` subcommand** found 16 `Logger` matches across 5 artifacts with
   context — agents and humans can interrogate the artifacts without
   opening every file.

## ⚠ Findings (v0.2 input — not v0.1 bugs)

Every finding below is a *precision* or *signal-to-noise* problem in the
v0.1 algorithm. The output is deterministic and honestly `EXTRACTED`-tagged;
the algorithm is naive in known ways.

### 1. Same-language method-name collisions are the dominant noise source
**Severity: high.** `fromJson` appears as a "Dependency hot spot"
**four** times (in `bt_device.dart`, `geolocation.dart`, `message.dart`,
`structured.dart`), `toString` **five** times, `error` and `of` twice each.
A reference to `obj.fromJson(json)` from any file creates edges to *every*
file that defines a method called `fromJson`. This is the v0.1 residual we
documented in DEC-012 and the headline item in the `v0.2-priorities`
memory, but it is much more visible at Omi's scale than at dogfood scale.

**v0.2 fix direction**: tighten the Dart `tags.scm` to drop attribute /
method-call references (mirror the Python fix in `e5f0fd2`). Possibly
followed by real scope resolution.

### 2. Locale-file fan-out
**Severity: high.** `app/lib/utils/time_utils.dart` shows edges to dozens
of `app_localizations_*.dart` (ar / be / bg / bn / bs / ca / …) because
every locale file defines the same method names (`timeCompactHours`,
`timeCompactMins`, …). Same root cause as #1 — the catch-all Dart
reference query matches identifiers that resolve through Flutter's
generated locale subclasses. **`Churn × centrality` is dominated by these
locale files**, which is misleading: they aren't actually depended-on, they
just *appear* to be because of the name collision.

**v0.2 fix direction**: same as #1, plus a minimum-centrality floor for
the `Churn × centrality` table so low-centrality files don't show up just
because they're high-churn.

### 3. Vendored libraries inflate rankings
**Severity: medium.** `omi/firmware/devkit/src/lib/opus-1.2.1/MacroCount.h`
and `omi/firmware/omi/src/lib/core/lib/opus-1.2.1/MacroCount.h` — the same
Opus codec header vendored into two firmware variants — rank #7 and #8
most-central files. Vendored third-party code is not application code; an
agent shouldn't be told to "treat MacroCount.h as load-bearing."

**v0.2 fix direction**: heuristic detection of vendored / third-party
directories (`vendor/`, `third_party/`, paths with embedded version
strings like `*-1.2.1*`, recognised library names). Classify as
`vendored` role alongside source/test/fixture.

### 4. Generated files leak into the graph
**Severity: medium.** `app/lib/models/announcement.g.dart` is in the
cross-file dependency table. `.g.dart` is build_runner-generated from
`.dart` source. Generated code creates real edges but isn't "the
codebase."

**v0.2 fix direction**: classify `.g.dart`, `.freezed.dart`,
`*_pb.py`, `*.generated.*` as a `generated` role.

### 5. Entry-point heuristic is too broad
**Severity: low–medium.** The MENTAL_MODEL "Likely entry points" lists
47 files — many of them genuine (`backend/main.py`, `app/lib/main.dart`,
each plugin's `main.py`), but also obvious false positives:
`omi/firmware/devkit/src/lib/opus-1.2.1/main.h` (Opus header),
`app/lib/backend/schema/app.dart` (a schema, just named `app.dart`),
`backend/models/app.py` (a model).

**v0.2 fix direction**: combine the filename heuristic with content
checks — Python `if __name__ == "__main__":`, Dart top-level
`void main()`, C `int main(`. Filter the vendored paths from #3.

### 6. Contributor dedup misses obvious duplicates
**Severity: medium.** The contributor list shows `Aarav Garg` *twice*
(726 + 112 commits), `Nik Shevchenko` *twice* (930 + 76), and `Thinh` +
`thịnh` separately. These are clearly the same person committing under
different email addresses or with different unicode in their git name.

**v0.2 fix direction**: read the repo's `.mailmap` if present
(git-standard for this), and/or aggregate by lowercase email-local-part.

### 7. Bots show up as top contributors
**Severity: low.** `github-actions[bot]` is the #3 contributor at 12.3%
share. Useful information ("this repo automates a lot") but misleading as
a *who-to-ask* signal.

**v0.2 fix direction**: filter `[bot]` accounts out by default, surface
them separately as an "Automation" line.

### 8. Churn list mixes code and non-code files
**Severity: low.** `desktop/CHANGELOG.json` tops the churn list at 423
commits, followed by `app/pubspec.yaml` and `codemagic.yaml`. These are
real churn, but they're release-process noise, not *code* hot spots.

**v0.2 fix direction**: emit two churn views — "all" (current) and
"source-only" — filtered to languages we parse.

### 9. `Churn × centrality` table is misleading on this repo
**Severity: medium.** Every entry in the table is an
`app_localizations_*.dart` with centrality `0.0008` (very low — 40× below
the #1 file). It's the intersection of two top-N lists without requiring
that either coordinate be *meaningfully* high. A user reading "files that
are **both** highly depended-on and frequently changed" expects high on
both axes.

**v0.2 fix direction**: require centrality ≥ Nth percentile (e.g. top
quartile) before including in this table, or replace with a
rank-product / harmonic-mean ordering.

## Acceptance-criteria status (after this run)

The v0.1.0 tag (`80f143f`) was placed before this test. With the Omi run
results now in hand:

| # | Criterion | Status after Omi |
|---|---|---|
| 1 | `uv tool install -e .` on macOS + Linux | ⏳ still untested (Windows-only) |
| 2 | `forensic --version` → `0.1.0` | ✅ |
| 3 | `forensic extract <tiny>` → 5 files | ✅ (`tiny_fixture`, golden-tested) |
| 4 | Omi extract ≤15 min | ✅ **92 s** |
| 5 | AGENT_BRIEF ≤5 KB | ✅ (1.3 KB on Omi) |
| 6 | 3 skills load in Claude Code | ⏳ still untested |
| 7 | `pytest -x` passes | ✅ (100 tests) |
| 8 | `ruff check` clean | ✅ |
| 9 | Example output in `examples/<repo>/` | ✅ `examples/omi/` |

**Net:** 7 of 9 met. The two remaining gaps are environmental
(cross-platform install, Claude Code skill audit) and need someone with
the right OS / setup.

## What this means for v0.2

The Omi run **doesn't change the order** of the v0.2 priorities from the
`v0.2-priorities` memory — it sharpens them:

1. **Reference-query precision** — findings #1 and #2 are the same root
   cause (Dart catch-all). This jumped from "noted concern" to "the
   single most visible defect." Should be the first v0.2 commit.
2. **Same-language scope resolution** — the *true* fix for #1 / #2 when
   `obj.fromJson` resolves to a method on a known type. Bigger work.
3. **File-role widening** — add `vendored` and `generated` roles (findings
   #3, #4) on top of DEC-012's source / test / fixture.
4. **Contributor pipeline** — `.mailmap` support + bot filter (#6, #7).
5. **Emit refinements** — entry-point detection (#5), source-only churn
   view (#8), `Churn × centrality` threshold (#9).

Net verdict: v0.1.0 is **functional and useful** on a real codebase the
size of Omi. The output's *known limitations* show up exactly where the
algorithm is documented to be naive, and they tell us what to build next.
