# Omi — v0.3 real-repo test (the headline re-run)

Re-run of the v0.1/v0.2 reference repo under the full v0.3 stack. Omi is the
largest, most polyglot repo in the set and the one the perf work (Items A+B)
and method resolution (Item C) were built for. Compare against
`docs/findings/v0.1/omi-test.md`, `examples/omi/`, and the v0.2 acceptance
numbers (PROGRESS 2026-05-25, item 14a).

## Run summary

| | |
|---|---|
| Date | 2026-05-30 |
| Repo | [BasedHardware/omi](https://github.com/BasedHardware/omi) (15,647 commits in window) |
| Tool version | v0.3 HEAD (`8ad4110`) |
| OS | Windows 11 |

### Timings — the Item A+B perf win

| Run | v0.2 | **v0.3** |
|---|---|---|
| cold `extract --force` | 930 s | **406.6 s** |
| warm re-extract (cache hit) | 2.2 s | **1.05 s** |

**Cold extract dropped from 930 s → 407 s (−56%)** on the same repo — the
parse cache (DEC-036) + `ProcessPoolExecutor` parallel parse (DEC-035) paying
off at 2,149-file scale. Comfortably **materially below 930 s with headroom
under the 1200 s budget** (gate check #2). Warm re-extract is **1.05 s**
(single-digit seconds ✓).

### Inventory & graph

- **2,149** files · LANGS: dart 555, python 464, **tsx 378**, swift 315,
  typescript 224, c 103, javascript 63, **rust 46**, java 1.
- **34,450** Symbols · 2,044 Modules · 15,647 Commits · 215 Authors.
- Edges: **34,896 CALLS** · 22,863 MEMBER_OF · 11,485 IMPORTS · 215 EXTENDS ·
  49 IMPLEMENTS · **77,870 CO_CHANGES_WITH**.
- **AGENT_BRIEF 1,555 B** (≤5120 ✓).

> **Item D cross-reference:** the v0.1 findings noted *"Rust 46 — invisible to
> the static layer."* In v0.3 those **46 Rust files are now parsed** (Item D /
> DEC-040) and contribute to the symbol graph. The static layer went from 8
> languages to 9 on this exact repo.

## The before/after AMBIGUOUS metric (gate check #3)

DEC-037 left the **bare-name resolver (DEC-025) unchanged** — so in the v0.3
graph, the `via='bare'` CALLS edges *are* exactly the v0.2 graph. This lets us
read the true before/after off the v0.3 graph alone (no v0.2.0 re-run needed),
by decomposing CALLS by `(via, confidence)`:

| via | EXTRACTED | INFERRED | AMBIGUOUS | total |
|---|---|---|---|---|
| `bare` (= v0.2 graph) | 16,251 | 11,746 | **5,163** | 33,160 |
| `module` (Item C) | — | 576 | — | 576 |
| `self` (Item C) | — | 677 | — | 677 |
| `static` (Item C) | — | 110 | 322 | 432 |
| `this` (Item C) | — | 51 | — | 51 |

**Reading:**
- **v0.2 Omi:** 33,160 CALLS, **5,163 AMBIGUOUS (15.6 %)** — all bare-name;
  every dotted/method call was *dropped* (`_drop_method`).
- **v0.3 Omi:** 34,896 CALLS, 5,485 AMBIGUOUS (15.7 %).
- **Item C recovered 1,736 method/module calls v0.2 dropped entirely** —
  **1,414 (81 %) precise INFERRED**, only **322 (19 %) bounded AMBIGUOUS**
  (cross-file `static` calls with 2+ candidate owner types).

The headline is **not** "AMBIGUOUS went down" — it's that method-call recovery
landed **without inflating the AMBIGUOUS ratio** (15.6 % → 15.7 %). DEC-037's
deliberate choice to *drop* unresolved dotted calls rather than emit
one-AMBIGUOUS-per-same-named-method is exactly what avoids the flood the v0.1
run warned about (e.g. `ChatToolResponse`'s 449-candidate collision). The
resolvable majority — `self.`/`this.` receivers, which dominate OO code —
became precise INFERRED edges that simply **did not exist** in v0.2.

## ✅ What worked

1. **Hybrid NL query is the PRD §4.5 acceptance, met on real polyglot code.**
   `"websocket reconnection audio transcript"` (pure-static, offline,
   `degraded=True`) returns the right implementation symbols **across three
   languages**, ranked above the noise:
   - `DeviceProvider.attemptReconnection` / `.startReconnectionTimer` /
     `.stopReconnectionTimer` (Swift)
   - `CaptureProvider._initiateWebsocket` (Dart)
   - `pusher.py::websocket_endpoint_trigger` / `_websocket_util_trigger` (Python)

   This is the literal §4.5 acceptance example ("where do we handle websocket
   reconnection") returning the implementation, offline, with provenance — and
   it spans the Swift desktop client, the Dart app, and the Python backend.
2. **Mermaid `classDiagram` for `Logger`** (the v0.1 #1-central symbol) renders
   bounded with its 6 methods (`debug/error/handle/info/log/warning`).
3. **Co-change at scale** — 77,870 CO_CHANGES_WITH edges; the l10n localization
   cluster the v0.2 run caught is still there.
4. **407 s cold on 2,149 files / 9 languages / 15.6k commits**, graph DB 42 MB.

## Notes / honest failures

- **AGENT_BRIEF held at 1,555 B** across a 34k-symbol graph — the ≤5 KB cap is
  nowhere near threatened at real scale.
- The websocket query hits are all **INFERRED** (multi-word NL query, no single
  exact-identifier match) and lexical-only for several — the **semantic tier
  would lift recall here** (a paraphrase like "reconnect the device socket"
  would benefit), but it's opt-in/offline and not provisioned in this run, so
  the response honestly reports `degraded=True`. This is the pure-static floor
  working as designed.
- 5,485 total AMBIGUOUS is still a real number — but it's overwhelmingly
  bare-name cross-file collision on common Dart/TS names (the v0.2 behavior,
  unchanged), not method-resolution noise. Field-type / dataflow inference to
  resolve more of these is the v0.4 stack-graphs work.
