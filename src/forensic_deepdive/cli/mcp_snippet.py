"""The MCP client-config snippet renderer — one source of truth (DEC-105/101).

``forensic mcp-config`` prints what this module renders, and the ``onboard``
wizard (DEC-101) reuses the same function rather than hardcoding a second copy
of the snippet. Two launch shapes:

* ``uvx forensic-deepdive serve --repo <repo>`` — post-publish, CWD-independent.
* ``uv run --project <checkout> forensic serve --repo <repo>`` — the ``--dev``
  form, correct for a from-source checkout where nothing is on PyPI yet.

Output is ASCII-only and markup-free so it survives a cp1252 console and a
redirect (``forensic mcp-config > .mcp.json``).
"""

from __future__ import annotations

import json
from pathlib import Path

CLIENTS = ("claude", "cursor", "vscode", "codex")


def source_checkout_dir() -> Path:
    """The src-layout project root of the *installed* package.

    ``forensic_deepdive.__file__`` is ``<root>/src/forensic_deepdive/__init__.py``
    in a from-source checkout, so ``parents[2]`` is the directory holding
    ``pyproject.toml``. For a wheel install the same walk lands in site-packages,
    which is why :func:`is_source_checkout` gates the dev form.
    """
    import forensic_deepdive

    return Path(forensic_deepdive.__file__).resolve().parents[2]


def is_source_checkout() -> bool:
    """True when the package runs from a checkout (a ``pyproject.toml`` sits at
    the src-layout root) — the signal the wizard uses to auto-pick ``--dev``."""
    return (source_checkout_dir() / "pyproject.toml").is_file()


def mcp_command(repo: Path, *, dev: bool = False) -> tuple[str, list[str]]:
    """The ``(command, args)`` pair a client launches the stdio server with."""
    repo_str = str(Path(repo).resolve())
    if dev:
        project_dir = str(source_checkout_dir())
        return "uv", ["run", "--project", project_dir, "forensic", "serve", "--repo", repo_str]
    return "uvx", ["forensic-deepdive", "serve", "--repo", repo_str]


def render_mcp_config(repo: Path, *, client: str = "claude", dev: bool = False) -> str:
    """Render the config snippet for *client* as a plain string (no trailing newline)."""
    command, args = mcp_command(repo, dev=dev)
    if client == "codex":
        return "\n".join(
            [
                "[mcp_servers.forensic-deepdive]",
                f'command = "{command}"',
                f"args = {json.dumps(args)}",
            ]
        )
    key = "servers" if client == "vscode" else "mcpServers"
    return json.dumps({key: {"forensic-deepdive": {"command": command, "args": args}}}, indent=2)
