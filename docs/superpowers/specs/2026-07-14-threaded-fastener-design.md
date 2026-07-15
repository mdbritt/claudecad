# Threaded fastener — claudeCAD hardware pack, generality Phase 1

**Date:** 2026-07-14
**Status:** Approved; **amended 2026-07-15 — see the Amendment below, which supersedes the boolean 3-leg gate.**
**Predecessors:** 2026-07-12-claudecad-design.md (the verification-first core),
2026-07-13-open-source-release-design.md (v4: the `hardware/` domain pack and
the carabiner, this piece's sibling and the current generality proof)

This is **Phase 1 of a three-piece hardware roadmap** (bolt+nut → ball bearing
→ snap-fit/hinge). Each phase is its own spec → plan → build cycle, all landing
in `claudecad/hardware/`. The pieces are ordered so Phase 1 builds the most
general new verification machinery and later phases reuse it (see
`screw_clearance` below).

## Amendment (2026-07-15): analytic mesh gate supersedes the boolean 3-leg differential

Implementation (16 design spikes + the Task-3 review) proved the original
boolean approach below is the **wrong tool for a thread**, and this amendment
replaces it. What changed and why:

- **Boolean interference fits *clearance* mechanisms, not *contact* ones.** The
  carabiner/clasp verify crisply because their parts never touch (real air gaps
  → interference exactly 0). A thread is defined by flanks bearing on each
  other, so its working surfaces are in near-contact, and OCCT booleans on two
  meshing swept helicoids produce irreducible facet noise (~0.37 mm³/turn). The
  "rest interference == 0" of proof 5 is unachievable on the real swept solid.
- **A swept multi-turn helix also drifts** (not pitch-periodic); stacking one
  swept turn at exact pitch fixes periodicity, and the core cylinder must
  **overlap** the ridge (not sit tangent) or the fused solid is non-manifold.
  So the swept 3D thread is real but carries tessellation-level fuzz at contact.
- **The analytic route — previously rejected — is actually the ground truth
  for a thread.** For two coaxial same-pitch threads, helical symmetry makes
  the 3D mesh *exactly* reducible to the 2D axial cross-section (the standard
  way threads are analyzed). Each surface is a single-valued sawtooth `r(z)`;
  the parts interfere iff `r_bolt(z) ≥ r_nut(z)` somewhere, so
  `min_z (r_nut(z) − r_bolt(z))` is the **exact** signed clearance — positive is
  a real air gap, ≤ 0 is a jam. No facets, exact, milliseconds. Verified:
  mesh gap = the design clearance exactly (e.g. +0.08 mm at allowance 0.08),
  axial-shift and wrong-pitch both cleanly negative, with correct backlash.

**Revised gate (this is what ships):**
1. **Parts valid + manifold** — the swept 3D bolt/nut (corrected manifold
   construction) are built for the STEP/GLB export and gated on
   `valid ∧ manifold ∧ single-solid`.
2. **Mesh free (real air gap):** `thread_mesh_gap` (2D `r(z)` min-gap at the
   meshed phase) `> 0` — a genuine positive clearance, the shippable air gap.
3. **Axial-only blocked:** shift the bolt profile axially past the backlash
   (no rotation) → min-gap `< 0` (the helix constrains motion).
4. **Wrong-pitch blocked:** the nut profile at an off pitch → the phase drifts
   over the engagement → min-gap `< 0` (the pitch is a real property).

The manifold construction (corrected): reduce crest and root radii by the
clearance but evaluate the flank half-widths at the **shifted** radii (keeps
the flanks 60° through the pitch line, no pitch-diameter misalignment — a plain
2D `offset` raises the root above the nut crest and a naive radial shift
misaligns the pitch), with a small core overlap for manifoldness. `screw_clearance`
is retained (Task 1, done) as a general primitive that Phase 2's bearing reuses
at `lead=0`; it is no longer the bolt's mesh gate. "Verify what you ship"
holds: the analytic gate verifies the exact profile the swept solid realizes,
and the swept solid itself is gated valid+manifold.

The sections below are the **original (superseded) boolean design**, kept for
the rationale and the ISO geometry, which the amendment reuses.

## Problem

The public repo claims to be a *general* verification-first CAD system, not a
jewelry project. The carabiner proved one new domain (a spring-gate escape
differential). A threaded fastener proves it again along a genuinely different
axis: **coupled rotational motion**. Every gate the repo has today asserts a
property of a *linear* translation (chain interlock is topological; clasp
insertion, carabiner escape, and extraction are all straight-line sweeps). A
bolt and nut can only be proven with a *screw* motion — rotation coupled to
translation by the thread pitch. Building that gate expands the verification
vocabulary, which is the whole point of the exercise.

Deliverable: a realistic **M8×1.25 hex bolt + hex nut**, modeled and verified
in the assembled state, exported to STEP for Plasticity.

## What "meshing" means in static B-rep

Parts do not turn in a STEP file. A working thread is proven the same way the
carabiner's gate is proven — by ground-truth interference measured over an
explicitly driven motion — but the motion is now a screw, not a slide. Three
legs form the differential (the "bolt property"):

1. **Run-down (free):** the nut driven along a screw motion at the true lead,
   over the full modeled engagement, has ≈ 0 interference with the bolt at
   every station. The threads mesh and the nut travels.
2. **Axial-only (blocked):** the nut pushed *straight* along the axis (no
   rotation) by a fraction of a pitch has interference > 0. Motion is
   constrained to the helix — this is a real thread, not a slip-fit sleeve.
   (Reuses the existing `path_clearance`, pure translation.)
3. **Wrong-lead (blocked):** the nut driven along a screw motion at an *off*
   lead (e.g. 1.1×) has interference > 0. The pitch is a real geometric
   property of the modeled solids, not an artifact of how we chose to drive
   the motion.

Leg 2 is load-bearing in an unobvious way: it defines the manufacturable
**clearance window**. A too-loose thread fails leg 2 (axial push does not jam);
a too-tight thread fails leg 1 (run-down is not free). The single stated
`allowance` is tuned until legs 1–3 hold *simultaneously*; if no allowance
satisfies all three, the design fails honestly rather than being forced. The
gate defines the fit rather than us asserting it.

Plus the standing hardware-pack proofs (same as the carabiner):

4. Every part is a valid, manifold, single solid.
5. At rest (nut threaded onto the bolt at the seated position) all parts are
   pairwise zero-intersection — a real air gap of `allowance` at the flanks,
   never a touching boolean between different parts.

## Approach (decided)

**One honest thread geometry, verified and shipped.** build123d 0.11.1 has
**no built-in thread class** (`IsoThread`/`Thread` are not present — verified
against the installed package), so there is no "pretty" thread to ship
alongside a cheap verification proxy. We model the thread once, as a helical
sweep of a real profile, and the gate measures that exact geometry. "Verify
what you ship" is therefore automatic, not a principle we trade against.
`Helix(pitch, height, radius)` + `sweep(profile, path=helix)` is confirmed to
produce a valid single manifold solid.

**Threads modeled independently from ISO parameters** — the external (bolt)
and internal (nut) threads are each generated from the standard geometry
(major/minor/pitch diameters, 60° flank angle, pitch 1.25) with the `allowance`
applied, and the gate *proves* they mesh.

- *Rejected:* forming the nut by subtracting an enlarged copy of the bolt from
  the nut blank. It guarantees a fit by construction, which makes leg 1
  (run-down) tautological — it would prove only that we built the negative
  correctly, not that two independently specified threads mate. The carabiner
  constructs body and gate independently and proves they clear; this follows
  that discipline.
- *Rejected:* an analytic/parametric proof (no booleans — show crest/root radii
  never overlap given pitch and engagement). Exact and fast, but bespoke math
  that exercises no actual solid and does not generalize to Phases 2–3, whose
  whole value is measuring real geometry.

**Reference prior art for the profile, adapt not copy.** The ISO 60° metric
thread profile (ISO 68-1: truncated triangle, H = (√3/2)·P, external
truncation 5/8·H at the root and H/8 at the crest) is standard; the removed
build123d `IsoThread` and CadQuery's thread helpers are reputable references
for how to sweep it cleanly on a helix and cap the ends. Consult them for
technique, judge the geometry, then implement our own lean version — a real
truncated-V thread without cosmetic root/crest radii (those add B-rep
complexity that makes n-station booleans heavier without changing the
kinematics the gate measures).

## The M8×1.25 numbers (concrete, real)

Major Ø 8.0, pitch P 1.25, H = (√3/2)P = 1.083, pitch Ø 7.188, external minor Ø
6.647; hex across-flats ≈ 13.0, head height ≈ 5.3, standard nut height ≈ 6.5
(≈ 5 threads of engagement). Exact ISO 68-1 tolerance *classes* (6g/6H) are out
of scope — a single `allowance` stands in, as `clearance` does for the clasp.

## Components

### `claudecad/verify.py` (extend)

- `screw_clearance(moving, fixed, axis, center, lead, turns, n) -> list[float]`
  — the coupled rotation+translation sibling of `path_clearance`. Station i
  rotates `moving` by θ = 2π·turns·i/(n-1) about `axis` through `center` and
  translates it by lead·turns·i/(n-1) along `axis`; returns raw interference
  volumes (mm³). Numbers reported, no pass/fail policy baked in — callers
  assert, exactly as `path_clearance` does. Station 0 is the untranslated,
  unrotated pose. Validates n ≥ 2, nonzero axis.
  - **Family unification (the roadmap payoff):** `lead = 0` degenerates to a
    pure rotation about an axis — precisely Phase 2's ball-bearing free-spin
    sampler. `path_clearance` is the pure-translation member; `screw_clearance`
    the rotational/coupled member. Phase 2 inherits this primitive unchanged.

### `claudecad/hardware/fastener.py` (new, pure geometry)

Mirrors `hardware/carabiner.py`: frozen validated params, module-level
constants for shared fixtures, analytic + swept solids returned per function.

- `FastenerParams` (frozen dataclass, mm, value-carrying ValueErrors): major Ø,
  pitch, flank angle (default 60°), allowance, hex across-flats and head/nut
  heights, shank length, modeled engagement turns. Computed `@property`s: pitch
  radius, external/internal minor & major radii, thread height H, helix height
  from turns. Validation: all > 0; allowance leaves a positive flank gap but
  less than the axial slack that would let leg 2 pass without jamming (the
  clearance-window inequality, stated with a carrying error).
- `external_thread(p) -> Solid` — the bolt's threaded shank: core cylinder at
  the external minor radius, unioned with the 60° truncated-V rib swept along
  the helix out to the external major radius. Ends capped.
- `internal_thread(p) -> Solid` — the complementary tap cutter: the same
  core+rib construction at the *internal* minor/major radii with `allowance`
  applied. Generated from the nut's own ISO radii (its `FastenerParams`
  computed props), **not** from the bolt solid — that independence is exactly
  what keeps the run-down proof from being tautological (see the rejected
  alternative above). Subtracting a shank-shaped cutter leaves internal ridges
  where the cutter had valleys, i.e. a true internal thread that mates with the
  bolt because ISO 68-1 makes the two profiles complementary.
- `bolt(p) -> Solid` — hex head (analytic hex prism) ∪ `external_thread`.
- `nut(p) -> Solid` — hex prism − `internal_thread` cutter (→ threaded bore).
- Module constants: `AXIS` (screw/thread axis, Z), `FLANK_DEG`, the seated
  assembly pose (nut axial position at rest), and the `turns`/station defaults
  the design and tests share (one source, like `ESCAPE_AXIS`).

### `designs/bolt/` (new)

- `params.py`: `P = FastenerParams(...)` for M8×1.25, plus `RUNDOWN_STATIONS`
  / `RUNDOWN_TURNS` and the wrong-lead factor (mirrors `ESCAPE_STATIONS`).
- `build.py`: build bolt + nut → export GLB always (render/preview artifact,
  even on failure) → run the standing proofs (4, 5) and the three-leg
  differential (1, 2, 3), printing evidence per leg → export STEP only on a
  full pass (exit 1 otherwise). Same skeleton as `designs/carabiner/build.py`.
- `probe.py` (optional): dumps per-station interference for the three legs as
  JSON lines, for tuning the allowance during the spike.

### `tests/test_fastener.py` + `tests/test_verify.py` (extend)

- `screw_clearance` unit tests on a **known** geometry (a single helical rib
  vs a matching grooved cylinder): meshes at the true lead (all ≈ 0), jams at
  pure-axial and at a wrong lead (some > 0); lead = 0 is a pure rotation
  (sanity: a shape with rotational symmetry stays clear, an asymmetric one
  collides). Guards: n < 2 and zero axis raise.
- Fastener unit tests: bolt/nut valid/manifold/single; params validation
  inequalities; seated-assembly pairwise zero-intersection.
- The three-leg differential as an integration test at the design params.

### `.claude/skills/cad/SKILL.md` (extend)

Add the screw-motion gate to the mechanism-proof law, beside the carabiner's
escape differential: *a threaded/rotational joint is proven by a screw sweep —
free at the true lead, blocked under pure translation and under a wrong lead —
run on the shipped geometry in the local frame.*

## Verification & testing

- **Unit:** `screw_clearance` on known geometry (above); parts clean; params
  inequalities; seated pairwise clearance.
- **Functional (the heart):** the three-leg differential green at design params
  — run-down free, axial-only blocked, wrong-lead blocked.
- **Integration:** full `designs/bolt` gate green; STEP round-trips two named
  parts (`bolt`, `nut`).
- **Visual:** proportions judged against a real M8 hex bolt reference photo
  (fetched during implementation); render + STEP viewer; Mike is final judge in
  Plasticity.

## Out of scope

- Torque, preload, spring/friction, or any FEA reasoning — geometry only.
- Exact ISO 68-1 tolerance classes and thread run-out/incomplete lead threads
  (cosmetic); a single `allowance` stands in.
- Multi-start and left-hand threads; washers; clamped-plate context (a possible
  later extension).
- Cosmetic root/crest fillet radii on the profile (kinematically inert).

## Milestones

1. `screw_clearance` in `verify.py` + unit tests on known geometry green
   (the reusable primitive, proven before any thread exists).
2. **Thread-modeling spike (the #1 risk):** independently modeled external +
   internal M8 threads mesh with a tuned `allowance` — clean interference-0 at
   rest and a clean axial jam. Settles the profile/boolean approach and the
   allowance value before the full parts are built. Performance lever if a
   full-height M8 nut (~5 threads) makes n-station gating heavy: model a
   thinner, *fully threaded* jam-nut blank (a real 2–3 thread nut) — the whole
   bore is still threaded, physically valid, never a proxy.
3. `bolt()` + `nut()` full parts; standing proofs + three-leg differential
   green; `designs/bolt` gate exports STEP.
4. Render vs reference + STEP to Plasticity (user acceptance).
