# Open-Source Release + Generality Iteration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship claudeCAD as a public GitHub repo positioned as a general verification-first CAD system, then land the generality iteration (clearance verification, assembly.relieve, design template, carabiner domain pack) on the live repo.

**Architecture:** Stage 1 is docs/CI/packaging around unchanged library code, ending in `gh repo create mdbritt/claudecad --public` + push + verified-green Actions run. Stage 2 adds domain-neutral capabilities: `verify.clearance` (+ optional near-contact band in check_chain), `claudecad/assembly.py::relieve`, `designs/_template/`, and `claudecad/hardware/` with a spring-gate carabiner proven by open/closed differentials.

**Tech Stack:** Existing (build123d 0.11.x, uv, pytest, Blender-optional) + GitHub Actions (ubuntu-latest, astral-sh/setup-uv).

**Spec:** `docs/superpowers/specs/2026-07-13-open-source-release-design.md`

## Global Constraints

- Repo root `/Users/mike/code/claudeCAD`; run everything from there; branch off `main` (`feature/open-source-release`); the PUBLISH task is the only irreversible step and runs only after Tasks 1–5 are reviewed.
- **Positioning is binding for every doc written**: the system (loop + verification laws + tools + /cad skill) is the product; `claudecad/jewelry/` is a domain pack; the cuban bracelet is the benchmark that battle-tested the method. No doc may present the project as a jewelry/chain library.
- License Apache-2.0, copyright 2026 Mike Britt. GitHub account: `mdbritt`; repo name `claudecad`; public.
- Never weaken a verification check. All dims mm. Library modules pure; `tools/` only does I/O.
- Spike-verified facts this plan uses: `Shape.distance_to(other) -> float` returns exact minimum distance (10.0 for a 10mm gap, 0.0 touching); the stray tracked scratch file is exactly `.superpowers/sdd/task-3-report.md`; the relief helper to promote lives in `designs/cuban_bracelet/build.py` (`_expand` at ~line 31, `_relieve` closure at ~line 96).
- CI must pass WITHOUT Blender: the two render tests in `tests/test_render_smoke.py` gain a module-level skip marker keyed on BLENDER_BIN resolution (real binary present). Everything else runs.
- Commit after every task with the given message.

---

### Task 1: Hygiene — untrack scratch, pristine pytest, import smoke

**Files:**
- Modify: `pyproject.toml` (append to `[tool.pytest.ini_options]`)
- Create: `tests/test_designs_import.py`
- Untrack: `.superpowers/sdd/task-3-report.md`

**Interfaces:** Produces a pristine `uv run pytest` (0 warnings) and a tracked-file set with no scratch.

- [ ] **Step 1: Untrack the scratch file**

```bash
git rm --cached .superpowers/sdd/task-3-report.md
git status --short   # expect one 'D' staged entry; the file stays on disk
```

- [ ] **Step 2: Write the failing import-smoke test**

`tests/test_designs_import.py`:
```python
"""Fast smoke: every design module imports and exposes main().

Catches bitrot in designs/ (which the heavy build gates only catch when
someone runs a full build)."""
import importlib

import pytest

DESIGNS = ["designs.cuban_bracelet.build", "designs.cuban_bracelet.params",
           "designs.cuban_bracelet.probe"]


@pytest.mark.parametrize("module", DESIGNS)
def test_design_module_imports(module):
    mod = importlib.import_module(module)
    if module.endswith(".build"):
        assert callable(getattr(mod, "main"))
```

- [ ] **Step 3: Run — the test should already pass (it's a guard, not TDD red)**

Run: `uv run pytest tests/test_designs_import.py -v`
Expected: 3 passed. If any import fails, that IS a live bug — report it, do not paper over.

- [ ] **Step 4: Silence the upstream lib3mf noise (filter only that warning)**

In `pyproject.toml`, extend the existing `[tool.pytest.ini_options]` table:
```toml
filterwarnings = [
    "error",
    # upstream build123d dependency (lib3mf) emits ctypes DeprecationWarnings
    # on Python 3.13+; not ours to fix, tracked since v1
    "ignore::DeprecationWarning:lib3mf",
]
```
NOTE: `"error"` promotes all OTHER warnings to failures — the honest version
of "pristine". If the suite now fails on a warning that is OURS, fix that
warning at its source (do not add ignores for first-party code). If it fails
on a different upstream module, add a narrowly-scoped ignore with a comment,
same pattern as lib3mf. If the lib3mf filter doesn't match (warning module
attribution can vary), use the message form:
`"ignore:.*:DeprecationWarning:lib3mf.*"` — verify by running.

- [ ] **Step 5: Full suite — pristine**

Run: `uv run pytest -q`
Expected: `76 passed` (73 + 3 new) and **no warnings summary line at all**.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: untrack scratch, pristine warnings policy, designs import smoke"
```

---

### Task 2: /cad skill restructure + CONTRIBUTING

**Files:**
- Rewrite: `.claude/skills/cad/SKILL.md`
- Create: `CONTRIBUTING.md`

**Interfaces:** Produces the system-first skill and contribution contract that README (Task 5) links to.

- [ ] **Step 1: Rewrite `.claude/skills/cad/SKILL.md`** — same frontmatter name/description shape, restructured body. Full replacement content:

```markdown
---
name: cad
description: Use when designing, modifying, rendering, or exporting any CAD piece in this repo — defines the build → verify → render → iterate → export loop and its non-negotiable rules.
---

# CAD design loop

Parametric designs live in `designs/<name>/` as `params.py` (every dimension,
mm, single source of truth) + `build.py` (composes library parts, verifies,
writes GLB/STEP to `out/`). Domain-neutral geometry lives in `claudecad/`
(`core/`, `verify.py`, `assembly.py`); domain packs (e.g. `jewelry/`,
`hardware/`) hold reusable parts for a design family. `tools/` is the only
layer that touches disk/Blender.

## The loop

1. Edit `designs/<name>/params.py` (or library code for new components).
2. `uv run python -m designs.<name>.build` — builds, **verifies**, writes
   `out/glb/<name>.glb`, and (only if verification passes) `out/step/<name>.step`.
3. `uv run python tools/render.py out/glb/<name>.glb --outdir out/renders/<name>`
4. View every PNG with the Read tool. Judge against reference photos of the
   real-world piece — fetch references, don't design from memory.
5. Iterate 1–4 until the renders read true. Then hand `out/step/<name>.step`
   to the user (Plasticity: File → Import; parts arrive named). For quick
   3D inspection there's a bundled localhost STEP/GLB viewer —
   `tools/step_viewer/` (see its fetch_libs.sh; serve repo root on :8123).

## Non-negotiable rules

- All dimensions in millimeters, defined only in `params.py`. Derived values
  are computed by the library and printed, never set.
- Never show the user renders of geometry that failed verification; never
  export STEP that fails verification (build.py enforces; do not bypass).
- Verification is ground truth; renders are not evidence. When a check
  fails, adjust parameters or geometry — never the check.
- New components are pure functions in a domain pack with pytest coverage.

## Verification laws (domain-neutral)

- **Interlock** is proven by the Gauss linking number of discretized closed
  centerlines (`verify.linking_number`); **non-contact** by boolean
  intersection == 0 (`verify.intersection_volume`, bbox-disjoint fast path);
  chains of interlocking parts by `verify.check_chain(items, closed,
  interlock_depth)`.
- **Mechanisms** are proven with CONSTRUCTED STATES, never simulation:
  build each functional state as its own solid and gate on differentials —
  insertion = `verify.path_clearance` all-zero along the travel axis;
  lock = blocked state interferes at the station while the freed state
  clears; guards = the blocked motion's station intersects the guard part.
  Functional gates run in the part's LOCAL frame (rigid-invariant) and
  ALWAYS on the shipped (post-finishing) geometry.
- **Attachment** is proven by linking number against a closed loop through
  the mounting circuit — the loop must genuinely cross the other part's
  plane (a coplanar loop can never link).

## Construction laws (OCCT, hard-won — see the dated specs for evidence)

- Twisted closed tubes: ONLY two overlapping half-loop ruled lofts, fused.
  Forbidden (all gauntlet-proven broken): sweep() in any frame mode,
  ruled=False lofts, single closed lofts with first==last section,
  Shell/Solid reassembly, Edge.trim on sweep spines.
- Cavities are subtracted blocks, never OCCT shell/thicken.
- Prefer analytic (Box/Cylinder/planar-sweep) construction; `is_valid` is
  necessary but NOT sufficient — boolean-robustness is what the gates test.
- Overlapping unions in generic position are robust; coincident-face fuses
  are degenerate and forbidden.

## Domain notes: jewelry (accumulated benchmark learnings)

- Chains: chirality — twisted links are handed; chains alternate link
  handedness (`chains._link_bases`) or the two junction types diverge.
  Dense chains may thread depth 2 (`interlock_depth`). Real cuban pitch ≈
  0.49 × link length; the look comes from flat lie + diamond-cut facets.
- `finishing.diamond_cut` grinds an assembled chain flat (slab intersection,
  severing caught by piece_count); relief slots via `assembly.relieve`.

## Blender renderer

`tools/render.py` needs Blender; default binary is
"/Applications/Blender 4.5 LTS.app/Contents/MacOS/Blender", override with
env `BLENDER_BIN`. Views: persp, top, front, detail. Renders are optional
for library development (CI runs without Blender); they are required for
design acceptance.
```

(Note: `assembly.relieve` is created in Task 8 — the skill documents the
post-stage-2 state; acceptable because the skill ships publicly only with
this same branch. `verify.clearance`/near-contact is documented in Task 7's
step, not here, to keep this file stable.)

- [ ] **Step 2: Create `CONTRIBUTING.md`**

```markdown
# Contributing

This repo runs on a spec → plan → gate discipline. The short version:

1. **Specs and plans are first-class.** Nontrivial changes start as a design
   doc in `docs/superpowers/specs/` and an implementation plan in
   `docs/superpowers/plans/`. The dated documents already there carry the
   evidence for every load-bearing decision (including the OCCT construction
   laws) — read the relevant ones before re-deriving or re-litigating.
2. **Verification is ground truth.** Geometry claims are proven by the gates
   (linking number, boolean intersection, constructed-state differentials) —
   never by renders or eyeballing. PRs must keep `uv run pytest` green and
   may NEVER weaken a check to make something pass.
3. **Designs verify before they export.** `designs/<name>/build.py` writes
   STEP only when its full gate passes; keep that property.
4. **New domains come as domain packs**: a `claudecad/<domain>/` module of
   pure part functions with pytest coverage, plus an example under
   `designs/`. `claudecad/jewelry/` and its cuban-bracelet benchmark are the
   worked example of the pattern.
5. **Local setup**: `uv sync`, `uv run pytest`. Blender is optional (render
   tests skip without it); see README for the render loop.
```

- [ ] **Step 3: Verify the skill frontmatter still parses**

Run: `uv run python -c "
import pathlib, re
t = pathlib.Path('.claude/skills/cad/SKILL.md').read_text()
m = re.match(r'^---\n(.*?)\n---\n', t, re.S)
assert m and 'name: cad' in m.group(1)
print('SKILL.md OK')
"`
Expected: `SKILL.md OK`

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/cad/SKILL.md CONTRIBUTING.md
git commit -m "docs: system-first /cad skill restructure and contributing guide"
```

---

### Task 3: LICENSE + CI workflow + Blender-optional render tests

**Files:**
- Create: `LICENSE`, `.github/workflows/ci.yml`
- Modify: `tests/test_render_smoke.py` (top)

**Interfaces:** Produces the CI contract Task 6 verifies on GitHub.

- [ ] **Step 1: LICENSE (canonical Apache-2.0 text)**

```bash
curl -fsSL https://www.apache.org/licenses/LICENSE-2.0.txt -o LICENSE
grep -c "Apache License" LICENSE   # expect >= 1
```
Then append the standard copyright notice block is NOT required by Apache-2.0
in LICENSE itself; instead add to `pyproject.toml` under `[project]`:
```toml
license = "Apache-2.0"
authors = [{ name = "Mike Britt" }]
```

- [ ] **Step 2: Blender-optional marker in `tests/test_render_smoke.py`** — add at the top, after the module docstring:

```python
import os
import shutil
from pathlib import Path

import pytest

from tools.render import DEFAULT_BLENDER

_blender = os.environ.get("BLENDER_BIN", DEFAULT_BLENDER)
pytestmark = pytest.mark.skipif(
    not (Path(_blender).exists() or shutil.which(_blender)),
    reason="Blender not available (set BLENDER_BIN); render loop is optional",
)
```
(Keep existing imports; dedupe as needed.)

- [ ] **Step 3: Verify the skip works both ways**

Run: `uv run pytest tests/test_render_smoke.py -v` → 2 passed (Blender present locally).
Run: `BLENDER_BIN=/nonexistent uv run pytest tests/test_render_smoke.py -v` → 2 skipped.

- [ ] **Step 4: CI workflow** `.github/workflows/ci.yml`:

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync --locked
      - run: uv run pytest -q
```

- [ ] **Step 5: Full local suite still green**

Run: `uv run pytest -q`
Expected: 74 passed, 2 skipped OR 76 passed (depending on local Blender) — record which.

- [ ] **Step 6: Commit**

```bash
git add LICENSE pyproject.toml .github tests/test_render_smoke.py
git commit -m "chore: Apache-2.0 license, CI workflow, Blender-optional render tests"
```

---

### Task 4: simple_curb example

**Files:**
- Create: `designs/simple_curb/params.py`, `designs/simple_curb/build.py`
- Modify: `tests/test_designs_import.py` (add the new modules to DESIGNS)

**Interfaces:** Consumes `LinkParams`, `ChainParams`, `closed_loop`, `check_chain`, `export_design`, `export_glb` — all existing.

- [ ] **Step 1: Write the design**

`designs/simple_curb/params.py`:
```python
"""Simple planar curb bracelet — the gentle-entry example (~15 lines).

Uses the v1-verified planar config: see ChainParams' docstring for the
sweep evidence (pitch 10/tilt 55 is the verified planar combination).
"""
from claudecad.jewelry.chains import ChainParams
from claudecad.jewelry.links import LinkParams

TARGET_CIRCUMFERENCE = 200.0
CHAIN = ChainParams(link=LinkParams(length=20.0, width=14.0, wire_d=4.0),
                    tilt_deg=55.0, pitch=10.0)
```

`designs/simple_curb/build.py`:
```python
"""Build, verify, export the simple curb bracelet.
Usage: uv run python -m designs.simple_curb.build
"""
import sys

from claudecad.jewelry.chains import closed_loop
from claudecad.verify import check_chain
from tools.export import export_design, export_glb

from .params import CHAIN, TARGET_CIRCUMFERENCE


def main() -> int:
    links, info = closed_loop(CHAIN, TARGET_CIRCUMFERENCE)
    print(f"derived: {info.count} links, radius {info.radius:.2f} mm")
    parts = {f"link_{i:02d}": pl.solid for i, pl in enumerate(links)}
    export_glb(parts, "out/glb/simple_curb.glb")
    report = check_chain(links, closed=True)
    print(report.summary())
    if not report.ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1
    export_design(parts, "out/step/simple_curb.step", assembly_label="simple_curb")
    print("exported out/step/simple_curb.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Extend the import smoke** — add `"designs.simple_curb.build"`, `"designs.simple_curb.params"` to `DESIGNS` in `tests/test_designs_import.py`.

- [ ] **Step 3: Run the example end-to-end**

Run: `uv run python -m designs.simple_curb.build` (timeout generously; ~1–3 min)
Expected: derived 20 links, `chain verification: OK (20 solids, 190 pairs checked)`, STEP exported. Paste the output in your report.

- [ ] **Step 4: Tests**

Run: `uv run pytest tests/test_designs_import.py -q` → 5 passed.

- [ ] **Step 5: Commit**

```bash
git add designs/simple_curb tests/test_designs_import.py
git commit -m "feat: simple_curb gentle-entry example design"
```

---

### Task 5: README + hero images + quickstart dry-run

**Files:**
- Create: `README.md`, `docs/images/bracelet-top.png`, `docs/images/bracelet-detail.png`, `docs/images/clasp-top.png`

**Interfaces:** Consumes everything shipped; links to CONTRIBUTING.md (Task 2) and the skill.

- [ ] **Step 1: Images** — copy the current renders (they are the clasp-era set):

```bash
mkdir -p docs/images
cp out/renders/cuban_bracelet/top.png docs/images/clasp-top.png
cp out/renders/cuban_bracelet/persp.png docs/images/bracelet-persp.png
cp out/renders/cuban_bracelet/detail.png docs/images/bracelet-detail.png
ls -la docs/images/
```
(If any source is missing, re-render: `uv run python tools/render.py out/glb/cuban_bracelet.glb --outdir out/renders/cuban_bracelet`.)

- [ ] **Step 2: Write `README.md`** — full content (positioning is binding):

````markdown
# claudeCAD

[![ci](https://github.com/mdbritt/claudecad/actions/workflows/ci.yml/badge.svg)](https://github.com/mdbritt/claudecad/actions/workflows/ci.yml)
[![license](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**A verification-first parametric CAD workspace built for designing with
[Claude Code](https://claude.com/claude-code).** You describe a piece; the
model writes parametric [build123d](https://github.com/gumyr/build123d)
code; geometry ships only after machine-checkable proofs pass — topological
interlock, zero-interpenetration, working mechanisms — and lands in your CAD
app (tested with Plasticity) as named, editable NURBS via STEP.

![bracelet](docs/images/bracelet-persp.png)

## Why this exists

LLMs are good at writing parametric geometry and bad at knowing when it's
wrong. claudeCAD's answer is a design loop where **verification is ground
truth and renders are not evidence**:

1. Dimensions live in one `params.py` per design.
2. `uv run python -m designs.<name>.build` builds solids and runs the gate:
   - **interlock** proven by the Gauss linking number of part centerlines,
   - **clearance** proven by exact boolean intersection (must be 0),
   - **mechanisms** proven by constructed states — e.g. a clasp tongue is
     built in relaxed AND compressed states; the gate asserts the compressed
     state slides free while the relaxed state is blocked (that differential
     *is* the click),
   - a failed gate blocks STEP export, period.
3. Headless Blender renders gold studio shots for the human judgment pass.
4. STEP export preserves part names for your CAD app's outliner.

The dated design docs in [`docs/superpowers/`](docs/superpowers/) carry the
evidence trail for every load-bearing decision — including OCCT construction
laws that took real adversarial testing to establish (why twisted closed
tubes must be built as overlapping half-loop ruled lofts; why `is_valid` is
necessary but nowhere near sufficient).

## Quickstart

```bash
git clone https://github.com/mdbritt/claudecad && cd claudecad
uv sync
uv run pytest                              # full verification suite
uv run python -m designs.simple_curb.build # build + verify a bracelet
```

View the result three ways:
- **Your CAD app**: import `out/step/simple_curb.step` (named parts).
- **Bundled web viewer**: `tools/step_viewer/fetch_libs.sh` once, then
  `python3 -m http.server 8123` from the repo root and open
  `http://localhost:8123/tools/step_viewer/?model=/out/step/simple_curb.step`.
- **Renders** (needs Blender, `BLENDER_BIN` to override the default path):
  `uv run python tools/render.py out/glb/simple_curb.glb --outdir out/renders/simple_curb`

## Using it with Claude Code

The repo ships a project skill (`.claude/skills/cad/SKILL.md`) that teaches
Claude the loop and its non-negotiable rules (mm-only params, never render
unverified geometry, never weaken a check, constructed-state mechanism
proofs). Open the repo in Claude Code and ask for a design; the skill does
the rest. Start a new piece from `designs/_template/`.

## What's here

```
claudecad/            domain-neutral core
  core/               exact centerline math (planar + twisted)
  verify.py           the gate: linking number, intersection, path clearance
  assembly.py         assembly finishing (relief cuts)
  jewelry/            DOMAIN PACK: links, chains, clasps, diamond-cut
  hardware/           DOMAIN PACK: carabiner (spring gate)
designs/              examples — each is params.py + build.py with a gate
tools/                STEP/GLB export, Blender renderer, web STEP viewer
docs/superpowers/     the evidence trail (specs + plans, dated)
```

## The benchmark

The system was battle-tested by designing a Miami cuban bracelet end to end
— twisted chirality-alternating links, chain-level diamond-cut, and a fully
functional box clasp (hinged safety latches, folded-spring tongue whose
click is *proven*, statically, by the relaxed-vs-compressed differential).

![clasp](docs/images/clasp-top.png)
![detail](docs/images/bracelet-detail.png)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Short version: spec → plan → gate;
never weaken a check; new domains come as domain packs.

## License

Apache-2.0 — see [LICENSE](LICENSE).
````

NOTE: `designs/_template/`, `claudecad/assembly.py`, `claudecad/hardware/`
ship in stage 2 of THIS SAME branch before publish? NO — publish happens at
Task 6, before stage 2. Therefore the README at publish time must not
reference not-yet-existing paths: WRITE THE README WITHOUT the
`assembly.py`, `hardware/`, and `_template` lines, and Task 11 (cleanups)
updates the README when those land. Concretely: in the "What's here" tree
omit the `assembly.py` and `hardware/` lines; in "Using it with Claude
Code" end the paragraph at "the skill does the rest." Task 2's SKILL.md
references `assembly.relieve` in its domain notes — adjust that one line in
this task to say "relief slots via the benchmark's relieve helper (assembly
promotion planned)" and Task 8 restores it. Keep both edits in this task's
commit.

- [ ] **Step 3: Quickstart dry-run** — execute the README's own commands in a
scratch clone to prove them:

```bash
git clone /Users/mike/code/claudeCAD /tmp/claudecad-dryrun && cd /tmp/claudecad-dryrun
uv sync && uv run pytest -q
uv run python -m designs.simple_curb.build
cd /Users/mike/code/claudeCAD && rm -rf /tmp/claudecad-dryrun
```
Expected: suite green (2 render skips if no BLENDER_BIN in the env), build OK. Paste outputs.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/images .claude/skills/cad/SKILL.md
git commit -m "docs: system-first README with verified quickstart and hero renders"
```

---

### Task 6: Publish (IRREVERSIBLE — user pre-approved)

**Files:** none (remote operations)

- [ ] **Step 1: Merge the release branch to main** (controller does this via the normal review flow BEFORE this task runs; this task starts on main).

- [ ] **Step 2: Create and push**

```bash
gh repo create mdbritt/claudecad --public --source . --push \
  --description "Verification-first parametric CAD for designing with Claude Code (build123d + provable geometry gates)"
git remote -v   # expect origin -> github.com/mdbritt/claudecad
```

- [ ] **Step 3: Verify CI green on the real run**

```bash
gh run watch --exit-status || gh run list --limit 3
gh run list --limit 1
```
Expected: the push-triggered `ci` run concludes `success`. If it fails, fix
forward (the failure is real — likely env-specific; diagnose, commit, push,
re-verify). Do not delete the repo to hide a red run.

- [ ] **Step 4: Confirm the badge renders**

```bash
gh api repos/mdbritt/claudecad --jq '.html_url, .visibility'
```
Expected: URL + "public". Report the URL.

---

### Task 7: verify.clearance + near-contact band (stage 2 begins)

**Files:**
- Modify: `claudecad/verify.py`, `tests/test_verify.py`

**Interfaces:**
- Produces: `clearance(a, b) -> float` (exact minimum distance; 0.0 when touching or penetrating — pair with `intersection_volume` to distinguish); `check_chain(..., max_gap: float | None = None)` — when set, ADJACENT pairs must additionally satisfy `clearance <= max_gap` (near-contact band); failure message carries the measured gap. `PairCheck` gains `gap: float | None = None`.

- [ ] **Step 1: Failing tests (append to `tests/test_verify.py`)**

```python
from claudecad.verify import clearance


def test_clearance_exact_distances():
    assert clearance(Box(10, 10, 10), Pos(20, 0, 0) * Box(10, 10, 10)) == pytest.approx(10.0, abs=1e-9)
    assert clearance(Box(10, 10, 10), Pos(10, 0, 0) * Box(10, 10, 10)) == pytest.approx(0.0, abs=1e-9)


def test_check_chain_max_gap_flags_loose_neighbors():
    """Hopf pair is linked but its tubes sit ~1.8mm apart at closest
    approach (R=10 circles offset 10, minor 1.5: min centerline distance
    ~4.8mm... measured, not assumed: assert against the measured value)."""
    items = _hopf_tori()
    measured = clearance(items[0][0], items[1][0])
    assert measured > 0.0
    tight = check_chain(items, max_gap=measured + 0.5)
    assert tight.ok, tight.failures()
    strict = check_chain(items, max_gap=measured / 2)
    assert not strict.ok
    assert any("gap" in f for f in strict.failures())
```

- [ ] **Step 2: RED**

Run: `uv run pytest tests/test_verify.py -v` → new tests FAIL (ImportError).

- [ ] **Step 3: Implement**

In `claudecad/verify.py`:
```python
def clearance(a, b) -> float:
    """Exact minimum distance between two shapes (0.0 if touching or
    penetrating — combine with intersection_volume to distinguish)."""
    return float(a.distance_to(b))
```
`PairCheck`: the max_gap threshold is not a PairCheck field — the VERDICT is
encoded at construction. Add fields `gap: float | None = None` (measured)
and `gap_ok: bool = True` (computed in `check_chain`):

```python
@dataclass(frozen=True)
class PairCheck:
    i: int
    j: int
    adjacent: bool
    intersection: float
    linking: float
    adjacent_distance: int = 0
    gap: float | None = None
    gap_ok: bool = True

    @property
    def ok(self) -> bool:
        if self.intersection > 0.0:
            return False
        if not self.gap_ok:
            return False
        return self.is_linked if self.adjacent else not self.is_linked
```

In `check_chain(items, closed=False, interlock_depth=1, max_gap=None)`:
compute for adjacent pairs only (when `max_gap is not None`):
```python
            g = None
            g_ok = True
            if max_gap is not None and dist <= interlock_depth:
                g = clearance(si, sj)
                g_ok = g <= max_gap
            pairs.append(PairCheck(i, j, dist <= interlock_depth, inter,
                                   linking_number(ci, cj), dist, g, g_ok))
```
And in `ChainReport.failures`, after the interlock messages:
```python
            if not p.gap_ok:
                msgs.append(
                    f"links {p.i},{p.j}: gap {p.gap:.3f} mm exceeds max_gap"
                )
```
Validation: `max_gap <= 0` raises ValueError with the value.
(Also update the `check_chain` docstring: near-contact band semantics —
touching (0.0) up to max_gap passes; penetration is still caught by the
intersection check.)

- [ ] **Step 4: GREEN + no regressions**

Run: `uv run pytest tests/test_verify.py -q` then `uv run pytest -q` — all green
(default `max_gap=None` leaves every existing caller bit-identical).

- [ ] **Step 5: Commit**

```bash
git add claudecad/verify.py tests/test_verify.py
git commit -m "feat: exact clearance primitive and near-contact band in chain checks"
```

---

### Task 8: assembly.relieve promotion

**Files:**
- Create: `claudecad/assembly.py`, `tests/test_assembly.py`
- Modify: `designs/cuban_bracelet/build.py` (use the library), `.claude/skills/cad/SKILL.md` (restore the assembly.relieve mention per Task 5's note)

**Interfaces:**
- Produces: `expand(solid, delta) -> Solid` (solid grown ~delta by unioning axis-translated copies — READ the current `_expand` in designs/cuban_bracelet/build.py and port it faithfully including its docstring caveat about diagonal coverage) and `relieve(target, cutters, clearance) -> Solid` (subtract each cutter expanded by clearance, then the exact cutters; ValueError with values if clearance < 0 or cutters empty; the two-tier strategy and WHY it exists — coarse expanded cut + exact cut to kill slivers — ports from build.py's `_relieve`).

- [ ] **Step 1: Failing tests**

`tests/test_assembly.py`:
```python
import pytest
from build123d import Box, Pos

from claudecad.assembly import expand, relieve
from claudecad.verify import check_solid, clearance, intersection_volume


def test_expand_grows_in_axis_directions():
    e = expand(Box(10, 10, 10), 1.0)
    bb = e.bounding_box()
    assert bb.max.X - bb.min.X == pytest.approx(12.0, abs=1e-6)
    assert check_solid(e).ok


def test_relieve_cuts_clearance_pocket():
    target = Box(30, 30, 30)
    cutter = Pos(15, 0, 0) * Box(10, 10, 10)   # overlaps the +X face region
    relieved = relieve(target, [cutter], clearance=0.4)
    assert check_solid(relieved).ok
    assert relieved.volume < target.volume
    assert intersection_volume(relieved, cutter) == 0.0
    # axis-direction clearance is the guaranteed bound
    assert clearance(relieved, cutter) <= 0.4 + 1e-6


def test_relieve_validation():
    with pytest.raises(ValueError):
        relieve(Box(1, 1, 1), [], clearance=0.4)
    with pytest.raises(ValueError):
        relieve(Box(1, 1, 1), [Box(1, 1, 1)], clearance=-0.1)
```

- [ ] **Step 2: RED**, then **Step 3: Implement** by PORTING the existing
helpers: read `designs/cuban_bracelet/build.py` `_expand` (~line 31) and the
`_relieve` closure (~line 96) and move the logic into
`claudecad/assembly.py` with the docstrings preserved and generalized
(module docstring: "Assembly finishing: operations that fit parts of an
assembly to each other. Domain-neutral."). Then refactor
`designs/cuban_bracelet/build.py` to `from claudecad.assembly import
relieve` and delete the local copies — behavior must be IDENTICAL (the
two-tier cut order preserved).

- [ ] **Step 4: GREEN + the real gate**

Run: `uv run pytest tests/test_assembly.py -q` → 3 passed.
Run: `uv run python -m designs.cuban_bracelet.build` (timeout 900000) —
full gate output identical in PASS/FAIL structure to before the refactor
(paste the gate lines; the numbers must match the pre-refactor run — same
geometry, same checks).

- [ ] **Step 5: Restore the SKILL.md line** ("relief slots via
`assembly.relieve`") and commit:

```bash
git add claudecad/assembly.py tests/test_assembly.py designs/cuban_bracelet/build.py .claude/skills/cad/SKILL.md
git commit -m "refactor: promote relief finishing to domain-neutral claudecad.assembly"
```

---

### Task 9: designs/_template + recipe doc

**Files:**
- Create: `designs/_template/params.py`, `designs/_template/build.py`, `docs/new-design-recipe.md`
- Modify: `README.md` (restore the `_template` sentence per Task 5's note), `tests/test_designs_import.py` (add template modules)

- [ ] **Step 1: Template files**

`designs/_template/params.py`:
```python
"""<YOUR DESIGN> — every driving dimension, in mm.

Rules (see .claude/skills/cad/SKILL.md): driving params only; derived
values are computed by the library and printed by build.py, never set here.
"""
# Example driving parameter — replace with your design's:
EXAMPLE_SIZE = 42.0
```

`designs/_template/build.py`:
```python
"""Build, verify, export <YOUR DESIGN>.

Usage: uv run python -m designs._template.build
The shape of every claudeCAD design: build solids -> ALWAYS write the GLB
-> run the gate -> write STEP ONLY if the gate passes (exit 1 otherwise).
"""
import sys

from build123d import Box

from claudecad.verify import check_solid
from tools.export import export_design, export_glb

from .params import EXAMPLE_SIZE


def main() -> int:
    # 1) build your solids (library parts or raw build123d)
    parts = {"example": Box(EXAMPLE_SIZE, EXAMPLE_SIZE, EXAMPLE_SIZE)}

    # 2) GLB always — it's the render/preview artifact, even for failures
    export_glb(parts, "out/glb/_template.glb")

    # 3) the gate: compose the checks your design's claims require
    #    (check_chain for interlocking sequences; path_clearance +
    #    constructed-state differentials for mechanisms; clearance bands
    #    for fit — see claudecad/verify.py)
    ok = all(check_solid(s).ok for s in parts.values())
    print(f"gate: {'OK' if ok else 'FAILED'} ({len(parts)} parts)")

    # 4) STEP only on a passing gate
    if not ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1
    export_design(parts, "out/step/_template.step", assembly_label="template")
    print("exported out/step/_template.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`docs/new-design-recipe.md`:
```markdown
# Starting a new design

1. `cp -r designs/_template designs/<name>` and rename the strings.
2. Put every driving dimension in `params.py` (mm). Derived values are
   outputs — compute and print them in build.py, never hardcode.
3. Build solids from a domain pack (`claudecad/jewelry`, `claudecad/hardware`)
   or raw build123d. New reusable parts belong in a domain pack with tests.
4. Compose the gate from `claudecad/verify.py` primitives:
   - sequences that must interlock -> `check_chain` (linking number +
     intersection; `interlock_depth`, `max_gap` for near-contact fits)
   - mechanisms -> constructed states + `path_clearance` differentials
     (see the box clasp: relaxed blocked / compressed free IS the click)
   - fits -> `clearance` / `intersection_volume`
5. `uv run python -m designs.<name>.build` — STEP exports only on a green
   gate. Render with `tools/render.py`; judge against real reference photos.
6. Working with Claude Code? The `/cad` skill already knows this loop.
```

- [ ] **Step 2: Restore README's `_template` sentence** (Task 5 note) and add
`designs._template.build`/`.params` to the import smoke list.

- [ ] **Step 3: Run**

`uv run python -m designs._template.build` → gate OK, STEP exported.
`uv run pytest tests/test_designs_import.py -q` → 7 passed.

- [ ] **Step 4: Commit**

```bash
git add designs/_template docs/new-design-recipe.md README.md tests/test_designs_import.py
git commit -m "feat: design template and new-design recipe"
```

---

### Task 10: carabiner domain pack (the generality proof)

**Files:**
- Create: `claudecad/hardware/__init__.py`, `claudecad/hardware/carabiner.py`, `tests/test_carabiner.py`, `designs/carabiner/params.py`, `designs/carabiner/build.py`
- Modify: `README.md` ("What's here" gains the `hardware/` line — per Task 5's note), `tests/test_designs_import.py`

**Interfaces:**
- Produces: `CarabinerParams` frozen dataclass (mm, validated): `body_l=70.0` (outer, long axis X), `body_w=40.0`, `wire_d=8.0`, `gap_l=16.0` (gate opening along the +Y straight), `gate_d=7.0`, `nose_depth=2.0`, `pin_d=2.0`, `clearance=0.3`; `carabiner_body(p) -> Solid` (planar stadium sweep — curb_link-style analytic construction — with the gate opening cut from the +Y straight, a nose recess at the opening's +X end, and a pivot boss at the −X end); `carabiner_gate(p, state: Literal["closed","open"]) -> Solid` (rod pivoting at the −X end of the opening: closed = spanning the opening, tip seated in the nose recess with `clearance`; open = rotated 30 degrees INWARD about the pivot Z-axis); `carabiner_pin(p) -> Solid`; `escape_ring(p) -> tuple[Solid, np.ndarray]` (a torus + centerline sized to thread the aperture, used by the gates); `closed_circuit(p) -> np.ndarray` (body centerline with the gap bridged by the gate chord — the closed loop the ring links against); `ESCAPE_AXIS: tuple` and `escape_distance(p) -> float` (the shared escape path used by both the tests and the design gate).

- [ ] **Step 1: Failing tests**

`tests/test_carabiner.py`:
```python
import numpy as np
import pytest
from build123d import Pos

from claudecad.hardware.carabiner import (
    CarabinerParams, carabiner_body, carabiner_gate, carabiner_pin, escape_ring,
)
from claudecad.verify import (
    check_solid, intersection_volume, linking_number, path_clearance,
)


def test_parts_clean():
    p = CarabinerParams()
    for s in (carabiner_body(p), carabiner_gate(p, "closed"),
              carabiner_gate(p, "open"), carabiner_pin(p)):
        assert check_solid(s).ok


def test_closed_assembly_clear():
    p = CarabinerParams()
    body, gate, pin = carabiner_body(p), carabiner_gate(p, "closed"), carabiner_pin(p)
    assert intersection_volume(body, gate) == 0.0
    assert intersection_volume(body, pin) == 0.0
    assert intersection_volume(gate, pin) == 0.0


def test_ring_linked_through_closed_carabiner():
    p = CarabinerParams()
    ring, curve = escape_ring(p)
    body, _ = carabiner_body(p), None
    # body centerline circuit: with the gate CLOSED the aperture is a closed
    # loop topologically; prove by linking the ring against the body+gate
    # combined centerline is overkill — instead prove the functional pair:
    # ring is linked with the body's own closed circuit through the spine
    # and gate line. The carabiner module provides it:
    from claudecad.hardware.carabiner import closed_circuit
    lk = linking_number(closed_circuit(p), curve)
    assert abs(round(lk)) == 1 and abs(lk - round(lk)) < 0.1
    assert intersection_volume(ring, body) == 0.0


def test_escape_differential():
    """THE carabiner property: with the gate closed the ring cannot leave
    (its escape path collides); with the gate open the same path is clear
    of body+gate at every station."""
    p = CarabinerParams()
    ring, _ = escape_ring(p)
    body = carabiner_body(p)
    closed_g = carabiner_gate(p, "closed")
    open_g = carabiner_gate(p, "open")
    # escape path: out through the gap, +Y then away — the module provides
    # the axis and distance so the test and the design gate share it
    from claudecad.hardware.carabiner import ESCAPE_AXIS, escape_distance
    d = escape_distance(p)
    blocked = path_clearance(ring, body + closed_g, ESCAPE_AXIS, d, 12)
    assert max(blocked) > 0.0
    free_body = path_clearance(ring, body, ESCAPE_AXIS, d, 12)
    free_gate = path_clearance(ring, open_g, ESCAPE_AXIS, d, 12)
    assert max(free_body) == 0.0 and max(free_gate) == 0.0


def test_params_validation():
    with pytest.raises(ValueError):
        CarabinerParams(gap_l=0.0)
    with pytest.raises(ValueError):
        CarabinerParams(gate_d=9.0)   # gate fatter than body wire? define: gate_d < wire_d + something — encode the module's rule
```

CONTRACT (same as the clasp tasks): these tests are the spec of BEHAVIOR;
exact fixture numbers inside the module (`ESCAPE_AXIS`, ring size/position,
station counts) are the implementer's to derive — expose them as module
constants/functions as shown so tests and the design gate share one source.
The last validation case's rule: pick the geometric impossibility your
construction actually has (e.g. `gate_d >= wire_d` making the nose recess
unbuildable) and encode THAT with a value-carrying message; adjust the test
value accordingly and say so in your report.

- [ ] **Step 2: RED**, then **Step 3: Implement** `claudecad/hardware/carabiner.py`:
construction = planar analytic only (stadium sweep for the body like
`curb_link` — import `stadium_wire` from core; Box cuts for the opening and
nose recess; Cylinder gate/pin; `closed_circuit(p) -> np.ndarray` = the
body's centerline with the gap segment bridged by the gate line — sampled
from `claudecad.core.centerline.discretize` on the stadium wire, points in
the gap replaced by the straight gate chord). Two-state gate via rotation
about the pivot axis. Docstring the frame: body in XY, z=0 midplane,
opening on the +Y straight. Follow the /cad construction laws (no shells,
no twisted sweeps needed here — all planar/analytic).

- [ ] **Step 4: GREEN**

Run: `uv run pytest tests/test_carabiner.py -q` → 5 passed (few minutes: sweeps + booleans).

- [ ] **Step 5: The design** — `designs/carabiner/params.py` (instantiate
CarabinerParams + any display params) and `designs/carabiner/build.py`
(same shape as every design: GLB always; gate = the four checks from the
tests recomputed on the design instance — parts clean, closed-assembly
clear, ring linked, escape differential — printed with numbers; STEP with
parts body/gate/pin only on pass). Add to import smoke. Render 4 views;
view them; judge against carabiner reference photos (fetch 2); iterate
proportions in params until it reads as a carabiner (snap-gate style).

- [ ] **Step 6: Full suite + commit**

```bash
uv run pytest -q     # all green
git add claudecad/hardware tests/test_carabiner.py designs/carabiner README.md tests/test_designs_import.py
git commit -m "feat: hardware domain pack with statically-proven spring-gate carabiner"
```

---

### Task 11: Cleanups + README/skill touch-ups + push stage 2

**Files:**
- Modify: `claudecad/jewelry/clasps.py` (ear_w dedup), `tests/test_clasps.py` (tongue-end attachment_loop test), `designs/cuban_bracelet/build.py` (gap-frames decision), `README.md` (final tree includes assembly.py + hardware/)

- [ ] **Step 1: ear_w dedup** — `ear_w` formula `(p.box_w - _EAR_GAP) / 2 - 1.0`
appears in `clasp_box` and `clasp_tongue`; hoist to a module function
`_ear_w(p)` used by both (geometry bit-identical; tests unchanged).

- [ ] **Step 2: tongue-end attachment loop test** (append to `tests/test_clasps.py`):

```python
def test_attachment_loop_tongue_end_links():
    p = BoxClaspParams()
    loop = attachment_loop(p, "tongue")
    lp = LinkParams(length=20.0, width=15.0, wire_d=4.0)
    _, wire = curb_link(lp)
    bar_x = -p.lug_l + p.bar_d / 2 + 0.5
    link_curve = discretize(Pos(bar_x - (10.0 - lp.wire_d), 0, 0) * wire, 256)
    lk = linking_number(loop, np.asarray(link_curve))
    assert abs(round(lk)) == 1 and abs(lk - round(lk)) < 0.1
```
(Fixture-position exception applies as in the box-end test: if Lk=0 from
edge placement, move the link clearly into threading position and report.)

- [ ] **Step 3: gap-frames decision** — read `designs/cuban_bracelet/build.py`'s
placement block; EITHER rewrite the placement to derive from
`info.gap_start`/`gap_end` if that reads clearer than the chord math, OR
add one comment line at the placement stating the frames are probe-only and
chord math is authoritative. Run the full cuban build once (gate green,
numbers unchanged) if you touched placement; skip the build if comment-only.

- [ ] **Step 4: Final README tree** — ensure "What's here" lists
`assembly.py` and `hardware/` (added in Tasks 8/10 — verify both lines
present; add if missed).

- [ ] **Step 5: Suite, commit, push**

```bash
uv run pytest -q
git add -A && git commit -m "chore: clasp dedup, tongue-loop test, placement note, README tree"
git push origin main   # stage 2 lands on the live repo
gh run watch --exit-status || gh run list --limit 1
```
Expected: CI green on the stage-2 push. Report the run URL.

---

## Verification at plan level

Stage 1 exit = Task 6's green Actions run on the public repo. Stage 2 exit =
Task 11's green run. Spec coverage: positioning → Tasks 2/5 (binding text);
hygiene/license/CI → 1/3; simple_curb → 4; publish → 6; clearance → 7;
relieve → 8; template/recipe → 9; carabiner → 10; cleanups → 11.
