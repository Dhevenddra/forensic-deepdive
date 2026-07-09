# v0.9 → v0.10 deferred ledger (the v0.10 PRD is written from this)

What v0.9 surfaced and consciously did not fix, plus the improvement suggestions the build
and release run generated. Mirrors `../v0.8/DEFERRED.md`, which seeded v0.9.

**Frozen, do not regress:** the 5-artifact contract · the 9-MCP-tool contract · the
`Endpoint`/`base.join` keystone · AGENT_BRIEF ≤ 5 KB · no LLM in `src/`.

---

## 1. Found during the v0.9 release run (highest confidence — these are real)

1. **The test suite only ever exercises the emitter on a clean tree.** This is the root cause of
   DEC-108, not an instance of it. 909 tests passed over a bug where `--refresh-shims` could never
   refresh 5 of its 10 targets, because every test writes shims into an empty `tmp_path`. Nothing
   tested the **upgrade path**: a repo that already carries a *previous release's* output.
   **Seed:** a fixture that materializes a prior release's emitted surface (checked-in copies of
   0.8-era shims/artifacts), then re-extracts over it and asserts convergence. This class of bug —
   "fresh is fine, upgrade leaks" — is invisible to every test we currently have.

2. **The refresh summary prints bare basenames.** Two refreshed skills render as
   `Refreshed  SKILL.md, SKILL.md`. Cosmetic but genuinely confusing. **Seed:** disambiguate by
   parent dir or skill name in `cli/style/render.py`'s shim row.

3. **`--refresh-shims` is undiscoverable at the moment it is needed.** Nothing tells an upgrading
   user that their shims are stale; they must know the flag exists. **Seed:** on `extract`, detect
   Deepdive-owned shims whose content differs from what we'd write and print one line —
   *"3 generated shims are stale; re-run with `--refresh-shims`"* — without mutating anything. The
   ownership predicate for this already exists (`_is_deepdive_owned`, DEC-108).

4. **`examples/` regeneration is a manual out-of-repo script.** `C:\Dev\scratch\regen_examples.py`
   holds the eleven name→path mappings and is not version-controlled, so the release depends on a
   file that lives on one machine. Its exit code also conflates "an extract failed" with "the sweep
   found a token." **Seed:** move it into `scripts/regen_examples.py`, take the source-repo root
   from an env var, and separate the two failure modes.

---

## 2. Performance — the honest bottleneck (do not "just add threads")

5. **The serial tail dominates on large repos.** Parsing is *already* parallel
   (`ProcessPoolExecutor`, `phases.py:300`, `min(cpu_count - 1, 16)` workers). The time on omi
   (2,113 files) and superset (3,862) goes to what runs after it, in **one process**: graph
   construction, PageRank, and the LadybugDB inserts. omi burned ~374 s of CPU at ~1.15 GB RSS
   there. Threads cannot help (GIL-bound Python object churn) and processes cannot share the one
   writable handle (the store takes an exclusive lock).
   **Seed, in increasing order of ambition:**
   - **(a) Incremental extract.** Most re-extracts change a handful of files. Persist the graph and
     apply a diff rather than rebuilding. Biggest win, hardest to get right (invalidation).
   - **(b) PageRank on a sparse matrix.** The iterative fixpoint is the CPU hot spot and is a
     textbook `scipy.sparse` matvec loop. Would need a runtime dep → its own DEC.
   - **(c) Batched inserts.** Confirm whether the store writes are already batched; if not, a single
     UNWIND per node/edge kind is a cheap constant-factor win.
   Any of these needs a DEC. **v0.6 already delivered a 14.7× on superset**, so there is precedent
   that this is real, scoped work — not a threading pass.

---

## 3. Carryover (unchanged)

6. **GATE A Arm B — the autonomous end-to-end measurement.** Still hardware-gated (needs ≥16 GB GPU
   + a frontier main-agent endpoint). v0.8 shipped on assisted-analysis value with **no autonomous
   overclaim**; v0.9 changes nothing about that framing and makes no new claim. The Arm-A pilot
   stands: the static seed is a *weak* prior (F1 0.108, recall@10 ≈ 0.44, n=8).
   **This remains the one thing that would let the project claim autonomous usefulness. Until it
   runs, do not.**

7. **Protocol carryover (DEC-106, demand-gated).** Unbuilt by design. Build it when a real repo
   demands it, not speculatively.

8. **`serve --ui` node labels still render raw qualified names.** DEC-104 fixed the four markdown +
   trace surfaces; the web UI was consciously out of scope (its side panel shows full paths, which
   is self-explanatory). Revisit only if a finding names it.

---

## 4. Suggestions — not yet decided, argued both ways

9. **The interactive surfaces have no automated coverage of the thing that breaks them.** `repl`,
   `browse`, `onboard` and `deepdive` are tested at the function level, but the two real bugs of the
   arc (the `NoConsoleScreenBufferError` under Git Bash; the bulk-regex `return` that no-opped every
   query) were both found by *running the CLI*, not by tests. A pseudo-terminal harness (`pexpect` /
   `pywinpty`) could drive a real prompt.
   **Against:** it adds a heavy, platform-specific dev dep to catch a class of bug that a five-minute
   manual pass already catches. **For:** that five-minute pass is exactly what gets skipped when the
   machine is hot at 2 a.m. Undecided; leaning *for*, scoped to `deepdive`'s grammar only.

10. **`MANUAL_TEST.md` is written fresh each release, from the previous one's shape.** It has drifted
    into a checklist of *what changed* rather than a stable instrument. Two releases' scores are not
    comparable. **Seed:** split it — a stable core (the five questions, unchanged across releases,
    scored 1–5) plus a per-release delta section. Only then does the scorecard become a time series.

11. **Nothing enforces the `examples/` ↔ findings coupling.** `CLAUDE.md` says they are updated
    together; nothing checks it. **Seed:** a test that fails when `examples/*/AGENT_BRIEF.md`'s footer
    version differs from `pyproject.toml`'s. That single assertion would have caught the two stale
    directories at the start of this pre-release rather than in the middle of it.

12. **The DEC ledger is load-bearing and unshipped.** `DECISIONS.md` is gitignored (by choice), which
    is exactly why DEC-107 and DEC-108 exist — emitted output kept citing it. The rule now is "no
    ledger IDs in emitted output," enforced by a sweep. **Consider:** whether the *reasoning* in
    those entries deserves a public home (an `ARCHITECTURE_DECISIONS.md` digest, no numbers), since
    outside contributors currently cannot see why any invariant exists. **Against:** it is an
    internal working log and would rot. Genuinely unresolved.

---

## 5. Non-goals (do not regress)

- No sixth artifact. No tenth MCP tool. No `protocol ==` branch in the surfacing layer.
- No LLM at runtime in `src/`. The tool is pure-static; `[semantic]` is an optional retriever.
- No autonomous-usefulness claim until GATE A Arm B runs.
- No GUI arc until the interactive CLI has been used in anger and the MANUAL_TEST solo run is done.
