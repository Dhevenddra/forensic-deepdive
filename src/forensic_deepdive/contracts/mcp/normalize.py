"""MCP tool-name normalization + ``contract_id`` key-builder (DEC-057, v0.5 Step 2).

The MCP analog of ``contracts/http/normalize.http_contract_id``: a pure, tag-free
equivalence function that both the provider (``@mcp.tool(name="x")`` / function
name) and the consumer (``call_tool("x")``) key on, so the two sides share one
literal namespace → an EXTRACTED join with no inference (research §1).

**Keying decision (RESOLVED, DEC-057): key on the bare tool name** —
``mcp::<tool>``. A ``ClientSession`` is 1:1 with one server, so server identity
*is* statically recoverable, but only via dataflow, and MCP has no official
cross-server name-collision standard (SEP-986 is "SHOULD be unique within a
server"). Bare-tool keying is a single-AST-node extraction; ``mcp::<server>::<tool>``
is a future INFERRED enhancement (PRD §10), not a v0.5 requirement.

**Normalize ``. / -`` → ``_`` before keying** — model APIs sanitize tool names
(Anthropic ``^[a-zA-Z0-9_-]{1,64}$``) and multi-server clients prefix them
(``mcp_<server>_<tool>``); normalizing the separators avoids false-negative joins
when one side wrote ``get-info`` and the other ``get_info``.
"""

from __future__ import annotations

import re

# Tool-name separators that model APIs / multi-server clients rewrite. Collapsing
# them to ``_`` keeps both sides on one key (``get-info`` ≡ ``get.info`` ≡ ``get_info``).
_SEP_RE = re.compile(r"[./\-]+")


def normalize_tool_name(tool_name: str) -> str:
    """Canonicalize an MCP tool name for keying: strip surrounding whitespace and
    collapse ``. / -`` runs to a single ``_``. Returns ``""`` for an empty/blank
    name (the caller drops it — no stable id)."""
    return _SEP_RE.sub("_", tool_name.strip())


def mcp_contract_id(tool_name: str) -> str:
    """The canonical ``mcp::<tool>`` contract id (the registry's ``mcp``
    key-builder). Bare-tool keyed, separator-normalized (see module docstring)."""
    return f"mcp::{normalize_tool_name(tool_name)}"
