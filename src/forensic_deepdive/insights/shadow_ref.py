"""Git shadow-ref portability for the insight store (DEC-069, v0.6 Step 6).

Lane-(iii) memory travels with the repo. The JSONL store (DEC-019) lives under
``.deepdive/`` (gitignored — local-only), so by default insights don't survive a clone.
This syncs the JSONL to a **git shadow-ref** (``refs/forensic-deepdive/insights``) using
pure git plumbing (``hash-object`` / ``mktree`` / ``commit-tree`` / ``update-ref``): the
insights become a tiny commit reachable from a ref that is **not** a branch or tag (so it
never clutters ``git log`` / the working tree) yet can be pushed and fetched for
portability. No network here — saving/loading is local; pushing the ref is the user's call.

All operations are best-effort: outside a git repo, or if ``git`` is unavailable, they
return ``False`` and the JSONL floor still works (DEC-009 pure-static floor).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

SHADOW_REF = "refs/forensic-deepdive/insights"
_BLOB_NAME = "insights.jsonl"


def _git(repo_path: Path, *args: str, input_bytes: bytes | None = None) -> tuple[int, bytes]:
    """Run a git plumbing command in *repo_path*; return ``(returncode, stdout_bytes)``.
    Never raises on a non-zero exit — the caller decides."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            input=input_bytes,
            capture_output=True,
            check=False,
        )
    except (OSError, ValueError):
        return 1, b""
    return proc.returncode, proc.stdout


def _is_git_repo(repo_path: Path) -> bool:
    code, _ = _git(repo_path, "rev-parse", "--git-dir")
    return code == 0


def save_to_shadow_ref(repo_path: Path, jsonl_path: Path, *, ref: str = SHADOW_REF) -> bool:
    """Write the JSONL store's current content to the shadow *ref* as a one-file commit
    (parented on the prior ref if it exists, so the ref keeps a history). Returns ``True``
    on success, ``False`` outside a git repo / on any git failure / if the JSONL is absent."""
    repo_path = Path(repo_path)
    jsonl_path = Path(jsonl_path)
    if not jsonl_path.exists() or not _is_git_repo(repo_path):
        return False

    data = jsonl_path.read_bytes()
    code, out = _git(repo_path, "hash-object", "-w", "--stdin", input_bytes=data)
    if code != 0:
        return False
    blob = out.decode().strip()

    tree_spec = f"100644 blob {blob}\t{_BLOB_NAME}\n".encode()
    code, out = _git(repo_path, "mktree", input_bytes=tree_spec)
    if code != 0:
        return False
    tree = out.decode().strip()

    parent_args: list[str] = []
    code, out = _git(repo_path, "rev-parse", "--verify", "--quiet", ref)
    if code == 0 and out.strip():
        parent_args = ["-p", out.decode().strip()]
    code, out = _git(
        repo_path, "commit-tree", tree, *parent_args, "-m", "forensic-deepdive insights"
    )
    if code != 0:
        return False
    commit = out.decode().strip()

    code, _ = _git(repo_path, "update-ref", ref, commit)
    return code == 0


def _resolve_remote(repo_path: Path, remote: str | None) -> str | None:
    """The remote to push to: the explicit *remote*, else ``origin`` if present, else the
    first configured remote, else ``None`` (nothing to push to)."""
    code, out = _git(repo_path, "remote")
    remotes = out.decode().split() if code == 0 else []
    if remote is not None:
        return remote if remote in remotes else None
    if "origin" in remotes:
        return "origin"
    return remotes[0] if remotes else None


def push_shadow_ref(
    repo_path: Path,
    *,
    remote: str | None = None,
    ref: str = SHADOW_REF,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Publish the local insight shadow *ref* to a *remote* (DEC-075) — **explicit only,
    never automatic** (the never-push discipline extends to the insight ref). Returns
    ``(ok, message)``. Best-effort: outside a git repo, with no remote, or if the ref
    doesn't exist yet, returns ``(False, <reason>)`` rather than raising. ``dry_run`` passes
    ``git push --dry-run`` (no refs actually move)."""
    repo_path = Path(repo_path)
    if not _is_git_repo(repo_path):
        return False, "not a git repository"
    code, _ = _git(repo_path, "rev-parse", "--verify", "--quiet", ref)
    if code != 0:
        return False, f"no insight ref to push ({ref}); record an insight first"
    target = _resolve_remote(repo_path, remote)
    if target is None:
        reason = f"remote {remote!r} not found" if remote else "no git remote configured"
        return False, reason
    args = ["push"]
    if dry_run:
        args.append("--dry-run")
    args += [target, f"{ref}:{ref}"]
    code, out = _git(repo_path, *args)
    verb = "would push" if dry_run else "pushed"
    if code == 0:
        return True, f"{verb} {ref} → {target}"
    return False, f"git push failed (exit {code}): {out.decode(errors='replace').strip()}"


def load_from_shadow_ref(repo_path: Path, jsonl_path: Path, *, ref: str = SHADOW_REF) -> bool:
    """Restore the JSONL store from the shadow *ref* (e.g. after a clone that fetched it).
    Writes ``<ref>:insights.jsonl`` to *jsonl_path*. Returns ``True`` on success, ``False``
    if the ref / blob is absent or not a git repo."""
    repo_path = Path(repo_path)
    jsonl_path = Path(jsonl_path)
    if not _is_git_repo(repo_path):
        return False
    code, out = _git(repo_path, "cat-file", "-p", f"{ref}:{_BLOB_NAME}")
    if code != 0:
        return False
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path.write_bytes(out)
    return True
