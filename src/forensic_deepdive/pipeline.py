"""Extract pipeline — wires the layers into ``forensic extract``.

Stages: **inventory → static → flatten → history → emit**. Assembles a
:class:`RepoFacts` bundle, writes the five artifacts (plus the optional
AGENT_BRIEF_DEEP.md) to the output directory, drops editor shims, and records a
run fingerprint so an unchanged repo is a cache hit.

The flatten stage is best-effort: a missing or failing Repomix degrades to
``flatten=None`` rather than aborting the run.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from forensic_deepdive.cache import (
    cache_dir,
    read_last_run,
    repo_fingerprint,
    write_last_run,
)
from forensic_deepdive.emit import RepoFacts, render_all
from forensic_deepdive.emit.shims import ShimResult, write_shims
from forensic_deepdive.flatten.repomix_backend import (
    RepomixError,
    flatten_repo,
    is_repomix_available,
)
from forensic_deepdive.history.git_archaeology import analyze_history
from forensic_deepdive.inventory import take_inventory
from forensic_deepdive.static.graph import build_symbol_graph
from forensic_deepdive.static.pagerank import rank_files
from forensic_deepdive.static.parse import parse_file
from forensic_deepdive.static.tags import Tag, extract_tags

_DEFAULT_OUTPUT_SUBDIR = ("docs", "codebase")


@dataclass
class ExtractResult:
    """The outcome of one :func:`run_extract` call."""

    repo_path: Path
    output_dir: Path
    artifacts: dict[str, Path]  # filename -> written path
    facts: RepoFacts | None  # None on a cache hit
    shims: ShimResult
    cache_hit: bool
    flatten_ok: bool


def run_extract(
    repo_path: Path,
    output_dir: Path | None = None,
    *,
    force: bool = False,
    flatten: bool = True,
    write_editor_shims: bool = True,
    fetch_github: bool = False,
    github_token: str | None = None,
) -> ExtractResult:
    """Run the full extract pipeline against *repo_path*.

    Args:
        repo_path: Repository root to analyze.
        output_dir: Where to write artifacts. Defaults to
            ``<repo>/docs/codebase``.
        force: Ignore the cache and regenerate even if nothing changed.
        flatten: Run the Repomix flatten stage when Repomix is available.
        write_editor_shims: Drop CLAUDE.md / AGENTS.md / editor-rule shims.
        fetch_github: Fetch GitHub metadata for the `origin` remote.
        github_token: Optional GitHub API token.
    """
    repo_path = Path(repo_path).resolve()
    if not repo_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {repo_path}")
    output_dir = (
        repo_path.joinpath(*_DEFAULT_OUTPUT_SUBDIR) if output_dir is None else Path(output_dir)
    )

    # 1. inventory
    inventory = take_inventory(repo_path)

    # 2. cache check
    fingerprint = repo_fingerprint([(item.rel_path, item.path) for item in inventory.files])
    if not force:
        last = read_last_run(repo_path)
        if last is not None and last.fingerprint == fingerprint:
            existing = {name: output_dir / name for name in last.artifacts}
            if existing and all(path.is_file() for path in existing.values()):
                return ExtractResult(
                    repo_path=repo_path,
                    output_dir=output_dir,
                    artifacts=existing,
                    facts=None,
                    shims=ShimResult(),
                    cache_hit=True,
                    flatten_ok=False,
                )

    # 3. static analysis
    tags: list[Tag] = []
    for source in inventory.source_files:
        parsed = parse_file(source.path, rel_path=source.rel_path)
        if parsed is not None:
            tags.extend(extract_tags(parsed))
    symbol_graph = build_symbol_graph(tags)
    ranked = rank_files(symbol_graph)

    # 4. flatten (best-effort — never fatal)
    flatten_result = None
    if flatten and is_repomix_available():
        try:
            flatten_result = flatten_repo(
                repo_path,
                cache_dir(repo_path) / "repomix-pack.md",
                style="markdown",
            )
        except RepomixError:
            flatten_result = None

    # 5. history
    history = analyze_history(repo_path, fetch_github=fetch_github, github_token=github_token)

    # 6. assemble facts
    facts = RepoFacts(
        repo_path=repo_path,
        repo_name=repo_path.name,
        generated_at=datetime.now(UTC),
        file_count=len(inventory.source_files),
        language_breakdown=inventory.language_breakdown,
        tags=tags,
        symbol_graph=symbol_graph,
        ranked=ranked,
        history=history,
        flatten=flatten_result,
        test_file_count=len(inventory.test_files),
        fixture_file_count=len(inventory.fixture_files),
    )

    # 7. emit
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, Path] = {}
    for filename, content in render_all(facts).items():
        path = output_dir / filename
        path.write_text(content, encoding="utf-8")
        artifacts[filename] = path

    # 8. shims (only when the brief lands inside the repo)
    shims = ShimResult()
    if write_editor_shims:
        try:
            brief_rel = (
                (output_dir / "AGENT_BRIEF.md").resolve().relative_to(repo_path)
            ).as_posix()
        except ValueError:
            brief_rel = None
        if brief_rel is not None:
            shims = write_shims(repo_path, brief_rel)

    # 9. cache
    write_last_run(
        repo_path,
        fingerprint,
        facts.generated_at.isoformat(),
        list(artifacts),
    )

    return ExtractResult(
        repo_path=repo_path,
        output_dir=output_dir,
        artifacts=artifacts,
        facts=facts,
        shims=shims,
        cache_hit=False,
        flatten_ok=flatten_result is not None,
    )
