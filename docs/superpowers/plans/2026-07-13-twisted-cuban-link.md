# Twisted Cuban Link Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the cuban bracelet benchmark with twisted links (ruled-loft construction) and chain-level diamond-cut, closing the v1 density/V-groove gap.

**Architecture:** New exact twisted-centerline map in `claudecad/core/twisted.py`; `cuban_link` in links.py builds the solid as a ruled loft through analytic frames; chains.py gains a params-dispatch and a shared placement helper; new `finishing.py` grinds the assembled chain flat; verify.py gains `piece_count` and `interlock_depth`. The benchmark switches to spike-verified defaults.

**Tech Stack:** Same as v1 — Python 3.14 (uv), build123d 0.11.x, numpy, pytest, Blender 4.5 headless.

**Spec:** `docs/superpowers/specs/2026-07-13-twisted-cuban-link-design.md` (amended per spike gate)

## Global Constraints

- Project root `/Users/mike/code/claudeCAD`; all commands run from there (`uv run ...`).
- All dimensions mm. Library modules stay pure (no I/O); `tools/` only touches disk.
- Never weaken a verification check. Never export STEP that fails verification.
- **Construction law (spike-established; amended during Task 5 — see the spec):** twisted closed tubes are built ONLY as ruled lofts (`ruled=True`) through analytically computed frames, assembled as TWO overlapping half-loop lofts fused (a single closed loft buries coincident seam cap discs that break downstream booleans — Task 5 diagnosis). Forbidden, all gauntlet-proven broken for twisted closed paths: `sweep()` in any frame mode (corrected = unorientable seam; Frenet = self-intersecting surface), `ruled=False` lofts (boolean-pathological), single closed lofts with first==last section, Shell/Solid reassembly of loft faces, fusing pipes at coincident faces, `Edge.trim()` on sweep spines.
- `is_valid` is necessary but NOT sufficient — boolean-robustness is proven only by cut/intersection behavior (that is what the tests assert).
- Verified parameter facts (2026-07-13 spike, 176 arc-placed probe combos + construction gauntlet):
  - ruled loft passes the full gauntlet for twist ∈ [20, 60], n_sections=144, vol_err ≤ 0.05%.
  - Passing bracelet config: link 20×14×4.1, twist 60, pitch 10, tilt 20 — all pairs intersection 0, neighbors Lk=1, lk02=0 (interlock depth 1). Frontier: tilt 15 grazes (iv01=0.065), twist 45/tilt 20 grazes (iv01=0.015); slimmer proportions are uniformly worse.
  - Real-cuban pitch ≈ 0.49×length (photo-calibrated in Task 6); density below pitch≈9.5 structurally collides at the 2-apart pair for every proportion tried — do not chase it.
- Escape hatch when a check fails during the benchmark: raise tilt 20→25 first, then lower twist toward 45, re-running the full gate each step; record final numbers in params.py comments. Never loosen a check.
- Commit after every task with the message given in the task.

---

### Task 1: Exact twisted centerline map

**Files:**
- Create: `claudecad/core/twisted.py`
- Test: `tests/test_twisted.py`

**Interfaces:**
- Consumes: `stadium_wire`, `discretize` from `claudecad.core.centerline` (tests only).
- Produces:
  - `twisted_stadium_frame(length, width, wire_d, twist_deg, u) -> tuple[Vector, Vector, Vector]` — exact (point, unit tangent, section x_dir) at arc-parameter u ∈ [0,1) of the twisted stadium centerline (map `(x,y,0) -> (x, y·cos(kx), y·sin(kx))`, `k = radians(twist)/(2·(h+r))`, long axis X, centered at origin).
  - `twisted_centerline_points(length, width, wire_d, twist_deg, n) -> np.ndarray` — (n,3) exact samples (endpoint-exclusive).

- [ ] **Step 1: Write the failing tests**

`tests/test_twisted.py`:
```python
import math

import numpy as np
import pytest

from claudecad.core.centerline import discretize, stadium_wire
from claudecad.core.twisted import twisted_centerline_points, twisted_stadium_frame


def test_zero_twist_matches_planar_stadium():
    """twist=0 must reproduce the planar stadium centerline exactly."""
    L, W, D = 20.0, 14.0, 4.1
    pts = twisted_centerline_points(L, W, D, 0.0, 256)
    wire_pts = discretize(stadium_wire(L - W, (W - D) / 2), 256)
    # same closed curve; sampling may start at a different point, so compare
    # as sets via nearest-neighbour distance
    for p in pts[:: 16]:
        d = np.linalg.norm(wire_pts - p, axis=1).min()
        assert d < 0.02, f"point {p} is {d} from the planar stadium"


def test_frame_properties():
    L, W, D, T = 20.0, 14.0, 4.1, 45.0
    for u in (0.0, 0.13, 0.35, 0.5, 0.77, 0.99):
        p, t, xd = twisted_stadium_frame(L, W, D, T, u)
        assert abs(t.length - 1.0) < 1e-9          # unit tangent
        assert abs(xd.length - 1.0) < 1e-9         # unit x_dir
        assert abs(t.dot(xd)) < 1e-9               # orthogonal frame


def test_extents_and_closure():
    L, W, D, T = 20.0, 14.0, 4.1, 60.0
    pts = twisted_centerline_points(L, W, D, T, 512)
    xmax = (L - D) / 2
    assert pts[:, 0].max() == pytest.approx(xmax, abs=1e-6)
    assert pts[:, 0].min() == pytest.approx(-xmax, abs=1e-6)
    # closure: first and last samples are one step apart, not far apart
    step = np.linalg.norm(pts[1] - pts[0])
    assert np.linalg.norm(pts[0] - pts[-1]) < 3 * step


def test_twist_rotates_material_out_of_plane():
    """At x=0 the twist is zero (point stays in-plane); at the end of the
    top straight (x = h) the material is clearly rotated out of plane."""
    L, W, D, T = 20.0, 14.0, 4.1, 60.0
    pts = twisted_centerline_points(L, W, D, T, 1024)
    r, h = (W - D) / 2, (L - W) / 2
    mid_top = pts[np.argmin(np.abs(pts[:, 0]))]      # x ~ 0, pre-twist (0, +-r, 0)
    assert abs(mid_top[2]) < 0.05                    # still in-plane at the center
    assert abs(abs(mid_top[1]) - r) < 0.05
    near_end = pts[np.argmin(np.abs(pts[:, 0] - h))]  # straight/arc junction
    phi = math.atan2(near_end[2], near_end[1])
    # expected twist at x=h: T/2 * h/(h+r) ~ 11.3 deg for these dims
    assert phi > math.radians(5)


def test_degenerate_params_rejected():
    with pytest.raises(ValueError):
        twisted_stadium_frame(10.0, 14.0, 4.1, 45.0, 0.0)   # length <= width
    with pytest.raises(ValueError):
        twisted_centerline_points(20.0, 14.0, 0.0, 45.0, 64)  # wire_d <= 0
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_twisted.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'claudecad.core.twisted'`

- [ ] **Step 3: Implement**

`claudecad/core/twisted.py`:
```python
"""Exact twisted-stadium centerline: the cuban link's spine.

Map: planar stadium point (x, y, 0) -> (x, y cos(kx), y sin(kx)) with
k = radians(twist_deg) / (2 * x_max), x_max = h + r — a linear twist ramp
about the long (X) axis reaching +-twist_deg/2 at the ends. Everything here
is closed-form; no geometry kernel calls.
"""
from __future__ import annotations

import math

import numpy as np
from build123d import Vector


def _params(length: float, width: float, wire_d: float):
    if not (0 < wire_d < width < length):
        raise ValueError(
            f"need 0 < wire_d < width < length, got "
            f"wire_d={wire_d} width={width} length={length}"
        )
    r = (width - wire_d) / 2
    h = (length - width) / 2
    return r, h


def twisted_stadium_frame(
    length: float, width: float, wire_d: float, twist_deg: float, u: float
) -> tuple[Vector, Vector, Vector]:
    """Exact (point, unit tangent, section x_dir) at arc-parameter u in [0,1).

    x_dir is derived from the twisted vertical (0, -sin(kx), cos(kx)) —
    smooth and periodic around the loop, so consecutive loft sections
    never flip orientation.
    """
    r, h = _params(length, width, wire_d)
    x_max = h + r
    k = math.radians(twist_deg) / (2 * x_max)
    seg = [2 * h, math.pi * r, 2 * h, math.pi * r]
    total = sum(seg)
    d = (u % 1.0) * total
    if d < seg[0]:                                   # top straight
        x, y = -h + d, r
        dx, dy = 1.0, 0.0
    elif d < seg[0] + seg[1]:                        # right arc
        a = (d - seg[0]) / r
        x, y = h + r * math.sin(a), r * math.cos(a)
        dx, dy = math.cos(a), -math.sin(a)
    elif d < seg[0] + seg[1] + seg[2]:               # bottom straight
        x, y = h - (d - seg[0] - seg[1]), -r
        dx, dy = -1.0, 0.0
    else:                                            # left arc
        a = (d - seg[0] - seg[1] - seg[2]) / r
        x, y = -h - r * math.sin(a), -r * math.cos(a)
        dx, dy = -math.cos(a), math.sin(a)
    phi = k * x
    c, s = math.cos(phi), math.sin(phi)
    p = Vector(x, y * c, y * s)
    dphi = k * dx
    t = Vector(dx, dy * c - y * s * dphi, dy * s + y * c * dphi).normalized()
    up = Vector(0, -s, c)
    x_dir = t.cross(up).normalized()
    return p, t, x_dir


def twisted_centerline_points(
    length: float, width: float, wire_d: float, twist_deg: float, n: int
) -> np.ndarray:
    """(n,3) exact samples of the twisted centerline (endpoint-exclusive)."""
    return np.array(
        [
            tuple(twisted_stadium_frame(length, width, wire_d, twist_deg, i / n)[0])
            for i in range(n)
        ]
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_twisted.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add claudecad/core/twisted.py tests/test_twisted.py
git commit -m "feat: exact twisted-stadium centerline map"
```

---

### Task 2: Verification — piece_count and interlock_depth

**Files:**
- Modify: `claudecad/verify.py`
- Test: `tests/test_verify.py` (append)

**Interfaces:**
- Consumes: existing `SolidReport`, `check_solid`, `check_chain`, `PairCheck`.
- Produces:
  - `SolidReport` gains field `piece_count: int` (after `volume`); `ok` additionally requires `piece_count == 1`. `check_solid` fills it with `len(shape.solids())`.
  - `check_chain(items, closed=False, interlock_depth=1)` — pairs with cyclic index distance ≤ interlock_depth must be linked; farther pairs unlinked; all pairs zero intersection. `interlock_depth=1` reproduces current behavior bit-for-bit.
  - `PairCheck` gains field `adjacent_distance: int` (cyclic index distance; 0 replaces the old bool semantics — keep the existing `adjacent: bool` field, now meaning "within interlock depth").

- [ ] **Step 1: Write the failing tests (append to `tests/test_verify.py`)**

```python
from build123d import Compound


def test_solid_report_piece_count():
    single = Torus(10, 1.5)
    assert check_solid(single).piece_count == 1
    assert check_solid(single).ok
    split = Compound(children=[Box(5, 5, 5), Pos(50, 0, 0) * Box(5, 5, 5)])
    r = check_solid(split)
    assert r.piece_count == 2
    assert not r.ok


def _ring_chain(n, spacing):
    """n unlinked tori in a row — a topology fixture for depth classification."""
    return [
        (Pos(spacing * i, 0, 0) * Torus(10, 1.5), 10 * _circle() + (spacing * i, 0, 0))
        for i in range(n)
    ]


def test_interlock_depth_default_matches_old_behavior():
    """depth=1 on the Hopf pair passes exactly as before."""
    report = check_chain(_hopf_tori())
    assert report.ok, report.failures()


def test_interlock_depth_2_requires_second_neighbor_linked():
    """With depth=2, an unlinked (0,2) pair becomes a failure; with depth=1
    the same geometry passes the (0,2) check (must be unlinked) and fails
    only the adjacent pairs (unlinked neighbors)."""
    items = _ring_chain(3, 50)
    d1 = check_chain(items, interlock_depth=1)
    d2 = check_chain(items, interlock_depth=2)
    d1_msgs = [f for f in d1.failures() if "not interlocked" in f]
    d2_msgs = [f for f in d2.failures() if "not interlocked" in f]
    assert len(d1_msgs) == 2          # (0,1), (1,2)
    assert len(d2_msgs) == 3          # + (0,2) now required linked


def test_interlock_depth_validation():
    with pytest.raises(ValueError):
        check_chain(_hopf_tori(), interlock_depth=0)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_verify.py -v`
Expected: existing tests pass; new ones FAIL (`piece_count` attribute missing / unexpected keyword `interlock_depth`)

- [ ] **Step 3: Implement**

In `claudecad/verify.py`, replace `SolidReport` and `check_solid` with:

```python
@dataclass(frozen=True)
class SolidReport:
    is_valid: bool
    is_manifold: bool
    volume: float
    piece_count: int = 1

    @property
    def ok(self) -> bool:
        return (
            self.is_valid
            and self.is_manifold
            and self.volume > 0.0
            and self.piece_count == 1
        )


def check_solid(shape) -> SolidReport:
    return SolidReport(
        shape.is_valid, shape.is_manifold, shape.volume, len(shape.solids())
    )
```

Replace `check_chain` with (and update its `ChainReport.failures` caller — the message set is unchanged):

```python
def check_chain(items, closed: bool = False, interlock_depth: int = 1) -> ChainReport:
    """Verify a chain of (solid, centerline_points) pairs.

    Pairs within `interlock_depth` cyclic index distance must interlock
    (|Lk| >= 1); pairs beyond must be unlinked; ALL pairs must have zero
    intersection. Dense cuban chains thread depth 2; classic curb chains
    are depth 1 (the default, which preserves the original behavior).
    Disjoint bounding boxes prove zero intersection (a separating
    axis-aligned plane exists), so the boolean is skipped there.
    """
    if interlock_depth < 1:
        raise ValueError(f"need interlock_depth >= 1, got {interlock_depth}")
    items = list(items)
    n = len(items)
    solids = [check_solid(s) for s, _ in items]
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            dist = j - i
            if closed and n > 2:
                dist = min(dist, n - (j - i))
            si, ci = items[i]
            sj, cj = items[j]
            inter = 0.0 if _bboxes_disjoint(si, sj) else intersection_volume(si, sj)
            pairs.append(
                PairCheck(i, j, dist <= interlock_depth, inter, linking_number(ci, cj))
            )
    return ChainReport(solids, pairs)
```

(Note: the `adjacent` field of `PairCheck` keeps its name; its meaning is now "within interlock depth". Do not rename the field — the report messages and existing tests use it via `PairCheck.ok` only.)

Also extend `ChainReport.failures` solid message to include pieces:

```python
                msgs.append(
                    f"link {i}: invalid solid (valid={s.is_valid} "
                    f"manifold={s.is_manifold} volume={s.volume:.3f} "
                    f"pieces={s.piece_count})"
                )
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_verify.py -v`
Expected: all pass (existing 10 + 4 new)

- [ ] **Step 5: Run the whole suite** (chains/links tests construct SolidReports indirectly)

Run: `uv run pytest -q`
Expected: all pass, no regressions

- [ ] **Step 6: Commit**

```bash
git add claudecad/verify.py tests/test_verify.py
git commit -m "feat: piece-count check and interlock_depth in chain verification"
```

---

### Task 3: cuban_link component (ruled loft)

**Files:**
- Modify: `claudecad/jewelry/links.py`
- Test: `tests/test_links.py` (append)

**Interfaces:**
- Consumes: `twisted_stadium_frame`, `twisted_centerline_points` (Task 1); existing `LinkParams` patterns.
- Produces:
  - `CubanLinkParams` frozen dataclass: `length=20.0`, `width=14.0`, `wire_d=4.1`, `twist_deg=60.0`, `n_sections=144`, `n_centerline=256`. Validates `0 < wire_d < width < length`, `20.0 <= twist_deg <= 60.0` (spike-verified loft range), `n_sections >= 32`, `n_centerline >= 3`. ValueErrors carry the values.
  - `cuban_link(p: CubanLinkParams) -> tuple[Solid, Wire]` — ruled-loft solid + a measurement-only periodic spline Wire through the exact centerline samples (documented: for discretization/transform only, NEVER for sweeping).

- [ ] **Step 1: Write the failing tests (append to `tests/test_links.py`)**

```python
import numpy as np
from build123d import Box, Pos

from claudecad.core.twisted import twisted_centerline_points
from claudecad.jewelry.links import CubanLinkParams, cuban_link


def test_cuban_link_valid_single_solid():
    solid, wire = cuban_link(CubanLinkParams())
    r = check_solid(solid)
    assert r.ok, r


def test_cuban_link_volume_matches_tube_theorem():
    p = CubanLinkParams()
    solid, _ = cuban_link(p)
    pts = twisted_centerline_points(p.length, p.width, p.wire_d, p.twist_deg, 4000)
    clen = float(np.linalg.norm(np.roll(pts, -1, axis=0) - pts, axis=1).sum())
    expected = math.pi * (p.wire_d / 2) ** 2 * clen
    assert solid.volume == pytest.approx(expected, rel=5e-3)  # spike: <=0.05%


def test_cuban_link_is_boolean_robust_to_slab_cut():
    """The construction law's acid test: a mid-tube slab cut must produce a
    valid, correctly-trimmed result (this is what every forbidden
    construction failed)."""
    solid, _ = cuban_link(CubanLinkParams())
    bb = solid.bounding_box()
    cz = 2.0
    slab = Box((bb.max.X - bb.min.X) + 4, (bb.max.Y - bb.min.Y) + 4, 2 * cz)
    cut = solid & slab
    cbb = cut.bounding_box()
    assert cut.is_valid
    assert cbb.max.Z - cbb.min.Z == pytest.approx(2 * cz, abs=0.01)
    assert 0 < cut.volume < solid.volume


def test_cuban_link_measurement_wire_matches_map():
    p = CubanLinkParams()
    _, wire = cuban_link(p)
    pts = twisted_centerline_points(p.length, p.width, p.wire_d, p.twist_deg, 64)
    from claudecad.core.centerline import discretize
    wpts = discretize(wire, 256)
    for q in pts[::8]:
        assert np.linalg.norm(wpts - q, axis=1).min() < 0.05


def test_cuban_link_params_validation():
    with pytest.raises(ValueError):
        CubanLinkParams(twist_deg=10.0)     # below verified loft range
    with pytest.raises(ValueError):
        CubanLinkParams(twist_deg=75.0)     # above verified loft range
    with pytest.raises(ValueError):
        CubanLinkParams(n_sections=16)
    with pytest.raises(ValueError):
        CubanLinkParams(wire_d=0.0)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_links.py -v`
Expected: existing 4 pass; new FAIL with ImportError

- [ ] **Step 3: Implement (append to `claudecad/jewelry/links.py`)**

```python
from build123d import Circle, Edge, Plane, loft

from claudecad.core.twisted import twisted_centerline_points, twisted_stadium_frame


@dataclass(frozen=True)
class CubanLinkParams:
    """Twisted cuban link, outer dimensions (mm), long axis X.

    twist_deg is limited to [20, 60]: the spike-verified range where the
    ruled-loft construction is boolean-robust (below 20 was only ever
    verified for the PLANAR curb_link; above 60 is unverified).
    """

    length: float = 20.0
    width: float = 14.0
    wire_d: float = 4.1
    twist_deg: float = 60.0
    n_sections: int = 144
    n_centerline: int = 256

    def __post_init__(self):
        if not (0 < self.wire_d < self.width < self.length):
            raise ValueError(
                f"need 0 < wire_d < width < length, got "
                f"wire_d={self.wire_d} width={self.width} length={self.length}"
            )
        if not (20.0 <= self.twist_deg <= 60.0):
            raise ValueError(
                f"need 20 <= twist_deg <= 60 (verified loft range), "
                f"got {self.twist_deg}"
            )
        if self.n_sections < 32:
            raise ValueError(f"need n_sections >= 32, got {self.n_sections}")
        if self.n_centerline < 3:
            raise ValueError(f"need n_centerline >= 3, got {self.n_centerline}")


def cuban_link(p: CubanLinkParams) -> tuple[Solid, Wire]:
    """Twisted link solid (ruled loft — see the construction law in the
    2026-07-13 spec) plus a measurement-only centerline Wire.

    The Wire is a periodic spline through exact map samples; it exists so
    placement transforms and discretization work identically to curb_link.
    It must NEVER be used as a sweep path (that construction is broken in
    OCCT for twisted closed curves; the loft is the only verified builder).
    """
    sections = []
    for i in range(p.n_sections + 1):                # first == last plane
        pt, t, xd = twisted_stadium_frame(
            p.length, p.width, p.wire_d, p.twist_deg, i / p.n_sections
        )
        sections.append(Plane(origin=pt, z_dir=t, x_dir=xd) * Circle(p.wire_d / 2))
    solid = loft(sections, ruled=True)

    pts = twisted_centerline_points(
        p.length, p.width, p.wire_d, p.twist_deg, p.n_centerline
    )
    wire = Wire([Edge.make_spline([tuple(q) for q in pts], periodic=True)])
    return solid, wire
```

Also extend the module imports at the top as needed (`Solid`, `Wire` are already imported; add `Edge`, `Plane`, `Circle`, `loft` if missing — keep one import block).

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_links.py -v`
Expected: 9 passed (4 existing + 5 new). The loft builds take a few seconds each.

- [ ] **Step 5: Commit**

```bash
git add claudecad/jewelry/links.py tests/test_links.py
git commit -m "feat: twisted cuban link via ruled loft"
```

---

### Task 4: Chain dispatch and placement helper

**Files:**
- Modify: `claudecad/jewelry/chains.py`
- Test: `tests/test_chains.py` (append)

**Interfaces:**
- Consumes: `CubanLinkParams`, `cuban_link` (Task 3); existing `LinkParams`, `curb_link`, `PlacedLink`, `discretize`.
- Produces:
  - `build_link(params: LinkParams | CubanLinkParams) -> tuple[Solid, Wire]` — single dispatch point (type-based).
  - `ChainParams.link: LinkParams | CubanLinkParams` (annotation widened; no behavior change).
  - Internal `_place_links(base_solid, base_wire, locs, n_centerline) -> list[PlacedLink]` — shared by `straight_chain` and `closed_loop` (the duplication flagged in the v1 final review). Public signatures of both functions unchanged.

- [ ] **Step 1: Write the failing tests (append to `tests/test_chains.py`)**

```python
from claudecad.jewelry.chains import build_link
from claudecad.jewelry.links import CubanLinkParams, LinkParams, curb_link


def test_build_link_dispatches_by_params_type():
    s1, w1 = build_link(LinkParams())
    ref, _ = curb_link(LinkParams())
    assert s1.volume == pytest.approx(ref.volume, rel=1e-9)
    s2, w2 = build_link(CubanLinkParams())
    assert s2.is_valid
    # a twisted link is non-planar: its z-extent exceeds the wire diameter
    bb = s2.bounding_box()
    assert bb.max.Z - bb.min.Z > CubanLinkParams().wire_d + 1.0


def test_straight_chain_accepts_cuban_params():
    p = ChainParams(link=CubanLinkParams(), tilt_deg=20.0, pitch=10.0)
    links = straight_chain(p, count=2)
    assert len(links) == 2
    report = check_chain(links)
    assert report.ok, report.summary()
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_chains.py -v`
Expected: existing pass; new FAIL with ImportError on `build_link`

- [ ] **Step 3: Implement**

In `claudecad/jewelry/chains.py`:

```python
from claudecad.jewelry.links import (
    CubanLinkParams, LinkParams, cuban_link, curb_link,
)


def build_link(params: LinkParams | CubanLinkParams) -> tuple[Solid, Wire]:
    """Single dispatch point from link parameters to (solid, centerline wire)."""
    if isinstance(params, CubanLinkParams):
        return cuban_link(params)
    if isinstance(params, LinkParams):
        return curb_link(params)
    raise TypeError(f"unknown link params type: {type(params).__name__}")


def _place_links(base_solid, base_wire, locs, n_centerline) -> list[PlacedLink]:
    return [
        PlacedLink(loc * base_solid, discretize(loc * base_wire, n_centerline))
        for loc in locs
    ]
```

Widen the annotation on `ChainParams.link` to `LinkParams | CubanLinkParams` and rewrite the two chain builders to use the helpers (bodies only; signatures unchanged):

```python
def straight_chain(p: ChainParams, count: int) -> list[PlacedLink]:
    """Chain along +X: link i at x=i*pitch, tilted about X, alternating sign."""
    base_solid, base_wire = build_link(p.link)
    locs = [
        Pos(i * p.pitch, 0, 0) * Rot(X=(p.tilt_deg if i % 2 == 0 else -p.tilt_deg))
        for i in range(count)
    ]
    return _place_links(base_solid, base_wire, locs, p.link.n_centerline)
```

and in `closed_loop`, replace the build/loop body equivalently:

```python
    base_solid, base_wire = build_link(p.link)
    locs = [
        Rot(Z=360 * i / n)
        * Pos(0, -radius, 0)
        * Rot(X=(p.tilt_deg if i % 2 == 0 else -p.tilt_deg))
        for i in range(n)
    ]
    placed = _place_links(base_solid, base_wire, locs, p.link.n_centerline)
    return placed, LoopInfo(count=n, radius=radius, circumference=n * p.pitch)
```

(`Wire` needs importing for the annotation; keep `curb_link` import — it moved into `build_link`.)

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_chains.py -v`
Expected: all pass (8 existing + 2 new; the cuban 2-link chain check takes ~1 min)

- [ ] **Step 5: Commit**

```bash
git add claudecad/jewelry/chains.py tests/test_chains.py
git commit -m "feat: link-params dispatch and shared placement in chains"
```

---

### Task 5: diamond_cut finishing op

**Files:**
- Create: `claudecad/jewelry/finishing.py`
- Test: `tests/test_finishing.py`

**Interfaces:**
- Consumes: `PlacedLink` (chains), `check_chain` (verify, in tests).
- Produces:
  - `diamond_cut(links: list[PlacedLink], cut_z: float) -> list[PlacedLink]` — intersects every solid with one shared slab `|z| <= cut_z` sized to the whole chain's XY footprint (+margin), positioned at the chain's XY center. Centerlines pass through untouched. Raises ValueError (with values) if `cut_z <= 0`, or if the cut would be a no-op (chain z-half-extent ≤ cut_z), or if any cut result is empty.

- [ ] **Step 1: Write the failing tests**

`tests/test_finishing.py`:
```python
import pytest

from claudecad.jewelry.chains import ChainParams, straight_chain
from claudecad.jewelry.finishing import diamond_cut
from claudecad.jewelry.links import CubanLinkParams
from claudecad.verify import check_chain


def _chain():
    p = ChainParams(link=CubanLinkParams(), tilt_deg=20.0, pitch=10.0)
    return straight_chain(p, count=2)


def test_diamond_cut_flattens_to_exact_height():
    links = _chain()
    cut = diamond_cut(links, cut_z=2.8)
    for pl in cut:
        bb = pl.solid.bounding_box()
        assert bb.max.Z - bb.min.Z == pytest.approx(2 * 2.8, abs=0.01)
        assert pl.solid.is_valid
    # centerlines untouched
    for before, after in zip(links, cut):
        assert (before.centerline == after.centerline).all()
    # still a passing chain after the cut
    report = check_chain(cut)
    assert report.ok, report.summary()


def test_diamond_cut_severing_is_caught_by_chain_report():
    links = _chain()
    cut = diamond_cut(links, cut_z=0.6)     # slices through the whole wire
    report = check_chain(cut)
    assert not report.ok
    assert any("pieces=" in f for f in report.failures())


def test_diamond_cut_rejects_bad_cut_z():
    links = _chain()
    with pytest.raises(ValueError):
        diamond_cut(links, cut_z=0.0)
    with pytest.raises(ValueError):
        diamond_cut(links, cut_z=50.0)      # taller than the chain: no-op
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_finishing.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'claudecad.jewelry.finishing'`

- [ ] **Step 3: Implement**

`claudecad/jewelry/finishing.py`:
```python
"""Chain-level finishing: operations on assembled (placed) links.

diamond_cut mirrors real cuban manufacturing: the assembled chain is ground
flat top and bottom. One shared slab guarantees a uniform world-space cut.
"""
from __future__ import annotations

from build123d import Box, Pos

from claudecad.jewelry.chains import PlacedLink


def diamond_cut(links: list[PlacedLink], cut_z: float) -> list[PlacedLink]:
    """Keep material within |z| <= cut_z on every link; centerlines untouched.

    The slab spans the whole chain's XY footprint (single grind, like the
    real process). Severed links are NOT detected here — check_chain's
    piece_count does that; this function only rejects parameter mistakes.
    """
    if cut_z <= 0:
        raise ValueError(f"need cut_z > 0, got {cut_z}")
    if not links:
        raise ValueError("diamond_cut needs at least one link")
    boxes = [pl.solid.bounding_box() for pl in links]
    zmax = max(max(abs(b.max.Z), abs(b.min.Z)) for b in boxes)
    if zmax <= cut_z:
        raise ValueError(
            f"cut_z={cut_z} does not cut: chain z-half-extent is {zmax:.3f}"
        )
    xmin = min(b.min.X for b in boxes)
    xmax = max(b.max.X for b in boxes)
    ymin = min(b.min.Y for b in boxes)
    ymax = max(b.max.Y for b in boxes)
    margin = 2.0
    slab = Pos((xmin + xmax) / 2, (ymin + ymax) / 2, 0) * Box(
        (xmax - xmin) + 2 * margin, (ymax - ymin) + 2 * margin, 2 * cut_z
    )
    out = []
    for i, pl in enumerate(links):
        cut = pl.solid & slab
        if cut is None or not cut.solids():
            raise ValueError(f"diamond_cut emptied link {i} (cut_z={cut_z})")
        out.append(PlacedLink(cut, pl.centerline))
    return out
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_finishing.py -v`
Expected: 3 passed (severing test included — the 0.6mm cut leaves middle slivers, multiple pieces, which check_chain must flag). If the severing cut at 0.6 produces an EMPTY solid instead of pieces (raises ValueError), adjust the test's severing cut_z upward in 0.2 steps until it produces pieces>1 — the point is the pieces path, not the exact number.

- [ ] **Step 5: Commit**

```bash
git add claudecad/jewelry/finishing.py tests/test_finishing.py
git commit -m "feat: chain-level diamond-cut finishing with severing detection"
```

---

### Task 6: Benchmark upgrade — the twisted cuban bracelet

**Files:**
- Modify: `designs/cuban_bracelet/params.py`, `designs/cuban_bracelet/build.py`
- Create: `designs/cuban_bracelet/probe.py`

**Interfaces:**
- Consumes: everything above; `export_design`/`export_glb` (tools.export); `tools/render.py` CLI.
- Produces: `out/step/cuban_bracelet.step` (20 named twisted+cut links) and `out/renders/cuban_bracelet/*.png`.

- [ ] **Step 1: Gather reference images and calibrate pitch**

WebSearch for Miami cuban bracelet top-view photos; fetch 2–3 and view them. Count links across a known bracelet length to confirm pitch ≈ 0.49×link-length (the spike's calibration). Note: flat lie, facet flats, V-groove. These calibrate step 5.

- [ ] **Step 2: Update the design files**

`designs/cuban_bracelet/params.py`:
```python
"""Cuban link bracelet — every driving dimension, in mm.

Derived values (link count, loop radius) are computed by closed_loop()
and printed by build.py; they are outputs, not inputs.

Config verified 2026-07-13 (arc-placed probe, ruled-loft construction):
link 20x14x4.1, twist 60, pitch 10, tilt 20 — all pairs zero intersection,
neighbors Lk=1, links two apart unlinked (interlock depth 1). Frontier:
tilt 15 grazes (iv01=0.065mm^3), twist 45 at tilt 20 grazes (0.015mm^3).
Escape hatch on any gate failure: tilt 20->25 first, then twist 60->45,
re-running the full gate each step.
"""
from claudecad.jewelry.chains import ChainParams
from claudecad.jewelry.links import CubanLinkParams

# bracelet centerline circumference: wrist + wearing ease
TARGET_CIRCUMFERENCE = 200.0

CHAIN = ChainParams(
    link=CubanLinkParams(length=20.0, width=14.0, wire_d=4.1, twist_deg=60.0),
    tilt_deg=20.0,
    pitch=10.0,
)

# diamond cut: keep |z| <= CUT_Z after assembly. Start at 2.8 (kept volume
# ~85-90%, clear facets); tune visually within [2.4, 3.2] — the gate
# (piece_count) protects against severing at any value.
CUT_Z = 2.8

# neighbors thread once each side at pitch 10 (probe: lk02 = 0)
INTERLOCK_DEPTH = 1
```

`designs/cuban_bracelet/build.py`:
```python
"""Build, verify, and export the cuban link bracelet (twisted + diamond-cut).

Usage: uv run python -m designs.cuban_bracelet.build
Writes out/glb/cuban_bracelet.glb always; out/step/cuban_bracelet.step only
if verification passes (exit 1 otherwise).
"""
import sys

from claudecad.jewelry.chains import closed_loop
from claudecad.jewelry.finishing import diamond_cut
from claudecad.verify import check_chain
from tools.export import export_design, export_glb

from .params import CHAIN, CUT_Z, INTERLOCK_DEPTH, TARGET_CIRCUMFERENCE


def main() -> int:
    links, info = closed_loop(CHAIN, TARGET_CIRCUMFERENCE)
    print(
        f"derived: {info.count} links, radius {info.radius:.2f} mm, "
        f"circumference {info.circumference:.1f} mm"
    )
    links = diamond_cut(links, CUT_Z)
    print(f"diamond-cut at |z| <= {CUT_Z}")

    parts = {f"link_{i:02d}": pl.solid for i, pl in enumerate(links)}
    export_glb(parts, "out/glb/cuban_bracelet.glb")

    report = check_chain(links, closed=True, interlock_depth=INTERLOCK_DEPTH)
    print(report.summary())
    if not report.ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1

    export_design(parts, "out/step/cuban_bracelet.step", assembly_label="cuban_bracelet")
    print("exported out/step/cuban_bracelet.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`designs/cuban_bracelet/probe.py`:
```python
"""Fast pairwise frontier probe for tuning this design without full builds.

Usage: uv run python -m designs.cuban_bracelet.probe '[[twist,pitch,tilt], ...]'
Builds links 0..3 of the real bracelet arc and reports pair clearances and
threading depth as JSON lines — the same criteria the full gate enforces,
at a fraction of the cost. Numbers are ground truth; renders are not.
"""
import json
import math
import sys

import numpy as np
from build123d import Pos, Rot

from claudecad.core.twisted import twisted_centerline_points
from claudecad.jewelry.links import CubanLinkParams, cuban_link
from claudecad.verify import intersection_volume, linking_number

from .params import CHAIN, TARGET_CIRCUMFERENCE


def _is_linked(lk):
    return abs(round(lk)) >= 1 and abs(lk - round(lk)) < 0.1


def probe(twist, pitch, tilt):
    lp = CHAIN.link
    p = CubanLinkParams(length=lp.length, width=lp.width, wire_d=lp.wire_d,
                        twist_deg=twist)
    solid0, _ = cuban_link(p)
    pts0 = twisted_centerline_points(p.length, p.width, p.wire_d, twist, 256)
    n = round(TARGET_CIRCUMFERENCE / pitch)
    radius = n * pitch / (2 * math.pi)
    solids, curves = [], []
    for i in range(4):
        t = tilt if i % 2 == 0 else -tilt
        loc = Rot(Z=360.0 * i / n) * Pos(0, -radius, 0) * Rot(X=t)
        solids.append(loc * solid0)
        a = math.radians(t)
        c, s = math.cos(a), math.sin(a)
        rx = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
        q = pts0 @ rx.T + np.array([0, -radius, 0])
        phi = math.radians(360.0 * i / n)
        c2, s2 = math.cos(phi), math.sin(phi)
        rz = np.array([[c2, -s2, 0], [s2, c2, 0], [0, 0, 1]])
        curves.append(q @ rz.T)
    iv = [intersection_volume(solids[0], solids[j]) for j in (1, 2, 3)]
    lk = [linking_number(curves[0], curves[j]) for j in (1, 2, 3)]
    linked = [_is_linked(v) for v in lk]
    depth = {(True, False, False): 1, (True, True, False): 2}.get(tuple(linked), 0)
    return {"twist": twist, "pitch": pitch, "tilt": tilt,
            "iv": [round(v, 4) for v in iv], "lk": [round(v, 4) for v in lk],
            "depth": depth, "ok": all(v == 0.0 for v in iv) and depth > 0}


if __name__ == "__main__":
    for combo in json.loads(sys.argv[1]):
        print(json.dumps(probe(*combo)), flush=True)
```

- [ ] **Step 3: Build and render**

```bash
uv run python -m designs.cuban_bracelet.build
uv run python tools/render.py out/glb/cuban_bracelet.glb --outdir out/renders/cuban_bracelet
```

Expected: `derived: 20 links, radius 31.83 mm, circumference 200.0 mm`, `diamond-cut at |z| <= 2.8`, `chain verification: OK (20 solids, 190 pairs checked)`, STEP exported, 4 PNGs. The 20-link check with lofted+cut solids is the heaviest run yet — expect several minutes. If any pair fails, follow the escape hatch in Global Constraints (probe.py makes each trial cheap) and record the final numbers in params.py.

- [ ] **Step 4: Full-quality visual pass**

View all four PNGs with the Read tool against the step-1 references. Checklist: links lie visibly flatter than v1 (tilt 20 vs 34); top view shows flat diamond-cut facets with a V-groove pattern; the cut faces read as polished flats (not accidental slivers); no visible loft faceting at render distance (if facets show in the detail view, raise n_sections to 192 in params and rebuild); gold reads as metal. Tune CUT_Z within [2.4, 3.2] for facet size vs chunkiness — every rebuild re-runs the full gate by construction.

- [ ] **Step 5: Update the /cad skill note and commit**

Append to `.claude/skills/cad/SKILL.md` under the loop section:

```markdown
Dense-chain designs verify with `check_chain(..., interlock_depth=N)` — see
the 2026-07-13 spec. `designs/cuban_bracelet/probe.py` is the cheap pairwise
frontier probe for parameter tuning; the construction law for twisted closed
tubes (overlapping half-loop ruled lofts ONLY) lives in that spec's "Why
ruled loft" section.
```

```bash
git add designs/ .claude/skills/cad/SKILL.md
git commit -m "feat: twisted diamond-cut cuban bracelet benchmark"
```

Then hand off: `out/step/cuban_bracelet.step` → Plasticity (File → Import). Acceptance (spec): the two v1 PARTIAL items re-judged — flat dense lie and diamond-cut V-groove — plus named editable solids in Plasticity. The user is the final judge.

---

## Verification at plan level

After all tasks: `uv run pytest -q` green (expect ~49 tests; the heavy chain/finishing tests dominate runtime). Spec coverage: Task 1+3 = component; Task 2 = verification extensions; Task 4 = dispatch/refactor; Task 5 = finishing; Task 6 = benchmark + acceptance. The spec's spike-gate requirement is already satisfied (evidence in the spec's "Why ruled loft" section and the ChainParams-style records in params.py).
