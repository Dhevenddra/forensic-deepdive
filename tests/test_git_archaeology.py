"""Tests for the git-archaeology Layer-3 backend.

Plain-git tests build a real temporary repo with `git`; the GitHub side is
exercised with a fake `Github` client so no network or token is needed.
"""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from forensic_deepdive.history import git_archaeology as ga
from forensic_deepdive.history.git_archaeology import (
    analyze_history,
    detect_github_repo,
    fetch_github_stats,
)


def _git(repo: Path, *args: str, env_extra: dict[str, str] | None = None) -> None:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _commit(
    repo: Path,
    *,
    author: str,
    email: str,
    message: str,
    date: str,
    files: dict[str, str],
) -> None:
    for name, content in files.items():
        (repo / name).write_text(content, encoding="utf-8")
    env = {
        "GIT_AUTHOR_NAME": author,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_NAME": author,
        "GIT_COMMITTER_EMAIL": email,
        "GIT_COMMITTER_DATE": date,
    }
    _git(repo, "add", "-A")
    _git(repo, "-c", "commit.gpgsign=false", "commit", "-m", message, env_extra=env)


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """A 3-commit repo: Alice ×2, Bob ×1; a.txt churned 3×, b.txt 1×."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _commit(
        repo,
        author="Alice",
        email="alice@example.com",
        message="add a",
        date="2020-01-01T00:00:00+00:00",
        files={"a.txt": "a1\n"},
    )
    _commit(
        repo,
        author="Alice",
        email="alice@example.com",
        message="edit a, add b",
        date="2021-06-15T00:00:00+00:00",
        files={"a.txt": "a2\n", "b.txt": "b1\n"},
    )
    _commit(
        repo,
        author="Bob",
        email="bob@example.com",
        message="edit a again",
        date="2022-12-31T00:00:00+00:00",
        files={"a.txt": "a3\n"},
    )
    return repo


# --- plain-git -------------------------------------------------------------


def test_non_git_directory(tmp_path: Path) -> None:
    result = analyze_history(tmp_path)
    assert result.is_git_repo is False
    assert result.total_commits == 0
    assert result.contributors == []
    assert result.churn == []
    assert result.first_commit is None
    assert result.last_commit is None


def test_empty_git_repo(tmp_path: Path) -> None:
    repo = tmp_path / "empty"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    result = analyze_history(repo)
    assert result.is_git_repo is True
    assert result.total_commits == 0
    assert result.contributors == []
    assert result.churn == []
    assert result.first_commit is None


def test_basic_stats(sample_repo: Path) -> None:
    result = analyze_history(sample_repo)
    assert result.is_git_repo is True
    assert result.total_commits == 3
    assert result.first_commit is not None and result.first_commit.year == 2020
    assert result.last_commit is not None and result.last_commit.year == 2022
    assert result.github is None


def test_contributors_ranked(sample_repo: Path) -> None:
    contributors = analyze_history(sample_repo).contributors
    assert len(contributors) == 2
    assert (contributors[0].name, contributors[0].commits) == ("Alice", 2)
    assert (contributors[1].name, contributors[1].commits) == ("Bob", 1)


def test_churn_ranked(sample_repo: Path) -> None:
    churn = analyze_history(sample_repo).churn
    by_path = {c.path: c.commits for c in churn}
    assert by_path["a.txt"] == 3
    assert by_path["b.txt"] == 1
    assert churn[0].path == "a.txt"  # most-churned first


def test_churn_limit(sample_repo: Path) -> None:
    churn = analyze_history(sample_repo, churn_limit=1).churn
    assert len(churn) == 1
    assert churn[0].path == "a.txt"


# --- GitHub remote detection ----------------------------------------------


def test_detect_github_repo_https(sample_repo: Path) -> None:
    _git(
        sample_repo,
        "remote",
        "add",
        "origin",
        "https://github.com/octocat/Hello-World.git",
    )
    assert detect_github_repo(sample_repo) == ("octocat", "Hello-World")


def test_detect_github_repo_ssh(sample_repo: Path) -> None:
    _git(
        sample_repo,
        "remote",
        "add",
        "origin",
        "git@github.com:octocat/Hello-World.git",
    )
    assert detect_github_repo(sample_repo) == ("octocat", "Hello-World")


def test_detect_github_repo_non_github(sample_repo: Path) -> None:
    _git(
        sample_repo,
        "remote",
        "add",
        "origin",
        "https://gitlab.com/octocat/Hello-World.git",
    )
    assert detect_github_repo(sample_repo) is None


def test_detect_github_repo_no_remote(sample_repo: Path) -> None:
    assert detect_github_repo(sample_repo) is None


def test_detect_github_repo_not_a_repo(tmp_path: Path) -> None:
    assert detect_github_repo(tmp_path) is None


# --- GitHub REST (faked client) -------------------------------------------


class _FakeRepo:
    description = "A test repository"
    stargazers_count = 42
    open_issues_count = 7
    created_at = datetime(2011, 1, 26, tzinfo=UTC)
    pushed_at = datetime(2024, 3, 1, tzinfo=UTC)
    default_branch = "main"


class _FakeGithub:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.closed = False

    def get_repo(self, full_name: str) -> _FakeRepo:
        assert full_name == "octocat/Hello-World"
        return _FakeRepo()

    def close(self) -> None:
        self.closed = True


class _FailingGithub:
    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def get_repo(self, full_name: str) -> object:
        raise RuntimeError("network is down")

    def close(self) -> None:
        pass


def test_fetch_github_stats_mapped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ga, "Github", _FakeGithub)
    stats = fetch_github_stats("octocat", "Hello-World")
    assert stats is not None
    assert (stats.owner, stats.name) == ("octocat", "Hello-World")
    assert stats.stars == 42
    assert stats.open_issues == 7
    assert stats.default_branch == "main"
    assert stats.created_at is not None and stats.created_at.year == 2011


def test_fetch_github_stats_failure_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ga, "Github", _FailingGithub)
    assert fetch_github_stats("octocat", "Hello-World") is None


def test_default_repo_has_no_bots(sample_repo: Path) -> None:
    """DEC-022. A repo with only human commits has an empty `bots` list and
    full attribution stays in `contributors`."""
    result = analyze_history(sample_repo)
    assert result.bots == []
    assert {c.name for c in result.contributors} == {"Alice", "Bob"}


def test_bot_accounts_split_from_humans(tmp_path: Path) -> None:
    """DEC-022. `[bot]` and `-bot` suffixes get routed to `bots`."""
    repo = tmp_path / "with-bots"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _commit(
        repo,
        author="Alice",
        email="alice@example.com",
        message="real work",
        date="2023-01-01T00:00:00+00:00",
        files={"a.txt": "a1\n"},
    )
    _commit(
        repo,
        author="dependabot[bot]",
        email="49699333+dependabot[bot]@users.noreply.github.com",
        message="chore(deps): bump foo",
        date="2023-02-01T00:00:00+00:00",
        files={"a.txt": "a2\n"},
    )
    _commit(
        repo,
        author="github-actions[bot]",
        email="ga@example.com",
        message="ci: regenerate",
        date="2023-03-01T00:00:00+00:00",
        files={"a.txt": "a3\n"},
    )
    _commit(
        repo,
        author="renovate-bot",
        email="renovate@example.com",
        message="chore: lockfile",
        date="2023-04-01T00:00:00+00:00",
        files={"a.txt": "a4\n"},
    )
    result = analyze_history(repo)
    assert [c.name for c in result.contributors] == ["Alice"]
    bot_names = {c.name for c in result.bots}
    assert bot_names == {"dependabot[bot]", "github-actions[bot]", "renovate-bot"}
    # bots are still counted in total_commits — they happened
    assert result.total_commits == 4


def test_mailmap_canonicalizes_contributors(tmp_path: Path) -> None:
    """DEC-022. `git log --use-mailmap` collapses the two email forms of one
    person into a single contributor entry."""
    repo = tmp_path / "mailmapped"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _commit(
        repo,
        author="Alice Old",
        email="alice@oldjob.example",
        message="from old email",
        date="2022-01-01T00:00:00+00:00",
        files={"a.txt": "a1\n"},
    )
    _commit(
        repo,
        author="alice",
        email="alice@example.com",
        message="from new email, casual name",
        date="2022-02-01T00:00:00+00:00",
        files={"a.txt": "a2\n"},
    )
    # Map both forms to one canonical identity.
    (repo / ".mailmap").write_text(
        "Alice Canonical <alice@example.com> <alice@oldjob.example>\n"
        "Alice Canonical <alice@example.com> alice <alice@example.com>\n",
        encoding="utf-8",
    )
    _commit(
        repo,
        author="Bob",
        email="bob@example.com",
        message="add mailmap",
        date="2022-03-01T00:00:00+00:00",
        files={"a.txt": "a3\n"},
    )
    result = analyze_history(repo)
    by_name = {c.name: c.commits for c in result.contributors}
    # Without --use-mailmap this would be 3 contributors (Alice Old, alice, Bob).
    # With --use-mailmap, the two Alices collapse into one canonical identity.
    assert "Alice Canonical" in by_name, by_name
    assert by_name["Alice Canonical"] == 2
    assert by_name["Bob"] == 1
    assert len(result.contributors) == 2


def test_analyze_history_with_github(monkeypatch: pytest.MonkeyPatch, sample_repo: Path) -> None:
    _git(
        sample_repo,
        "remote",
        "add",
        "origin",
        "https://github.com/octocat/Hello-World.git",
    )
    monkeypatch.setattr(ga, "Github", _FakeGithub)
    result = analyze_history(sample_repo, fetch_github=True)
    assert result.github is not None
    assert result.github.stars == 42


# --- include_commit_files: shared-pass derivation (perf fix) --------------


def test_include_commit_files_derives_same_contributors_and_churn(
    sample_repo: Path,
) -> None:
    """The include_commit_files=True path derives contributors + churn from
    the single ``git log --name-only`` walk. It must produce the same data
    as the include_commit_files=False path that does separate passes."""
    cheap = analyze_history(sample_repo, include_commit_files=False)
    shared = analyze_history(sample_repo, include_commit_files=True)

    # Same total commits, same contributors (name + count, in order).
    assert shared.total_commits == cheap.total_commits
    assert [(c.name, c.commits) for c in shared.contributors] == [
        (c.name, c.commits) for c in cheap.contributors
    ]
    # Same bots split.
    assert [(c.name, c.commits) for c in shared.bots] == [(c.name, c.commits) for c in cheap.bots]
    # Same churn (path + count, in order).
    assert [(f.path, f.commits) for f in shared.churn] == [(f.path, f.commits) for f in cheap.churn]
    # First / last commit dates match.
    assert shared.first_commit == cheap.first_commit
    assert shared.last_commit == cheap.last_commit
    # The shared path additionally populates commit_records.
    assert len(shared.commits) == cheap.total_commits
    assert cheap.commits == []


def test_include_commit_files_uses_one_git_log_pass(
    monkeypatch: pytest.MonkeyPatch,
    sample_repo: Path,
) -> None:
    """When commit-files are needed, only one ``git log`` invocation runs —
    the heavy ``--name-only`` walk. The header-only and churn passes are
    derived from its output, not re-fetched. Other git plumbing calls
    (``rev-parse --is-inside-work-tree``) still happen."""
    log_calls: list[list[str]] = []
    real_run_git = ga._run_git

    def _spy(repo_path: Path, args: list[str], *, check: bool):
        if args and args[0] == "log":
            log_calls.append(list(args))
        return real_run_git(repo_path, args, check=check)

    monkeypatch.setattr(ga, "_run_git", _spy)
    analyze_history(sample_repo, include_commit_files=True)
    assert len(log_calls) == 1, log_calls
    # The single pass is the --name-only one (it's what feeds both derivations).
    assert "--name-only" in log_calls[0]


def test_legacy_path_still_uses_two_passes(
    monkeypatch: pytest.MonkeyPatch,
    sample_repo: Path,
) -> None:
    """When commit-files aren't needed (v0.1 default), the cheaper
    header-only + churn pair is used — no --name-only walk at all."""
    log_calls: list[list[str]] = []
    real_run_git = ga._run_git

    def _spy(repo_path: Path, args: list[str], *, check: bool):
        if args and args[0] == "log":
            log_calls.append(list(args))
        return real_run_git(repo_path, args, check=check)

    monkeypatch.setattr(ga, "_run_git", _spy)
    analyze_history(sample_repo, include_commit_files=False)
    assert len(log_calls) == 2, log_calls
    # First call: header-only (no --name-only).
    assert "--name-only" not in log_calls[0]
    # Second call: churn (--name-only, --format=).
    assert "--name-only" in log_calls[1]
    assert "--format=" in log_calls[1]


def test_churn_from_records_helper_handles_empty() -> None:
    """Empty records yield empty churn — DEC-026 graceful no-op."""
    assert ga._churn_from_records([]) == []
