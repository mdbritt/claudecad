"""Cuban link bracelet — every driving dimension, in mm.

Derived values (link count, loop radius) are computed by closed_loop()
and printed by build.py; they are outputs, not inputs.

Config verified 2026-07-13 (probe on the real arc, ruled-loft construction,
chirality-alternating placement — odd links mirrored, chains._link_bases):
link 20x15x4.0, twist 45, pitch 10, tilt 30 — both adjacent junction types
zero intersection, neighbors |Lk|=1, links two apart unlinked (interlock
depth 1). Frontier: tilt 29 grazes (iv=0.086 mm^3), width 14.5 at tilt 34
grazes (0.069), wire 4.1 at tilt 30 grazes (0.175).

History: the plan's original config (20x14x4.1, twist 60, tilt 20) had been
verified only on the (0,1) junction; the first full 20-link gate run failed
every (odd,even) neighbor pair with an identical 119.531 mm^3 / Lk=0 —
identical chiral links make the two adjacent junction types non-congruent.
The escape hatch (tilt->25, twist->45) could not close it (best 73.9 mm^3);
the fix is alternating link handedness (see chains._link_bases), after which
one junction law governs all pairs and the grid re-tune below applies.
Re-tune at pitch 10 (0.5 x length — reference-calibrated Miami density,
kept fixed): tilt is the strong lever but stalls in a grazing tail from a
tip-to-outer-wall tangency below the cut plane; width 14->15 breaks it.
Chosen 45/30/4.0/15 over 60/34/4.1/15 (also exactly zero) for the visibly
flatter lie — beats v1's tilt 34.
"""
from claudecad.jewelry.chains import ChainParams
from claudecad.jewelry.links import CubanLinkParams

# bracelet centerline circumference: wrist + wearing ease
TARGET_CIRCUMFERENCE = 200.0

CHAIN = ChainParams(
    # n_sections 256: the default 144 showed faint transverse banding on the
    # tube in the render detail view (iteration 1); 192 reduced but did not
    # kill it under glossy metal (iteration 2 — normal-interpolation ripple
    # across ruled strips), 256 + finer GLB tessellation does
    link=CubanLinkParams(length=20.0, width=15.0, wire_d=4.0, twist_deg=45.0,
                         n_sections=256),
    tilt_deg=30.0,
    pitch=10.0,
)

# diamond cut: keep |z| <= CUT_Z after assembly, tuned visually within
# [2.4, 3.2] — the gate (piece_count) protects against severing at any
# value. 2.8 gave clean but narrow flats (iteration 1); 2.6 widens them
# toward the reference look (facets dominate the top view).
CUT_Z = 2.6

# neighbors thread once each side at pitch 10 (probe: lk02 = 0)
INTERLOCK_DEPTH = 1
