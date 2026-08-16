#!/usr/bin/env python3
"""Render docs/assets/demo.gif — non-interactive, no vhs/ttyd (DEC-122).

vhs (docs/assets/demo.tape, DEC-120) hangs on Windows with no error — a known,
unresolved upstream bug (charmbracelet/vhs#631) independent of which ttyd build is
used. This script replaces it: pure Python + Pillow, runs the *real* CLI against a
scratch copy of tests/fixtures/tiny_fixture, captures real output, and renders a
typed-command / revealed-output terminal animation. No Go toolchain, no ttyd, no
native terminal emulator required on any platform.

Usage:
    uv run --with pillow python scripts/render_demo_gif.py
Wired up as `make demo-gif`. Pillow is NOT a project dependency — `--with` installs it
into an ephemeral overlay for this one script, never touching pyproject.toml/uv.lock.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "tiny_fixture"
SCRATCH = Path(tempfile.gettempdir()) / "deepdive-demo-gif"
OUTPUT = REPO_ROOT / "docs" / "assets" / "demo.gif"

WIDTH, HEIGHT = 1200, 650
PADDING = 28
TOPBAR = 40
LINE_H = 24
FONT_SIZE = 18
MAX_LINES = (HEIGHT - TOPBAR - PADDING) // LINE_H

BG = (40, 42, 54)  # Dracula-ish background — matches the abandoned vhs tape's theme
BAR = (68, 71, 90)
FG = (248, 248, 242)
PROMPT = (80, 250, 123)
COMMENT = (98, 114, 164)
DOTS = [(255, 95, 86), (255, 189, 46), (39, 201, 63)]

COMMANDS = [
    ("$ forensic extract .", ["extract", "."]),
    ("$ forensic graph main", ["graph", "main"]),
]


def find_font() -> ImageFont.ImageFont:
    """Prefer a real monospace TTF where one is known to live; fall back to Pillow's
    own bundled scalable font (Pillow >=10.1) so this never hard-fails on a machine
    without any of the guessed system paths."""
    for candidate in (
        "C:/Windows/Fonts/consola.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/System/Library/Fonts/Menlo.ttc",
    ):
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), FONT_SIZE)
    return ImageFont.load_default(size=FONT_SIZE)


FONT = find_font()


def sanitize(text: str) -> str:
    """ASCII-only. The CLI's own styled output already degrades gracefully off a TTY
    (DEC-078), but a stray Unicode glyph (e.g. the "x" in "N files x M edges") can still
    land outside whatever font this script found — ASCII-folding sidesteps glyph
    coverage entirely rather than gambling on it."""
    return text.replace("\r\n", "\n").strip("\n").encode("ascii", errors="replace").decode("ascii")


def resolve_forensic_exe() -> Path:
    """The 'forensic' console-script next to the current interpreter — this script
    itself runs under `uv run --with pillow`, which layers onto the synced project
    venv, so this is already the right one. Avoids re-invoking through `uv run`
    (whose first-run 'Building/Installed' banner would otherwise leak into the
    recorded output)."""
    ext = ".exe" if os.name == "nt" else ""
    candidate = Path(sys.executable).parent / f"forensic{ext}"
    if candidate.exists():
        return candidate
    found = shutil.which("forensic")
    if found:
        return Path(found)
    raise SystemExit("Could not find the 'forensic' console script. Run `uv sync` first.")


def setup_scratch() -> None:
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    shutil.copytree(
        FIXTURE,
        SCRATCH,
        ignore=shutil.ignore_patterns(".deepdive", ".forensic-deepdive", "docs"),
    )


def run_command(forensic_exe: Path, args: list[str]) -> str:
    result = subprocess.run(
        [str(forensic_exe), *args],
        cwd=SCRATCH,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    return sanitize(result.stdout + result.stderr)


def render_frame(lines: list[str], cursor_on: bool) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, WIDTH, TOPBAR], fill=BAR)
    for i, color in enumerate(DOTS):
        x = 16 + i * 22
        draw.ellipse([x, 14, x + 12, 26], fill=color)
    visible = lines[-MAX_LINES:]
    y = TOPBAR + 16
    for line in visible:
        is_prompt = line.startswith("$ ")
        color = PROMPT if is_prompt else (COMMENT if line.startswith("#") else FG)
        draw.text((PADDING, y), line, font=FONT, fill=color)
        y += LINE_H
    if cursor_on and visible:
        last = visible[-1]
        cursor_x = PADDING + draw.textlength(last, font=FONT) + 2
        cursor_y = y - LINE_H
        draw.rectangle([cursor_x, cursor_y, cursor_x + 10, cursor_y + LINE_H - 4], fill=FG)
    return img


def typed_frames(history: list[str], full_line: str, chunk: int = 3) -> list[Image.Image]:
    frames = []
    for end in range(chunk, len(full_line) + chunk, chunk):
        partial = full_line[:end]
        frames.append(render_frame([*history, partial], cursor_on=True))
    return frames


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    setup_scratch()
    forensic_exe = resolve_forensic_exe()

    frames: list[Image.Image] = []
    durations: list[int] = []
    history: list[str] = [
        "# forensic-deepdive: build the graph + 5 markdown artifacts, then visualize",
    ]
    frames.append(render_frame(history, cursor_on=False))
    durations.append(1200)

    for prompt_line, args in COMMANDS:
        # 1. type the command
        for frame in typed_frames(history, prompt_line):
            frames.append(frame)
            durations.append(45)
        history.append(prompt_line)

        # 2. hold on the completed command line (cursor blink)
        for cursor_on in (True, False, True, False):
            frames.append(render_frame(history, cursor_on=cursor_on))
            durations.append(220)

        # 3. run it for real and reveal the output a few lines at a time
        output_lines = run_command(forensic_exe, args).split("\n")
        revealed: list[str] = []
        for line in output_lines:
            revealed.append(line)
            frames.append(render_frame([*history, *revealed], cursor_on=False))
            durations.append(90)
        history.extend(output_lines)
        history.append("")

        # 4. hold on the finished screen
        frames.append(render_frame(history, cursor_on=False))
        durations.append(1800)

    # final hold
    frames.append(render_frame(history, cursor_on=False))
    durations.append(2500)

    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    shutil.rmtree(SCRATCH, ignore_errors=True)
    print(f"Wrote {OUTPUT} ({len(frames)} frames, {OUTPUT.stat().st_size / 1024:.0f} KiB)")


if __name__ == "__main__":
    main()
