# forensic-deepdive — a couple of convenience targets, not a build system.
# Day-to-day commands are `uv run ...` (see CLAUDE.md / README "Local development").

.PHONY: demo-gif

## Regenerate docs/assets/demo.gif (DEC-122). Pure Python + Pillow — no vhs, no ttyd,
## no Go toolchain. Pillow is not a project dependency; `--with` installs it into an
## ephemeral overlay for this one script only.
demo-gif:
	uv run --with pillow python scripts/render_demo_gif.py
	@echo "Review docs/assets/demo.gif, then commit deliberately (it's gitignored by default)."
