# Styled command rendering — v0.7 Step 7 acceptance (DEC-079)

The final build step: the `extract` summary and a new `forensic trace` command, styled on
the DEC-078 foundation. Console-only (the presentation keystone); artifacts byte-identical;
machine/JSON output stays plain.

## `extract` / `update` — status spinner + confidence-split summary

The run is wrapped in a Rich **status spinner** (live on a TTY, silent on a pipe — no runner
change, no ANSI piped), and the summary is restyled with the **colour-coded confidence
split** over the cross-stack routes — the v0.7 headline, made visible at a glance:

```
✓ forensic extract complete  spring_react_demo
       Files  9  (typescript (5), java (4))
       Graph  9 files · 21 edges
   Artifacts  …/docs/codebase
      Routes  2 cross-stack route(s)  (● E 2  ◐ I 0  ○ A 0)
```

The split is read read-only from the freshly built graph (best-effort — a failure just omits
the line). Never colour-alone: `[E]/[I]/[A]` ASCII on a non-UTF-8/plain stream.

## `forensic trace` — the cross-stack slice, now in the terminal

`trace` existed only as an MCP tool; DEC-079 adds the **CLI command** (reusing the same
`mcp_server.server.trace` query — one source of truth). On a real graph (`spring_react_demo`):

```
frontend/src/api.ts::addUser  (downstream)
└── [POST] /api/users  via http  ● EXTRACTED
    └── → …UserController.java::UserController.createUser  ● EXTRACTED

…UserController.createUser  (upstream)
└── [POST] http::POST::/api/users  via http  ● EXTRACTED
    └── ← frontend/src/api.ts::addUser  ● EXTRACTED
```

Confidence-coloured edges, the `via <protocol>` label, `⚠ unlocated` for an endpoint with no
located handler. **Machine mode preserved:** `forensic trace … --json` (or piping) emits
**plain JSON** — `highlight=False`, **0 ANSI** even on a colour TTY:

```json
{ "matches": [...], "direction": "downstream",
  "chains": [ { "endpoint": "http::POST::/api/users", "method": "POST",
                "call_confidence": "EXTRACTED",
                "handler": "…UserController.createUser", "handles_confidence": "EXTRACTED" } ] }
```

## Presentation keystone — verified

| check | result |
|---|---|
| `trace` TTY | confidence-coloured tree (downstream + upstream) |
| `trace --json` / piped | plain JSON, **0 ANSI**, pipe-safe |
| `extract` summary | confidence split coloured (glyph) on TTY, `[E]` ASCII when plain |
| status spinner | live on TTY, silent on pipe (no control codes piped) |
| goldens | **byte-identical** (CLI stdout isn't an artifact; `emit/` untouched) |
| scope | `cli/style/render.py` + `cli/app.py` only — no `emit/*`, no machine path |

## Keystone / scope

`cli/style/render.py` (new) + `cli/style/__init__.py` (exports) + `cli/app.py` (extract/update
restyle, new `trace`, removed the old plain summary). No `emit/*` or machine-output change.
`tests/test_cli_style.py` now 12. **772 passed, 1 deselected** — the environment-flaky
`test_unwind_beats_single_row_by_at_least_5x` (an UNWIND≥5× insert-speed assertion that dips
under concurrent load; green 3/3 in isolation; untouched by Console-only work — a candidate to
soften to ≥3× / mark `perf` in a later cleanup).

## Takeaway

The publish-facing terminal surface is complete: every `extract` ends with the confidence
split, and `trace` renders the cross-stack slice as a coloured tree (or clean JSON when
piped). **Track B — and the entire v0.7 build (DEC-072→079) — is done.** What remains is the
honest usability question, which the manual-test playbook (`docs/v0.7/MANUAL_TEST.md`) is
built to answer.
