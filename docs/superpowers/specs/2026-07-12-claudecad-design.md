# claudeCAD — Claude Code-driven CAD design system

**Date:** 2026-07-12
**Status:** Approved
**Benchmark:** Cuban link bracelet

## Problem

Mike wants a CAD design workflow driven by Claude Code, focused purely on design
(manufacturing constraints come later), with results landing in Plasticity — his
preferred CAD program — as editable geometry. The benchmark that proves the system
is a cuban link bracelet.

## Constraints discovered

- Plasticity has no scripting API and no MCP server exists for it. Its only
  programmatic surface is the Blender Bridge WebSocket, which streams *mesh*
  (facet) data — not usable for commanding geometry creation.
- Plasticity natively imports STEP as fully editable NURBS/B-rep solids.
  STEP is therefore the interchange format; mesh-based code-CAD tools
  (OpenSCAD et al.) are ruled out because meshes arrive in Plasticity as
  dead facet geometry.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| End goal | Looks-first, manufacturing later | Nail design workflow and visual quality; tolerances/printability are a later phase |
| Iteration loop | In chat, export at the end | Claude renders previews in conversation; STEP export to Plasticity when the design is right |
| Deliverable | Reusable system | A project with a `/cad` skill, growing component library, render+export tooling — bracelet is benchmark #1 |
| Kernel/stack | build123d (Python on OpenCASCADE) | True B-rep → lossless STEP; best ergonomics for sweeps/patterns/assemblies; Python enables programmatic geometry verification |
| Preview renderer | Headless Blender 4.5 CLI (`blender -b`) | Already installed; gold material + studio HDRI so previews read as jewelry; no GUI dependency |

## Architecture

Project root: `/Users/mike/code/claudeCAD`, uv-managed Python project.

```
claudeCAD/
├── .claude/skills/cad/SKILL.md   # /cad workflow skill — how Claude designs, verifies, renders, exports
├── claudecad/                    # parametric component library (Python package)
│   ├── core/                     # geometry helpers: profiles, sweep-along-curve, patterning
│   ├── jewelry/                  # domain parts: curb links, chain assembly, clasps
│   └── verify.py                 # geometry checks (validity, interference, interlock)
├── designs/
│   └── cuban_bracelet/
│       ├── params.py             # every dimension in one place, all mm
│       └── build.py              # thin script composing library parts
├── tools/
│   ├── render.py                 # headless Blender render — gold material, HDRI, multi-angle
│   └── export.py                 # STEP export with named solids (clean Plasticity outliner)
└── out/                          # renders + .step files (gitignored)
```

### Component boundaries

- **Library components (`claudecad/`)** are pure functions: parameters in →
  solid(s) out. No I/O, no rendering, no export.
- **`verify.py`** takes solids and returns structured pass/fail reports with
  numbers (e.g., penetration depth, linking number). No I/O.
- **`tools/`** is the only layer that touches disk and Blender.
- **`designs/`** are thin composition scripts: a `params.py` holding every
  dimension and a `build.py` that assembles library parts.

## Iteration loop (data flow)

1. User describes a piece or a tweak in chat.
2. Claude edits `params.py` / `build.py` and runs the build.
3. Verification runs automatically as part of every build — failures block
   rendering and are reported with numbers.
4. Geometry is written to a temp GLB → Blender CLI renders 3–4 angles plus a
   close-up with gold material → images shown in chat.
5. Iterate 2–4 until the user is happy.
6. `export.py` writes STEP with named solids → user imports into Plasticity
   as fully editable NURBS.

### The /cad skill codifies

- All dimensions in mm, defined only in `params.py`.
- Never render unverified geometry; never export STEP that fails verification.
- Compare renders against real reference photos (pulled during implementation)
  rather than assuming what a cuban link looks like.

## Benchmark: cuban link bracelet

A cuban (curb) link chain: flattened oval links, each twisted so the chain lies
flat, each link threading through its neighbor.

**Parameters:** wrist circumference, link width, wire gauge, twist angle, and
inter-link clearance are the *driving* parameters; link count and pitch are
*derived* from circumference and link geometry (they are coupled — specifying
both independently could contradict). `params.py` exposes the derived values
read-only.

**v1 scope:** a closed continuous loop of properly interlocked curb links that
reads as a real cuban link in renders. The box clasp (standard on real cuban
bracelets) is a separate follow-up milestone and must not block the chain.

## Verification layer

- **Validity:** every solid passes OCCT validity checks, is watertight,
  volume > 0.
- **Dimensions:** bounding-box assertions against params.
- **No interpenetration:** boolean intersection volume between every adjacent
  link pair must be exactly 0; penetration depth reported on failure.
- **Interlock:** Gauss linking number of adjacent links' closed centerline
  curves must be nonzero — a mathematical guarantee the links are topologically
  inseparable, computed numerically from the discretized centerlines.

## Error handling

- OCCT operations (booleans, sweeps) can fail opaquely: every build step reports
  which operation failed with which parameters. No silent retries with fudged
  tolerances.
- Render failures surface Blender's stderr.
- Verification failures block export.

## Testing

pytest suite:

- Every library component builds, is watertight, and matches its parameter
  dimensions (bounding-box assertions).
- Chain-level tests: zero interference between adjacent links; nonzero linking
  number for every adjacent pair.
- STEP round-trip: export → reimport via build123d → solid count matches.
- Render smoke test: Blender CLI produces non-empty PNGs.

Tests pass before any component is claimed to work.

## Milestones

1. **Scaffold + smoke test:** uv project, build123d installed, end-to-end
   pipeline proven with a gold torus (build → verify → render → STEP →
   manual Plasticity import).
2. **Single curb link** component, tested.
3. **Straight chain segment** with verified interlocking.
4. **Closed bracelet loop** — the benchmark render + STEP into Plasticity.
5. **Stretch: box clasp.**

## Out of scope (v1)

- Manufacturing constraints (castability, print tolerances, metal weight).
- Driving Plasticity directly (no API exists).
- Live/hot-reload into Plasticity; export is a deliberate end-of-loop step.
- Clasp mechanics (milestone 5, after benchmark).
