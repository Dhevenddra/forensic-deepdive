"""Console-only presentation layer (DEC-078, v0.7 Track B).

The styled CLI surface — a shared themed Rich ``Console``, the confidence palette, a static
ASCII banner, and a data-driven capability panel. **Presentation keystone (DEC-071 §1b):**
this package styles the Console (stdout/stderr) ONLY. It NEVER imports ``emit/`` and never
emits ANSI to an artifact file or a machine-output stream (``serve``, MCP stdio). It degrades
to plain text on a non-TTY, under ``--plain``, and under ``NO_COLOR``; confidence is never
encoded by colour alone (a glyph + word always accompany it).
"""

from forensic_deepdive.cli.style.banner import capability_panel, render_banner, render_info
from forensic_deepdive.cli.style.console import (
    FORENSIC_THEME,
    confidence_label,
    get_console,
    set_plain,
)

__all__ = [
    "FORENSIC_THEME",
    "capability_panel",
    "confidence_label",
    "get_console",
    "render_banner",
    "render_info",
    "set_plain",
]
