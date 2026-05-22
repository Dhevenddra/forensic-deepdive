"""Tests for the repository inventory stage."""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.inventory import take_inventory

FIXTURES = Path(__file__).parent / "fixtures"


def test_inventory_python_sample() -> None:
    inventory = take_inventory(FIXTURES / "python_sample")
    assert inventory.file_count == 2
    assert inventory.language_breakdown == {"python": 2}
    assert {item.rel_path for item in inventory.source_files} == {"app.py", "greeter.py"}


def test_inventory_skips_ignored_directories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib.py").write_text("z = 3\n", encoding="utf-8")
    inventory = take_inventory(tmp_path)
    assert {item.rel_path for item in inventory.source_files} == {"src/main.py"}


def test_inventory_skips_unknown_extensions(tmp_path: Path) -> None:
    (tmp_path / "readme.md").write_text("# hi\n", encoding="utf-8")
    (tmp_path / "data.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "code.py").write_text("a = 1\n", encoding="utf-8")
    inventory = take_inventory(tmp_path)
    assert {item.rel_path for item in inventory.source_files} == {"code.py"}


def test_inventory_skips_oversized_files(tmp_path: Path) -> None:
    (tmp_path / "big.py").write_text("# " + "x" * 500, encoding="utf-8")
    inventory = take_inventory(tmp_path, max_file_bytes=10)
    assert inventory.source_files == []
