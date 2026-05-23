"""Read and write posts on disk."""
from __future__ import annotations

import json
from pathlib import Path

from blog.config import Config, load_config
from blog.models import Author, Post


class Storage:
    """Loads and saves posts in JSON form."""

    def __init__(self, config_path: Path) -> None:
        self.config: Config = load_config(config_path)

    def load_posts(self) -> list[Post]:
        return load_posts(self.config.posts_dir)

    def save_posts(self, posts: list[Post]) -> None:
        save_posts(self.config.posts_dir, posts)


def load_posts(directory: Path) -> list[Post]:
    """Read every JSON post file in *directory*."""
    posts: list[Post] = []
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        author = Author(name=data["author"]["name"], email=data["author"]["email"])
        posts.append(
            Post(
                title=data["title"],
                body=data["body"],
                author=author,
                published=data["published"],
                tags=list(data.get("tags", [])),
            )
        )
    return posts


def save_posts(directory: Path, posts: list[Post]) -> None:
    """Write each Post to its own JSON file under *directory*."""
    directory.mkdir(parents=True, exist_ok=True)
    for post in posts:
        path = directory / f"{post.title}.json"
        path.write_text(json.dumps({"title": post.title}), encoding="utf-8")
