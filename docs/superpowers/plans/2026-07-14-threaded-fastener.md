# Threaded Fastener (Hardware Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a verified M8×1.25 hex bolt + hex nut in the hardware pack, proven to mesh by a new screw-motion verification gate.

**Architecture:** Add `screw_clearance` (coupled rotation+translation) to `verify.py` as the rotational sibling of `path_clearance`. Model the bolt's external thread and the nut's internal thread independently as helical sweeps from ISO 68-1 geometry, then prove they mate with a three-leg differential — run-down free / axial-only blocked / wrong-lead blocked — measured on the shipped geometry.

**Tech Stack:** build123d 0.11.1 (`Helix` + `sweep` + 2D `offset`), Python 3.14, uv, pytest; STEP+GLB via `tools/export.py`.

## Global Constraints

- build123d **0.11.1**, Python **3.14** (pinned via `.python-version`); run everything with `uv run`.
- build123d 0.11.1 has **no built-in thread class** — threads are helical sweeps we construct.
- **Verify the shipped geometry** — the STEP/GLB parts and the gated parts are the same solids; no verification proxy.
- **Never weaken a gate to pass.** The single `allowance` is tuned so the seated air gap and both differential legs hold simultaneously; if no value does, the design fails honestly.
- Parts are separate manifold solids with **real air gaps at every mating pair** — never a touching boolean between different parts (hardware-pack law).
- Follow `hardware/carabiner.py` conventions: frozen validated params (value-carrying `ValueError`s), shared module constants, analytic + swept solids returned per function.
- mm units throughout; the single `allowance` stands in for ISO 68-1 tolerance classes.

---

## AMENDMENT 2026-07-15 — analytic mesh gate (supersedes Tasks 3, 5, 6 below)

Implementation proved the boolean 3-leg gate is the wrong tool for a thread (facet noise at meshing contact; see the spec amendment). **Tasks 1, 2, 4 stand as written and are done/valid.** Tasks 3, 5, 6 are REPLACED by the versions here; the boolean versions below (screw_clearance-based gate, `seated_nut`, `path_clearance` legs, the pitch-periodic boolean test) are **superseded — do not implement them.** `screw_clearance` (Task 1) stays committed as a general primitive Phase 2 reuses; it is no longer the bolt's mesh gate.

### Task 3′ — manifold swept threads (for export), gated valid+manifold

The swept 3D thread is built only so the STEP/GLB export has a real solid; the MESH is verified analytically (Task 5′). Construction (verified manifold): reduce crest & root radii by `allowance` but take the flank half-widths at the **shifted** radii (keeps flanks 60° through the pitch line — no pitch-diameter misalignment), and give the core a small overlap so the union fuses manifold instead of tangent.

Add to `claudecad/hardware/fastener.py` (build123d import line: `Cylinder, Helix, Location, Plane, Polygon, Pos, Solid, sweep`):

```python
_SEGMENTS_PER_TURN = 1
_CORE_OVERLAP = 0.02  # core sits this far above the ridge root -> manifold fuse
                      # (a tangent core makes non-manifold seams; verified)


def _half_width(p: FastenerParams, r: float) -> float:
    """Axial half-width of the 60-deg thread at radius r."""
    return p.pitch / 4 - (r - p.pitch_radius) * math.tan(math.radians(FLANK_DEG / 2))


def _profile(p: FastenerParams, allowance: float) -> list[tuple[float, float]]:
    """Undersize trapezoid: crest & root radii reduced by `allowance`, flank
    half-widths taken at the SHIFTED radii and inset by `allowance`. Evaluating
    the half-widths at the shifted (not basic) radii is what keeps the flanks
    60 deg through the pitch line, so the bolt stays pitch-aligned with the
    basic nut (a plain 2D offset raises the root above the nut crest; a naive
    radial shift misaligns the pitch diameter)."""
    crest_r = p.major_d / 2 - allowance
    root_r = p.minor_radius - allowance
    return [
        (root_r - p.pitch_radius, -(_half_width(p, root_r) - allowance)),
        (crest_r - p.pitch_radius, -(_half_width(p, crest_r) - allowance)),
        (crest_r - p.pitch_radius, _half_width(p, crest_r) - allowance),
        (root_r - p.pitch_radius, _half_width(p, root_r) - allowance),
    ]


def _one_turn(p: FastenerParams, allowance: float) -> Solid:
    """One turn of thread ridge, K sub-segments placed by exact fractional
    screws (K=1 is a single 1-turn sweep)."""
    k = _SEGMENTS_PER_TURN
    h = Helix(pitch=p.pitch, height=p.pitch / k, radius=p.pitch_radius)
    plane = Plane(origin=h @ 0, x_dir=(1, 0, 0), z_dir=h % 0)
    seg = sweep(plane * Polygon(*_profile(p, allowance), align=None), path=h)
    ridge = seg
    for i in range(1, k):
        ridge = ridge + Pos(0, 0, i * p.pitch / k) * \
            Location((0, 0, 0), AXIS, i * 360.0 / k) * seg
    return ridge


def _thread(p: FastenerParams, turns: int, allowance: float) -> Solid:
    """Pitch-periodic thread: one turn stacked at exact integer-pitch spacing
    (a continuous multi-turn sweep drifts), unioned with a core cylinder that
    overlaps the ridge root by _CORE_OVERLAP for a manifold fuse."""
    one = _one_turn(p, allowance)
    ridge = one
    for t in range(1, turns):
        ridge = ridge + Pos(0, 0, t * p.pitch) * one
    core_r = (p.minor_radius - allowance) + _CORE_OVERLAP
    core = Pos(0, 0, turns * p.pitch / 2) * Cylinder(core_r, turns * p.pitch)
    return core + ridge


def external_thread(p: FastenerParams) -> Solid:
    """Bolt threaded shank (undersize by `allowance`)."""
    return _thread(p, p.bolt_turns, p.allowance)


def internal_thread(p: FastenerParams) -> Solid:
    """Nut tap cutter (basic thread), subtracted from the nut blank."""
    return _thread(p, p.nut_turns, 0.0)
```

Test (`tests/test_fastener.py`) — TDD RED (ImportError) then GREEN. Threads must be VALID + MANIFOLD (this is the bug the boolean version missed — `is_valid` alone passed a non-manifold solid):

```python
def test_threads_are_clean_manifold_solids():
    from claudecad.verify import check_solid
    from claudecad.hardware.fastener import external_thread, internal_thread
    p = FastenerParams()
    for name, s in (("external", external_thread(p)), ("internal", internal_thread(p))):
        r = check_solid(s)
        assert r.ok, f"{name} not clean: valid={r.is_valid} manifold={r.is_manifold} pieces={r.piece_count}"
```

### Task 5′ — analytic mesh gate (`thread_mesh_gap`)

By helical symmetry each thread surface is a single-valued sawtooth `r(z)` in the axial section; the parts interfere iff `r_bolt(z) >= r_nut(z)` somewhere, so `min_z(r_nut - r_bolt)` is the EXACT signed clearance. Verified: mesh gap = `allowance` (a real air gap), axial-shift and wrong-pitch both cleanly negative, correct backlash. Add to `fastener.py` (`import numpy as np` at top):

```python
# analytic mesh-gate fixtures (shared by the design build and the test)
AXIAL_SHIFT = 0.15        # mm of pure-axial shift (past the ~0.05 backlash) -> jam
WRONG_PITCH_FACTOR = 1.05  # nut pitch error over the engagement -> jam
_GAP_SAMPLES = 20000


def _surf(z, phase: float, crest_r: float, root_r: float, crest_hw: float,
          pitch: float):
    """Single-valued thread surface r(z) in the axial section: crest flat ->
    60-deg flank -> root flat, period `pitch`, crest centered at `phase`."""
    u = np.abs((z - phase + pitch / 2) % pitch - pitch / 2)
    fz = abs(crest_r - root_r) * math.tan(math.radians(FLANK_DEG / 2))
    return np.where(u <= crest_hw, crest_r,
           np.where(u <= crest_hw + fz,
                    crest_r + (root_r - crest_r) * (u - crest_hw) / fz, root_r))


def thread_mesh_gap(p: FastenerParams, bolt_dz: float = 0.0,
                    nut_pitch_factor: float = 1.0) -> float:
    """Exact min axial-section clearance (mm) between the meshed bolt and nut
    threads over the nut's engagement. >0 is a real air gap (free); <=0 is
    interference (jam). The nut inner surface is a basic external-thread
    sawtooth; the bolt is the undersize sawtooth at the same phase (+bolt_dz).
    Coaxial same-pitch helical symmetry makes this 2D section exact."""
    z = np.linspace(0.0, p.nut_turns * p.pitch, _GAP_SAMPLES)
    hw = lambda r: _half_width(p, r)
    a = p.allowance
    rn = _surf(z, 0.0, p.major_d / 2, p.minor_radius, hw(p.major_d / 2),
               p.pitch * nut_pitch_factor)
    rb = _surf(z, bolt_dz, p.major_d / 2 - a, p.minor_radius - a,
               hw(p.major_d / 2 - a) - a, p.pitch)
    return float(np.min(rn - rb))
```

Test — the crisp differential (TDD RED then GREEN):

```python
def test_thread_mesh_differential():
    from claudecad.hardware.fastener import (
        AXIAL_SHIFT, WRONG_PITCH_FACTOR, thread_mesh_gap)
    p = FastenerParams()
    assert thread_mesh_gap(p) > 0                              # mesh: real air gap
    assert math.isclose(thread_mesh_gap(p), p.allowance, abs_tol=1e-6)  # gap == clearance
    assert thread_mesh_gap(p, bolt_dz=AXIAL_SHIFT) < 0         # axial-only: jam
    assert thread_mesh_gap(p, nut_pitch_factor=WRONG_PITCH_FACTOR) < 0  # wrong pitch: jam
```

Also add a `_surf`/gap unit test on a known trivial case if useful, but the differential above is the heart.

### Task 6′ — design `designs/bolt` with the analytic gate

`designs/bolt/params.py`: `P = FastenerParams()` (unchanged). `designs/bolt/__init__.py`: empty. `designs/bolt/build.py` mirrors `carabiner/build.py` but the gate is: parts clean+manifold, mesh air gap >0, axial jam <0, wrong-pitch jam <0.

```python
"""Build, verify, and export the M8 hex bolt + nut.

Usage: uv run python -m designs.bolt.build
GLB always; STEP only if the gate passes (exit 1 otherwise). The gate: parts
are clean manifold solids, and the analytic thread mesh has a real air gap on
the true pitch (free) but jams under a pure-axial shift and a wrong pitch.
Mesh proof is the exact 2D axial section (helical symmetry), not booleans.
"""
import sys

from claudecad.hardware.fastener import (
    AXIAL_SHIFT, WRONG_PITCH_FACTOR, bolt, nut, thread_mesh_gap,
)
from claudecad.verify import check_solid
from tools.export import export_design, export_glb

from .params import P


def main() -> int:
    b, n = bolt(P), nut(P)
    parts = {"bolt": b, "nut": n}
    export_glb(parts, "out/glb/bolt.glb", linear_deflection=0.01,
               angular_deflection=0.1)

    ok = True
    for name, s in parts.items():
        r = check_solid(s)
        print(f"{name}: valid={r.is_valid} manifold={r.is_manifold} "
              f"pieces={r.piece_count} volume={r.volume:.1f}")
        ok = ok and r.ok

    mesh = thread_mesh_gap(P)
    axial = thread_mesh_gap(P, bolt_dz=AXIAL_SHIFT)
    wrong = thread_mesh_gap(P, nut_pitch_factor=WRONG_PITCH_FACTOR)
    print(f"mesh air gap {mesh:+.4f} (free, >0) | axial-shift {axial:+.4f} "
          f"(jam, <0) | wrong-pitch {wrong:+.4f} (jam, <0)")
    ok = ok and mesh > 0 and axial < 0 and wrong < 0

    if not ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1
    export_design(parts, "out/step/bolt.step", assembly_label="bolt")
    print("exported out/step/bolt.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`bolt(p)`/`nut(p)` are Task 4 (unchanged — they call `external_thread`/`internal_thread`). Add the screw-motion **and** analytic-mesh law to `.claude/skills/cad/SKILL.md`: *a threaded joint is proven by the exact 2D axial-section clearance (helical symmetry) — a real air gap on the true pitch, jamming under pure-axial shift and wrong pitch; the swept 3D solid is gated valid+manifold for export.* Then render (`tools/render.py out/glb/bolt.glb --outdir out/renders/bolt`) and judge vs an M8 reference.

---

### Task 1: `screw_clearance` verification primitive

**Files:**
- Modify: `claudecad/verify.py` (add function after `path_clearance`)
- Test: `tests/test_verify.py` (append)

**Interfaces:**
- Consumes: `intersection_volume` (existing, same module).
- Produces: `screw_clearance(moving, fixed, axis, center, lead, turns, n) -> list[float]` — interference volume (mm³) at `n` stations of a screw motion: station `i` rotates `moving` by `θ = 360·turns·i/(n-1)` degrees about `axis` through `center`, then translates it by `lead·turns·i/(n-1)` along `axis`. Station 0 is the untransformed pose. `lead=0` degenerates to a pure rotation (Phase 2 reuses this). Raises `ValueError` for `n < 2` or a zero `axis`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_verify.py`:

```python
def test_screw_clearance_station0_is_rest_pose():
    from build123d import Box, Pos
    from claudecad.verify import screw_clearance, intersection_volume
    a = Box(2, 2, 2)
    b = Pos(1, 0, 0) * Box(2, 2, 2)
    vals = screw_clearance(a, b, axis=(0, 0, 1), center=(0, 0, 0),
                           lead=1.0, turns=1.0, n=5)
    assert abs(vals[0] - intersection_volume(a, b)) < 1e-9


def test_screw_clearance_axisymmetric_shape_is_invariant_under_pure_rotation():
    # a cylinder on the Z axis is unchanged by Z-rotation; lead=0 => all equal
    from build123d import Cylinder, Pos
    from claudecad.verify import screw_clearance
    moving = Cylinder(1.0, 4.0)
    fixed = Pos(0.5, 0, 0) * Cylinder(1.0, 4.0)
    vals = screw_clearance(moving, fixed, axis=(0, 0, 1), center=(0, 0, 0),
                           lead=0.0, turns=1.0, n=6)
    assert max(vals) - min(vals) < 1e-6


def test_screw_clearance_offaxis_shape_varies_under_pure_rotation():
    from build123d import Box, Pos
    from claudecad.verify import screw_clearance
    moving = Pos(1.2, 0, 0) * Box(1, 1, 4)
    fixed = Pos(1.2, 0, 0) * Box(1, 1, 4)
    vals = screw_clearance(moving, fixed, axis=(0, 0, 1), center=(0, 0, 0),
                           lead=0.0, turns=1.0, n=9)
    assert vals[0] > 0.0 and max(vals) - min(vals) > 1e-3


def test_screw_clearance_guards():
    import pytest
    from build123d import Box
    from claudecad.verify import screw_clearance
    with pytest.raises(ValueError):
        screw_clearance(Box(1, 1, 1), Box(1, 1, 1), (0, 0, 1), (0, 0, 0),
                        1.0, 1.0, 1)
    with pytest.raises(ValueError):
        screw_clearance(Box(1, 1, 1), Box(1, 1, 1), (0, 0, 0), (0, 0, 0),
                        1.0, 1.0, 5)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_verify.py -k screw_clearance -v`
Expected: FAIL / ERROR with `ImportError: cannot import name 'screw_clearance'`.

- [ ] **Step 3: Implement `screw_clearance`**

Add to `claudecad/verify.py` (it already imports `Pos`, `Vector` from build123d; add `Location`):

```python
def screw_clearance(moving, fixed, axis, center, lead: float, turns: float,
                    n: int) -> list[float]:
    """Intersection volume of `moving` under a screw motion at n stations.

    Station i rotates `moving` by 360*turns*i/(n-1) degrees about `axis`
    through `center`, then translates it by lead*turns*i/(n-1) along `axis`.
    Station 0 is the untransformed pose. `lead=0` is a pure rotation about
    the axis. Returns raw volumes (mm^3) — callers decide pass/fail, exactly
    like `path_clearance`.
    """
    if n < 2:
        raise ValueError(f"need n >= 2 stations, got {n}")
    a = Vector(*axis) if not isinstance(axis, Vector) else axis
    if a.length == 0:
        raise ValueError(f"axis must be nonzero, got {tuple(a)}")
    a = a.normalized()
    c = tuple(Vector(*center))
    ad = tuple(a)
    out = []
    for i in range(n):
        frac = i / (n - 1)
        angle = 360.0 * turns * frac
        axial = lead * turns * frac
        placed = Pos(a.X * axial, a.Y * axial, a.Z * axial) * \
            Location(c, ad, angle) * moving
        out.append(intersection_volume(placed, fixed))
    return out
```

Update the build123d import line at the top of `verify.py`:

```python
from build123d import Location, Pos, Vector
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_verify.py -k screw_clearance -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add claudecad/verify.py tests/test_verify.py
git commit -m "feat: screw_clearance — coupled rotation+translation verify gate

The rotational sibling of path_clearance; lead=0 degenerates to a pure
rotation (reused by the ball-bearing phase). Numbers reported, no policy."
```

---

### Task 2: `FastenerParams` (driving dims + ISO 68-1 radii)

**Files:**
- Create: `claudecad/hardware/fastener.py`
- Test: `tests/test_fastener.py`

**Interfaces:**
- Produces: `FastenerParams` frozen dataclass with fields `major_d=8.0`, `pitch=1.25`, `allowance=0.08`, `bolt_turns=6`, `nut_turns=3`, `hex_across_flats=13.0`, `head_height=5.3`; computed properties `H`, `pitch_radius`, `minor_radius` (all mm). Module constants `AXIS=(0.0,0.0,1.0)`, `FLANK_DEG=60.0`. Verified M8×1.25 values: `H≈1.0825`, `pitch_radius≈3.5941`, `minor_radius≈3.3234`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_fastener.py`:

```python
import math

import pytest

from claudecad.hardware.fastener import FastenerParams


def test_iso_radii_m8():
    p = FastenerParams()  # M8×1.25
    assert math.isclose(p.H, 1.25 * math.sqrt(3) / 2, rel_tol=1e-9)
    assert math.isclose(p.pitch_radius, 4.0 - 3 * p.H / 8, rel_tol=1e-9)
    assert math.isclose(p.minor_radius, 4.0 - 5 * p.H / 8, rel_tol=1e-9)


def test_params_validation():
    with pytest.raises(ValueError):
        FastenerParams(pitch=0.0)
    with pytest.raises(ValueError):
        # allowance must stay under the crest FLAT width or the flank-normal
        # offset erodes the crest away entirely (for M8 the crest flat ≈ 0.156)
        FastenerParams(allowance=0.2)
    with pytest.raises(ValueError):
        # the nut must be shorter than the shank so it runs down a longer bolt
        FastenerParams(bolt_turns=3, nut_turns=3)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_fastener.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'claudecad.hardware.fastener'`.

- [ ] **Step 3: Implement `FastenerParams`**

Create `claudecad/hardware/fastener.py`:

```python
"""Threaded fastener: M8×1.25 hex bolt + hex nut, modeled as helical sweeps.

Local frame: thread axis is +Z (`AXIS`). The thread is built by stacking
exact-pitch-spaced copies of a single swept turn so the solid is truly
pitch-periodic (a continuous multi-turn sweep drifts turn-to-turn and reads
as interference under an ideal screw motion — see the design spec). The nut is
the BASIC-profile negative; the bolt is the same profile offset undersize along
the flank normal — so the run-down gate proves an undersize bolt clears a basic
nut rather than that a solid fits its own negative.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

AXIS: tuple[float, float, float] = (0.0, 0.0, 1.0)
FLANK_DEG: float = 60.0  # ISO metric included flank angle


@dataclass(frozen=True)
class FastenerParams:
    """Driving dimensions, mm. major_d/pitch are the nominal ISO thread size
    (M8×1.25). allowance is the single radial+flank clearance that stands in
    for ISO tolerance classes. bolt_turns/nut_turns are thread lengths in
    turns; the nut is shorter so it runs down a longer shank."""

    major_d: float = 8.0
    pitch: float = 1.25
    allowance: float = 0.08  # flank-normal clearance; 0.08 gives rest iv==0 for M8 (verified)
    bolt_turns: int = 6
    nut_turns: int = 3
    hex_across_flats: float = 13.0
    head_height: float = 5.3

    def __post_init__(self):
        bad = {k: v for k, v in self.__dict__.items() if v <= 0}
        if bad:
            raise ValueError(f"all fastener params must be > 0, got {bad}")
        crest_flat = 2 * (self.pitch / 4 - (self.major_d / 2 - self.pitch_radius)
                          * math.tan(math.radians(FLANK_DEG / 2)))
        if self.allowance >= crest_flat:
            raise ValueError(
                f"allowance={self.allowance} must be < the crest flat width "
                f"({crest_flat:.4f}); a larger flank-normal offset erodes the "
                "crest flat away entirely"
            )
        if self.bolt_turns <= self.nut_turns:
            raise ValueError(
                f"need bolt_turns > nut_turns (the nut runs down a longer "
                f"shank), got bolt_turns={self.bolt_turns} "
                f"nut_turns={self.nut_turns}"
            )

    @property
    def H(self) -> float:
        """ISO 68-1 fundamental triangle height."""
        return self.pitch * math.sqrt(3) / 2

    @property
    def pitch_radius(self) -> float:
        return self.major_d / 2 - 3 * self.H / 8

    @property
    def minor_radius(self) -> float:
        """External thread root == internal thread minor radius."""
        return self.major_d / 2 - 5 * self.H / 8
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_fastener.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add claudecad/hardware/fastener.py tests/test_fastener.py
git commit -m "feat: FastenerParams — M8 ISO 68-1 driving dims and radii"
```

---

### Task 3: pitch-periodic thread construction

**Files:**
- Modify: `claudecad/hardware/fastener.py` (add helpers + two public functions)
- Test: `tests/test_fastener.py` (append)

**Interfaces:**
- Consumes: `FastenerParams`, `AXIS`, `FLANK_DEG` (Task 2).
- Produces: `external_thread(p) -> Solid` (bolt shank: core ∪ external thread, clearance-inset) and `internal_thread(p) -> Solid` (the nut's basic tap cutter). Both are valid single manifold solids and are **exactly pitch-periodic**.

**Why this construction (all verified during design):**
- A single continuous multi-turn `sweep` along a `Helix` **drifts turn-to-turn** — a pure one-pitch translation leaves ~1 mm³ interference, growing per pitch — so an ideal screw motion reads as scraping (run-down never goes free). **Fix:** build **one** turn and stack copies at exact integer-pitch spacing; integer-pitch shifts then re-mesh at **0.0000** (verified). This is the essential construction.
- At the default `_SEGMENTS_PER_TURN = 1` (stack whole 1-turn sweeps) there is a small *fractional* run-down residual — the single continuous sweep deviates slightly from an ideal helicoid, so mid-turn the flanks graze (exactly 0 at every whole turn). It scales with engagement length: ~0.3 mm³ over a 2-turn engagement, ~3.6 mm³ over the design's 3-turn engagement. This is a light B-rep and a fast gate, and the residual is dominated by the jams — so it reads "free" via the differential gate (Task 5), not an absolute cutoff. Subdividing the turn into K sub-segments placed by fractional screws shrinks the residual (~0.04 mm³ at K=8, short engagement) **but** the heavier B-rep makes the gate booleans impractically slow (K≥4 measured at minutes). K=1 is the shipped default; K is tunable for anyone who wants crisper at a speed cost.
- `is_frenet=True` is **banned** — pathologically slow on multi-turn helices, malformed geometry on a single turn.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_fastener.py`:

```python
def test_threads_are_clean_solids():
    from claudecad.verify import check_solid
    from claudecad.hardware.fastener import external_thread, internal_thread
    p = FastenerParams()
    assert check_solid(external_thread(p)).ok
    assert check_solid(internal_thread(p)).ok


def test_external_thread_is_pitch_periodic():
    # The property the stacked construction exists to guarantee: shifting the
    # thread by exactly one pitch re-meshes with the nut's cutter-carved
    # channel at ~0. Guards against a refactor reintroducing sweep drift.
    from build123d import Pos, RegularPolygon, extrude
    from claudecad.verify import intersection_volume
    from claudecad.hardware.fastener import external_thread, internal_thread
    p = FastenerParams(bolt_turns=4, nut_turns=3)
    nut_channel = extrude(
        RegularPolygon(p.hex_across_flats / 2, 6, major_radius=False),
        p.nut_turns * p.pitch,
    ) - internal_thread(p)
    bolt = external_thread(p)
    # flank-normal offset -> rest interference ~0 (real air gap); stacking ->
    # a whole-pitch shift re-meshes (integer periodicity), both verified.
    assert intersection_volume(bolt, nut_channel) < 0.1              # rest meshes
    assert intersection_volume(Pos(0, 0, p.pitch) * bolt, nut_channel) < 0.1  # +1 pitch re-meshes
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_fastener.py -k thread -v`
Expected: FAIL with `ImportError: cannot import name 'external_thread'`.

- [ ] **Step 3: Implement the thread helpers**

Add to `claudecad/hardware/fastener.py` (extend the build123d import):

```python
from build123d import (Cylinder, Helix, Location, Plane, Polygon, Pos, Solid,
                       make_face, offset, sweep)

# Sub-turn stacking granularity. K=1 (stack whole 1-turn sweeps) is light and
# fast; the fractional run-down residual (~3.6 mm^3 at the design's 3-turn
# engagement) is dominated by the jams, so the differential gate reads it as
# free. Raising K subdivides the turn (crisper run-down) but makes the gate
# booleans much slower (K>=4 measured at minutes). Keep at 1 unless a crisper
# gate is worth the speed.
_SEGMENTS_PER_TURN = 1


def _half_width(p: FastenerParams, r: float) -> float:
    """Axial half-width of the 60-deg thread at radius r (pitch/2 total at the
    pitch radius, tapering to the crest and root)."""
    return p.pitch / 4 - (r - p.pitch_radius) * math.tan(math.radians(FLANK_DEG / 2))


def _basic_profile(p: FastenerParams) -> list[tuple[float, float]]:
    """Basic (zero-allowance) trapezoidal 60-deg thread cross-section in the
    (radial-from-pitch, axial) plane."""
    return [
        (p.minor_radius - p.pitch_radius, -_half_width(p, p.minor_radius)),
        (p.major_d / 2 - p.pitch_radius, -_half_width(p, p.major_d / 2)),
        (p.major_d / 2 - p.pitch_radius, _half_width(p, p.major_d / 2)),
        (p.minor_radius - p.pitch_radius, _half_width(p, p.minor_radius)),
    ]


def _profile_face(p: FastenerParams, allowance: float):
    """The thread cross-section face, inset by `allowance` PERPENDICULAR to the
    flanks (2D offset) — the ISO 6g-style undersize. A flank-normal offset (not
    a radial or axial inset) keeps the pitch line aligned, so an undersize bolt
    and a basic nut mesh with a uniform gap and rest interference == 0
    (verified: a radial shift misaligns the pitch diameters and interferes)."""
    face = make_face(Polygon(*_basic_profile(p), align=None))
    return offset(face, amount=-allowance) if allowance > 0 else face


def _core_radius(p: FastenerParams, allowance: float) -> float:
    """Innermost radius reached by the (offset) profile — the shank core
    cylinder connects to the thread ridge here."""
    return p.pitch_radius + _profile_face(p, allowance).bounding_box().min.X


def _one_turn(p: FastenerParams, allowance: float) -> Solid:
    """One turn of thread ridge (z in [0, pitch]). Built from K sub-segments
    placed by exact fractional screws so it is periodic at pitch/K within the
    turn (K=1 is a single continuous 1-turn sweep)."""
    k = _SEGMENTS_PER_TURN
    seg_helix = Helix(pitch=p.pitch, height=p.pitch / k, radius=p.pitch_radius)
    plane = Plane(origin=seg_helix @ 0, x_dir=(1, 0, 0), z_dir=seg_helix % 0)
    seg = sweep(plane * _profile_face(p, allowance), path=seg_helix)
    ridge = seg
    for i in range(1, k):
        ridge = ridge + Pos(0, 0, i * p.pitch / k) * \
            Location((0, 0, 0), AXIS, i * 360.0 / k) * seg
    return ridge


def _thread(p: FastenerParams, turns: int, allowance: float) -> Solid:
    """A pitch-periodic thread: build one turn, then stack `turns` copies at
    exact integer-pitch spacing (drift-free) and union a core cylinder at the
    minor radius. Integer-pitch periodicity is what lets the screw gate read
    run-down as free (a continuous multi-turn sweep would drift)."""
    one = _one_turn(p, allowance)
    ridge = one
    for t in range(1, turns):
        ridge = ridge + Pos(0, 0, t * p.pitch) * one
    core = Pos(0, 0, turns * p.pitch / 2) * Cylinder(
        _core_radius(p, allowance), turns * p.pitch)
    return core + ridge


def external_thread(p: FastenerParams) -> Solid:
    """The bolt's threaded shank (core ∪ external thread), inset by the
    allowance so it runs freely in the basic nut (the ISO 6g undersize idea,
    collapsed to a single allowance)."""
    return _thread(p, p.bolt_turns, p.allowance)


def internal_thread(p: FastenerParams) -> Solid:
    """The nut's tap cutter: a BASIC (zero-allowance) thread at p's own ISO
    radii, subtracted from the nut blank to leave a mating threaded bore. It
    is the nut's negative former, built independently of the bolt solid — so
    the run-down gate proves an undersize bolt clears a basic nut, not that a
    solid fits its own negative."""
    return _thread(p, p.nut_turns, 0.0)
```

Also add `import math` if not already present (Task 2 added it).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_fastener.py -k thread -v`
Expected: 2 passed. (Thread construction takes a few seconds — the stacking unions.)

- [ ] **Step 5: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add claudecad/hardware/fastener.py tests/test_fastener.py
git commit -m "feat: pitch-periodic thread via 1-turn screw stacking"
```

---

### Task 4: `bolt()` and `nut()` full parts

**Files:**
- Modify: `claudecad/hardware/fastener.py` (add hex helper + two public parts)
- Test: `tests/test_fastener.py` (append)

**Interfaces:**
- Consumes: `FastenerParams`, `external_thread`, `internal_thread` (Tasks 2–3).
- Produces: `bolt(p) -> Solid` (hex head below z=0 ∪ threaded shank) and `nut(p) -> Solid` (hex prism − threaded bore). Both verified valid single manifold solids (bolt vol ≈ 1102 mm³, nut ≈ 396 mm³ at defaults).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_fastener.py`:

```python
def test_parts_clean():
    from claudecad.verify import check_solid
    from claudecad.hardware.fastener import bolt, nut
    p = FastenerParams()
    for name, s in (("bolt", bolt(p)), ("nut", nut(p))):
        r = check_solid(s)
        assert r.ok, f"{name} not a clean solid: {r}"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_fastener.py -k parts_clean -v`
Expected: FAIL with `ImportError: cannot import name 'bolt'`.

- [ ] **Step 3: Implement `bolt` and `nut`**

Extend the build123d import in `fastener.py` with `RegularPolygon, extrude`, then add:

```python
def _hex_prism(p: FastenerParams, height: float) -> Solid:
    """Hex prism across `hex_across_flats`, base at z=0, extruded +Z."""
    return extrude(
        RegularPolygon(p.hex_across_flats / 2, 6, major_radius=False), height
    )


def bolt(p: FastenerParams) -> Solid:
    """Hex head (below z=0) ∪ threaded shank (z=0..bolt_turns*pitch). The head
    overlaps the shank base by 0.3 mm so the union fuses to a single solid
    rather than joining on a coincident face (verified: solids==1)."""
    shank = external_thread(p)
    head = Pos(0, 0, -p.head_height) * _hex_prism(p, p.head_height + 0.3)
    return shank + head


def nut(p: FastenerParams) -> Solid:
    """Hex prism (nut_turns*pitch tall) with a threaded bore."""
    return _hex_prism(p, p.nut_turns * p.pitch) - internal_thread(p)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_fastener.py -k parts_clean -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add claudecad/hardware/fastener.py tests/test_fastener.py
git commit -m "feat: bolt() and nut() — hex head shank and threaded hex nut"
```

---

### Task 5: the screw-motion differential (the fastener property)

**Files:**
- Modify: `claudecad/hardware/fastener.py` (gate constants + a seated-nut helper)
- Test: `tests/test_fastener.py` (append the differential test)

**Interfaces:**
- Consumes: `bolt`, `nut` (Task 4), `AXIS` (Task 2), `screw_clearance` + `path_clearance` + `intersection_volume` (verify).
- Produces: gate constants and `seated_nut(p) -> Solid` (the nut threaded onto the shank at `NUT_SEAT_TURNS` pitches, phase-aligned by integer-pitch translation). The design gate (Task 6) and this test share them.

**The gate (verified numbers at defaults, K=1):** rest interference **0.0** (a real air gap — shippable); true-lead run-down **~3.6 mm³**; axial-only jam **~6.6 mm³** (at `AXIAL_DISTANCE=0.2`); wrong-lead jam **~8.3 mm³** (at `WRONG_LEAD_FACTOR=1.25`). Two assertions: (1) **rest air gap** `rest < REST_TOL` is crisp and is the shippability check; (2) the **differential** — true-lead run-down is strictly and substantially less than both jams. The run-down residual is B-rep discretization of the swept helicoid (facet misalignment mid-turn, exactly 0 at every whole turn), *not* physical scraping; the proof is that it is dominated by the real blocking. A crisper (near-0) run-down needs `_SEGMENTS_PER_TURN > 1`, which slows the gate — see Task 3.

> **Margin note (confirm on the first gate run):** at K=1 the differential margin is real but not wide (3.6 < 0.7·6.6 = 4.6). `RUNDOWN_STATIONS=25` samples finer than the design spike (n=13), so if the run-down peak comes in higher and the assertion fails, **widen the jams, don't loosen the gate**: the jams grow monotonically with displacement (axial iv ≈ 0.06 → 5.5 → 9.0 at pushes 0.1 → 0.2 → 0.3), so bump `AXIAL_DISTANCE` toward 0.3 and `WRONG_LEAD_FACTOR` toward 1.4. Only raise `_SEGMENTS_PER_TURN` if you want the run-down itself near 0.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_fastener.py`:

```python
def test_screw_differential():
    """The fastener property: the nut runs freely DOWN the bolt on the true
    lead (screw motion) but jams under pure-axial pull-off and under a wrong
    lead (cross-threading). Free run-down is strictly dominated by both jams."""
    from claudecad.verify import (intersection_volume, path_clearance,
                                  screw_clearance)
    from claudecad.hardware.fastener import (
        AXIS, AXIAL_DISTANCE, AXIAL_STATIONS, FREE_MARGIN, REST_TOL,
        RUNDOWN_STATIONS, RUNDOWN_TURNS, WRONG_LEAD_FACTOR,
        WRONG_LEAD_STATIONS, bolt, seated_nut,
    )
    p = FastenerParams()
    b, n = bolt(p), seated_nut(p)

    # (1) real air gap at rest — parts do not interpenetrate (shippable)
    assert intersection_volume(n, b) < REST_TOL

    # (2) free / blocked differential
    run_down = max(screw_clearance(n, b, AXIS, (0, 0, 0), p.pitch,
                                   RUNDOWN_TURNS, RUNDOWN_STATIONS))
    axial = max(path_clearance(n, b, AXIS, AXIAL_DISTANCE, AXIAL_STATIONS))
    wrong = max(screw_clearance(n, b, AXIS, (0, 0, 0),
                                p.pitch * WRONG_LEAD_FACTOR, 1,
                                WRONG_LEAD_STATIONS))
    assert run_down < FREE_MARGIN * axial   # free << axial pull-off
    assert run_down < FREE_MARGIN * wrong   # free << wrong-lead cross-thread
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_fastener.py -k differential -v`
Expected: FAIL with `ImportError: cannot import name 'seated_nut'`.

- [ ] **Step 3: Add the gate constants and `seated_nut`**

Add to `claudecad/hardware/fastener.py` (the design gate and the test import these — one source):

```python
# --- screw-motion gate fixtures (shared by the design build and the test) ---
NUT_SEAT_TURNS = 2       # nut seated this many whole pitches up the shank
                         # (integer -> phase-aligned, fully engaged)
RUNDOWN_TURNS = 1.0      # revolutions of true-lead run-down to sample
RUNDOWN_STATIONS = 25    # stations across the run-down (fine enough to catch
                         # any mid-turn contact)
AXIAL_DISTANCE = 0.2     # mm of pure-axial pull to sample (past the backlash)
AXIAL_STATIONS = 7
WRONG_LEAD_FACTOR = 1.25  # cross-thread lead error for the wrong-lead leg
WRONG_LEAD_STATIONS = 13
REST_TOL = 0.1           # mm^3 — the seated air-gap ceiling (verified rest==0)
FREE_MARGIN = 0.7        # run-down must be < FREE_MARGIN * each jam (verified:
                         # 3.6 < 0.7*6.6). Tighten as the gate is made crisper.


def seated_nut(p: FastenerParams) -> Solid:
    """The nut threaded onto the bolt at NUT_SEAT_TURNS whole pitches up the
    shank. An integer-pitch translation keeps it phase-aligned with the shank
    thread (stacking guarantees integer-pitch periodicity), so it is fully
    engaged with a real air gap."""
    return Pos(0, 0, NUT_SEAT_TURNS * p.pitch) * nut(p)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_fastener.py -k differential -v`
Expected: 1 passed. (The gate builds both parts and runs ~45 booleans — allow up to ~90 s.)

- [ ] **Step 5: Run the whole fastener + verify suite**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_fastener.py tests/test_verify.py -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add claudecad/hardware/fastener.py tests/test_fastener.py
git commit -m "feat: screw-motion differential gate — the fastener property"
```

---

### Task 6: the `designs/bolt` design, skill law, and render

**Files:**
- Create: `designs/bolt/__init__.py` (empty package marker)
- Create: `designs/bolt/params.py`
- Create: `designs/bolt/build.py`
- Modify: `.claude/skills/cad/SKILL.md` (add the screw-motion gate law)

**Interfaces:**
- Consumes: everything from `claudecad.hardware.fastener` and `claudecad.verify`; `tools.export`.
- Produces: `designs/bolt/build.py::main() -> int`, runnable as `uv run python -m designs.bolt.build`.

- [ ] **Step 1: Create the design package and params**

`designs/bolt/__init__.py`: empty file.

`designs/bolt/params.py`:

```python
"""M8×1.25 hex bolt + nut parameters."""
from claudecad.hardware.fastener import FastenerParams

P = FastenerParams()  # M8×1.25 defaults
```

- [ ] **Step 2: Create the build/verify/export driver**

`designs/bolt/build.py` (same skeleton as `designs/carabiner/build.py`):

```python
"""Build, verify, and export the M8 hex bolt + nut.

Usage: uv run python -m designs.bolt.build
Writes out/glb/bolt.glb always; out/step/bolt.step only if the gate passes
(exit 1 otherwise). The gate recomputes the fastener property on the design
instance: parts clean, seated air gap, and THE fastener property — the
screw-motion differential (free run-down vs axial-pull and wrong-lead jam).
Mechanism proof is constructed states, never simulation (/cad).
"""
import sys

from claudecad.hardware.fastener import (
    AXIS, AXIAL_DISTANCE, AXIAL_STATIONS, FREE_MARGIN, REST_TOL,
    RUNDOWN_STATIONS, RUNDOWN_TURNS, WRONG_LEAD_FACTOR, WRONG_LEAD_STATIONS,
    bolt, seated_nut,
)
from claudecad.verify import (
    check_solid, intersection_volume, path_clearance, screw_clearance,
)
from tools.export import export_design, export_glb

from .params import P


def main() -> int:
    b = bolt(P)
    seated = seated_nut(P)
    parts = {"bolt": b, "nut": seated}

    # GLB always — the render/preview artifact, even for failures
    export_glb(parts, "out/glb/bolt.glb",
               linear_deflection=0.01, angular_deflection=0.1)

    ok = True

    # 1) parts clean
    for name, s in parts.items():
        r = check_solid(s)
        print(f"{name}: valid={r.is_valid} pieces={r.piece_count} "
              f"volume={r.volume:.1f}")
        ok = ok and r.ok

    # 2) seated air gap — a real clearance, not interpenetration
    rest = intersection_volume(seated, b)
    print(f"seated air gap: rest iv {rest:.4f} (< {REST_TOL})")
    ok = ok and rest < REST_TOL

    # 3) THE fastener property — the screw-motion differential
    run_down = max(screw_clearance(seated, b, AXIS, (0, 0, 0), P.pitch,
                                   RUNDOWN_TURNS, RUNDOWN_STATIONS))
    axial = max(path_clearance(seated, b, AXIS, AXIAL_DISTANCE, AXIAL_STATIONS))
    wrong = max(screw_clearance(seated, b, AXIS, (0, 0, 0),
                                P.pitch * WRONG_LEAD_FACTOR, 1,
                                WRONG_LEAD_STATIONS))
    print(f"differential: run-down {run_down:.3f} (free) vs axial {axial:.3f}, "
          f"wrong-lead {wrong:.3f} (blocked)")
    ok = ok and run_down < FREE_MARGIN * axial
    ok = ok and run_down < FREE_MARGIN * wrong

    if not ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1
    export_design(parts, "out/step/bolt.step", assembly_label="bolt")
    print("exported out/step/bolt.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run the design gate**

Run: `cd /Users/mike/code/claudeCAD && uv run python -m designs.bolt.build`
Expected: prints clean parts, `rest iv 0.0000`, a differential line with run-down well under both jams, and `exported out/step/bolt.step`; exit 0. (~1–2 min — the thread build plus ~45 gate booleans.)

- [ ] **Step 4: Confirm the design-import test still passes**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_designs_import.py -v`
Expected: pass (auto-discovers `designs/bolt`).

- [ ] **Step 5: Add the screw-motion gate law to the /cad skill**

In `.claude/skills/cad/SKILL.md`, beside the carabiner's escape-differential entry in the mechanism-proof law, add:

> - **Threaded / screw joint** (`hardware/fastener`): proven by a screw sweep on the shipped geometry — the nut runs FREE down the bolt at the true lead (`screw_clearance`, interference dominated by the jams and 0 at every whole turn) but is BLOCKED under pure-axial pull (`path_clearance`) and under a wrong lead. Clearance is a flank-normal profile offset so the seated pair keeps a real air gap (rest interference 0). Threads are pitch-periodic by stacking one swept turn — a continuous multi-turn sweep drifts.

- [ ] **Step 6: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add designs/bolt .claude/skills/cad/SKILL.md
git commit -m "feat: designs/bolt — M8 hex bolt+nut design, gate, and skill law"
```

- [ ] **Step 7: Render and judge against a reference**

Run: `cd /Users/mike/code/claudeCAD && uv run python tools/render.py out/glb/bolt.glb --outdir out/renders/bolt`
Then judge `out/renders/bolt/*.png` against a real M8 hex bolt reference photo (fetch one during implementation): hex proportions, thread pitch/lead angle, head height, nut engagement. Iterate `params.py` (never weaken the gate) until the proportions read true, then re-run the gate and re-render. Mike is the final judge in Plasticity via `out/step/bolt.step`.

---

## Notes for the implementer

- **Gate speed / crispness knob:** `_SEGMENTS_PER_TURN` (Task 3) trades gate speed for run-down crispness. K=1 (default) is light and fast with run-down ~3.6 mm³ (discretization-level, dominated by the ~7–8 mm³ jams). Raising K shrinks run-down toward ~0 but the heavier thread B-rep makes the gate booleans much slower (K≥4 measured in minutes) — only raise it if a crisper gate is worth the wall-clock, and consider fewer `nut_turns` to compensate.
- **Do not** substitute `is_frenet=True` in the sweep (pathologically slow on multi-turn, malformed on a single turn) or a continuous multi-turn `Helix` sweep (drifts, breaks pitch-periodicity).
- **Tuning is against the gate, never around it:** if a proportion change breaks a leg, fix the geometry — never widen `FREE_MARGIN`/`REST_TOL` to pass.
