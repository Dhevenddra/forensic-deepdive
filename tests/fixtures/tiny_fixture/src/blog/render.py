"""HTML rendering for posts and the index."""
from __future__ import annotations

from blog.models import Post
from blog.utils import format_date, slugify


def render_post(post: Post) -> str:
    """Render a single post to HTML."""
    slug = slugify(post.title)
    date = format_date(post.published)
    return (
        f'<article id="{slug}">'
        f"<h1>{post.title}</h1><time>{date}</time>"
        f"<p>{post.body}</p></article>"
    )


def render_index(posts: list[Post]) -> str:
    """Render the index page listing all posts."""
    rows = [
        f"<li>{slugify(post.title)} — {format_date(post.published)}</li>"
        for post in posts
    ]
    return "<ul>" + "".join(rows) + "</ul>"
