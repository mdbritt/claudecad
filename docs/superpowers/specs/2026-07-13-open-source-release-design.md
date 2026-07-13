# claudeCAD open-source release + generality iteration

**Date:** 2026-07-13
**Status:** Approved
**Predecessors:** all prior specs (2026-07-12 system, 2026-07-13 twisted link,
2026-07-13 box clasp)

## Problem

claudeCAD is ready to be public, but its accumulated artifacts read as a
cuban-link project. The cuban bracelet was always the BENCHMARK — the
product is the general system: a verification-first parametric CAD
workspace built for designing with Claude Code. The release must position
it that way, and the next functionality must serve generality, not deeper
chain tuning.

## Positioning (binding for all docs written in this cycle)

- The system = the design loop (params -> build -> verify -> render ->
  iterate -> STEP to the user's CAD app), the verification-first rules
  (topological interlock via Gauss linking number, boolean clearance gates,
  constructed-state mechanism proofs), the tools (headless Blender render
  pipeline, bundled localhost STEP viewer, named STEP assembly export), and
  the /cad skill that teaches Claude the workflow in any clone.
- `claudecad/core` + `claudecad/verify.py` + `tools/` = the heart
  (domain-neutral). `claudecad/jewelry/` = a DOMAIN PACK, the worked example
  of growing a domain library. `designs/` = examples.
- The cuban bracelet is presented as the benchmark that battle-tested the
  system; the spec/plan evidence trail in docs/superpowers is presented as
  the method's proof, not chain lore.

## Stage 1 — Release (repo public at the end of this stage)

1. Hygiene: untrack the stray `.superpowers` file (scratch stays local);
   pytest `filterwarnings` for the upstream lib3mf DeprecationWarnings so a
   fresh clone sees a pristine run; fast import-smoke test for `designs/`.
2. LICENSE: Apache-2.0, (c) 2026 Mike Britt.
3. README.md: hero renders (copied to `docs/images/`), system-first story
   per Positioning, quickstart (uv sync -> build a design -> view in the
   bundled STEP viewer), Claude Code section (the /cad skill), architecture
   map, evidence-trail pointer, CI badge, license badge.
4. CONTRIBUTING.md (short): spec -> plan -> gate discipline; never weaken a
   check; construction laws live in the specs; new domains come as domain
   packs with their own gates.
5. CI: `.github/workflows/ci.yml` — ubuntu-latest, uv, full pytest; the two
   Blender render tests skip via a `BLENDER_BIN`-presence marker (render
   fidelity stays a local capability, documented in README).
6. `/cad` skill restructured: general laws first (verification ground
   truth; OCCT construction laws — general kernel knowledge; mechanism
   constructed-states law), jewelry learnings sectioned as domain notes.
7. `designs/simple_curb/`: ~15-line planar bracelet using existing parts —
   the gentle entry example.
8. Publish: `gh repo create mdbritt/claudecad --public` + push main +
   verify the GitHub Actions run is green (the badge's first proof).

## Stage 2 — Generality iteration (on the live repo)

1. **Clearance verification (general):** `clearance(a, b) -> float` in
   verify.py (exact OCCT minimum-distance query; API spike-checked during
   planning) and an optional near-contact criterion in the chain checks
   (`max_gap`: adjacent pairs must sit within a clearance band — touching
   or near-touching — not merely non-penetrating). Domain-neutral mechanism
   verification; also documents (not fixes) the v2 "chain reads slightly
   open" residual as a tunable.
2. **Relief promotion (general):** the benchmark's relief-slot helper is
   generic assembly finishing (expand cutter solids by a clearance, subtract
   from a target), not jewelry-specific — promote it to a new domain-neutral
   `claudecad/assembly.py` as `relieve(target, cutters, clearance) -> Solid`
   with tests; the cuban design calls it.
3. **Design template:** `designs/_template/` (params.py + build.py skeleton
   with the gate composed in and comments showing where checks plug in) +
   a short `docs/new-design-recipe.md` linked from README.
4. **Carabiner example (the generality proof):** `designs/carabiner/` — a
   spring-gate carabiner in a new domain pack `claudecad/hardware/`:
   body (open C-profile solid), gate modeled in two constructed states
   (closed: gate tip seats in the nose with clearance; open: swung in,
   proving the swing path via path_clearance), pivot pin, spring modeled as
   the gate's two states (no FEA — same law as the clasp tongue). Gates:
   closed-gate loop is topologically closed for a test ring threaded on the
   body (linking number = 1 vs a synthetic ring through the aperture...
   precisely: a ring threaded through the closed carabiner must be linked
   (Lk=1) and must have zero intersection; with the gate OPEN, the same
   ring can be translated out through the gap along an escape path with
   zero intersection at every station (path_clearance) — the open/closed
   differential IS the carabiner's function, provable statically.
5. Small cleanups riding along: ear_w dedup in clasps.py; tongue-end
   attachment_loop unit test; open_arc gap frames — consume in the
   benchmark placement if it reads better, else document as probe-only
   (implementer judges, reviewer checks).

## Out of scope

- Denser cuban tuning, probe/library unification beyond what stage-2 items
  touch, box-clasp cosmetics — deferred to real usage/demand.
- PyPI packaging (repo-first release; revisit on demand).
- Windows/Linux Blender path presets beyond the BLENDER_BIN env override.

## Verification & testing

- Stage 1: every claim runnable — fresh-clone quickstart commands executed
  as written before publish; CI verified green on the real GitHub run;
  pristine pytest output (no warnings) confirmed.
- Stage 2: existing TDD + gate discipline; carabiner acceptance = its
  open/closed differential gates green + renders read as a real carabiner
  vs reference photos + STEP imports clean.

## Milestones

1. Hygiene + license + CI workflow + skill restructure (local, tested).
2. README + CONTRIBUTING + images + simple_curb + quickstart dry-run.
3. Publish + CI-green verification. (Repo is live.)
4. Clearance verification + assembly.relieve + template + cleanups.
5. Carabiner domain pack + example + acceptance.
