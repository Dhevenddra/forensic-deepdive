"""MCP distribution artifact guards (DEC-089).

Structural checks on the registry `server.json`, the Claude Code plugin manifest,
the bundled `.mcp.json`, and the README `mcp-name` marker — so the published
distribution metadata can't drift from each other or from the actual console-script
entry point. (Full JSON-Schema validation of server.json against the official
2025-09-29 schema is done out-of-band — it needs network; here we assert the
required fields + cross-file consistency offline.)
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MCP_NAME = "io.github.dhevenddra/forensic-deepdive"
_SERVE_CMD = "uvx"
_SERVE_ARGS = ["forensic-deepdive", "serve", "--repo", "."]


def _load(name: str) -> dict:
    return json.loads((_ROOT / name).read_text(encoding="utf-8"))


def test_server_json_required_fields_and_package() -> None:
    s = _load("server.json")
    # Server (base) required fields per the official schema.
    for field in ("name", "description", "version"):
        assert s.get(field), f"server.json missing required field {field!r}"
    assert s["name"] == _MCP_NAME
    pkgs = s.get("packages", [])
    assert len(pkgs) == 1
    pkg = pkgs[0]
    assert pkg["registryType"] == "pypi"
    assert pkg["identifier"] == "forensic-deepdive"
    assert pkg["transport"] == {"type": "stdio"}
    # The serve subcommand + --repo must be encoded as package arguments.
    args = pkg.get("packageArguments", [])
    assert any(a.get("type") == "positional" and a.get("value") == "serve" for a in args)
    assert any(a.get("type") == "named" and a.get("name") == "--repo" for a in args)


def test_readme_mcp_name_marker_matches_server_json() -> None:
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    m = re.search(r"<!--\s*mcp-name:\s*(\S+)\s*-->", readme)
    assert m, "README is missing the mcp-name ownership marker"
    assert m.group(1) == _MCP_NAME == _load("server.json")["name"]


def test_plugin_manifest_minimal_and_named() -> None:
    p = _load(".claude-plugin/plugin.json")
    assert p.get("name") == "forensic-deepdive"  # the only required field


def test_bundled_mcp_json_runs_the_package() -> None:
    cfg = _load(".mcp.json")
    server = cfg["mcpServers"]["forensic-deepdive"]
    assert server["command"] == _SERVE_CMD
    assert server["args"] == _SERVE_ARGS


def test_advertised_command_matches_a_real_console_script() -> None:
    """`uvx forensic-deepdive …` requires a console script named exactly
    `forensic-deepdive` — guard the alias against accidental removal."""
    pyproject = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = pyproject["project"]["scripts"]
    assert "forensic-deepdive" in scripts
    assert scripts["forensic-deepdive"] == "forensic_deepdive.cli:app"
    assert scripts["forensic"] == "forensic_deepdive.cli:app"  # primary binary (DEC-010)


def test_server_and_plugin_versions_agree() -> None:
    """server.json + plugin.json advertise the same release version (bump both at
    the DEC-092 release)."""
    assert _load("server.json")["version"] == _load(".claude-plugin/plugin.json")["version"]
