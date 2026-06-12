"""A tool-dispatch fixture (DEC-058) — the dispatch (consumer) side.

Exercises: a literal-key subscript dispatch (resolves one handler → INFERRED), a
dynamic-key subscript dispatch (fans out to every handler → AMBIGUOUS-all), and a
``.get`` dispatch.
"""

from tools import TOOLS, registry


def run_literal(name):
    # literal key → exactly one handler (INFERRED)
    return registry["greet"](name)


def run_dynamic(tool_name, a, b):
    # dynamic key → fans out to every TOOLS handler (AMBIGUOUS-all)
    return TOOLS[tool_name](a, b)


def run_get(tool_name, a, b):
    return TOOLS.get(tool_name)(a, b)
