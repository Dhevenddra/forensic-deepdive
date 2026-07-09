# Installing forensic-deepdive

`forensic-deepdive` is a single PyPI package that ships both the `forensic` CLI and
an MCP server. The MCP-config-friendly form is **`uvx forensic-deepdive serve --repo
<path>`** — `uvx` runs it CWD-independently and `--repo` makes the target repo
explicit, so the working directory never matters.

> Published on PyPI as [`forensic-deepdive`](https://pypi.org/project/forensic-deepdive/)
> (v0.8.0) and indexed in the official [MCP Registry](https://registry.modelcontextprotocol.io)
> as `io.github.Dhevenddra/forensic-deepdive`. The from-source form
> (`uv run --project /path/to/forensic-deepdive forensic serve --repo <path>`) still
> works for development.

Two config generators, one per install style (`forensic mcp-config` prints the
snippet for `--client claude|cursor|vscode|codex`):

- **Installed from PyPI** — `forensic mcp-config --repo <repo>` → the `uvx` form.
- **From-source checkout** — `forensic mcp-config --repo <repo> --dev` → the
  `uv run --project <checkout> forensic serve --repo <repo>` form (the `uvx`
  form can't launch an unpublished working copy).

## CLI

```bash
uv tool install forensic-deepdive      # puts `forensic` on PATH (~/.local/bin)
forensic extract /path/to/repo         # 5 artifacts + the graph
forensic info                          # capabilities banner

# or run ephemerally, no install:
uvx forensic-deepdive extract /path/to/repo
```

Optional extras: `uv tool install "forensic-deepdive[semantic]"` (offline ONNX NL
query), `[openapi]` (YAML spec parsing), `[graphiti]`.

## MCP server — per-client setup

First build the graph for the repo you want to query: `forensic extract <repo>`
(creates `<repo>/.deepdive/graph.lbug`). Then point your agent at it. All clients use
the same `uvx forensic-deepdive serve --repo <repo>` command; the 9 tools (`impact`,
`context`, `archaeology`, `flow`, `query`, `record_insight`, `recall_insights`,
`visualize`, `trace`) register automatically.

### Claude Code

```bash
claude mcp add forensic-deepdive -- uvx forensic-deepdive serve --repo .
```

or commit a project-scoped `.mcp.json` at the repo root (Claude Code will prompt to
approve it):

```json
{
  "mcpServers": {
    "forensic-deepdive": {
      "command": "uvx",
      "args": ["forensic-deepdive", "serve", "--repo", "."]
    }
  }
}
```

As a **plugin**: this repo self-hosts a Claude Code marketplace
(`.claude-plugin/marketplace.json`) alongside the `.claude-plugin/plugin.json` +
`.mcp.json` manifest, so two commands register the MCP server (no clone, no PyPI
step needed — Claude Code fetches the plugin from GitHub):

```shell
/plugin marketplace add Dhevenddra/forensic-deepdive
/plugin install forensic-deepdive@dhevenddra
```

`@dhevenddra` is the marketplace name; `forensic-deepdive` is the plugin. Refresh
later with `/plugin marketplace update dhevenddra`.

### Cursor

`.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "forensic-deepdive": {
      "command": "uvx",
      "args": ["forensic-deepdive", "serve", "--repo", "."]
    }
  }
}
```

### VS Code (Copilot)

`.vscode/mcp.json`:

```json
{
  "servers": {
    "forensic-deepdive": {
      "command": "uvx",
      "args": ["forensic-deepdive", "serve", "--repo", "."]
    }
  }
}
```

### Codex

```bash
codex mcp add forensic-deepdive -- uvx forensic-deepdive serve --repo .
```

or in `~/.codex/config.toml`:

```toml
[mcp_servers.forensic-deepdive]
command = "uvx"
args = ["forensic-deepdive", "serve", "--repo", "."]
```

### Continue / Cline / Windsurf

Same `mcpServers` JSON shape as Cursor.

## GUI apps and the `uvx`-not-found gotcha

GUI apps (e.g. Claude Desktop) don't inherit your shell `PATH`, so `command: "uvx"`
can fail with `ENOENT`. Use the absolute path to `uvx` (find it with
`which uvx` / `where uvx`), e.g. `command: "/home/you/.local/bin/uvx"`.
