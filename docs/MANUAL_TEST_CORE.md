# MANUAL_TEST_CORE.md — the stable core (do not rewrite per release)

> **This file is the instrument. It does not change between releases.**
>
> Each release adds a `docs/v<X.Y>/MANUAL_TEST.md` **delta** covering what's new that cycle.
> This core stays fixed so the five scores form a **time series** instead of five unrelated
> opinions. Changing a question here resets that series — do it only with a DEC saying why.

## Why this file exists (DEC-116)

Through v0.9, `MANUAL_TEST.md` was written fresh each release, shaped by whatever had just been
built. It drifted into a checklist of *what changed* rather than a measuring instrument, so two
releases' scores were never comparable — 4/5 on "is it usable" in v0.7 and in v0.9 were answers
to differently-framed questions, asked after doing different things.

The split: **stable core here** (the five questions, fixed wording, fixed anchors) plus a
**per-release delta** (the new surface, the regressions to re-check, the known-open findings to
verify closed).

## How to run it

1. Do the release's `docs/v<X.Y>/MANUAL_TEST.md` first — it walks the new surface and any
   re-tests.
2. Then come back here and score the five, **alone, without the agent's help**, from what you
   actually experienced. Not from what the docs claim.
3. Record scores in the table at the bottom of the release's delta file, and copy the row into
   the history table below.

**Score honestly and against the anchors, not against last time.** A score that only goes up is
an instrument that has stopped measuring.

---

## The five questions

### Q1 — Usable
*Could you drive it to a useful answer without asking for help or reading source?*

| | |
|---|---|
| **1** | Got stuck; needed help or source-reading to complete a basic task. |
| **2** | Completed it, but by trial and error; several dead ends. |
| **3** | Worked, with one or two places where the right move wasn't obvious. |
| **4** | Smooth. Errors, when they happened, told me what to do next. |
| **5** | Obvious throughout. I never wondered what to type. |

### Q2 — Honest
*Did it ever tell you something that wasn't true — a wrong count, a bad citation, a confident
claim about code that didn't hold up when you opened the file?*

| | |
|---|---|
| **1** | Found a confidently-stated falsehood. |
| **2** | Found something misleading, or a number I couldn't reconcile. |
| **3** | Nothing false, but some things unverifiable or unclear. |
| **4** | Everything I spot-checked held up; uncertainty was marked where it existed. |
| **5** | Spot-checks held, **and** the confidence tags (EXTRACTED / INFERRED / AMBIGUOUS) matched my own judgement of how sure the tool should have been. |

### Q3 — Useful to an agent
*Did giving an AI agent these artifacts make its work on this repo measurably better — faster
orientation, better-targeted edits, fewer wrong files opened?*

| | |
|---|---|
| **1** | No difference, or it distracted the agent. |
| **2** | Marginal; the agent mostly ignored them. |
| **3** | Helped orientation, but I couldn't point at a concrete win. |
| **4** | Clear win I can name: it went to the right place because of an artifact. |
| **5** | The agent auto-discovered the brief and routed itself to the right skill **unprompted**, and the resulting work was visibly better. |

### Q4 — Worth the cost
*Given what it cost — install, extract wall time, disk, the files it wrote into your repo — would
you run it again on a repo you cared about?*

| | |
|---|---|
| **1** | No. The cost outweighs the value. |
| **2** | Only on a repo I was desperate about. |
| **3** | Maybe, for a large unfamiliar codebase. |
| **4** | Yes, for any repo I'm new to. |
| **5** | Yes, routinely — and I'd be annoyed to work without it. |

### Q5 — Durable
*Run it a second time on the same repo, after the first run's output is already there. Does the
result stay correct and current — artifacts, shims, and skills all converged, nothing stale, and
nothing of yours overwritten?*

| | |
|---|---|
| **1** | The second run broke something or clobbered a file I'd edited. |
| **2** | Left stale output behind with no indication anything was out of date. |
| **3** | Converged, but I had to know a flag existed to make it happen. |
| **4** | Converged, told me what it was going to do, left my edits alone. |
| **5** | As 4, and I'd trust it in a repo I share with other people. |

> Q5 was added in v0.10 and is the one question the tool had **never** been asked. The upgrade
> path was untested for three releases (DEC-108/110). If it scores below 4, that is the release's
> most important finding regardless of everything else.

---

## Score history

One row per release. Never edit a past row — a bad score is data.

| Release | Q1 usable | Q2 honest | Q3 agent | Q4 cost | Q5 durable | Notes |
|---|---|---|---|---|---|---|
| v0.10.0 | | | | | | first run of the stable instrument |

Earlier releases (v0.7–v0.9) are deliberately **not** back-filled: they answered differently
worded questions, and inventing comparable numbers for them would be exactly the fabrication this
file exists to prevent. The series starts at v0.10.
