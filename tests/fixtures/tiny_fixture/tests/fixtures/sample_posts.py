"""Sample post data used by tests."""
from datetime import datetime

SAMPLE_POSTS = [
    {
        "title": "Hello",
        "body": "World",
        "published": datetime(2024, 1, 1),
        "author": {"name": "Alice", "email": "alice@example.com"},
        "tags": ["intro"],
    },
]
