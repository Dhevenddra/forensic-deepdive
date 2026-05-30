"""Opt-in offline ONNX semantic retriever (DEC-042, PRD §4.5 test 3).

The model-dependent tests are skipped when the ``[semantic]`` extra or a local
model is absent — exactly the PRD contract. The availability/degradation logic
is testable without the extra and is exercised here.
"""

from __future__ import annotations

import importlib.util

import pytest

from forensic_deepdive.query import semantic as sem

_EXTRA_PRESENT = all(
    importlib.util.find_spec(m) is not None for m in ("onnxruntime", "tokenizers", "numpy")
)


def test_semantic_unavailable_without_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Even if the runtime is installed, no configured model ⇒ unavailable.
    monkeypatch.delenv("FORENSIC_SEMANTIC_MODEL", raising=False)
    assert sem.semantic_available() is False


def test_semantic_unavailable_with_bad_model_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORENSIC_SEMANTIC_MODEL", "/no/such/model/dir")
    assert sem.semantic_available() is False


def test_importing_module_never_requires_the_extra() -> None:
    # The whole point of DEC-042: importing the module is safe without onnxruntime.
    assert hasattr(sem, "semantic_available")
    assert hasattr(sem, "build_semantic_index")
    assert hasattr(sem, "SemanticIndex")


@pytest.mark.skipif(not _EXTRA_PRESENT, reason="[semantic] extra not installed")
def test_semantic_roundtrip_when_extra_present(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    # When the extra is present but no model is configured, build is a no-op and
    # search degrades to empty — never an error (the pure-static floor holds).
    monkeypatch.delenv("FORENSIC_SEMANTIC_MODEL", raising=False)
    assert sem.build_semantic_index(tmp_path, []) is None
    assert sem.SemanticIndex(tmp_path).search("anything") == []
