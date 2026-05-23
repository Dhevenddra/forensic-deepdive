"""v0.1 extract pipeline expressed as DAG phases.

DEC-014. Each phase owns one v0.1 stage and declares its dependencies as
strings. Outputs are typed dataclasses — downstream phases read them via
``ctx.get(UpstreamPhase)``.

v0.1 behavior is preserved exactly: same fingerprint, same artifacts, same
flatten-is-best-effort degradation, same shim semantics. The golden-emit
tests are the canary.

v0.2 PRD §10 item 8 adds :class:`BuildGraphPhase` — opt-in via
``ExtractConfig.build_graph_db=True``. When on, it persists File +
Symbol + DEFINES into a LadybugDB graph at ``<repo>/.deepdive/graph.lbug``
(or wherever ``graph_db_path`` points). Off by default until the markdown
emitters cut over to read from the graph (PRD §10 item 9).
"""

from __future__ import annotations

import hashlib
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
from forensic_deepdive.graph import (
    Confidence,
    DefinesEdge,
    File,
    LadybugStore,
    Symbol,
    SymbolKind,
)
from forensic_deepdive.graph.schema import FileRole
from forensic_deepdive.history.git_archaeology import GitHistory, analyze_history
from forensic_deepdive.inventory import Inventory, SourceFile, take_inventory
from forensic_deepdive.pipeline.runner import Context, Phase
from forensic_deepdive.static.graph import SymbolGraph, build_symbol_graph
from forensic_deepdive.static.pagerank import RankedRepo, rank_files
from forensic_deepdive.static.parse import parse_file
from forensic_deepdive.static.tags import Tag, extract_tags

# DEC-013 default DB location, mirroring v0.1's cache convention.
_DEFAULT_GRAPH_DB_SUBDIR = (".deepdive", "graph.lbug")

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


@dataclass(frozen=True, slots=True)
class BuildGraphOutput:
    """Result of the LadybugDB build phase (DEC-013 activation)."""

    enabled: bool  # False when ``ExtractConfig.build_graph_db`` is off
    db_path: Path | None  # the .lbug directory; None when disabled
    file_count: int = 0  # File nodes written
    symbol_count: int = 0  # Symbol nodes written
    defines_count: int = 0  # DEFINES edges written


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
            vendored_file_count=len(inv.vendored_files),
            generated_file_count=len(inv.generated_files),
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


class BuildGraphPhase(Phase):
    """Persist the v0.1 in-memory analysis into a LadybugDB graph
    (DEC-013, PRD §10 item 8).

    Writes File + Symbol nodes and DEFINES edges. v0.2 phase 1 stops there
    — CALLS edges require a symbol-level resolver (PRD §10 future), and
    IMPORTS / MEMBER_OF land alongside it. The phase is **opt-in** via
    ``ExtractConfig.build_graph_db`` so the v0.1 cache + golden tests stay
    untouched until the markdown emitters cut over to read from the graph
    (PRD §10 item 9).
    """

    name = "build_graph"
    depends_on = ("inventory", "static")
    output_type = BuildGraphOutput

    def run(self, ctx: Context) -> BuildGraphOutput:
        cfg = ctx.config
        if not cfg.build_graph_db:
            return BuildGraphOutput(enabled=False, db_path=None)

        db_path = cfg.graph_db_path or cfg.repo_path.joinpath(*_DEFAULT_GRAPH_DB_SUBDIR)
        inv = ctx.get(InventoryPhase).inventory
        static = ctx.get(StaticPhase)

        file_count = symbol_count = defines_count = 0
        with LadybugStore(db_path) as store:
            for sf in inv.source_files:
                store.add_file(_source_to_file(sf, cfg.repo_path))
                file_count += 1

            # SymbolGraph.definitions is keyed by (rel_path, name) so a
            # symbol with multiple def Tags (overloads, broad-query repeats)
            # is naturally deduped — one Symbol per entry.
            for (rel_path, name), tag_list in sorted(static.symbol_graph.definitions.items()):
                first = tag_list[0]
                qn = _qualified_name(rel_path, name)
                store.add_symbol(
                    Symbol(
                        qualified_name=qn,
                        kind=_category_to_kind(first.category),
                        file_path=rel_path,
                        line_start=first.line,
                        line_end=max(t.line for t in tag_list),
                        signature="",
                    )
                )
                symbol_count += 1
                store.add_defines(
                    DefinesEdge(
                        file_path=rel_path,
                        symbol=qn,
                        confidence=Confidence.EXTRACTED,
                        evidence="tree-sitter",
                    )
                )
                defines_count += 1

        return BuildGraphOutput(
            enabled=True,
            db_path=db_path,
            file_count=file_count,
            symbol_count=symbol_count,
            defines_count=defines_count,
        )


# ---------------------------------------------------------------------------
# Tag -> graph translation helpers
# ---------------------------------------------------------------------------


_CATEGORY_TO_KIND: dict[str, SymbolKind] = {
    "function": SymbolKind.FUNCTION,
    "class": SymbolKind.CLASS,
    "method": SymbolKind.METHOD,
    "interface": SymbolKind.INTERFACE,
    "enum": SymbolKind.ENUM,
    "type": SymbolKind.TYPE,
    "struct": SymbolKind.STRUCT,
}


def _category_to_kind(category: str) -> SymbolKind:
    """Map a Tag.category to a SymbolKind, defaulting to FUNCTION."""
    return _CATEGORY_TO_KIND.get(category, SymbolKind.FUNCTION)


def _qualified_name(rel_path: str, name: str) -> str:
    """Schema convention: ``<rel_path>::<name>`` (see schema.Symbol)."""
    return f"{rel_path}::{name}"


def _source_to_file(sf: SourceFile, repo_path: Path) -> File:
    """Convert an Inventory SourceFile into a graph File node.

    Computes the three bits of metadata the v0.1 SourceFile doesn't carry:
    SHA-256 of the content, line count, and last-modified ISO timestamp.
    Failure to read the file degrades each field to a safe default rather
    than aborting the whole graph build.
    """
    sha = "0" * 64
    loc = 0
    last_modified = ""
    try:
        data = sf.path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        loc = data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)
        mtime = datetime.fromtimestamp(sf.path.stat().st_mtime, tz=UTC)
        last_modified = mtime.isoformat(timespec="seconds")
    except OSError:
        pass
    return File(
        path=sf.rel_path,
        language=sf.language,
        role=FileRole(sf.role),
        sha=sha,
        loc=loc,
        last_modified=last_modified,
    )


def default_phases() -> list[Phase]:
    """The v0.2 phase DAG. ``BuildGraphPhase`` is in the list but is a no-op
    unless ``ExtractConfig.build_graph_db=True`` (DEC-013)."""
    return [
        InventoryPhase(),
        StaticPhase(),
        FlattenPhase(),
        HistoryPhase(),
        BuildGraphPhase(),
        EmitPhase(),
    ]
