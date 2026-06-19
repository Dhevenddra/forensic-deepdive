# MANUAL_TEST.md — forensic-deepdive, self-guided usability test (v0.7)

> **For you to run alone, without my help.** Work top to bottom, mark each `[ ]`, and write
> in the **Notes** boxes as you go — especially anything confusing, slow, wrong, or delightful.
> There are no wrong answers; the point is honest evidence. At the end there's a **scorecard**
> tied to the four questions that decide whether Deepdive goes public.
>
> Everything here is **pure-static** (no LLM at runtime) unless a step says `[semantic]`. The
> tool never edits your code — it only reads it and writes artifacts under `docs/codebase/`
> plus agent-onboarding files (listed in §9, all safe/regenerable).

> **Shell note (Windows).** The code blocks use Unix tools (`head`, `cat`, `wc`, `ls`). Run
> them in **Git Bash** or **WSL**. In **cmd.exe / PowerShell** they fail (e.g. `'head' is not
> recognized`); substitute:
> - `… | head` → drop it (the output is short), or PowerShell `… | Select-Object -First 20`
> - `… | cat` → drop it; for a **pipe-safety** check (§11) redirect to a file instead:
>   `uv run forensic extract … > out.txt 2>&1` — a redirected stream is the same non-TTY
>   cp1252 condition a pipe is, so it exercises the exact path we hardened.
> - `wc -c file` → PowerShell `(Get-Item file).Length`
> - `NO_COLOR=1 cmd` → PowerShell `$env:NO_COLOR=1; cmd` (then `Remove-Item Env:NO_COLOR`)

## The four questions we're really answering
1. **Usable?** Could *you* drive it without me?
2. **Does it help an agent** find issues, trace flows, and work autonomously?
3. **Are the 5 markdown artifacts useful** — or a gimmick?
4. **How does an agent start** — is it told what the tool, outputs, and capabilities are?

Keep these in mind; the scorecard at the end asks you to rate each 1–5.

---

## What changed since your first run (2026-06-19) — re-test these

Your first pass surfaced four CLI-surface gaps (the usability gate working as intended). All
are fixed with regression tests; details in `docs/findings/v0.7/manual-test-cli-gaps.md`.
When you go back through, pay extra attention to:

- **§7 / §8 — `serve --repo`.** `serve` now accepts `--repo` (it was positional-only, which
  is the error you hit). The §7 command and the §8 MCP config now work as written.
- **§2 / §11 — `extract` piped/redirected.** The styled summary's `✓` used to crash a Windows
  cp1252 pipe; it now degrades to ASCII. Re-run `uv run forensic extract … | cat` and confirm
  clean text + exit 0.
- **§0 / §5 — `--help` piped.** `forensic --help | cat` and `forensic trace --help | cat` no
  longer crash on cp1252 (an arrow glyph in trace's help was the culprit).
- **§9 — onboarding shims now list all 9 MCP tools** (was a stale "five"). **Important:** shims
  are *write-if-absent* — a re-`extract` will NOT overwrite an existing `CLAUDE.md`/`AGENTS.md`.
  To regenerate them, delete the old ones first (see the note added to §9).

---

## 0. Install & smoke  ⏱️ ~2 min
```bash
cd C:/Dev/projects/forensic-deepdive
uv sync --all-extras
uv run forensic --version          # → forensic-deepdive 0.7.0
uv run forensic --help             # the command list
```
- [ ] Version prints. Help lists: `extract update query trace graph list serve info insights version`.

**Notes:**
> 

---

## 1. `forensic info` — capabilities at a glance  ⏱️ ~1 min
This is the "what can this thing do" screen (your Q4 starting point).
```bash
uv run forensic info
```
- [ ] You see the **DEEPDIVE** block banner (blue gradient), then a **Capabilities** panel:
  Artifacts (5), Protocols (5), MCP tools (9), and the **Confidence legend** (`● EXTRACTED`,
  `◐ INFERRED`, `○ AMBIGUOUS`).
- [ ] Pipe it and confirm it degrades to clean text: `uv run forensic info | cat` (no garbled
  colour codes; a plain `DEEPDIVE` title; `[E] EXTRACTED` letters).

**Was the panel enough to understand what the tool offers? Notes:**
> 

---

## 2. The headline run — `extract` on a small cross-stack repo  ⏱️ ~1 min
We'll use **spring_react_demo** (a React frontend + Spring backend — a clean cross-stack case).
```bash
uv run forensic extract C:/Dev/scratch/spring_react_demo --force
```
- [ ] A live spinner, then a summary ending with a coloured **Routes** line, e.g.
  `2 cross-stack route(s)  (● E 2 ◐ I 0 ○ A 0)`. The 5 artifacts are listed.
- [ ] Note the elapsed feel and whether the numbers look believable.

**Notes (speed, clarity, surprises):**
> 

---

## 3. Read the 5 artifacts — the core of Q3  ⏱️ ~15 min (the most important part)
Open `C:/Dev/scratch/spring_react_demo/docs/codebase/`. Read each and judge: **would this make
you (or an agent) faster in an unfamiliar repo, or is it filler?**

- [ ] **AGENT_BRIEF.md** — the headline (≤5 KB). Assertive *Never/Always* rules + the cross-stack
  routes. *Is it the first thing you'd want an agent to read?* `wc -c .../AGENT_BRIEF.md` (≤5120).
- [ ] **MAP.md** — the structural map (dirs, key files, entry points). *Accurate? Useful?*
- [ ] **HOTPATHS.md** — the important code paths + the **cross-stack routes** table
  (consumer → handler → endpoint, with confidence). *This is the differentiator — does it land?*
- [ ] **ARCHAEOLOGY.md** — git-history signal (churn, ownership, co-change). *Insightful or noise?*
- [ ] **MENTAL_MODEL.md** — the "how to think about this codebase" narrative. *True to reality?*

**For EACH artifact, one line: keep / cut / fix. Be brutal — this answers Q3:**
> AGENT_BRIEF:
> MAP:
> HOTPATHS:
> ARCHAEOLOGY:
> MENTAL_MODEL:

---

## 4. Judge accuracy on a repo YOU know cold  ⏱️ ~15 min
The real Q2/Q3 test: run it on **a codebase you know intimately** so you can catch lies.
Suggested: **hermes-agent** (yours) — or any repo you wrote.
```bash
uv run forensic extract C:/Dev/scratch/hermes-agent --force
```
Then read its `docs/codebase/AGENT_BRIEF.md` + `MENTAL_MODEL.md` + `HOTPATHS.md`.
- [ ] Does the MENTAL_MODEL match how *you* actually think about the repo?
- [ ] Are the Never/Always rules things you'd genuinely tell a new teammate?
- [ ] Did it find real flows/hotpaths — or miss the ones that matter?
- [ ] Anything **wrong** (hallucinated)? (It shouldn't fabricate — note any case if it does.)

**The honest verdict — does it understand a repo you know? Notes:**
> 

---

## 5. `trace` — the cross-stack feature slice  ⏱️ ~3 min
The flow-finding capability (Q2). Pick a frontend call symbol (the summary/HOTPATHS name some).
```bash
# downstream: a frontend call → endpoint → handler → tail
uv run forensic trace addUser --repo C:/Dev/scratch/spring_react_demo
# upstream: who calls this handler/endpoint
uv run forensic trace createUser --upstream --repo C:/Dev/scratch/spring_react_demo
# machine mode (pipe-safe JSON)
uv run forensic trace addUser --repo C:/Dev/scratch/spring_react_demo --json    # add `| head` only in Git Bash/WSL
```
- [ ] The tree shows `[POST] /api/users via http ● EXTRACTED → …createUser`. Colours + glyphs.
- [ ] `--json` is plain JSON (no colour codes) — usable by a script/agent.

**Did the trace answer "where does this flow go" in one command? Notes:**
> 

---

## 6. `query`, `graph`, `list` — the rest of the CLI  ⏱️ ~4 min
```bash
# grep the generated artifacts
uv run forensic query "endpoint" --artifacts-dir C:/Dev/scratch/spring_react_demo/docs/codebase
# a bounded Mermaid diagram of the code graph (paste into a Mermaid viewer)
uv run forensic graph --repo C:/Dev/scratch/spring_react_demo --central --max-nodes 30
# the multi-repo registry (every repo you've extracted is remembered)
uv run forensic list
```
- [ ] `query` returns matches with context. `graph` prints valid Mermaid. `list` shows your repos.

**Notes:**
> 

---

## 7. The graph web UI — `serve --ui`  ⏱️ ~3 min
```bash
uv run forensic serve --ui --repo C:/Dev/scratch/spring_react_demo
# opens a local (127.0.0.1) Sigma.js explorer; Ctrl-C to stop
```
- [ ] The whole-graph explorer opens. Filter by edge type / confidence / language. The
  cross-stack `ROUTES_TO` edges are highlighted. (Read-only; loopback-only.)

**Is the visual graph useful, or do the markdown artifacts already suffice? Notes:**
> 

---

## 8. The MCP server + the 9 tools — "use it the way an agent does"  ⏱️ ~15 min
This is **how an agent actually consumes Deepdive** (Q2/Q4). Wire the server into Claude Code
(or Claude Desktop). Add to your MCP config (adjust **both** paths):
```json
{ "mcpServers": { "deepdive": {
    "command": "uv",
    "args": ["run", "--project", "C:/Dev/projects/forensic-deepdive",
             "forensic", "serve", "--repo", "C:/Dev/scratch/spring_react_demo"]
} } }
```
> **Two things that trip people up here (both real, both fixed/required):**
> 1. **`--project` is mandatory.** The MCP server launches with its working directory set to
>    the *target* repo, where `uv run forensic` can't find the package (`program not found`).
>    `--project <forensic-deepdive dir>` pins the right environment. (Once Deepdive is
>    `uv tool install`-ed and on PATH, drop `uv run --project` and just use `"command":
>    "forensic"`.)
> 2. **Restart + approve.** MCP servers load at session start, and a project-scoped `.mcp.json`
>    needs a one-time trust prompt — a mid-session add never exposes the tools. Restart the
>    agent in the repo dir and approve `deepdive` (or use `/mcp`). Then `mcp__deepdive__*`
>    (nine tools) appear.

Then, in that agent, exercise the **9 composite tools** by asking for each (the tool names):
- [ ] **impact** — "what's the blast radius of changing `createUser`?"
- [ ] **context** — "give me a one-call overview of `UserController`."
- [ ] **archaeology** — "what's the git history/ownership of this file?"
- [ ] **flow** — "trace the execution flow from `addUser`."
- [ ] **query** — "Cypher: count Endpoints" and a natural-language: "where are users created?"
- [ ] **record_insight** — have it record a learning about the repo.
- [ ] **recall_insights** — ask it to recall what it learned (newest-first; recency-decayed).
- [ ] **visualize** — "draw a Mermaid diagram around `UserController`."
- [ ] **trace** — "trace the cross-stack slice for the create-user feature."

**Did the agent get genuinely useful answers it couldn't get from plain file-reading? Notes:**
> 

---

## 9. The agent-onboarding question (Q4) — does an agent get *told*?  ⏱️ ~10 min
When you ran `extract`, Deepdive wrote **onboarding files into the repo root** (all safe):
`CLAUDE.md`, `AGENTS.md`, `.cursor/rules/codebase.mdc`, `.continue/rules/codebase.md`,
`.claude-plugin/plugin.json`, and **5 skills** under `.claude/skills/codebase-*/SKILL.md`.
```bash
ls C:/Dev/scratch/spring_react_demo            # CLAUDE.md, AGENTS.md, .cursor, .continue, .claude*
cat C:/Dev/scratch/spring_react_demo/CLAUDE.md # points the agent at docs/codebase/AGENT_BRIEF.md
```
> **If you extracted this repo before 2026-06-19**, its `CLAUDE.md`/`AGENTS.md` may still say
> "five composite tools". Shims are *write-if-absent* (they never clobber hand-edits), so delete
> the old ones and re-extract to get the corrected nine-tool version:
> ```bash
> rm C:/Dev/scratch/spring_react_demo/CLAUDE.md C:/Dev/scratch/spring_react_demo/AGENTS.md
> uv run forensic extract C:/Dev/scratch/spring_react_demo --force
> grep "composite tools" C:/Dev/scratch/spring_react_demo/CLAUDE.md   # → "nine composite tools"
> ```
**The real test:** open a **fresh** Claude Code session in `C:/Dev/scratch/spring_react_demo`
and — *without mentioning Deepdive* — give it a real task, e.g.
*"I need to add an email field to users end-to-end. Where do I touch?"*
- [ ] Does the agent **discover** `CLAUDE.md` / `AGENT_BRIEF.md` / the skills on its own?
- [ ] Does it use them to answer faster/better than a cold agent would?
- [ ] Is the onboarding **obvious**, or did you have to point it there?

**This is the make-or-break for Q4. Be specific about what the agent did: Notes:**
> 

---

## 10. Memory (lane iii) — durable agent learning  ⏱️ ~5 min
```bash
# from the MCP agent (§8) or directly: record then recall an insight
# then prove portability — the shadow-ref survives a clone:
cd C:/Dev/scratch/spring_react_demo
git rev-parse refs/forensic-deepdive/insights   # exists after a record
uv run forensic insights push --dry-run          # shows what WOULD push (never auto-pushes)
```
- [ ] `record_insight` → `recall_insights` round-trips (lexical; `[semantic]` adds meaning-match).
- [ ] `insights push --dry-run` reports the ref + remote without pushing (explicit-only).

**Notes:**
> 

---

## 11. Confidence taxonomy + pipe/CI safety  ⏱️ ~3 min
Everything Deepdive asserts is tagged **EXTRACTED** (literal/deterministic) / **INFERRED**
(resolved heuristically) / **AMBIGUOUS** (several candidates — surfaced, never guessed).
- [ ] In artifacts + `trace` + the summary, the confidence is visible and the glyph/word is
  present even with colour off: `NO_COLOR=1 uv run forensic trace addUser --repo …` and
  `uv run forensic --plain info`.
- [ ] Pipe safety: `uv run forensic extract … | cat` — plain text, no ANSI; artifacts on disk
  are plain markdown.

**Do you trust the confidence tags? Did anything claim EXTRACTED that was actually a guess? Notes:**
> 

---

## 12. Scale + breadth (optional, heavier)  ⏱️ ~15 min
- [ ] **Scale:** `uv run forensic extract C:/Dev/scratch/superset --force` (~18k symbols). Does it
  finish, stay under ~2–3 min, and produce sane artifacts? AGENT_BRIEF still ≤5 KB?
- [ ] **Protocol breadth** (already-extracted graphs in scratch): grpc-examples (gRPC),
  rabbitmq-tutorials (messaging), jersey/nest (JAX-RS/NestJS), wagtail (Django). Spot-check that
  `HOTPATHS.md` cross-stack routes look right for the stack you know.
- [ ] **Dogfood:** `uv run forensic extract C:/Dev/projects/forensic-deepdive --force` — does
  Deepdive understand *its own* code? Read its AGENT_BRIEF.

**Notes:**
> 

---

## Feature checklist (so we don't forget our own capabilities)
Tick what you actually exercised:
- [ ] CLI: `version` · `info` · `extract` (`--force/--workers/--semantic/--output/--legacy-repomix`)
  · `update` · `query` · `trace` (`--upstream/--json/--depth/--graph`) · `graph` (Mermaid) ·
  `list` · `serve` · `serve --ui` · `insights push` (`--dry-run/--remote`) · `--plain`/`NO_COLOR`
- [ ] 5 artifacts: MAP · HOTPATHS · ARCHAEOLOGY · MENTAL_MODEL · AGENT_BRIEF (+ DEEP overflow)
- [ ] 9 MCP tools: impact · context · archaeology · flow · query · record_insight ·
  recall_insights · visualize · trace
- [ ] 5 protocols: HTTP (FastAPI/Flask/Spring/Express/NestJS/JAX-RS/Django/Flask-AppBuilder/
  OpenAPI) · MCP tools · registry-dispatch · gRPC · messaging (Kafka/RabbitMQ/AMQP-topic)
- [ ] Graph: Symbol/File/Module/Endpoint/Table/Commit/Author nodes; CALLS/DEFINES/IMPORTS/
  EXTENDS/IMPLEMENTS/INJECTS/PERSISTS_TO/HANDLES/CALLS_ENDPOINT/ROUTES_TO edges; confidence tags
- [ ] Memory: record/recall (FTS5/BM25 + `[semantic]` RRF + recency decay) · git shadow-ref
  (save/load/push)
- [ ] Onboarding shims: CLAUDE.md · AGENTS.md · .cursor · .continue · plugin.json · 5 skills
- [ ] Confidence: EXTRACTED/INFERRED/AMBIGUOUS, never colour-alone · pipe/CI safe
- [ ] Languages: Python · TS/JS · Java · Dart · Go · C · … (tree-sitter)

---

## Scorecard — the decision
Rate 1 (gimmick / unusable) to 5 (genuinely valuable). Add a sentence each.

> Filled 2026-06-19 from the evidence: the solo MANUAL_TEST run, the agent-onboarding A/B/C on
> Iris-Nearby, and the live MCP test (nine tools, post-restart). Owner can adjust.

| # | Question | 1–5 | One-sentence verdict |
|---|---|---|---|
| 1 | **Usable** without help? | **4** | Drove every step solo and confirmed usable; the four CLI gaps (`serve --repo`, two cp1252 pipe crashes, the MCP `--project` launch) were real friction but all found-and-fixed during the run. |
| 2 | Helps an agent find issues/flows/work autonomously? | **4** | A strong *lead-generator + git-risk lens*: archaeology/Cypher/briefs are high-trust, while `impact()`/`flow()`/NL-`query()` are high-recall but **noisy** (a grounded stress-test caught `impact()` false positives and an NL miss — see `docs/findings/v0.7/mcp-tool-review.md`), so it speeds *finding what to read*, not *deciding what breaks*; full autonomous task-execution remains unproven and deferred. |
| 3 | Are the 5 artifacts useful (not a gimmick)? | **4** | MAP / HOTPATHS / MENTAL_MODEL clearly earned their keep (agents cited them and beelined to the load-bearing files); ARCHAEOLOGY is the weakest cut on solo/low-history repos and the AGENT_BRIEF Never/Always rules need richer signal. |
| 4 | Does an agent get properly onboarded (told tool/outputs/capabilities)? | **5** | In a real fresh session the agent auto-read `AGENT_BRIEF` on turn one and auto-routed to the right `codebase-*` skill per task; with the MCP wired it used all nine tools — onboarding is obvious *when CLAUDE.md auto-loads* (CWD = repo). |

**Top 3 painpoints (ranked):**
> 1. CLI/onboarding-surface gaps that only show under real use: `serve --repo` positional, piped `--help` and `extract` crashing on Windows cp1252, and the MCP `uv run --project` launch requirement (all now fixed).
> 2. Autonomous usefulness (Q2) is only partially evidenced — the agent *planned* well but didn't execute an end-to-end change; needs a dedicated future test.
> 3. On a fresh/solo repo the git-driven artifacts thin out — ARCHAEOLOGY ownership is empty (bus factor 1) and the AGENT_BRIEF rules lean on centrality artifacts (e.g. `AppColors`).

**Top 3 delights:**
> 1. Real-session **skill routing** — the agent picked `codebase-onboarding` / `codebase-impact-analysis` per task unprompted and followed the prescribed artifact order.
> 2. The MCP `impact()` caught real depth-2/3 ripple the by-hand pass missed (high recall) — though a later stress-test showed the same wide net also returns false positives, so it's a lead-generator to verify, not a source of truth.
> 3. Four independent agents converged on the same correct findings (read receipts ~90% pre-built, the `chat_screen.dart:124-132` gap, the Hive `typeId:3` collision) — the artifacts didn't mislead any of them.

**Publish-ready? (y/n) — and what's the one thing that must be true first:**
> **Not yet — "usable" is proven, but publish should wait on a dedicated autonomous-usefulness (Q2) test in a later version.** The one thing that must be true first: an agent completes a real end-to-end change (not just a plan) measurably faster/safer *because of* the artifacts + MCP, on a repo richer than a solo one.
> 

---

*Deepdive stays private until questions 1–4 are answered with confidence. This document is the
instrument; your honest notes are the data. Thank you for testing it the way a stranger would.*
