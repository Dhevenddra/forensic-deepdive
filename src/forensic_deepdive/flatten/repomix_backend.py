"""Repomix flatten backend — Layer 2.

Wraps the Repomix CLI (https://github.com/yamadashy/repomix) as a subprocess to
flatten a repository into a single AI-friendly file. Repomix is the default
Layer-2 backend per DEC-004; ``yek`` is planned as a v0.2 ``--fast`` alternative.

Repomix is an external Node tool, *not* a Python dependency. Install it with::

    npm install -g repomix

``flatten_repo`` raises :class:`RepomixNotFoundError` (a subclass of
:class:`RepomixError`) carrying that hint when the binary is absent, so callers
can degrade gracefully rather than crash.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPOMIX_INSTALL_HINT = "Repomix CLI not found. Install it with: npm install -g repomix"

# Repomix output formats (see `repomix --help`, "--style").
VALID_STYLES: frozenset[str] = frozenset({"markdown", "xml", "json", "plain"})

_DEFAULT_TIMEOUT_S = 600.0


class RepomixError(RuntimeError):
    """A Repomix run failed (bad arguments, non-zero exit, missing output)."""


class RepomixNotFoundError(RepomixError):
    """The Repomix CLI is not installed or not on PATH."""


@dataclass(frozen=True, slots=True)
class FlattenResult:
    """The outcome of a successful Repomix run.

    ``char_count`` is the size of the artifact we produced; ``file_count`` and
    ``token_count`` are Repomix's own counts for the *source* repo, best-effort
    parsed from its summary (``None`` if the summary format changes upstream).
    """

    output_path: Path
    style: str
    char_count: int
    file_count: int | None
    token_count: int | None
    command: list[str]


def repomix_path() -> str | None:
    """Return the resolved Repomix executable path, or ``None`` if not found."""
    return shutil.which("repomix")


def is_repomix_available() -> bool:
    """True if the Repomix CLI can be located on PATH."""
    return repomix_path() is not None


def flatten_repo(
    repo_path: Path,
    output_path: Path,
    *,
    style: str = "markdown",
    compress: bool = False,
    remove_comments: bool = False,
    security_check: bool = True,
    include: str | None = None,
    ignore: str | None = None,
    timeout: float = _DEFAULT_TIMEOUT_S,
) -> FlattenResult:
    """Flatten *repo_path* into a single file at *output_path* via Repomix.

    Args:
        repo_path: Repository root to pack.
        output_path: Where to write the packed file. Parent dirs are created.
        style: Output format — one of :data:`VALID_STYLES`.
        compress: Use Repomix's Tree-sitter compression (structure only).
        remove_comments: Strip code comments before packing.
        security_check: Keep Repomix's Secretlint scan on (recommended).
        include: Comma-separated glob include patterns.
        ignore: Comma-separated extra glob ignore patterns.
        timeout: Seconds before the subprocess is killed.

    Raises:
        RepomixNotFoundError: Repomix is not installed.
        RepomixError: Bad arguments, non-zero exit, timeout, or missing output.
    """
    if style not in VALID_STYLES:
        raise RepomixError(f"Unsupported style {style!r}; expected one of {sorted(VALID_STYLES)}")

    repo_path = Path(repo_path)
    if not repo_path.is_dir():
        raise RepomixError(f"Repo path is not a directory: {repo_path}")

    exe = repomix_path()
    if exe is None:
        raise RepomixNotFoundError(REPOMIX_INSTALL_HINT)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        *_invocation(exe),
        str(repo_path),
        "--output",
        str(output_path),
        "--style",
        style,
    ]
    if compress:
        command.append("--compress")
    if remove_comments:
        command.append("--remove-comments")
    if not security_check:
        command.append("--no-security-check")
    if include:
        command += ["--include", include]
    if ignore:
        command += ["--ignore", ignore]

    try:
        proc = subprocess.run(  # noqa: S603 - command built from a resolved path
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError as exc:  # exe vanished between which() and run()
        raise RepomixNotFoundError(REPOMIX_INSTALL_HINT) from exc
    except subprocess.TimeoutExpired as exc:
        raise RepomixError(f"Repomix timed out after {timeout:g}s") from exc

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RepomixError(f"Repomix exited with code {proc.returncode}:\n{detail}")
    if not output_path.is_file():
        raise RepomixError(f"Repomix reported success but wrote no output at {output_path}")

    content = output_path.read_text(encoding="utf-8", errors="replace")
    summary = f"{proc.stdout or ''}\n{proc.stderr or ''}"
    return FlattenResult(
        output_path=output_path,
        style=style,
        char_count=len(content),
        file_count=_parse_count(summary, "Total Files"),
        token_count=_parse_count(summary, "Total Tokens"),
        command=command,
    )


def _invocation(exe: str) -> list[str]:
    """Return the argv prefix to invoke *exe*.

    Windows ``.cmd`` / ``.bat`` shims (how ``npm -g`` installs Node CLIs) cannot
    be launched directly by ``CreateProcess``; route them through ``cmd /c``.
    """
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        return [os.environ.get("COMSPEC", "cmd.exe"), "/c", exe]
    return [exe]


def _parse_count(summary: str, label: str) -> int | None:
    """Best-effort parse of e.g. ``Total Files: 2 files`` from Repomix output."""
    match = re.search(rf"{re.escape(label)}\s*:?\s*([\d,]+)", summary)
    if match is None:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None
