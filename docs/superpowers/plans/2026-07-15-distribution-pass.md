# Distribution Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make claudeCAD consumable outside this repo: `pip install claudecad` carries the whole workflow, `claudecad new` stamps a ready-to-design project, and this repo doubles as a Claude Code plugin.

**Architecture:** Absorb the workflow into the package (`tools/export.py` → `claudecad/export.py`, `tools/render.py` → `claudecad/render/`), add a stdlib-argparse CLI (`claudecad render`, `claudecad new`), move the design template into `claudecad/_scaffold/` as real package data, single-source the `/cad` skill via a sync script + CI equality gate, ship plugin manifests, and gate distribution itself with a CI clean-room job (wheel → empty venv → scaffold → run the stamped project's build).

**Tech Stack:** hatchling (existing backend), stdlib argparse/importlib.resources/shutil (no new runtime deps), GitHub Actions + PyPI trusted publishing.

## Global Constraints

- Python `>=3.12`, build123d pinned `>=0.11,<0.12` (unchanged); backend **hatchling** with `packages = ["claudecad"]` — everything under `claudecad/` (including non-`.py` package data) ships in the wheel automatically; nothing outside it does.
- **No new runtime dependencies** — the CLI is stdlib only.
- **Spike-verified facts (2026-07-15):** PyPI name `claudecad` is AVAILABLE (HTTP 404; `claude-cad` is taken — do not use it). Plugin manifest lives at `.claude-plugin/plugin.json` (minimal working schema per the installed superpowers plugin: `name`, `version`, `description`, `author{name}`, `homepage`, `license`, `keywords`, `"skills": "./skills/"`); marketplace manifest at `.claude-plugin/marketplace.json` with `{name, description, owner{name}, plugins:[{name, description, author{name}, category, source{...}, homepage}]}` and a published JSON Schema at `https://anthropic.com/claude-code/marketplace.schema.json` — **the exact `source` form for a repo-root plugin MUST be validated against that schema during Task 3, not assumed.** Baseline `uv build` is green (wheel currently 16 files, no workflow — the coupling this pass fixes).
- **Skill single-sourcing:** `.claude/skills/cad/SKILL.md` is the ONE source of truth; `skills/cad/SKILL.md` (plugin) and `claudecad/_scaffold/skills/cad/SKILL.md` (package data) are synced copies enforced by `scripts/sync_skill.py --check` in CI. No symlinks (loader behavior unverified).
- The repo is its own first consumer: after Task 1 nothing in the repo imports from `tools.*`; the 130-test suite stays green at every task boundary.
- Import-site inventory for the migration (verified by grep): `designs/{_template,bearing_608,bolt,carabiner,cuban_bracelet,simple_curb,snapbox}/build.py`, `tests/test_export.py`, `tests/test_render_smoke.py`.

---

### Task 1: absorb export/render into the package + `claudecad render` CLI

**Files:**
- Move: `tools/export.py` → `claudecad/export.py`; `tools/render.py` → `claudecad/render/__init__.py`; `tools/blender_scene.py` → `claudecad/render/blender_scene.py`
- Delete: `tools/__init__.py`
- Create: `claudecad/cli.py`
- Modify: `pyproject.toml` (console script), the 9 inventoried import sites, `.claude/skills/cad/SKILL.md` (loop step 3 + layer wording)
- Test: `tests/test_cli.py` (new); existing suite green

**Interfaces:**
- Produces: `claudecad.export.export_design/export_glb` (signatures unchanged), `claudecad.render.render_glb(glb_path, outdir, views, res, samples)` (unchanged), console script `claudecad` → `claudecad.cli:main`, `main(argv: list[str] | None) -> int` with a `render` subcommand mirroring the old `tools/render.py` CLI (`glb`, `--outdir` required, `--views`, `--res`, `--samples`).

- [ ] **Step 1: Write the failing CLI test**

Create `tests/test_cli.py`:

```python
import pytest

from claudecad.cli import main


def test_render_requires_outdir(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["render", "some.glb"])
    assert exc.value.code == 2  # argparse usage error


def test_render_missing_glb_reports_cleanly(tmp_path):
    # render_glb raises FileNotFoundError for a missing GLB; the CLI
    # surfaces it as a nonzero exit with a message, not a traceback
    rc = main(["render", str(tmp_path / "nope.glb"),
               "--outdir", str(tmp_path / "out")])
    assert rc == 1


def test_no_command_is_usage_error():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'claudecad.cli'`.

- [ ] **Step 3: Move the modules (history-preserving) and fix their internals**

```bash
cd /Users/mike/code/claudeCAD
mkdir -p claudecad/render
git mv tools/export.py claudecad/export.py
git mv tools/render.py claudecad/render/__init__.py
git mv tools/blender_scene.py claudecad/render/blender_scene.py
git rm tools/__init__.py
```

Then two small edits:
- `claudecad/render/__init__.py`: the module docstring's first line becomes `"""Drive headless Blender to render a GLB into studio PNGs (claudecad render)."""` — the `SCENE_SCRIPT = Path(__file__).parent / "blender_scene.py"` line already resolves correctly in the new location (the scene script moved alongside); leave `render_glb` and `main` bodies untouched.
- `claudecad/export.py`: docstring gains one sentence: `Part of the installed claudecad package — consumer projects import claudecad.export.`

- [ ] **Step 4: Create the CLI**

Create `claudecad/cli.py`:

```python
"""claudecad command line: render GLBs (and, in later tasks, scaffold
projects). Stdlib only — argparse; no new runtime dependencies."""
from __future__ import annotations

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="claudecad",
        description="Verification-first parametric CAD tooling for "
                    "Claude Code projects.")
    sub = ap.add_subparsers(dest="command", required=True)

    render = sub.add_parser(
        "render", help="render a GLB into studio PNGs via headless Blender")
    render.add_argument("glb")
    render.add_argument("--outdir", required=True)
    render.add_argument("--views", default="persp,top,front,detail")
    render.add_argument("--res", default="1280x960")
    render.add_argument("--samples", type=int, default=64)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "render":
        from claudecad.render import render_glb
        w, h = (int(v) for v in args.res.split("x"))
        try:
            render_glb(args.glb, args.outdir,
                       tuple(args.views.split(",")), (w, h), args.samples)
        except FileNotFoundError as e:
            print(f"claudecad render: {e}", file=sys.stderr)
            return 1
        return 0
    raise AssertionError(f"unhandled command {args.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())
```

Add to `pyproject.toml` (after the `[project]` table):

```toml
[project.scripts]
claudecad = "claudecad.cli:main"
```

- [ ] **Step 5: Migrate the 9 import sites**

In each of `designs/_template/build.py`, `designs/bearing_608/build.py`, `designs/bolt/build.py`, `designs/carabiner/build.py`, `designs/cuban_bracelet/build.py`, `designs/simple_curb/build.py`, `designs/snapbox/build.py`, `tests/test_export.py`: replace `from tools.export import` → `from claudecad.export import` (same names). In `tests/test_render_smoke.py`: replace `from tools.render import` → `from claudecad.render import` (same names). Verify zero remnants:

```bash
grep -rn "from tools\|import tools" --include="*.py" . | grep -v __pycache__ | grep -v step_viewer
```
Expected: no output.

- [ ] **Step 6: Update the /cad skill's command + layer wording**

In `.claude/skills/cad/SKILL.md`:
- Replace `` 3. `uv run python tools/render.py out/glb/<name>.glb --outdir out/renders/<name>` `` with `` 3. `uv run claudecad render out/glb/<name>.glb --outdir out/renders/<name>` ``
- Replace `` `tools/` is the only layer that touches disk/Blender. `` with `` `claudecad.export`/`claudecad.render` are the only layers that touch disk/Blender. ``
- In the "Blender renderer" section, replace `` `tools/render.py` needs Blender; `` with `` `claudecad render` needs Blender; ``

- [ ] **Step 7: Run the CLI tests, then the full suite**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_cli.py -v` then `uv run pytest -q`
Expected: 3 passed; full suite 133 (130 + 3) passed. Then sanity: `uv run claudecad render --help` prints usage, exit 0.

- [ ] **Step 8: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add -A
git commit -m "feat: absorb export/render into the package + claudecad CLI

The wheel now carries the whole workflow: claudecad.export,
claudecad.render (blender_scene as package data), and a stdlib CLI with
a render subcommand. All in-repo imports migrated off tools.*; the /cad
skill's loop now says 'uv run claudecad render'."
```

---

### Task 2: `claudecad new` scaffolder + template as package data

**Files:**
- Move: `designs/_template/build.py` → `claudecad/_scaffold/designs/_template/build.py`; `designs/_template/params.py` → `claudecad/_scaffold/designs/_template/params.py`
- Create: `claudecad/scaffold.py`
- Modify: `claudecad/cli.py` (add `new`), `tests/test_designs_import.py` (drop the two `designs._template` entries)
- Test: `tests/test_scaffolder.py` (new)

**Interfaces:**
- Consumes: Task 1's CLI skeleton and `claudecad.export` template import.
- Produces: `claudecad.scaffold.new_project(name: str, parent: Path) -> Path` (raises `ValueError` on bad name / non-empty target); CLI `claudecad new <name> [--dir PATH]`. Task 3 adds the skill copy into `_scaffold/` — until then the scaffolder writes the design/template/project files only if the skill file is absent it must still succeed (guard with `exists()`), so Tasks 2 and 3 stay independently green.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scaffolder.py`:

```python
import subprocess
import sys

import pytest

from claudecad.scaffold import new_project


def test_new_project_structure(tmp_path):
    target = new_project("mypart", tmp_path)
    assert target == tmp_path / "mypart"
    assert (target / "pyproject.toml").exists()
    assert (target / "designs" / "mypart" / "build.py").exists()
    assert (target / "designs" / "mypart" / "params.py").exists()
    assert (target / "out" / ".gitkeep").exists()
    assert (target / ".gitignore").exists()
    assert (target / "README.md").exists()


def test_template_strings_renamed(tmp_path):
    target = new_project("mypart", tmp_path)
    build = (target / "designs" / "mypart" / "build.py").read_text()
    assert "_template" not in build
    assert "designs.mypart.build" in build      # usage line renamed
    assert "out/glb/mypart.glb" in build        # artifact path renamed
    assert "from claudecad.export import" in build


def test_refuses_nonempty_target(tmp_path):
    (tmp_path / "mypart").mkdir()
    (tmp_path / "mypart" / "junk.txt").write_text("x")
    with pytest.raises(ValueError, match="not empty"):
        new_project("mypart", tmp_path)


def test_rejects_bad_names(tmp_path):
    for bad in ("My-Part", "1part", "designs/evil", ""):
        with pytest.raises(ValueError):
            new_project(bad, tmp_path)


def test_stamped_build_runs_green(tmp_path):
    """The stamped project's gate runs end-to-end with THIS checkout's
    claudecad on the path — the in-repo half of the clean-room story
    (the CI clean-room job repeats this against the built wheel)."""
    target = new_project("demo", tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "designs.demo.build"],
        cwd=target, capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (target / "out" / "step" / "demo.step").exists()
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_scaffolder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'claudecad.scaffold'`.

- [ ] **Step 3: Move the template into the package**

```bash
cd /Users/mike/code/claudeCAD
mkdir -p claudecad/_scaffold/designs/_template
git mv designs/_template/build.py claudecad/_scaffold/designs/_template/build.py
git mv designs/_template/params.py claudecad/_scaffold/designs/_template/params.py
rmdir designs/_template 2>/dev/null; rm -rf designs/_template
```

In `tests/test_designs_import.py`, delete the two entries `"designs._template.build", "designs._template.params",` from `DESIGNS` (the scaffolder test now covers the template end-to-end, which the import smoke never did).

- [ ] **Step 4: Implement the scaffolder + CLI wiring**

Create `claudecad/scaffold.py`:

```python
"""Stamp a ready-to-design claudeCAD project (`claudecad new <name>`).

The template ships as package data under claudecad/_scaffold/ (a real
source directory — identical in a repo checkout and in the wheel), so the
stamped project's gate runs green immediately: pyproject depending on
claudecad, the /cad skill, a designs/<name>/ from the template, out/.
"""
from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

_NAME_RE = re.compile(r"[a-z][a-z0-9_]*\Z")

_PYPROJECT = """\
[project]
name = "{name}"
version = "0.1.0"
description = "A claudeCAD design project"
requires-python = ">=3.12"
dependencies = ["claudecad"]

[dependency-groups]
dev = ["pytest>=8"]
"""

_README = """\
# {name}

A claudeCAD design project. Design in chat with Claude Code (the /cad
skill drives the loop); the gate verifies; STEP comes out.

    uv sync
    uv run python -m designs.{name}.build      # build + verify + export
    uv run claudecad render out/glb/{name}.glb --outdir out/renders/{name}

Edit `designs/{name}/params.py` (every driving dimension) and
`designs/{name}/build.py` (parts + the verification gate). STEP lands in
`out/step/{name}.step` when — and only when — the gate passes.
"""

_GITIGNORE = """\
out/
__pycache__/
*.pyc
.venv/
"""


def new_project(name: str, parent: Path) -> Path:
    """Create `parent/name` as a ready-to-design project. Raises ValueError
    for invalid names or a non-empty existing target."""
    if not _NAME_RE.match(name or ""):
        raise ValueError(
            f"invalid project name {name!r}: need a python-identifier-safe "
            "lowercase name matching [a-z][a-z0-9_]*"
        )
    parent = Path(parent)
    target = parent / name
    if target.exists() and any(target.iterdir()):
        raise ValueError(f"target {target} exists and is not empty")

    scaffold = resources.files("claudecad") / "_scaffold"

    design_dst = target / "designs" / name
    design_dst.mkdir(parents=True, exist_ok=True)
    template = scaffold / "designs" / "_template"
    for fname in ("build.py", "params.py"):
        text = (template / fname).read_text()
        (design_dst / fname).write_text(text.replace("_template", name))

    # the /cad skill ships in _scaffold from Task 3 (skill single-sourcing);
    # guard so Task 2 is independently green before the copy exists
    skill_src = scaffold / "skills" / "cad" / "SKILL.md"
    if skill_src.is_file():
        skill_dst = target / ".claude" / "skills" / "cad" / "SKILL.md"
        skill_dst.parent.mkdir(parents=True, exist_ok=True)
        skill_dst.write_text(skill_src.read_text())

    (target / "out").mkdir(exist_ok=True)
    (target / "out" / ".gitkeep").touch()
    (target / "pyproject.toml").write_text(_PYPROJECT.format(name=name))
    (target / "README.md").write_text(_README.format(name=name))
    (target / ".gitignore").write_text(_GITIGNORE)
    return target
```

In `claudecad/cli.py`, add to `_build_parser()` (before the `render` block):

```python
    new = sub.add_parser(
        "new", help="stamp a ready-to-design claudeCAD project")
    new.add_argument("name")
    new.add_argument("--dir", default=".",
                     help="parent directory (default: cwd)")
```

and to `main()` (before the `render` branch):

```python
    if args.command == "new":
        from pathlib import Path

        from claudecad.scaffold import new_project
        try:
            target = new_project(args.name, Path(args.dir))
        except ValueError as e:
            print(f"claudecad new: {e}", file=sys.stderr)
            return 1
        print(f"created {target} — next: cd {target} && uv sync, "
              "then design in chat")
        return 0
```

- [ ] **Step 5: Run the tests, then the full suite**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest tests/test_scaffolder.py -v` then `uv run pytest -q`
Expected: 5 passed (the stamped-build test takes ~5–10 s); full suite 136 passed (133 + 5 new − 2 dropped `_template` import entries).

- [ ] **Step 6: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add -A
git commit -m "feat: claudecad new — scaffolder with the template as package data

designs/_template moves into claudecad/_scaffold (ships in the wheel);
the scaffolder stamps pyproject/README/.gitignore/out and a renamed
design, and the stamped project's gate runs green end-to-end in-repo."
```

---

### Task 3: plugin manifests + skill single-sourcing

**Files:**
- Create: `scripts/sync_skill.py`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `skills/cad/SKILL.md` + `claudecad/_scaffold/skills/cad/SKILL.md` (both generated by the sync script)
- Modify: `.claude/skills/cad/SKILL.md` (consumer-accuracy edits), `.github/workflows/ci.yml` (sync --check step)

**Interfaces:**
- Consumes: Task 2's `_scaffold` layout (the skill copy lands where the scaffolder already looks).
- Produces: `python scripts/sync_skill.py` (writes copies) / `--check` (exit 1 on drift); the plugin + marketplace manifests.

- [ ] **Step 1: Consumer-accuracy edits to the source skill**

In `.claude/skills/cad/SKILL.md`:
- In the opening layout paragraph, replace `` Domain-neutral geometry lives in `claudecad/` (`core/`, `verify.py`, `assembly.py`); domain packs (e.g. `jewelry/`, `hardware/`) hold reusable parts for a design family. `` with `` Domain-neutral geometry lives in the `claudecad` package (`core/`, `verify.py`, `assembly.py`, `export.py`, `render/`); domain packs (e.g. `claudecad.jewelry`, `claudecad.hardware`) hold reusable parts for a design family. In a consumer project the package comes from PyPI (`uv add claudecad`); new reusable parts belong in your project, or upstream as PRs. ``
- In the loop's step 5, replace `` For quick 3D inspection there's a bundled localhost STEP/GLB viewer — `tools/step_viewer/` (see its fetch_libs.sh; serve repo root on :8123). `` with `` For quick 3D inspection the claudecad REPO (not the pip package) bundles a localhost STEP/GLB viewer — `tools/step_viewer/` (repo-dev only). ``

- [ ] **Step 2: Write the sync script**

Create `scripts/sync_skill.py`:

```python
"""Single-source the /cad skill.

.claude/skills/cad/SKILL.md is the ONE source of truth. Two consumers need
byte-identical copies tracked in git: skills/cad/SKILL.md (the Claude Code
plugin layout) and claudecad/_scaffold/skills/cad/SKILL.md (package data
the scaffolder stamps into new projects). Run with no args to write the
copies; --check (CI) exits 1 if any copy is missing or drifted.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / ".claude" / "skills" / "cad" / "SKILL.md"
COPIES = [
    REPO / "skills" / "cad" / "SKILL.md",
    REPO / "claudecad" / "_scaffold" / "skills" / "cad" / "SKILL.md",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify copies match the source instead of writing")
    args = ap.parse_args()

    src_text = SRC.read_text()
    drifted = []
    for dst in COPIES:
        if args.check:
            if not dst.is_file() or dst.read_text() != src_text:
                drifted.append(dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SRC, dst)
            print(f"synced {dst.relative_to(REPO)}")
    if drifted:
        rels = ", ".join(str(d.relative_to(REPO)) for d in drifted)
        print(f"skill copies drifted from {SRC.relative_to(REPO)}: {rels}\n"
              f"run: python scripts/sync_skill.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run it: `cd /Users/mike/code/claudeCAD && python3 scripts/sync_skill.py` — expect two `synced ...` lines. Then `python3 scripts/sync_skill.py --check` — exit 0.

- [ ] **Step 3: Plugin + marketplace manifests**

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "claudecad",
  "version": "0.1.0",
  "description": "Verification-first parametric CAD in Claude Code: the /cad design loop (build -> verify -> render -> export STEP for Plasticity and friends).",
  "author": { "name": "Mike Britt" },
  "homepage": "https://github.com/mdbritt/claudecad",
  "license": "Apache-2.0",
  "keywords": ["cad", "build123d", "parametric", "step", "verification"],
  "skills": "./skills/"
}
```

Create `.claude-plugin/marketplace.json` (starting point — the `source` form for a repo-root plugin is the one unverified schema detail):

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "claudecad",
  "description": "Verification-first parametric CAD tooling for Claude Code",
  "owner": { "name": "Mike Britt" },
  "plugins": [
    {
      "name": "claudecad",
      "description": "The /cad design loop skill: build -> verify -> render -> export STEP. Pairs with the claudecad Python package (uv add claudecad).",
      "author": { "name": "Mike Britt" },
      "category": "design",
      "source": "./",
      "homepage": "https://github.com/mdbritt/claudecad"
    }
  ]
}
```

**REQUIRED before committing:** fetch the published schema and validate both files — do not assume `"source": "./"` is the correct repo-root form; if the schema requires an object form (e.g. `{"source": "git", ...}` or a `github` variant), correct the manifest to what the schema actually allows:

```bash
cd /Users/mike/code/claudeCAD
curl -fsSL https://anthropic.com/claude-code/marketplace.schema.json -o /tmp/marketplace.schema.json
uvx check-jsonschema --schemafile /tmp/marketplace.schema.json .claude-plugin/marketplace.json
```
Expected: `ok`. (If the schema URL is unavailable, validate against the shape of an installed marketplace at `~/.claude/plugins/marketplaces/*/.claude-plugin/marketplace.json` and record which form was used in the commit message.)

- [ ] **Step 4: CI equality gate**

In `.github/workflows/ci.yml`, add to the `test` job's steps, right after checkout:

```yaml
      - run: python3 scripts/sync_skill.py --check
```

- [ ] **Step 5: Full suite + scaffolder now stamps the skill**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest -q` — 136 passed. Then confirm the Task-2 guard now activates: `cd /tmp && rm -rf skilldemo && uv run --project /Users/mike/code/claudeCAD python -c "from pathlib import Path; from claudecad.scaffold import new_project; t = new_project('skilldemo', Path('/tmp')); print((t / '.claude/skills/cad/SKILL.md').is_file())"`
Expected: `True`.

- [ ] **Step 6: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add -A
git commit -m "feat: Claude Code plugin manifests + single-sourced /cad skill

.claude/skills/cad/SKILL.md is the source of truth; scripts/sync_skill.py
maintains the plugin copy (skills/cad) and the scaffold package-data copy,
with a --check equality gate in CI. plugin.json/marketplace.json let
'/plugin marketplace add mdbritt/claudecad' install the skill."
```

---

### Task 4: CI clean-room job + release workflow + releasing doc

**Files:**
- Modify: `.github/workflows/ci.yml` (clean-room job)
- Create: `.github/workflows/release.yml`, `docs/releasing.md`

**Interfaces:**
- Consumes: the wheel now carrying workflow + scaffold (Tasks 1–3).
- Produces: the distribution gate (every push proves the out-of-repo story) and the tag-to-PyPI path.

- [ ] **Step 1: Add the clean-room job**

Append to `.github/workflows/ci.yml` (same level as the `test` job):

```yaml
  clean-room:
    # the distribution gate: install ONLY the wheel in an empty venv,
    # scaffold a project, and run its verification gate end-to-end
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv build
      - name: scaffold and build in a clean venv
        run: |
          WHEEL=$(ls "$PWD"/dist/*.whl)
          mkdir -p /tmp/cleanroom && cd /tmp/cleanroom
          uv venv
          uv pip install --python .venv/bin/python "$WHEEL"
          .venv/bin/claudecad new demo
          cd demo
          ../.venv/bin/python -m designs.demo.build
          test -f out/step/demo.step
          test -f .claude/skills/cad/SKILL.md
```

- [ ] **Step 2: Release workflow (PyPI trusted publishing)**

Create `.github/workflows/release.yml`:

```yaml
name: release
on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write   # PyPI trusted publishing (OIDC) — no tokens stored
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

- [ ] **Step 3: The releasing doc**

Create `docs/releasing.md`:

```markdown
# Releasing claudecad

## One-time setup (Mike, on pypi.org — cannot be automated)

1. pypi.org → account → Publishing → "Add a new pending publisher":
   - PyPI project name: `claudecad` (verified available 2026-07-15)
   - Owner: `mdbritt`  ·  Repository: `claudecad`
   - Workflow: `release.yml`  ·  Environment: `pypi`
2. github.com/mdbritt/claudecad → Settings → Environments → create `pypi`
   (optionally add yourself as a required reviewer — that makes every
   publish a one-click manual approval).

## Each release

1. Bump `version` in BOTH `pyproject.toml` and `.claude-plugin/plugin.json`
   (keep them identical), commit, push, wait for CI green (the clean-room
   job is the release gate).
2. `git tag vX.Y.Z && git push origin vX.Y.Z`
3. `gh release create vX.Y.Z --generate-notes` — publishing the GitHub
   release triggers `release.yml`, which builds and uploads to PyPI via
   trusted publishing.
4. Verify: `uvx claudecad@X.Y.Z new smoke && cd smoke && uv sync &&
   uv run python -m designs.smoke.build` (fresh machine-equivalent).

## Plugin consumers

`/plugin marketplace add mdbritt/claudecad` then `/plugin install
claudecad` — the plugin version comes from `.claude-plugin/plugin.json`
at the repo's default branch; no separate publish step.
```

- [ ] **Step 4: Local dry-run of the clean-room script**

Run the clean-room block locally (same commands, `/tmp/cleanroom-local`):

```bash
cd /Users/mike/code/claudeCAD && rm -rf dist /tmp/cleanroom-local && uv build
WHEEL=$(ls "$PWD"/dist/*.whl)
mkdir -p /tmp/cleanroom-local && cd /tmp/cleanroom-local
uv venv && uv pip install --python .venv/bin/python "$WHEEL"
.venv/bin/claudecad new demo && cd demo
../.venv/bin/python -m designs.demo.build && test -f out/step/demo.step && echo CLEAN-ROOM-OK
```
Expected: `CLEAN-ROOM-OK`. This is the pass's decisive evidence — a wheel-only environment runs the full scaffold→verify→STEP story.

- [ ] **Step 5: Commit**

```bash
cd /Users/mike/code/claudeCAD
git add .github/workflows/ci.yml .github/workflows/release.yml docs/releasing.md
git commit -m "ci: clean-room distribution gate + PyPI trusted-publishing release"
```

---

### Task 5: README + recipe rewrite (consumption-first)

**Files:**
- Modify: `README.md`, `docs/new-design-recipe.md`

**Interfaces:** none new — docs only, but they are the community's front door and must match Tasks 1–4 exactly (commands: `uv add claudecad`, `uvx claudecad new`, `uv run claudecad render`, `/plugin marketplace add mdbritt/claudecad`).

- [ ] **Step 1: README consumption section**

In `README.md`, insert directly after the title/tagline block (before any existing quickstart) a new section:

```markdown
## Use it in your project

Two ways in — both end with you designing in chat while the gates verify:

**Existing Claude Code project**

    /plugin marketplace add mdbritt/claudecad     # in Claude Code
    /plugin install claudecad                     # installs the /cad skill
    uv add claudecad                              # the library

**Fresh project**

    uvx claudecad new mypart
    cd mypart && uv sync

Then just describe the part in chat. The `/cad` skill drives the loop:
build → **verify** (the gates are ground truth) → render → export. STEP
lands in `out/step/` only when verification passes.
```

Update the existing repo-oriented quickstart heading to `## Developing claudeCAD itself` (keep its content), and update the `designs/_template/` reference (README line ~65) to: `Start a new piece with `uvx claudecad new` (in-repo contributors: the template lives at `claudecad/_scaffold/designs/_template/`)`.

- [ ] **Step 2: Recipe rewrite**

In `docs/new-design-recipe.md`, replace the step-1 line `` 1. `cp -r designs/_template designs/<name>` and rename the strings. `` with:

```markdown
1. Out-of-repo (the normal case): `uvx claudecad new <name>` stamps the
   project — template, skill, pyproject — already renamed. In THIS repo
   (adding a benchmark design): `cp -r claudecad/_scaffold/designs/_template
   designs/<name>` and rename the `_template` strings, then register the
   design in `tests/test_designs_import.py` (hardcoded list).
```

- [ ] **Step 3: Full suite + docs sanity, commit**

Run: `cd /Users/mike/code/claudeCAD && uv run pytest -q` (136 passed) and `grep -rn "tools/render\|designs/_template" README.md docs/new-design-recipe.md .claude/skills/cad/SKILL.md` — expected: only the intentional `claudecad/_scaffold/designs/_template` contributor references.

```bash
cd /Users/mike/code/claudeCAD
git add README.md docs/new-design-recipe.md skills claudecad/_scaffold
git commit -m "docs: consumption-first README and recipe (plugin + uvx paths)"
```

---

## Notes for the implementer

- **The clean-room dry-run (Task 4 Step 4) is the pass's real gate** — if it fails, the wheel is missing something (package data, console script, template): fix the packaging, never the check.
- **Skill copies are generated** — never hand-edit `skills/cad/SKILL.md` or `claudecad/_scaffold/skills/cad/SKILL.md`; edit `.claude/skills/cad/SKILL.md` and run `python3 scripts/sync_skill.py`.
- **The marketplace `source` form is the one deliberately-unverified detail** (Task 3 Step 3): validate against the published schema before committing; record the chosen form. Final acceptance of the plugin path is Mike running `/plugin marketplace add mdbritt/claudecad` interactively — it cannot be CI'd.
- Mike-only actions (out of scope for implementers): PyPI pending-publisher setup, the `pypi` GitHub environment, cutting the first release (`docs/releasing.md` steps 1–2 of one-time setup).
