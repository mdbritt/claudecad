# Twisted cuban link — claudeCAD upgrade

**Date:** 2026-07-13
**Status:** Approved
**Predecessor:** 2026-07-12-claudecad-design.md (v1 benchmark shipped; density and
V-groove rated PARTIAL)

## Problem

The v1 bracelet uses `curb_link`: a planar oval of round wire. Task 11's
clearance probe proved this is a design-space ceiling, not a tuning miss:
`length <= 2*pitch` caps adjacent overlap at 50%, width 14 is required for
interlock room, wire >= 4.3 never clears at pitch 10. Real Miami cuban links
are individually twisted and then ground flat (diamond-cut), which is what
lets them nest nearly coplanar with tiny openings, dense packing, and the
signature V-groove. This upgrade adds both features.

## Approach (decided)

**Twisted centerline, RULED LOFT through circular sections** (amended
2026-07-13 after the spike gate; originally a periodic-spline sweep). The
twist is modeled as the metal deforms: each point of the planar stadium
centerline at position x along the link rotates about the link's long axis
by phi(x) = twist_deg * (x / length), with x in [-length/2, +length/2] — a
linear ramp through zero at the link center, reaching +-twist_deg/2 at the
two ends, so the link stays symmetric.

The solid is built by lofting circular sections (ruled=True) placed at
n_sections (default 144) analytically computed frames along the twisted
centerline (exact point, tangent, and a smooth periodic x_dir from the
twisted vertical), keeping the Solid that loft() returns directly.

**Why ruled loft (spike-established, all alternatives gauntleted):** every
closed-twisted-path sweep in OCCT 7.x fails structurally — the corrected
frame cannot close the seam (BRepCheck_UnorientableShape; ShapeFix provably
cannot repair it), the Frenet frame oscillates near the low-curvature sides
producing a locally self-intersecting surface whose plane cuts return
garbage (BRepCheck_InvalidImbricationOfWires), and smooth (ruled=False)
lofts overshoot between sections with the same boolean pathology. The ruled
loft passed the full gauntlet at twist 20-60: valid/manifold/single-solid,
volume within 0.05% of the tube-theorem value, and every slab cut and
link-link boolean correct. The faceting (144 sections) renders as faint
brushed texture, invisible at bracelet scale; n_sections is a quality dial.

- Interlock verification is unchanged: the Gauss linking number consumes the
  discretized twisted centerline directly.
- The twist map at twist_deg = 0 must reproduce the planar stadium
  centerline within tolerance (test at the centerline level; the SOLID
  builder validates twist_deg to [20, 60], so planar solids remain
  `curb_link`'s job).
- Volume ~= pi * (wire_d/2)^2 * curve_length remains a test invariant.

**Diamond-cut at chain level.** After assembly (straight or closed loop),
boolean-subtract two half-space boxes: everything above +cut_z and below
-cut_z (world Z, chain midplane = Z0). One uniform cut across all links,
exactly like grinding an assembled chain. Centerlines are not cut.

Rejected alternatives: bowed/saddle link (documented fallback if the twisted
sweep proves pathological in OCCT); direct solid twist deformation
(non-affine — impossible in clean B-rep, would break Plasticity editability).

## Components

### `claudecad/jewelry/links.py` (extend)
- `CubanLinkParams`: frozen dataclass — `length`, `width`, `wire_d`,
  `n_centerline` (same semantics/validation as `LinkParams`) plus
  `twist_deg: float` (validated to the spike-established range [20, 60] —
  outside it the loft construction is unverified) and `n_sections: int`
  (loft section count, default 144, validated >= 32).
- `cuban_link(p: CubanLinkParams) -> tuple[Solid, Wire]` — same contract as
  `curb_link`: solid + untessellated centerline wire, both centered at the
  origin, long axis X.
- `curb_link` and `LinkParams` remain unchanged.

### `claudecad/jewelry/chains.py` (refactor + extend)
- `build_link(params: LinkParams | CubanLinkParams) -> tuple[Solid, Wire]` —
  single dispatch point.
- Shared placement helper extracted from `straight_chain`/`closed_loop` (the
  duplication flagged in the v1 final review); public signatures unchanged;
  `ChainParams.link` widens to `LinkParams | CubanLinkParams`.

### `claudecad/jewelry/finishing.py` (new)
- `diamond_cut(links: list[PlacedLink], cut_z: float) -> list[PlacedLink]` —
  subtracts the two half-spaces from every solid; centerlines pass through
  untouched. `cut_z <= 0` or cut boxes that miss the chain entirely raise
  ValueError with values.

### `claudecad/verify.py` (extend)
- `SolidReport` gains `piece_count` (number of disjoint solids); `ok`
  requires `piece_count == 1`. A cut that severs a wire splits the link into
  pieces and fails the chain report with a named message. Topological
  guarantee preserved: an unsevered tube around a linked centerline stays
  linked, so linking number + zero intersection + single-piece together still
  prove the chain holds.
- `check_chain` gains `interlock_depth: int = 1` (discovered during the
  spike probe): dense cuban chains legitimately thread each link through its
  TWO nearest neighbors per side. Pairs within `interlock_depth` index
  distance (cyclic when closed) must be linked (|Lk| >= 1); pairs beyond it
  must be unlinked; ALL pairs must have zero intersection. depth=1
  reproduces today's behavior exactly (existing tests unchanged); the dense
  bracelet uses depth=2.

### `designs/cuban_bracelet/` (upgrade in place)
- `params.py`: switch to `CubanLinkParams` (adds `TWIST_DEG` via the link
  params) and add `CUT_Z`. Frontier probing (2026-07-13, 176 arc-placed
  combos) falsified the "pitch drops below 10" expectation: real Miami
  cubans run pitch ~= 0.49*length (same 50% overlap v1 shipped), and denser
  pitches structurally collide at the 2-apart pair for every proportion
  tried. What the twist actually buys is FLAT LIE at that pitch: verified
  passing config = v1 dims (20x14x4.1) at twist 60, pitch 10, tilt 20
  (vs v1's tilt 34), all pairs zero-intersection, neighbors linked. The
  diamond cut then supplies the facets.
- `build.py`: insert `diamond_cut` between `closed_loop` and `check_chain`.

## Verification & testing

- All existing checks unchanged and unweakened.
- New tests: `cuban_link` validity/dimensions/volume; twist_deg=0 planar
  regression vs `curb_link`; twisted-pair interlock (Lk = +-1, intersection
  0); `diamond_cut` produces flat faces (bbox Z extent == 2*cut_z), preserves
  single-piece links at sane cut_z, and a deliberately severing cut_z is
  caught by the chain report; dispatch returns the right component per params
  type.
- Spike gate (before the implementation plan is written): closed periodic
  BSpline sweep of a twisted stadium in build123d proven in scratchpad —
  valid solid, volume invariant, boolean-safe, safe twist_deg range recorded.
  If the sweep is pathological, fall back to the bowed-link alternative and
  amend this spec.

## Acceptance

The two v1 PARTIAL checklist items re-judged against the same reference
photos, in Blender renders and the localhost STEP viewer:
1. Packing density comparable to a real Miami cuban (adjacent overlap well
   past the planar 50% ceiling).
2. Top view shows the diamond-cut V-groove: flat facets, continuous surface.

Plus: verification gate passes on the full closed loop; STEP imports into
Plasticity as named editable solids (user-judged).

## Out of scope

- Box clasp (still milestone 5 of the v1 spec).
- Manufacturing constraints (unchanged from v1).
- Mesh-based deformations of any kind.
