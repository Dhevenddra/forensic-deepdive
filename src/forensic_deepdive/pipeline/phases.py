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
    Author,
    AuthoredByEdge,
    CallsEdge,
    CoChangesWithEdge,
    Commit,
    Confidence,
    DefinesEdge,
    ExtendsEdge,
    File,
    ImplementsEdge,
    ImportsEdge,
    LadybugStore,
    MemberOfEdge,
    Module,
    Symbol,
    SymbolKind,
    TouchedByCommitEdge,
)
from forensic_deepdive.graph.schema import FileRole, module_pk
from forensic_deepdive.history.git_archaeology import GitHistory, analyze_history
from forensic_deepdive.inventory import Inventory, SourceFile, take_inventory
from forensic_deepdive.pipeline.runner import Context, Phase
from forensic_deepdive.static.graph import SymbolGraph, build_symbol_graph
from forensic_deepdive.static.imports import Import, extract_imports
from forensic_deepdive.static.inheritance import InheritanceRecord, extract_inheritance
from forensic_deepdive.static.pagerank import RankedRepo, rank_files
from forensic_deepdive.static.parse import parse_file
from forensic_deepdive.static.resolver import MODULE_SCOPE, resolve_calls
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
    imports: list[Import]  # DEC-024 — one per import/include/require statement
    inheritance: list[InheritanceRecord]  # DEC-028 — class-hierarchy declarations


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
    member_of_count: int = 0  # MEMBER_OF edges written (DEC-023)
    module_count: int = 0  # Module nodes written (DEC-024)
    imports_count: int = 0  # IMPORTS edges written (DEC-024)
    calls_count: int = 0  # CALLS edges written (DEC-025)
    commit_count: int = 0  # Commit nodes written (DEC-026)
    author_count: int = 0  # Author nodes written (DEC-026)
    touched_by_commit_count: int = 0  # TOUCHED_BY_COMMIT edges written (DEC-026)
    authored_by_count: int = 0  # AUTHORED_BY edges written (DEC-026)
    co_changes_count: int = 0  # CO_CHANGES_WITH edges written (DEC-027)
    extends_count: int = 0  # EXTENDS edges written (DEC-028)
    implements_count: int = 0  # IMPLEMENTS edges written (DEC-028)


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
        imports: list[Import] = []
        inheritance: list[InheritanceRecord] = []
        for source in inv.source_files:
            parsed = parse_file(source.path, rel_path=source.rel_path)
            if parsed is not None:
                tags.extend(extract_tags(parsed))
                # DEC-024 — extract imports in the same parse pass to
                # avoid re-parsing every file in BuildGraphPhase.
                imports.extend(extract_imports(parsed))
                # DEC-028 — extract inheritance the same way.
                inheritance.extend(extract_inheritance(parsed))
        symbol_graph = build_symbol_graph(tags)
        ranked = rank_files(symbol_graph)
        return StaticOutput(
            tags=tags,
            symbol_graph=symbol_graph,
            ranked=ranked,
            imports=imports,
            inheritance=inheritance,
        )


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
        # DEC-026: when building the LadybugDB graph, request full
        # per-commit metadata + file lists so BuildGraphPhase can write
        # Commit / Author / TOUCHED_BY_COMMIT / AUTHORED_BY. The v0.1
        # path leaves this off — the extra ``git log --name-only`` pass
        # costs nothing on small repos but is measurable on huge ones.
        return HistoryOutput(
            history=analyze_history(
                cfg.repo_path,
                fetch_github=cfg.fetch_github,
                github_token=cfg.github_token,
                include_commit_files=cfg.build_graph_db,
            )
        )


class EmitPhase(Phase):
    """Assembles the :class:`RepoFacts` bundle, renders every artifact,
    writes the optional editor shims. v0.1's emit-from-NetworkX path —
    PRD §10 item 9 makes this read from the LadybugDB projection."""

    name = "emit"
    depends_on = ("inventory", "static", "flatten", "history", "build_graph")
    output_type = EmitOutput

    def run(self, ctx: Context) -> EmitOutput:
        cfg = ctx.config
        inv = ctx.get(InventoryPhase).inventory
        static = ctx.get(StaticPhase)
        history = ctx.get(HistoryPhase).history
        flatten = ctx.get(FlattenPhase).result
        # DEC-029: pass through the populated LadybugDB path (or None)
        # so emitters can query the graph for symbol-level / co-change /
        # call-graph content. Path is set IFF BuildGraphPhase populated
        # the DB on this run.
        build_graph = ctx.get(BuildGraphPhase)
        graph_db_path = build_graph.db_path if build_graph.enabled else None

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
            graph_db_path=graph_db_path,
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

    Writes File + Symbol + Module + Commit + Author nodes and
    DEFINES + MEMBER_OF + IMPORTS + CALLS + TOUCHED_BY_COMMIT +
    AUTHORED_BY edges. The phase is **opt-in** via
    ``ExtractConfig.build_graph_db`` so the v0.1 cache + golden tests
    stay untouched until the markdown emitters cut over to read from
    the graph (PRD §10 item 9).
    """

    name = "build_graph"
    depends_on = ("inventory", "static", "history")
    output_type = BuildGraphOutput

    def run(self, ctx: Context) -> BuildGraphOutput:
        cfg = ctx.config
        if not cfg.build_graph_db:
            return BuildGraphOutput(enabled=False, db_path=None)

        db_path = cfg.graph_db_path or cfg.repo_path.joinpath(*_DEFAULT_GRAPH_DB_SUBDIR)
        # DEC-030: every extract REGENERATES the graph from current source
        # state — matching the v0.1 "extract rebuilds artifacts" semantics.
        # Without this, a second extract on the same repo collides on
        # File / Symbol / Module / etc. primary keys. real-ladybug uses
        # a single-file ``.lbug`` plus a sibling ``.lbug.wal`` on Windows;
        # other platforms may use a directory. Handle both.
        import shutil

        if db_path.exists():
            if db_path.is_dir():
                shutil.rmtree(db_path)
            else:
                db_path.unlink()
        # Also clean up the WAL sidecar real-ladybug writes next to the
        # main DB file. Without this, reopening picks up stale state and
        # PKs collide.
        wal_path = db_path.with_suffix(db_path.suffix + ".wal")
        if wal_path.exists():
            if wal_path.is_dir():
                shutil.rmtree(wal_path)
            else:
                wal_path.unlink()
        inv = ctx.get(InventoryPhase).inventory
        static = ctx.get(StaticPhase)

        # DEC-023: group def Tags by their FULLY-QUALIFIED local name
        # (``<parent>.<name>`` for methods, ``<name>`` for top-level). This
        # is finer-grained than v0.1's SymbolGraph.definitions, which keys
        # on bare name — same-name methods in two classes in one file
        # would collide there but here become distinct Symbols.
        def_groups: dict[tuple[str, str], list[Tag]] = {}
        for tag in static.tags:
            if tag.kind != "def":
                continue
            qn_local = f"{tag.parent}.{tag.name}" if tag.parent else tag.name
            def_groups.setdefault((tag.rel_path, qn_local), []).append(tag)

        # DEC-024: dedup Module nodes by their (language, raw_path) pair.
        # Two imports of "os" from Python files share one Module; Python's
        # "os" and Go's "os" do NOT share — see ``module_pk``.
        module_pks: dict[str, Module] = {}  # pk -> Module dataclass
        source_file_paths = {sf.rel_path for sf in inv.source_files}
        edges_imports: list[ImportsEdge] = []
        for imp in static.imports:
            if imp.rel_path not in source_file_paths:
                continue  # importing file isn't a source file we wrote
            if not imp.module_path:
                continue
            pk = module_pk(imp.language, imp.module_path)
            module_pks[pk] = Module(path=pk, language=imp.language)
            edges_imports.append(
                ImportsEdge(
                    file_path=imp.rel_path,
                    module_path=pk,
                    confidence=Confidence.EXTRACTED,
                    evidence="tree-sitter",
                )
            )

        # DEC-025: resolve CALLS now (in-memory, before opening the DB)
        # so the resolver's intra-repo file-set is sealed before we start
        # writing. The CALLS edges below MATCH on the Symbol qns we
        # write further down — including the synthetic per-file
        # ``<module>`` Symbols that carry module-level refs.
        source_files_by_path = {sf.rel_path: sf.language for sf in inv.source_files}
        resolved_calls = resolve_calls(static.tags, static.imports, source_files_by_path)

        # DEC-026: history data into the graph. Authors aggregated from
        # commit records (mailmap-canonical post-DEC-022), commits keyed
        # by sha, edges only for files present in the inventory's source
        # set (git history may reference deleted / renamed / vendored
        # files we don't analyze).
        history = ctx.get(HistoryPhase).history
        author_records: dict[str, Author] = {}  # email_canonical -> Author
        commit_records_to_write: list[Commit] = []
        edges_authored_by: list[AuthoredByEdge] = []
        edges_touched_by_commit: list[TouchedByCommitEdge] = []
        # DEC-027 co-change aggregation: for each commit, the set of
        # source-set files it touched contributes one count to every
        # unordered pair within that set. We compute counts in-memory
        # over the inventoried touches (NOT raw commit files) so the
        # signal is restricted to the production graph.
        co_change_counts: dict[tuple[str, str], int] = {}
        for commit in history.commits:
            commit_records_to_write.append(
                Commit(
                    sha=commit.sha,
                    author_email=commit.author_email,
                    date=commit.date.isoformat() if commit.date else "",
                    message=commit.message_subject,
                    files_touched_count=len(commit.files_touched),
                )
            )
            author_records.setdefault(
                commit.author_email,
                Author(email_canonical=commit.author_email, name=commit.author_name),
            )
            edges_authored_by.append(
                AuthoredByEdge(
                    commit_sha=commit.sha,
                    author_email=commit.author_email,
                    confidence=Confidence.EXTRACTED,
                    evidence="git-log",
                )
            )
            commit_source_files: list[str] = []
            for file_path in commit.files_touched:
                if file_path in source_file_paths:
                    commit_source_files.append(file_path)
                    edges_touched_by_commit.append(
                        TouchedByCommitEdge(
                            file_path=file_path,
                            commit_sha=commit.sha,
                            confidence=Confidence.EXTRACTED,
                            evidence="git-log-name-only",
                        )
                    )
            # DEC-027: every unordered pair within this commit's
            # source-set files gets one co-occurrence count. The pair is
            # stored alphabetically so each unordered pair maps to
            # exactly one key.
            commit_source_files.sort()
            for i, a in enumerate(commit_source_files):
                for b in commit_source_files[i + 1 :]:
                    co_change_counts[(a, b)] = co_change_counts.get((a, b), 0) + 1

        # DEC-028: resolve inheritance parent names against the same
        # indexes the CALLS resolver uses — same-file -> import -> cross-
        # file fallback. Build a quick lookup of class-shaped Symbol
        # qn_locals per file (top-level only — inheritance always names
        # a top-level type in v0.2). Inheritance edges resolve at
        # build-time, not via the resolver.py call-resolver, because the
        # input shape is different (declaration vs reference).
        defs_top_by_file: dict[str, set[str]] = {}
        defs_top_by_lang: dict[str, dict[str, list[str]]] = {}
        for rel_path, qn_local in def_groups:
            if "." in qn_local:
                continue  # top-level only
            defs_top_by_file.setdefault(rel_path, set()).add(qn_local)
            lang = source_files_by_path.get(rel_path)
            if lang is not None:
                defs_top_by_lang.setdefault(lang, {}).setdefault(qn_local, []).append(rel_path)

        resolved_extends: list[ExtendsEdge] = []
        resolved_implements: list[ImplementsEdge] = []
        for ihr in static.inheritance:
            if ihr.rel_path not in source_file_paths:
                continue
            child_qn = _qualified_name(ihr.rel_path, ihr.child_qn_local)
            # 1. Same-file lookup.
            target_files: list[str] = []
            if ihr.parent_name in defs_top_by_file.get(ihr.rel_path, ()):
                target_files = [ihr.rel_path]
                conf = Confidence.EXTRACTED
            else:
                # 2. Import-walk: any import in this file naming the parent?
                imp_matches: list[str] = []
                for imp in static.imports:
                    if imp.rel_path != ihr.rel_path:
                        continue
                    for ime in imp.imported_names:
                        if ime.name == ihr.parent_name or ime.alias == ihr.parent_name:
                            from forensic_deepdive.static.resolver import (
                                _resolve_import_to_file,
                            )

                            tgt = _resolve_import_to_file(imp, source_files_by_path)
                            if tgt is not None and ihr.parent_name in defs_top_by_file.get(tgt, ()):
                                imp_matches.append(tgt)
                            break
                if imp_matches:
                    target_files = imp_matches
                    conf = Confidence.EXTRACTED
                else:
                    # 3. Cross-file fallback (same language only).
                    candidates = defs_top_by_lang.get(ihr.language, {}).get(ihr.parent_name, [])
                    candidates = [c for c in candidates if c != ihr.rel_path]
                    if not candidates:
                        continue  # external — drop
                    target_files = sorted(candidates)
                    conf = Confidence.INFERRED if len(target_files) == 1 else Confidence.AMBIGUOUS
            for tgt_file in target_files:
                parent_qn = _qualified_name(tgt_file, ihr.parent_name)
                if ihr.kind == "extends":
                    resolved_extends.append(
                        ExtendsEdge(
                            child=child_qn,
                            parent=parent_qn,
                            confidence=conf,
                            evidence="ast-declaration",
                        )
                    )
                else:
                    resolved_implements.append(
                        ImplementsEdge(
                            implementation=child_qn,
                            interface=parent_qn,
                            confidence=conf,
                            evidence="ast-declaration",
                        )
                    )

        file_count = symbol_count = defines_count = member_of_count = 0
        module_count = imports_count = calls_count = 0
        commit_count = author_count = 0
        touched_by_commit_count = authored_by_count = 0
        co_changes_count = extends_count = implements_count = 0
        with LadybugStore(db_path) as store:
            for sf in inv.source_files:
                store.add_file(_source_to_file(sf, cfg.repo_path))
                file_count += 1

            # DEC-024: Module nodes first, then IMPORTS edges. Dedup
            # already done in module_pks; sort for deterministic order.
            for pk in sorted(module_pks):
                store.add_module(module_pks[pk])
                module_count += 1

            # DEC-025: synthetic per-file ``<module>`` Symbol. Required
            # so module-level CALLS (refs outside any function/method)
            # have a valid caller endpoint. Kind=MODULE distinguishes
            # these from real symbols. The file DEFINES its own module
            # scope — keeping the invariant ``defines_count ==
            # symbol_count`` (every Symbol has a File defining it).
            for sf in inv.source_files:
                module_qn = _qualified_name(sf.rel_path, MODULE_SCOPE)
                store.add_symbol(
                    Symbol(
                        qualified_name=module_qn,
                        kind=SymbolKind.MODULE,
                        file_path=sf.rel_path,
                        line_start=0,
                        line_end=0,
                        signature="",
                    )
                )
                symbol_count += 1
                store.add_defines(
                    DefinesEdge(
                        file_path=sf.rel_path,
                        symbol=module_qn,
                        confidence=Confidence.EXTRACTED,
                        evidence="synthetic-module-scope",
                    )
                )
                defines_count += 1

            # Sort by (rel_path, qn_local). The lexical order of the
            # dotted qn_local guarantees a parent (e.g. ``Greeter``) is
            # written before any of its members (``Greeter.greet``,
            # ``Greeter.Inner.deep``) — the MEMBER_OF MATCH then resolves.
            for (rel_path, qn_local), tag_list in sorted(def_groups.items()):
                first = tag_list[0]
                qn = _qualified_name(rel_path, qn_local)
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
                # DEC-023: emit MEMBER_OF when the definition is nested
                # inside another definition (class method, nested class,
                # Go receiver method, etc.). EXTRACTED — the parent chain
                # is AST-deterministic.
                if first.parent:
                    parent_qn = _qualified_name(rel_path, first.parent)
                    store.add_member_of(
                        MemberOfEdge(
                            member=qn,
                            parent=parent_qn,
                            confidence=Confidence.EXTRACTED,
                            evidence="tree-sitter-ast-walk",
                        )
                    )
                    member_of_count += 1

            # DEC-024: IMPORTS edges last — after both File and Module
            # endpoints exist. Deterministic order via the staged list.
            edges_imports.sort(key=lambda e: (e.file_path, e.module_path))
            for edge in edges_imports:
                store.add_imports(edge)
                imports_count += 1

            # DEC-025: CALLS edges last — both endpoints (caller +
            # callee Symbols) must be present. The resolver's output is
            # already deterministically sorted, but we filter to skip
            # any whose callee Symbol won't exist (defensive: the
            # resolver's index aligns with def_groups, so this is
            # belt-and-suspenders).
            valid_symbol_qns = {
                _qualified_name(sf.rel_path, MODULE_SCOPE) for sf in inv.source_files
            } | {_qualified_name(rel_path, qn_local) for (rel_path, qn_local) in def_groups}
            for call in resolved_calls:
                if call.caller_qn not in valid_symbol_qns or call.callee_qn not in valid_symbol_qns:
                    continue
                store.add_calls(
                    CallsEdge(
                        caller=call.caller_qn,
                        callee=call.callee_qn,
                        confidence=call.confidence,
                        evidence=call.evidence,
                    )
                )
                calls_count += 1

            # DEC-026: history into the graph. Authors first (Commits
            # reference them via AUTHORED_BY), then Commits, then the
            # two edge types. Deterministic order via sorted iteration.
            for email in sorted(author_records):
                store.add_author(author_records[email])
                author_count += 1
            commit_records_to_write.sort(key=lambda c: c.sha)
            for commit in commit_records_to_write:
                store.add_commit(commit)
                commit_count += 1
            edges_authored_by.sort(key=lambda e: (e.commit_sha, e.author_email))
            for edge in edges_authored_by:
                store.add_authored_by(edge)
                authored_by_count += 1
            edges_touched_by_commit.sort(key=lambda e: (e.file_path, e.commit_sha))
            for edge in edges_touched_by_commit:
                store.add_touched_by_commit(edge)
                touched_by_commit_count += 1

            # DEC-027: CO_CHANGES_WITH edges last — Files must exist
            # (they already do from the inventory loop). Threshold from
            # cfg.co_changes_threshold filters out coincidence.
            threshold = cfg.co_changes_threshold
            for (file_a, file_b), count in sorted(co_change_counts.items()):
                if count < threshold:
                    continue
                store.add_co_changes_with(
                    CoChangesWithEdge(
                        file_a=file_a,
                        file_b=file_b,
                        frequency=float(count),
                        confidence=Confidence.INFERRED,
                        evidence="touched-by-commit-join",
                    )
                )
                co_changes_count += 1

            # DEC-028: EXTENDS / IMPLEMENTS edges — both endpoints
            # (Symbol qns) must exist. The resolver above filtered out
            # unresolved cases. Deterministic order via sort.
            resolved_extends.sort(key=lambda e: (e.child, e.parent))
            for edge in resolved_extends:
                if edge.child in valid_symbol_qns and edge.parent in valid_symbol_qns:
                    store.add_extends(edge)
                    extends_count += 1
            resolved_implements.sort(key=lambda e: (e.implementation, e.interface))
            for edge in resolved_implements:
                if edge.implementation in valid_symbol_qns and edge.interface in valid_symbol_qns:
                    store.add_implements(edge)
                    implements_count += 1

        return BuildGraphOutput(
            enabled=True,
            db_path=db_path,
            file_count=file_count,
            symbol_count=symbol_count,
            defines_count=defines_count,
            member_of_count=member_of_count,
            module_count=module_count,
            imports_count=imports_count,
            calls_count=calls_count,
            commit_count=commit_count,
            author_count=author_count,
            touched_by_commit_count=touched_by_commit_count,
            authored_by_count=authored_by_count,
            co_changes_count=co_changes_count,
            extends_count=extends_count,
            implements_count=implements_count,
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
