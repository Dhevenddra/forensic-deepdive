"""End-to-end tests for the extract pipeline."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from forensic_deepdive.pipeline import run_extract

FIXTURES = Path(__file__).parent / "fixtures"
_CONTRACT = {
    "MAP.md",
    "HOTPATHS.md",
    "ARCHAEOLOGY.md",
    "MENTAL_MODEL.md",
    "AGENT_BRIEF.md",
}


def _make_repo(tmp_path: Path) -> Path:
    """Copy the python_sample fixture into a fresh, non-git temp directory."""
    repo = tmp_path / "sample_repo"
    shutil.copytree(FIXTURES / "python_sample", repo)
    return repo


def test_run_extract_produces_the_contract(tmp_path: Path) -> None:
    result = run_extract(_make_repo(tmp_path), flatten=False)
    assert not result.cache_hit
    assert set(result.artifacts) >= _CONTRACT
    codebase = result.output_dir
    for name in _CONTRACT:
        assert (codebase / name).is_file()
    assert (codebase / "AGENT_BRIEF.md").stat().st_size <= 5120


def test_run_extract_writes_shims_and_cache(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    result = run_extract(repo, flatten=False)
    assert (repo / "CLAUDE.md").is_file()
    assert (repo / ".forensic-deepdive" / "last_run.json").is_file()
    assert result.shims.written


def test_run_extract_cache_hit_on_unchanged_repo(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    assert not run_extract(repo, flatten=False).cache_hit
    assert run_extract(repo, flatten=False).cache_hit
    assert not run_extract(repo, flatten=False, force=True).cache_hit


def test_run_extract_cache_invalidated_by_change(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    run_extract(repo, flatten=False)
    (repo / "greeter.py").write_text("# changed\n", encoding="utf-8")
    assert not run_extract(repo, flatten=False).cache_hit


def test_run_extract_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        run_extract(tmp_path / "does_not_exist", flatten=False)


def test_run_extract_explicit_output_dir(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    out = tmp_path / "artifacts"
    result = run_extract(repo, out, flatten=False)
    assert result.output_dir == out
    assert (out / "AGENT_BRIEF.md").is_file()
