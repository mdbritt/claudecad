# Box clasp — claudeCAD cuban bracelet closure

**Date:** 2026-07-13
**Status:** Approved
**Predecessors:** 2026-07-12-claudecad-design.md (milestone 5),
2026-07-13-twisted-cuban-link-design.md (the chain this closes)

## Problem

The v2 bracelet is a closed seamless loop — real Miami cubans open and close
with a box clasp: a rectangular box body, a folded V-spring tongue that
clicks in, and hinged side safety latches. Mike wants the FUNCTIONAL
mechanism modeled (not a decorative block): geometry that provably works,
with real pivots and detents, modeled in the closed/worn state.

## What "functional" means in static B-rep

Parts do not articulate in a STEP file. Functionality is proven the same
way the chain's interlock is proven — by ground-truth geometric checks on
explicitly constructed states:

1. **Insertion**: the COMPRESSED tongue, sampled at N stations along the
   insertion axis, has zero intersection with the box at every station.
2. **Lock (differential)**: at a partial-extraction station, the RELAXED
   tongue intersects the box's retention lip (> 0 = blocked) while the
   COMPRESSED tongue at the same station has zero intersection (pressing
   the release button frees it). This differential IS the click mechanism.
3. **Latch guard**: with latches closed, the compressed tongue's extraction
   station intersects the latch (> 0 = the safety works); the closed latch
   itself intersects nothing (0 = it sits clear).
4. **Attachment**: each end link threads its clasp lug — Gauss linking
   number vs a synthetic closed loop through the lug bar + body.
5. All clasp parts pairwise zero-intersection in the closed state (except
   the intended pin-in-bore coincidences, which are clearance-fitted).

## Approach (decided)

**Prismatic construction**: every part from planar profiles, extruded and
booleaned — analytic geometry throughout (the twisted-loft construction law
applies only to twisted closed tubes; nothing here is one). The box cavity
is a subtracted block, NOT an OCCT shell/thicken operation (fragile).
Rejected: shell ops; importing a non-parametric downloaded model.

## Components

### `claudecad/jewelry/clasps.py` (new, pure geometry)
- `BoxClaspParams` (frozen dataclass, mm, validated with value-carrying
  ValueErrors): box outer length/width/height (width defaults to link
  width; height defaults to 2*CUT_Z so the flat faces continue the
  diamond-cut chain), wall thickness, mouth slot dims, retention lip depth,
  blade thickness, leaf thickness, leaf relaxed angle / spring lift,
  release-button dims, lug length, bar diameter, latch dims (arm length,
  thickness, bore), pin diameter, and a single `clearance` (default 0.15 —
  slide-fit design value; manufacturing tolerances remain out of scope).
- `box_clasp(p) -> ClaspAssembly` where `ClaspAssembly` is a small
  dataclass: `parts: dict[str, Solid]` (clasp_box, clasp_tongue,
  clasp_latch_l, clasp_latch_r, clasp_pin_l, clasp_pin_r — tongue in the
  RELAXED state, latches CLOSED: the export/worn state), plus
  `tongue_state(state: Literal["relaxed","compressed"]) -> Solid`,
  `insertion_axis: Vector`, `stations(n) -> list[Location]` (sampled
  insertion/extraction positions), and `attachment_loops: tuple[np.ndarray,
  np.ndarray]` (closed centerline loops through each lug's bar circuit, for
  linking checks).
- Pins are concentric with latch bores and box ears BY CONSTRUCTION
  (shared axis parameters), with radial `clearance` in the bores.

### `claudecad/verify.py` (extend)
- `path_clearance(moving: Solid, fixed: Solid, axis, distance, n) ->
  list[float]` — intersection volume at n stations of `moving` translated
  along `axis` up to `distance`. Pure composition of existing primitives;
  numbers reported, no pass/fail policy baked in (callers assert).

### `claudecad/jewelry/chains.py` (extend)
- `open_arc(p: ChainParams, target_circumference, gap_arc_length) ->
  tuple[list[PlacedLink], LoopInfo]` — the closed-loop placement minus the
  links whose arc positions fall inside the clasp gap; same chirality
  alternation, same derived-count law; the two arc-end tangent Locations
  are exposed on LoopInfo (new fields `gap_start: Location`,
  `gap_end: Location`) so the clasp lugs align to the chain ends.

### `designs/cuban_bracelet/` (extend)
- `params.py`: CLASP section (BoxClaspParams instance + gap sizing).
- `build.py`: open arc + clasp assembly bridging the gap + diamond_cut on
  links (clasp faces are built flat) + full gate: all existing chain checks
  plus the five functional checks above. STEP exports chain links +
  6 named clasp parts.

## Verification & testing

- Unit: each clasp part valid/manifold/single-piece; params validation;
  two tongue states differ only in leaf angle (blade region identical);
  pin/bore concentricity and radial clearance.
- Functional (the heart): insertion sweep all-zero; lock differential
  (relaxed blocked / compressed free at the same station); latch guard
  (blocks compressed extraction; sits clear when closed); attachment
  linking = +-1 both ends.
- Integration: full-bracelet gate green (chain checks + clasp checks);
  STEP round-trip part count.
- Visual: clasp proportions judged against Miami cuban box-clasp reference
  photos (fetched during implementation); renders + STEP viewer; user is
  final judge in Plasticity.

## Out of scope

- Spring-force/FEA reasoning of the leaf (geometry only; leaf thickness and
  travel are design values calibrated visually).
- Manufacturing tolerances beyond the single stated clearance value.
- Articulated/animated states beyond the constructed ones (relaxed,
  compressed, closed latches).

## Milestones

1. Box + two-state tongue parts, insertion + lock checks green.
2. Latches + pins, guard checks green.
3. Open-arc integration, attachment linking, full-bracelet gate green.
4. Renders vs references + STEP to Plasticity (user acceptance).
