# v0.10 — profiling the serial post-parse tail (DEC-113)

**The deliverable DEC-113 demanded: numbers before patches.** They contradict the plan those
patches were written for.

Measured with `forensic extract --timings`, the always-on per-phase instrumentation added in
DEC-113. One run per repo, `--force` (no cache), artifacts to a temp dir.

---

## 1. The numbers

### Apache Superset — 3,862 source files, 3,276 in graph, 10,215 file-level edges

| Phase | Seconds | Share |
|---|---:|---:|
| **build_graph** | **342.33** | **82.5 %** |
|   ├ `store_write` | 328.03 | 79.0 % |
|   ├ `resolve_calls` | 3.78 | 0.9 % |
|   ├ `lexical_index` | 1.04 | 0.3 % |
|   └ other | 9.48 | 2.3 % |
| contracts | 43.18 | 10.4 % |
| history | 11.17 | 2.7 % |
| parse | 7.16 | 1.7 % |
| inventory | 6.12 | 1.5 % |
| emit | 4.65 | 1.1 % |
| **static** | **0.50** | **0.1 %** |
|   ├ `build_symbol_graph` | 0.34 | 0.08 % |
|   └ `pagerank` | **0.16** | **0.04 %** |
| flatten | 0.00 | 0.0 % |
| **Total** | **415.1** | |

### Omi — 2,113 source files, 2,048 in graph, 18,276 file-level edges, 9 languages

| Phase | Seconds | Share |
|---|---:|---:|
| **build_graph** | **550.23** | **93.1 %** |
|   ├ `store_write` | 513.88 | 86.9 % |
|   ├ `resolve_calls` | 28.59 | 4.8 % |
|   ├ `lexical_index` | 2.24 | 0.4 % |
|   └ other | 5.52 | 0.9 % |
| contracts | 19.17 | 3.2 % |
| parse | 10.64 | 1.8 % |
| emit | 3.82 | 0.6 % |
| history | 3.39 | 0.6 % |
| inventory | 2.37 | 0.4 % |
| **static** | **1.46** | **0.2 %** |
|   ├ `build_symbol_graph` | 1.18 | 0.2 % |
|   └ `pagerank` | **0.28** | **0.05 %** |
| flatten | 0.00 | 0.0 % |
| **Total** | **591.1** | |

---

## 2. What this overturns

### 2.1 PageRank is not the bottleneck. It is a rounding error.

**0.16 s on superset. 0.28 s on omi.** Four to five hundredths of one percent.

The v0.9 DEFERRED ledger (§2) named the tail as "graph construction, PageRank, and the LadybugDB
inserts" and ranked its seeds by ambition: (a) incremental extract, (b) **PageRank on a sparse
matrix**, (c) batched inserts. The v0.10 KICKOFF inherited that, made PageRank the headline
optimization (DEC-114), and flagged that a `scipy` dependency would reopen DEC-011.

A sparse-matrix rewrite of the power iteration would save **0.16 seconds on a 415-second run**, at
the cost of a runtime dependency the project rejected once on purpose. **DEC-114 as written is
cancelled.** Not deferred — disproven.

### 2.2 The insert seed was struck for the wrong reason, and it is the whole cost.

DEFERRED §5(c) asked: *"Confirm whether the store writes are already batched; if not, a single
UNWIND per node/edge kind is a cheap constant-factor win."*

That question was answered **yes** while writing the v0.10 KICKOFF (DEC-032: one `UNWIND $rows`
Cypher call per node/edge kind, chunked at `_BATCH_SIZE`, `ladybug_store.py:603`), the seed was
struck, and KICKOFF §4 told future readers not to re-litigate it.

**`store_write` is 79 % of superset's run and 87 % of omi's.** Being batched did not make it fast.
The question was the wrong question: it asked whether a known technique had been applied, and
nobody had ever measured whether the result was quick. "Already optimized" was mistaken for
"not the problem."

### 2.3 Parse — the one phase that got parallelized — is under 2 %.

`ProcessPoolExecutor`, `min(cpu-1, 16)` workers (`phases.py:300`). **7.16 s (1.7 %) on superset,
10.64 s (1.8 %) on omi.** The parallel parse is real and works; it is also no longer where any time
goes. The ledger's framing — "parsing is *already* parallel, the time goes to what runs after it" —
was directionally right and is worth keeping in mind before anyone proposes more parse workers.

### 2.4 `contracts` is the unremarked #2.

**43.18 s (10.4 %) on superset**, never mentioned in any ledger or roadmap. Ten times PageRank,
`build_symbol_graph`, `resolve_calls` and `lexical_index` *combined*. Not a target yet — but it is
the second thing to look at, and nobody knew it existed.

### 2.5 Cost tracks the graph, not the file count.

Omi has **46 % fewer files** than superset but **79 % more** file-level edges, and a **57 % longer**
`store_write`. `resolve_calls` shows it harder: 28.59 s on omi against 3.78 s on superset — 7.6×,
on a smaller repo, driven by 9 languages' worth of references rather than file count. Any scaling
claim in the README should be phrased against graph size, not repo size.

---

## 3. What was NOT measured (do not over-read this)

- **One run per repo, no repetition.** No variance estimate. The 79 %/87 % split is far too large to
  be noise, but a 5 % change in a follow-up is not evidence of anything yet.
- **Wall clock, not CPU time.** The v0.9 ledger's "~374 s of CPU" on omi is a different metric from
  this 591 s wall; they are not directly comparable.
- **No RSS.** The ledger's ~1.15 GB observation is unverified here. Peak memory needs its own
  instrument (`psutil` is not a dependency).
- **One machine, Windows, thermal state unknown.** Linux/macOS may weight differently — LadybugDB's
  exclusive lock is already known to be Windows-only behavior (DEC-102 correction).
- **`store_write` is not broken down by node/edge kind.** This is the single most important gap:
  328 s and 514 s are attributed to *one* sub-step covering ~22 `add_many_*` calls. **Optimizing it
  blind would repeat exactly the mistake this document exists to correct.**

---

## 4. What follows (feeds the DEC-114 rewrite)

1. **Break `store_write` down per `add_many_*` call** before touching it. Same discipline, one level
   deeper: the instrument already supports it (`ctx.substep` accumulates by name).
2. **Then** optimize what that names. Candidate hypotheses, none yet evidenced: `_BATCH_SIZE` is
   tuned for the wrong shape; per-call query re-preparation; index maintenance during bulk insert;
   `MATCH`-then-`CREATE` edge patterns doing a lookup per row.
3. **Incremental extract (DEC-115) is now the strongest remaining idea**, precisely because the cost
   is concentrated in writes. If most re-extracts change a handful of files, not rewriting 500 s of
   store is the largest available win — but invalidation correctness is unchanged in difficulty and
   it still must not land before (1) and (2).
4. **Leave PageRank alone.** DEC-011's pure-Python power iteration is fine, and now has measurements
   to say so rather than an assumption in either direction.

---

*The point of the gate held. Skipping the profile and "just optimizing PageRank" would have cost a
session, possibly a runtime dependency, and delivered a 0.04 % improvement.*
