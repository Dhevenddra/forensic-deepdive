"""Artifact emitters — turn a :class:`RepoFacts` bundle into the five markdown
artifacts (plus the optional AGENT_BRIEF_DEEP.md overflow)."""

from __future__ import annotations

from forensic_deepdive.emit.agent_brief_md import render_agent_brief
from forensic_deepdive.emit.archaeology_md import render_archaeology
from forensic_deepdive.emit.common import RepoFacts
from forensic_deepdive.emit.hotpaths_md import render_hotpaths
from forensic_deepdive.emit.map_md import render_map
from forensic_deepdive.emit.mental_model_md import render_mental_model

__all__ = [
    "RepoFacts",
    "render_agent_brief",
    "render_all",
    "render_archaeology",
    "render_hotpaths",
    "render_map",
    "render_mental_model",
]


def render_all(facts: RepoFacts) -> dict[str, str]:
    """Render every artifact. Returns ``{filename: markdown}``.

    Always contains the five contract artifacts; ``AGENT_BRIEF_DEEP.md`` is
    included only when AGENT_BRIEF.md overflowed its 5 KB cap.
    """
    brief, deep = render_agent_brief(facts)
    artifacts = {
        "MAP.md": render_map(facts),
        "HOTPATHS.md": render_hotpaths(facts),
        "ARCHAEOLOGY.md": render_archaeology(facts),
        "MENTAL_MODEL.md": render_mental_model(facts),
        "AGENT_BRIEF.md": brief,
    }
    if deep is not None:
        artifacts["AGENT_BRIEF_DEEP.md"] = deep
    return artifacts
