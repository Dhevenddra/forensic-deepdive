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
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from forensic_deepdive.cache import cache_dir
from forensic_deepdive.contracts import Contract, ContractContext, ContractRole, CrossLink, join
from forensic_deepdive.contracts.dispatch.register import register_dispatch_extractors
from forensic_deepdive.contracts.http.normalize import http_wildcard_id
from forensic_deepdive.contracts.http.register import register_http_extractors
from forensic_deepdive.contracts.mcp.register import register_mcp_extractors
from forensic_deepdive.contracts.registry import REGISTRY
from forensic_deepdive.contracts.specs import collect_spec_operations, reconcile_with_specs
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
    CallsEndpointEdge,
    CoChangesWithEdge,
    Commit,
    Confidence,
    DefinesEdge,
    Endpoint,
    ExtendsEdge,
    File,
    HandlesEdge,
    ImplementsEdge,
    ImportsEdge,
    LadybugStore,
    MemberOfEdge,
    Module,
    RoutesToEdge,
    Symbol,
    SymbolKind,
    TouchedByCommitEdge,
)
from forensic_deepdive.graph.schema import FileRole, module_pk
from forensic_deepdive.history.git_archaeology import GitHistory, analyze_history
from forensic_deepdive.inventory import Inventory, SourceFile, take_inventory
from forensic_deepdive.pipeline.runner import Context, Phase
from forensic_deepdive.query.lexical import (
    build_lexical_index_from_store,
    lexical_index_path_for_db,
    records_from_store,
)
from forensic_deepdive.static.graph import SymbolGraph, build_symbol_graph
from forensic_deepdive.static.ids import SymbolDescriptor, assign_disambiguators
from forensic_deepdive.static.imports import Import
from forensic_deepdive.static.inheritance import InheritanceRecord
from forensic_deepdive.static.method_calls import MethodCall
from forensic_deepdive.static.pagerank import RankedRepo, rank_files
from forensic_deepdive.static.parse_cache import (
    PARALLEL_MIN_FILES,
    ManifestDiff,
    ParseCache,
    ParseResult,
    ParseTask,
    content_hash,
    diff_manifest,
    parse_cache_dir,
    parse_tasks,
    read_manifest,
    resolve_worker_count,
    write_manifest,
)
from forensic_deepdive.static.resolver import MODULE_SCOPE, resolve_calls, resolve_method_calls
from forensic_deepdive.static.tags import Tag

logger = logging.getLogger(__name__)

# DEC-013 default DB location, mirroring v0.1's cache convention.
_DEFAULT_GRAPH_DB_SUBDIR = (".deepdive", "graph.lbug")

# DEC-049: PageRank teleport weight for example/tutorial files — down-weighted
# vs the 1.0 baseline so tutorials don't rank as "central". Only applied when
# example files exist (otherwise the walk stays uniform == byte-identical).
_EXAMPLE_PR_WEIGHT = 0.1

# ---------------------------------------------------------------------------
# Phase outputs (typed dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InventoryOutput:
    inventory: Inventory


@dataclass(frozen=True, slots=True)
class ParseOutput:
    """Per-repo aggregate of the parse layer (DEC-036). ``ParsePhase`` produces
    the Tag / Import / InheritanceRecord records — from the content-addressed
    cache where possible, by parsing the rest — and reports how many files it
    actually had to run through Tree-sitter (``parsed_count``) vs served from
    cache (``cached_count``). ``diff`` is the Merkle-manifest diff vs the
    previous run, or ``None`` when the cache is disabled."""

    tags: list[Tag]
    imports: list[Import]  # DEC-024 — one per import/include/require statement
    inheritance: list[InheritanceRecord]  # DEC-028 — class-hierarchy declarations
    method_calls: list[MethodCall]  # DEC-037 — dotted method calls
    parsed_count: int  # files run through Tree-sitter this run
    cached_count: int  # files served from the parse cache
    diff: ManifestDiff | None  # manifest diff vs previous run; None if cache off


@dataclass(frozen=True, slots=True)
class StaticOutput:
    tags: list[Tag]
    symbol_graph: SymbolGraph
    ranked: RankedRepo
    imports: list[Import]  # DEC-024 — one per import/include/require statement
    inheritance: list[InheritanceRecord]  # DEC-028 — class-hierarchy declarations
    method_calls: list[MethodCall]  # DEC-037 — dotted method calls


@dataclass(frozen=True, slots=True)
class ContractOutput:
    """DEC-043 (v0.4 Item D). The cross-boundary contract layer: providers +
    consumers extracted per protocol, the materialized cross-links (ROUTES_TO),
    and the deduped Endpoint join nodes. Empty until Items F/G register HTTP
    extractors — the abstraction/schema/persistence are wired now."""

    providers: list[Contract]
    consumers: list[Contract]
    cross_links: list[CrossLink]
    endpoints: list[Endpoint]


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
    endpoint_count: int = 0  # Endpoint nodes written (DEC-043)
    handles_count: int = 0  # HANDLES edges written (DEC-043)
    calls_endpoint_count: int = 0  # CALLS_ENDPOINT edges written (DEC-043)
    routes_to_count: int = 0  # ROUTES_TO edges written (DEC-043)


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


class ParsePhase(Phase):
    """Parse source files into Tag / Import / InheritanceRecord records, using
    the content-addressed parse cache (DEC-036) to skip re-parsing unchanged
    files.

    Split out of the v0.1 ``StaticPhase`` (PRD §4.1, foreshadowed by DEC-014):
    this is the only phase that touches Tree-sitter, which makes it the unit
    Item B (DEC-035) parallelizes.

    Two-pass shape (DEC-035): pass 1 hashes every source file, builds the
    manifest, and consults the parse cache — the cheap, I/O-bound half. Cache
    *misses* become parse tasks dispatched to a ``ProcessPoolExecutor`` (or run
    serially below the small-repo threshold / with ``--workers 1``). Pass 2
    reassembles all records in **sorted ``rel_path`` order**, which reproduces
    the serial order exactly and preserves each file's intra-file record order
    — byte-identical artifacts regardless of worker count or completion order.
    """

    name = "parse"
    depends_on = ("inventory",)
    output_type = ParseOutput

    def run(self, ctx: Context) -> ParseOutput:
        cfg = ctx.config
        inv = ctx.get(InventoryPhase).inventory

        use_cache = cfg.use_parse_cache
        root = parse_cache_dir(cfg.repo_path)
        cache = ParseCache(root) if use_cache else None

        # Pass 1: hash + manifest + cache lookup. Hits resolve here; misses
        # become parse tasks for the pool.
        results: dict[str, ParseResult] = {}
        manifest: dict[str, str] = {}
        tasks: list[ParseTask] = []
        languages: dict[str, str] = {}  # rel_path -> language (for cache.put)
        # DEC-049: parse production source *and* example/tutorial files — both
        # feed the graph (example demoted later, not excluded).
        for source in inv.graph_files:
            try:
                data = source.path.read_bytes()
            except OSError:
                # Matches v0.1: an unreadable source file is silently skipped.
                continue
            sha = content_hash(data)
            manifest[source.rel_path] = sha
            languages[source.rel_path] = source.language

            hit = cache.get(source.rel_path, sha, source.language) if cache is not None else None
            if hit is not None:
                results[source.rel_path] = hit
            else:
                tasks.append((str(source.path), source.rel_path, source.language, sha))

        # Dispatch the misses. Serial below the threshold or with one worker;
        # parallel otherwise. Workers re-read + parse; the parent writes cache.
        workers = resolve_worker_count(cfg.workers)
        parallel = workers > 1 and len(tasks) >= PARALLEL_MIN_FILES
        for rel_path, _language, sha, result in parse_tasks(
            tasks, workers=workers, parallel=parallel
        ):
            results[rel_path] = result
            if cache is not None:
                cache.put(sha, _language, result)

        # Pass 2: deterministic reassembly. ``sorted(results)`` is the sorted
        # rel_path order == the serial source_files order.
        tags: list[Tag] = []
        imports: list[Import] = []
        inheritance: list[InheritanceRecord] = []
        method_calls: list[MethodCall] = []
        for rel_path in sorted(results):
            r = results[rel_path]
            tags.extend(r.tags)
            imports.extend(r.imports)
            inheritance.extend(r.inheritance)
            method_calls.extend(r.method_calls)

        diff: ManifestDiff | None = None
        if use_cache:
            diff = diff_manifest(read_manifest(root), manifest)
            write_manifest(root, manifest)

        return ParseOutput(
            tags=tags,
            imports=imports,
            inheritance=inheritance,
            method_calls=method_calls,
            parsed_count=len(tasks),
            cached_count=len(results) - len(tasks),
            diff=diff,
        )


class StaticPhase(Phase):
    """Builds the symbol graph and ranks files via PageRank from the parsed
    records. DEC-036 split the Tree-sitter parse half into :class:`ParsePhase`;
    this phase is now pure graph construction + ranking and re-exposes the
    parse records so downstream phases (Build/Emit) read an unchanged
    ``StaticOutput``."""

    name = "static"
    depends_on = ("inventory", "parse")
    output_type = StaticOutput

    def run(self, ctx: Context) -> StaticOutput:
        inv = ctx.get(InventoryPhase).inventory
        parsed = ctx.get(ParsePhase)
        symbol_graph = build_symbol_graph(parsed.tags)
        # DEC-049: bias PageRank away from example/tutorial files. The teleport
        # vector is built ONLY when example files exist; otherwise None keeps the
        # exact uniform-teleport path (byte-identical on no-example repos).
        example_paths = {sf.rel_path for sf in inv.example_files}
        personalization: dict[str, float] | None = None
        if example_paths:
            personalization = {
                node: (_EXAMPLE_PR_WEIGHT if node in example_paths else 1.0)
                for node in symbol_graph.graph.nodes
            }
        ranked = rank_files(symbol_graph, personalization)
        return StaticOutput(
            tags=parsed.tags,
            symbol_graph=symbol_graph,
            ranked=ranked,
            imports=parsed.imports,
            inheritance=parsed.inheritance,
            method_calls=parsed.method_calls,
        )


def _http_match_keys(consumer: Contract) -> tuple[str, ...]:
    """DEC-047 join candidate keys for an HTTP consumer: the exact
    ``http::<VERB>::<path>`` first, then the method-agnostic ``http::*::<path>``
    fallback (so a Spring bare ``@RequestMapping`` provider still joins). Other
    protocols match exact-only — the HTTP wildcard is HTTP's concern."""
    if consumer.protocol == "http" and consumer.normalized_path:
        return (consumer.contract_id, http_wildcard_id(consumer.normalized_path))
    return (consumer.contract_id,)


class ContractPhase(Phase):
    """Cross-boundary contract extraction + join (DEC-043, v0.4 Item D).

    Runs each protocol's registered provider/consumer extractors over the parsed
    repo, joins by ``contract_id``, and emits providers/consumers/cross-links +
    the deduped Endpoint nodes. In Item D the HTTP extractor lists are empty
    (Items F/G fill them), so output is empty — the abstraction, schema, and
    persistence path are wired and tested ahead of the extractors.
    """

    name = "contracts"
    depends_on = ("parse", "static")
    output_type = ContractOutput

    def run(self, ctx: Context) -> ContractOutput:
        # DEC-045: wire the HTTP provider/consumer extractors into the registry
        # (idempotent — a guarded no-op after the first call). DEC-057 (v0.5
        # Step 2): MCP registers the same way — a registration wire, not a
        # surfacing-layer change (the keystone: join/trace/emit/serve untouched).
        register_http_extractors()
        register_mcp_extractors()
        register_dispatch_extractors()  # DEC-058 (v0.5 Step 3) — same registration wire.
        cfg = ctx.config
        # inventory ran before static (which depends on it), so it's in ctx.
        inv = ctx.get(InventoryPhase).inventory
        static = ctx.get(StaticPhase)
        context = ContractContext(
            tags=static.tags,
            imports=static.imports,
            method_calls=static.method_calls,
            source_files_by_path={sf.rel_path: sf.language for sf in inv.graph_files},
            repo_path=cfg.repo_path,
        )

        providers: list[Contract] = []
        consumers: list[Contract] = []
        for entry in REGISTRY.values():
            for extractor in entry.provider_extractors:
                providers.extend(extractor(context))
            for extractor in entry.consumer_extractors:
                consumers.extend(extractor(context))

        # DEC-048 (Item I — the codegen shortcut): fold in OpenAPI/Swagger specs.
        # Spec-backed providers upgrade their unique join to EXTRACTED (DEC-047);
        # spec ops with no in-code handler become spec-only Endpoints. A YAML spec
        # found without the [openapi] extra is skipped LOUDLY (never silently).
        spec_scan = collect_spec_operations(cfg.repo_path)
        if spec_scan.skipped_yaml:
            logger.warning(
                "OpenAPI: %d YAML spec(s) skipped — install forensic-deepdive[openapi] "
                "to parse them: %s",
                len(spec_scan.skipped_yaml),
                ", ".join(spec_scan.skipped_yaml),
            )
        providers = reconcile_with_specs(providers, spec_scan.operations)

        cross_links = join(providers, consumers, match_keys=_http_match_keys)
        endpoints = _build_endpoints(providers, consumers)
        return ContractOutput(
            providers=providers,
            consumers=consumers,
            cross_links=cross_links,
            endpoints=endpoints,
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
            example_file_count=len(inv.example_files),
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
    depends_on = ("inventory", "static", "contracts", "history")
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
        # DEC-049: the graph corpus is production source *and* example files
        # (example demoted in ranking/query, not excluded). The four excluded
        # roles (test/fixture/vendored/generated) are not here.
        graph_files = inv.graph_files

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
        source_file_paths = {sf.rel_path for sf in graph_files}
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
        source_files_by_path = {sf.rel_path: sf.language for sf in graph_files}
        # DEC-025 bare-name calls + DEC-037 receiver-type method calls. Both
        # produce ResolvedCall records; the method-call edges carry via != bare
        # and are INFERRED/AMBIGUOUS (the receiver type is inferred).
        resolved_calls = resolve_calls(static.tags, static.imports, source_files_by_path)
        resolved_calls += resolve_method_calls(
            static.method_calls, static.tags, static.imports, source_files_by_path
        )

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

        # DEC-032: collect everything in memory, then write each table via
        # a single batched UNWIND call (chunked at LadybugStore._BATCH_SIZE).
        # The lists are sorted for determinism — UNWIND preserves row order,
        # so byte-identical graph hashes survive the batch path.

        # Files.
        files_to_write = [_source_to_file(sf, cfg.repo_path) for sf in graph_files]

        # Modules (already deduped in module_pks).
        modules_to_write = [module_pks[pk] for pk in sorted(module_pks)]

        # Symbols + DEFINES + MEMBER_OF.
        # DEC-025: synthetic per-file ``<module>`` Symbol first so module-level
        # CALLS have a valid caller endpoint. Kind=MODULE distinguishes them.
        symbols_to_write: list[Symbol] = []
        edges_defines: list[DefinesEdge] = []
        edges_member_of: list[MemberOfEdge] = []

        # DEC-051: mint a stable ``node_id`` for every Symbol via the
        # ``static.ids`` authority. Descriptors are assembled in the exact order
        # the Symbols are appended below (synthetic ``<module>`` symbols first,
        # then ``def_groups`` in sorted order); ``assign_disambiguators`` runs
        # over the whole set so the overload-disambiguation logic is live in the
        # build path (current mint granularity produces no collisions, so ids
        # are the clean ``<kind>:<rel_path>:<qn_local>`` form).
        sorted_def_items = sorted(def_groups.items())
        symbol_descriptors: list[SymbolDescriptor] = [
            SymbolDescriptor(str(SymbolKind.MODULE), sf.rel_path, MODULE_SCOPE)
            for sf in graph_files
        ]
        symbol_descriptors += [
            SymbolDescriptor(str(_category_to_kind(tags_[0].category)), rel_path, qn_local)
            for (rel_path, qn_local), tags_ in sorted_def_items
        ]
        symbol_ids = assign_disambiguators(symbol_descriptors)
        module_id_count = len(graph_files)

        for idx, sf in enumerate(graph_files):
            module_qn = _qualified_name(sf.rel_path, MODULE_SCOPE)
            symbols_to_write.append(
                Symbol(
                    qualified_name=module_qn,
                    kind=SymbolKind.MODULE,
                    file_path=sf.rel_path,
                    line_start=0,
                    line_end=0,
                    signature="",
                    node_id=symbol_ids[idx],
                )
            )
            edges_defines.append(
                DefinesEdge(
                    file_path=sf.rel_path,
                    symbol=module_qn,
                    confidence=Confidence.EXTRACTED,
                    evidence="synthetic-module-scope",
                )
            )
        # DEC-023: parents must be written before their members (the v0.1
        # path relied on lexical qn_local sort — same here). UNWIND inside
        # a single batch is fine, but the MATCH for MEMBER_OF needs both
        # endpoint Symbols to already exist — so we write Symbols (incl.
        # synthetics + real) in one batch, then DEFINES, then MEMBER_OF.
        for jdx, ((rel_path, qn_local), tag_list) in enumerate(sorted_def_items):
            first = tag_list[0]
            qn = _qualified_name(rel_path, qn_local)
            symbols_to_write.append(
                Symbol(
                    qualified_name=qn,
                    kind=_category_to_kind(first.category),
                    file_path=rel_path,
                    line_start=first.line,
                    line_end=max(t.line for t in tag_list),
                    signature="",
                    node_id=symbol_ids[module_id_count + jdx],
                )
            )
            edges_defines.append(
                DefinesEdge(
                    file_path=rel_path,
                    symbol=qn,
                    confidence=Confidence.EXTRACTED,
                    evidence="tree-sitter",
                )
            )
            if first.parent:
                parent_qn = _qualified_name(rel_path, first.parent)
                edges_member_of.append(
                    MemberOfEdge(
                        member=qn,
                        parent=parent_qn,
                        confidence=Confidence.EXTRACTED,
                        evidence="tree-sitter-ast-walk",
                    )
                )

        # IMPORTS — File and Module endpoints exist after the bulk writes
        # above. Deterministic sort.
        edges_imports.sort(key=lambda e: (e.file_path, e.module_path))

        # CALLS — defensive endpoint filter (resolver's index aligns with
        # def_groups, so this is belt-and-suspenders).
        valid_symbol_qns = {_qualified_name(sf.rel_path, MODULE_SCOPE) for sf in graph_files} | {
            _qualified_name(rel_path, qn_local) for (rel_path, qn_local) in def_groups
        }
        edges_calls = [
            CallsEdge(
                caller=call.caller_qn,
                callee=call.callee_qn,
                confidence=call.confidence,
                evidence=call.evidence,
                via=call.via,
            )
            for call in resolved_calls
            if call.caller_qn in valid_symbol_qns and call.callee_qn in valid_symbol_qns
        ]
        # Bare-name + method-call edges are concatenated from two resolvers;
        # sort the union for a deterministic write order (DEC-035 invariant).
        edges_calls.sort(key=lambda e: (e.caller, e.callee, e.via, e.evidence, str(e.confidence)))

        # DEC-026 history-into-graph: Authors first, then Commits, then
        # the two edges.
        authors_to_write = [author_records[email] for email in sorted(author_records)]
        commit_records_to_write.sort(key=lambda c: c.sha)
        edges_authored_by.sort(key=lambda e: (e.commit_sha, e.author_email))
        edges_touched_by_commit.sort(key=lambda e: (e.file_path, e.commit_sha))

        # DEC-027: CO_CHANGES_WITH edges with threshold filter.
        threshold = cfg.co_changes_threshold
        edges_co_changes: list[CoChangesWithEdge] = [
            CoChangesWithEdge(
                file_a=a,
                file_b=b,
                frequency=float(count),
                confidence=Confidence.INFERRED,
                evidence="touched-by-commit-join",
            )
            for (a, b), count in sorted(co_change_counts.items())
            if count >= threshold
        ]

        # DEC-028: EXTENDS / IMPLEMENTS — both endpoints filter + sort.
        resolved_extends.sort(key=lambda e: (e.child, e.parent))
        resolved_implements.sort(key=lambda e: (e.implementation, e.interface))
        edges_extends_to_write = [
            e
            for e in resolved_extends
            if e.child in valid_symbol_qns and e.parent in valid_symbol_qns
        ]
        edges_implements_to_write = [
            e
            for e in resolved_implements
            if e.implementation in valid_symbol_qns and e.interface in valid_symbol_qns
        ]

        # DEC-043: cross-boundary contracts → Endpoint nodes + HANDLES /
        # CALLS_ENDPOINT / ROUTES_TO edges. Endpoint nodes are already deduped +
        # sorted; the edges filter their Symbol endpoints against the valid set
        # (a handler/caller that isn't a real symbol is dropped) and sort for
        # determinism. Empty in Item D until the HTTP extractors land (F/G).
        contracts_out = ctx.get(ContractPhase)
        endpoints_to_write = contracts_out.endpoints
        edges_handles = sorted(
            (
                HandlesEdge(
                    symbol=p.symbol_id,
                    contract_id=p.contract_id,
                    confidence=p.confidence,
                    evidence=p.evidence or "route-decl",
                )
                for p in contracts_out.providers
                if p.symbol_id in valid_symbol_qns
            ),
            key=lambda e: (e.symbol, e.contract_id),
        )
        # DEC-048: a consumer hitting a spec-backed Endpoint (the spec is the
        # provider truth) gets its CALLS_ENDPOINT upgraded to EXTRACTED even when
        # no handler symbol is located — the join must not require a HANDLES edge.
        spec_backed_ids = {e.contract_id for e in endpoints_to_write if e.spec_backed}
        edges_calls_endpoint = sorted(
            (
                CallsEndpointEdge(
                    symbol=c.symbol_id,
                    contract_id=c.contract_id,
                    confidence=(
                        Confidence.EXTRACTED if c.contract_id in spec_backed_ids else c.confidence
                    ),
                    evidence=c.evidence or "call-site",
                )
                for c in contracts_out.consumers
                if c.symbol_id in valid_symbol_qns
            ),
            key=lambda e: (e.symbol, e.contract_id),
        )
        edges_routes_to = sorted(
            (
                RoutesToEdge(
                    consumer=cl.consumer_symbol_id,
                    provider=cl.provider_symbol_id,
                    via=cl.via,
                    endpoint=cl.contract_id,
                    confidence=cl.confidence,
                    evidence=cl.evidence,
                )
                for cl in contracts_out.cross_links
                if cl.consumer_symbol_id in valid_symbol_qns
                and cl.provider_symbol_id in valid_symbol_qns
            ),
            key=lambda e: (e.consumer, e.provider, e.endpoint),
        )

        with LadybugStore(db_path) as store:
            # Order matters: nodes before edges; for edges, both endpoints
            # must already exist.
            store.add_many_files(files_to_write)
            store.add_many_modules(modules_to_write)
            store.add_many_symbols(symbols_to_write)
            store.add_many_endpoints(endpoints_to_write)
            store.add_many_authors(authors_to_write)
            store.add_many_commits(commit_records_to_write)
            store.add_many_defines(edges_defines)
            store.add_many_member_of(edges_member_of)
            store.add_many_imports(edges_imports)
            store.add_many_calls(edges_calls)
            store.add_many_extends(edges_extends_to_write)
            store.add_many_implements(edges_implements_to_write)
            store.add_many_authored_by(edges_authored_by)
            store.add_many_touched_by_commit(edges_touched_by_commit)
            store.add_many_co_changes_with(edges_co_changes)
            # DEC-043: cross-boundary edges — Endpoint nodes exist now, so the
            # Symbol↔Endpoint and Symbol→Symbol edges can attach.
            store.add_many_handles(edges_handles)
            store.add_many_calls_endpoint(edges_calls_endpoint)
            store.add_many_routes_to(edges_routes_to)

            # DEC-038 (Item E): build the sidecar lexical FTS5 index from the
            # graph so the hybrid NL query has its always-on floor ready. The
            # opt-in semantic vector index is built only with --semantic and
            # when the [semantic] extra + a local model are present (DEC-042);
            # absent ⇒ silently skipped (the NL query degrades and says so).
            index_path = lexical_index_path_for_db(db_path)
            build_lexical_index_from_store(store, index_path)
            if cfg.semantic:
                _build_semantic_index(store, index_path)

        file_count = len(files_to_write)
        module_count = len(modules_to_write)
        symbol_count = len(symbols_to_write)
        defines_count = len(edges_defines)
        member_of_count = len(edges_member_of)
        imports_count = len(edges_imports)
        calls_count = len(edges_calls)
        author_count = len(authors_to_write)
        commit_count = len(commit_records_to_write)
        authored_by_count = len(edges_authored_by)
        touched_by_commit_count = len(edges_touched_by_commit)
        co_changes_count = len(edges_co_changes)
        extends_count = len(edges_extends_to_write)
        implements_count = len(edges_implements_to_write)

        return BuildGraphOutput(
            endpoint_count=len(endpoints_to_write),
            handles_count=len(edges_handles),
            calls_endpoint_count=len(edges_calls_endpoint),
            routes_to_count=len(edges_routes_to),
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


def _build_endpoints(providers: list[Contract], consumers: list[Contract]) -> list[Endpoint]:
    """DEC-043. Dedup providers+consumers by ``contract_id`` into Endpoint join
    nodes. Provider metadata is canonical (the route *defines* the contract);
    ``raw_path_samples`` keeps a few originals for display. Sorted by
    contract_id for determinism."""
    by_id: dict[str, list[Contract]] = {}
    for c in (*providers, *consumers):
        by_id.setdefault(c.contract_id, []).append(c)
    endpoints: list[Endpoint] = []
    for contract_id in sorted(by_id):
        members = by_id[contract_id]
        canonical = next((m for m in members if m.role == ContractRole.PROVIDER), members[0])
        samples = sorted({m.raw_path for m in members if m.raw_path})[:3]
        endpoints.append(
            Endpoint(
                contract_id=contract_id,
                protocol=canonical.protocol,
                method=canonical.method,
                normalized_path=canonical.normalized_path,
                raw_path_samples=", ".join(samples),
                framework=next((m.framework for m in members if m.framework), ""),
                spec_backed=any(m.spec_backed for m in members),
            )
        )
    return endpoints


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


def _build_semantic_index(store: LadybugStore, index_path: Path) -> None:
    """DEC-042: build the opt-in ONNX vector index next to the lexical one.

    No-op (silently) when the ``[semantic]`` extra or a local model is absent —
    the NL query then runs two-retriever and says so. Importing inside the
    function keeps the ``[semantic]`` deps off the core import path."""
    from forensic_deepdive.query.semantic import build_semantic_index

    build_semantic_index(index_path.parent, records_from_store(store))


def default_phases() -> list[Phase]:
    """The v0.2 phase DAG. ``BuildGraphPhase`` is in the list but is a no-op
    unless ``ExtractConfig.build_graph_db=True`` (DEC-013)."""
    return [
        InventoryPhase(),
        ParsePhase(),
        StaticPhase(),
        ContractPhase(),
        FlattenPhase(),
        HistoryPhase(),
        BuildGraphPhase(),
        EmitPhase(),
    ]
