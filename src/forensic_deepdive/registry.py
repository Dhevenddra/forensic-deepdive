"""Multi-repo registry (DEC-018) — ``~/.deepdive/registry.json``.

Records every repo that has been analyzed by ``forensic extract``, so
``forensic list`` can show them and (v0.3) the MCP server can serve
multiple repos in one process. GitNexus pattern (research §1 Tier 1).

v0.2 ships the registry + the CLI ``list`` subcommand + auto-register
on every successful ``run_extract``. Multi-repo MCP serving is v0.3:
the MCP tools currently take a single ``graph_db_path`` baked in at
construction; multi-repo would require a repo-selector arg on every
tool call. Out of v0.2 scope by design.

File format (JSON, human-readable, single object with one ``repos``
list)::

    {
      "version": 1,
      "repos": [
        {
          "name": "forensic-deepdive",
          "repo_path": "C:/Dev/projects/forensic-deepdive",
          "graph_db_path": "C:/Dev/projects/forensic-deepdive/.deepdive/graph.lbug",
          "last_extracted_at": "2026-05-25T12:34:56+00:00"
        }
      ]
    }

The ``name`` field is the repo's directory basename — the primary key
for dedup on subsequent extracts.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

REGISTRY_FORMAT_VERSION = 1


def default_registry_path() -> Path:
    """Return the platform-appropriate path to ``~/.deepdive/registry.json``.

    Honors the ``FORENSIC_REGISTRY`` environment variable for tests so
    we don't pollute the user's home directory.
    """
    override = os.environ.get("FORENSIC_REGISTRY")
    if override:
        return Path(override)
    return Path.home() / ".deepdive" / "registry.json"


@dataclass(frozen=True, slots=True)
class RegistryEntry:
    """One registered repo."""

    name: str
    repo_path: str  # absolute posix-style
    graph_db_path: str | None  # absolute posix-style; None if no graph built
    last_extracted_at: str  # ISO-8601 UTC


@dataclass(frozen=True, slots=True)
class Registry:
    """In-memory view of the registry. Construct via :func:`load` and
    persist via :func:`save`."""

    version: int
    repos: tuple[RegistryEntry, ...]


def load(registry_path: Path | None = None) -> Registry:
    """Read the registry from disk. Returns an empty registry when the
    file doesn't exist (first-run case)."""
    path = registry_path or default_registry_path()
    if not path.is_file():
        return Registry(version=REGISTRY_FORMAT_VERSION, repos=())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # Corrupt file — treat as empty rather than crashing the
        # extract pipeline. The next save will overwrite cleanly.
        return Registry(version=REGISTRY_FORMAT_VERSION, repos=())
    if not isinstance(data, dict) or "repos" not in data:
        return Registry(version=REGISTRY_FORMAT_VERSION, repos=())
    repos = tuple(
        RegistryEntry(
            name=r.get("name", ""),
            repo_path=r.get("repo_path", ""),
            graph_db_path=r.get("graph_db_path"),
            last_extracted_at=r.get("last_extracted_at", ""),
        )
        for r in data["repos"]
        if isinstance(r, dict)
    )
    return Registry(
        version=int(data.get("version", REGISTRY_FORMAT_VERSION)),
        repos=repos,
    )


def save(registry: Registry, registry_path: Path | None = None) -> None:
    """Persist *registry* to disk. Creates the parent directory if needed."""
    path = registry_path or default_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": registry.version,
        "repos": [asdict(r) for r in registry.repos],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def register(
    repo_path: Path,
    graph_db_path: Path | None = None,
    *,
    registry_path: Path | None = None,
    now: datetime | None = None,
) -> RegistryEntry:
    """Insert-or-update a repo in the registry. Returns the entry that
    was written.

    Dedup is by directory basename (matching the v0.2 ``name`` semantic).
    If a repo with the same name exists, this call REPLACES it — useful
    for path-moved repos so the registry doesn't accumulate duplicates.
    """
    registry = load(registry_path)
    entry = RegistryEntry(
        name=Path(repo_path).resolve().name,
        repo_path=Path(repo_path).resolve().as_posix(),
        graph_db_path=Path(graph_db_path).resolve().as_posix()
        if graph_db_path is not None
        else None,
        last_extracted_at=(now or datetime.now(UTC)).isoformat(timespec="seconds"),
    )
    others = tuple(r for r in registry.repos if r.name != entry.name)
    save(
        Registry(version=REGISTRY_FORMAT_VERSION, repos=(*others, entry)),
        registry_path,
    )
    return entry


def remove(name: str, *, registry_path: Path | None = None) -> bool:
    """Remove a repo by name. Returns True if an entry was removed."""
    registry = load(registry_path)
    kept = tuple(r for r in registry.repos if r.name != name)
    if len(kept) == len(registry.repos):
        return False
    save(Registry(version=REGISTRY_FORMAT_VERSION, repos=kept), registry_path)
    return True
