---
name: cad
description: Use when designing, modifying, rendering, or exporting any CAD piece in this repo — defines the build → verify → render → iterate → export loop and its non-negotiable rules.
---

# CAD design loop

Parametric designs live in `designs/<name>/` as `params.py` (every dimension,
mm, single source of truth) + `build.py` (composes library parts, verifies,
writes GLB/STEP to `out/`). Domain-neutral geometry lives in the `claudecad`
package (`core/`, `verify.py`, `assembly.py`, `export.py`, `render/`); domain
packs (e.g. `claudecad.jewelry`, `claudecad.hardware`) hold reusable parts
for a design family. In a consumer project the package comes from PyPI
(`uv add claudecad`); new reusable parts belong in your project, or upstream
as PRs. `claudecad.export`/`claudecad.render` are the only layers that touch
disk/Blender.

## The loop

1. Edit `designs/<name>/params.py` (or library code for new components).
2. `uv run python -m designs.<name>.build` — builds, **verifies**, writes
   `out/glb/<name>.glb`, and (only if verification passes) `out/step/<name>.step`.
3. `uv run claudecad render out/glb/<name>.glb --outdir out/renders/<name>`
4. View every PNG with the Read tool. Judge against reference photos of the
   real-world piece — fetch references, don't design from memory.
5. Iterate 1–4 until the renders read true. Then hand `out/step/<name>.step`
   to the user (Plasticity: File → Import; parts arrive named). For quick
   3D inspection the claudecad REPO (not the pip package) bundles a
   localhost STEP/GLB viewer — `tools/step_viewer/` (repo-dev only).

## Non-negotiable rules

- All dimensions in millimeters, defined only in `params.py`. Derived values
  are computed by the library and printed, never set.
- Never show the user renders of geometry that failed verification; never
  export STEP that fails verification (build.py enforces; do not bypass).
- Verification is ground truth; renders are not evidence. When a check
  fails, adjust parameters or geometry — never the check.
- New components are pure functions in a domain pack with pytest coverage.

## Verification laws (domain-neutral)

- **Interlock** is proven by the Gauss linking number of discretized closed
  centerlines (`verify.linking_number`); **non-contact** by boolean
  intersection == 0 (`verify.intersection_volume`, bbox-disjoint fast path);
  chains of interlocking parts by `verify.check_chain(items, closed,
  interlock_depth)`.
- **Mechanisms** are proven with CONSTRUCTED STATES, never simulation:
  build each functional state as its own solid and gate on differentials —
  insertion = `verify.path_clearance` all-zero along the travel axis;
  lock = blocked state interferes at the station while the freed state
  clears; guards = the blocked motion's station intersects the guard part.
  Functional gates run in the part's LOCAL frame (rigid-invariant) and
  ALWAYS on the shipped (post-finishing) geometry.
  Blocked-leg sweeps must sample the BLOCKING BAND densely (band-scale
  distances — wide stations straddle a thin feature and pass on a sliver);
  envelope-scale distances are for free legs only.
- **Threaded / screw joint** (`hardware/fastener`): a threaded joint is
  proven by the exact 2D axial-section clearance (helical symmetry) — a
  real air gap on the true pitch, jamming under pure-axial shift and wrong
  pitch; the 3D solid is gated valid+manifold for export. Build helical
  ridges by LOFTING explicitly-oriented sections (x=axial, y=radial) along
  the helix, one turn stacked per pitch — never `sweep()` a profile along a
  helix: the sweep frame drifts, tilting the profile (breaks periodicity,
  renders as stacked discs, not a continuous spiral).
- **Multi-body / rolling set** (`hardware/bearing`): a mechanism whose moving
  element is a SET of bodies is gated by moving the set as ONE compound
  (`screw_clearance` accepts it directly). Discrete N-fold symmetry means one
  360/N period proves the full revolution. On axisymmetric obstacles the
  sweep's value is PROVING the axisymmetry — material-adding or
  raceway-displacing defects (eccentric groove, inward dent) fail it; every
  design carries a negative control that pins this. Clearance mechanisms read
  crisp 0 — any nonzero is a defect, never noise.
- **Hinged / limited-travel joint** (`hardware/snapbox`): gated by partial-arc
  sweeps about the hinge axis — `screw_clearance` with `lead=0` and `center`
  ON the hinge axis (off-origin centers are supported and must be used;
  never re-origin the model to dodge them). Travel limits are proven by a
  SAME-PARAMETER differential: free within travel, blocked past the stop,
  along one angular sweep. Snap retention is the two-state differential at
  the closed pose (relaxed blocked / deflected free — blocking MOTION, not
  touching). Every hinged design carries a displaced-center negative
  control: sweeping about a center off the true axis must fail, proving the
  gate detects a mis-built hinge.
- **Attachment** is proven by linking number against a closed loop through
  the mounting circuit — the loop must genuinely cross the other part's
  plane (a coplanar loop can never link).
- **Clearance/fit** is measured by `verify.clearance(a, b)` — exact minimum distance, 0.0 when touching or penetrating (pair with intersection to distinguish). Near-contact fits gate via `check_chain(..., max_gap=...)`: adjacent pairs must sit within the band, not merely avoid penetration.
- **Single parts verify functionally too**: gate them against REFERENCE
  solids — a bar seated in a V-groove, a pin in a bore, a mating dummy —
  using the same fit bands and free/blocked differentials (e.g. bar blocked
  pushed down, free sliding along the groove). Proof solids may ship in the
  GLB so the render shows the proof, but NEVER in the STEP.

## Construction laws (OCCT, hard-won — see the dated specs for evidence)

- Twisted closed tubes: ONLY two overlapping half-loop ruled lofts, fused.
  Forbidden (all gauntlet-proven broken): sweep() in any frame mode,
  ruled=False lofts, single closed lofts with first==last section,
  Shell/Solid reassembly, Edge.trim on sweep spines.
- Cavities are subtracted blocks, never OCCT shell/thicken.
- Prefer analytic (Box/Cylinder/planar-sweep) construction; `is_valid` is
  necessary but NOT sufficient — boolean-robustness is what the gates test.
- Overlapping unions in generic position are robust; coincident-face fuses
  are degenerate and forbidden.
- Coincident faces seam CUTS too: a cutter face landing exactly on another
  cut's edge or face makes non-manifold seams — overlap cuts ~0.5mm past
  each other (dogfood-proven: a relief slot topping out exactly at a V apex
  edge went non-manifold).
- A 45°-rotated square prism closes back up above its half-diagonal — only
  its LOWER half cuts a V. Vertical walls above the flank tops need their
  own rectangular cut (dogfood-proven: the closing upper diamond left
  534 mm³ of hidden interference that renders didn't show).

## Domain notes: jewelry (accumulated benchmark learnings)

- Chains: chirality — twisted links are handed; chains alternate link
  handedness (`chains._link_bases`) or the two junction types diverge.
  Open (non-closed) chains use `chains.open_arc`, whose parity follows the
  original position index.
  Dense chains may thread depth 2 (`interlock_depth`). Real cuban pitch ≈
  0.49 × link length; the look comes from flat lie + diamond-cut facets.
- `finishing.diamond_cut` grinds an assembled chain flat (slab intersection,
  severing caught by piece_count); relief slots via `assembly.relieve` (or
  `assembly.expand` composition when cutters are shared/expensive — see
  cuban_bracelet).

## Blender renderer

`claudecad render` needs Blender; default binary is
"/Applications/Blender 4.5 LTS.app/Contents/MacOS/Blender", override with
env `BLENDER_BIN`. Views: persp, top, front, detail. Renders are optional
for library development (CI runs without Blender); they are required for
design acceptance.
