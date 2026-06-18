"""The shared themed Console + confidence palette (DEC-078, v0.7 Track B).

Brand tones are **blue / black / white** (the chrome: wordmark, borders, headers, labels).
The **confidence taxonomy keeps its semantic colours** — EXTRACTED green / INFERRED yellow /
AMBIGUOUS red — because those are a universal convention (and must survive colourblind / pipe
use); recolouring them to the brand blue would destroy their meaning. Confidence is therefore
**never colour-alone**: a glyph (``● ◐ ○``) and the word always travel with the colour, so it
reads under ``--plain`` / ``NO_COLOR`` too.
"""

from __future__ import annotations

import os

from rich.console import Console
from rich.text import Text
from rich.theme import Theme

# Brand chrome = blue/black/white; confidence = the fixed semantic palette (DEC-071/077).
FORENSIC_THEME = Theme(
    {
        # --- brand chrome (blue on black, white text) ---
        "banner": "bold bright_blue",
        "brand": "bold bright_blue",
        "header": "bold bright_blue",
        "border": "blue",
        "label": "blue",
        "value": "white",
        "muted": "dim white",
        "version": "bold bright_blue",
        "tagline": "dim white",
        # --- status ---
        "ok": "green",
        "warn": "yellow",
        "err": "bold red",
        # --- confidence taxonomy (semantic — fixed, never recoloured to the brand) ---
        "confidence.extracted": "bold green",
        "confidence.inferred": "bold yellow",
        "confidence.ambiguous": "bold red",
        "confidence.dropped": "dim",
    }
)

# (glyph, letter, theme-style) per confidence tier. The glyph + word carry the signal so it
# is never colour-alone (colourblind + ``--plain`` + pipe safety — DEC-071 §1b).
_CONFIDENCE = {
    "EXTRACTED": ("●", "E", "confidence.extracted"),
    "INFERRED": ("◐", "I", "confidence.inferred"),
    "AMBIGUOUS": ("○", "A", "confidence.ambiguous"),
    "DROPPED": ("·", "D", "confidence.dropped"),
}

# ``--plain`` global toggle, set once by the CLI callback before any command renders.
_PLAIN = False


def set_plain(value: bool) -> None:
    """Force plain (no-colour) output for every subsequently created Console — the
    ``--plain`` / ``--no-color`` global flag."""
    global _PLAIN
    _PLAIN = value


def _force_no_color() -> bool:
    # ``NO_COLOR`` (any value) is the cross-tool convention; ``--plain`` is ours.
    return _PLAIN or bool(os.environ.get("NO_COLOR"))


def get_console(*, stderr: bool = False) -> Console:
    """A themed Console for command output. Colour is auto-disabled on a non-TTY (Rich
    detects pipes/CI), and force-disabled under ``--plain`` / ``NO_COLOR`` — so machine
    output and logs stay plain. ``stderr=True`` routes to stderr (for status/errors)."""
    return Console(
        theme=FORENSIC_THEME,
        stderr=stderr,
        no_color=True if _force_no_color() else None,
    )


def confidence_label(name: str, *, compact: bool = False, glyphs: bool = True) -> Text:
    """A styled, **never-colour-alone** confidence chip. The colour always travels with a
    marker (and, unless *compact*, the word): ``● EXTRACTED`` / ``[E] EXTRACTED``.

    *glyphs* must be ``False`` on a non-UTF-8 / plain console — the ``●◐○`` glyphs aren't
    ASCII (they crash a cp1252 pipe), so the **letter** form ``[E]`` is used instead. *compact*
    drops the word (just the marker), for dense contexts like a trace tree. Returns a Rich
    :class:`Text`."""
    key = name.strip().upper()
    glyph, letter, style = _CONFIDENCE.get(key, ("?", "?", "value"))
    marker = glyph if glyphs else f"[{letter}]"
    body = marker if compact else f"{marker} {key}"
    return Text(body, style=style)
