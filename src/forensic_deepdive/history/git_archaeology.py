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
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from github import Auth, Github

# Unit-separator byte: a field delimiter that cannot occur in git metadata.
_FIELD_SEP = "\x1f"
_GIT_TIMEOUT_S = 600.0

# Matches owner/repo in both HTTPS and SSH GitHub remote URLs.
_GITHUB_REMOTE_RE = re.compile(r"github\.com[/:]([^/]+)/(.+?)(?:\.git)?/?$")

# DEC-022 bot detection. Matches GitHub's `[bot]` account convention, the
# looser `-bot` / `_bot` suffix, and known infrastructure accounts. The
# `noreply@github.com` form is intentionally NOT a bot signal — many real
# humans use it via web-flow commits.
_BOT_NAME_RE = re.compile(r"(?:\[bot\]|[-_]bot)$", re.IGNORECASE)
_BOT_EMAIL_HINTS: frozenset[str] = frozenset(
    {
        "noreply@dependabot.com",
        "noreply@github-actions.com",
        "support@github.com",
    }
)


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
class CommitRecord:
    """One commit's full metadata plus its file-touch list (DEC-026).

    Populated only when ``analyze_history(include_commit_files=True)`` is
    called — extracting the per-commit file list is a separate ``git log
    --name-only`` pass and we keep the aggregate-only path cheap. Files
    are repo-relative posix paths; authors are post-mailmap canonical
    (DEC-022)."""

    sha: str
    date: datetime | None
    author_name: str
    author_email: str
    message_subject: str  # first line of commit message, %s
    files_touched: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GitHistory:
    """The full Layer-3 result for one repository."""

    repo_path: Path
    is_git_repo: bool
    total_commits: int
    first_commit: datetime | None
    last_commit: datetime | None
    contributors: list[Contributor]  # human contributors, sorted by commit count
    churn: list[FileChurn]  # sorted by commit count, descending
    github: GitHubStats | None = None
    # DEC-022: bot accounts split out of `contributors`. Empty list for repos
    # without bot activity, so the ARCHAEOLOGY artifact stays clean.
    bots: list[Contributor] = field(default_factory=list)
    # DEC-026: full per-commit records, including file-touch lists.
    # Populated only when ``analyze_history(include_commit_files=True)``
    # — empty otherwise.
    commits: list[CommitRecord] = field(default_factory=list)
    # DEC-086: True when the work tree is a shallow clone (``git clone --depth N``).
    # Shallow history collapses commit counts, churn, and contributor shares to the
    # fetched slice — the artifact must say so rather than report the degenerate
    # signal as fact. Default False (full clones + the non-git path).
    is_shallow: bool = False


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
    include_commit_files: bool = False,
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
        include_commit_files: If True (DEC-026), additionally collect every
            commit's full metadata + file-touch list via a separate
            ``git log --name-only`` pass. Required by the v0.2 LadybugDB
            build phase for TOUCHED_BY_COMMIT / AUTHORED_BY edges; the
            v0.1 path leaves this off so it costs nothing.
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

    # When include_commit_files=True, one ``git log --name-only`` pass covers
    # everything: per-commit headers, file-touch lists, and (derived from
    # those file lists) churn. The v0.1 path keeps the cheaper header-only +
    # separate churn pass when commit-files aren't needed. On a 18k-commit
    # repo like Omi this saves two redundant full-history walks.
    if include_commit_files:
        commit_records = _read_commits_with_files(repo_path)
        commits = [
            _Commit(sha=r.sha, date=r.date, name=r.author_name, email=r.author_email)
            for r in commit_records
        ]
        churn = _churn_from_records(commit_records)[:churn_limit]
    else:
        commits = _read_commits(repo_path)
        churn = _read_churn(repo_path)[:churn_limit]
        commit_records = []
    humans, bots = _aggregate_contributors(commits)
    contributors = humans[:contributor_limit]
    bots = bots[:contributor_limit]

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
        bots=bots,
        commits=commit_records,
        is_shallow=_is_shallow(repo_path),
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


def _is_shallow(repo_path: Path) -> bool:
    """True if *repo_path* is a shallow clone (DEC-086). ``git rev-parse
    --is-shallow-repository`` prints ``true``/``false`` (git ≥2.15); any error
    is treated as not-shallow (the conservative default — we only *warn* on a
    positive)."""
    proc = _run_git(repo_path, ["rev-parse", "--is-shallow-repository"], check=False)
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def _read_commits(repo_path: Path) -> list[_Commit]:
    """Return all non-merge commits, newest first. Empty for a commit-less repo.

    Uses ``git log --use-mailmap`` (DEC-022) so ``%aN`` / ``%aE`` come out
    canonical when the repo ships a ``.mailmap``. No-op for repos without one.
    """
    fmt = _FIELD_SEP.join(["%H", "%cI", "%aN", "%aE"])
    proc = _run_git(
        repo_path,
        ["log", "--no-merges", "--use-mailmap", f"--format={fmt}"],
        check=False,
    )
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


def _read_commits_with_files(repo_path: Path) -> list[CommitRecord]:
    """Walk ``git log --name-only`` to collect every commit's metadata
    AND the list of files it touched (DEC-026).

    ``git log --name-only --format=<header>`` emits one block per commit
    with a blank line between header and files AND a blank line between
    commits. Rather than rely on the visually-ambiguous double-newline,
    we parse line-by-line and distinguish header lines (containing the
    unit-separator field delimiter) from file lines.
    """
    fmt = _FIELD_SEP.join(["%H", "%cI", "%aN", "%aE", "%s"])
    proc = _run_git(
        repo_path,
        ["log", "--no-merges", "--use-mailmap", "--name-only", f"--format={fmt}"],
        check=False,
    )
    if proc.returncode != 0:
        return []

    records: list[CommitRecord] = []
    current_header: tuple[str, str, str, str, str] | None = None
    current_files: list[str] = []

    def _flush() -> None:
        if current_header is None:
            return
        sha, date_str, name, email, subject = current_header
        records.append(
            CommitRecord(
                sha=sha,
                date=_parse_date(date_str),
                author_name=name,
                author_email=email,
                message_subject=subject,
                files_touched=tuple(current_files),
            )
        )

    for line in proc.stdout.split("\n"):
        if _FIELD_SEP in line:
            # New commit — emit the previous one and reset.
            _flush()
            fields = line.split(_FIELD_SEP)
            if len(fields) == 5:
                current_header = (fields[0], fields[1], fields[2], fields[3], fields[4])
            else:
                current_header = None
            current_files = []
        elif line.strip():
            # File path (--name-only output).
            current_files.append(line)
        # Blank line: skip.
    _flush()
    return records


def _read_churn(repo_path: Path) -> list[FileChurn]:
    """Return files ranked by how many commits have touched them."""
    proc = _run_git(repo_path, ["log", "--no-merges", "--format=", "--name-only"], check=False)
    if proc.returncode != 0:
        return []
    counts = Counter(line.strip() for line in proc.stdout.splitlines() if line.strip())
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [FileChurn(path=path, commits=n) for path, n in ranked]


def _churn_from_records(records: list[CommitRecord]) -> list[FileChurn]:
    """Derive churn from already-walked commit records — avoids a second
    ``git log --name-only`` pass when DEC-026 commit-files are present."""
    counts: Counter[str] = Counter()
    for r in records:
        counts.update(r.files_touched)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [FileChurn(path=path, commits=n) for path, n in ranked]


def _is_bot(name: str, email: str) -> bool:
    """DEC-022 bot heuristic. ``[bot]`` suffix, ``-bot`` / ``_bot`` suffix,
    or a known infrastructure email."""
    if _BOT_NAME_RE.search(name):
        return True
    return email.lower() in _BOT_EMAIL_HINTS


def _aggregate_contributors(
    commits: list[_Commit],
) -> tuple[list[Contributor], list[Contributor]]:
    """Aggregate commits by (name, email), ranked by commit count.

    Returns ``(humans, bots)`` — DEC-022 splits bot accounts out so the
    human-attribution surface (top-N, bus-factor, defect-proximity) is
    clean. Both lists are sorted by descending commit count, with name
    then email as tiebreakers.
    """
    counts = Counter((c.name, c.email) for c in commits)
    humans: list[Contributor] = []
    bots: list[Contributor] = []
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))
    for (name, email), n in ranked:
        bucket = bots if _is_bot(name, email) else humans
        bucket.append(Contributor(name=name, email=email, commits=n))
    return humans, bots


def _parse_date(value: str) -> datetime | None:
    """Parse a strict-ISO git date (``%cI``); return None if unparseable."""
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
