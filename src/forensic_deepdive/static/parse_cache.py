"""Content-addressed parse cache (v0.3 Item A, DEC-036).

The parse half of the pipeline (Tree-sitter parse + tag / import / inheritance
extraction) is the cold-extract bottleneck (DEC-033: ~930 s on Omi, dominated
by parsing ~5,500 files). A one-file edit forces a full re-parse because the
v0.1 cache fingerprint is whole-extract (see ``cache.py``).

This module makes the *parse* incremental. For every analyzed source file we
compute a content hash and look the file up in a content-addressed store keyed
by ``(content_sha256, language, PARSER_VERSION, tags.scm version)``. A hit
returns the file's previously-extracted ``Tag`` / ``Import`` /
``InheritanceRecord`` records without touching Tree-sitter; a miss parses once
and writes the entry.

**v0.3 scope boundary (DEC-036):** this is incremental *parse*, not incremental
*graph*. The symbol graph + PageRank are still rebuilt from the union of cached
and freshly-parsed Tags on every run. Invalidating only the affected graph edges
is v1.0 work. Parsing is the bottleneck (DEC-033), so skipping it captures ~all
of the win without the hard graph-diff problem.

Design notes
------------
* **Content-addressed, path-independent.** Cache entries are stored by content
  hash, so two identical files anywhere in the repo (empty ``__init__.py``,
  repeated license-header stubs) share one entry. The stored records have their
  ``rel_path`` stripped; :meth:`ParseCache.get` re-stamps it from the lookup
  argument. ``language`` is folded into the key because the same bytes parse
  differently as ``.ts`` (typescript) vs ``.tsx`` (tsx).
* **Inspectable, version-portable.** Entries are JSON over explicit
  ``to_dict`` / ``from_dict`` (no pickle) so a stale cache is debuggable and a
  schema change is a visible format change, per PRD §4.1.
* **Invalidation.** ``PARSER_VERSION`` (this module) is a global bump for any
  change to the parse / extraction *code* that changes output; the per-language
  ``tags.scm`` hash auto-invalidates a language's entries when its query string
  changes. Both are in the key.
* **Atomic writes.** Entries are written to a temp file and ``os.replace``-d into
  place so a crash (or a future parallel writer — Item B / DEC-035) never leaves
  a half-written entry that would later be read as a corrupt miss.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from forensic_deepdive.cache import CACHE_DIRNAME
from forensic_deepdive.static.imports import Import, ImportedName, extract_imports
from forensic_deepdive.static.inheritance import InheritanceRecord, extract_inheritance
from forensic_deepdive.static.injection import InjectionRecord, extract_injection
from forensic_deepdive.static.method_calls import MethodCall, extract_method_calls
from forensic_deepdive.static.parse import ParsedFile, parse_source
from forensic_deepdive.static.persistence import PersistenceRecord, extract_persistence
from forensic_deepdive.static.tags import TAGS_SCM, Tag, extract_tags

# Bump when the parse / extraction *code* changes in a way that alters the
# emitted Tag / Import / InheritanceRecord records (e.g. a new field, a changed
# import-walk heuristic). A bump invalidates every cached entry across all
# languages. The per-language tags.scm hash (``_scm_version``) covers query
# edits automatically, so query-only changes do NOT need a bump here.
#   v2 (DEC-037): ParseResult gained ``method_calls``.
#   v3 (DEC-050): TS/TSX heritage extraction widened (abstract classes,
#       interface→interface extends, generic_type / member_expression targets).
#   v4 (DEC-059): + injection / persistence records.
PARSER_VERSION = 5  # DEC-064 (v0.6 Step 1): ORM Django/SQLAlchemy disambiguation

# Subdirectory layout under the repo's gitignored cache dir:
#   .forensic-deepdive/cache/parse/<entry_key>.json   — one per (content, lang)
#   .forensic-deepdive/cache/parse/manifest.json      — {rel_path: content_sha}
_PARSE_SUBDIR = ("cache", "parse")
MANIFEST_FILENAME = "manifest.json"


def parse_cache_dir(repo_path: Path) -> Path:
    """Return the parse-cache directory for *repo_path* (gitignored)."""
    return Path(repo_path) / CACHE_DIRNAME / Path(*_PARSE_SUBDIR)


def content_hash(data: bytes) -> str:
    """Hex SHA-256 of raw file bytes — the content address of one file."""
    return hashlib.sha256(data).hexdigest()


@cache
def _scm_version(language: str) -> str:
    """Short hash of *language*'s ``tags.scm`` query string.

    Changing a language's query changes this digest, which changes every entry
    key for that language — its cached entries become misses and re-parse. Cached
    on ``language`` (the TAGS_SCM strings are module constants)."""
    scm = TAGS_SCM.get(language, "")
    return hashlib.sha256(scm.encode("utf-8")).hexdigest()[:16]


def _entry_key(content_sha: str, language: str) -> str:
    """The content-addressed entry identity.

    Reads ``PARSER_VERSION`` from the module global at call time so a test (or a
    real bump) that rebinds it invalidates the whole cache deterministically."""
    digest = hashlib.sha256()
    digest.update(content_sha.encode("ascii"))
    digest.update(b"\0")
    digest.update(language.encode("utf-8"))
    digest.update(b"\0")
    digest.update(str(PARSER_VERSION).encode("ascii"))
    digest.update(b"\0")
    digest.update(_scm_version(language).encode("ascii"))
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Per-file parse result (path-independent records re-stamped on cache read)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Everything the static layer extracts from one source file.

    This is the unit the parse cache stores and the unit an Item B worker will
    return (DEC-035) — deliberately plain dataclasses, never a Tree-sitter
    ``Tree`` (unpicklable)."""

    rel_path: str
    tags: tuple[Tag, ...]
    imports: tuple[Import, ...]
    inheritance: tuple[InheritanceRecord, ...]
    method_calls: tuple[MethodCall, ...] = ()  # DEC-037 — dotted method calls
    injection: tuple[InjectionRecord, ...] = ()  # DEC-059 — DI sites
    persistence: tuple[PersistenceRecord, ...] = ()  # DEC-059 — ORM model→table


def parse_and_extract(abs_path: Path, rel_path: str, language: str, source: bytes) -> ParseResult:
    """Parse *source* and extract tags + imports + inheritance in one pass.

    The single entry point for "turn bytes into records", shared by the cache
    miss path here and (in Item B) the process-pool worker. Pure given its
    inputs — no disk read, no cache — so it is trivially parallelizable."""
    tree = parse_source(source, language)
    parsed = ParsedFile(
        path=abs_path,
        rel_path=rel_path,
        language=language,
        source=source,
        tree=tree,
    )
    return ParseResult(
        rel_path=rel_path,
        tags=tuple(extract_tags(parsed)),
        imports=tuple(extract_imports(parsed)),
        inheritance=tuple(extract_inheritance(parsed)),
        method_calls=tuple(extract_method_calls(parsed)),
        injection=tuple(extract_injection(parsed)),
        persistence=tuple(extract_persistence(parsed)),
    )


# ---------------------------------------------------------------------------
# Parallel parse (v0.3 Item B, DEC-035)
# ---------------------------------------------------------------------------
#
# Parsing is GIL-bound Python AST-walking, so threads don't help — we use
# processes. The parent computes the manifest + consults the cache (the cheap,
# I/O-bound half) and hands the *misses* — the expensive parse work — to a
# ProcessPoolExecutor. Workers re-read the file and run the pure
# ``parse_and_extract`` (re-read is page-cache-warm; this keeps IPC to plain
# strings instead of pickling every file's bytes). Cache hits never touch the
# pool. Determinism is the parent's job: it reassembles results in sorted
# ``rel_path`` order (see ``ParsePhase``), which reproduces the serial order
# exactly and preserves each file's intra-file record order — byte-identical to
# the Item A serial path regardless of worker count or completion order.

# Below this many files-to-parse, the serial path wins: process spawn + IPC
# overhead dominates the parse on small repos and fixtures. Module-level so a
# test can lower it to exercise the pool on a small fixture.
PARALLEL_MIN_FILES = 200

# One unit of parse work shipped to a worker: (abs_path, rel_path, language,
# content_sha). All plain strings — trivially picklable for the spawn start
# method (Windows / macOS).
ParseTask = tuple[str, str, str, str]

# What a worker hands back: (rel_path, language, content_sha, ParseResult). The
# sha + language ride along so the parent can write the cache entry in one place
# (single cache writer — simpler than concurrent worker writes, and the atomic
# ``ParseCache.put`` would tolerate concurrency anyway).
ParseOutcome = tuple[str, str, str, ParseResult]


def resolve_worker_count(configured: int | None) -> int:
    """Effective worker count. ``None`` ⇒ ``min(cpu-1, 16)`` (GitNexus's cap),
    clamped to ≥ 1; an explicit value is honored (clamped to ≥ 1)."""
    if configured is not None:
        return max(1, configured)
    return max(1, min((os.cpu_count() or 1) - 1, 16))


def _parse_one(task: ParseTask) -> ParseOutcome:
    """Worker entry point: re-read the file and parse it. Module-level so the
    ProcessPoolExecutor can pickle it under the spawn start method."""
    abs_path, rel_path, language, sha = task
    data = Path(abs_path).read_bytes()
    return (rel_path, language, sha, parse_and_extract(Path(abs_path), rel_path, language, data))


class WorkerParseError(RuntimeError):
    """A worker failed to parse a specific file. Carries the offending path so
    the failure is never a silent drop (PRD §4.2)."""

    def __init__(self, rel_path: str) -> None:
        super().__init__(f"parse worker failed for {rel_path!r}")
        self.rel_path = rel_path


def parse_tasks(tasks: list[ParseTask], *, workers: int, parallel: bool) -> list[ParseOutcome]:
    """Run *tasks* serially or across a process pool, returning outcomes in
    completion order (the caller sorts for determinism).

    ``parallel`` is decided by the caller (it knows the file count + worker
    count). When parallel, a worker exception is re-raised as
    :class:`WorkerParseError` naming the file rather than swallowed."""
    if not tasks:
        return []
    if not parallel or workers <= 1:
        return [_parse_one(t) for t in tasks]

    outcomes: list[ParseOutcome] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        future_to_rel = {pool.submit(_parse_one, t): t[1] for t in tasks}
        for future in as_completed(future_to_rel):
            rel = future_to_rel[future]
            try:
                outcomes.append(future.result())
            except Exception as exc:  # noqa: BLE001 — re-raised with file context
                raise WorkerParseError(rel) from exc
    return outcomes


# ---------------------------------------------------------------------------
# Serialization (explicit, path-independent — rel_path is re-stamped on read)
# ---------------------------------------------------------------------------


def _tag_to_dict(t: Tag) -> dict:
    return {
        "name": t.name,
        "kind": t.kind,
        "category": t.category,
        "line": t.line,
        "language": t.language,
        "parent": t.parent,
        "enclosing_scope": t.enclosing_scope,
    }


def _tag_from_dict(d: dict, rel_path: str) -> Tag:
    return Tag(
        rel_path=rel_path,
        name=d["name"],
        kind=d["kind"],
        category=d["category"],
        line=d["line"],
        language=d["language"],
        parent=d.get("parent", ""),
        enclosing_scope=d.get("enclosing_scope", ""),
    )


def _import_to_dict(i: Import) -> dict:
    return {
        "module_path": i.module_path,
        "language": i.language,
        "line": i.line,
        "module_alias": i.module_alias,
        "imported_names": [{"name": n.name, "alias": n.alias} for n in i.imported_names],
        "is_reexport": i.is_reexport,
    }


def _import_from_dict(d: dict, rel_path: str) -> Import:
    return Import(
        rel_path=rel_path,
        module_path=d["module_path"],
        language=d["language"],
        line=d["line"],
        module_alias=d.get("module_alias", ""),
        imported_names=tuple(
            ImportedName(name=n["name"], alias=n.get("alias", ""))
            for n in d.get("imported_names", ())
        ),
        is_reexport=d.get("is_reexport", False),
    )


def _inheritance_to_dict(r: InheritanceRecord) -> dict:
    return {
        "child_qn_local": r.child_qn_local,
        "parent_name": r.parent_name,
        "kind": r.kind,
        "language": r.language,
        "line": r.line,
    }


def _inheritance_from_dict(d: dict, rel_path: str) -> InheritanceRecord:
    return InheritanceRecord(
        rel_path=rel_path,
        child_qn_local=d["child_qn_local"],
        parent_name=d["parent_name"],
        kind=d["kind"],
        language=d["language"],
        line=d["line"],
    )


def _method_call_to_dict(m: MethodCall) -> dict:
    return {
        "receiver": m.receiver,
        "method": m.method,
        "enclosing_scope": m.enclosing_scope,
        "line": m.line,
        "language": m.language,
    }


def _method_call_from_dict(d: dict, rel_path: str) -> MethodCall:
    return MethodCall(
        rel_path=rel_path,
        receiver=d["receiver"],
        method=d["method"],
        enclosing_scope=d.get("enclosing_scope", ""),
        line=d["line"],
        language=d["language"],
    )


def _injection_to_dict(r: InjectionRecord) -> dict:
    return {
        "injector_qn_local": r.injector_qn_local,
        "injected_type_name": r.injected_type_name,
        "kind": r.kind,
        "language": r.language,
        "line": r.line,
    }


def _injection_from_dict(d: dict, rel_path: str) -> InjectionRecord:
    return InjectionRecord(
        rel_path=rel_path,
        injector_qn_local=d["injector_qn_local"],
        injected_type_name=d["injected_type_name"],
        kind=d["kind"],
        language=d["language"],
        line=d["line"],
    )


def _persistence_to_dict(r: PersistenceRecord) -> dict:
    return {
        "model_qn_local": r.model_qn_local,
        "table_name": r.table_name,
        "orm": r.orm,
        "framework": r.framework,
        "language": r.language,
        "line": r.line,
        "literal": r.literal,
    }


def _persistence_from_dict(d: dict, rel_path: str) -> PersistenceRecord:
    return PersistenceRecord(
        rel_path=rel_path,
        model_qn_local=d["model_qn_local"],
        table_name=d["table_name"],
        orm=d["orm"],
        framework=d["framework"],
        language=d["language"],
        line=d["line"],
        literal=d["literal"],
    )


# ---------------------------------------------------------------------------
# The cache
# ---------------------------------------------------------------------------


class ParseCache:
    """Content-addressed on-disk store of per-file parse results.

    One JSON file per ``(content, language, PARSER_VERSION, scm)`` entry under
    :func:`parse_cache_dir`. Stateless across calls beyond the filesystem — safe
    to construct fresh per run."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    def _entry_path(self, content_sha: str, language: str) -> Path:
        return self._root / f"{_entry_key(content_sha, language)}.json"

    def get(self, rel_path: str, content_sha: str, language: str) -> ParseResult | None:
        """Return the cached :class:`ParseResult` for this file, re-stamped with
        *rel_path*, or ``None`` on a miss (absent, unreadable, or corrupt)."""
        path = self._entry_path(content_sha, language)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        try:
            # Defensive: a hash that doesn't match its own payload means a
            # corrupt or tampered entry — treat as a miss and re-parse.
            if payload["content_sha"] != content_sha or payload["language"] != language:
                return None
            return ParseResult(
                rel_path=rel_path,
                tags=tuple(_tag_from_dict(t, rel_path) for t in payload["tags"]),
                imports=tuple(_import_from_dict(i, rel_path) for i in payload["imports"]),
                inheritance=tuple(
                    _inheritance_from_dict(h, rel_path) for h in payload["inheritance"]
                ),
                method_calls=tuple(
                    _method_call_from_dict(m, rel_path) for m in payload.get("method_calls", ())
                ),
                injection=tuple(
                    _injection_from_dict(j, rel_path) for j in payload.get("injection", ())
                ),
                persistence=tuple(
                    _persistence_from_dict(p, rel_path) for p in payload.get("persistence", ())
                ),
            )
        except (KeyError, TypeError):
            return None

    def put(self, content_sha: str, language: str, result: ParseResult) -> None:
        """Write *result* to the cache (path-independent — ``rel_path`` stripped).

        Atomic: writes a temp file in the cache dir then ``os.replace``-s it into
        place, so a concurrent reader never sees a half-written entry."""
        self._root.mkdir(parents=True, exist_ok=True)
        payload = {
            "content_sha": content_sha,
            "language": language,
            "parser_version": PARSER_VERSION,
            "scm_version": _scm_version(language),
            "tags": [_tag_to_dict(t) for t in result.tags],
            "imports": [_import_to_dict(i) for i in result.imports],
            "inheritance": [_inheritance_to_dict(h) for h in result.inheritance],
            "method_calls": [_method_call_to_dict(m) for m in result.method_calls],
            "injection": [_injection_to_dict(j) for j in result.injection],
            "persistence": [_persistence_to_dict(p) for p in result.persistence],
        }
        text = json.dumps(payload, separators=(",", ":")) + "\n"
        dest = self._entry_path(content_sha, language)
        fd, tmp_name = tempfile.mkstemp(dir=self._root, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
            os.replace(tmp_name, dest)
        except OSError:
            # Best-effort cache write — a failure here must never break extract.
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)


# ---------------------------------------------------------------------------
# Merkle manifest + diff (drives reporting and removed-file detection)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ManifestDiff:
    """What changed between the previous run's manifest and this run's."""

    changed: frozenset[str] = field(default_factory=frozenset)  # same path, new content
    added: frozenset[str] = field(default_factory=frozenset)  # new path
    removed: frozenset[str] = field(default_factory=frozenset)  # path gone

    @property
    def is_empty(self) -> bool:
        return not (self.changed or self.added or self.removed)


def read_manifest(root: Path) -> dict[str, str]:
    """Load ``{rel_path: content_sha}`` from the parse-cache manifest, or ``{}``."""
    path = Path(root) / MANIFEST_FILENAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def write_manifest(root: Path, manifest: dict[str, str]) -> None:
    """Write the ``{rel_path: content_sha}`` manifest (sorted, atomic)."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    text = json.dumps(dict(sorted(manifest.items())), indent=2, sort_keys=True) + "\n"
    dest = root / MANIFEST_FILENAME
    fd, tmp_name = tempfile.mkstemp(dir=root, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp_name, dest)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)


def diff_manifest(old: dict[str, str], new: dict[str, str]) -> ManifestDiff:
    """Diff two ``{rel_path: content_sha}`` manifests."""
    old_keys = set(old)
    new_keys = set(new)
    added = new_keys - old_keys
    removed = old_keys - new_keys
    changed = {k for k in old_keys & new_keys if old[k] != new[k]}
    return ManifestDiff(
        changed=frozenset(changed),
        added=frozenset(added),
        removed=frozenset(removed),
    )
