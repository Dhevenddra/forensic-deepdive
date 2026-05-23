"""Core data models: Author and Post."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Author:
    name: str
    email: str


@dataclass(frozen=True)
class Post:
    title: str
    body: str
    author: Author
    published: datetime
    tags: list[str]
