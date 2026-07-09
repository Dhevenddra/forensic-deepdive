"""Interactive CLI layer (v0.9 Track A, DEC-099+).

Human-facing interactive surfaces — the query REPL (`forensic repl`), and in
later steps the Textual graph browser, the `onboard` wizard, and the `deepdive`
session shell. Every one of them is a **view** over the existing graph + the 9
MCP tools + the query paths (DEC-009 zero-LLM floor; the artifact/tool contract
is frozen).

The heavy dependencies (`prompt_toolkit`, later `textual`) live behind the
``[interactive]`` extra so the agent-first install (`extract` + `serve`) stays
lean. Modules here must import cleanly WITHOUT the extra — the third-party
imports happen inside the entry functions, which fail with
:data:`INSTALL_HINT` when the extra is absent.
"""

from __future__ import annotations

INSTALL_HINT = (
    "Interactive mode needs the `interactive` extra:\n"
    "  pip install 'forensic-deepdive[interactive]'\n"
    "  (or: uv tool install 'forensic-deepdive[interactive]')"
)


def interactive_available() -> bool:
    """True when the ``[interactive]`` extra's REPL dependency is importable."""
    try:
        import prompt_toolkit  # noqa: F401, PLC0415 — availability probe only
    except ImportError:
        return False
    return True
