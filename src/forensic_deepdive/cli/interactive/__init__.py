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


# A TTY check is not enough on Windows: MinTTY/Git Bash reports ``isatty() ==
# True`` but hands prompt_toolkit an xterm-style terminal with no Windows
# console screen buffer, so the full-screen surfaces raise on startup. Catch
# that at the point of construction and say what to do about it, rather than
# spilling a traceback (found by running the `deepdive` script under Git Bash).
TERMINAL_HINT = (
    "This terminal can't host an interactive session (it looks like MinTTY /\n"
    "Git Bash, which reports a TTY but has no Windows console screen buffer).\n"
    "Run it from PowerShell, Windows Terminal or cmd.exe - or prefix the\n"
    "command with `winpty`."
)


def terminal_errors() -> tuple[type[BaseException], ...]:
    """Exceptions raised when a terminal cannot host a full-screen surface."""
    import io

    errors: list[type[BaseException]] = [io.UnsupportedOperation]
    try:
        from prompt_toolkit.output.win32 import (  # noqa: PLC0415 — optional, Windows-only
            NoConsoleScreenBufferError,
        )
    except Exception:  # pragma: no cover — not Windows, or the extra is absent
        pass
    else:
        errors.append(NoConsoleScreenBufferError)
    return tuple(errors)
