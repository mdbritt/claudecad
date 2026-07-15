# Ball bearing — claudeCAD hardware pack, generality Phase 2

**Date:** 2026-07-15
**Status:** Approved
**Predecessors:** 2026-07-14-threaded-fastener-design.md (Phase 1: built
`screw_clearance`, whose `lead=0` degeneration this piece consumes; and the
method law this piece applies — boolean gates for CLEARANCE mechanisms,
analytic gates for CONTACT mechanisms)

Phase 2 of the three-piece hardware roadmap (bolt+nut → **ball bearing** →
snap-fit/hinge). **Project lens (explicit since 2026-07-15): claudeCAD is
tooling for the community; this bearing is a test article whose job is to
force new verification machinery, not to be a product.** What it forces:
multi-body moving sets in gates, symmetry-period sampling, and per-ball
capture differentials.

## Problem

Every gate in the repo moves ONE solid against fixed geometry (a tongue, a
ring, a nut). Real mechanisms move *sets* of bodies: a bearing's 7 balls orbit
together between two races. Verifying that requires (a) treating a multi-body
set as the moving object of a gate, and (b) exploiting the set's discrete
symmetry so the sweep is affordable. A deep-groove ball bearing is the minimal
mechanism that forces both.

Deliverable: a **608-geometry cageless deep-groove ball bearing** (bore 8 mm —
deliberately mating the Phase 1 M8 bolt — OD 22, width 7, 7 balls Ø 3.969
nominal), verified in the assembled state, exported to STEP.

## What "a working bearing" means in static B-rep

A bearing is a **clearance mechanism**: in the model, balls never touch the
races (real bearings run on radial play + film). Per the Phase 1 method law,
boolean interference gates are the right tool and must read **crisp 0** — any
nonzero interference is a real modeling defect, not facet noise. Four proofs:

1. **Rest clearance:** every ball has zero boolean interference with both
   races AND a positive exact gap (`verify.clearance`) no larger than the
   `REST_MAX_GAP` band — near-contact, never touching (the cuban chain's
   `max_gap` concept, applied radially).
2. **Orbital free-spin (the multi-body gate):** the 7-ball ring, moved as ONE
   compound, is swept about the axis with `screw_clearance(balls, races, AXIS,
   center, lead=0, turns=1/7, n)` — interference must be 0 at every station.
   - *Symmetry-period sampling:* the ball ring is 7-fold symmetric, so one
     360/7° period covers every relative pose of a full turn.
   - *Why this is not a tautology:* on correctly built races (exact solids of
     revolution) every station is symmetry-equivalent to station 0 — and the
     gate exists to PROVE that, not assume it. Any axisymmetry-breaking
     construction defect that ADDS material to the ball path or displaces the
     raceway — an eccentric (off-axis) groove, an inward protrusion or dent,
     a mis-centered race — fails the sweep. (Material-REMOVING defects like a
     filling notch cannot create interference and are caught by the capture
     differentials instead, if they breach the shoulders.) It is the
     rotational sibling of the bolt's wrong-lead leg: a check that the
     geometry actually has the symmetry the mechanism depends on.
3. **Capture differential (per ball, by symmetry checked on one):** with both
   races present, a ball pushed radially outward, radially inward, and axially
   both ways (`path_clearance`, distance ≥ its escape distance) is BLOCKED
   (interference > 0 at some station); with the **outer race removed**, the
   radially-outward push runs FREE (0 everywhere) — the carabiner's escape
   differential, applied per ball. Balls are placed as rotation-copies of one
   ball, so one ball's differential + the placement law covers all seven.
4. **Ball ring integrity:** all ball-pair boolean interferences 0 and center
   spacing = pitch-circle chord (placement law pinned by test; the orbit gate
   moves the ring rigidly, so spacing is invariant by construction — asserted
   once statically).

Plus the standing pack proofs: every part valid ∧ manifold ∧ single solid
(`check_solid.ok` — the Phase 1 lesson: `is_valid` alone is not enough), and
the exported assembly pose is itself gated (shipped-geometry guard, Phase 1's
I1 lesson).

## Approach (decided: multi-body orbital gate)

- **Races as solids of revolution:** inner and outer race sections revolved
  about Z — analytic 2D sections (rectangles minus a circular groove arc), no
  shells, no sweeps (nothing helical here; the thread laws don't apply).
  Groove radius = `osculation × ball_d` with osculation default **0.52**
  (52 % — the standard deep-groove conformity band is ~51.5–53 %); groove
  centers on the pitch circle.
- **Balls:** `Sphere(ball_d/2)` placed at pitch radius, rotation-copied 7×
  about Z (the placement law); the rest gap comes from the osculation (see
  the amended nominal-numbers section).
- **The moving set:** the 7 balls unioned/compounded as ONE shape passed as
  `moving` to `screw_clearance` — this is deliberately the FIRST multi-body
  `moving` in the repo and the tooling point of the phase. `screw_clearance`
  already accepts any build123d shape; if Compound behaves badly under
  `intersection_volume` the fallback is a fused union (both verified in the
  milestone-1 spike before the plan is written — Phase 1's process lesson:
  spike the risky geometry before planning on it).
- *Rejected — per-ball orbit:* same physics by symmetry, ~7× the boolean
  cost, and never exercises a multi-body moving set (the tooling payoff).
- *Rejected — analytic radial-section gate:* exact and fast (races are
  axisymmetric so ball-race clearance reduces to 2D section math), but the
  method law reserves analytic gates for contact mechanisms; a clearance
  mechanism's booleans are already crisp. Noted as a possible future
  cross-check, not the gate.

## Nominal numbers (verified arithmetic; tuned values land in the spike)

608: bore 8.0, OD 22.0, width 7.0, pitch circle Ø 15.0. Balls 7 × Ø 3.969
(5/32″ standard complement). Pitch circumference 47.12 mm vs 27.78 mm of ball
diameters → center spacing 6.73 mm, ball-to-ball surface gap ≈ 2.76 mm
(comfortable). *(Amended after the milestone-1 spike: the planned separate
`radial_play` parameter is dropped — the osculation itself supplies the rest
gap, `rest_gap = groove_r − ball_d/2` = 0.0794 mm at defaults, and a second
play parameter would double-count. The gap band is gated by `REST_MAX_GAP`.
Still a design value, not a manufacturing clearance — real C0 play is
~0.005–0.018 and out of scope like the clasp's `clearance`.)* Shoulder heights and groove depth
are derived params with validation inequalities (shoulders must overlap the
ball's equator enough to capture radially and axially: the radial gap between
inner-shoulder OD and outer-shoulder ID must be < ball_d);
exact defaults are tuned in the milestone-1 spike and pinned by tests.

## Components

### `claudecad/hardware/bearing.py` (new, pure geometry — mirrors carabiner/fastener conventions)
- `BearingParams` (frozen dataclass, mm, value-carrying ValueErrors): `bore`,
  `outer_d`, `width`, `n_balls`, `ball_d`, `osculation`, `shoulder_frac`,
  computed props (pitch radius, groove radius, shoulder radii, rest gap) and
  the capture inequality in `__post_init__`.
- `inner_race(p) -> Solid`, `outer_race(p) -> Solid` — revolved sections.
- `ball(p, i) -> Solid` — the i-th ball (rotation-copy placement law).
- `ball_ring(p) -> Shape` — all balls as the single multi-body moving set.
- Module gate fixtures (one source for design + tests): `AXIS`, orbit
  station count, escape distances, `REST_MAX_GAP` (the near-contact band).

### `claudecad/verify.py` (extend only if the spike demands)
- `screw_clearance` is reused as-is (`lead=0`). If the spike shows compounds
  need help, the minimal general fix lands in verify (e.g. accepting an
  iterable of solids by fusing) — decided by evidence, not speculatively.

### `designs/bearing_608/` (new)
- `params.py` (`P = BearingParams()`), `build.py` (build → GLB always → gate
  → STEP on pass; same skeleton as `designs/bolt`). Gate prints: parts clean,
  rest clearance + gap band, orbital sweep max (== 0), capture differential
  legs, shipped-assembly guard.

### `.claude/skills/cad/SKILL.md` (extend)
- Add the multi-body/symmetry law: *a multi-body mechanism is gated by moving
  the body SET as one compound; discrete N-fold symmetry means one 360/N
  period proves the full revolution; on axisymmetric obstacles the sweep's
  value is proving the axisymmetry (construction defects fail it).*

## Verification & testing

- Unit: params validation (capture inequality, osculation band, geometry
  closes: n_balls fit the pitch circle); parts clean (valid+manifold+single);
  placement law (ball centers on pitch circle, equal spacing).
- Functional (the heart): the four proofs above — rest clearance + gap band,
  orbital free-spin 0 at every station over one period, capture differential
  (blocked with races / free without outer), ball-pair 0.
- Negative control (pins the "not a tautology" claim): a deliberately notched
  outer race (test-local geometry) must FAIL the orbital sweep — the gate
  detects broken axisymmetry. This is the test-side twin of the bolt's
  wrong-lead leg.
- Integration: full `designs/bearing_608` gate green; STEP round-trips 9
  named parts (2 races + 7 balls); registered in `tests/test_designs_import.py`
  (hardcoded list — Phase 1 lesson, it does NOT auto-discover).
- Visual: renders + STEP viewer vs a real 608 reference photo; Mike judges in
  Plasticity (as final acceptance, not the gate).

## Out of scope

- Cage/retainer (future extension — clearance vocabulary already exists).
- Assemblability (a cageless deep-groove cannot be filled without eccentric
  displacement; we model the assembled state, same precedent as the chain's
  interlocked links).
- Manufacturing clearances/tolerances, load ratings, contact mechanics, seals
  and shields (608-2RS lips), lubricant.
- Rolling kinematics (ball spin/cage speed) — the static orbit sweep is the
  free-spin proof; no simulation.

## Milestones

1. **Geometry spike (the known risk, before the plan's code is written):**
   revolved race sections + one ball; verify manifoldness of the grooved
   races, the capture inequality at defaults, and that `screw_clearance`
   accepts the multi-ball compound (fallback: fused union). Tuned defaults
   come out of this spike.
2. `BearingParams` + races + balls, parts-clean and placement tests green.
3. The four functional proofs + the notched-race negative control green.
4. `designs/bearing_608` gate + shipped-assembly guard green, STEP exported.
5. Render vs reference; skill law added; user acceptance in Plasticity.
