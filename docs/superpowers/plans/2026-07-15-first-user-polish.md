# First-User Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix what the first community user hits — a teaching template, a README that shows the hardware pack, cross-platform Blender discovery — with the reviewers' deferred verification minors folded in.

**Architecture:** Rewrite `claudecad/_scaffold/designs/_template` as a spike-verified peg-and-socket fit demonstrating the three core gate patterns; add `find_blender()` (env-strict → PATH → platform globs → how-to-fix error) to `claudecad/render`; land the five verification minors (pin free-leg control, osculation bound, manifold unification, `_unit_axis` dedup, band-sampling skill law); regenerate hardware renders into `docs/images/` and add the README showcase.

**Tech Stack:** build123d 0.11.1, stdlib (`shutil.which`, `glob`), pytest monkeypatching.

## Global Constraints

- Suite is currently **136 passed** — green at every task boundary; no gate is loosened anywhere.
- The scaffolder's rename contract (pinned by `tests/test_scaffolder.py::test_template_strings_renamed`) requires the template's `build.py` to contain the literal strings `designs._template.build`, `out/glb/_template.glb`, and `from claudecad.export import` — the new template keeps all three.
- **Spike-verified (2026-07-15):** the peg-and-socket template builds in ~0.01 s, gates in ~0.04 s; fit gap reads **exactly 0.2000** with the peg seated `FIT_CLEARANCE` above the bore floor (seating it ON the floor reads gap 0.0000 — coplanar contact, the tangency defect class); withdraw-free max 0.0000, lateral-blocked max ≈490. On this machine `shutil.which("blender")` is None and the macOS glob matches both `Blender 4.5 LTS.app` and `Blender.app` — sorted order puts 4.5 LTS first (the verified renderer).
- Skill copies are generated: after ANY `.claude/skills/cad/SKILL.md` edit, run `python3 scripts/sync_skill.py` (CI enforces equality).
- `tests/test_links.py` already imports `check_solid` (line 9) — the unification is a one-line assertion swap.

---

### Task 1: teaching template (peg-and-socket)

**Files:**
- Rewrite: `claudecad/_scaffold/designs/_template/params.py`, `claudecad/_scaffold/designs/_template/build.py`
- Test: existing `tests/test_scaffolder.py` (contract + end-to-end) — no new tests needed; the stamped-build test now exercises the richer gate.

**Interfaces:** none new — the template is data; the scaffolder contract strings (Global Constraints) are the interface.

- [ ] **Step 1: Rewrite `params.py`**

```python
"""<YOUR DESIGN> — every driving dimension, in mm.

Rules (see .claude/skills/cad/SKILL.md): driving params only; derived
values are computed by the library and printed by build.py, never set here.
This starter is a PEG-AND-SOCKET fit — replace it with your design, but
keep the shape: params here, parts + gate in build.py.
"""
BASE_L = 30.0          # base block footprint
BASE_W = 30.0
BASE_H = 14.0
PEG_D = 8.0            # peg diameter
PEG_STICKOUT = 12.0    # how far the peg stands proud of the base top
BORE_DEPTH = 10.0      # socket depth into the base
FIT_CLEARANCE = 0.2    # radial + seat air gap: parts NEVER touch
```

- [ ] **Step 2: Rewrite `build.py`**

```python
"""Build, verify, export <YOUR DESIGN>.

Usage: uv run python -m designs._template.build
The shape of every claudeCAD design: build solids -> ALWAYS write the GLB
-> run the gate -> write STEP ONLY if the gate passes (exit 1 otherwise).

This starter is a PEG-AND-SOCKET fit demonstrating the three core gate
patterns (see the /cad skill's verification laws):
  1. parts clean    — check_solid(...).ok for every part
  2. clearance fit  — zero interference AND a real air gap in a band
  3. mechanism      — a free/blocked differential: the peg withdraws
                      axially (free) but cannot escape sideways (blocked)
"""
import sys

from build123d import Box, Cylinder, Pos

from claudecad.export import export_design, export_glb
from claudecad.verify import (check_solid, clearance, intersection_volume,
                              path_clearance)

from .params import (BASE_H, BASE_L, BASE_W, BORE_DEPTH, FIT_CLEARANCE,
                     PEG_D, PEG_STICKOUT)


def main() -> int:
    # 1) build the solids (library parts or raw build123d)
    bore_floor = BASE_H - BORE_DEPTH
    base = Pos(0, 0, BASE_H / 2) * Box(BASE_L, BASE_W, BASE_H) \
        - Pos(0, 0, BASE_H - BORE_DEPTH / 2 + 0.5) * Cylinder(
            PEG_D / 2 + FIT_CLEARANCE, BORE_DEPTH + 1)
    peg_len = BORE_DEPTH + PEG_STICKOUT
    # seat the peg FIT_CLEARANCE above the bore floor: nothing ever touches
    # (a coplanar face is a defect — see the /cad clearance law)
    peg = Pos(0, 0, bore_floor + FIT_CLEARANCE + peg_len / 2) * Cylinder(
        PEG_D / 2, peg_len)
    parts = {"base": base, "peg": peg}

    # 2) GLB always — the render/preview artifact, even for failures
    export_glb(parts, "out/glb/_template.glb")

    ok = True

    # 3a) parts clean
    for name, s in parts.items():
        r = check_solid(s)
        print(f"{name}: valid={r.is_valid} manifold={r.is_manifold} "
              f"pieces={r.piece_count} volume={r.volume:.1f}")
        ok = ok and r.ok

    # 3b) clearance fit: crisp zero interference AND a real air gap
    iv = intersection_volume(peg, base)
    gap = clearance(peg, base)
    print(f"fit: iv {iv:.4f} (==0), gap {gap:.4f} "
          f"(0 < gap <= {FIT_CLEARANCE})")
    ok = ok and iv == 0.0 and 0 < gap <= FIT_CLEARANCE

    # 3c) the smallest mechanism differential: withdrawing the peg axially
    # is FREE (0 at every station); pushing it sideways is BLOCKED (>0).
    # Note the distances: blocked legs sample the BLOCKING BAND densely
    # (band-scale distance, here one peg diameter), never envelope-scale.
    out_free = path_clearance(peg, base, (0, 0, 1), peg_len + 2, 8)
    lateral = path_clearance(peg, base, (1, 0, 0), PEG_D, 8)
    print(f"withdraw max {max(out_free):.4f} (==0) | "
          f"lateral max {max(lateral):.2f} (>0)")
    ok = ok and max(out_free) == 0.0 and max(lateral) > 0.0

    if not ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1
    export_design(parts, "out/step/_template.step",
                  assembly_label="_template")
    print("exported out/step/_template.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Verify via the scaffolder suite (contract + end-to-end)**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_scaffolder.py -v` then `uv run pytest -q`
Expected: 5 passed (the stamped-build test now runs the peg-and-socket gate — printout shows the fit gap 0.2000 and the differential); full suite 136.

- [ ] **Step 4: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add claudecad/_scaffold/designs/_template
git commit -m "feat: teaching template — peg-and-socket fit with the three gate patterns"
```

---

### Task 2: cross-platform Blender discovery

**Files:**
- Modify: `claudecad/render/__init__.py`
- Test: `tests/test_render_discovery.py` (new)

**Interfaces:**
- Produces: `claudecad.render.find_blender() -> str` — resolution chain: strict `BLENDER_BIN` (set-but-missing raises, never silently ignored) → `shutil.which("blender")` → sorted platform globs (`_PLATFORM_GLOBS`) → `FileNotFoundError` with the fix instructions. `render_glb` calls it in place of the old `os.environ.get("BLENDER_BIN", DEFAULT_BLENDER)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_render_discovery.py`:

```python
import os
import shutil

import pytest

import claudecad.render as render


def test_env_override_strict(monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_BIN", str(tmp_path / "nope"))
    with pytest.raises(FileNotFoundError, match="BLENDER_BIN"):
        render.find_blender()


def test_env_override_accepts_executable(monkeypatch, tmp_path):
    fake = tmp_path / "blender"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    monkeypatch.setenv("BLENDER_BIN", str(fake))
    assert render.find_blender() == str(fake)


def test_path_lookup_wins_over_globs(monkeypatch):
    monkeypatch.delenv("BLENDER_BIN", raising=False)
    monkeypatch.setattr(shutil, "which",
                        lambda name: "/fake/bin/blender"
                        if name == "blender" else None)
    assert render.find_blender() == "/fake/bin/blender"


def test_glob_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("BLENDER_BIN", raising=False)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    fake = tmp_path / "Blender 4.5 LTS.app" / "Contents" / "MacOS"
    fake.mkdir(parents=True)
    (fake / "Blender").write_text("#!/bin/sh\n")
    monkeypatch.setattr(
        render, "_PLATFORM_GLOBS",
        (str(tmp_path / "Blender*.app" / "Contents" / "MacOS" / "Blender"),))
    assert render.find_blender() == str(fake / "Blender")


def test_helpful_error_when_nothing_found(monkeypatch):
    monkeypatch.delenv("BLENDER_BIN", raising=False)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setattr(render, "_PLATFORM_GLOBS", ())
    with pytest.raises(FileNotFoundError, match="BLENDER_BIN=/path/to"):
        render.find_blender()
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_render_discovery.py -v`
Expected: FAIL with `AttributeError: ... has no attribute 'find_blender'`.

- [ ] **Step 3: Implement `find_blender`**

In `claudecad/render/__init__.py`: add `import glob` and `import shutil` to the imports; replace the `DEFAULT_BLENDER = ...` constant with:

```python
_PLATFORM_GLOBS = (
    "/Applications/Blender*.app/Contents/MacOS/Blender",          # macOS
    "C:/Program Files/Blender Foundation/Blender*/blender.exe",   # Windows
    "/usr/bin/blender",                                           # Linux
    "/usr/local/bin/blender",
    "/snap/bin/blender",
    "/opt/blender*/blender",
)


def find_blender() -> str:
    """Resolve the Blender binary. Order: BLENDER_BIN (strict — an explicit
    setting that isn't executable is an error, never silently ignored), then
    PATH, then platform-typical install locations (sorted, so on macOS
    'Blender 4.5 LTS.app' wins over 'Blender.app'), else a how-to-fix
    error."""
    env = os.environ.get("BLENDER_BIN")
    if env:
        if shutil.which(env) or (Path(env).is_file()
                                 and os.access(env, os.X_OK)):
            return env
        raise FileNotFoundError(
            f"BLENDER_BIN={env!r} is set but is not an executable — "
            "fix or unset it")
    on_path = shutil.which("blender")
    if on_path:
        return on_path
    for pattern in _PLATFORM_GLOBS:
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[0]
    raise FileNotFoundError(
        "Blender not found: BLENDER_BIN is unset, no 'blender' on PATH, "
        "and no install at the usual locations. Install Blender or set "
        "BLENDER_BIN=/path/to/blender.")
```

and in `render_glb`, replace the line `blender = os.environ.get("BLENDER_BIN", DEFAULT_BLENDER)` with `blender = find_blender()`.

**Known consumer of the removed constant (verified):** `tests/test_render_smoke.py:10-15` imports `DEFAULT_BLENDER` and re-implements env-or-default for its skipif — and its current logic treats an existing-but-broken `BLENDER_BIN` as present (an old deferred minor). Replace its header block:

```python
from claudecad.render import DEFAULT_BLENDER, render_glb

_blender = os.environ.get("BLENDER_BIN", DEFAULT_BLENDER)
```

with:

```python
from claudecad.render import find_blender, render_glb

try:
    _blender = find_blender()
except FileNotFoundError:
    _blender = None
```

(keep the existing `pytestmark = pytest.mark.skipif(...)` shape, its condition now `_blender is None` — adjust the existing condition expression accordingly; the `reason` string stays). Then confirm no other references: `grep -rn "DEFAULT_BLENDER" --include="*.py" .` → no hits.

- [ ] **Step 4: Run to verify they pass, plus the render smoke**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_render_discovery.py tests/test_render_smoke.py -v` then `uv run pytest -q`
Expected: discovery 5 passed; smoke unchanged; full suite 141 (136 + 5).

- [ ] **Step 5: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add claudecad/render/__init__.py tests/test_render_discovery.py
git commit -m "feat: cross-platform Blender discovery (env-strict -> PATH -> globs)"
```

---

### Task 3: folded verification minors

**Files:**
- Modify: `claudecad/hardware/snapbox.py` (+`base_through_bored`), `designs/snapbox/build.py` (free-leg gate line), `claudecad/hardware/bearing.py` (osculation bound), `claudecad/verify.py` (`_unit_axis` dedup), `tests/test_links.py:74` (manifold unification), `.claude/skills/cad/SKILL.md` (band-sampling law) + `python3 scripts/sync_skill.py`
- Test: `tests/test_snapbox.py`, `tests/test_bearing.py` (append)

**Interfaces:**
- Produces: `claudecad.hardware.snapbox.base_through_bored(p) -> Solid` (the pin free-leg control). No other public API changes.

- [ ] **Step 1: Write the two failing tests**

Append to `tests/test_snapbox.py`:

```python
def test_pin_axial_free_leg_control():
    """Causality control for pin capture: the axial escape is BLOCKED by the
    shipped blind-bored base and FREE through a through-bored variant — the
    blind ends are WHY the pin stays (outer_race_eccentric pattern)."""
    from claudecad.hardware.snapbox import (base_through_bored,
                                            pin_escape_distance)
    from claudecad.verify import path_clearance
    p = SnapBoxParams()
    pin = hinge_pin(p)
    d = pin_escape_distance(p)
    l = lid(p, "relaxed")
    blocked = max(path_clearance(pin, base(p) + l, (1, 0, 0), d, 7))
    free = max(path_clearance(pin, base_through_bored(p) + l, (1, 0, 0),
                              d, 7))
    assert blocked > 0.0
    assert free == 0.0
```

Append to `tests/test_bearing.py` (inside `test_params_validation` add one clause, or as its own test — use its own):

```python
def test_osculation_upper_bound():
    # deep-groove conformity runs ~0.515-0.53; a looser groove abandons
    # raceway guidance and only REST_MAX_GAP would catch it at gate time
    with pytest.raises(ValueError, match="osculation"):
        BearingParams(osculation=0.6)
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_snapbox.py::test_pin_axial_free_leg_control tests/test_bearing.py::test_osculation_upper_bound -v`
Expected: ImportError (`base_through_bored`) and DID-NOT-RAISE respectively.

- [ ] **Step 3: Implement the four code minors**

(a) Add to `claudecad/hardware/snapbox.py` (after `hinge_pin`):

```python
def base_through_bored(p: SnapBoxParams) -> Solid:
    """FREE-LEG CONTROL for the pin's axial capture: the shipped base with
    the hinge bore cut clear through the outer knuckles (blind ends
    removed). The pin's axial escape must run FREE through this variant and
    BLOCKED through the shipped base — pinning that the blind ends are what
    retain the pin (prove causality, not coincidence)."""
    hc = p.hinge_center
    span = 2 * abs(_KNUCKLE_XC_BASE[0]) + p.knuckle_w + 2.0
    return base(p) - (Pos(0, hc[1], hc[2]) * Rot(Y=90)
                      * Cylinder(p.bore_radius, span))
```

And in `designs/snapbox/build.py`, extend gate check 6 (pin capture): after the existing `caps` block, add:

```python
    free_ctrl = max(path_clearance(pin, base_through_bored(P) + l_relaxed,
                                   (1, 0, 0), d, 7))
    print(f"pin free-leg control (through-bored base): {free_ctrl:.6f} (==0)")
    ok = ok and free_ctrl == 0.0
```

with `base_through_bored` added to the `claudecad.hardware.snapbox` import list.

(b) In `claudecad/hardware/bearing.py` `__post_init__`, after the `rest_gap <= 0` check:

```python
        if self.osculation > 0.54:
            raise ValueError(
                f"osculation={self.osculation} exceeds 0.54: deep-groove "
                "conformity runs ~0.515-0.53; a looser groove abandons "
                "raceway guidance"
            )
```

(c) In `tests/test_links.py:74`, replace `assert cut.is_manifold          # seam membranes surface here if present` with `assert check_solid(cut).is_manifold  # seam membranes surface here if present` (`check_solid` is already imported at line 9).

(d) In `claudecad/verify.py`, add above `path_clearance`:

```python
def _unit_axis(axis) -> Vector:
    """Validate and normalize a sweep axis (shared by the travel and screw
    gates)."""
    a = Vector(*axis) if not isinstance(axis, Vector) else axis
    if a.length == 0:
        raise ValueError(f"axis must be nonzero, got {tuple(a)}")
    return a.normalized()
```

and in BOTH `path_clearance` and `screw_clearance`, replace their three-line axis blocks (`a = Vector(*axis) ...` / `if a.length == 0: raise ...` / `a = a.normalized()`) with `a = _unit_axis(axis)`. The existing zero-axis guard tests pin the behavior.

- [ ] **Step 4: The skill law addendum + sync**

In `.claude/skills/cad/SKILL.md`, at the end of the **Mechanisms** law bullet (after "ALWAYS on the shipped (post-finishing) geometry."), append:

```
  Blocked-leg sweeps must sample the BLOCKING BAND densely (band-scale
  distances — wide stations straddle a thin feature and pass on a sliver);
  envelope-scale distances are for free legs only.
```

Then: `python3 scripts/sync_skill.py` (two `synced` lines) and `python3 scripts/sync_skill.py --check` (exit 0).

- [ ] **Step 5: Run everything**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_snapbox.py tests/test_bearing.py tests/test_links.py tests/test_verify.py -q` then `uv run pytest -q` and `uv run python -m designs.snapbox.build 2>&1 | tail -4`
Expected: targeted files green; full suite 143 (141 + 2); snapbox gate green with the new free-leg control line.

- [ ] **Step 6: Commit (and clear the filed chip)**

```bash
cd /Users/mike/code/claudeCAD
git add -A
git commit -m "fix: fold reviewers' deferred minors — free-leg control, osculation
bound, one manifold notion, axis dedup, band-sampling law"
```

The controller dismisses background chip `task_00d3408d` (test_links unification — superseded by (c)).

---

### Task 4: hardware renders + README showcase

**Files:**
- Create: `docs/images/bolt.png`, `docs/images/bearing-608.png`, `docs/images/snapbox.png` (fresh renders of current geometry)
- Modify: `README.md`

**Interfaces:** none — docs. Requires Blender locally (renders are design-acceptance artifacts; CI never runs them).

- [ ] **Step 1: Re-render current geometry and pick views**

```bash
cd /Users/mike/code/claudeCAD
uv run python -m designs.bolt.build && uv run python -m designs.bearing_608.build && uv run python -m designs.snapbox.build
uv run claudecad render out/glb/bolt.glb --outdir out/renders/bolt
uv run claudecad render out/glb/bearing_608.glb --outdir out/renders/bearing_608
uv run claudecad render out/glb/snapbox.glb --outdir out/renders/snapbox
cp out/renders/bolt/front.png docs/images/bolt.png
cp out/renders/bearing_608/persp.png docs/images/bearing-608.png
cp out/renders/snapbox/persp.png docs/images/snapbox.png
```

View all three copied PNGs with the Read tool and confirm they show current geometry (continuous-spiral thread; balls visible in the raceway; hinged box with latch) before committing — renders are judged, never assumed.

- [ ] **Step 2: README section**

In `README.md`, insert immediately before `## Developing claudeCAD itself`:

```markdown
## What the gates can prove

The hardware pack is the generality benchmark — three mechanism classes,
each forcing its own verification law (all encoded in the `/cad` skill):

| ![M8 bolt](docs/images/bolt.png) | ![608 bearing](docs/images/bearing-608.png) | ![snap enclosure](docs/images/snapbox.png) |
|---|---|---|
| **M8×1.25 bolt + nut** — thread mesh proven by the exact 2D axial-section clearance (helical symmetry): a real air gap on the true pitch, jams under axial shift and wrong pitch. | **608 ball bearing** — the 7-ball ring swept as one compound over a single 360/7° symmetry period; an eccentric-groove negative control proves the gate detects broken axisymmetry. | **Hinged snap box** — off-origin partial-arc swing gates, a same-parameter travel-limit differential (free ≤100°, blocked ≥105°), and snap retention as a two-state differential. |
```

- [ ] **Step 3: Verify + commit**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest -q` (143 passed — unchanged by docs) and view the rendered README section for table sanity.

```bash
git add docs/images/bolt.png docs/images/bearing-608.png docs/images/snapbox.png README.md
git commit -m "docs: hardware-pack showcase — three mechanism classes, three laws"
```

---

## Notes for the implementer

- **Template contract:** the three literal strings in Global Constraints must survive any template edit — `tests/test_scaffolder.py::test_template_strings_renamed` is the tripwire.
- **`find_blender` env strictness is deliberate:** a set-but-broken `BLENDER_BIN` raises instead of falling through — silently ignoring a user's explicit setting is worse than failing.
- **No gate loosening:** `_unit_axis` and the manifold unification are refactors pinned by existing tests; the osculation bound and free-leg control only ADD assertions.
- Renders (Task 4) need local Blender; everything else runs anywhere.
