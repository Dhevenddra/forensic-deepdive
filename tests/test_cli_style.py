"""The Console-only styled CLI layer (DEC-077/078, v0.7 Track B Step 6).

The presentation keystone (DEC-071 §1b): Console-only; data-driven capability panel; ANSI
only on a colour TTY (never on a pipe / ``--plain`` / ``NO_COLOR``); the block wordmark and
confidence glyphs degrade to ASCII when the console can't render them; confidence is never
encoded by colour alone (a glyph/letter + the word always travel with it).
"""

from __future__ import annotations

import io
from pathlib import Path

from rich.console import Console

from forensic_deepdive.cli.style.banner import (
    _artifact_names,
    _mcp_tool_names,
    _protocol_names,
    render_info,
)
from forensic_deepdive.cli.style.console import (
    FORENSIC_THEME,
    confidence_label,
    get_console,
    set_plain,
)


def _console(*, terminal: bool, color: bool) -> tuple[Console, io.StringIO]:
    sio = io.StringIO()
    c = Console(
        file=sio,
        theme=FORENSIC_THEME,
        force_terminal=terminal,
        color_system="truecolor" if color else None,
        no_color=not color,
        width=100,
    )
    return c, sio


# --- data-driven capability panel (no drift from the frozen contract) -------


def test_capability_panel_is_registry_driven():
    from forensic_deepdive.contracts.registry import REGISTRY
    from forensic_deepdive.query.artifacts import ARTIFACT_FILENAMES

    assert _protocol_names() == sorted(REGISTRY)  # live protocol registry
    assert set(_artifact_names()) == {n for n in ARTIFACT_FILENAMES if "DEEP" not in n}
    assert len(_artifact_names()) == 5  # the 5-artifact contract
    assert len(_mcp_tool_names()) == 9  # the frozen 9-tool contract
    assert "recall_insights" in _mcp_tool_names()  # suffix-stripped


# --- confidence never colour-alone ------------------------------------------


def test_confidence_label_carries_glyph_and_word():
    t = confidence_label("EXTRACTED")
    assert "EXTRACTED" in t.plain and "●" in t.plain  # word + glyph (never colour-alone)
    assert "confidence.extracted" in str(t.style)


def test_confidence_label_ascii_fallback():
    assert confidence_label("INFERRED", glyphs=False).plain == "[I] INFERRED"  # ASCII + word
    assert confidence_label("AMBIGUOUS", compact=True, glyphs=False).plain == "[A]"
    assert confidence_label("EXTRACTED", compact=True).plain == "●"


# --- TTY vs plain degradation (the presentation keystone) -------------------


def test_info_on_colour_tty_has_block_art_glyphs_and_ansi():
    c, sio = _console(terminal=True, color=True)
    render_info(c)
    out = sio.getvalue()
    assert "█" in out  # block wordmark
    assert "●" in out  # confidence glyphs
    assert "\x1b[" in out  # ANSI on a colour TTY


def test_info_plain_has_no_ansi_no_block_art_and_ascii_confidence():
    c, sio = _console(terminal=False, color=False)
    render_info(c)
    out = sio.getvalue()
    assert "\x1b[" not in out  # NO ANSI on a plain/non-TTY stream
    assert "█" not in out  # block art degraded to a plain title
    assert "DEEPDIVE" in out
    assert "[E] EXTRACTED" in out  # ASCII confidence markers (cp1252-pipe safe)
    assert "●" not in out  # no non-ASCII glyphs that could crash a cp1252 pipe


def test_set_plain_forces_no_color():
    set_plain(True)
    try:
        assert get_console().no_color is True
    finally:
        set_plain(False)


# --- keystone guard: the style layer must never touch emit/ -----------------


def test_style_layer_never_imports_emit():
    import forensic_deepdive.cli.style as style_pkg

    base = Path(style_pkg.__file__).parent
    for f in sorted(base.glob("*.py")):
        for line in f.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                assert "emit" not in stripped, (
                    f"{f.name} imports emit/ — violates the presentation keystone"
                )
