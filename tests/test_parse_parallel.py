"""Tests for parse-phase parallelism (v0.3 Item B, DEC-035).

The load-bearing property is **determinism under parallelism**: artifacts and
the parse record lists must be byte-identical regardless of worker count or the
order workers happen to finish in. Plus the operational guards — small-repo
serial fallback, ``--workers 1`` serial path, and worker exceptions surfacing
with the offending file path (never a silent drop).
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
    WorkerParseError,
    parse_tasks,
    resolve_worker_count,
)

FIXTURES = Path(__file__).parent / "fixtures"
_CONTRACT = ("MAP.md", "HOTPATHS.md", "ARCHAEOLOGY.md", "MENTAL_MODEL.md", "AGENT_BRIEF.md")
_POLYGLOT = (
    "python_sample",
    "dart_sample",
    "c_sample",
    "swift_sample",
    "typescript_sample",
    "javascript_sample",
    "java_sample",
    "go_sample",
)


def _polyglot_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for sample in _POLYGLOT:
        shutil.copytree(FIXTURES / sample, root / sample)
    return root


def _parse_records(repo: Path, out: Path, **cfg_kw: object) -> list[tuple]:
    cfg = ExtractConfig(repo_path=repo, output_dir=out, **cfg_kw)  # type: ignore[arg-type]
    ctx = Context(config=cfg)
    ctx.put(InventoryPhase.name, InventoryPhase().run(ctx))
    out_parse = ParsePhase().run(ctx)
    # A flat, comparable projection of every record the phase produced.
    return (
        [(t.rel_path, t.name, t.kind, t.category, t.line, t.parent) for t in out_parse.tags]
        + [("IMP", i.rel_path, i.module_path, i.line) for i in out_parse.imports]
        + [
            ("INH", h.rel_path, h.child_qn_local, h.parent_name, h.kind)
            for h in out_parse.inheritance
        ]
    )


# ---------------------------------------------------------------------------
# resolve_worker_count
# ---------------------------------------------------------------------------


def test_resolve_worker_count() -> None:
    assert resolve_worker_count(1) == 1
    assert resolve_worker_count(4) == 4
    assert resolve_worker_count(0) == 1  # clamped to >= 1
    assert resolve_worker_count(-3) == 1
    auto = resolve_worker_count(None)
    assert auto >= 1
    assert auto <= 16  # GitNexus cap


# ---------------------------------------------------------------------------
# parse_tasks: serial vs parallel produce the same outcomes
# ---------------------------------------------------------------------------


def test_parse_tasks_empty_is_noop() -> None:
    assert parse_tasks([], workers=4, parallel=True) == []


def test_parse_tasks_serial_and_parallel_agree() -> None:
    greeter = FIXTURES / "python_sample" / "greeter.py"
    app = FIXTURES / "python_sample" / "app.py"
    tasks = [
        (str(greeter), "greeter.py", "python", "sha-g"),
        (str(app), "app.py", "python", "sha-a"),
    ]
    serial = {o[0]: o for o in parse_tasks(tasks, workers=1, parallel=False)}
    parallel = {o[0]: o for o in parse_tasks(tasks, workers=2, parallel=True)}
    assert serial.keys() == parallel.keys()
    for rel in serial:
        s_rel, s_lang, s_sha, s_res = serial[rel]
        p_rel, p_lang, p_sha, p_res = parallel[rel]
        assert (s_rel, s_lang, s_sha) == (p_rel, p_lang, p_sha)
        assert [t.name for t in s_res.tags] == [t.name for t in p_res.tags]


def test_worker_exception_surfaces_offending_file() -> None:
    tasks = [(str(FIXTURES / "does_not_exist.py"), "ghost.py", "python", "sha")]
    with pytest.raises(WorkerParseError) as excinfo:
        parse_tasks(tasks, workers=2, parallel=True)
    assert excinfo.value.rel_path == "ghost.py"


# ---------------------------------------------------------------------------
# ParsePhase: determinism across worker counts
# ---------------------------------------------------------------------------


def test_parse_records_identical_serial_vs_parallel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _polyglot_repo(tmp_path / "poly")
    out = tmp_path / "out"
    # Force the pool on the small fixture by lowering the threshold. Cache off
    # so BOTH runs actually parse (no warm-hit shortcut).
    monkeypatch.setattr(pc, "PARALLEL_MIN_FILES", 1)
    monkeypatch.setattr("forensic_deepdive.pipeline.phases.PARALLEL_MIN_FILES", 1)

    serial = _parse_records(repo, out, use_parse_cache=False, workers=1)
    parallel = _parse_records(repo, out, use_parse_cache=False, workers=4)
    assert serial == parallel
    assert serial  # the polyglot fixture really did produce records


def test_small_repo_uses_serial_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Below PARALLEL_MIN_FILES the pool must NOT be constructed, even with
    workers > 1 — spawn overhead would dominate."""
    repo = _polyglot_repo(tmp_path / "poly")  # 8 files, << 200
    out = tmp_path / "out"

    def _boom(*args: object, **kwargs: object):  # pragma: no cover - must not run
        raise AssertionError("ProcessPoolExecutor must not be used on a small repo")

    monkeypatch.setattr(pc, "ProcessPoolExecutor", _boom)
    # Default threshold (200) is in effect; workers=4 but 8 files → serial.
    _parse_records(repo, out, use_parse_cache=False, workers=4)


# ---------------------------------------------------------------------------
# End-to-end: byte-identical artifacts across worker counts (PRD §4.2 / §3.5)
# ---------------------------------------------------------------------------


def test_artifacts_byte_identical_workers_1_vs_4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pc, "PARALLEL_MIN_FILES", 1)
    monkeypatch.setattr("forensic_deepdive.pipeline.phases.PARALLEL_MIN_FILES", 1)

    # Two fresh copies with the SAME leaf name so repo_name (embedded in MAP.md
    # etc.) matches; both cold so every file is parsed.
    repo1 = _polyglot_repo(tmp_path / "a" / "poly")
    repo4 = _polyglot_repo(tmp_path / "b" / "poly")

    r1 = run_extract(repo1, flatten=False, write_editor_shims=False, workers=1)
    r4 = run_extract(repo4, flatten=False, write_editor_shims=False, workers=4)

    for name in _CONTRACT:
        assert (r1.output_dir / name).read_bytes() == (r4.output_dir / name).read_bytes(), name
