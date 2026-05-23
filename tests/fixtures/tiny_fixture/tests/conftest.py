"""Shared pytest fixtures for the tiny blog tests."""
from __future__ import annotations

from datetime import datetime

from blog.models import Author, Post


def make_post(title: str = "Hello") -> Post:
    """Build a Post for tests."""
    return Post(
        title=title,
        body="Body.",
        author=Author(name="Alice", email="alice@example.com"),
        published=datetime(2024, 1, 1),
        tags=["intro"],
    )
