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

**Twisted centerline, swept round profile.** The twist is modeled as the
metal deforms: each point of the planar stadium centerline at position x
along the link rotates about the link's long axis by phi(x) =
twist_deg * (x / length), with x in [-length/2, +length/2] — a linear ramp
through zero at the link center, reaching +-twist_deg/2 at the two ends, so
the link stays symmetric.
The twisted curve is sampled, fit with a closed periodic BSpline, and the
circular wire profile is swept along it.

- Interlock verification is unchanged: the Gauss linking number consumes the
  discretized twisted centerline directly.
- twist_deg = 0 must reproduce the planar curb link within tolerance (test).
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
  `twist_deg: float` (validated to a spike-established safe range) and
  `n_spline: int` (centerline sampling density for the BSpline fit).
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

### `designs/cuban_bracelet/` (upgrade in place)
- `params.py`: switch to `CubanLinkParams` (adds `TWIST_DEG` via the link
  params) and add `CUT_Z`. Same probe-then-verify workflow to find the new
  frontier — with twist, pitch should drop below 10 and tilt toward flat;
  the gate decides.
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
