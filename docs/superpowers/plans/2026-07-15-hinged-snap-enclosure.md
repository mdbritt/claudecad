# Hinged Snap Enclosure (Hardware Phase 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a verified hinged snap-latch parts-box — the repo's first partial-arc, off-origin rotational gates (swing, travel-limit, snap retention).

**Architecture:** Prismatic construction throughout (boxes, cylinders, generic-position fuses). The lid is built in the CLOSED pose with two constructed latch states (relaxed/deflected — the clasp's tongue convention); gates sweep it about the hinge axis with `screw_clearance(lead=0)` where `center` is the hinge point far from the origin. The travel stop is a fin CONSTRUCTED AT the stop angle by rotating a radial block about the hinge — parametric by construction. The negative control sweeps about a DISPLACED center, proving the gate detects a mis-built hinge axis.

**Tech Stack:** build123d 0.11.1 (Box/Cylinder/Pos/Rot/Location), Python 3.14, uv, pytest; STEP+GLB via `tools/export.py`.

## Global Constraints

- build123d **0.11.1**, Python **3.14** (pinned); run everything with `uv run`.
- **Clearance mechanism** (method law): all boolean gates read **crisp 0** — any nonzero at a free station is a real defect. Design air gap `clearance = 0.15` at every mating pair; NOTHING touches (a tangent contact is a defect — the hinge height is DERIVED as `base_h + knuckle_d/2 + clearance` for exactly this reason; spike round 3 caught the tangency at the undersized value).
- **Never weaken a gate.** The spike-verified expectations below are the ground truth; if a transcription produces different numbers, fix the geometry, not the assertion.
- Every part `check_solid(...).ok`; shipped pose (closed, relaxed, pin seated) gated pairwise-0 with the near-contact band.
- House conventions per `hardware/carabiner.py`/`hardware/bearing.py`: frozen validated params, module gate fixtures shared by design build + tests; positional layout constants tuned at defaults (carabiner `_ring_geometry` precedent) documented as such.
- **Spike-verified constants (2026-07-15, 4 rounds):** hinge axis `(1,0,0)` through `(0, −15, 15.15)`; swing 0→90° all-0 (10 stations); overtravel from the open pose free ≤100°, blocked ≥105° (0.91 @105° → 5.5 @115°); retention: relaxed blocked 1–5° (max ≈7.0, station 0 == 0), deflected free through 8°; pin escapes blocked +Z ≈79.7 / +Y ≈79.6 / ±X ≈4.7 (blind outer bores, single through-bore length 33, pin length 32; sweep distance = knuckle_d so stations sample the blocking band densely — post-ship fix 42b279e); displaced-center (+0.5 y) sweep max ≈21.2 (as-shipped fin width); part volumes base ≈5552 / lid ≈3655 / pin ≈100.5.
- `tests/test_designs_import.py` is a **hardcoded list** — register new designs there.

---

### Task 1: `SnapBoxParams` + part constructors

**Files:**
- Create: `claudecad/hardware/snapbox.py`
- Test: `tests/test_snapbox.py`

**Interfaces:**
- Produces: `SnapBoxParams` (frozen; driving fields with defaults `outer_l=40.0`, `outer_w=30.0`, `base_h=12.0`, `lid_t=3.0`, `wall=2.0`, `knuckle_d=6.0`, `knuckle_w=6.0`, `pin_d=2.0`, `clearance=0.15`, `swing_deg=90.0`, `stop_fin_deg=108.0`, `deflect_deg=14.0`; computed `hinge_center -> tuple`, `bore_radius`, `lid_z0`); `HINGE_AXIS = (1.0, 0.0, 0.0)`; `base(p)`, `lid(p, state)`, `hinge_pin(p)`; private `_rot_about(center, axis, deg, shape)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_snapbox.py`:

```python
import math

import pytest

from claudecad.hardware.snapbox import (
    HINGE_AXIS, SnapBoxParams, base, hinge_pin, lid,
)
from claudecad.verify import check_solid, clearance, intersection_volume


def test_derived_geometry():
    p = SnapBoxParams()
    # hinge height is DERIVED: base_h + knuckle radius + clearance — the
    # spike caught an exact knuckle-to-wall tangency at anything less
    assert p.hinge_center == (0.0, -15.0, 15.15)
    assert math.isclose(p.bore_radius, 1.15, rel_tol=1e-12)
    assert math.isclose(p.lid_z0, 12.15, rel_tol=1e-12)


def test_params_validation():
    with pytest.raises(ValueError):
        SnapBoxParams(wall=0.0)
    with pytest.raises(ValueError):
        # stop must lie beyond the swing range
        SnapBoxParams(stop_fin_deg=85.0)
    with pytest.raises(ValueError):
        # pin (+2*clearance) must fit inside the knuckle
        SnapBoxParams(pin_d=6.0)


def test_parts_clean():
    p = SnapBoxParams()
    for name, s in (("base", base(p)), ("lid_relaxed", lid(p, "relaxed")),
                    ("lid_deflected", lid(p, "deflected")),
                    ("pin", hinge_pin(p))):
        r = check_solid(s)
        assert r.ok, f"{name}: valid={r.is_valid} manifold={r.is_manifold} pieces={r.piece_count}"


def test_lid_states_differ_only_in_snap():
    # same volume to within the tilt's sliver; both single solids
    p = SnapBoxParams()
    vr, vd = lid(p, "relaxed").volume, lid(p, "deflected").volume
    assert abs(vr - vd) < 5.0
    with pytest.raises(ValueError):
        lid(p, "open")  # invalid state name


def test_shipped_pose_clearances():
    """Closed, relaxed, pin seated: crisp 0 everywhere, real air gaps."""
    p = SnapBoxParams()
    b, l, pin = base(p), lid(p, "relaxed"), hinge_pin(p)
    assert intersection_volume(b, l) == 0.0
    assert intersection_volume(b, pin) == 0.0
    assert intersection_volume(l, pin) == 0.0
    assert math.isclose(clearance(pin, b), p.clearance, abs_tol=1e-6)
    assert math.isclose(clearance(pin, l), p.clearance, abs_tol=1e-6)
    assert math.isclose(clearance(l, b), p.clearance, abs_tol=1e-2)
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_snapbox.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'claudecad.hardware.snapbox'`.

- [ ] **Step 3: Implement the module**

Create `claudecad/hardware/snapbox.py`:

```python
"""Hinged snap-latch parts-box: base, lid on a pin hinge, cantilever snap.

Local frame: box centered on XY, base z in [0, base_h], lid plate above it
with `clearance` air; hinge axis parallel X along the back top edge at the
DERIVED height base_h + knuckle_d/2 + clearance (anything lower makes the
lid knuckles exactly tangent to the wall top — a coincident contact the
spike caught). The lid is built CLOSED with two constructed latch states
(relaxed / deflected, the box-clasp tongue convention); gates swing it about
the hinge with screw_clearance(lead=0) and an OFF-ORIGIN center. The travel
stop is a fin constructed AT the stop angle by rotating a radial block about
the hinge — the stop angle is parametric by construction. Prismatic
construction throughout: generic-position fuses only, nothing touches
(clearance mechanism -> every boolean gate reads crisp 0).

Knuckle layout, latch, and catch positions are tuned at the default
dimensions (carabiner _ring_geometry precedent) and are unverified for
arbitrary overrides; the driving dims and the gate laws are parametric.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from build123d import Box, Cylinder, Location, Pos, Rot, Solid

HINGE_AXIS: tuple[float, float, float] = (1.0, 0.0, 0.0)

# construction-only layout constants, tuned at defaults (mm)
_KNUCKLE_XC_BASE = (-15.0, 0.0, 15.0)   # 3 base knuckles
_KNUCKLE_XC_LID = (-7.5, 7.5)           # 2 lid knuckles, interleaved
_BORE_LEN = 33.0    # single through-bore; ends short of the outer knuckle
                    # faces -> blind ends give the pin axial retention
_PIN_LEN = 32.0
_RISER = (3.0, 3.0)         # base knuckle riser (y-depth, z-height)
_CATCH = (10.0, 1.2, 1.5, 15.5, 9.4)   # ridge w, t, h, y-center, z-center
_BRIDGE = (8.0, 3.5, 1.0, 16.1, 14.65)  # w, depth, t, y-center, z-center
_TAB = (8.0, 1.6, 8.5, 17.15, 10.9)     # w, t, drop, y-center, z-center
_NUB = (8.0, 1.6, 1.5, 15.95, 7.75)     # w, t, h, y-center, z-center
_TAB_PIVOT_Z = 15.15   # deflection tilts the snap about its top edge
_FIN = (6.35, 1.9, 0.6, 1.175, 3.65)    # stop fin: w, radial depth, thickness,
                                        # x-center, radial center from hinge


def _rot_about(center, axis, deg: float, shape):
    """Rotate `shape` by `deg` about the line through `center` along `axis`
    (the same conjugation screw_clearance uses internally)."""
    cx, cy, cz = center
    return Pos(cx, cy, cz) * Location((0, 0, 0), axis, deg) * \
        Pos(-cx, -cy, -cz) * shape


@dataclass(frozen=True)
class SnapBoxParams:
    """Driving dimensions, mm. clearance is the single design air gap at
    every mating pair. swing_deg is the working travel; stop_fin_deg places
    the travel-stop fin (contact begins a few degrees before it — verified
    free at 100, blocked by 105 at defaults). deflect_deg tilts the snap tab
    outward about its top edge for the deflected constructed state."""

    outer_l: float = 40.0
    outer_w: float = 30.0
    base_h: float = 12.0
    lid_t: float = 3.0
    wall: float = 2.0
    knuckle_d: float = 6.0
    knuckle_w: float = 6.0
    pin_d: float = 2.0
    clearance: float = 0.15
    swing_deg: float = 90.0
    stop_fin_deg: float = 108.0
    deflect_deg: float = 14.0

    def __post_init__(self):
        bad = {k: v for k, v in self.__dict__.items() if v <= 0}
        if bad:
            raise ValueError(f"all snapbox params must be > 0, got {bad}")
        if self.stop_fin_deg <= self.swing_deg + 5.0:
            raise ValueError(
                f"stop_fin_deg={self.stop_fin_deg} must exceed swing_deg="
                f"{self.swing_deg} by > 5 deg or the stop intrudes into the "
                "working travel"
            )
        if self.pin_d + 2 * self.clearance >= self.knuckle_d:
            raise ValueError(
                f"pin_d={self.pin_d} (+2*clearance) must fit inside "
                f"knuckle_d={self.knuckle_d}"
            )
        if self.wall >= min(self.outer_l, self.outer_w) / 4:
            raise ValueError(
                f"wall={self.wall} too thick for outer "
                f"{self.outer_l}x{self.outer_w}"
            )

    @property
    def hinge_center(self) -> tuple[float, float, float]:
        """Point on the hinge axis: back top edge, at the DERIVED height
        base_h + knuckle radius + clearance (lower is tangent — forbidden)."""
        return (0.0, -self.outer_w / 2,
                self.base_h + self.knuckle_d / 2 + self.clearance)

    @property
    def bore_radius(self) -> float:
        return self.pin_d / 2 + self.clearance

    @property
    def lid_z0(self) -> float:
        """Lid plate underside: clearance above the base top."""
        return self.base_h + self.clearance


def _knuckle(p: SnapBoxParams, xc: float) -> Solid:
    hc = p.hinge_center
    return Pos(xc, hc[1], hc[2]) * Rot(Y=90) * Cylinder(
        p.knuckle_d / 2, p.knuckle_w)


def _bore(p: SnapBoxParams) -> Solid:
    hc = p.hinge_center
    return Pos(0, hc[1], hc[2]) * Rot(Y=90) * Cylinder(
        p.bore_radius, _BORE_LEN)


def base(p: SnapBoxParams) -> Solid:
    """Open-top shell + 3 hinge knuckles on risers + catch ridge + travel
    stop fin. The fin is CONSTRUCTED AT stop_fin_deg by rotating a radial
    block about the hinge — the lid's plate top face meets it just past
    swing_deg (verified: free at 100 deg, blocked by 105 at defaults)."""
    hc = p.hinge_center
    b = Pos(0, 0, p.base_h / 2) * Box(p.outer_l, p.outer_w, p.base_h)
    b -= Pos(0, 0, p.wall + p.base_h / 2) * Box(
        p.outer_l - 2 * p.wall, p.outer_w - 2 * p.wall, p.base_h)
    ry, rz = _RISER
    for xc in _KNUCKLE_XC_BASE:
        b += Pos(xc, hc[1] + 1.0, p.base_h + 0.2) * Box(p.knuckle_w, ry, rz)
        b += _knuckle(p, xc)
    b -= _bore(p)
    cw, ct, ch, cy, cz = _CATCH
    b += Pos(0, cy, cz) * Box(cw, ct, ch)
    fw, fd, ft, fxc, frc = _FIN
    fin0 = Pos(fxc, hc[1] + frc, hc[2]) * Box(fw, fd, ft)
    b += _rot_about(hc, HINGE_AXIS, p.stop_fin_deg, fin0)
    return b


def lid(p: SnapBoxParams, state: Literal["relaxed", "deflected"]) -> Solid:
    """Lid in the CLOSED pose: plate (back edge held clear of the base
    knuckles) + 2 interleaved knuckles on arms + the cantilever snap
    (bridge over the front wall, hanging tab, inward nub). The deflected
    state tilts tab+nub outward by deflect_deg about the tab's top edge —
    the tilt preserves the bridge overlap so the state stays one solid."""
    if state not in ("relaxed", "deflected"):
        raise ValueError(f"state must be 'relaxed' or 'deflected', got {state!r}")
    hc = p.hinge_center
    plate_back = hc[1] + 3.0 + p.clearance      # clear of knuckle band (r=3)
    plate_w = p.outer_w / 2 - plate_back
    l = Pos(0, plate_back + plate_w / 2, p.lid_z0 + p.lid_t / 2) * Box(
        p.outer_l, plate_w, p.lid_t)
    for xc in _KNUCKLE_XC_LID:
        l += Pos(xc, hc[1] + 1.75, hc[2] - 1.15) * Box(p.knuckle_w, 4.3, 2.0)
        l += _knuckle(p, xc)
    l -= _bore(p)
    bw, bd, bt, by, bz = _BRIDGE
    bridge = Pos(0, by, bz) * Box(bw, bd, bt)
    tw, tt, td, ty, tz = _TAB
    tab = Pos(0, ty, tz) * Box(tw, tt, td)
    nw, nt, nh, ny, nz = _NUB
    nub = Pos(0, ny, nz) * Box(nw, nt, nh)
    snap = tab + nub
    if state == "deflected":
        snap = _rot_about((0, ty, _TAB_PIVOT_Z), HINGE_AXIS,
                          +p.deflect_deg, snap)
    return l + bridge + snap


def hinge_pin(p: SnapBoxParams) -> Solid:
    """Slip-fit pin: clearance-fitted in every bore, axially captured by the
    blind outer ends of the through-bore (bore len < knuckle span)."""
    hc = p.hinge_center
    return Pos(0, hc[1], hc[2]) * Rot(Y=90) * Cylinder(p.pin_d / 2, _PIN_LEN)
```

- [ ] **Step 4: Run to verify they pass, then the full suite**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_snapbox.py -v` then `uv run pytest -q`
Expected: 5 passed; full suite green (118 + 5 = 123).

- [ ] **Step 5: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add claudecad/hardware/snapbox.py tests/test_snapbox.py
git commit -m "feat: snapbox geometry — hinged base/lid states/pin, prismatic"
```

---

### Task 2: the five proofs + negative control

**Files:**
- Modify: `claudecad/hardware/snapbox.py` (gate fixtures)
- Test: `tests/test_snapbox.py` (append)

**Interfaces:**
- Consumes: Task 1's parts, `screw_clearance`/`path_clearance` (verify).
- Produces: module gate fixtures `SWING_STATIONS = 10`, `OVERTRAVEL_SPAN_DEG = 25.0`, `OVERTRAVEL_STATIONS = 11`, `OPEN_FREE_MAX_DEG = 100.0`, `BLOCKED_BY_DEG = 105.0`, `RETENTION_SPAN_DEG = 8.0`, `RETENTION_STATIONS = 9`, `NEG_CENTER_OFFSET = 0.5`, `pin_escape_distance(p) -> float`. Task 3's design gate imports them.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_snapbox.py`:

```python
def test_swing_arc_free():
    """Proof 1 (off-origin partial arc): the deflected lid sweeps the full
    swing about the hinge axis — center far from the origin — clear of
    base + pin at every station."""
    from claudecad.hardware.snapbox import SWING_STATIONS
    from claudecad.verify import screw_clearance
    p = SnapBoxParams()
    fixed = base(p) + hinge_pin(p)
    vals = screw_clearance(lid(p, "deflected"), fixed, HINGE_AXIS,
                           p.hinge_center, 0.0, p.swing_deg / 360.0,
                           SWING_STATIONS)
    assert max(vals) == 0.0


def test_travel_limit_differential():
    """Proof 2 (same-parameter differential): from the open pose, further
    opening is free through OPEN_FREE_MAX_DEG and blocked by BLOCKED_BY_DEG
    — the stop fin actually limits travel."""
    from claudecad.hardware.snapbox import (
        BLOCKED_BY_DEG, OPEN_FREE_MAX_DEG, OVERTRAVEL_SPAN_DEG,
        OVERTRAVEL_STATIONS, _rot_about)
    from claudecad.verify import screw_clearance
    p = SnapBoxParams()
    fixed = base(p) + hinge_pin(p)
    lid_open = _rot_about(p.hinge_center, HINGE_AXIS, p.swing_deg,
                          lid(p, "deflected"))
    vals = screw_clearance(lid_open, fixed, HINGE_AXIS, p.hinge_center,
                           0.0, OVERTRAVEL_SPAN_DEG / 360.0,
                           OVERTRAVEL_STATIONS)
    step = OVERTRAVEL_SPAN_DEG / (OVERTRAVEL_STATIONS - 1)
    for i, v in enumerate(vals):
        ang = p.swing_deg + i * step
        if ang <= OPEN_FREE_MAX_DEG:
            assert v == 0.0, f"blocked inside travel at {ang} deg: {v}"
        if ang >= BLOCKED_BY_DEG:
            assert v > 0.0, f"free past the stop at {ang} deg"


def test_snap_retention_differential():
    """Proof 3 (the click): over the first RETENTION_SPAN_DEG of opening,
    the RELAXED latch is blocked at some station (nub arcs into the catch)
    while the DEFLECTED latch runs free. Station 0 (at rest) is clear for
    both — the latch holds by blocking MOTION, not by touching."""
    from claudecad.hardware.snapbox import (RETENTION_SPAN_DEG,
                                            RETENTION_STATIONS)
    from claudecad.verify import screw_clearance
    p = SnapBoxParams()
    fixed = base(p) + hinge_pin(p)
    rel = screw_clearance(lid(p, "relaxed"), fixed, HINGE_AXIS,
                          p.hinge_center, 0.0, RETENTION_SPAN_DEG / 360.0,
                          RETENTION_STATIONS)
    dfl = screw_clearance(lid(p, "deflected"), fixed, HINGE_AXIS,
                          p.hinge_center, 0.0, RETENTION_SPAN_DEG / 360.0,
                          RETENTION_STATIONS)
    assert rel[0] == 0.0            # at rest: air gap, not contact
    assert max(rel) > 0.0           # opening arcs the nub into the catch
    assert max(dfl) == 0.0          # deflected: sweeps open free


def test_pin_capture():
    """Proof 4: pin blocked radially both ways and axially both ways
    (blind-ended bore); the escape distances clear the box envelope."""
    from claudecad.hardware.snapbox import pin_escape_distance
    from claudecad.verify import path_clearance
    p = SnapBoxParams()
    fixed = base(p) + lid(p, "relaxed")
    pin = hinge_pin(p)
    d = pin_escape_distance(p)
    for axis in ((0, 0, 1), (0, 1, 0), (1, 0, 0), (-1, 0, 0)):
        assert max(path_clearance(pin, fixed, axis, d, 7)) > 0.0, axis


def test_displaced_center_fails_swing():
    """Negative control (pins the off-origin claim): sweeping about a
    center displaced NEG_CENTER_OFFSET off the true hinge axis must FAIL —
    the gate detects a mis-built hinge. This control would have caught the
    original screw_clearance center bug."""
    from claudecad.hardware.snapbox import NEG_CENTER_OFFSET, SWING_STATIONS
    from claudecad.verify import screw_clearance
    p = SnapBoxParams()
    fixed = base(p) + hinge_pin(p)
    hc = p.hinge_center
    bad_center = (hc[0], hc[1] + NEG_CENTER_OFFSET, hc[2])
    vals = screw_clearance(lid(p, "deflected"), fixed, HINGE_AXIS,
                           bad_center, 0.0, p.swing_deg / 360.0,
                           SWING_STATIONS)
    assert max(vals) > 0.0
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_snapbox.py -k "swing or travel or retention or capture or displaced" -v`
Expected: FAIL with `ImportError: cannot import name 'SWING_STATIONS'` (etc.).

- [ ] **Step 3: Add the gate fixtures**

Add to `claudecad/hardware/snapbox.py`:

```python
# --- gate fixtures (one source for the design build and the tests) ---
SWING_STATIONS = 10        # stations across the working swing
OVERTRAVEL_SPAN_DEG = 25.0  # sweep past the open pose for the travel limit
OVERTRAVEL_STATIONS = 11
OPEN_FREE_MAX_DEG = 100.0  # verified free through here at defaults
BLOCKED_BY_DEG = 105.0     # verified blocked from here at defaults
RETENTION_SPAN_DEG = 8.0   # opening arc that must catch the relaxed nub
RETENTION_STATIONS = 9     # (verified: blocked 1-5 deg, max ~7.0 mm^3)
NEG_CENTER_OFFSET = 0.5    # mm hinge-axis displacement for the neg control


def pin_escape_distance(p: SnapBoxParams) -> float:
    """Translation that carries the pin clearly past the box envelope in
    any of the four blocked directions."""
    return max(p.outer_l, p.outer_w) / 2 + 5.0
```

- [ ] **Step 4: Run to verify they pass, then the full suite**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_snapbox.py -v` then `uv run pytest -q`
Expected: 10 passed in test_snapbox (5 + 5); full suite green (128). The sweep tests take a few seconds each.

- [ ] **Step 5: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add claudecad/hardware/snapbox.py tests/test_snapbox.py
git commit -m "feat: snapbox proofs — swing arc, travel limit, retention, capture"
```

---

### Task 3: `designs/snapbox`, registration, skill law

**Files:**
- Create: `designs/snapbox/__init__.py` (empty), `designs/snapbox/params.py`, `designs/snapbox/build.py`
- Modify: `tests/test_designs_import.py` (hardcoded list), `.claude/skills/cad/SKILL.md`

**Interfaces:**
- Consumes: everything from `claudecad.hardware.snapbox`, `claudecad.verify`, `tools.export`.
- Produces: `designs/snapbox/build.py::main() -> int`, runnable as `uv run python -m designs.snapbox.build`.

- [ ] **Step 1: Create the design package**

`designs/snapbox/__init__.py`: empty file.

`designs/snapbox/params.py`:

```python
"""Hinged snap-latch parts-box parameters (40 x 30 x 15)."""
from claudecad.hardware.snapbox import SnapBoxParams

P = SnapBoxParams()
```

`designs/snapbox/build.py`:

```python
"""Build, verify, and export the hinged snap enclosure.

Usage: uv run python -m designs.snapbox.build
GLB always; STEP only if the gate passes (exit 1 otherwise). The gate: parts
clean, shipped-pose crisp-0 with real air gaps, the off-origin swing arc,
THE box properties — the travel-limit differential (free within travel,
blocked past the stop, same angular parameter) and the snap retention
differential (relaxed blocked / deflected free) — pin capture, and the
displaced-center negative control. Clearance mechanism: every boolean
reads exactly 0 at free stations.
"""
import sys

from claudecad.hardware.snapbox import (
    BLOCKED_BY_DEG, HINGE_AXIS, NEG_CENTER_OFFSET, OPEN_FREE_MAX_DEG,
    OVERTRAVEL_SPAN_DEG, OVERTRAVEL_STATIONS, RETENTION_SPAN_DEG,
    RETENTION_STATIONS, SWING_STATIONS, _rot_about, base, hinge_pin, lid,
    pin_escape_distance,
)
from claudecad.verify import (
    check_solid, clearance, intersection_volume, path_clearance,
    screw_clearance,
)
from tools.export import export_design, export_glb

from .params import P


def main() -> int:
    b = base(P)
    l_relaxed = lid(P, "relaxed")
    l_deflected = lid(P, "deflected")
    pin = hinge_pin(P)
    parts = {"snapbox_base": b, "snapbox_lid": l_relaxed, "snapbox_pin": pin}

    export_glb(parts, "out/glb/snapbox.glb",
               linear_deflection=0.01, angular_deflection=0.1)

    ok = True

    # 1) parts clean (deflected lid is a load-bearing proof state)
    for name, s in [*parts.items(), ("snapbox_lid_deflected", l_deflected)]:
        r = check_solid(s)
        print(f"{name}: valid={r.is_valid} manifold={r.is_manifold} "
              f"pieces={r.piece_count} volume={r.volume:.1f}")
        ok = ok and r.ok

    # 2) shipped pose: crisp 0, real air gaps
    worst = max(intersection_volume(b, l_relaxed),
                intersection_volume(b, pin),
                intersection_volume(l_relaxed, pin))
    g_pin = clearance(pin, b)
    print(f"shipped pose: worst pairwise iv {worst:.6f} (==0), "
          f"pin-bore gap {g_pin:.4f} (== clearance {P.clearance})")
    ok = ok and worst == 0.0 and abs(g_pin - P.clearance) < 1e-6

    # 3) swing arc (off-origin center — the hinge axis, not the origin)
    fixed = b + pin
    sw = screw_clearance(l_deflected, fixed, HINGE_AXIS, P.hinge_center,
                         0.0, P.swing_deg / 360.0, SWING_STATIONS)
    print(f"swing 0..{P.swing_deg:.0f} deg about {P.hinge_center}: "
          f"max iv {max(sw):.6f} (==0)")
    ok = ok and max(sw) == 0.0

    # 4) travel-limit differential (same-parameter free/blocked)
    l_open = _rot_about(P.hinge_center, HINGE_AXIS, P.swing_deg, l_deflected)
    ot = screw_clearance(l_open, fixed, HINGE_AXIS, P.hinge_center,
                         0.0, OVERTRAVEL_SPAN_DEG / 360.0,
                         OVERTRAVEL_STATIONS)
    step = OVERTRAVEL_SPAN_DEG / (OVERTRAVEL_STATIONS - 1)
    free_ok = all(v == 0.0 for i, v in enumerate(ot)
                  if P.swing_deg + i * step <= OPEN_FREE_MAX_DEG)
    blocked_ok = all(v > 0.0 for i, v in enumerate(ot)
                     if P.swing_deg + i * step >= BLOCKED_BY_DEG)
    print(f"travel limit: free through {OPEN_FREE_MAX_DEG} deg "
          f"({free_ok}), blocked from {BLOCKED_BY_DEG} deg ({blocked_ok}), "
          f"max {max(ot):.3f}")
    ok = ok and free_ok and blocked_ok

    # 5) snap retention differential
    rel = screw_clearance(l_relaxed, fixed, HINGE_AXIS, P.hinge_center,
                          0.0, RETENTION_SPAN_DEG / 360.0,
                          RETENTION_STATIONS)
    dfl = screw_clearance(l_deflected, fixed, HINGE_AXIS, P.hinge_center,
                          0.0, RETENTION_SPAN_DEG / 360.0,
                          RETENTION_STATIONS)
    print(f"retention over {RETENTION_SPAN_DEG} deg: relaxed max "
          f"{max(rel):.3f} (>0, rest {rel[0]:.3f}==0) vs deflected max "
          f"{max(dfl):.6f} (==0)")
    ok = ok and rel[0] == 0.0 and max(rel) > 0.0 and max(dfl) == 0.0

    # 6) pin capture (blind-ended bore)
    d = pin_escape_distance(P)
    caps = [max(path_clearance(pin, b + l_relaxed, ax, d, 7))
            for ax in ((0, 0, 1), (0, 1, 0), (1, 0, 0), (-1, 0, 0))]
    print(f"pin capture +Z/+Y/+X/-X: "
          f"{' / '.join(f'{c:.2f}' for c in caps)} (all >0)")
    ok = ok and all(c > 0.0 for c in caps)

    # 7) negative control: displaced hinge center must fail the swing
    hc = P.hinge_center
    bad = screw_clearance(l_deflected, fixed, HINGE_AXIS,
                          (hc[0], hc[1] + NEG_CENTER_OFFSET, hc[2]),
                          0.0, P.swing_deg / 360.0, SWING_STATIONS)
    print(f"negative control (center +{NEG_CENTER_OFFSET} y): max "
          f"{max(bad):.3f} (>0 — the gate detects a mis-built hinge)")
    ok = ok and max(bad) > 0.0

    if not ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1
    export_design(parts, "out/step/snapbox.step", assembly_label="snapbox")
    print("exported out/step/snapbox.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the design gate**

Run: `cd /Users/mike/code/claudeCAD && uv run python -m designs.snapbox.build`
Expected: 4 clean parts, shipped worst iv 0.000000 / pin gap 0.1500, swing max 0.000000, travel limit free=True blocked=True (max ≈5.4), retention relaxed max ≈7.0 vs deflected 0.000000, pin capture ≈79.7/79.6/4.7/4.7, negative control ≈21.2, `exported out/step/snapbox.step`, exit 0.

- [ ] **Step 3: Register in the designs-import smoke test**

In `tests/test_designs_import.py`, add `designs.snapbox.build` and `designs.snapbox.params` entries following exactly how `designs.bearing_608` is listed (hardcoded list — no auto-discovery).

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_designs_import.py -v`
Expected: pass with the two new entries.

- [ ] **Step 4: Add the hinged-travel law to the /cad skill**

In `.claude/skills/cad/SKILL.md`, beside the multi-body/rolling-set entry in the verification-laws section, add:

> - **Hinged / limited-travel joint** (`hardware/snapbox`): gated by partial-arc
>   sweeps about the hinge axis — `screw_clearance` with `lead=0` and `center`
>   ON the hinge axis (off-origin centers are supported and must be used;
>   never re-origin the model to dodge them). Travel limits are proven by a
>   SAME-PARAMETER differential: free within travel, blocked past the stop,
>   along one angular sweep. Snap retention is the two-state differential at
>   the closed pose (relaxed blocked / deflected free — blocking MOTION, not
>   touching). Every hinged design carries a displaced-center negative
>   control: sweeping about a center off the true axis must fail, proving the
>   gate detects a mis-built hinge.

- [ ] **Step 5: Run the full suite, commit**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest -q`
Expected: all pass (130).

```bash
cd /Users/mike/code/claudeCAD
git add designs/snapbox tests/test_designs_import.py .claude/skills/cad/SKILL.md
git commit -m "feat: designs/snapbox — off-origin swing gates design + skill law"
```

- [ ] **Step 6: Render and judge**

Run: `cd /Users/mike/code/claudeCAD && uv run python tools/render.py out/glb/snapbox.glb --outdir out/renders/snapbox`
Judge `out/renders/snapbox/*.png` against a real hinged snap box (parts organizer style): closed lid seated with a visible gap line, knuckle hinge along the back, latch tab over the front catch. Tooling lens: geometry defects matter; cosmetics don't. Mike is final judge in Plasticity via `out/step/snapbox.step`.

---

## Notes for the implementer

- **Crisp-0 discipline:** every free station reads exactly 0.0. A small nonzero at a free station is a geometry bug (something touching or intruding) — fix the geometry, never tolerate it.
- **The stop-fin construction is rotation-derived:** the fin is a radial block rotated to `stop_fin_deg` about the hinge with `_rot_about`. Do not replace it with a hand-placed box — the spike showed hand-placed stops end up inside the plate's swept sector (blocking from ~50°) because the plate is a slab whose whole angular sector sweeps, not just its edge arc.
- **The hinge height is derived** (`base_h + knuckle_d/2 + clearance`); the spike caught an exact knuckle-to-wall tangency at anything less. Do not "simplify" it to a literal.
- **Deflection tilts about the tab TOP** (`_TAB_PIVOT_Z`) with POSITIVE `deflect_deg` (bottom swings outward, +Y). The spike's first round had the sign backwards — the deflected tab dove into the wall (35 mm³ at station 0). If station 0 of the deflected swing is nonzero, check this sign first.
- **Blind bore ends are the pin's axial retention:** `_BORE_LEN` (33) < outer knuckle span (36) leaves solid ends; `_PIN_LEN` (32) < `_BORE_LEN`. Lengthening either past the other breaks proof 4's axial legs.
