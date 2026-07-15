# Ball Bearing (Hardware Phase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a verified 608-geometry cageless deep-groove ball bearing, proven by the repo's first multi-body orbital gate.

**Architecture:** Fix a real upstream false-negative in `check_solid`'s manifold test (build123d 0.11.1 mis-detects degenerate edges — closed spheres read non-manifold), then build races as solids of revolution (annulus − torus), balls as rotation-placed spheres, and gate with: crisp-0 rest clearance + gap band, the 7-ball ring swept as ONE compound via `screw_clearance(lead=0)` over a single 360/7° symmetry period, per-ball capture differentials, and an eccentric-groove negative control that proves the sweep has teeth.

**Tech Stack:** build123d 0.11.1 (`Cylinder`/`Torus`/`Sphere` booleans; OCP for the corrected edge test), Python 3.14, uv, pytest; STEP+GLB via `tools/export.py`.

## Global Constraints

- build123d **0.11.1**, Python **3.14** (pinned); run everything with `uv run`.
- **A bearing is a CLEARANCE mechanism** (method law): boolean gates must read **crisp 0** — any nonzero interference is a real defect, never tolerated as "noise".
- **Never weaken a gate to pass.** The corrected manifold check (Task 1) fixes a checker bug with the canonical OCCT test — it does not relax the criterion (genuinely non-manifold shapes still fail).
- Every part `check_solid(...).ok` (valid ∧ manifold ∧ single ∧ volume>0); the exported pose is itself gated (all-pairs interference == 0).
- Follow `hardware/carabiner.py`/`hardware/fastener.py` conventions: frozen validated params (value-carrying `ValueError`s), shared module gate fixtures (one source for design build + tests).
- mm units. Verified spike constants (2026-07-15): pitch_r 7.5, groove_r 2.0639 (= 0.52·3.969), inner shoulder r 6.825, outer shoulder r 8.175, rest gap 0.0794 (= groove_r − ball_d/2), ball-to-ball gap 2.5393, orbital sweep max 0.000000, capture blocked ≈19.1/19.0/11.4 mm³ vs free 0.000000, eccentric(+0.15) sweep ≥0.146 at every station.
- `tests/test_designs_import.py` is a **hardcoded list** (it does not auto-discover) — new designs must be registered there.

---

### Task 1: corrected watertight/manifold check in `verify`

**Files:**
- Modify: `claudecad/verify.py` (add `_edges_watertight`, use it in `check_solid`)
- Test: `tests/test_verify.py` (append)

**Interfaces:**
- Consumes: existing `SolidReport`/`check_solid`.
- Produces: `check_solid` whose `is_manifold` field is computed by the corrected edge test — `Sphere` now passes `.ok`; genuinely non-manifold shapes still fail. Every later task's parts-clean checks rely on this.

**Why (verified):** build123d 0.11.1's `Shape.is_manifold` skips "degenerate edges" only when *both vertices are null* — but real degenerate edges (a sphere's pole edges) carry vertices, so they are counted, border one face instead of two, and a closed watertight `Sphere` reads non-manifold. The canonical OCCT degeneracy test is `BRep_Tool.Degenerated_s(edge)`. Corrected check verified: Sphere/Box/Torus/grooved-race → True; two boxes glued on one edge (4 faces on an edge) → False.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_verify.py`:

```python
def test_check_solid_sphere_is_watertight():
    # build123d 0.11.1 Shape.is_manifold false-negatives on spheres: pole
    # edges are degenerate but carry vertices, so its null-vertex skip never
    # fires and the single-face count fails. check_solid must use the
    # canonical OCCT degeneracy test instead (BRep_Tool.Degenerated_s).
    from build123d import Sphere
    from claudecad.verify import check_solid
    r = check_solid(Sphere(2.0))
    assert r.is_manifold and r.ok


def test_check_solid_still_rejects_nonmanifold():
    # two boxes sharing exactly one edge: that edge borders 4 faces
    from build123d import Box, Pos
    from claudecad.verify import check_solid
    bad = Box(1, 1, 1) + Pos(1, 1, 0) * Box(1, 1, 1)
    assert not check_solid(bad).is_manifold
```

- [ ] **Step 2: Run the tests to verify the sphere one fails**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_verify.py -k "sphere or nonmanifold" -v`
Expected: `test_check_solid_sphere_is_watertight` FAILS (is_manifold False under the buggy upstream test); the non-manifold test may already pass.

- [ ] **Step 3: Implement the corrected check**

In `claudecad/verify.py`, add after the imports (OCP is the same binding build123d itself uses):

```python
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape


def _edges_watertight(shape) -> bool:
    """Manifold/watertight test: every non-degenerate edge borders exactly
    two faces. Replaces build123d 0.11.1's Shape.is_manifold, whose
    degenerate-edge skip checks for null vertices — real degenerate edges
    (e.g. sphere poles) carry vertices, so closed spheres read non-manifold.
    Uses OCCT's canonical degeneracy test (BRep_Tool.Degenerated_s);
    genuinely non-manifold shapes (an edge bordering != 2 faces) still fail."""
    edge_map = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shape.wrapped, TopAbs_EDGE, TopAbs_FACE,
                                   edge_map)
    for i in range(edge_map.Extent()):
        if BRep_Tool.Degenerated_s(TopoDS.Edge_s(edge_map.FindKey(i + 1))):
            continue
        if edge_map.FindFromIndex(i + 1).Extent() != 2:
            return False
    return True
```

And in `check_solid`, replace `shape.is_manifold` with `_edges_watertight(shape)`:

```python
def check_solid(shape) -> SolidReport:
    return SolidReport(
        shape.is_valid, _edges_watertight(shape), shape.volume,
        len(shape.solids())
    )
```

- [ ] **Step 4: Run the tests to verify they pass, then the full suite**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_verify.py -v` then `uv run pytest -q`
Expected: all pass (existing parts already satisfied the stricter-on-nothing corrected test; 106+2 total).

- [ ] **Step 5: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add claudecad/verify.py tests/test_verify.py
git commit -m "fix: correct manifold test — degenerate edges via BRep_Tool

build123d 0.11.1's is_manifold null-vertex skip never fires on real
degenerate edges (sphere poles carry vertices), so closed spheres read
non-manifold. Use OCCT's canonical Degenerated_s; non-manifold still fails."
```

---

### Task 2: `BearingParams`, races, and balls

**Files:**
- Create: `claudecad/hardware/bearing.py`
- Test: `tests/test_bearing.py`

**Interfaces:**
- Consumes: `check_solid` (Task 1 semantics).
- Produces: `BearingParams` (frozen; fields `bore=8.0`, `outer_d=22.0`, `width=7.0`, `n_balls=7`, `ball_d=3.969`, `osculation=0.52`, `shoulder_frac=0.35`; computed `pitch_radius`, `groove_radius`, `inner_shoulder_radius`, `outer_shoulder_radius`, `rest_gap`); `inner_race(p)`, `outer_race(p)`, `ball(p, i)`, `ball_ring(p)`; module constant `AXIS = (0.0, 0.0, 1.0)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bearing.py`:

```python
import math

import pytest

from claudecad.hardware.bearing import (
    BearingParams, ball, ball_ring, inner_race, outer_race,
)
from claudecad.verify import check_solid, clearance, intersection_volume


def test_derived_geometry_608():
    p = BearingParams()
    assert math.isclose(p.pitch_radius, 7.5, rel_tol=1e-12)
    assert math.isclose(p.groove_radius, 0.52 * 3.969, rel_tol=1e-12)
    assert math.isclose(p.rest_gap, p.groove_radius - p.ball_d / 2,
                        rel_tol=1e-12)  # 0.0794 at defaults
    # verified spike values
    assert math.isclose(p.inner_shoulder_radius, 6.825, abs_tol=5e-4)
    assert math.isclose(p.outer_shoulder_radius, 8.175, abs_tol=5e-4)


def test_params_validation():
    with pytest.raises(ValueError):
        BearingParams(bore=0.0)
    with pytest.raises(ValueError):
        # capture inequality: shoulder gap must be < ball_d
        BearingParams(shoulder_frac=0.01)
    with pytest.raises(ValueError):
        # balls must fit on the pitch circle (chord spacing > ball_d)
        BearingParams(n_balls=13)


def test_parts_clean():
    p = BearingParams()
    for name, s in (("inner", inner_race(p)), ("outer", outer_race(p)),
                    ("ball", ball(p, 0))):
        r = check_solid(s)
        assert r.ok, f"{name}: valid={r.is_valid} manifold={r.is_manifold} pieces={r.piece_count}"


def test_ball_placement_law():
    p = BearingParams()
    balls = [ball(p, i) for i in range(p.n_balls)]
    # centers on the pitch circle, equal chord spacing, pairwise clear
    chord = 2 * p.pitch_radius * math.sin(math.pi / p.n_balls)
    for i, b in enumerate(balls):
        c = b.center()
        assert math.isclose(math.hypot(c.X, c.Y), p.pitch_radius, abs_tol=1e-9)
        assert abs(c.Z) < 1e-9
    for i in range(p.n_balls):
        j = (i + 1) % p.n_balls
        d = (balls[i].center() - balls[j].center()).length
        assert math.isclose(d, chord, abs_tol=1e-9)
        assert intersection_volume(balls[i], balls[j]) == 0.0
    # spike-verified surface gap between neighbors: 2.5393
    assert math.isclose(clearance(balls[0], balls[1]), chord - p.ball_d,
                        abs_tol=1e-6)
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_bearing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'claudecad.hardware.bearing'`.

- [ ] **Step 3: Implement the module**

Create `claudecad/hardware/bearing.py`:

```python
"""608-geometry cageless deep-groove ball bearing.

Local frame: bearing axis +Z (`AXIS`), races centered on the origin, balls on
the pitch circle at z=0. Races are exact solids of revolution — an annular
cylinder minus a groove TORUS whose tube radius is the osculation-scaled ball
radius — so raceway axisymmetry is by construction, and the orbital gate
(designs/bearing_608) exists to PROVE it rather than assume it. A bearing is a
CLEARANCE mechanism (balls never touch races; rest gap = groove_r − ball_r),
so every boolean gate must read crisp 0 — per the /cad method law, unlike the
fastener's contact mesh which needed an analytic gate.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from build123d import Compound, Cylinder, Pos, Shape, Solid, Sphere, Torus

AXIS: tuple[float, float, float] = (0.0, 0.0, 1.0)


@dataclass(frozen=True)
class BearingParams:
    """Driving dimensions, mm — 608 defaults. osculation is groove-to-ball
    conformity (raceway groove radius = osculation·ball_d; deep-groove
    standard band ≈ 0.515–0.53); shoulder_frac is shoulder height above the
    groove bottom as a fraction of ball_d. The rest radial gap is DERIVED:
    groove_radius − ball_d/2 (0.0794 at defaults) — a design value for robust
    booleans, not a manufacturing clearance."""

    bore: float = 8.0
    outer_d: float = 22.0
    width: float = 7.0
    n_balls: int = 7
    ball_d: float = 3.969
    osculation: float = 0.52
    shoulder_frac: float = 0.35

    def __post_init__(self):
        bad = {k: v for k, v in self.__dict__.items() if v <= 0}
        if bad:
            raise ValueError(f"all bearing params must be > 0, got {bad}")
        if not self.bore < 2 * self.inner_shoulder_radius:
            raise ValueError(
                f"bore={self.bore} leaves no inner race wall "
                f"(inner shoulder radius {self.inner_shoulder_radius:.3f})"
            )
        if not self.outer_shoulder_radius < self.outer_d / 2:
            raise ValueError(
                f"outer_d={self.outer_d} leaves no outer race wall "
                f"(outer shoulder radius {self.outer_shoulder_radius:.3f})"
            )
        shoulder_gap = self.outer_shoulder_radius - self.inner_shoulder_radius
        if not shoulder_gap < self.ball_d:
            raise ValueError(
                f"capture inequality violated: radial shoulder gap "
                f"{shoulder_gap:.3f} must be < ball_d={self.ball_d} or balls "
                "escape radially between the shoulders"
            )
        chord = 2 * self.pitch_radius * math.sin(math.pi / self.n_balls)
        if not chord > self.ball_d:
            raise ValueError(
                f"n_balls={self.n_balls} do not fit: pitch-circle chord "
                f"{chord:.3f} must exceed ball_d={self.ball_d}"
            )
        if self.rest_gap <= 0:
            raise ValueError(
                f"osculation={self.osculation} gives rest_gap "
                f"{self.rest_gap:.4f}; must be > 0 (groove must be wider "
                "than the ball)"
            )

    @property
    def pitch_radius(self) -> float:
        return (self.bore + self.outer_d) / 4

    @property
    def groove_radius(self) -> float:
        return self.osculation * self.ball_d

    @property
    def inner_shoulder_radius(self) -> float:
        return (self.pitch_radius - self.groove_radius
                + self.shoulder_frac * self.ball_d)

    @property
    def outer_shoulder_radius(self) -> float:
        return (self.pitch_radius + self.groove_radius
                - self.shoulder_frac * self.ball_d)

    @property
    def rest_gap(self) -> float:
        """Radial air gap between a centered ball and either raceway."""
        return self.groove_radius - self.ball_d / 2


def _groove_torus(p: BearingParams) -> Solid:
    return Torus(p.pitch_radius, p.groove_radius)


def inner_race(p: BearingParams) -> Solid:
    """Annulus bore/2..inner_shoulder_radius minus the groove torus."""
    return (Cylinder(p.inner_shoulder_radius, p.width)
            - Cylinder(p.bore / 2, p.width + 1)
            - _groove_torus(p))


def outer_race(p: BearingParams) -> Solid:
    """Annulus outer_shoulder_radius..outer_d/2 minus the groove torus."""
    return (Cylinder(p.outer_d / 2, p.width)
            - Cylinder(p.outer_shoulder_radius, p.width + 1)
            - _groove_torus(p))


def ball(p: BearingParams, i: int) -> Solid:
    """The i-th ball: rotation-copy placement law — ball i sits on the pitch
    circle at angle 2πi/n_balls, z=0. All balls congruent by construction, so
    symmetry arguments in the gates (capture checked on ball 0) are sound."""
    if not 0 <= i < p.n_balls:
        raise ValueError(f"ball index {i} out of range 0..{p.n_balls - 1}")
    a = 2 * math.pi * i / p.n_balls
    return Pos(p.pitch_radius * math.cos(a), p.pitch_radius * math.sin(a),
               0) * Sphere(p.ball_d / 2)


def ball_ring(p: BearingParams) -> Shape:
    """All n_balls as ONE multi-body moving set (a Compound — verified to
    work directly as `moving` in screw_clearance) for the orbital gate."""
    return Compound(children=[ball(p, i) for i in range(p.n_balls)])
```

- [ ] **Step 4: Run to verify they pass, then the full suite**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_bearing.py -v` then `uv run pytest -q`
Expected: 4 passed; full suite green.

- [ ] **Step 5: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add claudecad/hardware/bearing.py tests/test_bearing.py
git commit -m "feat: 608 bearing geometry — revolved races, rotation-placed balls"
```

---

### Task 3: the four functional proofs + negative control

**Files:**
- Modify: `claudecad/hardware/bearing.py` (gate fixtures + eccentric helper)
- Test: `tests/test_bearing.py` (append)

**Interfaces:**
- Consumes: Task 2's parts, `screw_clearance`/`path_clearance`/`clearance`/`intersection_volume`.
- Produces: module gate fixtures `ORBIT_STATIONS = 15`, `REST_MAX_GAP = 0.1`, `escape_distance(p) -> float`; test-support `outer_race_eccentric(p, offset) -> Solid`. The design gate (Task 4) imports the fixtures.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_bearing.py`:

```python
def test_rest_clearance_band():
    """Proof 1: crisp 0 interference AND a positive near-contact gap band."""
    from claudecad.hardware.bearing import REST_MAX_GAP
    p = BearingParams()
    b0, ir, orc = ball(p, 0), inner_race(p), outer_race(p)
    for race in (ir, orc):
        assert intersection_volume(b0, race) == 0.0
        g = clearance(b0, race)
        assert 0 < g <= REST_MAX_GAP
        # spike-verified: gap == rest_gap == 0.0794 at defaults
        assert math.isclose(g, p.rest_gap, abs_tol=1e-3)


def test_orbital_free_spin():
    """Proof 2 (THE multi-body gate): the 7-ball ring, moved as one compound,
    sweeps one 360/n symmetry period with zero interference at every station."""
    from claudecad.hardware.bearing import AXIS, ORBIT_STATIONS
    from claudecad.verify import screw_clearance
    p = BearingParams()
    races = inner_race(p) + outer_race(p)
    vals = screw_clearance(ball_ring(p), races, AXIS, (0, 0, 0),
                           0.0, 1.0 / p.n_balls, ORBIT_STATIONS)
    assert max(vals) == 0.0


def test_capture_differential():
    """Proof 3: ball 0 (all balls congruent by the placement law) is blocked
    radially out/in and axially with both races present; removing the outer
    race frees the radial-out escape — the carabiner differential, per ball."""
    from claudecad.hardware.bearing import escape_distance
    from claudecad.verify import path_clearance
    p = BearingParams()
    b0, ir, orc = ball(p, 0), inner_race(p), outer_race(p)
    races = ir + orc
    d = escape_distance(p)
    assert max(path_clearance(b0, races, (1, 0, 0), d, 9)) > 0.0    # out: blocked
    assert max(path_clearance(b0, races, (-1, 0, 0), p.pitch_radius, 9)) > 0.0  # in
    assert max(path_clearance(b0, races, (0, 0, 1), p.width, 9)) > 0.0          # axial
    assert max(path_clearance(b0, ir, (1, 0, 0), d, 9)) == 0.0      # sans outer: FREE


def test_eccentric_groove_fails_orbit():
    """Negative control (pins the non-tautology claim): an outer race whose
    groove is displaced 0.15 mm off-axis must FAIL the orbital sweep — the
    gate detects broken axisymmetry (spike-verified: iv >= 0.146 at every
    station of the period)."""
    from claudecad.hardware.bearing import (AXIS, ORBIT_STATIONS,
                                            outer_race_eccentric)
    from claudecad.verify import screw_clearance
    p = BearingParams()
    races_bad = inner_race(p) + outer_race_eccentric(p, 0.15)
    vals = screw_clearance(ball_ring(p), races_bad, AXIS, (0, 0, 0),
                           0.0, 1.0 / p.n_balls, ORBIT_STATIONS)
    assert max(vals) > 0.0
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_bearing.py -k "rest or orbital or capture or eccentric" -v`
Expected: FAIL with `ImportError: cannot import name 'REST_MAX_GAP'` (etc.).

- [ ] **Step 3: Add the gate fixtures**

Add to `claudecad/hardware/bearing.py`:

```python
# --- gate fixtures (one source for the design build and the tests) ---
ORBIT_STATIONS = 15   # stations across one 360/n_balls symmetry period
REST_MAX_GAP = 0.1    # mm — near-contact band ceiling on the rest gap
                      # (rest_gap 0.0794 at defaults sits inside it)


def escape_distance(p: BearingParams) -> float:
    """Radial translation that carries a ball clearly past the outer race's
    envelope (used by the capture differential)."""
    return p.outer_d / 2 + p.ball_d / 2 - p.pitch_radius + 1.0


def outer_race_eccentric(p: BearingParams, offset: float) -> Solid:
    """DEFECTIVE outer race for the negative control: the groove torus is
    displaced `offset` mm off-axis, breaking raceway axisymmetry. The orbital
    gate must fail on it — that failure is what proves the sweep checks
    axisymmetry rather than assuming it."""
    return (Cylinder(p.outer_d / 2, p.width)
            - Cylinder(p.outer_shoulder_radius, p.width + 1)
            - Pos(offset, 0, 0) * _groove_torus(p))
```

- [ ] **Step 4: Run to verify they pass, then the full suite**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_bearing.py -v` then `uv run pytest -q`
Expected: 8 passed (Task 2's four + these four); full suite green. The orbital tests take a few seconds each (boolean sweeps; spike measured ~0.3 s per 8-station sweep).

- [ ] **Step 5: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add claudecad/hardware/bearing.py tests/test_bearing.py
git commit -m "feat: bearing proofs — orbital free-spin, capture, negative control"
```

---

### Task 4: `designs/bearing_608`, skill law, registration, render

**Files:**
- Create: `designs/bearing_608/__init__.py` (empty), `designs/bearing_608/params.py`, `designs/bearing_608/build.py`
- Modify: `tests/test_designs_import.py` (register — hardcoded list), `.claude/skills/cad/SKILL.md` (multi-body law)

**Interfaces:**
- Consumes: everything from `claudecad.hardware.bearing`, `claudecad.verify`, `tools.export`.
- Produces: `designs/bearing_608/build.py::main() -> int`, runnable as `uv run python -m designs.bearing_608.build`.

- [ ] **Step 1: Create the design package**

`designs/bearing_608/__init__.py`: empty file.

`designs/bearing_608/params.py`:

```python
"""608 deep-groove ball bearing parameters (8 x 22 x 7, 7 balls)."""
from claudecad.hardware.bearing import BearingParams

P = BearingParams()
```

`designs/bearing_608/build.py`:

```python
"""Build, verify, and export the 608 deep-groove ball bearing.

Usage: uv run python -m designs.bearing_608.build
GLB always; STEP only if the gate passes (exit 1 otherwise). The gate: all 9
parts clean, rest clearance crisp 0 with a positive near-contact gap, THE
bearing property — the 7-ball ring swept as one compound about the axis
(orbital free-spin, one 360/7 symmetry period) with zero interference — the
per-ball capture differential, and the shipped-pose all-pairs guard. A
bearing is a clearance mechanism: every boolean here must read exactly 0.
"""
import sys

from claudecad.hardware.bearing import (
    AXIS, ORBIT_STATIONS, REST_MAX_GAP, ball, ball_ring, escape_distance,
    inner_race, outer_race,
)
from claudecad.verify import (
    check_solid, clearance, intersection_volume, path_clearance,
    screw_clearance,
)
from tools.export import export_design, export_glb

from .params import P


def main() -> int:
    ir, orc = inner_race(P), outer_race(P)
    balls = [ball(P, i) for i in range(P.n_balls)]
    parts = {"bearing_inner": ir, "bearing_outer": orc}
    parts.update({f"ball_{i + 1}": b for i, b in enumerate(balls)})

    # GLB always — the render/preview artifact, even for failures
    export_glb(parts, "out/glb/bearing_608.glb",
               linear_deflection=0.01, angular_deflection=0.1)

    ok = True

    # 1) parts clean
    for name, s in parts.items():
        r = check_solid(s)
        print(f"{name}: valid={r.is_valid} manifold={r.is_manifold} "
              f"pieces={r.piece_count} volume={r.volume:.1f}")
        ok = ok and r.ok

    # 2) rest clearance: crisp 0 + positive near-contact band (ball 0 vs
    #    each race; all balls congruent by the placement law)
    for name, race in (("inner", ir), ("outer", orc)):
        iv = intersection_volume(balls[0], race)
        g = clearance(balls[0], race)
        print(f"rest vs {name}: iv {iv:.4f} (==0), gap {g:.4f} "
              f"(0 < gap <= {REST_MAX_GAP})")
        ok = ok and iv == 0.0 and 0 < g <= REST_MAX_GAP

    # 3) THE bearing property — multi-body orbital free-spin over one
    #    360/n symmetry period, the ball ring moved as ONE compound
    races = ir + orc
    orbit = screw_clearance(ball_ring(P), races, AXIS, (0, 0, 0),
                            0.0, 1.0 / P.n_balls, ORBIT_STATIONS)
    print(f"orbital free-spin over 360/{P.n_balls} deg x {ORBIT_STATIONS} "
          f"stations: max iv {max(orbit):.6f} (==0)")
    ok = ok and max(orbit) == 0.0

    # 4) capture differential (ball 0): blocked out/in/axial; free sans outer
    d = escape_distance(P)
    b_out = max(path_clearance(balls[0], races, (1, 0, 0), d, 9))
    b_in = max(path_clearance(balls[0], races, (-1, 0, 0), P.pitch_radius, 9))
    b_ax = max(path_clearance(balls[0], races, (0, 0, 1), P.width, 9))
    free = max(path_clearance(balls[0], ir, (1, 0, 0), d, 9))
    print(f"capture: out {b_out:.3f} / in {b_in:.3f} / axial {b_ax:.3f} "
          f"(all >0) | sans outer {free:.6f} (==0)")
    ok = ok and b_out > 0 and b_in > 0 and b_ax > 0 and free == 0.0

    # 5) shipped-pose guard: the exported assembly has zero interference
    #    across ALL part pairs (clearance mechanism -> crisp 0)
    names = list(parts)
    worst = max(
        intersection_volume(parts[names[i]], parts[names[j]])
        for i in range(len(names)) for j in range(i + 1, len(names))
    )
    print(f"shipped-pose all-pairs worst iv: {worst:.6f} (==0)")
    ok = ok and worst == 0.0

    if not ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1
    export_design(parts, "out/step/bearing_608.step",
                  assembly_label="bearing_608")
    print("exported out/step/bearing_608.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the design gate**

Run: `cd /Users/mike/code/claudeCAD && uv run python -m designs.bearing_608.build`
Expected: 9 clean parts, rest gaps 0.0794 in band, orbital max 0.000000, capture out/in/axial ≈ 19.1/19.0/11.4 vs free 0.000000, all-pairs 0.000000, `exported out/step/bearing_608.step`, exit 0.

- [ ] **Step 3: Register in the designs-import smoke test**

In `tests/test_designs_import.py`, add `"designs.bearing_608.build"` and `"designs.bearing_608.params"` entries following the existing hardcoded pattern (open the file and match how `designs.bolt` is listed — it does NOT auto-discover).

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_designs_import.py -v`
Expected: pass, with the two new bearing entries collected.

- [ ] **Step 4: Add the multi-body law to the /cad skill**

In `.claude/skills/cad/SKILL.md`, beside the threaded-joint entry in the mechanism-proof section, add:

> - **Multi-body / rolling set** (`hardware/bearing`): a mechanism whose moving element is a SET of bodies is gated by moving the set as ONE compound (`screw_clearance` accepts it directly). Discrete N-fold symmetry means one 360/N period proves the full revolution. On axisymmetric obstacles the sweep's value is PROVING the axisymmetry — material-adding or raceway-displacing defects (eccentric groove, inward dent) fail it; every design carries a negative control that pins this. Clearance mechanisms read crisp 0 — any nonzero is a defect, never noise.

- [ ] **Step 5: Run the full suite, commit**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest -q`
Expected: all pass.

```bash
cd /Users/mike/code/claudeCAD
git add designs/bearing_608 tests/test_designs_import.py .claude/skills/cad/SKILL.md
git commit -m "feat: designs/bearing_608 — multi-body orbital gate design + skill law"
```

- [ ] **Step 6: Render and judge**

Run: `cd /Users/mike/code/claudeCAD && uv run python tools/render.py out/glb/bearing_608.glb --outdir out/renders/bearing_608`
Judge `out/renders/bearing_608/*.png` against a real 608 bearing reference: concentric races, balls seated in the groove, correct proportions (22 mm OD vs 7 mm width). Tooling lens: geometry defects matter; cosmetics don't. Mike is final judge in Plasticity via `out/step/bearing_608.step`.

---

## Notes for the implementer

- **Crisp-0 discipline:** every boolean in this design must read exactly 0.0. If any gate reads a small nonzero, that is a geometry bug to fix (unlike the fastener's analytic-vs-facet situation) — do not add tolerances.
- **The Compound works:** `screw_clearance` takes the `ball_ring` Compound directly as `moving` (spike-verified, 0.3 s for an 8-station sweep). No fusing needed.
- **Symmetry arguments are load-bearing:** capture is checked on ball 0 only because `ball(p, i)` is a rotation-copy placement law pinned by `test_ball_placement_law`. If the placement law changes, the symmetry argument (and the orbit period) must be revisited.
- Spike constants (shoulders 6.825/8.175, rest gap 0.0794, blocked ≈19/19/11.4, eccentric ≥0.146/station) are at defaults; they are printed by the gate, asserted loosely in tests (`>0`/`==0`/band), and exactly derived where exact (`rest_gap`).
