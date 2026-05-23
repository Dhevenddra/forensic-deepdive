"""Tests for blog.models."""
from datetime import datetime

from blog.models import Author, Post


def test_post_round_trip():
    author = Author(name="A", email="a@a.com")
    post = Post(
        title="t",
        body="b",
        author=author,
        published=datetime(2024, 1, 1),
        tags=[],
    )
    assert post.title == "t"
    assert post.author is author
