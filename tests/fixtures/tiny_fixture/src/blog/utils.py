"""Small string and date helpers."""
from __future__ import annotations

import re
from datetime import datetime


def slugify(value: str) -> str:
    """Turn a title into a URL-safe slug."""
    value = value.lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def format_date(when: datetime) -> str:
    """Render a date for the blog index."""
    return when.strftime("%Y-%m-%d")
