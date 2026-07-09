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
from forensic_deepdive.cli.style.render import (
    _confidence_split_text,
    print_extract_summary,
    render_trace,
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


# --- styled command rendering (DEC-079) -------------------------------------


def _downstream_payload() -> dict:
    return {
        "matches": [{"qualified_name": "a.ts::f"}],
        "direction": "downstream",
        "chains": [
            {
                "consumer": "a.ts::f",
                "endpoint": "http::POST::/api/x",
                "method": "POST",
                "normalized_path": "/api/x",
                "call_confidence": "EXTRACTED",
                "handler": "H.java::C.m",
                "handles_confidence": "INFERRED",
                "downstream": ["svc.do"],
            }
        ],
        "symbol": "f",
    }


def test_trace_json_mode_is_plain_no_ansi():
    import json

    c, sio = _console(terminal=True, color=True)  # colour TTY, but --json → plain JSON
    render_trace(c, _downstream_payload(), plain=True)
    out = sio.getvalue()
    assert "\x1b[" not in out  # no ANSI even on a colour TTY when piping JSON
    assert json.loads(out)["direction"] == "downstream"


def test_trace_tree_shows_endpoint_handler_and_confidence_words():
    c, sio = _console(terminal=True, color=True)
    render_trace(c, _downstream_payload(), plain=False)
    out = sio.getvalue()
    assert "POST" in out and "/api/x" in out and "via http" in out
    assert "EXTRACTED" in out and "INFERRED" in out  # confidence never colour-alone
    assert "C.m" in out  # the resolved handler


def test_trace_unresolved_is_a_friendly_message():
    c, sio = _console(terminal=True, color=True)
    render_trace(c, {"matches": [], "unresolved": True, "symbol": "nope"}, plain=False)
    assert "no symbol matched" in sio.getvalue()


def test_confidence_split_text_ascii():
    t = _confidence_split_text({"EXTRACTED": 3, "INFERRED": 1, "AMBIGUOUS": 0}, glyphs=False)
    assert "4 cross-stack route" in t.plain
    assert "[E] 3" in t.plain and "[I] 1" in t.plain and "[A] 0" in t.plain


def test_extract_summary_cache_hit():
    from types import SimpleNamespace

    c, sio = _console(terminal=False, color=False)
    print_extract_summary(c, SimpleNamespace(cache_hit=True, output_dir="docs/codebase"))
    out = sio.getvalue()
    assert "cache hit" in out and "\x1b[" not in out


def _fake_extract_result(cache_hit: bool, example_file_count: int = 0):
    """Minimal duck-typed ExtractResult for print_extract_summary (graph_db_path=None
    skips the live DB read)."""
    from types import SimpleNamespace

    facts = SimpleNamespace(
        language_breakdown={"Python": 3},
        repo_name="demo",
        symbol_graph=SimpleNamespace(
            graph=SimpleNamespace(number_of_nodes=lambda: 3, number_of_edges=lambda: 2)
        ),
        file_count=3,
        example_file_count=example_file_count,
        graph_db_path=None,
    )
    return SimpleNamespace(
        cache_hit=cache_hit,
        facts=None if cache_hit else facts,
        output_dir="docs/codebase",
        artifacts=["MAP.md", "AGENT_BRIEF.md"],
        shims=SimpleNamespace(written=[], refreshed=[]),
    )


def test_extract_summary_is_cp1252_safe_when_piped():
    """The styled summary's success check (✓, U+2713) used to be emitted unconditionally and
    crashed a redirected/piped cp1252 stream on Windows (UnicodeEncodeError). On a non-TTY /
    non-colour console it must degrade to ASCII so the whole output encodes to cp1252."""
    for cache_hit in (True, False):
        c, sio = _console(terminal=False, color=False)
        print_extract_summary(c, _fake_extract_result(cache_hit))
        out = sio.getvalue()
        assert "✓" not in out
        out.encode("cp1252")  # must not raise
        assert "\x1b[" not in out  # no ANSI on a non-colour stream


def test_extract_summary_shows_check_glyph_on_utf8_colour_tty():
    """The ✓ is still shown where it can be encoded — a UTF-8 colour TTY — so the degrade
    path didn't simply delete it."""
    c, sio = _console(terminal=True, color=True)
    print_extract_summary(c, _fake_extract_result(cache_hit=False))
    assert "✓" in sio.getvalue()


def test_extract_summary_annotates_demoted_examples():
    """DEC-103: with ROLE_EXAMPLE demotions the Files line carries the in-graph total so an
    examples-only repo doesn't read as a 3-file repo."""
    c, sio = _console(terminal=False, color=False)
    print_extract_summary(c, _fake_extract_result(cache_hit=False, example_file_count=114))
    out = sio.getvalue()
    assert "3 (+114 in graph, demoted as examples/)" in out
    out.encode("cp1252")  # annotation must stay pipe-safe


def test_extract_summary_no_demotions_line_unchanged():
    """DEC-103: zero demotions → no annotation (most repos' output doesn't move)."""
    c, sio = _console(terminal=False, color=False)
    print_extract_summary(c, _fake_extract_result(cache_hit=False))
    assert "in graph, demoted" not in sio.getvalue()


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
