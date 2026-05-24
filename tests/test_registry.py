"""Tests for the multi-repo registry (DEC-018)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from forensic_deepdive.registry import (
    REGISTRY_FORMAT_VERSION,
    Registry,
    RegistryEntry,
    default_registry_path,
    load,
    register,
    remove,
    save,
)


@pytest.fixture
def registry_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "registry.json"
    monkeypatch.setenv("FORENSIC_REGISTRY", str(path))
    return path


def test_load_returns_empty_when_file_missing(registry_path: Path) -> None:
    r = load()
    assert r.version == REGISTRY_FORMAT_VERSION
    assert r.repos == ()


def test_save_and_load_round_trip(registry_path: Path) -> None:
    entry = RegistryEntry(
        name="foo",
        repo_path="/abs/foo",
        graph_db_path="/abs/foo/.deepdive/graph.lbug",
        last_extracted_at="2026-05-25T12:00:00+00:00",
    )
    save(Registry(version=REGISTRY_FORMAT_VERSION, repos=(entry,)))
    r = load()
    assert r.repos == (entry,)


def test_register_inserts_new_repo(registry_path: Path, tmp_path: Path) -> None:
    repo = tmp_path / "myrepo"
    repo.mkdir()
    e = register(repo, repo / ".lbug", now=datetime(2026, 5, 25, tzinfo=UTC))
    assert e.name == "myrepo"
    assert e.last_extracted_at == "2026-05-25T00:00:00+00:00"
    r = load()
    assert len(r.repos) == 1
    assert r.repos[0].name == "myrepo"


def test_register_replaces_existing_by_name(registry_path: Path, tmp_path: Path) -> None:
    repo = tmp_path / "myrepo"
    repo.mkdir()
    register(repo, repo / ".lbug", now=datetime(2026, 1, 1, tzinfo=UTC))
    register(repo, repo / ".lbug", now=datetime(2026, 5, 25, tzinfo=UTC))
    r = load()
    assert len(r.repos) == 1
    assert r.repos[0].last_extracted_at == "2026-05-25T00:00:00+00:00"


def test_register_keeps_other_repos(registry_path: Path, tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    register(a, None)
    register(b, None)
    r = load()
    assert {x.name for x in r.repos} == {"a", "b"}


def test_remove_returns_false_when_absent(registry_path: Path) -> None:
    assert remove("nope") is False


def test_remove_drops_entry(registry_path: Path, tmp_path: Path) -> None:
    repo = tmp_path / "myrepo"
    repo.mkdir()
    register(repo, None)
    assert remove("myrepo") is True
    assert load().repos == ()


def test_default_registry_path_honors_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORENSIC_REGISTRY", "/tmp/x.json")
    assert default_registry_path() == Path("/tmp/x.json")


def test_default_registry_path_falls_back_to_home(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FORENSIC_REGISTRY", raising=False)
    p = default_registry_path()
    assert p.name == "registry.json"
    assert p.parent.name == ".deepdive"


def test_corrupt_registry_treated_as_empty(registry_path: Path) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text("not json at all", encoding="utf-8")
    r = load()
    assert r.repos == ()


def test_register_uses_resolved_paths(registry_path: Path, tmp_path: Path) -> None:
    """register stores absolute resolved paths so the registry survives
    cwd changes / symlink rewrites."""
    repo = tmp_path / "myrepo"
    repo.mkdir()
    e = register(Path("./" + repo.name), None)
    # On Windows the resolved path is normalized to absolute.
    assert Path(e.repo_path).is_absolute()


def test_extract_auto_registers_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end: run_extract registers the repo in the global registry."""
    import shutil

    from forensic_deepdive.pipeline import run_extract

    monkeypatch.setenv("FORENSIC_REGISTRY", str(tmp_path / "registry.json"))
    repo = tmp_path / "py"
    shutil.copytree(Path("tests/fixtures/python_sample"), repo)
    run_extract(repo, write_editor_shims=False)
    r = load()
    names = [e.name for e in r.repos]
    assert "py" in names
