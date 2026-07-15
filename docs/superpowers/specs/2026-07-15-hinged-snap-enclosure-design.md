# Hinged snap enclosure — claudeCAD hardware pack, generality Phase 3

**Date:** 2026-07-15
**Status:** Approved
**Predecessors:** 2026-07-14-threaded-fastener-design.md (Phase 1: built
`screw_clearance`, including the off-origin rotation-center fix this piece is
the first design to consume), 2026-07-15-ball-bearing-design.md (Phase 2: the
negative-control pattern and lead=0 rotational gates this piece extends to
partial arcs), 2026-07-13-box-clasp-design.md (the constructed two-state
pattern the snap latch reuses).

Phase 3 — the finale of the three-piece hardware roadmap (bolt+nut → ball
bearing → **hinged snap enclosure**). **Project lens: claudeCAD is tooling for
the community; this box is a test article.** What it forces: partial-arc
travel gates about an off-origin axis, and a travel-limit differential (free
and blocked along the SAME motion parameter).

## Problem

Every rotational gate so far is a full revolution about the world origin (the
bearing's orbit) or no rotation at all. Real hinged mechanisms move through a
PARTIAL arc about an axis that is nowhere near the origin, and they have hard
travel limits. Neither pattern exists in the repo:

- The off-origin `center` argument of `screw_clearance` was fixed in Phase 1's
  review (rotation about the line through `center`, not about the origin) but
  **no design has ever exercised it** — the bolt and bearing both rotate about
  the world Z axis. An unconsumed code path in verification tooling is a
  liability; this piece consumes it in anger.
- No gate distinguishes "free within travel, blocked beyond travel" along one
  motion. The clasp/carabiner differentials compare different states or
  different motions.

Deliverable: a small **parts-box** — base, lid on a pin hinge, closed by a
cantilever snap latch — verified in constructed states, exported to STEP as
named parts (base, lid ×2 states shipped as the closed relaxed pose, pin).

## What "a working hinged snap box" means in static B-rep

Parts do not swing in a STEP file. Function is proven on constructed states
and swept arcs (all boolean gates crisp-0 — clearance mechanism, per the
method law):

1. **Swing-arc clearance (the off-origin partial-arc gate):** the lid in its
   DEFLECTED-latch state, swept about the hinge axis across the full swing
   arc (`screw_clearance` with `lead=0`, `axis` = the hinge axis direction,
   `center` = a point ON the hinge axis — far from the origin — and
   `turns = swing_deg/360`; the lid is constructed closed, so the sweep runs
   closed→open — clearance-equivalent to closing), has zero interference
   with the base + pin at every station. This is simultaneously the insertion proof (the lid can
   close) and the first real consumer of the off-origin rotation center.
2. **Travel-limit differential (new pattern):** the OPEN lid swept FURTHER
   open must hit the hinge stop — stations beyond `stop_deg` interfere
   (blocked > 0) while stations within travel are free (== 0). Free and
   blocked along the same angular parameter, split at the stop angle: this
   is what proves the stop actually limits travel.
3. **Snap retention differential (clasp pattern, second consumer):** at the
   closed pose, the RELAXED latch blocks the opening arc (the first few
   degrees of opening sweep interfere with the catch) while the DEFLECTED
   latch sweeps open free. The differential IS the click.
4. **Hinge-pin capture:** the pin is clearance-fitted through base knuckles
   and lid knuckles (never touching — bores at `pin_d/2 + clearance`, the
   carabiner pin pattern); with knuckles present the pin's radial escape is
   blocked, axially blocked by end knuckles (escape differentials).
5. **Negative control (house standard since Phase 2):** a defective base
   whose knuckle bores are displaced off the pin axis must FAIL the
   swing-arc gate — proving the sweep detects a mis-built hinge rather than
   assuming a correct one.

Plus standing proofs: every part `check_solid(...).ok` (valid ∧ manifold ∧
single, corrected test), and the shipped pose (closed, relaxed latch, pin
seated) gated: intended near-contacts within a stated band, everything else
crisp-0 pairwise.

## Approach (decided)

**Prismatic construction** (box-clasp precedent — the twisted-loft and thread
laws don't apply; nothing here is helical): base and lid are shelled-by-
subtraction boxes (cavity = subtracted block, never OCCT shell), knuckles are
cylinders fused in generic position (no coincident-face fuses), bores are
cylinder cuts with radial `clearance`, the cantilever latch is an integral
prismatic tab on the lid with a catch bar on the base.

- **Two lid states** (`lid_state("relaxed"|"deflected")`, the clasp's
  tongue-state convention): identical except the latch tab region — deflected
  rotates/translates the tab by the deflection needed to clear the catch.
  Deflection is a CONSTRUCTED state; elasticity/FEA is out of scope
  (precedent: clasp leaf, carabiner gate).
- **Hinge stop:** a stop tab on the base knuckle line that the open lid's
  edge meets at `stop_deg` (e.g. 100°) — chosen so the travel-limit
  differential has a clean blocked region.
- **The closed pose is the shipped pose** (lid relaxed, latched). The swing
  and travel sweeps run on proof states, same as the carabiner's open gate.
- *Rejected — new `swing_clearance` verify primitive:* `screw_clearance`
  already expresses partial arcs (`turns = deg/360`); sugar adds API without
  power. The tooling contribution is the PATTERN (encoded in the skill law),
  not a new function.
- *Deferred — promoting the two-state pattern to domain-neutral:* the pattern
  now has two consumers (clasp, snapbox) but the CODE is bespoke geometry in
  each; promotion waits until actually-shared code exists (the `assembly.py`
  bar). Revisit at final review with implementation evidence.

## Nominal numbers (design values; tuned in the milestone-1 spike)

Box 40 × 30 × 15 (outer), wall 2.0, lid height 6, base height 12 (lip
overlap 3). Hinge: pin Ø 2.0, knuckle Ø 6, three base knuckles + two lid
knuckles interleaved along the 40 mm back edge; hinge axis parallel to X at
roughly (y = −15, z = 15) in the box frame — deliberately far from the world
origin. Swing 0→90° closed→open; stop at ~100°. Latch: tab 8 wide × 1.6
thick, catch depth 1.2, deflection 1.6 (≥ catch depth + clearance).
`clearance` 0.15 (clasp's slide-fit value); near-contact band for the
shipped pose via the existing `verify.clearance` (`SEATED_MAX_GAP`-style
fixture). All validated with value-carrying inequalities (deflection must
clear the catch; stop_deg > swing_deg; knuckle interleave must fit the edge).

## Components

### `claudecad/hardware/snapbox.py` (new, pure geometry — house conventions)
- `SnapBoxParams` (frozen, validated): outer dims, wall, lid/base split,
  hinge (pin_d, knuckle_d, knuckle counts/widths, axis position, swing_deg,
  stop_deg), latch (tab w/t, catch depth, deflection), `clearance`.
  Computed props: hinge axis point + direction (the gate's `center`/`axis`),
  travel fractions (`swing_deg/360`, arc past stop).
- `base(p) -> Solid` (box + knuckles + catch bar + stop tab, bored).
- `lid(p, state: Literal["relaxed","deflected"]) -> Solid` (box lid +
  knuckles + integral latch tab; state moves the tab), built IN THE CLOSED
  POSE (the swing gate rotates it open — constructed states live at the
  gate's station 0, mirroring `seated_nut`).
- `hinge_pin(p) -> Solid`.
- `base_misaligned(p, offset) -> Solid` — negative-control base (knuckle
  bores displaced off the hinge axis).
- Module gate fixtures (one source): `SWING_STATIONS`, `OVERTRAVEL_STATIONS`,
  `OPEN_BLOCK_MIN_DEG`, `SEATED_MAX_GAP`, escape distances.

### `claudecad/verify.py`
- No changes expected (`screw_clearance` covers arcs). If the spike shows
  otherwise, the minimal general fix lands with evidence.

### `designs/snapbox/` (new)
- `params.py`, `build.py` (build → GLB always → gate → STEP on pass; prints
  every proof; registers in `tests/test_designs_import.py` — hardcoded list).

### `.claude/skills/cad/SKILL.md` (extend)
- Add the hinged-travel law: *a hinged joint is gated by partial-arc sweeps
  about the hinge axis (`screw_clearance`, `lead=0`, `center` ON the axis —
  off-origin centers are supported and must be used, never re-origin the
  model); travel limits are proven by a same-parameter differential (free
  within travel, blocked past the stop); snap retention by the two-state
  differential at the closed pose.*

## Verification & testing

- Unit: params validation inequalities; parts clean; two lid states differ
  only in the tab region (volume delta bounded, knuckles identical).
- Functional: the five proofs above, each a test + a design-gate print.
- Negative control: `base_misaligned` fails the swing gate.
- Integration: full gate green; STEP round-trips named parts; designs-import
  registration.
- Visual: renders vs a real hinged snap box reference (e.g. a parts organizer
  lid); Mike judges in Plasticity.

## Out of scope

- Elasticity/FEA of the cantilever (deflection is a constructed state);
  print tolerances beyond the single `clearance`; the lid's open-pose
  export (proof state only); multi-latch variants; promoting the two-state
  pattern (deferred, see Approach).

## Milestones

1. **Geometry spike (before the plan's code):** base/lid/pin construction
   manifold; the off-origin swing sweep behaves (verify `screw_clearance`
   center semantics on the real hinge axis); stop-tab blocked region reads
   cleanly; misaligned-knuckle negative control fails. Tuned defaults out.
2. `SnapBoxParams` + parts, clean/state tests green.
3. The five proofs + negative control green.
4. `designs/snapbox` gate + shipped-pose guard green, STEP exported.
5. Render vs reference; skill law; user acceptance in Plasticity.
