"""Shared scanning helpers for HTTP route extractors (DEC-045, v0.4 Item F).

Provider/consumer extractors can't read Tree-sitter ``Tree`` objects from the
pipeline — :class:`~forensic_deepdive.static.parse_cache.ParseResult` deliberately
drops them (DEC-035, unpicklable across the parallel-parse pool). So extractors
**re-parse** the candidate route files here: a cheap substring pre-filter selects
files that *could* carry routes, then those (and only those) are parsed once.

This mirrors GitNexus's ``compilePatterns``/``runCompiledPatterns`` shape (research
§2) — compile/parse once, walk per file — without retaining trees globally.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING

from tree_sitter import Node

from forensic_deepdive.static.parse import parse_source

if TYPE_CHECKING:
    from forensic_deepdive.contracts.registry import ContractContext

# The HTTP verbs a route decorator/annotation/client call can name.
HTTP_VERBS: frozenset[str] = frozenset(
    {"get", "post", "put", "delete", "patch", "head", "options", "trace"}
)


def iter_candidate_files(
    ctx: ContractContext,
    *,
    languages: Sequence[str],
    markers: Sequence[bytes],
) -> Iterator[tuple[str, bytes, Node]]:
    """Yield ``(rel_path, source_bytes, root_node)`` for each graph file whose
    language is in *languages* and whose bytes contain at least one of *markers*.

    The marker pre-filter (e.g. ``b"fastapi"``, ``b"APIRouter"``) keeps us from
    parsing every file in a large repo — only plausible route files are parsed.
    Files are visited in sorted ``rel_path`` order for determinism; unreadable
    files are skipped (the inventory already counted them)."""
    lang_set = set(languages)
    for rel_path in sorted(ctx.source_files_by_path):
        if ctx.source_files_by_path[rel_path] not in lang_set:
            continue
        try:
            data = (ctx.repo_path / rel_path).read_bytes()
        except OSError:
            continue
        if not any(m in data for m in markers):
            continue
        language = ctx.source_files_by_path[rel_path]
        yield rel_path, data, parse_source(data, language).root_node


def py_string_literal(node: Node, src: bytes) -> str | None:
    """Return a Python ``string`` node's static value, or ``None`` when it isn't a
    plain literal (an f-string/byte-string or one with ``${}``-style
    interpolation is *computed* — the caller marks that INFERRED or skips it)."""
    if node.type != "string":
        return None
    parts: list[str] = []
    for child in node.children:
        if child.type == "interpolation":
            return None  # f-string with a substitution → not static
        if child.type == "string_start":
            prefix = src[child.start_byte : child.end_byte].decode("utf-8", "replace").lower()
            if "f" in prefix or "b" in prefix:
                return None
        elif child.type == "string_content":
            parts.append(src[child.start_byte : child.end_byte].decode("utf-8", "replace"))
    return "".join(parts)


def rightmost_name(node: Node, src: bytes) -> str | None:
    """The trailing identifier of an ``identifier`` or ``attribute`` node:
    ``router`` → ``router``; ``items.router`` → ``router``. Used to match an
    ``include_router(items.router, …)`` mount to the router's local var name."""
    if node.type == "identifier":
        return src[node.start_byte : node.end_byte].decode("utf-8", "replace")
    if node.type == "attribute":
        attr = node.child_by_field_name("attribute")
        if attr is not None:
            return src[attr.start_byte : attr.end_byte].decode("utf-8", "replace")
    return None


def keyword_arg_value(call_args: Node, name: str, src: bytes) -> str | None:
    """The static string value of keyword arg *name* in an ``argument_list``
    (``prefix="/api"`` → ``/api``), or ``None`` if absent/computed."""
    for child in call_args.children:
        if child.type != "keyword_argument":
            continue
        key = child.child_by_field_name("name")
        val = child.child_by_field_name("value")
        if key is None or val is None:
            continue
        if src[key.start_byte : key.end_byte].decode("utf-8", "replace") == name:
            return py_string_literal(val, src)
    return None


def first_positional_string(call_args: Node, src: bytes) -> str | None:
    """The first positional argument of an ``argument_list`` as a static string
    (the route path in ``@app.get("/x")``), or ``None`` if computed/absent."""
    for child in call_args.children:
        if child.type in ("(", ")", ",", "comment"):
            continue
        if child.type == "keyword_argument":
            continue
        return py_string_literal(child, src)
    return None
