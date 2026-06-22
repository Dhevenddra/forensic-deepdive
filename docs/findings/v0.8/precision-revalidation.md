# v0.8 precision re-validation on real repos (DEC-083 → DEC-094)

Track B shipped its precision work golden-neutral on `tiny_fixture` (no git, no graph). This
document is the proof those changes do the right thing on **real** code. Evidence repos are the
`C:\Dev\scratch` set; see [`README.md`](README.md) for the full result table.

## DEC-083 — AMBIGUOUS route/impact tier is *precise*, not a blanket

The change: the CALLS resolver's cross-file same-name fallback is always `AMBIGUOUS` (never
`INFERRED`-when-unique), so a bare-name coincidence stays out of the precise default set but
recoverable at the AMBIGUOUS floor. The risk was that everything would collapse to AMBIGUOUS.
Real data says no — the tier tracks genuine ambiguity:

- **superset**: 62 routes, **0 AMBIGUOUS** (54 EXTRACTED / 8 INFERRED). Routes resolve to a
  unique handler ⇒ no ambiguity surfaced. This is the flagship and the precision is clean.
- **fastapi**: 14 of 15 routes AMBIGUOUS — and *correctly so*. `GET /docs` maps to **both**
  `docs_src/custom_docs_ui/tutorial001_py310.py::custom_swagger_ui_html` **and**
  `tutorial002_py310.py::custom_swagger_ui_html`: the docs tutorials each redefine the same
  path, so there are genuinely several candidate handlers. DEC-083 surfaces **all** of them
  rather than picking one — exactly the design.
- **grpc-examples**: 68 AMBIGUOUS / 94 — many tutorials reuse `Greeter/SayHello` across
  directories; the 26 EXTRACTED are the uniquely-resolved client→server pairs.

Verdict: **holds**. AMBIGUOUS fires on real ambiguity (duplicate example paths), stays absent
where resolution is unique (superset). No false collapse.

## DEC-085 — HOTPATHS "Callers" = distinct callers, not edge count

The change: the "Callers" column counts `count(DISTINCT caller)`; the confidence mix stays
edge-based (a callee can have more edges than distinct callers). The v0.7 complaint was the
"383 inbound vs 271 grep" inflation. Real data shows the two numbers now diverge honestly:

| Symbol (superset) | Distinct callers | Confidence mix (edges) |
|---|---|---|
| `t` (translation singleton) | **237** | **1381 AMBIGUOUS** |
| `useTheme` | 191 | 203 AMBIGUOUS |
| `transaction` | 96 | 98 EXTRACTED |
| `ensureIsArray` | 70 | 142 AMBIGUOUS |

`t` is called from 237 distinct symbols over 1381 call edges — the column now says **237**, not
1381. The note states the definition and that the mix remains edge-based. Verdict: **holds**.

## DEC-090 — ARCHITECTURE.md: three honest modes observed

The new cross-boundary surface (a regenerated human-validation view, **not** a 6th artifact)
behaves correctly across the spectrum of real repos:

1. **Cross-stack routes** — `spring_react_demo`: 4 ROUTES_TO edges, rendered as 2 solid
   (EXTRACTED) + 2 dashed (INFERRED), matching the extract summary's `[E] 2 [I] 2`.
2. **DI / ORM cross-boundary** — `spring-petclinic`: **0 HTTP routes** but the diagram still
   has content — `injects` edges (Controller→Repository) and `persists` edges (model→table).
   "0 routes" is not "no architecture"; the DI/ORM boundary is real and shown.
3. **Honest degrade** — `ripgrep` (pure Rust CLI): *"No cross-boundary architecture detected …
   this repository's structure is intra-process."* No fabricated diagram.

Verdict: **holds**. The three modes are the honest spectrum we wanted.

## DEC-094 — `--emit-vault`

`forensic extract … --emit-vault` on `spring_react_demo` wrote a complete Obsidian vault under
`docs/codebase/vault/`: all six rendered surfaces (the 5 artifacts + ARCHITECTURE.md) plus an
`INDEX.md` MOC, with `.obsidian/` config. Flag-off remains byte-identical (golden-guarded).
Verdict: **holds**.

## DEC-084 — NL query() name-match

The lexical name-substring tier + de-inflection lives in the **MCP `query` tool** (the CLI
`query` is substring-grep over artifacts, a different path). Re-validated live this session by
calling `hybrid_query` against fastapi's graph: query **"encode"** now returns `jsonable_encoder`,
`decimal_encoder`, and `generate_encoders_by_class_tuples` — the name-substring tier finds symbols
whose *name* carries the stem, which is the exact v0.7 miss (the old BM25-only path returned none).
The degraded-mode note ("semantic tier not installed — lexical + structural only") is present.
Noted so a reader doesn't mistake the CLI grep for the ranked NL path.

## AGENT_BRIEF ≤ 5 KB hard cap (sacred invariant)

Held on every repo, with margin — largest was `spring-petclinic` at 1870 b against the 5120 cap
(2113-file `omi` = 1731 b). No DEEP overflow needed on any real repo in the set.

## Residual findings (→ v0.9 / DEFERRED)

- **`<module>` qualified-name placeholder.** Module-level call sites and some handlers render
  as `…/image01.py::<module>` / `backend <module>` in routes and AGENT_BRIEF rules (seen in
  fastapi consumers and the hermes-agent cross-stack rule). The join is correct; the *display
  name* of a module-scope symbol degrades to `<module>`. Cosmetic/clarity, not a wrong edge.
- **Examples-only repos under-count "source files."** DEC-049 demotion (correct for libraries)
  makes `grpc-examples` report "3 source files" while the graph is 117 files / 94 routes. The
  fix is reporting-side. See [`grpc-examples-test.md`](grpc-examples-test.md).
