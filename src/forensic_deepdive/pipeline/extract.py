"""Public ``run_extract`` orchestration.

DEC-014. Wraps the DAG :class:`PipelineRunner` with cache-hit handling and
``ExtractResult`` assembly. The cache check lives outside the DAG because it
fundamentally answers "should we run anything at all?" — an orchestration
concern, not a phase concern.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from forensic_deepdive.cache import read_last_run, repo_fingerprint, write_last_run
from forensic_deepdive.emit import RepoFacts
from forensic_deepdive.emit.shims import ShimResult
from forensic_deepdive.pipeline.phases import (
    EmitPhase,
    InventoryPhase,
    default_phases,
)
from forensic_deepdive.pipeline.runner import Context, ExtractConfig, PipelineRunner
from forensic_deepdive.registry import register as register_repo

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
    flatten: bool = False,
    write_editor_shims: bool = True,
    fetch_github: bool = False,
    github_token: str | None = None,
    workers: int | None = None,
) -> ExtractResult:
    """Run the full extract pipeline against *repo_path*.

    v0.2 routes through the DAG :class:`PipelineRunner` (DEC-014). DEC-017
    flipped the ``flatten`` default to ``False`` — Repomix is demoted to
    opt-in (the LadybugDB graph + MCP server supersede "pack the repo
    for an LLM"). Pass ``flatten=True`` to keep the v0.1 behavior.

    Args:
        repo_path: Repository root to analyze.
        output_dir: Where to write artifacts. Defaults to
            ``<repo>/docs/codebase``.
        force: Ignore the cache and regenerate even if nothing changed.
        flatten: DEC-017 — opt into Repomix flatten. Default ``False``.
        write_editor_shims: Drop CLAUDE.md / AGENTS.md / editor-rule shims.
        fetch_github: Fetch GitHub metadata for the `origin` remote.
        github_token: Optional GitHub API token.
        workers: DEC-035 — parse-phase worker count. ``None`` ⇒ ``min(cpu-1,
            16)``; ``1`` forces the serial path.
    """
    repo_path = Path(repo_path).resolve()
    if not repo_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {repo_path}")
    resolved_output = (
        repo_path.joinpath(*_DEFAULT_OUTPUT_SUBDIR) if output_dir is None else Path(output_dir)
    )

    config = ExtractConfig(
        repo_path=repo_path,
        output_dir=resolved_output,
        force=force,
        flatten=flatten,
        write_editor_shims=write_editor_shims,
        fetch_github=fetch_github,
        github_token=github_token,
        workers=workers,
    )

    runner = PipelineRunner(default_phases())

    # Inventory first so we can compute the fingerprint for cache lookup.
    # On a hit, every downstream phase is skipped — matches v0.1's
    # 2.2 s cached-Omi run.
    inv_phase = InventoryPhase()
    inv_output = inv_phase.run(Context(config=config))
    fingerprint = repo_fingerprint(
        [(item.rel_path, item.path) for item in inv_output.inventory.files]
    )

    if not force:
        last = read_last_run(repo_path)
        if last is not None and last.fingerprint == fingerprint:
            existing = {name: resolved_output / name for name in last.artifacts}
            if existing and all(path.is_file() for path in existing.values()):
                return ExtractResult(
                    repo_path=repo_path,
                    output_dir=resolved_output,
                    artifacts=existing,
                    facts=None,
                    shims=ShimResult(),
                    cache_hit=True,
                    flatten_ok=False,
                )

    # Cache miss — run the DAG, seeding the already-computed inventory.
    ctx = runner.run(config, seed_outputs={inv_phase.name: inv_output})
    emit_out = ctx.get(EmitPhase)

    write_last_run(
        repo_path,
        fingerprint,
        emit_out.facts.generated_at.isoformat(),
        list(emit_out.artifacts),
    )

    # DEC-018: register the repo in ~/.deepdive/registry.json so
    # `forensic list` shows it (and v0.3 multi-repo MCP can find it).
    # Best-effort — registry write failures must not break extract.
    import contextlib

    with contextlib.suppress(OSError):
        register_repo(repo_path, emit_out.facts.graph_db_path)

    return ExtractResult(
        repo_path=repo_path,
        output_dir=resolved_output,
        artifacts=emit_out.artifacts,
        facts=emit_out.facts,
        shims=emit_out.shims,
        cache_hit=False,
        flatten_ok=emit_out.facts.flatten is not None,
    )
