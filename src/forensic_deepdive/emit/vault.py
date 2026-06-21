"""Obsidian vault emission (DEC-094).

An opt-in, deterministic serialization pass that turns the already-emitted markdown
artifacts into a local-first Obsidian vault: a `.obsidian/` config, YAML frontmatter
(``summary:`` / ``tags:`` / ``status:``) on every page, normalized ``[[wikilinks]]``
between the artifacts, and a MOC (map-of-content) index. No new dependency — it is a
pure string transform over the artifact content. Off by default (``--emit-vault``),
so the five contract artifacts stay byte-identical when the flag is absent.

The agent-friendly delta (research.md Thread 4d): every page carries a ``summary:``
frontmatter field (triage/retrieve without opening the file) and the MOC is a single
traversable entry point.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

VAULT_SUBDIR = "vault"

# Per-artifact one-line summaries (the `summary:` frontmatter). Keyed by filename so
# the page is self-describing for an agent without opening it.
_PAGE_SUMMARY: dict[str, str] = {
    "MAP.md": "What's where in the codebase, ranked by centrality.",
    "HOTPATHS.md": "Dependency + change hot spots — the load-bearing and high-churn code.",
    "ARCHAEOLOGY.md": "What git history reveals: age, contributors, churn.",
    "MENTAL_MODEL.md": "The onboarding mental model a maintainer would write.",
    "AGENT_BRIEF.md": "Assertive Never/Always rules for AI agents (<=5kb).",
    "AGENT_BRIEF_DEEP.md": "Overflow detail for the agent brief.",
    "ARCHITECTURE.md": "System-level cross-boundary architecture diagram.",
}

# The artifact stems whose cross-references in body text become [[wikilinks]].
_ARTIFACT_STEMS = (
    "MAP",
    "HOTPATHS",
    "ARCHAEOLOGY",
    "MENTAL_MODEL",
    "AGENT_BRIEF_DEEP",
    "AGENT_BRIEF",
    "ARCHITECTURE",
)

# Minimal Obsidian config: wikilinks on (not markdown links), shortest link format.
_OBSIDIAN_APP_JSON = {"useMarkdownLinks": False, "newLinkFormat": "shortest"}


def _page_name(filename: str) -> str:
    return filename[:-3] if filename.endswith(".md") else filename


def _frontmatter(filename: str, repo_name: str) -> str:
    summary = _PAGE_SUMMARY.get(filename, "forensic-deepdive artifact.")
    tag = _page_name(filename).lower().replace("_", "-")
    return (
        "---\n"
        f"summary: {summary}\n"
        f"tags: [forensic-deepdive, {tag}]\n"
        "status: generated\n"
        f"repo: {repo_name}\n"
        "source: forensic-deepdive\n"
        "---\n\n"
    )


def _wikilink_crossrefs(body: str) -> str:
    """Turn artifact cross-references (``MAP.md`` / `` `MAP.md` ``) in body text into
    ``[[MAP]]`` wikilinks so Obsidian's graph links the pages. The ``\\.md`` anchor
    means ``AGENT_BRIEF_DEEP.md`` is matched as itself, never as ``AGENT_BRIEF``."""
    for stem in _ARTIFACT_STEMS:
        body = re.sub(rf"`?{stem}\.md`?", f"[[{stem}]]", body)
    return body


def emit_vault(artifacts: dict[str, str], repo_name: str, vault_dir: Path) -> list[Path]:
    """Write an Obsidian vault from ``{filename: markdown}`` into *vault_dir*.

    Deterministic. Returns the written paths (sorted). Each artifact becomes a page
    with frontmatter + wikilinked body; a `.obsidian/app.json` enables wikilinks; an
    ``INDEX.md`` MOC links every page with its summary.
    """
    vault_dir = Path(vault_dir)
    vault_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    obsidian = vault_dir / ".obsidian"
    obsidian.mkdir(exist_ok=True)
    app_json = obsidian / "app.json"
    app_json.write_text(json.dumps(_OBSIDIAN_APP_JSON, indent=2) + "\n", encoding="utf-8")
    written.append(app_json)

    for filename, content in sorted(artifacts.items()):
        page = vault_dir / filename
        page.write_text(
            _frontmatter(filename, repo_name) + _wikilink_crossrefs(content), encoding="utf-8"
        )
        written.append(page)

    moc = [
        "---",
        "summary: Map of content — the index of every deepdive artifact for this repo.",
        "tags: [forensic-deepdive, moc]",
        "status: generated",
        f"repo: {repo_name}",
        "---",
        "",
        f"# {repo_name} — deepdive vault",
        "",
        "Start here. Each artifact is a page; open the graph view to see how they link.",
        "",
    ]
    for filename in sorted(artifacts):
        stem = _page_name(filename)
        moc.append(f"- [[{stem}]] — {_PAGE_SUMMARY.get(filename, '')}".rstrip(" —"))
    index = vault_dir / "INDEX.md"
    index.write_text("\n".join(moc) + "\n", encoding="utf-8")
    written.append(index)

    return sorted(written)
