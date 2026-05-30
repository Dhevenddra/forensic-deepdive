# spring-petclinic — v0.3 real-repo test

Regression re-run of the v0.2 reference Java repo under the v0.3 stack
(parse cache + parallel parse + receiver-type method resolution + hybrid
query + Mermaid). Compare against `examples/spring-petclinic/` and the v0.2
acceptance numbers (PROGRESS 2026-05-25, item 14a).

## Run summary

| | |
|---|---|
| Date | 2026-05-30 |
| Repo | [spring-projects/spring-petclinic](https://github.com/spring-projects/spring-petclinic) (`C:/Dev/scratch`, 941 commits in window) |
| Tool version | `forensic-deepdive 0.2.0` + v0.3 items A–F (HEAD `8ad4110`) |
| OS | Windows 11 |

### Timings

| Run | Time |
|---|---|
| cold `extract --force` | **2.2 s** |
| warm re-extract (cache hit) | **0.03 s** |

v0.2 measured 125 s cold (dominated by the git pass over 1.5k commits); the
v0.3 run is on a 941-commit window and the parse cache + parallel-parse path,
so the headline is the **0.03 s cache-hit** — comfortably inside the §4.7
"single-digit seconds" warm budget.

### Inventory & graph

- **30** Java files · **143** Symbols · 86 Modules · 941 Commits · 149 Authors.
- Edges: **24 CALLS** · 88 MEMBER_OF · 179 IMPORTS · 8 EXTENDS · 0 IMPLEMENTS · 318 CO_CHANGES_WITH.
- **AGENT_BRIEF 1854 B** (≤5120 ✓).

### CALLS by confidence (the Item-C metric)

| confidence | count |
|---|---|
| EXTRACTED | 16 |
| INFERRED | 8 |
| **AMBIGUOUS** | **0** |

By `via`: 23 `bare` + 1 `this`. Item C recovered one `this.`-receiver method
call (`bare` covers the DEC-025 same-file/import-resolved calls). petclinic is
a small, clean MVC app — there is almost no dotted-call surface to recover and
**zero** AMBIGUOUS noise, which is the honest outcome: the resolver doesn't
manufacture edges where there's nothing to resolve.

## ✅ What worked

1. **Hybrid NL query** — `"owner repository pet"` (pure-static, offline,
   `degraded=True`) ranks the domain models first, exact-name matches tagged
   EXTRACTED, ranked matches INFERRED:
   - `Owner` / `Pet` — **EXTRACTED** (`[lexical, structural]`)
   - `Owner.getPets` / `Owner.getPet` / `Owner.addPet` — INFERRED
2. **Mermaid classDiagram** auto-picked for `OwnerController` (a class),
   rendering all 12 handler methods in a bounded, paste-ready block.
3. **Co-change** still catches the canonical Spring MVC triangle
   (Owner/Pet/Visit controllers) — 318 CO_CHANGES_WITH edges over the window.
4. Byte-identical to the v0.2 structural output where comparable; the v0.3
   additions (method `via`, lexical index, Mermaid) are purely additive.

## Notes / honest failures

- **0 AMBIGUOUS** is a feature here, not a gap — Java's typed call sites that
  *do* resolve become EXTRACTED via DEC-023 qualified names; the rest are
  external (Spring framework) and correctly dropped rather than guessed.
- Annotation/route resolution (`@GetMapping` ↔ controller) is **v0.4** (the
  cross-stack wedge), not v0.3 — petclinic is staged for that re-run.
