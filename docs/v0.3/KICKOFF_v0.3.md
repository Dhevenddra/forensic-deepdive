# KICKOFF_v0.3.md — operating mode for the v0.3→v1.0 arc

> Paste the block in §8 as your first message to Claude Code in the repo. Everything above it is the
> reasoning that block compresses. This file binds with `CLAUDE.md` (session discipline) and points at
> `PRD_v0.3.md` (the contract) and `research_v0.3.md` (the evidence).

---

## 1. What you're building (one breath)
forensic-deepdive is a persistent code knowledge graph served to AI coding agents over MCP. v0.2 made
it real (LadybugDB graph, 8 languages, git archaeology, 7 MCP tools, confidence taxonomy, 394 tests,
tagged). **This arc takes it from v0.2 to v1.0 — stopping just short of the IDE.** v0.3 = Precision &
Speed (foundation). Then v0.4 wedge, v0.5 memory, v0.6 Rust performance, v1.0 scale.

## 2. The one decision that reverses the old roadmap
The old plan put cross-stack (Spring/React) in v0.3. **It moves to v0.4.** Reason: you cannot join a
React `fetch()` to a Spring route until you can resolve the call sites at both ends, and right now
dotted calls are dropped (DEC-025). Method resolution + speed + query are **prerequisites** for the
wedge. This re-sequence is **DEC-034** — write it before any v0.3 code, and never undo it without a
superseding DEC. (Full rationale: `PRD_v0.3.md` §1.)

## 3. Session-start protocol (in addition to CLAUDE.md's)
1. `CLAUDE.md` → `DECISIONS.md` → `PROGRESS.md` → `git log --oneline -10` (as always).
2. Read `PRD_v0.3.md` §0–§4 and this file. Skim `research_v0.3.md` once; re-read the § X a PRD item cites.
3. State in one sentence: *"Working on v0.3 Item <X> (<name>), respecting DEC-<N> about <Y>."*
4. If `DECISIONS.md` ends below DEC-033, you're on the right base; v0.3 starts at **DEC-034**.

## 4. Build order (do not interleave out of order)
**v0.3:** A (incremental parse cache) → B (parallel parse) → C (method resolution) → D (Rust) →
E (hybrid query) → F (Mermaid) → G (acceptance). A+B are co-designed (the perf pair). C needs DEC-023
members. E and F are independent and may interleave with each other, not with C.

Finish v0.3 and ship its findings **before** starting v0.4. After v0.3, write the v0.4 detail PRD pass
(the PRD scopes v0.4 but intentionally does not spec it line-by-line — you'll know more by then).

## 5. The five rules that catch most mistakes here
1. **Determinism survives parallelism + caching.** Workers return dataclasses; parent collects-then-sorts
   by `(rel_path, start_byte, kind, name)`. Every parallel/cached path has a `--workers 1` and a
   cold-vs-warm golden test proving byte-identical artifacts. (DEC-035.)
2. **Confidence is sacred.** New resolvers tag EXTRACTED/INFERRED/AMBIGUOUS. The heuristic receiver
   resolver (Item C) is **INFERRED** — never claim EXTRACTED for an inferred receiver type.
3. **Pure-static floor (DEC-009).** All 5 artifacts must build with no LLM, no network, no embeddings.
   Hybrid query's semantic tier is opt-in and degrades to FTS5+structural, and the response says so.
4. **AGENT_BRIEF ≤ 5 kb** on every test repo. Overflow → `AGENT_BRIEF_DEEP.md`.
5. **The 5-artifact contract holds.** New data extends artifacts (or adds a section); it does not
   rename/reorder them. New MCP tool (`visualize`) and any new section update all three SKILL.md files,
   README, and the tool count (CLAUDE.md coupling rule).

## 6. Calibration honesty (the v0.2 lesson)
v0.2 planned 8 DECs and shipped 21 (2.5×). Expect v0.3 to surface ~2–3× the pre-drafted DECs in
`PRD_v0.3.md` §4.8. That's normal — log each real choice as an append-only DEC; don't compress the
truth to hit a count. Update `PROGRESS.md` at every session end with done / in-flight / blocked.

## 7. What "done" means for v0.3 (the gate — PRD §4.8)
`pytest -x` green; ruff clean; warm re-extract on Omi in single-digit seconds; cold extract materially
below 930s with headroom; AMBIGUOUS CALLS edges measurably reduced; hybrid NL query shaped + provenance
+ confidence offline; Mermaid bounded + confidence-styled; Rust fixture + one real Rust repo parsed;
byte-identical across worker counts and cold/warm; `examples/gitnexus` + `examples/fastapi` committed;
findings under `docs/findings/v0.3/` with real numbers. The supervisor will test v0.3 across more repos
and report back — make the findings easy to compare.

## 8. The paste-able kickoff block
```
Read CLAUDE.md, DECISIONS.md, PROGRESS.md, and `git log --oneline -10`. Then read
docs/v0.3/PRD_v0.3.md (§0–§4 fully, §5–§11 skim) and docs/v0.3/KICKOFF_v0.3.md;
keep docs/v0.3/research_v0.3.md handy for the §refs.

We are starting the v0.3→v1.0 arc. v0.3 is "Precision & Speed" and is specified to
implementation depth; later versions are scoped and get their own detail passes.

FIRST: write DEC-034 recording the roadmap re-sequence (foundation in v0.3, cross-stack
wedge moved to v0.4) with the dependency-ordering rationale from PRD §1. Do not write
other code until DEC-034 is committed.

THEN build v0.3 in order A→B→C→D→E→F→G (PRD §4.1–§4.7), one item at a time, tests green
before moving on, a DEC for every non-trivial choice (expect ~2–3× the §4.8 pre-draft),
PROGRESS.md updated each session end. Honor every cross-version invariant in PRD §3 —
especially determinism under parallelism/caching, the confidence taxonomy, and the
pure-static floor.

Confirm your understanding in one sentence, write DEC-034, then begin Item A. Do not push
to remote. Do not touch v0.4+ until v0.3 passes its §4.8 gate.
```

---

*The IDE is out of scope for this whole arc. Build the substrate so well that, when the IDE ideation
finally happens, the coupling for agent development is already better than we'd have planned for. That's
the only forward-looking instruction: don't foreclose it (PRD §10) — but don't build toward it yet.*
