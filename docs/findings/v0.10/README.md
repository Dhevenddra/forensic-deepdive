# v0.10 findings — "The Upgrade Path"

Per the convention in [`../README.md`](../README.md): one folder per release, narrative documents
capturing what we learn when the tool meets real code (and, here, when it meets a stopwatch).

## Documents

- [`PROFILE.md`](PROFILE.md) — **DEC-113**: per-phase profile of the serial post-parse tail on
  Superset and Omi. The measurement that cancelled DEC-114. `store_write` is 79–87 % of a large
  extract; PageRank is 0.04 %. The v0.9 ledger's perf hypothesis was wrong, and so was the KICKOFF's
  correction to it.

## Real-repo runs

Track A (upgrade integrity) is verified by the suite rather than by a repo run: the DEC-110 fixture
*is* a prior release's output, checked in. The v0.9 lesson that produced it — always run findings
against a repo carrying a **previous** release's output — is now a test
(`tests/test_upgrade_path.py`) instead of a habit that has to be remembered.

Per-repo narrative docs land here at pre-release, alongside the `examples/` regeneration.
