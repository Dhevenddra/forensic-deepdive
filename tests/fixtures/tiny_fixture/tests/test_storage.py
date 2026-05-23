"""Tests for blog.storage."""
from pathlib import Path

from blog.storage import save_posts


def test_save_posts_creates_directory(tmp_path: Path):
    save_posts(tmp_path / "posts", [])
    assert (tmp_path / "posts").is_dir()
