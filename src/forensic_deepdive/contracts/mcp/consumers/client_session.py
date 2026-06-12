"""MCP ClientSession tool-consumer extractor (DEC-057, v0.5 Step 2 — the headline
consumer).

An ``await session.call_tool("name", arguments=...)`` on an MCP ``ClientSession``
is a *consumer* of an MCP tool — the ``CALLS_ENDPOINT`` side, joined to its
``@mcp.tool()`` provider through a shared ``Endpoint(protocol='mcp')``::

    async with ClientSession(read, write) as session:
        result = await session.call_tool("get_weather", arguments={"city": city})
        await session.call_tool(name="add", arguments={"a": 1, "b": 2})

The tool name is the first positional string literal (or the ``name=`` kwarg) →
``mcp::<tool>`` (separator-normalized). ``.call_tool`` is a highly MCP-specific
attribute, so any receiver is accepted (no allowlist needed). Caller ``symbol_id``
via ``_parent_chain`` (the nearest enclosing ``def``, else ``<module>``), reused
from the requests/httpx consumer (the anti-drift convention).

Confidence: a literal tool name → **EXTRACTED** (both sides share one literal key →
an EXTRACTED join). A non-literal name (a variable / f-string / computed expr) has
no stable key → **dropped** (the DEC-037 "bound-or-drop, never guess one" posture);
server-qualified keying and a wildcard fan-out for dynamic names are future arcs
(PRD §10, Step 3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tree_sitter import Node

from forensic_deepdive.contracts.base import Contract, ContractRole
from forensic_deepdive.contracts.http.consumers.py_requests import (
    _enclosing_symbol,
    _positional_strings,
    _walk,
)
from forensic_deepdive.contracts.http.scan import (
    iter_candidate_files,
    keyword_arg_node,
    py_string_literal,
)
from forensic_deepdive.contracts.mcp.normalize import mcp_contract_id, normalize_tool_name
from forensic_deepdive.graph.schema import Confidence

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

_MARKERS = (b"call_tool",)
_LANGS = ("python",)


def _tool_name(call: Node, src: bytes) -> str | None:
    """The static tool name of a ``call_tool(...)`` call — first positional string
    literal, else the ``name=`` kwarg literal — or ``None`` when not a literal
    (a variable / f-string is unkeyable → dropped, not guessed)."""
    for arg in _positional_strings(call):
        return py_string_literal(arg, src)  # only the first positional matters
    args = call.child_by_field_name("arguments")
    if args is not None:
        name_node = keyword_arg_node(args, "name", src)
        if name_node is not None:
            return py_string_literal(name_node, src)
    return None


def extract_client_session_consumers(ctx: ContractContext) -> list[Contract]:
    seen: set[tuple[str, str]] = set()
    contracts: list[Contract] = []
    for rel_path, src, root in iter_candidate_files(ctx, languages=_LANGS, markers=_MARKERS):
        for node in _walk(root):
            if node.type != "call":
                continue
            fn = node.child_by_field_name("function")
            if fn is None or fn.type != "attribute":
                continue
            attr = fn.child_by_field_name("attribute")
            if attr is None or src[attr.start_byte : attr.end_byte] != b"call_tool":
                continue
            tool_name = _tool_name(node, src)
            if tool_name is None or not normalize_tool_name(tool_name):
                continue
            contract_id = mcp_contract_id(tool_name)
            symbol_id = _enclosing_symbol(node, src, rel_path)
            key = (contract_id, symbol_id)
            if key in seen:
                continue
            seen.add(key)
            normalized = normalize_tool_name(tool_name)
            contracts.append(
                Contract(
                    role=ContractRole.CONSUMER,
                    contract_id=contract_id,
                    symbol_id=symbol_id,
                    confidence=Confidence.EXTRACTED,
                    evidence=f"call_tool({tool_name!r})",
                    protocol="mcp",
                    method="",
                    normalized_path=normalized,
                    raw_path=normalized,
                    framework="mcp-client",
                    rel_path=rel_path,
                    line=node.start_point[0],
                )
            )
    return contracts
