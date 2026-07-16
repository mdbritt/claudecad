# First-user polish — pre-release pass

**Date:** 2026-07-15
**Status:** Approved
**Predecessors:** 2026-07-15-distribution-pass-design.md (shipped; release
deliberately deferred to land this pass first).

**Lens:** what does the FIRST community user hit? A bare-Box template that
teaches nothing, a README that hides the hardware pack, and a render command
hardcoded to one macOS path. Fix those three; fold in the reviewers'
deferred verification minors while we're in the files.

## 1. Teaching template (replaces the bare Box)

`claudecad new` stamps the first code a user reads — it should teach the
gate vocabulary, not just prove imports. New `_template` design: a
**peg-and-socket fit** (base block with a bore + a peg), ~40 lines, boxes
and cylinders only, building in seconds (the scaffolder test and clean-room
CI run it):

- parts clean (`check_solid(...).ok`),
- fit: peg-to-bore gap in a near-contact band (`verify.clearance`, crisp
  iv == 0 — clearance mechanism),
- mechanism: `path_clearance` differential — axial insertion free (== 0 at
  every station), lateral escape blocked (> 0) — the smallest possible
  free/blocked pair, with comments naming the pattern and pointing at the
  /cad skill laws.

Same file shapes (`params.py` driving dims / `build.py` gate), `_template`
naming preserved (the scaffolder's rename contract is unchanged). Geometry
and gate numbers spike-verified before the plan.

## 2. README hardware-pack showcase

The README shows one bracelet render; the generality story (three mechanism
classes, each with its own verification law) is invisible. Add a
**"What the gates can prove"** section after "Why this exists": a 3-image
row (bolt, 608 bearing, snap enclosure — fresh renders of CURRENT geometry,
copied into `docs/images/`) each with 1–2 lines naming its law (analytic
thread-mesh gate; multi-body orbital gate + negative control; off-origin
swing + travel-limit differential). Renders regenerated from the current
GLBs during implementation — not reused from stale pre-fix eras.

## 3. Blender discovery (kill the macOS-only default)

`claudecad render` currently defaults to one hardcoded macOS path; every
Linux/Windows first run fails confusingly. Root fix in
`claudecad/render/__init__.py`: a `find_blender() -> str` resolution chain —

1. `BLENDER_BIN` env (existing override, unchanged, checked first; error if
   set but not executable — never silently fall through a user's explicit
   setting),
2. `shutil.which("blender")` (PATH — Linux package managers, winget links,
   macOS brew),
3. platform-typical install globs (macOS `/Applications/Blender*.app/...`,
   Windows `C:\Program Files\Blender Foundation\Blender*\blender.exe`,
   Linux `/usr/bin`, `/snap/bin`, `/opt`),
4. else a `FileNotFoundError` that lists what was tried and says exactly
   how to fix it (install Blender or `export BLENDER_BIN=...`).

Unit-tested with monkeypatched env/which/globs; no behavior change on this
machine (env unset → which misses → macOS glob finds Blender 4.5/5.1).

## 4. Folded verification minors (reviewers' deferred list)

- **snapbox pin free-leg control:** module gains `base_through_bored(p)`
  (the blind ends removed — the `outer_race_eccentric` pattern); the gate
  and a test assert the axial escape is FREE through it and BLOCKED through
  the shipped blind-bored base — pinning that the blind ends are what
  retain the pin (causality, not coincidence).
- **bearing osculation upper bound:** validation `osculation <= 0.54`
  (deep-groove conformity band is ~0.515–0.53; value-carrying error). Test.
- **`tests/test_links.py` manifold unification:** route the raw
  `.is_manifold` assertion through `claudecad.verify.check_solid` — one
  manifold notion repo-wide. (Supersedes the filed background chip.)
- **`verify` axis dedup:** extract `_unit_axis(axis) -> Vector` (validate
  nonzero + normalize) used by both `path_clearance` and `screw_clearance`.
- **skill law addendum (band sampling):** one sentence in the mechanisms
  law — blocked-leg sweeps must sample the blocking band densely
  (band-scale distances); envelope-scale distances are for free legs — the
  P3 lesson, currently only in the ledger.

## Verification

Existing 136-test suite green throughout; new unit tests for
`find_blender`, the template's own gate (via the existing scaffolder
end-to-end test, which automatically now exercises the richer template),
the pin free-leg differential, and the osculation bound. Clean-room CI
covers the new template from the wheel. Renders judged (persp views) before
landing in the README.

## Out of scope

`claudecad viewer`; any gate loosening (REST_MAX_GAP headroom stays as-is —
it's a gate); release mechanics (parked per Mike).

## Milestones

1. Spike: template geometry + gates verified; `find_blender` chain proven
   on this machine.
2. Template + scaffolder-contract tests green.
3. Blender discovery + tests.
4. Folded minors (4 items + skill addendum).
5. Fresh renders → docs/images → README section; suite + clean-room green.
