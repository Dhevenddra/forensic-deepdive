# Findings — real-repo testing

Per-version findings from running `forensic extract` against real external
codebases. Internal regression and golden-file tests live under
`tests/` — these documents capture what we learn when the tool meets code
it wasn't tuned for.

## Convention (codified 2026-05-25)

- **One folder per release version**: `docs/findings/v<X.Y>/`.
- **One file per repo**: `<repo>-test.md` (e.g. `omi-test.md`).
- **Findings docs are narrative** — what worked, what surprised us,
  what's deferred to a later version. Numbered findings (e.g. "9
  findings from the Omi v0.1 run") map to v-next scope items.
- **Example artifacts** for the same repo live under `examples/<repo>/`
  (the 5 markdown files `forensic extract` writes). The findings doc
  is the *commentary*; `examples/<repo>/` is the *evidence*. Updated
  together.
- Old version folders stay untouched — `v0.1/` is the v0.1 snapshot
  forever, even after v0.2 ships. Use git history if you need the
  exact tool version that produced them.

## Index

- [`v0.1/`](v0.1/) — v0.1.0 findings (Omi: 9 findings → fed v0.2 scope)
- `v0.2/` — created during the v0.2.0 acceptance session (item 14a)
- [`v0.3/`](v0.3/) — v0.3 "Precision & Speed" acceptance (Item G). Repo set
  (PRD §4.7, after the DEC-034 re-sequence): **Apache Superset** (primary
  polyglot stress) + **a Rust repo** (ripgrep, Item D) + re-runs of **Omi**
  and **spring-petclinic** (regression + before/after AMBIGUOUS metric) +
  the **fastapi** and **gitnexus** carryover (the §5.4 v0.2 debt). Backstage
  and Odoo were **deferred** — cross-stack is v0.4, Odoo is a v1.0 scale test
  ([[stress-test-repos]] / DEC-034). See [`v0.3/README.md`](v0.3/README.md).
- [`v0.4/`](v0.4/) — v0.4 "Cross-Stack & Visual" acceptance (Item L). Repo set
  (PRD §4.9): **Apache Superset** (flagship — cross-stack + scale + the 348k
  `serve --ui` LOD proof) + purpose-built **spring-react-demo** & **openapi-shop**
  (clean cross-language ROUTES_TO + the committed-spec codegen shortcut) + re-runs
  of **gitnexus** (TS-heritage 2→21) and **fastapi** (the `example` role). **8/9
  gate items green**; the honest shortfall — 0 ROUTES_TO on Superset (its
  `SupersetClient` + Flask-AppBuilder abstractions) — defines the v0.5 head-of-line.
  See [`v0.4/README.md`](v0.4/README.md).
- [`v0.5/`](v0.5/) — v0.5 "Cross-Boundary Protocols" acceptance. **Five protocols on
  one `Endpoint` spine** (HTTP, MCP, registry-dispatch, gRPC, messaging) + the DI/ORM
  tail. **Superset** (the v0.4 head-of-line, now **closed: 0 → 61 cross-stack
  `ROUTES_TO`** + 210 `PERSISTS_TO`) + **hermes-agent** (the headline — 22 MCP tools +
  35 registry-dispatch `ROUTES_TO`, vs 1 in v0.4) + **spring-petclinic** (DI/ORM tail)
  + **grpc/rabbitmq/nest/jersey** (Steps 5–6). See [`v0.5/README.md`](v0.5/README.md).
- [`v0.6/`](v0.6/) — v0.6 "Findings-Driven Refinements": hardened the 5-protocol Endpoint
  abstraction against the v0.5 findings + Django (wagtail 0→125 Endpoints) + JAX-RS (jersey)
  + AMQP (rabbitmq) + a 14.7× Superset extract speedup.
- [`v0.7/`](v0.7/) — v0.7 "Coverage Completion + CLI Style": Django/JAX-RS/AMQP completion,
  the styled CLI foundation, the usability gate (Iris-Nearby agent-onboarding + live MCP),
  and the [`DEFERRED.md`](v0.7/DEFERRED.md) ledger that seeded v0.8.
- [`v0.8/`](v0.8/) — v0.8 "USABLE → USEFUL" precision re-validation. The DEC-083→094 changes
  proven on real data: AMBIGUOUS route tier is precise (superset A0 vs fastapi A14), distinct
  caller counts, ARCHITECTURE.md (3 honest modes), `--emit-vault`. Repo set: **superset**
  (flagship), **fastapi**, **grpc-examples**, **rabbitmq-tutorials**, **hermes-agent**,
  **spring_react_demo**, **spring-petclinic**, **ripgrep**, **omi** (9-language breadth).
  See [`v0.8/README.md`](v0.8/README.md).
- [`v0.9/`](v0.9/) — v0.9 "The Interactive CLI". A completion release, so the run is built around
  a **negative** claim (nothing moved: superset 62 routes 54/8/0, hermes 36 routes 0/1/35, both
  identical to v0.8) plus one explicit check: **no internal `DEC-NNN` ledger ID in anything the
  tool emits**. That check *failed on first run* — `--refresh-shims` could never refresh the five
  emitted skills (**DEC-108**, fixed before the tag). Both v0.8 open findings closed. Repo set:
  **superset** (flagship), **hermes-agent** (owner's repo, and an 0.8 → 0.9 upgrade).
  See [`v0.9/README.md`](v0.9/README.md).
