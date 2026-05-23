"""v0.1 extract pipeline expressed as DAG phases.

DEC-014. Each phase owns one v0.1 stage and declares its dependencies as
strings. Outputs are typed dataclasses — downstream phases read them via
``ctx.get(UpstreamPhase)``.

v0.1 behavior is preserved exactly: same fingerprint, same artifacts, same
flatten-is-best-effort degradation, same shim semantics. The golden-emit
tests are the canary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from forensic_deepdive.cache import cache_dir
from forensic_deepdive.emit import RepoFacts, render_all
from forensic_deepdive.emit.shims import ShimResult, write_shims
from forensic_deepdive.flatten.repomix_backend import (
    FlattenResult,
    RepomixError,
    flatten_repo,
    is_repomix_available,
)
from forensic_deepdive.history.git_archaeology import GitHistory, analyze_history
from forensic_deepdive.inventory import Inventory, take_inventory
from forensic_deepdive.pipeline.runner import Context, Phase
from forensic_deepdive.static.graph import SymbolGraph, build_symbol_graph
from forensic_deepdive.static.pagerank import RankedRepo, rank_files
from forensic_deepdive.static.parse import parse_file
from forensic_deepdive.static.tags import Tag, extract_tags

# ---------------------------------------------------------------------------
# Phase outputs (typed dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InventoryOutput:
    inventory: Inventory


@dataclass(frozen=True, slots=True)
class StaticOutput:
    tags: list[Tag]
    symbol_graph: SymbolGraph
    ranked: RankedRepo


@dataclass(frozen=True, slots=True)
class FlattenOutput:
    """The flatten result is optional — missing or failing Repomix degrades
    to ``result=None`` rather than aborting the run (v0.1 behavior, DEC-004)."""

    result: FlattenResult | None


@dataclass(frozen=True, slots=True)
class HistoryOutput:
    history: GitHistory


@dataclass(frozen=True, slots=True)
class EmitOutput:
    facts: RepoFacts
    artifacts: dict[str, Path] = field(default_factory=dict)
    shims: ShimResult = field(default_factory=ShimResult)


# ---------------------------------------------------------------------------
# Phases
# ---------------------------------------------------------------------------


class InventoryPhase(Phase):
    """Walks the repo, classifies files by language and role (DEC-012)."""

    name = "inventory"
    depends_on = ()
    output_type = InventoryOutput

    def run(self, ctx: Context) -> InventoryOutput:
        return InventoryOutput(inventory=take_inventory(ctx.config.repo_path))


class StaticPhase(Phase):
    """Parses source files, builds the symbol graph, ranks files via
    PageRank. v0.1 keeps parse + graph + rank fused; PRD §10 item 8 will
    split parse / resolve / build_graph / persist into separate phases."""

    name = "static"
    depends_on = ("inventory",)
    output_type = StaticOutput

    def run(self, ctx: Context) -> StaticOutput:
        inv = ctx.get(InventoryPhase).inventory
        tags: list[Tag] = []
        for source in inv.source_files:
            parsed = parse_file(source.path, rel_path=source.rel_path)
            if parsed is not None:
                tags.extend(extract_tags(parsed))
        symbol_graph = build_symbol_graph(tags)
        ranked = rank_files(symbol_graph)
        return StaticOutput(tags=tags, symbol_graph=symbol_graph, ranked=ranked)


class FlattenPhase(Phase):
    """Runs Repomix when available. Best-effort — never fatal (DEC-004 /
    DEC-017-soon: this whole phase moves to ``--legacy-repomix`` in PRD §10
    item 12)."""

    name = "flatten"
    depends_on = ("inventory",)
    output_type = FlattenOutput

    def run(self, ctx: Context) -> FlattenOutput:
        cfg = ctx.config
        if not cfg.flatten or not is_repomix_available():
            return FlattenOutput(result=None)
        try:
            result = flatten_repo(
                cfg.repo_path,
                cache_dir(cfg.repo_path) / "repomix-pack.md",
                style="markdown",
            )
        except RepomixError:
            return FlattenOutput(result=None)
        return FlattenOutput(result=result)


class HistoryPhase(Phase):
    """Plain-git Layer-3 (DEC-005). GitHub REST is opt-in via config."""

    name = "history"
    depends_on = ("inventory",)
    output_type = HistoryOutput

    def run(self, ctx: Context) -> HistoryOutput:
        cfg = ctx.config
        return HistoryOutput(
            history=analyze_history(
                cfg.repo_path,
                fetch_github=cfg.fetch_github,
                github_token=cfg.github_token,
            )
        )


class EmitPhase(Phase):
    """Assembles the :class:`RepoFacts` bundle, renders every artifact,
    writes the optional editor shims. v0.1's emit-from-NetworkX path —
    PRD §10 item 9 makes this read from the LadybugDB projection."""

    name = "emit"
    depends_on = ("inventory", "static", "flatten", "history")
    output_type = EmitOutput

    def run(self, ctx: Context) -> EmitOutput:
        cfg = ctx.config
        inv = ctx.get(InventoryPhase).inventory
        static = ctx.get(StaticPhase)
        history = ctx.get(HistoryPhase).history
        flatten = ctx.get(FlattenPhase).result

        facts = RepoFacts(
            repo_path=cfg.repo_path,
            repo_name=cfg.repo_path.name,
            generated_at=datetime.now(UTC),
            file_count=len(inv.source_files),
            language_breakdown=inv.language_breakdown,
            tags=static.tags,
            symbol_graph=static.symbol_graph,
            ranked=static.ranked,
            history=history,
            flatten=flatten,
            test_file_count=len(inv.test_files),
            fixture_file_count=len(inv.fixture_files),
        )

        cfg.output_dir.mkdir(parents=True, exist_ok=True)
        artifacts: dict[str, Path] = {}
        for filename, content in render_all(facts).items():
            path = cfg.output_dir / filename
            path.write_text(content, encoding="utf-8")
            artifacts[filename] = path

        shims = ShimResult()
        if cfg.write_editor_shims:
            try:
                brief_rel = (
                    (cfg.output_dir / "AGENT_BRIEF.md").resolve().relative_to(cfg.repo_path)
                ).as_posix()
            except ValueError:
                brief_rel = None
            if brief_rel is not None:
                shims = write_shims(cfg.repo_path, brief_rel)

        return EmitOutput(facts=facts, artifacts=artifacts, shims=shims)


def default_phases() -> list[Phase]:
    """The v0.1 5-phase DAG. Used by :func:`run_extract` and any test that
    wants the canonical phase list."""
    return [
        InventoryPhase(),
        StaticPhase(),
        FlattenPhase(),
        HistoryPhase(),
        EmitPhase(),
    ]
