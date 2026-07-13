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
