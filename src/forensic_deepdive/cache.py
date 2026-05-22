"""Run cache — content fingerprints and ``last_run.json``.

A SHA-256 fingerprint over the inventoried source files lets ``extract`` skip
re-running when nothing has changed. State lives in
``<repo>/.forensic-deepdive/`` (gitignored). The v0.1 cache is all-or-nothing;
incremental update is v0.2.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from forensic_deepdive import __version__

CACHE_DIRNAME = ".forensic-deepdive"
LAST_RUN_FILENAME = "last_run.json"
_HASH_CHUNK = 1 << 16


@dataclass(frozen=True, slots=True)
class LastRun:
    """A record of the previous successful extract."""

    fingerprint: str
    generated_at: str  # ISO-8601
    tool_version: str
    artifacts: list[str]


def cache_dir(repo_path: Path) -> Path:
    """Return the ``.forensic-deepdive/`` cache directory for *repo_path*."""
    return Path(repo_path) / CACHE_DIRNAME


def file_sha256(path: Path) -> str:
    """Return the hex SHA-256 of a file's contents."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_fingerprint(files: list[tuple[str, Path]]) -> str:
    """Fingerprint a repo from ``(rel_path, absolute_path)`` pairs.

    Order-independent: pairs are sorted by ``rel_path`` first, so the result
    depends only on which files exist and what they contain.
    """
    digest = hashlib.sha256()
    for rel_path, abs_path in sorted(files, key=lambda pair: pair[0]):
        digest.update(rel_path.encode("utf-8"))
        digest.update(b"\0")
        try:
            digest.update(file_sha256(abs_path).encode("ascii"))
        except OSError:
            digest.update(b"<unreadable>")
        digest.update(b"\n")
    return digest.hexdigest()


def read_last_run(repo_path: Path) -> LastRun | None:
    """Load the previous run record, or ``None`` if absent / unreadable."""
    path = cache_dir(repo_path) / LAST_RUN_FILENAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return LastRun(
            fingerprint=data["fingerprint"],
            generated_at=data["generated_at"],
            tool_version=data["tool_version"],
            artifacts=list(data["artifacts"]),
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return None


def write_last_run(
    repo_path: Path,
    fingerprint: str,
    generated_at: str,
    artifacts: list[str],
) -> Path:
    """Write ``last_run.json`` and return its path, creating the cache dir."""
    record = LastRun(
        fingerprint=fingerprint,
        generated_at=generated_at,
        tool_version=__version__,
        artifacts=sorted(artifacts),
    )
    directory = cache_dir(repo_path)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / LAST_RUN_FILENAME
    path.write_text(json.dumps(asdict(record), indent=2) + "\n", encoding="utf-8")
    return path
