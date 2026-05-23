"""RSS-style feed builder."""
from __future__ import annotations

from blog.models import Post
from blog.render import render_post
from blog.utils import format_date, slugify


def build_feed(posts: list[Post]) -> str:
    """Build a tiny pseudo-RSS feed from *posts*."""
    items = []
    for post in posts:
        body = render_post(post)
        items.append(
            f"<item><guid>{slugify(post.title)}</guid>"
            f"<pubDate>{format_date(post.published)}</pubDate>"
            f"<description>{body}</description></item>"
        )
    return "<rss><channel>" + "".join(items) + "</channel></rss>"
