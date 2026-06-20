"""Unit tests for the pure-static FastContext seed-builder (DEC-087).

These are the normal-suite tests for deepdive's contribution to the usefulness
experiment; the harness + the model-dependent end-to-end run live in
``experiments/fastcontext/`` and are documented/reproduced there, not CI-gated
(the established pattern for model-dependent paths, cf. DEC-042/075).
"""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.pipeline import ExtractConfig, PipelineRunner, default_phases
from forensic_deepdive.seed import build_seed, localization_score


def _build_repo(tmp_path: Path) -> Path:
    """A tiny two-domain repo: a payment path and an unrelated auth path."""
    repo = tmp_path / "shop"
    repo.mkdir()
    (repo / "payment.py").write_text(
        "def process_payment(order):\n    return _charge(order)\n\n\n"
        "def _charge(order):\n    return order\n"
    )
    (repo / "auth.py").write_text(
        "def login(user):\n    return _check_password(user)\n\n\n"
        "def _check_password(user):\n    return True\n"
    )
    db_path = tmp_path / "graph.lbug"
    cfg = ExtractConfig(
        repo_path=repo.resolve(),
        output_dir=repo / "out",
        flatten=False,
        write_editor_shims=False,
        build_graph_db=True,
        graph_db_path=db_path,
    )
    PipelineRunner(default_phases()).run(cfg)
    return db_path


def test_build_seed_localizes_issue_to_the_right_file(tmp_path: Path) -> None:
    """An issue mentioning 'payment' localizes to payment.py and surfaces
    process_payment — not the unrelated auth code."""
    db_path = _build_repo(tmp_path)
    seed = build_seed(db_path, "process_payment fails when refunding an order")
    assert "payment.py" in seed.candidate_files
    # payment.py should outrank auth.py for this issue.
    assert seed.candidate_files[0] == "payment.py"
    symbol_names = {c.short_name for c in seed.candidate_symbols}
    assert "process_payment" in symbol_names
    # Pure-static floor: degraded (no [semantic] extra) by default.
    assert seed.degraded is True


def test_build_seed_prompt_contains_sections_and_is_deterministic(tmp_path: Path) -> None:
    db_path = _build_repo(tmp_path)
    seed1 = build_seed(db_path, "refund handling in process_payment")
    seed2 = build_seed(db_path, "refund handling in process_payment")
    prompt = seed1.to_prompt()
    assert "Likely-relevant files" in prompt
    assert "payment.py" in prompt
    assert "Repository context" in prompt
    # Deterministic apparatus — the experiment must reproduce.
    assert seed1 == seed2
    assert seed1.to_prompt() == seed2.to_prompt()


def test_build_seed_unlocalizable_issue_degrades_to_hotpaths(tmp_path: Path) -> None:
    """An issue with no lexical/structural hits yields no candidate files but the
    seed still renders (global hot spots / the note), never crashes."""
    db_path = _build_repo(tmp_path)
    seed = build_seed(db_path, "zzzznotapresentterm qqqxylophone")
    assert seed.candidate_files == []
    # to_prompt is still valid (header + degraded note at minimum).
    assert "Repository context" in seed.to_prompt()


def test_localization_score_precision_recall_f1() -> None:
    """The standalone file-localization metric — pure set math."""
    # 2 predicted, 1 correct of 2 gold → P=0.5, R=0.5, F1=0.5.
    s = localization_score(["a.py", "b.py"], {"a.py", "c.py"})
    assert s["true_positives"] == 1.0
    assert s["precision"] == 0.5
    assert s["recall"] == 0.5
    assert s["f1"] == 0.5
    # Perfect hit.
    perfect = localization_score(["a.py"], {"a.py"})
    assert perfect["f1"] == 1.0
    # No gold → unscoreable, all zeros (caller skips).
    assert localization_score(["a.py"], set())["f1"] == 0.0
    # No overlap → zero.
    assert localization_score(["x.py"], {"y.py"})["f1"] == 0.0
