# claudeCAD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Claude Code-driven parametric CAD system (build123d → verify → headless Blender render → STEP to Plasticity), proven by a cuban link bracelet.

**Architecture:** Pure-function geometry library (`claudecad/`) produces B-rep solids; a verification layer proves validity, non-interpenetration, and topological interlock (Gauss linking number) before anything is rendered or exported; I/O lives only in `tools/` (Blender CLI rendering, named STEP export); `designs/` are thin param+build scripts.

**Tech Stack:** Python 3.12 (uv), build123d 0.11.x (OpenCASCADE), numpy, pytest, Blender 4.5 LTS headless CLI.

**Spec:** `docs/superpowers/specs/2026-07-12-claudecad-design.md`

## Global Constraints

- Project root: `/Users/mike/code/claudeCAD`. All commands run from there unless stated.
- Python `>=3.12` via uv; deps: `build123d>=0.11,<0.12`, `numpy>=1.26`, dev: `pytest>=8`.
- All dimensions are millimeters. Design parameters live only in `designs/<name>/params.py`.
- Blender binary: env `BLENDER_BIN`, default `/Applications/Blender 4.5 LTS.app/Contents/MacOS/Blender` (verified: Blender 4.5.8 LTS).
- Never render unverified geometry; never export STEP that fails verification.
- `out/` is gitignored; `uv.lock` is committed.
- In build123d 0.11.x: `is_valid` / `is_manifold` are **properties**, not methods; `shape & shape` returns a `Compound` (empty → `volume == 0.0`); `export_step`/`export_gltf` return `bool`; `Compound(children=...)` with `.label` set on children **preserves names in STEP** (spike-verified).
- Commit after every task with the message given in the task.

### Spike-verified facts this plan builds on

All verified 2026-07-12 on this machine (arm64 macOS, build123d 0.11.1, Blender 4.5.8):

1. `uv pip install build123d numpy` succeeds on Python 3.12.13 arm64.
2. Stadium wire (2 lines + 2 `JernArc`s) closes; length exactly `2*straight + 2*pi*radius`; circular-profile `sweep` along it yields a valid solid with volume `pi*r^2*length` (to 0.1%).
3. Gauss linking number on 256–400-point discretized curves: Hopf link → ±1.000, unlinked/coplanar-unthreaded → 0.000.
4. Disjoint solids: `(a & b).volume == 0.0` exactly. Overlapping: positive volume.
5. STEP round-trip via `import_step` preserves solid count and volume; labels survive as STEP names.
6. Blender 4.5 headless (`-b -P script -- args`) imports GLB, applies Principled BSDF gold, renders PNG via Cycles. Two pitfalls found: default camera `clip_end=100` clips large scenes (set from bbox), and area-light energy guesswork underexposes (use sun lights + gray world instead — distance-independent).
7. Curb-link interlock parameter grid (link 20×14×4mm): pitch 8–11mm × tilt 45–60° → intersection 0.000, Lk = 1.000 (PASS). Fails at tilt 70° (intersection ~18mm³) and pitch 12 (≥0.12mm³). **Defaults: pitch 9.0, tilt 55.0.**

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `claudecad/__init__.py`, `claudecad/core/__init__.py`, `claudecad/jewelry/__init__.py`, `tests/test_scaffold.py`

**Interfaces:**
- Produces: importable `claudecad` package; `uv run pytest` works.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "claudecad"
version = "0.1.0"
description = "Claude Code-driven parametric CAD design system"
requires-python = ">=3.12"
dependencies = ["build123d>=0.11,<0.12", "numpy>=1.26"]

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["claudecad"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Write `.gitignore`**

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
out/
```

- [ ] **Step 3: Create package skeleton**

`claudecad/__init__.py`:
```python
"""claudecad — parametric CAD component library.

Pure geometry only: modules here take parameters and return build123d
shapes plus centerline data. All I/O (rendering, export) lives in tools/.
All dimensions are millimeters.
"""
```

`claudecad/core/__init__.py` and `claudecad/jewelry/__init__.py`: empty files.

- [ ] **Step 4: Write the smoke test**

`tests/test_scaffold.py`:
```python
import build123d


def test_build123d_version():
    major, minor, *_ = build123d.__version__.split(".")
    assert (int(major), int(minor)) == (0, 11)


def test_claudecad_imports():
    import claudecad  # noqa: F401
```

- [ ] **Step 5: Sync environment and run tests**

Run: `uv sync && uv run pytest -v`
Expected: 2 passed. (First `uv sync` downloads ~200MB of OCCT wheels; takes a minute.)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock .gitignore claudecad/ tests/
git commit -m "feat: scaffold claudecad uv project with build123d"
```

---

### Task 2: Verification — solid checks and interference

**Files:**
- Create: `claudecad/verify.py`, `tests/test_verify.py`

**Interfaces:**
- Produces:
  - `SolidReport` dataclass: fields `is_valid: bool`, `is_manifold: bool`, `volume: float`; property `ok: bool`.
  - `check_solid(shape) -> SolidReport`
  - `intersection_volume(a, b) -> float` — exact boolean intersection volume; `0.0` for disjoint solids.

- [ ] **Step 1: Write failing tests**

`tests/test_verify.py`:
```python
import pytest
from build123d import Box, Pos, Torus

from claudecad.verify import SolidReport, check_solid, intersection_volume


def test_check_solid_valid_torus():
    r = check_solid(Torus(20, 3))
    assert r.is_valid and r.is_manifold
    assert r.volume == pytest.approx(3553.06, rel=1e-3)
    assert r.ok


def test_intersection_volume_disjoint_is_exactly_zero():
    assert intersection_volume(Box(10, 10, 10), Pos(100, 0, 0) * Box(10, 10, 10)) == 0.0


def test_intersection_volume_overlapping():
    # unit-offset boxes overlap in a 5x10x10 slab
    v = intersection_volume(Box(10, 10, 10), Pos(5, 0, 0) * Box(10, 10, 10))
    assert v == pytest.approx(500.0, rel=1e-6)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_verify.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'claudecad.verify'`

- [ ] **Step 3: Implement**

`claudecad/verify.py`:
```python
"""Geometry verification: validity, interference, and topological interlock.

Pure functions over build123d shapes and numpy point arrays. No I/O.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SolidReport:
    is_valid: bool
    is_manifold: bool
    volume: float

    @property
    def ok(self) -> bool:
        return self.is_valid and self.is_manifold and self.volume > 0.0


def check_solid(shape) -> SolidReport:
    return SolidReport(shape.is_valid, shape.is_manifold, shape.volume)


def intersection_volume(a, b) -> float:
    inter = a & b
    return 0.0 if inter is None else inter.volume
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_verify.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add claudecad/verify.py tests/test_verify.py
git commit -m "feat: solid validity and interference checks"
```

---

### Task 3: Verification — linking number and chain report

**Files:**
- Modify: `claudecad/verify.py` (append)
- Test: `tests/test_verify.py` (append)

**Interfaces:**
- Consumes: `SolidReport`, `check_solid`, `intersection_volume` from Task 2.
- Produces:
  - `linking_number(c1: np.ndarray, c2: np.ndarray) -> float` — Gauss linking integral over two closed discretized curves, shape (N,3)/(M,3).
  - `PairCheck` dataclass: `i: int`, `j: int`, `adjacent: bool`, `intersection: float`, `linking: float`; property `ok`.
  - `ChainReport` dataclass: `solids: list[SolidReport]`, `pairs: list[PairCheck]`; property `ok`; methods `failures() -> list[str]`, `summary() -> str`.
  - `check_chain(items: Sequence[tuple[Shape, np.ndarray]], closed: bool = False) -> ChainReport` — items are (solid, centerline-points) pairs; adjacency is consecutive indices, plus (last, 0) when `closed`.

- [ ] **Step 1: Write failing tests (append to `tests/test_verify.py`)**

```python
import numpy as np
from build123d import Rot

from claudecad.verify import ChainReport, check_chain, linking_number


def _circle(n=400, radius=1.0, center=(0, 0, 0), plane="xy"):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    zeros = np.zeros_like(t)
    if plane == "xy":
        pts = np.stack([np.cos(t), np.sin(t), zeros], axis=1)
    else:  # xz
        pts = np.stack([np.cos(t), zeros, np.sin(t)], axis=1)
    return radius * pts + np.asarray(center)


def test_linking_number_hopf_link():
    lk = linking_number(_circle(), _circle(center=(1, 0, 0), plane="xz"))
    assert round(lk) in (-1, 1)
    assert abs(lk - round(lk)) < 0.01


def test_linking_number_unlinked():
    assert abs(linking_number(_circle(), _circle(center=(10, 0, 0), plane="xz"))) < 0.01


def test_linking_number_coplanar_unthreaded():
    # overlapping projections but not threaded
    assert abs(linking_number(_circle(), _circle(center=(1.5, 0, 0)))) < 0.01


def _hopf_tori():
    """Two interlocked tori (solid Hopf link) + their centerline circles."""
    a = Torus(10, 1.5)
    b = Pos(10, 0, 0) * Rot(X=90) * Torus(10, 1.5)
    ca = 10 * _circle()
    cb = _circle(radius=10, center=(10, 0, 0), plane="xz")
    return [(a, ca), (b, cb)]


def test_check_chain_interlocked_pair_passes():
    report = check_chain(_hopf_tori())
    assert isinstance(report, ChainReport)
    assert report.ok, report.failures()


def test_check_chain_fails_on_unlinked_adjacent():
    a = Torus(10, 1.5)
    b = Pos(50, 0, 0) * Torus(10, 1.5)
    report = check_chain([(a, 10 * _circle()), (b, 10 * _circle() + (50, 0, 0))])
    assert not report.ok
    assert any("not interlocked" in f for f in report.failures())


def test_check_chain_fails_on_interpenetration():
    a = Torus(10, 1.5)
    b = Pos(2, 0, 0) * Torus(10, 1.5)  # same plane, overlapping tubes
    report = check_chain([(a, 10 * _circle()), (b, 10 * _circle() + (2, 0, 0))])
    assert not report.ok
    assert any("interpenetrates" in f for f in report.failures())
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_verify.py -v`
Expected: earlier 3 still pass; new tests FAIL with `ImportError: cannot import name 'linking_number'`

- [ ] **Step 3: Implement (append to `claudecad/verify.py`)**

```python
LINKING_TOL = 0.1  # max deviation of discretized Gauss integral from an integer


def linking_number(c1: np.ndarray, c2: np.ndarray) -> float:
    """Gauss linking integral of two closed curves given as (N,3) point loops.

    Nonzero integer => the loops are topologically inseparable. Midpoint
    quadrature over all segment pairs; exact in the limit, within ~1e-2 of
    an integer at >=256 points for well-separated curves.
    """
    r1, r2 = np.asarray(c1, float), np.asarray(c2, float)
    d1 = np.roll(r1, -1, axis=0) - r1
    d2 = np.roll(r2, -1, axis=0) - r2
    m1, m2 = r1 + 0.5 * d1, r2 + 0.5 * d2
    diff = m1[:, None, :] - m2[None, :, :]
    dist3 = np.linalg.norm(diff, axis=2) ** 3
    cross = np.cross(d1[:, None, :], d2[None, :, :])
    integrand = np.einsum("nmk,nmk->nm", cross, diff) / dist3
    return float(integrand.sum() / (4 * np.pi))


@dataclass(frozen=True)
class PairCheck:
    i: int
    j: int
    adjacent: bool
    intersection: float
    linking: float

    @property
    def is_linked(self) -> bool:
        return (
            abs(round(self.linking)) >= 1
            and abs(self.linking - round(self.linking)) < LINKING_TOL
        )

    @property
    def ok(self) -> bool:
        if self.intersection > 0.0:
            return False
        return self.is_linked if self.adjacent else not self.is_linked


@dataclass(frozen=True)
class ChainReport:
    solids: list[SolidReport]
    pairs: list[PairCheck]

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.solids) and all(p.ok for p in self.pairs)

    def failures(self) -> list[str]:
        msgs = []
        for i, s in enumerate(self.solids):
            if not s.ok:
                msgs.append(
                    f"link {i}: invalid solid (valid={s.is_valid} "
                    f"manifold={s.is_manifold} volume={s.volume:.3f})"
                )
        for p in self.pairs:
            if p.intersection > 0.0:
                msgs.append(
                    f"links {p.i},{p.j}: interpenetrates by {p.intersection:.3f} mm^3"
                )
            if p.adjacent and not p.is_linked:
                msgs.append(
                    f"links {p.i},{p.j}: not interlocked (Lk={p.linking:.3f})"
                )
            if not p.adjacent and p.is_linked:
                msgs.append(
                    f"links {p.i},{p.j}: unexpectedly linked (Lk={p.linking:.3f})"
                )
        return msgs

    def summary(self) -> str:
        status = "OK" if self.ok else "FAILED"
        lines = [
            f"chain verification: {status} "
            f"({len(self.solids)} solids, {len(self.pairs)} pairs checked)"
        ]
        lines += self.failures()
        return "\n".join(lines)


def _bboxes_disjoint(a, b) -> bool:
    ba, bb = a.bounding_box(), b.bounding_box()
    return (
        ba.max.X < bb.min.X or bb.max.X < ba.min.X
        or ba.max.Y < bb.min.Y or bb.max.Y < ba.min.Y
        or ba.max.Z < bb.min.Z or bb.max.Z < ba.min.Z
    )


def check_chain(items, closed: bool = False) -> ChainReport:
    """Verify a chain of (solid, centerline_points) pairs.

    Adjacent = consecutive indices (+ wraparound when closed). Adjacent pairs
    must interlock (|Lk|>=1) without touching; all other pairs must be
    unlinked and disjoint. Disjoint bounding boxes prove zero intersection
    (a separating axis-aligned plane exists), so the boolean is skipped.
    """
    items = list(items)
    n = len(items)
    solids = [check_solid(s) for s, _ in items]
    adjacent = {(i, i + 1) for i in range(n - 1)}
    if closed and n > 2:
        adjacent.add((0, n - 1))
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            si, ci = items[i]
            sj, cj = items[j]
            inter = 0.0 if _bboxes_disjoint(si, sj) else intersection_volume(si, sj)
            pairs.append(
                PairCheck(i, j, (i, j) in adjacent, inter, linking_number(ci, cj))
            )
    return ChainReport(solids, pairs)
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_verify.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add claudecad/verify.py tests/test_verify.py
git commit -m "feat: Gauss linking-number interlock check and chain report"
```

---

### Task 4: Core — stadium centerline and discretization

**Files:**
- Create: `claudecad/core/centerline.py`, `tests/test_centerline.py`

**Interfaces:**
- Produces:
  - `stadium_wire(straight: float, radius: float) -> Wire` — closed stadium (slot) centerline in the XY plane, long axis X, centered at origin. `straight` is the full length of each straight segment.
  - `discretize(wire: Wire, n: int = 256) -> np.ndarray` — (n,3) points along the wire.

- [ ] **Step 1: Write failing tests**

`tests/test_centerline.py`:
```python
import math

import numpy as np
import pytest

from claudecad.core.centerline import discretize, stadium_wire


def test_stadium_wire_closed_and_length():
    w = stadium_wire(straight=12.0, radius=5.0)
    assert w.is_closed
    assert w.length == pytest.approx(2 * 12.0 + 2 * math.pi * 5.0, rel=1e-6)


def test_stadium_wire_extents():
    w = stadium_wire(straight=12.0, radius=5.0)
    bb = w.bounding_box()
    assert bb.max.X - bb.min.X == pytest.approx(12.0 + 2 * 5.0, rel=1e-6)
    assert bb.max.Y - bb.min.Y == pytest.approx(2 * 5.0, rel=1e-6)
    assert abs(bb.max.Z) < 1e-6 and abs(bb.min.Z) < 1e-6


def test_stadium_wire_centered():
    bb = stadium_wire(straight=12.0, radius=5.0).bounding_box()
    assert bb.center().length == pytest.approx(0.0, abs=1e-6)


def test_discretize_shape_and_closure():
    w = stadium_wire(straight=12.0, radius=5.0)
    pts = discretize(w, n=200)
    assert pts.shape == (200, 3)
    # endpoint=False: last point must not duplicate the first
    assert np.linalg.norm(pts[0] - pts[-1]) > 1e-3


def test_degenerate_params_rejected():
    with pytest.raises(ValueError):
        stadium_wire(straight=0.0, radius=5.0)
    with pytest.raises(ValueError):
        stadium_wire(straight=10.0, radius=0.0)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_centerline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'claudecad.core.centerline'`

- [ ] **Step 3: Implement**

`claudecad/core/centerline.py`:
```python
"""Centerline curves for swept components."""
from __future__ import annotations

import numpy as np
from build123d import BuildLine, JernArc, Line, Wire


def stadium_wire(straight: float, radius: float) -> Wire:
    """Closed stadium (slot) curve in XY: two straights joined by semicircles.

    Long axis along X, centered at the origin. `straight` is the full length
    of each straight segment; total X extent is straight + 2*radius.
    """
    if straight <= 0 or radius <= 0:
        raise ValueError(
            f"stadium_wire needs straight > 0 and radius > 0, got {straight=} {radius=}"
        )
    h = straight / 2
    with BuildLine() as path:
        Line((-h, radius), (h, radius))
        JernArc(start=(h, radius), tangent=(1, 0), radius=radius, arc_size=-180)
        Line((h, -radius), (-h, -radius))
        JernArc(start=(-h, -radius), tangent=(-1, 0), radius=radius, arc_size=-180)
    return path.wire()


def discretize(wire: Wire, n: int = 256) -> np.ndarray:
    """Sample a wire into an (n,3) point array (open sampling of a closed loop)."""
    return np.array(
        [tuple(wire.position_at(t)) for t in np.linspace(0, 1, n, endpoint=False)]
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_centerline.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add claudecad/core/centerline.py tests/test_centerline.py
git commit -m "feat: stadium centerline wire and discretization"
```

---

### Task 5: STEP/GLB export with named parts

**Files:**
- Create: `tools/__init__.py` (empty), `tools/export.py`, `tests/test_export.py`

**Interfaces:**
- Produces:
  - `export_design(parts: dict[str, Shape], path, assembly_label: str = "design") -> None` — writes STEP; each dict key becomes the part's name in the STEP assembly (visible in Plasticity's outliner). Raises `RuntimeError` on failure.
  - `export_glb(parts: dict[str, Shape], path, linear_deflection: float = 0.02, angular_deflection: float = 0.2) -> None` — binary glTF for rendering.

- [ ] **Step 1: Write failing tests**

`tests/test_export.py`:
```python
import pytest
from build123d import Pos, Torus, import_step

from tools.export import export_design, export_glb


def _parts():
    return {"link_1": Torus(20, 3), "link_2": Pos(50, 0, 0) * Torus(20, 3)}


def test_step_roundtrip_and_names(tmp_path):
    path = tmp_path / "two_tori.step"
    export_design(_parts(), path, assembly_label="pair")
    back = import_step(str(path))
    assert len(back.solids()) == 2
    total = sum(s.volume for s in back.solids())
    assert total == pytest.approx(2 * 3553.06, rel=1e-3)
    text = path.read_text()
    for name in ("pair", "link_1", "link_2"):
        assert name in text


def test_glb_export(tmp_path):
    path = tmp_path / "two_tori.glb"
    export_glb(_parts(), path)
    data = path.read_bytes()
    assert data[:4] == b"glTF"
    assert len(data) > 10_000
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_export.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.export'`

- [ ] **Step 3: Implement**

`tools/export.py`:
```python
"""Disk export: named STEP assemblies (for Plasticity) and GLB (for rendering)."""
from __future__ import annotations

import os

from build123d import Compound, export_gltf, export_step


def _labeled_compound(parts: dict, assembly_label: str) -> Compound:
    shapes = []
    for name, shape in parts.items():
        shape.label = name  # mutates caller's shape label; geometry untouched
        shapes.append(shape)
    comp = Compound(children=shapes)
    comp.label = assembly_label
    return comp


def export_design(parts: dict, path, assembly_label: str = "design") -> None:
    """Write parts as a named STEP assembly. Keys become Plasticity part names."""
    os.makedirs(os.path.dirname(str(path)) or ".", exist_ok=True)
    if not export_step(_labeled_compound(parts, assembly_label), str(path)):
        raise RuntimeError(f"STEP export failed: {path}")


def export_glb(
    parts: dict,
    path,
    linear_deflection: float = 0.02,
    angular_deflection: float = 0.2,
) -> None:
    """Write parts as binary glTF for rendering. Deflections in mm/radians."""
    os.makedirs(os.path.dirname(str(path)) or ".", exist_ok=True)
    comp = _labeled_compound(parts, "render")
    if not export_gltf(
        comp,
        str(path),
        binary=True,
        linear_deflection=linear_deflection,
        angular_deflection=angular_deflection,
    ):
        raise RuntimeError(f"GLB export failed: {path}")
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_export.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add tools/__init__.py tools/export.py tests/test_export.py
git commit -m "feat: named STEP assembly and GLB export"
```

---

### Task 6: Headless Blender rendering

**Files:**
- Create: `tools/render.py`, `tools/blender_scene.py`, `tests/test_render_smoke.py`

**Interfaces:**
- Consumes: `export_glb` from Task 5 (in the test).
- Produces:
  - CLI: `uv run python tools/render.py <model.glb> --outdir <dir> [--views persp,top,front,detail] [--res 1280x960] [--samples 64]` — writes `<dir>/<view>.png` per view.
  - Function: `render_glb(glb_path, outdir, views=("persp", "top", "front", "detail"), res=(1280, 960), samples=64) -> list[Path]` — returns written PNGs; raises `RuntimeError` with Blender's stderr tail on failure.
- Note: `tools/blender_scene.py` runs *inside* Blender's bundled Python (has `bpy`, no numpy guarantees, no project imports) — it must stay dependency-free.

- [ ] **Step 1: Write `tools/blender_scene.py`** (not unit-testable outside Blender; exercised by the smoke test)

```python
"""Runs INSIDE Blender: import GLB, gold material, studio setup, render views.

Invoked by tools/render.py as:
  blender -b -P tools/blender_scene.py -- <glb> <outdir> <views_csv> <WxH> <samples>
Dependency-free on purpose: only bpy/mathutils are available.
"""
import os
import sys

import bpy
import mathutils

argv = sys.argv[sys.argv.index("--") + 1 :]
glb_path, outdir, views_csv, res_str, samples_str = argv
views = views_csv.split(",")
res_x, res_y = (int(v) for v in res_str.split("x"))
samples = int(samples_str)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()

bpy.ops.import_scene.gltf(filepath=glb_path)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    print("RENDER_ERROR no meshes imported", file=sys.stderr)
    sys.exit(1)

# gold material (base color: commonly used measured gold albedo)
gold = bpy.data.materials.new("Gold")
gold.use_nodes = True
bsdf = gold.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (1.0, 0.766, 0.336, 1.0)
bsdf.inputs["Metallic"].default_value = 1.0
bsdf.inputs["Roughness"].default_value = 0.22
for o in meshes:
    o.data.materials.clear()
    o.data.materials.append(gold)
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.shade_auto_smooth()

# scene bounds
mins = mathutils.Vector((1e18,) * 3)
maxs = mathutils.Vector((-1e18,) * 3)
for o in meshes:
    for corner in o.bound_box:
        wc = o.matrix_world @ mathutils.Vector(corner)
        mins = mathutils.Vector(map(min, mins, wc))
        maxs = mathutils.Vector(map(max, maxs, wc))
center = (mins + maxs) / 2
size = max((maxs - mins).length, 1e-6)

# lighting: uniform gray world as a giant softbox + two suns for definition.
# Suns are distance-independent, so this works at any model scale.
world = bpy.data.worlds.new("Studio")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.35, 0.35, 0.36, 1.0)
bg.inputs["Strength"].default_value = 1.0


def add_sun(name, direction, energy):
    """direction = the way the light travels (sun local -Z points along it)."""
    data = bpy.data.lights.new(name, type="SUN")
    data.energy = energy
    data.angle = 0.3  # soft shadows
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    d = mathutils.Vector(direction).normalized()
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return obj


add_sun("Key", (-0.6, 0.6, -1.0), 4.0)   # from upper front-left, pointing down-back
add_sun("Rim", (0.2, -1.0, -0.4), 2.0)

cam_data = bpy.data.cameras.new("Cam")
cam_data.clip_start = size / 1000
cam_data.clip_end = size * 20
cam = bpy.data.objects.new("Cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = samples
scene.cycles.use_denoising = True
scene.render.resolution_x = res_x
scene.render.resolution_y = res_y

VIEW_DIRS = {
    "persp": mathutils.Vector((1.0, -1.0, 0.7)),
    "top": mathutils.Vector((0.001, -0.001, 1.0)),
    "front": mathutils.Vector((0.0, -1.0, 0.25)),
    "detail": mathutils.Vector((1.0, -1.0, 0.7)),
}


def aim(target, direction, dist):
    cam.location = target + direction.normalized() * dist
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()


for view in views:
    direction = VIEW_DIRS[view]
    if view == "detail":
        # zoom onto the +X edge of the model (a few links of a chain)
        aim(mathutils.Vector((maxs.x, center.y, center.z)), direction, size * 0.45)
    else:
        aim(center, direction, size * 1.6)
    out = os.path.join(outdir, f"{view}.png")
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print(f"RENDER_DONE {out}")
```

- [ ] **Step 2: Write `tools/render.py`**

```python
"""Drive headless Blender to render a GLB into studio PNGs."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_BLENDER = "/Applications/Blender 4.5 LTS.app/Contents/MacOS/Blender"
SCENE_SCRIPT = Path(__file__).parent / "blender_scene.py"
DEFAULT_VIEWS = ("persp", "top", "front", "detail")


def render_glb(
    glb_path,
    outdir,
    views=DEFAULT_VIEWS,
    res=(1280, 960),
    samples=64,
) -> list[Path]:
    glb_path, outdir = Path(glb_path), Path(outdir)
    if not glb_path.exists():
        raise FileNotFoundError(glb_path)
    outdir.mkdir(parents=True, exist_ok=True)
    blender = os.environ.get("BLENDER_BIN", DEFAULT_BLENDER)
    cmd = [
        blender, "-b", "-P", str(SCENE_SCRIPT), "--",
        str(glb_path), str(outdir), ",".join(views),
        f"{res[0]}x{res[1]}", str(samples),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    written = [outdir / f"{v}.png" for v in views]
    missing = [p for p in written if not p.exists() or p.stat().st_size == 0]
    if proc.returncode != 0 or missing:
        tail = "\n".join((proc.stderr or proc.stdout).splitlines()[-25:])
        raise RuntimeError(
            f"Blender render failed (rc={proc.returncode}, missing={missing}):\n{tail}"
        )
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("glb")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--views", default=",".join(DEFAULT_VIEWS))
    ap.add_argument("--res", default="1280x960")
    ap.add_argument("--samples", type=int, default=64)
    args = ap.parse_args()
    w, h = (int(v) for v in args.res.split("x"))
    for png in render_glb(
        args.glb, args.outdir, tuple(args.views.split(",")), (w, h), args.samples
    ):
        print(png)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write the smoke test**

`tests/test_render_smoke.py`:
```python
"""End-to-end render smoke test. Runs real Blender headlessly (~30-60s)."""
from build123d import Torus

from tools.export import export_glb
from tools.render import render_glb


def test_render_torus(tmp_path):
    glb = tmp_path / "torus.glb"
    export_glb({"torus": Torus(20, 3)}, glb)
    pngs = render_glb(glb, tmp_path / "renders", views=("persp",), res=(480, 360), samples=24)
    assert len(pngs) == 1
    assert pngs[0].stat().st_size > 10_000
```

- [ ] **Step 4: Run the smoke test**

Run: `uv run pytest tests/test_render_smoke.py -v`
Expected: 1 passed (takes ~30–60s — Blender startup + Cycles render)

- [ ] **Step 5: Visually inspect a full-quality render**

```bash
uv run python - <<'EOF'
from build123d import Torus
from tools.export import export_glb
export_glb({"torus": Torus(20, 3)}, "out/glb/smoke_torus.glb")
EOF
uv run python tools/render.py out/glb/smoke_torus.glb --outdir out/renders/smoke
```

Then **view `out/renders/smoke/persp.png` with the Read tool**. Acceptance: complete torus (no clipped/black-capped geometry), clearly gold metallic, well exposed, soft shadows. If clipped or dark, fix `blender_scene.py` (clip planes / light energies) before committing — do not proceed with a broken renderer.

- [ ] **Step 6: Commit**

```bash
git add tools/render.py tools/blender_scene.py tests/test_render_smoke.py
git commit -m "feat: headless Blender studio renderer for GLB models"
```

---

### Task 7: Curb link component

**Files:**
- Create: `claudecad/jewelry/links.py`, `tests/test_links.py`

**Interfaces:**
- Consumes: `stadium_wire` from Task 4 (`claudecad.core.centerline`).
- Produces:
  - `LinkParams` frozen dataclass: `length: float = 20.0` (outer, along chain axis X), `width: float = 14.0` (outer, Y), `wire_d: float = 4.0`, `n_centerline: int = 256`. Validates `wire_d < width < length` in `__post_init__`.
  - `curb_link(p: LinkParams) -> tuple[Solid, Wire]` — flat link solid centered at origin in XY, plus its **untessellated** centerline wire (so placement transforms can be applied to both before discretizing).

- [ ] **Step 1: Write failing tests**

`tests/test_links.py`:
```python
import math

import pytest

from claudecad.jewelry.links import LinkParams, curb_link
from claudecad.verify import check_solid


def test_curb_link_valid_solid():
    solid, wire = curb_link(LinkParams())
    assert check_solid(solid).ok


def test_curb_link_outer_dimensions():
    p = LinkParams(length=20.0, width=14.0, wire_d=4.0)
    solid, _ = curb_link(p)
    bb = solid.bounding_box()
    assert bb.max.X - bb.min.X == pytest.approx(p.length, abs=1e-4)
    assert bb.max.Y - bb.min.Y == pytest.approx(p.width, abs=1e-4)
    assert bb.max.Z - bb.min.Z == pytest.approx(p.wire_d, abs=1e-4)


def test_curb_link_volume_matches_sweep():
    p = LinkParams(length=20.0, width=14.0, wire_d=4.0)
    solid, wire = curb_link(p)
    expected = math.pi * (p.wire_d / 2) ** 2 * wire.length
    assert solid.volume == pytest.approx(expected, rel=1e-2)


def test_link_params_validation():
    with pytest.raises(ValueError):
        LinkParams(length=10.0, width=14.0, wire_d=4.0)  # length <= width
    with pytest.raises(ValueError):
        LinkParams(length=20.0, width=4.0, wire_d=4.0)  # wire_d >= width
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_links.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'claudecad.jewelry.links'`

- [ ] **Step 3: Implement**

`claudecad/jewelry/links.py`:
```python
"""Chain link components. Pure geometry: params in, solids out."""
from __future__ import annotations

from dataclasses import dataclass

from build123d import Circle, Plane, Solid, Wire, sweep

from claudecad.core.centerline import stadium_wire


@dataclass(frozen=True)
class LinkParams:
    """Outer dimensions (mm) of a flat oval link, long axis X."""

    length: float = 20.0
    width: float = 14.0
    wire_d: float = 4.0
    n_centerline: int = 256

    def __post_init__(self):
        if not (self.wire_d < self.width < self.length):
            raise ValueError(
                f"need wire_d < width < length, got "
                f"wire_d={self.wire_d} width={self.width} length={self.length}"
            )

    @property
    def end_radius(self) -> float:
        """Centerline radius of the semicircular ends."""
        return (self.width - self.wire_d) / 2

    @property
    def straight(self) -> float:
        """Full length of each straight centerline segment."""
        return self.length - self.width


def curb_link(p: LinkParams) -> tuple[Solid, Wire]:
    """Flat oval link: circular wire profile swept along a stadium centerline.

    Returns (solid, centerline wire), both centered at the origin in the XY
    plane. The wire is returned untessellated so callers can transform solid
    and centerline together before discretizing.
    """
    w = stadium_wire(p.straight, p.end_radius)
    profile = Plane(origin=w @ 0, z_dir=w % 0) * Circle(p.wire_d / 2)
    return sweep(profile, path=w), w
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_links.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add claudecad/jewelry/links.py tests/test_links.py
git commit -m "feat: parametric curb link component"
```

---

### Task 8: Straight chain assembly

**Files:**
- Create: `claudecad/jewelry/chains.py`, `tests/test_chains.py`

**Interfaces:**
- Consumes: `LinkParams`, `curb_link` (Task 7); `discretize` (Task 4); `check_chain` (Task 3).
- Produces:
  - `ChainParams` frozen dataclass: `link: LinkParams = LinkParams()`, `tilt_deg: float = 55.0`, `pitch: float = 9.0`. Spike-verified defaults: interlocked, zero intersection.
  - `PlacedLink` NamedTuple: `solid: Solid`, `centerline: np.ndarray` — unpacks as the (solid, points) tuple `check_chain` consumes.
  - `straight_chain(p: ChainParams, count: int) -> list[PlacedLink]` — links along +X, link *i* at `x = i*pitch`, tilted about X by `+tilt` (even *i*) / `−tilt` (odd *i*).

- [ ] **Step 1: Write failing tests**

`tests/test_chains.py`:
```python
import pytest

from claudecad.jewelry.chains import ChainParams, PlacedLink, straight_chain
from claudecad.verify import check_chain


def test_straight_chain_count_and_type():
    links = straight_chain(ChainParams(), count=3)
    assert len(links) == 3
    assert all(isinstance(pl, PlacedLink) for pl in links)


def test_straight_chain_spacing():
    p = ChainParams()
    links = straight_chain(p, count=3)
    c0 = links[0].centerline.mean(axis=0)
    c1 = links[1].centerline.mean(axis=0)
    assert c1[0] - c0[0] == pytest.approx(p.pitch, abs=1e-6)


def test_straight_chain_verifies():
    """The core benchmark property: interlocked, untouching, only neighbors linked."""
    report = check_chain(straight_chain(ChainParams(), count=4))
    assert report.ok, report.summary()
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_chains.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'claudecad.jewelry.chains'`

- [ ] **Step 3: Implement**

`claudecad/jewelry/chains.py`:
```python
"""Chain assemblies built from links. Pure geometry: params in, placed solids out."""
from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

import numpy as np
from build123d import Pos, Rot, Solid

from claudecad.core.centerline import discretize
from claudecad.jewelry.links import LinkParams, curb_link


@dataclass(frozen=True)
class ChainParams:
    """Curb chain: links tilted alternately +/-tilt_deg about the chain axis.

    Defaults verified by parameter sweep (2026-07-12): pitch 8-11 x tilt 45-60
    interlock without intersection for the default 20x14x4 link; 55/9.0 sits
    in the middle of that region.
    """

    link: LinkParams = LinkParams()
    tilt_deg: float = 55.0
    pitch: float = 9.0


class PlacedLink(NamedTuple):
    solid: Solid
    centerline: np.ndarray  # (n,3) points, world coordinates


def straight_chain(p: ChainParams, count: int) -> list[PlacedLink]:
    """Chain along +X: link i at x=i*pitch, tilted about X, alternating sign."""
    base_solid, base_wire = curb_link(p.link)
    placed = []
    for i in range(count):
        tilt = p.tilt_deg if i % 2 == 0 else -p.tilt_deg
        loc = Pos(i * p.pitch, 0, 0) * Rot(X=tilt)
        placed.append(
            PlacedLink(loc * base_solid, discretize(loc * base_wire, p.link.n_centerline))
        )
    return placed
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_chains.py -v`
Expected: 3 passed (`test_straight_chain_verifies` runs several boolean ops; ~10–30s)

If `test_straight_chain_verifies` fails (e.g., a non-adjacent pair touches): the ground truth is the report — print `report.summary()`, then adjust `ChainParams` defaults within the spike-verified passing region (pitch 8–11, tilt 45–60), re-run, and record the final numbers in the `ChainParams` docstring. Do not loosen the checks.

- [ ] **Step 5: Commit**

```bash
git add claudecad/jewelry/chains.py tests/test_chains.py
git commit -m "feat: straight curb chain assembly with verified interlock"
```

---

### Task 9: Closed bracelet loop

**Files:**
- Modify: `claudecad/jewelry/chains.py` (append)
- Test: `tests/test_chains.py` (append)

**Interfaces:**
- Consumes: everything from Task 8.
- Produces:
  - `LoopInfo` frozen dataclass: `count: int`, `radius: float`, `circumference: float` — the derived values (spec: driving params drive; count/pitch-derived values are read-only outputs).
  - `closed_loop(p: ChainParams, target_circumference: float) -> tuple[list[PlacedLink], LoopInfo]` — links arranged around a circle in XY; count is `target_circumference/pitch` rounded to the nearest **even** integer (alternating tilt must close seamlessly); actual radius recomputed from the final count.

- [ ] **Step 1: Write failing tests (append to `tests/test_chains.py`)**

```python
import math

import numpy as np

from claudecad.jewelry.chains import LoopInfo, closed_loop


def test_closed_loop_derived_values():
    p = ChainParams()
    links, info = closed_loop(p, target_circumference=200.0)
    assert isinstance(info, LoopInfo)
    assert info.count % 2 == 0
    assert info.count == round(200.0 / p.pitch) or info.count == round(200.0 / p.pitch) + 1
    assert info.circumference == pytest.approx(info.count * p.pitch)
    assert info.radius == pytest.approx(info.circumference / (2 * math.pi))
    assert len(links) == info.count


def test_closed_loop_links_lie_on_circle():
    links, info = closed_loop(ChainParams(), target_circumference=200.0)
    for pl in links:
        center = pl.centerline.mean(axis=0)
        assert np.hypot(center[0], center[1]) == pytest.approx(info.radius, rel=0.02)


def test_closed_loop_verifies_including_wraparound():
    """Benchmark property on the full bracelet: every neighbor pair (incl.
    last-first) interlocked, zero interpenetration anywhere."""
    links, _ = closed_loop(ChainParams(), target_circumference=200.0)
    report = check_chain(links, closed=True)
    assert report.ok, report.summary()
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_chains.py -v`
Expected: Task 8 tests pass; new tests FAIL with `ImportError: cannot import name 'closed_loop'`

- [ ] **Step 3: Implement (append to `claudecad/jewelry/chains.py`)**

```python
import math


@dataclass(frozen=True)
class LoopInfo:
    """Derived (read-only) values of a closed loop."""

    count: int
    radius: float
    circumference: float


def closed_loop(
    p: ChainParams, target_circumference: float
) -> tuple[list[PlacedLink], LoopInfo]:
    """Closed bracelet: links around a circle in XY, faces up +/-Z.

    Link count = target_circumference/pitch rounded to the nearest even
    integer (odd counts cannot close an alternating +/-tilt pattern); the
    actual radius is then count*pitch / 2*pi, so the realized circumference
    tracks the pitch exactly and the target approximately.
    """
    n = round(target_circumference / p.pitch)
    if n % 2:
        n += 1
    if n < 4:
        raise ValueError(
            f"loop needs >=4 links, got {n} from "
            f"target_circumference={target_circumference} pitch={p.pitch}"
        )
    radius = n * p.pitch / (2 * math.pi)
    base_solid, base_wire = curb_link(p.link)
    placed = []
    for i in range(n):
        tilt = p.tilt_deg if i % 2 == 0 else -p.tilt_deg
        # at angle 0 the link sits at (0,-radius) with its long axis (X)
        # along the circle tangent; Rot(Z) walks it around the loop
        loc = Rot(Z=360 * i / n) * Pos(0, -radius, 0) * Rot(X=tilt)
        placed.append(
            PlacedLink(loc * base_solid, discretize(loc * base_wire, p.link.n_centerline))
        )
    return placed, LoopInfo(count=n, radius=radius, circumference=n * p.pitch)
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_chains.py -v`
Expected: 6 passed. `test_closed_loop_verifies_including_wraparound` builds ~22 links and runs ~22 boolean ops; expect 1–3 minutes.

If the wraparound test fails: curvature packs links ~0.4% tighter than the straight chain (chord vs arc at n≈22) and rotates neighbors ~16° about Z relative to each other. The report names the failing pair and penetration depth. Fix by adjusting `ChainParams` defaults within the verified region (raise pitch toward 10–11 before touching tilt), re-run, and record the working numbers in the `ChainParams` docstring. Do not special-case the wraparound pair and do not loosen the checks.

- [ ] **Step 5: Commit**

```bash
git add claudecad/jewelry/chains.py tests/test_chains.py
git commit -m "feat: closed bracelet loop with wraparound interlock verification"
```

---

### Task 10: The /cad skill

**Files:**
- Create: `.claude/skills/cad/SKILL.md`

**Interfaces:**
- Consumes: the commands established in Tasks 5, 6, 9 (documented verbatim).
- Produces: the workflow contract every future design session in this repo follows.

- [ ] **Step 1: Write `.claude/skills/cad/SKILL.md`**

```markdown
---
name: cad
description: Use when designing, modifying, rendering, or exporting any CAD piece in this repo — defines the build → verify → render → iterate → export loop and its non-negotiable rules.
---

# CAD design loop

Parametric designs live in `designs/<name>/` as `params.py` (every dimension,
mm, single source of truth) + `build.py` (composes claudecad library parts,
verifies, writes GLB/STEP to `out/`). The library is `claudecad/`
(pure geometry) + `tools/` (render/export I/O).

## The loop

1. Edit `designs/<name>/params.py` (or library code for new components).
2. `uv run python -m designs.<name>.build` — builds, **verifies**, writes
   `out/glb/<name>.glb`, and (only if verification passes) `out/step/<name>.step`.
3. `uv run python tools/render.py out/glb/<name>.glb --outdir out/renders/<name>`
4. View every PNG with the Read tool. Judge against reference photos of the
   real-world piece — fetch references, don't design from memory.
5. Iterate 1–4 until the renders read true. Then hand `out/step/<name>.step`
   to the user for Plasticity import (File → Import; parts arrive named).

## Non-negotiable rules

- All dimensions in millimeters, defined only in `params.py`. Derived values
  (link counts, radii) are computed by the library and printed, never set.
- Never show the user renders of geometry that failed verification; fix the
  geometry first. Never export STEP that fails verification (build.py
  enforces this — do not bypass it).
- Verification is ground truth: `check_chain` proves interlock via Gauss
  linking number and non-contact via boolean intersection. "It looks right
  in the render" is not evidence; the report is.
- When a check fails, adjust parameters or geometry — never the check.
- New components go in `claudecad/` as pure functions with pytest coverage
  (`uv run pytest`), following the patterns in `claudecad/jewelry/links.py`.

## Blender renderer

`tools/render.py` needs Blender; default binary is
`/Applications/Blender 4.5 LTS.app/Contents/MacOS/Blender`, override with
env `BLENDER_BIN`. Views: persp, top, front, detail. Bump `--samples` or
`--res` for beauty shots.
```

- [ ] **Step 2: Verify the skill file loads** (structural check: frontmatter parses, name matches directory)

Run: `uv run python -c "
import pathlib, re
text = pathlib.Path('.claude/skills/cad/SKILL.md').read_text()
m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
assert m, 'missing frontmatter'
assert 'name: cad' in m.group(1) and 'description:' in m.group(1)
print('SKILL.md OK')
"`
Expected: `SKILL.md OK`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/cad/SKILL.md
git commit -m "feat: /cad design-loop skill"
```

---

### Task 11: Benchmark — the cuban link bracelet

**Files:**
- Create: `designs/cuban_bracelet/params.py`, `designs/cuban_bracelet/build.py`

**Interfaces:**
- Consumes: `ChainParams`, `LinkParams`, `closed_loop` (Tasks 7–9); `check_chain` (Task 3); `export_design`, `export_glb` (Task 5); `render_glb` CLI (Task 6).
- Produces: `out/step/cuban_bracelet.step` (the deliverable) and `out/renders/cuban_bracelet/*.png`.

- [ ] **Step 1: Gather reference images**

WebSearch for cuban link bracelet product photos (e.g., "cuban link bracelet close up flat lay"); fetch 2–3 and view them. Note the proportions that define the look: link width:length ratio (~0.7 typical), tight packing (adjacent links overlap roughly half a link), near-flat lie, uniform V-groove pattern down the center. These observations calibrate step 4 — do not skip.

- [ ] **Step 2: Write the design**

`designs/cuban_bracelet/params.py`:
```python
"""Cuban link bracelet — every driving dimension, in mm.

Derived values (link count, loop radius) are computed by closed_loop()
and printed by build.py; they are outputs, not inputs.
"""
from claudecad.jewelry.chains import ChainParams
from claudecad.jewelry.links import LinkParams

# bracelet centerline circumference: wrist + wearing ease
TARGET_CIRCUMFERENCE = 200.0

CHAIN = ChainParams(
    link=LinkParams(length=20.0, width=14.0, wire_d=4.0),
    tilt_deg=55.0,
    pitch=9.0,
)
```

`designs/cuban_bracelet/build.py`:
```python
"""Build, verify, and export the cuban link bracelet.

Usage: uv run python -m designs.cuban_bracelet.build
Writes out/glb/cuban_bracelet.glb always; out/step/cuban_bracelet.step only
if verification passes (exit 1 otherwise).
"""
import sys

from claudecad.jewelry.chains import closed_loop
from claudecad.verify import check_chain
from tools.export import export_design, export_glb

from .params import CHAIN, TARGET_CIRCUMFERENCE


def main() -> int:
    links, info = closed_loop(CHAIN, TARGET_CIRCUMFERENCE)
    print(
        f"derived: {info.count} links, radius {info.radius:.2f} mm, "
        f"circumference {info.circumference:.1f} mm"
    )
    parts = {f"link_{i:02d}": pl.solid for i, pl in enumerate(links)}
    export_glb(parts, "out/glb/cuban_bracelet.glb")

    report = check_chain(links, closed=True)
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

- [ ] **Step 3: Build and render**

```bash
uv run python -m designs.cuban_bracelet.build
uv run python tools/render.py out/glb/cuban_bracelet.glb --outdir out/renders/cuban_bracelet
```

Expected: derived values printed (~22 links, radius ~31.5mm — a ~63mm-diameter bracelet), `chain verification: OK`, STEP exported, 4 PNGs written. (`check_chain` on 22 links takes 1–3 minutes.)

- [ ] **Step 4: Judge the renders against the references**

View all four PNGs with the Read tool next to the step-1 references. Checklist: links read as a flat-lying curb chain (not a cable chain standing on edge); packing density comparable to the reference; V-groove pattern visible down the centerline in the top view; gold material reads as metal in the detail view; no faceting visible (if faceted, lower `linear_deflection` in the GLB export call and re-render). Adjust `params.py` dials (`tilt_deg`, `pitch`, link proportions — stay inside the verified region or re-verify) and repeat step 3 until it reads as a cuban link. Every iteration re-runs verification by construction — an iteration that fails verification never produces a STEP.

- [ ] **Step 5: Commit, then hand off to the user**

```bash
git add designs/
git commit -m "feat: cuban link bracelet benchmark design"
```

Tell the user: the bracelet STEP is at `out/step/cuban_bracelet.step` — import into Plasticity (File → Import). Acceptance (spec): geometry arrives as named, editable NURBS solids and the design reads as a real cuban link. The user is the final judge of both.

---

## Verification at plan level

After all tasks: `uv run pytest -v` → all tests pass (expect ~25; full run takes a few minutes due to booleans + the Blender smoke test). The spec's milestone 1 (pipeline smoke test) is covered by Tasks 1–6; milestones 2–4 by Tasks 7–9+11. Milestone 5 (box clasp) is out of scope for this plan by design.
