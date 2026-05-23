"""Command-line entry for the tiny blog."""
from __future__ import annotations

import sys
from pathlib import Path

from blog.config import load_config
from blog.feed import build_feed
from blog.render import render_index
from blog.storage import Storage


def main(argv: list[str]) -> int:
    """Generate the blog site from a config file path."""
    config_path = Path(argv[1])
    config = load_config(config_path)
    storage = Storage(config_path)
    posts = storage.load_posts()
    feed = build_feed(posts)
    index = render_index(posts)
    (config.output_dir / "feed.xml").write_text(feed, encoding="utf-8")
    (config.output_dir / "index.html").write_text(index, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
