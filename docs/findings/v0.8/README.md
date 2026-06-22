# v0.8 findings — "USABLE → USEFUL" precision re-validation on real repos

Per-repo results from running `forensic extract` (0.8.0) over the `C:\Dev\scratch`
acceptance set, plus a focused re-validation of every v0.8 precision/feature change
(DEC-083 → DEC-094) against **real** code rather than `tiny_fixture`. Convention per
[`../README.md`](../README.md): one folder per release, narrative findings, evidence
mirrored under `examples/<repo>/`.

## Headline verdict

The v0.8 precision work holds up on real data. The single most important result is that
the **AMBIGUOUS route tier (DEC-083) is *precise*, not a blanket**: it fires exactly where
the data is genuinely ambiguous and stays silent where routes resolve cleanly.

| Repo | Stack | Src files | Graph | Routes (E / I / A) | Note |
|---|---|---|---|---|---|
| **superset** | TS + Python | 3862 | 3276 f / 10215 e | **62 (54 / 8 / 0)** | flagship — clean precision, **0 AMBIGUOUS** |
| **fastapi** | Python | 75 | 415 f / 1006 e | 15 (0 / 1 / 14) | AMBIGUOUS *correctly* dominates (duplicate example-app paths) |
| **grpc-examples** | polyglot | 3¹ | 117 f / 22 e | 94 (26 / 0 / 68) | gRPC client→server pairs matched EXTRACTED |
| **rabbitmq-tutorials** | 7 langs | 204 | 174 f / 22 e | 8 (1 / 3 / 4) | messaging (AMQP topic) |
| **hermes-agent** | Python + TS | 1340 | 1256 f / 7895 e | 36 (0 / 1 / 35) | owner repo; low-history Never-suppression (DEC-086) |
| **spring_react_demo** | Java + React | 4 | 4 f / 0 e | 4 (2 / 2 / 0) | clean cross-stack; ARCHITECTURE = 2 solid + 2 dashed |
| **spring-petclinic** | Java | 30 | 25 f / 5 e | 0 HTTP | DI + ORM cross-boundary surfaced in ARCHITECTURE |
| **ripgrep** | Rust | 81 | 75 f / 96 e | 0 | ARCHITECTURE degrades honestly (intra-process) |
| **omi** | 9 langs | 2113 | 2048 f / 18276 e | 3 (0 / 3 / 0) | largest polyglot (dart/py/tsx/swift/ts/c/js/rust/java); AGENT_BRIEF 1731 b |

¹ DEC-049 demotes `examples/`-segment files to `ROLE_EXAMPLE` (in-graph, not counted as
"source"). On an *examples-only* repo this nukes the headline count to 3 while the graph
(117 files) and 94 routes are real — see [`grpc-examples-test.md`](grpc-examples-test.md).
This is the one reporting-clarity gap the run surfaced.

## What was re-validated (DEC-by-DEC, on real data)

See [`precision-revalidation.md`](precision-revalidation.md) for the evidence per change:

- **DEC-083 impact()/route AMBIGUOUS tier** — precise: superset A0, fastapi A14, grpc A68.
- **DEC-084 NL query() name-match** — validated live over the MCP server (Item 2 walkthrough).
- **DEC-085 HOTPATHS distinct-caller counts** — the "distinct callers" definition + note present.
- **DEC-090 ARCHITECTURE.md** — three honest modes observed: routes (spring_react_demo),
  DI/ORM (spring-petclinic), and clean degrade (ripgrep "No cross-boundary architecture detected").
- **DEC-094 `--emit-vault`** — full 6-file Obsidian vault + INDEX MOC on spring_react_demo.

## Open findings (fed to v0.9 / DEFERRED)

1. **Examples-only repos read as "3 source files"** (grpc-examples) — DEC-049 demotion is
   correct for libraries but the headline is confusing when `examples/` *is* the repo. Fix
   is reporting-side (show graph count / "(N demoted)"), not a re-classification.
2. **`<module>` handler placeholder** on some cross-stack rules (hermes-agent AGENT_BRIEF) —
   the consumer→endpoint join resolved but the handler symbol name degraded to `<module>`.
