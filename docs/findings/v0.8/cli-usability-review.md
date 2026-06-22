# CLI usability review — v0.8

The CLI grew from a banner (v0.6) to a functional surface (v0.7/v0.8). This is an end-to-end
exercise of every command at 0.8.0, with rough edges noted and the worthwhile ones fixed in
this session.

## Exercised (all pass)

| Command | Check | Result |
|---|---|---|
| `info` / `info \| cat` | banner + capability panel; pipe degrade | ✓ clean `[E]/[I]/[A]` on pipe |
| `extract --force` | summary + 5 artifacts + Diagram line | ✓ |
| `extract --emit-vault` | Obsidian vault under `docs/codebase/vault/` | ✓ 6 files + INDEX MOC |
| `extract --refresh-shims` | rewrite stale fingerprinted shims | ✓ (write-if-absent honored) |
| `diagram --repo` | standalone ARCHITECTURE.md regen | ✓ "ARCHITECTURE.md written to …" |
| `mcp-config --client claude` | stdout JSON snippet | ✓ valid `mcpServers` (see note 2) |
| `query --artifacts-dir` | substring grep over artifacts | ✓ match w/ file:line context |
| `trace` (down / `--upstream` / `--json`) | cross-stack slice | ✓ tree + plain JSON |
| `graph --central` / target | bounded Mermaid | ✓ (empty case fixed — note 1) |
| `list` | multi-repo registry | ✓ (clutter — note 3) |
| `--plain info` / `NO_COLOR` | confidence visible colour-off | ✓ `[E] EXTRACTED …` |
| `serve --repo` / `--ui` | MCP stdio / Sigma.js | ✓ `--repo` accepted (v0.7 fix holds) |
| `insights --help` | push / record / recall | ✓ explicit-only push |

## Rough edges

### 1. `graph --central` on a 0-edge repo emitted a hollow diagram — FIXED

`forensic graph --repo <0-edge-repo> --central` printed an empty ` ```mermaid flowchart LR``` `
block (zero nodes) — useless to paste and inconsistent with the honest-degradation everything
else does. **Fixed this session**: it now prints a note ("No graph to draw — no nodes matched …
See MAP.md / HOTPATHS.md") and no hollow block, mirroring ARCHITECTURE.md's degrade. Guarded by
`tests/test_cli.py::test_cli_graph_empty_degrades_honestly`.

### 2. `mcp-config` emits the post-publish `uvx` form (noted)

`mcp-config` prints `{"command": "uvx", "args": ["forensic-deepdive", "serve", …]}` — correct
**once the package is on PyPI**, but a *pre-publish* user who pastes it gets a config that can't
launch (uvx can't fetch an unpublished package). The from-source / dev form is
`uv run --project <dir> forensic serve --repo …` instead. This **self-resolves the moment v0.8.0 is on PyPI**
(imminent). Optional v0.9 ergonomic: a `mcp-config --dev` that emits the `uv run --project` form
for from-source users. Low priority; documented in `docs/install.md`'s uvx-ENOENT fallback.

### 3. `list` accumulates stale registry entries (noted)

The multi-repo registry showed 37 repos including temp/smoke paths (`_smokeA`, `_smokeC`,
`%TEMP%/…`) from prior test runs. Not wrong — the registry is append-on-extract with no prune —
but it clutters `list`. Optional v0.9 ergonomic: `list --prune` / drop entries whose
`graph.lbug` no longer exists. Cosmetic.

## Verdict

The CLI is drivable end-to-end; every command does what its help says. The one genuine
paste-a-hollow-artifact wart (graph empty case) is fixed with a regression test; the other two
are cosmetic and one self-resolves at publish. No blocker for the v0.8 public release.
