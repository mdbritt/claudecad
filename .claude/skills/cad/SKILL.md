---
name: cad
description: Use when designing, modifying, rendering, or exporting any CAD piece in this repo — defines the build → verify → render → iterate → export loop and its non-negotiable rules.
---

# CAD design loop

Parametric designs live in `designs/<name>/` as `params.py` (every dimension,
mm, single source of truth) + `build.py` (composes claudecad library parts,
verifies, writes GLB/STEP to `out/`). The library is `claudecad/`
(pure geometry) + `tools/` (render/export I/O).

## The loop

1. Edit `designs/<name>/params.py` (or library code for new components).
2. `uv run python -m designs.<name>.build` — builds, **verifies**, writes
   `out/glb/<name>.glb`, and (only if verification passes) `out/step/<name>.step`.
3. `uv run python tools/render.py out/glb/<name>.glb --outdir out/renders/<name>`
4. View every PNG with the Read tool. Judge against reference photos of the
   real-world piece — fetch references, don't design from memory.
5. Iterate 1–4 until the renders read true. Then hand `out/step/<name>.step`
   to the user for Plasticity import (File → Import; parts arrive named).

## Non-negotiable rules

- All dimensions in millimeters, defined only in `params.py`. Derived values
  (link counts, radii) are computed by the library and printed, never set.
- Never show the user renders of geometry that failed verification; fix the
  geometry first. Never export STEP that fails verification (build.py
  enforces this — do not bypass it).
- Verification is ground truth: `check_chain` proves interlock via Gauss
  linking number and non-contact via boolean intersection. "It looks right
  in the render" is not evidence; the report is.
- When a check fails, adjust parameters or geometry — never the check.
- New components go in `claudecad/` as pure functions with pytest coverage
  (`uv run pytest`), following the patterns in `claudecad/jewelry/links.py`.

## Blender renderer

`tools/render.py` needs Blender; default binary is
`/Applications/Blender 4.5 LTS.app/Contents/MacOS/Blender`, override with
env `BLENDER_BIN`. Views: persp, top, front, detail. Bump `--samples` or
`--res` for beauty shots.
