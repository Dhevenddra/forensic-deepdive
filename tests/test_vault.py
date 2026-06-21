"""Obsidian vault emission (DEC-094).

Unit tests for the transform + an end-to-end `--emit-vault` extract, plus the
flag-off byte-identical guard (the default path must be unchanged).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from forensic_deepdive.emit.vault import VAULT_SUBDIR, _wikilink_crossrefs, emit_vault
from forensic_deepdive.pipeline import ExtractConfig, PipelineRunner, default_phases

FIXTURES = Path(__file__).parent / "fixtures"

_ARTIFACTS = {
    "MAP.md": "# MAP — demo\n\nSee AGENT_BRIEF.md and `HOTPATHS.md` for more.\n",
    "AGENT_BRIEF.md": "# AGENT_BRIEF — demo\n\nRules.\n",
    "AGENT_BRIEF_DEEP.md": "# AGENT_BRIEF_DEEP — demo\n\nOverflow.\n",
}


def test_emit_vault_writes_pages_obsidian_config_and_moc(tmp_path: Path) -> None:
    written = emit_vault(_ARTIFACTS, "demo", tmp_path / "vault")
    vault = tmp_path / "vault"
    # .obsidian config + a page per artifact + the MOC index.
    assert (vault / ".obsidian" / "app.json").is_file()
    assert (vault / "MAP.md").is_file()
    assert (vault / "INDEX.md").is_file()
    assert (vault / ".obsidian" / "app.json") in written


def test_vault_pages_carry_frontmatter(tmp_path: Path) -> None:
    emit_vault(_ARTIFACTS, "demo", tmp_path / "vault")
    page = (tmp_path / "vault" / "MAP.md").read_text(encoding="utf-8")
    assert page.startswith("---\n")
    assert "summary: What's where" in page
    assert "tags: [forensic-deepdive, map]" in page
    assert "status: generated" in page
    # The original body follows the frontmatter.
    assert "# MAP — demo" in page


def test_vault_normalizes_crossrefs_to_wikilinks() -> None:
    out = _wikilink_crossrefs("See AGENT_BRIEF.md and `HOTPATHS.md` and AGENT_BRIEF_DEEP.md.")
    assert "[[AGENT_BRIEF]]" in out
    assert "[[HOTPATHS]]" in out
    # The \.md anchor keeps AGENT_BRIEF_DEEP distinct (not mangled into AGENT_BRIEF).
    assert "[[AGENT_BRIEF_DEEP]]" in out
    assert "AGENT_BRIEF_DEEP.md" not in out


def test_moc_links_every_page(tmp_path: Path) -> None:
    emit_vault(_ARTIFACTS, "demo", tmp_path / "vault")
    moc = (tmp_path / "vault" / "INDEX.md").read_text(encoding="utf-8")
    assert "[[MAP]]" in moc and "[[AGENT_BRIEF]]" in moc
    assert "tags: [forensic-deepdive, moc]" in moc


def test_emit_vault_is_deterministic(tmp_path: Path) -> None:
    emit_vault(_ARTIFACTS, "demo", tmp_path / "a")
    emit_vault(_ARTIFACTS, "demo", tmp_path / "b")
    for name in ("MAP.md", "INDEX.md", ".obsidian/app.json"):
        assert (tmp_path / "a" / name).read_text(encoding="utf-8") == (
            tmp_path / "b" / name
        ).read_text(encoding="utf-8")


def _extract(parent: Path, *, emit_vault_flag: bool) -> Path:
    # Same repo NAME ("repo") under different parents so repo_name (and thus the
    # artifact titles) match — only the feature flag differs.
    repo = parent / "repo"
    shutil.copytree(FIXTURES / "python_sample", repo)
    PipelineRunner(default_phases()).run(
        ExtractConfig(
            repo_path=repo.resolve(),
            output_dir=repo / "docs" / "codebase",
            flatten=False,
            write_editor_shims=False,
            build_graph_db=True,
            graph_db_path=parent / "graph.lbug",
            emit_vault=emit_vault_flag,
        )
    )
    return repo / "docs" / "codebase"


def _strip_footer_date(text: str) -> str:
    """Normalize the only nondeterministic line — the footer's generated-on date."""
    import re

    return re.sub(r"on \d{4}-\d{2}-\d{2}\.", "on <date>.", text)


def test_extract_emits_vault_only_when_flag_on(tmp_path: Path) -> None:
    on = _extract(tmp_path / "on", emit_vault_flag=True)
    off = _extract(tmp_path / "off", emit_vault_flag=False)
    assert (on / VAULT_SUBDIR / "INDEX.md").is_file()
    assert (on / VAULT_SUBDIR / "MAP.md").is_file()
    assert not (off / VAULT_SUBDIR).exists()
    # Flag-off invariant: the contract artifacts are unaffected by the feature
    # (same repo name; only the footer's generated-on date differs run-to-run).
    for name in ("MAP.md", "HOTPATHS.md", "ARCHAEOLOGY.md", "MENTAL_MODEL.md", "AGENT_BRIEF.md"):
        assert _strip_footer_date((on / name).read_text(encoding="utf-8")) == _strip_footer_date(
            (off / name).read_text(encoding="utf-8")
        )
