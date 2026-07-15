# Distribution pass — claudeCAD consumable outside this repo

**Date:** 2026-07-15
**Status:** Approved
**Predecessors:** 2026-07-13-open-source-release-design.md (v4 made the repo
public and general; this pass makes it CONSUMABLE), the three hardware-phase
specs (the tooling this distributes).

**Project lens:** claudeCAD is tooling so the community can make verified CAD
designs in Claude Code projects. Today the consumable unit is accidentally
the *repo shape*: the wheel ships only `claudecad/`, but every design's
`build.py` imports `tools.export`, the `/cad` skill hardcodes the repo layout,
and the recipe starts with `cp -r designs/_template`. A pip install hands you
a geometry library that cannot run the workflow that makes it claudeCAD.
This pass fixes the root coupling and ships both consumption channels.

## The consumption story (design north star)

- **Existing project:** `/plugin marketplace add mdbritt/claudecad` → install
  the `claudecad` plugin (gets the `/cad` skill) → `uv add claudecad` →
  design in chat; gates run; STEP comes out.
- **Fresh project:** `uvx claudecad new mypart` → a stamped project
  (pyproject depending on `claudecad`, `.claude/skills/cad/SKILL.md`,
  `designs/mypart/` from the template, `out/`, README stub) → design in chat
  immediately.

## Components

### 1. Absorb the workflow into the package (the root fix)

- `tools/export.py` → **`claudecad/export.py`** (pure build123d, no repo
  coupling; moves verbatim plus docstring).
- `tools/render.py` + `tools/blender_scene.py` → **`claudecad/render/`**
  (`__init__.py` with `render_glb(...)`, `blender_scene.py` as package data;
  `BLENDER_BIN` env override unchanged).
- **`claudecad/cli.py`** — stdlib `argparse` (no new dependencies), console
  script `claudecad` with subcommands:
  - `claudecad new <name> [--dir PATH]` — scaffolder (below).
  - `claudecad render <glb> --outdir DIR [--views ...] [--res ...]
    [--samples N]` — thin wrapper over `claudecad.render.render_glb`.
- `pyproject.toml`: `[project.scripts] claudecad = "claudecad.cli:main"`;
  hatch config includes package data (scene script, scaffold template,
  skill copy).
- **In-repo migration:** every `designs/*/build.py` and test imports move
  `from tools.export import ...` → `from claudecad.export import ...`;
  `tools/` retains only the step_viewer (repo-local dev convenience) —
  no compatibility shims; the repo is its own first consumer. The `/cad`
  skill's loop step 3 becomes `uv run claudecad render out/glb/<name>.glb
  --outdir out/renders/<name>`.

### 2. Scaffolder (`claudecad new`)

Stamps a ready-to-design project:

```
<name>/
  pyproject.toml            # requires-python >=3.12, deps: claudecad, dev: pytest
  .claude/skills/cad/SKILL.md
  designs/<name>/{__init__.py, params.py, build.py}   # from the template
  out/.gitkeep
  README.md                 # 10-line quickstart
  .gitignore                # out/ artifacts, __pycache__
```

- Template source: the existing `designs/_template`, shipped as package data;
  the scaffolder renames strings to `<name>`.
- Refuses to overwrite an existing non-empty target (value-carrying error).
- The stamped project's `build.py` must run green immediately
  (`uv run python -m designs.<name>.build`) — the template already gates a
  simple part; imports updated to `claudecad.export`.

### 3. Skill single-sourcing

The `/cad` skill text gains a second and third consumer (plugin, scaffold
package data). Exactly ONE source of truth in the repo; the spike picks the
mechanism (preference order: hatch build hook copying at wheel-build time →
sync script + CI equality check; symlinks only if Claude Code's plugin loader
and hatchling both provably follow them). The skill text itself is edited
once for consumer-project accuracy: `claudecad render ...` for step 3,
"domain packs come from the installed `claudecad` package; new reusable
parts belong in your project or upstream PRs", step_viewer note marked
repo-dev-only. It must remain accurate for THIS repo too (the repo is a
consumer via `.claude/skills/cad`).

### 4. Claude Code plugin (this repo doubles as one)

- `.claude-plugin/plugin.json` (name `claudecad`, version synced with
  pyproject) and root-level `skills/cad/SKILL.md` — the plugin layout
  verified against the installed superpowers plugin; plus
  `.claude-plugin/marketplace.json` so
  `/plugin marketplace add mdbritt/claudecad` → `/plugin install claudecad`
  works. Exact schemas verified in the spike against Claude Code's plugin
  docs (not assumed).
- The plugin ships ONLY the skill (no hooks/agents). The skill instructs
  `uv add claudecad` if the library is missing.

### 5. PyPI release mechanics

- Wheel/sdist correctness: package data present (scene script, template,
  skill), `uv build` in CI, **clean-venv smoke job** (below).
- `.github/workflows/release.yml`: on GitHub release, build + publish via
  **PyPI trusted publishing** (no long-lived tokens). `docs/releasing.md`
  documents the one-time PyPI-side setup and the release steps.
- **Mike-only actions (outward-facing, not automated):** creating/owning the
  PyPI project + trusted-publisher config, and cutting the release. The
  `claudecad` name's availability on PyPI is checked in the spike; if taken,
  Mike picks the fallback name before the plan is executed.

### 6. Docs

- README: the two consumption paths up top (plugin + `uvx claudecad new`),
  repo-dev section moves below.
- `docs/new-design-recipe.md`: rewritten for out-of-repo use (scaffold-first;
  the in-repo `cp -r designs/_template` path stays as the contributor note).

## Verification (this pass's gate)

- **CI clean-room job — the distribution equivalent of a geometry gate:**
  build the wheel; in an EMPTY directory with a fresh venv, install the
  wheel, run `claudecad new demo`, then run the stamped project's
  `uv run python -m designs.demo.build` (or venv-python equivalent) and
  assert exit 0 + STEP produced. Renders excluded (CI has no Blender —
  existing precedent). This proves the out-of-repo story on every commit.
- Unit tests: CLI arg handling (new/render), scaffolder refuses non-empty
  target, template rename correctness, package-data presence (wheel
  contents assertion), skill single-source equality check.
- Existing 130-test suite stays green through the `tools.export` →
  `claudecad.export` migration.
- Plugin: schema-validated `plugin.json`/`marketplace.json`; a manual
  `/plugin marketplace add` acceptance by Mike (interactive; can't be CI'd).

## Out of scope

- `claudecad viewer` (step_viewer needs on-demand WASM fetching — deferred;
  the viewer stays as repo-local tooling).
- Conda/homebrew packaging; Windows-specific render paths (Blender default
  path stays macOS with `BLENDER_BIN` override — documented).
- Automated version bumping / changelog tooling.
- Publishing the plugin to any centralized marketplace beyond the repo's own
  marketplace.json.

## Milestones

1. **Spike (before the plan's code):** PyPI name availability; exact
   plugin.json/marketplace.json schemas from Claude Code docs; the skill
   single-source mechanism (test symlink behavior in hatchling + plugin
   loader, else pick sync+CI-check); wheel package-data inclusion mechanics;
   clean-venv scaffold smoke run end-to-end locally.
2. Absorb export/render into the package + CLI (`render` subcommand);
   migrate in-repo imports; suite green.
3. Scaffolder + template/skill package data + unit tests; local clean-venv
   smoke green.
4. Plugin files + skill single-sourcing + skill text consumer rewrite.
5. CI clean-room job + release workflow + `docs/releasing.md`.
6. README/recipe rewrite; final review; Mike: PyPI setup + first release +
   plugin acceptance test.
