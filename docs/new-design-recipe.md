# Starting a new design

1. Out-of-repo (the normal case): `uvx claudecad new <name>` stamps the
   project — template, skill, pyproject — already renamed. In THIS repo
   (adding a benchmark design): `cp -r claudecad/_scaffold/designs/_template
   designs/<name>` and rename the `_template` strings, then register the
   design in `tests/test_designs_import.py` (hardcoded list).
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
   gate. Render with `claudecad render`; judge against real reference photos.
6. Working with Claude Code? The `/cad` skill already knows this loop.
