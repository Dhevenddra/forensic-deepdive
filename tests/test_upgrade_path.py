"""The upgrade path — running Deepdive over a repo that already carries a
PREVIOUS release's output (DEC-110).

Every other test in this suite writes shims into an empty ``tmp_path``. That
exercises the **first** run only. DEC-108 was a flag (``--refresh-shims``) that
had been structurally incapable of refreshing 5 of its 10 targets since DEC-091,
and 909 green tests never saw it, because the bug is invisible on a clean tree
and only appears on the **second** run.

The fixture under ``fixtures/prior_release/v0_8_0/`` is the verbatim surface that
0.8.0 actually wrote, produced by executing ``emit/shims.py`` at the ``v0.8.0``
tag. It is historical evidence, not a mock — see that directory's README.

Two properties are asserted together, and neither is sufficient alone:

* **convergence** — after ``--refresh-shims``, every Deepdive-owned target is
  byte-identical to what a clean run writes; and
* **restraint** — every hand-edited or foreign file is byte-unchanged.

DEC-108's fix could have been written as "refresh everything." Restraint is what
forbids that, and write-if-absent (DEC-031) is the guarantee it protects.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from forensic_deepdive.emit import shims as shims_mod
from forensic_deepdive.emit.shims import write_shims

# The brief path the prior-release fixtures were generated against. Changing it
# would make the comparison meaningless — the emitted bodies interpolate it.
_BRIEF = "docs/codebase/AGENT_BRIEF.md"

_FIXTURES = Path(__file__).parent / "fixtures" / "prior_release"

# The upgrade boundary this suite actually tests. We assert convergence from each
# listed release to current. 0.8.0 is the one carrying the known DEC-108 leak; add
# newer releases here as they ship (see the fixture README).
PRIOR_RELEASES = ("v0_8_0",)


def _files(root: Path) -> dict[str, str]:
    """Every file under *root*, keyed by posix relative path."""
    return {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


# The staged and clean repos must share a basename: plugin.json's description
# embeds the repo directory name, so comparing `repo/` against `clean/` would
# diff on that alone. Same leaf name, different parents.
_REPO_NAME = "target-repo"


def _stage(prior: str, tmp_path: Path) -> Path:
    """Materialize a prior release's emitted surface into a fresh repo dir."""
    repo = tmp_path / "staged" / _REPO_NAME
    shutil.copytree(_FIXTURES / prior, repo)
    return repo


def _clean_run(tmp_path: Path) -> dict[str, str]:
    """What the current emitter writes into an empty repo — the convergence target."""
    fresh = tmp_path / "clean" / _REPO_NAME
    fresh.mkdir(parents=True)
    write_shims(fresh, _BRIEF)
    return _files(fresh)


# ---------------------------------------------------------------------------
# The fixture must have teeth
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("prior", PRIOR_RELEASES)
def test_prior_surface_is_genuinely_stale(prior: str, tmp_path: Path) -> None:
    """Guard against a vacuous fixture.

    If a prior surface ever equals current output, every convergence assertion
    below passes trivially and this module silently stops testing anything. That
    is exactly how DEC-108 survived: assertions that could not fail.
    """
    staged = _files(_stage(prior, tmp_path))
    current = _clean_run(tmp_path)
    assert staged.keys() == current.keys(), "prior surface should cover the same 10 targets"
    differing = [rel for rel, body in staged.items() if body != current[rel]]
    assert differing, (
        f"{prior} fixture is byte-identical to current output — it tests nothing. "
        "Regenerate it from the real tag, or retire it."
    )


def test_the_0_8_0_surface_carries_the_dec_108_leak() -> None:
    """The specific defect this fixture exists to reproduce (observed on hermes-agent):
    two skill bodies written by 0.8.0 cite internal ledger IDs from the gitignored
    DECISIONS.md, and carry no fingerprint for the DEC-091 gate to find."""
    surface = _files(_FIXTURES / "v0_8_0")
    leaks = {
        rel: sorted(set(re.findall(r"DEC-\d+", body)))
        for rel, body in surface.items()
        if re.search(r"DEC-\d+", body)
    }
    assert leaks == {
        ".claude/skills/codebase-impact-analysis/SKILL.md": ["DEC-015"],
        ".claude/skills/codebase-refactoring/SKILL.md": ["DEC-012"],
    }
    # Neither leaking file carries the DEC-091 ownership fingerprint — that is
    # precisely why refresh could never reach them.
    for rel in leaks:
        assert shims_mod._SHIM_FINGERPRINT not in surface[rel]


# ---------------------------------------------------------------------------
# Convergence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("prior", PRIOR_RELEASES)
def test_upgrade_with_refresh_converges_to_a_clean_run(prior: str, tmp_path: Path) -> None:
    """The headline guarantee: upgrading a repo yields byte-identical output to
    analyzing it fresh. No file may be left carrying a previous release's body."""
    repo = _stage(prior, tmp_path)
    write_shims(repo, _BRIEF, refresh=True)
    assert _files(repo) == _clean_run(tmp_path)


@pytest.mark.parametrize("prior", PRIOR_RELEASES)
def test_upgrade_leaves_no_internal_ledger_ids(prior: str, tmp_path: Path) -> None:
    """DEC-107's invariant, asserted on the upgrade path rather than a clean tree.

    DEC-107 held on a fresh repo and leaked on every upgrade for two releases;
    this is the assertion that would have caught that.
    """
    repo = _stage(prior, tmp_path)
    write_shims(repo, _BRIEF, refresh=True)
    leaks = {
        rel: sorted(set(re.findall(r"DEC-\d+", body)))
        for rel, body in _files(repo).items()
        if re.search(r"DEC-\d+", body)
    }
    assert not leaks, f"upgraded repo still cites internal ledger IDs: {leaks}"


@pytest.mark.parametrize("prior", PRIOR_RELEASES)
def test_upgrade_without_refresh_writes_nothing(prior: str, tmp_path: Path) -> None:
    """Write-if-absent (DEC-031) still governs the default path on upgrade: all ten
    targets exist, so all ten are skipped and the stale bodies survive untouched.

    Staleness is only ever resolved by the explicit flag — never as a side effect
    of a re-extract.
    """
    repo = _stage(prior, tmp_path)
    before = _files(repo)
    result = write_shims(repo, _BRIEF)
    assert not result.written and not result.refreshed
    assert len(result.skipped) == 10
    assert _files(repo) == before


@pytest.mark.parametrize("prior", PRIOR_RELEASES)
def test_upgrade_without_refresh_reports_what_is_stale(prior: str, tmp_path: Path) -> None:
    """DEC-111: detection without mutation. The default run leaves everything alone
    but names the targets that ``--refresh-shims`` would rewrite — the only way an
    upgrading user finds out the flag has work to do."""
    repo = _stage(prior, tmp_path)
    clean = _clean_run(tmp_path)
    before = _files(repo)
    expected = {rel for rel, body in before.items() if body != clean[rel]}

    result = write_shims(repo, _BRIEF)

    reported = {p.relative_to(repo).as_posix() for p in result.stale}
    assert reported == expected
    assert _files(repo) == before, "the advisory must not touch the disk"
    # Skills are reportable at all only because of DEC-108's namespace ownership.
    # Exactly two changed between 0.8.0 and now — the pair DEC-107 stripped ledger
    # IDs from; the other three bodies are byte-identical across the releases.
    assert {rel for rel in reported if rel.endswith("SKILL.md")} == {
        ".claude/skills/codebase-impact-analysis/SKILL.md",
        ".claude/skills/codebase-refactoring/SKILL.md",
    }


@pytest.mark.parametrize("prior", PRIOR_RELEASES)
def test_stale_is_empty_once_refreshed(prior: str, tmp_path: Path) -> None:
    """Nothing is both refreshed and still advised about, and a converged repo
    reports nothing on the next run."""
    repo = _stage(prior, tmp_path)
    assert not write_shims(repo, _BRIEF, refresh=True).stale
    assert not write_shims(repo, _BRIEF).stale


@pytest.mark.parametrize("prior", PRIOR_RELEASES)
def test_stale_never_names_a_users_own_file(prior: str, tmp_path: Path) -> None:
    """A hand-edited shim is not stale — it is theirs. Advising on it would invite
    the user to overwrite their own work with our template."""
    repo = _stage(prior, tmp_path)
    hand_edited = repo / "CLAUDE.md"
    hand_edited.write_text("MY OWN INSTRUCTIONS — no fingerprint\n", encoding="utf-8")

    result = write_shims(repo, _BRIEF)

    assert hand_edited not in result.stale
    assert hand_edited in result.skipped


def test_first_run_reports_nothing_stale(tmp_path: Path) -> None:
    """On a clean tree every target is written, so the advisory is silent by
    construction — it fires only on the upgrade path it was built for."""
    repo = tmp_path / "fresh"
    repo.mkdir()
    result = write_shims(repo, _BRIEF)
    assert len(result.written) == 10
    assert not result.stale


@pytest.mark.parametrize("prior", PRIOR_RELEASES)
def test_upgrade_refresh_reports_every_stale_target(prior: str, tmp_path: Path) -> None:
    """Whatever refresh rewrites, it reports — the summary is how a user learns
    their files changed."""
    repo = _stage(prior, tmp_path)
    clean = _clean_run(tmp_path)
    staged = _files(repo)
    expected_stale = {rel for rel, body in staged.items() if body != clean[rel]}

    result = write_shims(repo, _BRIEF, refresh=True)
    reported = {p.relative_to(repo).as_posix() for p in result.refreshed}
    assert reported == expected_stale


# ---------------------------------------------------------------------------
# Restraint — the other half, without which "refresh everything" would pass
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("prior", PRIOR_RELEASES)
def test_upgrade_never_clobbers_the_users_own_files(prior: str, tmp_path: Path) -> None:
    """A hand-edited editor shim and a foreign skill parked in our namespace both
    survive an upgrade byte-for-byte (DEC-091 / DEC-108 ownership)."""
    repo = _stage(prior, tmp_path)
    hand_edited = repo / "CLAUDE.md"
    hand_edited.write_text("MY OWN INSTRUCTIONS — no fingerprint\n", encoding="utf-8")
    foreign = repo / ".claude" / "skills" / "codebase-debugging" / "SKILL.md"
    foreign.write_text("---\nname: my-own-skill\ndescription: Mine.\n---\n\n# Mine\n", "utf-8")

    write_shims(repo, _BRIEF, refresh=True)

    assert hand_edited.read_text(encoding="utf-8") == "MY OWN INSTRUCTIONS — no fingerprint\n"
    assert "my-own-skill" in foreign.read_text(encoding="utf-8")


@pytest.mark.parametrize("prior", PRIOR_RELEASES)
def test_upgrade_does_not_delete_unrelated_files(prior: str, tmp_path: Path) -> None:
    """An upgrade touches its ten targets and nothing else in the repo."""
    repo = _stage(prior, tmp_path)
    bystander = repo / "src" / "main.py"
    bystander.parent.mkdir(parents=True)
    bystander.write_text("print('hi')\n", encoding="utf-8")

    write_shims(repo, _BRIEF, refresh=True)

    assert bystander.read_text(encoding="utf-8") == "print('hi')\n"


# ---------------------------------------------------------------------------
# Proof the convergence assertion has teeth (DEC-110's acceptance discipline)
# ---------------------------------------------------------------------------


def _dec_091_gate(path: Path, existing: str) -> bool:
    """The pre-DEC-108 ownership predicate: fingerprint only.

    Reproduced here verbatim so the regression it caused stays permanently
    detectable. This is the code that shipped in 0.8.0 and 0.9.0-dev.
    """
    return shims_mod._SHIM_FINGERPRINT in existing


def test_convergence_fails_under_the_pre_dec_108_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The acceptance rule from the v0.9 findings run: an upgrade-path test that
    cannot be shown failing on the bug it describes is decoration.

    Restore the DEC-091 fingerprint-only predicate and the convergence assertion
    must break — with the five skills left stale, because no skill body has ever
    contained the fingerprint. If this test ever passes trivially, the guarantee
    above has stopped being load-bearing.
    """
    monkeypatch.setattr(shims_mod, "_is_deepdive_owned", _dec_091_gate)

    repo = _stage("v0_8_0", tmp_path)
    result = write_shims(repo, _BRIEF, refresh=True)

    refreshed = {p.relative_to(repo).as_posix() for p in result.refreshed}
    assert not any(rel.endswith("SKILL.md") for rel in refreshed), (
        "the old gate should be unable to refresh any skill"
    )
    assert _files(repo) != _clean_run(tmp_path), "the old gate should NOT converge"
    # And the original symptom is reproduced: the ledger IDs survive the upgrade.
    stale = (repo / ".claude" / "skills" / "codebase-impact-analysis" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "DEC-015" in stale
