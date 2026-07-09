# MANUAL_TEST.md — forensic-deepdive, self-guided usability test (v0.9)

> **For you to run alone, without my help.** Work top to bottom, mark each `[ ]`, and write
> in the **Notes** boxes as you go — especially anything confusing, slow, wrong, or delightful.
> There are no wrong answers; the point is honest evidence. At the end there's a **scorecard**
> tied to the questions that decide whether v0.9.0 ships.
>
> Everything here is **pure-static** (no LLM at runtime) unless a step says `[semantic]`. The
> tool never edits your code — it only reads it and writes artifacts under `docs/codebase/`
> plus agent-onboarding files (all safe/regenerable).

> **⚠ Shell note (Windows) — new in v0.9 and load-bearing.** The four interactive surfaces
> (`repl`, `browse`, `onboard`, `deepdive`) need a **real Windows console**: run them in
> **PowerShell** or **cmd.exe**, *not* Git Bash / MinTTY. Under Git Bash `sys.stdin.isatty()`
> lies (returns True) and `prompt_toolkit` has no console screen buffer — you'll get an
> actionable hint telling you exactly this, which is itself one of the things to verify (§6).
> `winpty uv run forensic repl` also works.
>
> Non-interactive steps use Unix tools (`head`, `cat`, `wc`, `grep`). Run **those** in Git Bash
> or WSL. In PowerShell substitute: `wc -c file` → `(Get-Item file).Length`; `NO_COLOR=1 cmd` →
> `$env:NO_COLOR=1; cmd` then `Remove-Item Env:NO_COLOR`.

## The questions we're really answering (v0.9)

v0.7 proved **usable**; v0.8 shipped publicly on **assisted-analysis** value. v0.9 is
"The Interactive CLI" — the release that decides whether Deepdive is a tool you *invoke* or a
tool you *sit inside*. So this run asks:

1. **Is the interactive layer worth its weight?** Does `repl`/`browse`/`onboard`/`deepdive`
   beat typing `forensic <cmd>` over and over — or is it a shell for its own sake?
2. **Is `deepdive` the front door?** If a newcomer ran exactly one command, should it be this?
3. **Does `onboard` actually onboard?** Could a stranger go from `git clone` to a wired-up MCP
   server without reading any docs?
4. **Do the emitted artifacts stand on their own?** (v0.9 removed internal `DEC-NNN` ledger
   references — they were dangling links for every consumer.) Anything still unresolvable?
5. **Is it still honest?** Confidence tags, the AMBIGUOUS tier, the two reporting fixes.

Rate each 1–5 in the scorecard at the end.

---

## What changed since v0.8 — re-test these

- **§3 `forensic repl`** — one held-open store, many questions. NL by default, `:cypher` for raw.
- **§4 `forensic browse`** — a read-only Textual TUI graph browser. The offline sibling of
  `serve --ui`.
- **§5 `forensic onboard`** — the guided wizard. `--yes` runs it scripted and needs no extra.
- **§6 `deepdive`** — the session shell (a *new console script*, not a `forensic` subcommand).
- **§7 no ledger IDs in output** — no artifact, shim, or MCP payload may say `DEC-NNN`.
- **§8 the two reporting fixes** — examples-only source counts; `<module>` display names.
- **§9 `mcp-config --dev` + `list --prune`.**

Both v0.8 known-open findings are **closed** in v0.9 (§8). Verify, don't trust.

---

## 0. Install & smoke  ⏱️ ~2 min
```bash
cd C:/Dev/projects/forensic-deepdive
uv sync --all-extras
uv run forensic --version          # → forensic-deepdive 0.9.0
uv run forensic --help             # the command list
```
- [ ] Version prints **0.9.0**. Help now also lists `repl`, `browse`, `onboard`.
- [ ] The `deepdive` console script exists: `uv run deepdive --help`.

**Notes:**
>

---

## 1. Build a graph to play in  ⏱️ ~2 min
Everything below needs a graph. Use a repo you know cold.
```bash
uv run forensic extract C:/Dev/scratch/hermes-agent --force
```
- [ ] Live spinner → summary → 5 artifacts + `ARCHITECTURE.md`. A `.deepdive/graph.lbug` exists.

**Notes (speed, clarity, surprises):**
>

---

## 2. The interactive extra — what happens without it  ⏱️ ~1 min
```bash
uv run --no-dev --extra mcp forensic repl --repo C:/Dev/scratch/hermes-agent
```
- [ ] Prints an **actionable install hint** (install the `[interactive]` extra), not a traceback.
- [ ] `forensic extract`, `serve`, `query`, `trace` all still work without the extra.

**Notes:**
>

---

## 3. `forensic repl` — connect once, ask many  ⏱️ ~8 min
> **PowerShell or cmd.exe.** Not Git Bash.
```powershell
uv run forensic repl --repo C:/Dev/scratch/hermes-agent
```
Try, in one session:
- [ ] A bare natural-language question: `where is whatsapp sent?` → ranked symbols, no LLM.
- [ ] Three or four more questions **without reconnecting** — is it noticeably faster than
  `forensic query` per-question? (That connect-once promise is the whole point.)
- [ ] `:cypher MATCH (e:Endpoint) RETURN count(e)` → a raw result.
- [ ] `:help` lists the commands; **Ctrl-D** exits; **Ctrl-C** cancels the current line
  (it must NOT kill the session).
- [ ] Up-arrow history and Tab-completion on `:c…` work.

**Is the REPL faster *and* nicer than repeated one-shot commands? Or is it a novelty? Notes:**
>

---

## 4. `forensic browse` — the TUI graph browser  ⏱️ ~8 min
```powershell
uv run forensic browse --repo C:/Dev/scratch/hermes-agent
```
- [ ] Full-screen browser of **Symbol / File / Endpoint** nodes; the status line shows `N of M`
  (it loads a bounded snapshot — try `--max-nodes 2000`).
- [ ] Filters: name (type to filter), **c** confidence, **e** edge type, **l** language.
- [ ] **Enter** on a node → its context. **i** → impact. **f** → flow. **q** quits cleanly and
  gives your terminal back (no stuck colours, no broken echo).
- [ ] It is **read-only** — nothing it does can modify the repo or the graph.

**Does the TUI add signal over `serve --ui` and HOTPATHS.md — or is it a nicer way to see the
same thing? Would you reach for it? Notes:**
>

---

## 5. `forensic onboard` — the wizard (Q3)  ⏱️ ~10 min
First the scripted path, on a repo with **no** artifacts yet:
```bash
uv run forensic onboard --repo C:/Dev/scratch/ripgrep --yes --client claude
```
- [ ] Takes every default, asks nothing, and **works without the `[interactive]` extra**.
- [ ] Ends with a copy-pasteable MCP snippet and the **restart-and-approve** instruction.

Now the real thing — interactively, in PowerShell, on a repo you haven't extracted:
```powershell
uv run forensic onboard --repo C:/Dev/scratch/spring-petclinic
```
- [ ] Confirms the repo → runs `extract` → points you at **`AGENT_BRIEF.md` first**, then the
  other four + the graph → asks which client → prints the config → next steps.
- [ ] The printed paths and the `mcp-config` command are **copy-pasteable**: not hard-wrapped
  mid-path. **Shrink your terminal to ~40 columns and re-run** — still copy-pasteable?
- [ ] Declining the confirmation **never extracts**. Ctrl-D cancels cleanly.
- [ ] It is safe to re-run (the extract cache makes a second pass a no-op).
- [ ] The snippet it prints is **identical** to `uv run forensic mcp-config --client claude
  --repo C:/Dev/scratch/spring-petclinic`. (One renderer — verify it, don't assume.)

**Could a stranger go clone → wired-up MCP server with only this? Where did it lose you? Notes:**
>

---

## 6. `deepdive` — the session shell (Q2, the front door)  ⏱️ ~12 min
> A **new console script**. `deepdive`, not `forensic deepdive`.
```powershell
uv run deepdive --repo C:/Dev/scratch/hermes-agent
```
The grammar: a **known command word** is a command; **anything else is a question**.
- [ ] `:help` lists: `extract query trace impact flow diagram browse onboard serve`, plus
  `:cypher` / `:help` / `:quit`.
- [ ] Ask a bare question → NL query. Then `query <text>` explicitly → same thing.
- [ ] `trace <symbol>`, `impact <symbol>`, `flow <symbol>` — each runs, each returns you to the
  prompt. Then ask **another NL question**: it must still work (the store re-opens).
      *This is the DEC-102 borrow. If any of these raised a lock error, the release is broken.*
- [ ] `browse` from inside the shell → the TUI takes the screen → **q** → you land back at the
  `deepdive` prompt, working. (Not nested; the prompt had already returned.)
- [ ] `extract` from inside the shell → re-analyzes → the **next** command sees the new graph.
- [ ] `onboard` from inside the shell dispatches the wizard.
- [ ] On a repo with **no graph**, every graph-needing command says *"no graph yet — run
  `extract`"* rather than crashing. Try: `uv run deepdive --repo <some fresh clone>`.
- [ ] Ctrl-D exits; Ctrl-C cancels a line.

### 6a. The Windows console hint — verify the failure mode
In **Git Bash / MinTTY** (where `isatty()` lies):
```bash
uv run deepdive --repo C:/Dev/scratch/hermes-agent
uv run forensic repl --repo C:/Dev/scratch/hermes-agent
uv run forensic browse --repo C:/Dev/scratch/hermes-agent
```
- [ ] All three print a short, actionable hint (**use PowerShell/cmd, or prefix with `winpty`**)
  — **not** a `NoConsoleScreenBufferError` traceback.

**If a newcomer ran exactly ONE command, should it be `deepdive`? Notes:**
>

---

## 7. No internal ledger IDs in emitted output  ⏱️ ~3 min
v0.9 removed every `DEC-NNN` reference from what the tool emits. `DECISIONS.md` is local-only and
never ships, so each was a **dangling reference** for anyone reading an analyzed repo's artifacts.
```bash
grep -rn "DEC-[0-9]" C:/Dev/scratch/hermes-agent/docs/codebase/ ; echo "exit=$?"   # want: no matches
grep -rn "DEC-[0-9]" C:/Dev/scratch/hermes-agent/CLAUDE.md C:/Dev/scratch/hermes-agent/.claude/
grep -rn "DEC-[0-9]" examples/                                   # want: zero across all 11
```
- [ ] **Zero** matches in the artifacts, in `ARCHITECTURE.md`, in the skill shims, and across
  `examples/`. (`grep` exits 1 on no-match — that's the pass.)
- [ ] The provenance is still *there*, just in English ("per the call-graph resolver"). Read one
  confidence banner: does it still tell you **where the claim comes from**?
- [ ] Nothing else in the artifacts is a dangling reference — no file, doc, or ID you can't
  resolve from inside the analyzed repo.

**Notes:**
>

---

## 8. The two reporting fixes  ⏱️ ~4 min
```bash
uv run forensic extract C:/Dev/scratch/grpc-examples --force
head -20 C:/Dev/scratch/grpc-examples/docs/codebase/MAP.md
grep -rn "<module>" C:/Dev/scratch/hermes-agent/docs/codebase/
```
- [ ] **Examples-only counts:** MAP's headline reads `N (+M in graph, demoted as examples/)` —
  and the styled `extract` summary's Files row says the same. A repo with no demotions
  (`ripgrep`) prints the plain old line.
- [ ] **`<module>` display:** no literal `<module>` in HOTPATHS / AGENT_BRIEF / ARCHITECTURE —
  you see `backend.routers.whatsapp` instead. But `forensic trace <sym> --json` **still carries
  the raw qualified name** (it's the join identity — check it does).

**Both were v0.8 open findings. Are they actually closed? Notes:**
>

---

## 9. `mcp-config --dev` + `list --prune`  ⏱️ ~3 min
```bash
uv run forensic mcp-config --client claude --repo C:/Dev/scratch/hermes-agent          # uvx form
uv run forensic mcp-config --client claude --repo C:/Dev/scratch/hermes-agent --dev    # from-source
uv run forensic list
uv run forensic list --prune
```
- [ ] `--dev` prints `uv run --project <this checkout> forensic serve --repo <repo>`, and that
  checkout path really is this repo.
- [ ] `--prune` drops only entries whose graph file is **gone**, prints what it removed, and
  keeps live + graph-less entries. Bare `list` **never mutates**.

**Notes:**
>

---

## 10. Regression sweep — the things v0.9 must not have broken  ⏱️ ~10 min
- [ ] The **5 artifacts** are unchanged in structure; `AGENT_BRIEF.md` ≤ 5120 bytes
  (`wc -c`) on every repo you touched.
- [ ] `forensic serve` (MCP, stdio) still exposes its 9 tools; wire it into Claude Code with the
  §9 snippet, restart, approve — `impact` / `context` / `query` / `trace` answer as in v0.8.
- [ ] `forensic serve --ui` still opens the Sigma.js explorer.
- [ ] Pipe safety: `uv run forensic extract … | cat` → plain text, no ANSI. `NO_COLOR=1` and
  `--plain` still degrade the confidence glyphs to letters, never colour-alone.
- [ ] **Dogfood:** `uv run forensic extract C:/Dev/projects/forensic-deepdive --force` — and
  then `uv run deepdive` in it. Does Deepdive understand its own code from inside its own shell?

**Notes:**
>

---

## 11. Scale (optional, heavier — and hot)  ⏱️ ~15 min
- [ ] `uv run forensic extract C:/Dev/scratch/superset --force` (~3,800 files). Finishes in a
  couple of minutes? AGENT_BRIEF ≤ 5 KB? Cross-stack routes still ~62?
- [ ] `uv run deepdive --repo C:/Dev/scratch/superset` — is the REPL still responsive on a graph
  that size? Is `browse` still usable at `--max-nodes 2000`?

**Notes:**
>

---

## Scorecard — the decision
Rate 1 (gimmick / unusable) to 5 (genuinely valuable). Add a sentence each. Leave blank for your
own solo run; the column below is the **build-side expectation** going in, for you to confirm or
overturn.

| # | Question | 1–5 | One-sentence verdict |
|---|---|---|---|
| 1 | **Is the interactive layer worth its weight?** | | Four surfaces behind an opt-in extra; connect-once is real. Does it change how you use the tool? |
| 2 | **Is `deepdive` the front door?** | | One prompt, one repo, nine commands, NL by default — or one surface too many? |
| 3 | **Does `onboard` actually onboard?** | | Clone → wired MCP server with no docs. Where does a stranger fall off? |
| 4 | **Do the artifacts stand alone?** | | Ledger IDs gone; provenance kept as English. Any dangling reference left? |
| 5 | **Is it still honest?** | | Confidence tags, AMBIGUOUS tier, and the two reporting fixes. Anything now over-claimed? |

**Top 3 painpoints (ranked):**
> 1.
> 2.
> 3.

**Top 3 delights:**
> 1.
> 2.
> 3.

**Ship 0.9.0? (y/n) — and the one thing that must be true first:**
>

---

*This document is the instrument; your honest notes are the data. v0.9 is a completion release:
no new analysis power, a much lower floor to using it. Judge it on whether a human — not just an
agent — now has somewhere to stand.*
