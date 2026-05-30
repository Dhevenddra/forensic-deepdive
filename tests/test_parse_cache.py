"""Tests for the content-addressed parse cache (v0.3 Item A, DEC-036).

Covers the PRD §4.1 test matrix: cold miss populates; warm hit skips Tree-sitter;
a one-file change re-parses exactly one file; a removed file drops from the
records and shows in the manifest diff; a ``PARSER_VERSION`` bump forces a full
re-parse; and cold-vs-warm artifacts are byte-identical (determinism invariant).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from forensic_deepdive.pipeline import (
    Context,
    ExtractConfig,
    InventoryPhase,
    ParsePhase,
    run_extract,
)
from forensic_deepdive.static import parse_cache as pc
from forensic_deepdive.static.parse_cache import (
    ParseCache,
    ParseResult,
    content_hash,
    diff_manifest,
    parse_and_extract,
    parse_cache_dir,
    read_manifest,
    write_manifest,
)

FIXTURES = Path(__file__).parent / "fixtures"
_CONTRACT = ("MAP.md", "HOTPATHS.md", "ARCHAEOLOGY.md", "MENTAL_MODEL.md", "AGENT_BRIEF.md")


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "sample_repo"
    shutil.copytree(FIXTURES / "python_sample", repo)
    return repo


def _seeded_ctx(repo: Path, tmp_path: Path, **cfg_kw: object) -> Context:
    cfg = ExtractConfig(repo_path=repo, output_dir=tmp_path / "out", **cfg_kw)  # type: ignore[arg-type]
    ctx = Context(config=cfg)
    ctx.put(InventoryPhase.name, InventoryPhase().run(ctx))
    return ctx


class _ParseSpy:
    """Counts how many times Tree-sitter is actually invoked, by wrapping
    ``parse_cache.parse_source`` (the single call site inside
    ``parse_and_extract``)."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.count = 0
        real = pc.parse_source

        def spy(source: bytes, language: str):  # type: ignore[no-untyped-def]
            self.count += 1
            return real(source, language)

        monkeypatch.setattr(pc, "parse_source", spy)


# ---------------------------------------------------------------------------
# Low-level pieces: hashing, keys, serialization round-trip
# ---------------------------------------------------------------------------


def test_content_hash_is_deterministic_and_content_sensitive() -> None:
    assert content_hash(b"abc") == content_hash(b"abc")
    assert content_hash(b"abc") != content_hash(b"abd")


def test_entry_key_distinguishes_language_and_parser_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sha = content_hash(b"x")
    k_py = pc._entry_key(sha, "python")
    k_ts = pc._entry_key(sha, "typescript")
    assert k_py != k_ts  # same bytes, different grammar → different entry
    monkeypatch.setattr(pc, "PARSER_VERSION", pc.PARSER_VERSION + 1)
    assert pc._entry_key(sha, "python") != k_py  # version bump → different key


def test_cache_put_get_round_trip_restamps_rel_path(tmp_path: Path) -> None:
    cache = ParseCache(tmp_path / "parse")
    source = (FIXTURES / "python_sample" / "greeter.py").read_bytes()
    sha = content_hash(source)
    fresh = parse_and_extract(
        FIXTURES / "python_sample" / "greeter.py", "greeter.py", "python", source
    )
    assert fresh.tags  # the fixture defines symbols
    cache.put(sha, "python", fresh)

    # Re-stamped under a DIFFERENT rel_path — content-addressed entries are
    # path-independent and re-stamped on read.
    got = cache.get("sub/dir/greeter.py", sha, "python")
    assert got is not None
    assert {t.rel_path for t in got.tags} == {"sub/dir/greeter.py"}
    # Everything except rel_path matches the fresh extraction exactly.
    assert [(t.name, t.kind, t.category, t.line, t.parent) for t in got.tags] == [
        (t.name, t.kind, t.category, t.line, t.parent) for t in fresh.tags
    ]
    assert [i.module_path for i in got.imports] == [i.module_path for i in fresh.imports]


def test_cache_miss_returns_none(tmp_path: Path) -> None:
    cache = ParseCache(tmp_path / "parse")
    assert cache.get("a.py", content_hash(b"nope"), "python") is None


def test_cache_get_treats_corrupt_entry_as_miss(tmp_path: Path) -> None:
    cache = ParseCache(tmp_path / "parse")
    sha = content_hash(b"data")
    cache.put(sha, "python", ParseResult(rel_path="a.py", tags=(), imports=(), inheritance=()))
    # Corrupt the on-disk entry.
    entry = cache._entry_path(sha, "python")
    entry.write_text("{not json", encoding="utf-8")
    assert cache.get("a.py", sha, "python") is None


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def test_manifest_round_trip_and_diff(tmp_path: Path) -> None:
    root = tmp_path / "parse"
    write_manifest(root, {"a.py": "h1", "b.py": "h2", "c.py": "h3"})
    assert read_manifest(root) == {"a.py": "h1", "b.py": "h2", "c.py": "h3"}

    new = {"a.py": "h1", "b.py": "CHANGED", "d.py": "h4"}
    diff = diff_manifest(read_manifest(root), new)
    assert diff.changed == frozenset({"b.py"})
    assert diff.added == frozenset({"d.py"})
    assert diff.removed == frozenset({"c.py"})
    assert not diff.is_empty


def test_read_manifest_missing_is_empty(tmp_path: Path) -> None:
    assert read_manifest(tmp_path / "nope") == {}
    assert diff_manifest({}, {}).is_empty


# ---------------------------------------------------------------------------
# ParsePhase: the incremental behavior
# ---------------------------------------------------------------------------


def test_cold_run_parses_every_file_and_populates_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _make_repo(tmp_path)
    source_paths = {
        sf.rel_path
        for sf in InventoryPhase().run(_seeded_ctx(repo, tmp_path)).inventory.source_files
    }
    spy = _ParseSpy(monkeypatch)

    out = ParsePhase().run(_seeded_ctx(repo, tmp_path))

    assert out.parsed_count == len(source_paths)
    assert out.cached_count == 0
    assert spy.count == len(source_paths)  # every file hit Tree-sitter
    # First ever run: previous manifest empty → every source file is "added".
    assert out.diff is not None
    assert out.diff.added == frozenset(source_paths)
    assert not out.diff.changed and not out.diff.removed
    # Cache + manifest now exist on disk.
    cache_root = parse_cache_dir(repo)
    assert (cache_root / "manifest.json").is_file()
    assert list(cache_root.glob("*.json"))  # at least one entry written


def test_warm_run_serves_from_cache_without_touching_tree_sitter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _make_repo(tmp_path)
    cold = ParsePhase().run(_seeded_ctx(repo, tmp_path))  # populate

    spy = _ParseSpy(monkeypatch)
    warm = ParsePhase().run(_seeded_ctx(repo, tmp_path))

    assert spy.count == 0  # nothing re-parsed
    assert warm.parsed_count == 0
    assert warm.cached_count == cold.parsed_count
    assert warm.diff is not None and warm.diff.is_empty
    # Identical records (modulo ordering already fixed by source_files sort).
    assert [(t.rel_path, t.name, t.kind, t.line) for t in warm.tags] == [
        (t.rel_path, t.name, t.kind, t.line) for t in cold.tags
    ]


def test_one_changed_file_reparses_exactly_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _make_repo(tmp_path)
    ParsePhase().run(_seeded_ctx(repo, tmp_path))  # populate

    (repo / "greeter.py").write_text("def brand_new_function():\n    return 1\n", encoding="utf-8")
    spy = _ParseSpy(monkeypatch)
    out = ParsePhase().run(_seeded_ctx(repo, tmp_path))

    assert spy.count == 1
    assert out.parsed_count == 1
    assert out.diff is not None
    assert out.diff.changed == frozenset({"greeter.py"})
    assert any(t.name == "brand_new_function" for t in out.tags)


def test_removed_file_drops_from_records_and_shows_in_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _make_repo(tmp_path)
    ParsePhase().run(_seeded_ctx(repo, tmp_path))  # populate

    (repo / "app.py").unlink()
    spy = _ParseSpy(monkeypatch)
    out = ParsePhase().run(_seeded_ctx(repo, tmp_path))

    assert spy.count == 0  # remaining files still cached
    assert out.diff is not None
    assert out.diff.removed == frozenset({"app.py"})
    assert all(t.rel_path != "app.py" for t in out.tags)


def test_parser_version_bump_forces_full_reparse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _make_repo(tmp_path)
    cold = ParsePhase().run(_seeded_ctx(repo, tmp_path))  # populate at version N

    monkeypatch.setattr(pc, "PARSER_VERSION", pc.PARSER_VERSION + 1)
    spy = _ParseSpy(monkeypatch)
    out = ParsePhase().run(_seeded_ctx(repo, tmp_path))

    assert spy.count == cold.parsed_count  # every file re-parsed under new key
    assert out.cached_count == 0


def test_cache_disabled_writes_no_cache_and_reports_no_diff(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    out = ParsePhase().run(_seeded_ctx(repo, tmp_path, use_parse_cache=False))
    assert out.diff is None
    assert out.cached_count == 0
    assert not parse_cache_dir(repo).exists()


def test_identical_files_share_one_cache_entry(tmp_path: Path) -> None:
    repo = tmp_path / "dups"
    repo.mkdir()
    body = "def helper():\n    return 42\n"
    (repo / "a.py").write_text(body, encoding="utf-8")
    (repo / "b.py").write_text(body, encoding="utf-8")  # byte-identical content

    ParsePhase().run(_seeded_ctx(repo, tmp_path))
    entries = list(parse_cache_dir(repo).glob("*.json"))
    # Two identical (content, language) files → exactly one content-addressed
    # entry. (manifest.json is not matched by ``*.json`` glob below.)
    data_entries = [p for p in entries if p.name != "manifest.json"]
    assert len(data_entries) == 1


# ---------------------------------------------------------------------------
# Determinism invariant (PRD §3.5): cold-vs-warm byte-identical artifacts
# ---------------------------------------------------------------------------


def test_cold_vs_warm_artifacts_are_byte_identical(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    cold = run_extract(repo, flatten=False, write_editor_shims=False)
    cold_bytes = {n: (cold.output_dir / n).read_bytes() for n in _CONTRACT}

    # ``force`` re-runs the DAG; the parse cache hits transparently this time.
    warm = run_extract(repo, flatten=False, write_editor_shims=False, force=True)
    assert not warm.cache_hit
    for name in _CONTRACT:
        assert (warm.output_dir / name).read_bytes() == cold_bytes[name], name
