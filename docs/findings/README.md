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
- `v0.3/` — Apache Superset / Backstage / Odoo + re-runs of v0.2's
  set (Omi, spring-petclinic, GitNexus, fastapi) under the v0.3
  framework resolvers + parse threading.
