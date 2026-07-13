# Task 3 report: latches, pins, and attachment loops

## TDD evidence

1. Appended the brief's Step-1 tests verbatim to `tests/test_clasps.py`
   (plus the needed imports: `Rot`, `ClaspAssembly`, `attachment_loop`,
   `box_clasp`, `clasp_latch`, `clasp_pin`, `LinkParams`, `curb_link`,
   `discretize`, `linking_number`, `numpy`).
2. Ran `uv run pytest tests/test_clasps.py -v` before writing any
   implementation: `ImportError` (no `clasp_latch` etc. in `clasps.py`),
   confirming the new tests failed for the expected reason.
3. Implemented per the brief's Step-3 skeleton, then iterated against
   real pytest failures (not just my own arithmetic) until everything
   was green. Two rounds of failures, both root-caused and fixed
   honestly rather than by loosening any test:
   - Round 1: boss-as-drawn grew the box's Y bounding box, breaking the
     already-passing Task 2 test `test_box_outer_dims_match_chain`, and
     `attachment_loop` (flat rectangle) never linked with the flat
     end-link fixture (`Lk == 0` at every X offset tried, including the
     brief's own `dx=10`).
   - Round 2 (after redesign, see below): `uv run pytest
     tests/test_clasps.py -v` → **11 passed**.
4. Final full-suite run: `uv run pytest tests/ -v` → **68 passed**, 14
   lib3mf `DeprecationWarning`s (pre-existing, unrelated noise, called
   out in the task prompt).

## Geometry adjustments (deviations from the brief's Step-3 pseudocode)

The brief's literal pseudocode does not survive contact with two
already-committed Task 2 constraints. Both deviations are documented
inline in `clasps.py`; summarized here with the reasoning.

### 1. The ear boss: grows inward, not outward

Controller guidance said to anchor the pin in real box material with a
boss "on the outside face." Built literally (boss cylinder centered
outboard of `box_w/2`, per the brief's `_pin_axis` formula `box_w/2 +
latch_t/2`), this enlarges the box's Y bounding box past `box_w` —
which breaks `test_box_outer_dims_match_chain`, an **already-passing
Task 2 test** I'm not allowed to touch (append-only test file per this
task's contract, and that test isn't even one of Task 3's new tests).

Fix: the boss's outer face stays flush with the box's existing outer Y
face (so the bounding box is provably unchanged — verified, that test
still passes), and the boss grows **inward** into the cavity instead,
locally thickening the wall from 0.8mm to `wall + _BOSS_D` (0.8 + 0.8 =
1.6mm) at the pin axis. This is safe because `__post_init__` already
guarantees slack between the cavity wall (`box_w/2 - wall` = 6.7mm) and
the tongue blade/leaf's half-width (`blade_w/2` = 5.0mm) — the boss
occupies only part of that 1.7mm slack (reaching to 5.9mm), leaving a
verified-clear 0.9mm margin from the blade/leaf, and the boss's X
position (`ax = 2.5`, `boss_r = 1.35`) was chosen so its footprint
(`x∈[1.15, 3.85]`) never reaches `x ≤ 0`, keeping it clear of the
tongue lug ears (`x∈[-5,0]`, which reach the same Y band the boss
occupies). The bore overshoots outward into open air (harmless — no
material there) and only slightly inward past the boss's own face
(0.3mm, still 0.6mm clear of the blade/leaf).

Net result: `clasp_pin` now sits in ~1.6mm of real, boxed-in box
material (boss + original wall) instead of floating in air, and the
box's advertised outer dimensions are provably unchanged.

### 2. The latch: arm + Y-wide catch flange, not arm + small hook

Read literally, the brief's `_pin_axis` (`ay = box_w/2 + latch_t/2`,
~8mm) places the latch entirely outside the tongue's own Y-extent
(blade/button ≤ 5mm, lug ears ≤ 6.5mm) in **both** the seated and
guarded (shifted -2mm) tongue states — X-translation alone can't create
a Y-overlap that doesn't already exist, so `test_latch_guards_extraction`
can never pass with that geometry (confirmed by direct calculation
before touching the file, not just guessed at).

Fix: kept the "arm" (thin strip, pivots at the boss, crosses the x=0
seam) but replaced the hook with a Y-wide "catch" flange that bridges
from genuine overlap with the arm (real volume overlap, ≥0.3mm — not
edge-touching, learned from Task 2's `fold_overlap` lesson about
piece_count) all the way inward to the tongue lug ear's Y-span
(`ear_gap/2 + 1.0` = 4.0mm, safely inside the ear's `[3.0, 6.5]` band).
In X, the catch sits in `[-lug_l - 1.5, -lug_l - 0.5]` (default:
`[-6.5, -5.5]`) — strictly beyond the ear's seated rear edge (`x = -5`,
margin 0.5mm) but strictly within the ear's shifted range after a -2mm
extraction (`x∈[-7,-2]`, margin 0.5mm on the far side too). That
0.5/0.5mm margin (not a hairline touch) is why the guard test passes
robustly rather than by luck.

Known minor inconsistency: `BoxClaspParams.latch_arm` (a Task 2 field,
default 8.0) is validated (`>0`) but **not consumed** by this
redesigned latch — the arm's reach is derived independently from
`lug_l` and the catch geometry so the overlap margins above hold for
any `lug_l`. Wiring `latch_arm` back in would either be inert (its
default is too short to reach the catch zone, so a defensive `min()`
would silently ignore it) or require bumping its default, which felt
riskier than leaving it visibly unused. Flagging rather than hiding.

### 3. `attachment_loop`: a real 3D dip, not a flat rectangle

The brief's flat (`z=0` throughout) rectangle can never link with
`curb_link`'s wire, which is *also* exactly planar at `z=0` ("both
centered at the origin in the XY plane" per its own docstring). Two
coplanar closed curves have `Lk=0` by construction — I verified this
directly (not just by running the one test) by sweeping the link's X
offset from 0 to 20mm including the brief's own `dx=10`: `Lk` was
`0.0` at every single offset. This is not an "edge of the opening"
problem the exception note anticipates (fixable by nudging `Pos`) — no
translation fixes coplanarity.

Fix: redesigned `attachment_loop` to genuinely leave the plane. It
dips through `z=0` exactly **once**, under the bar itself (a single
clean crossing at `x=bx`, the real bar's own x — exactly where an end
link resting flat over the bar would be), then stays off-plane through
the return leg, and dips back a **second** time only at `x=rx`, deep
inside the box/tongue body and outside any real end link's X-footprint
— so that second crossing can't land inside a link's hole and cancel
the first one (two crossings under the same hole is exactly the
degenerate case that gives `Lk=0`, same failure mode as the flat
rectangle). Verified numerically before committing: at the test's
existing `dx=10` link placement, `Lk ≈ -1.0007` (and `-0.9995` at
`dx=5`; `≈0` at `dx=0/15/20`, confirming the design is discriminating,
not just accidentally hitting 1 everywhere).

**No change was needed to the test's link `Pos`** — the fix lives
entirely in `attachment_loop`'s own geometry (explicitly allowed:
"tests are the spec; builder-internal offsets adjustable"), so I did
not need to invoke the LINK-PLACEMENT exception at all.

## Files changed

- `claudecad/jewelry/clasps.py` — appended `_pin_axis`, `_boss_span`,
  `clasp_latch`, `clasp_pin`, `attachment_loop`, `ClaspAssembly`,
  `box_clasp`; modified `clasp_box` (Task 2) to add the two pivot ear
  bosses, per controller guidance.
- `tests/test_clasps.py` — appended the brief's Step-1 tests verbatim
  (imports adjusted); no existing Task 2 test was modified.

## Commit

```
[feature/box-clasp 2ba84f8] feat: hinged safety latches, pivot pins, and attachment loops
 2 files changed, 275 insertions(+), 4 deletions(-)
```

## Self-review

- **Placeholders / TODOs**: none.
- **Consistency**: `_pin_axis`, `_boss_span`, `clasp_latch`,
  `clasp_pin` all derive from the same shared constants
  (`_BOSS_D`, `_LATCH_GAP`, etc.) — the pin's concentricity with both
  bores is structural (same `ax`, `az`), not coincidental.
- **Scope**: touched `clasp_box` only for the boss addition (explicitly
  authorized by controller guidance); no other Task 2 code or test
  changed.
- **Ambiguity flagged above**: `latch_arm` param now unused — see §2.
- **Margins are real, not hairline**: every boolean-zero assertion in
  the new tests (`test_assembly_parts_clean_and_clear`,
  `test_pin_concentric_with_clearance`, guard test's seated-state
  clearance) has ≥0.1mm of deliberate margin baked into the offsets,
  verified by rerunning after each change rather than by inspection
  alone.
- **Full regression**: all 57 pre-existing tests across the other
  modules (`chains`, `links`, `verify`, `centerline`, `twisted`,
  `finishing`, `export`, `render_smoke`, `scaffold`) still pass
  unmodified — this task touched only `clasps.py`/`test_clasps.py`.

## Note on this report's path

`.superpowers/sdd/task-3-report.md` previously held an unrelated report
("Cuban Link Component (Ruled Loft)") from an earlier phase's task
numbering that also used "3". This file has been overwritten with the
current task's report per the task prompt's explicit instruction to
write here; the stale content is recoverable from git history
(`git log -- .superpowers/sdd/task-3-report.md`) if it's still needed
under a different filename.

## Fix round 1

Code review findings from 2026-07-13 round applied:

1. **Wired dead `latch_arm` parameter**: arm's x-reach now derives from `p.latch_arm` via formula `arm_x_lo = ax - (p.latch_arm + _ARM_REACH_MARGIN)` with `_ARM_REACH_MARGIN = 1.3`. Geometry bit-identical at default: arm span = 9.3 (reaches from 2.5 down to -6.8). Updated `BoxClaspParams.latch_arm` docstring to note it drives strap reach.

2. **Hoisted duplicate `ear_gap = 6.0`**: defined module constant `_EAR_GAP = 6.0` replacing three instances in `clasp_box`, `clasp_tongue`, and `clasp_latch` (load-bearing for guard's Y engagement in catch flange).

Verification: scratch run confirms reach = 2.5 - (-6.8) = 9.3 at defaults; `uv run pytest tests/test_clasps.py -v` → **11 passed** (geometry preserved).

Commit: `1049f24` "refactor: wire latch_arm to strap reach; hoist shared ear-gap constant"
