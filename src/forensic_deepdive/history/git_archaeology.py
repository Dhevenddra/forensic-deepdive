"""Git archaeology — Layer 3 (plain-git default).

Extracts a repository's history into structured facts for the `ARCHAEOLOGY.md`
artifact: contributors, commit timeline, and file churn. This is the v0.1
default Layer-3 backend per DEC-005 — plain `git` plus optional GitHub REST.
Graphiti (the bi-temporal knowledge graph) is deferred to v0.2 behind the
2-of-5 threshold gate, so nothing here depends on it.

`git` is invoked as a subprocess (not a Python dependency). The GitHub side
uses `pygithub` (already a declared dependency) and is strictly optional:
`analyze_history` is fully offline unless `fetch_github=True` is passed, and
any GitHub failure degrades to ``github=None`` rather than raising.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from github import Auth, Github

# Unit-separator byte: a field delimiter that cannot occur in git metadata.
_FIELD_SEP = "\x1f"
_GIT_TIMEOUT_S = 300.0

# Matches owner/repo in both HTTPS and SSH GitHub remote URLs.
_GITHUB_REMOTE_RE = re.compile(r"github\.com[/:]([^/]+)/(.+?)(?:\.git)?/?$")


class GitArchaeologyError(RuntimeError):
    """A required git operation failed (git missing, timeout, unexpected error)."""


@dataclass(frozen=True, slots=True)
class Contributor:
    """One author, aggregated across all of their commits."""

    name: str
    email: str
    commits: int


@dataclass(frozen=True, slots=True)
class FileChurn:
    """A file and how many commits have touched it across history."""

    path: str
    commits: int


@dataclass(frozen=True, slots=True)
class GitHubStats:
    """Top-level GitHub metadata for the repo (best-effort, optional)."""

    owner: str
    name: str
    description: str | None
    stars: int
    open_issues: int
    created_at: datetime | None
    pushed_at: datetime | None
    default_branch: str


@dataclass(frozen=True, slots=True)
class GitHistory:
    """The full Layer-3 result for one repository."""

    repo_path: Path
    is_git_repo: bool
    total_commits: int
    first_commit: datetime | None
    last_commit: datetime | None
    contributors: list[Contributor]  # sorted by commit count, descending
    churn: list[FileChurn]  # sorted by commit count, descending
    github: GitHubStats | None = None


@dataclass(frozen=True, slots=True)
class _Commit:
    """One parsed commit record (internal)."""

    sha: str
    date: datetime | None
    name: str
    email: str


def analyze_history(
    repo_path: Path,
    *,
    churn_limit: int = 20,
    contributor_limit: int = 50,
    fetch_github: bool = False,
    github_token: str | None = None,
) -> GitHistory:
    """Analyze the git history of *repo_path*.

    Returns a :class:`GitHistory` even for non-git directories (with
    ``is_git_repo=False``) so the extract pipeline never has to special-case
    them. Fully offline unless *fetch_github* is set.

    Args:
        repo_path: Repository root to analyze.
        churn_limit: Keep at most this many of the most-churned files.
        contributor_limit: Keep at most this many of the top contributors.
        fetch_github: If True, also fetch GitHub metadata for the `origin`
            remote (best-effort; failures degrade to ``github=None``).
        github_token: Optional token for the GitHub API (higher rate limit,
            private repos).
    """
    repo_path = Path(repo_path)
    if not _is_git_repo(repo_path):
        return GitHistory(
            repo_path=repo_path,
            is_git_repo=False,
            total_commits=0,
            first_commit=None,
            last_commit=None,
            contributors=[],
            churn=[],
        )

    commits = _read_commits(repo_path)
    contributors = _aggregate_contributors(commits)[:contributor_limit]
    churn = _read_churn(repo_path)[:churn_limit]

    github = None
    if fetch_github:
        detected = detect_github_repo(repo_path)
        if detected is not None:
            github = fetch_github_stats(*detected, token=github_token)

    return GitHistory(
        repo_path=repo_path,
        is_git_repo=True,
        total_commits=len(commits),
        # `git log` is newest-first: last element is the oldest commit.
        first_commit=commits[-1].date if commits else None,
        last_commit=commits[0].date if commits else None,
        contributors=contributors,
        churn=churn,
        github=github,
    )


def detect_github_repo(repo_path: Path) -> tuple[str, str] | None:
    """Return ``(owner, name)`` if the repo's `origin` is a GitHub remote."""
    repo_path = Path(repo_path)
    if not _is_git_repo(repo_path):
        return None
    proc = _run_git(repo_path, ["remote", "get-url", "origin"], check=False)
    if proc.returncode != 0:
        return None
    match = _GITHUB_REMOTE_RE.search(proc.stdout.strip())
    if match is None:
        return None
    return match.group(1), match.group(2)


def fetch_github_stats(
    owner: str,
    name: str,
    token: str | None = None,
) -> GitHubStats | None:
    """Fetch top-level GitHub repo metadata via REST.

    Returns ``None`` on any failure — missing repo, rate limit, no network —
    because GitHub enrichment is optional and must never break extraction.
    """
    client = Github(auth=Auth.Token(token)) if token else Github()
    try:
        repo = client.get_repo(f"{owner}/{name}")
        return GitHubStats(
            owner=owner,
            name=name,
            description=repo.description,
            stars=repo.stargazers_count,
            open_issues=repo.open_issues_count,
            created_at=repo.created_at,
            pushed_at=repo.pushed_at,
            default_branch=repo.default_branch,
        )
    except Exception:  # noqa: BLE001 - optional network enrichment, never fatal
        return None
    finally:
        client.close()


# --- internals -------------------------------------------------------------


def _resolve_git() -> str:
    """Return the `git` executable path, or raise if it is not installed."""
    git = shutil.which("git")
    if git is None:
        raise GitArchaeologyError("`git` executable not found on PATH.")
    return git


def _run_git(
    repo_path: Path,
    args: list[str],
    *,
    check: bool,
) -> subprocess.CompletedProcess[str]:
    """Run a `git -C <repo> ...` command and return the completed process."""
    try:
        proc = subprocess.run(  # noqa: S603 - git path resolved via shutil.which
            [_resolve_git(), "-C", str(repo_path), *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=_GIT_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitArchaeologyError(f"`git {args[0]}` timed out after {_GIT_TIMEOUT_S:g}s") from exc
    if check and proc.returncode != 0:
        raise GitArchaeologyError(
            f"`git {' '.join(args)}` failed ({proc.returncode}): {proc.stderr.strip()}"
        )
    return proc


def _is_git_repo(repo_path: Path) -> bool:
    """True if *repo_path* is inside a git work tree."""
    if not repo_path.is_dir():
        return False
    proc = _run_git(repo_path, ["rev-parse", "--is-inside-work-tree"], check=False)
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def _read_commits(repo_path: Path) -> list[_Commit]:
    """Return all non-merge commits, newest first. Empty for a commit-less repo."""
    fmt = _FIELD_SEP.join(["%H", "%cI", "%aN", "%aE"])
    proc = _run_git(repo_path, ["log", "--no-merges", f"--format={fmt}"], check=False)
    if proc.returncode != 0:  # e.g. a freshly-init'd repo with no commits
        return []
    commits: list[_Commit] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        fields = line.split(_FIELD_SEP)
        if len(fields) != 4:
            continue
        sha, date_str, name, email = fields
        commits.append(_Commit(sha=sha, date=_parse_date(date_str), name=name, email=email))
    return commits


def _read_churn(repo_path: Path) -> list[FileChurn]:
    """Return files ranked by how many commits have touched them."""
    proc = _run_git(repo_path, ["log", "--no-merges", "--format=", "--name-only"], check=False)
    if proc.returncode != 0:
        return []
    counts = Counter(line.strip() for line in proc.stdout.splitlines() if line.strip())
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [FileChurn(path=path, commits=n) for path, n in ranked]


def _aggregate_contributors(commits: list[_Commit]) -> list[Contributor]:
    """Aggregate commits by (name, email), ranked by commit count."""
    counts = Counter((c.name, c.email) for c in commits)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))
    return [Contributor(name=name, email=email, commits=n) for (name, email), n in ranked]


def _parse_date(value: str) -> datetime | None:
    """Parse a strict-ISO git date (``%cI``); return None if unparseable."""
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
