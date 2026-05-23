# forensic-deepdive v0.2 handoff package

Three documents go to Claude Code at the start of v0.2:

1. **`KICKOFF_v0.2.md`** — paste verbatim as the first message to Claude Code. Tells it what to read, in what order, and what to do first.

2. **`PRD_v0.2.md`** — the contract. The detailed product spec, scenario walkthrough, architecture, acceptance criteria, build order, DEC entries to write, test repos.

3. **`research_v0.2.md`** — save Claude's deep research output (the competitive landscape + hybrid architecture + roadmap report from this chat) as this filename. The PRD treats this as evidence; if the PRD and research conflict, PRD wins unless Claude raises a new DEC.

## Order of operations

1. In the forensic-deepdive repo root, drop `PRD_v0.2.md` and `research_v0.2.md` (and this README if you want) into a `docs/v0.2/` folder.
2. Open Claude Code in the repo.
3. Paste the prompt block from `KICKOFF_v0.2.md` as your first message.
4. Wait for the one-sentence confirmation.
5. Approve the first task (DEC-013 / GraphStore scaffold).
6. Standard session loop from there. Existing v0.1 protocol applies.

## What stays the same from v0.1

- CLAUDE.md, DECISIONS.md, PROGRESS.md as the runtime brain.
- Session start = read three docs; session end = update PROGRESS.
- Conventional commits.
- Never push without ask.
- Three skills (extract / query / update).
- Five artifacts (MAP / HOTPATHS / ARCHAEOLOGY / MENTAL_MODEL / AGENT_BRIEF).
- AGENT_BRIEF.md ≤ 5 KB.
- Apache-2.0.
- Pure-Python PageRank (DEC-011) and graph-scoping rules (DEC-012) remain Active.

## What changes in v0.2

Everything else. See PRD §1.2 for what v0.1 demonstrated could not work going forward, and PRD §2 for the one-paragraph product summary.

## Chat handoff note

This handoff was prepared at the end of a long chat on 2026-05-23. The Claude conversation that produced these documents is approaching its credit ceiling. Continue v0.2 conversations in a new Claude chat — point it at this folder (or the same files committed to docs/v0.2/) as context.

