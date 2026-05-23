"""Configuration loading."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    site_name: str
    posts_dir: Path
    output_dir: Path


def load_config(path: Path) -> Config:
    """Load a Config from a JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return Config(
        site_name=data["site_name"],
        posts_dir=Path(data["posts_dir"]),
        output_dir=Path(data["output_dir"]),
    )
