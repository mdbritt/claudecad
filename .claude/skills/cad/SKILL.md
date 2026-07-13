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

Dense-chain designs verify with `check_chain(..., interlock_depth=N)` — see
the 2026-07-13 spec. `designs/cuban_bracelet/probe.py` is the cheap pairwise
frontier probe for parameter tuning; the construction law for twisted closed
tubes (overlapping half-loop ruled lofts ONLY) lives in that spec's "Why
ruled loft" section. Twisted (chiral) links must alternate handedness along
a chain — with identical chiral links every second junction is a different,
non-congruent geometry and interpenetrates; `chains._link_bases` implements
the law and its docstring carries the evidence.

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

## Quick STEP viewing

`tools/step_viewer/` is a self-contained browser STEP viewer (Online3DViewer +
occt-import-js WASM, vendored by `tools/step_viewer/fetch_libs.sh` — run it
once per clone). Serve the repo root on port 8123 (`python3 -m http.server
8123 --directory .` — the port is baked into the vendored engine patch) and
open `http://localhost:8123/tools/step_viewer/?model=/out/step/<name>.step`.
Drag-and-drop of .step/.glb files also works.

## Mechanism verification (clasps and future moving parts)

Mechanisms are proven statically with CONSTRUCTED STATES, never simulation:
build each functional state as its own solid (e.g. the clasp tongue's
relaxed vs compressed leaf) and gate on differentials — insertion =
`verify.path_clearance` all-zero along the travel axis; lock = relaxed
state interferes at the extraction station while compressed clears; guards
= the blocked motion's station intersects the guard part. Functional gates
run in the part's LOCAL frame (rigid-invariant) and ALWAYS on the shipped
(post-relief/post-cut) geometry. Open chains use `chains.open_arc` (parity
follows original position indices); attachment is proven by linking number
against the lug's closed loop — the loop must genuinely cross the link's
plane (a coplanar loop can never link). See the 2026-07-13 box-clasp spec.
