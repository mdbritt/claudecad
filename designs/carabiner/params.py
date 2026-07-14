"""Snap-gate carabiner — every driving dimension, in mm.

Single instance of the hardware pack's CarabinerParams (module defaults
were verified 5/5 in tests/test_carabiner.py; see task-10a-report.md for
the escape-ring derivation). Values here are the DESIGN's choices and may
drift from the module defaults as the visual pass tunes proportions —
the build gate recomputes every functional check on THIS instance.

Frame (from claudecad.hardware.carabiner): body in the XY plane, z=0
midplane, long axis X, gate opening on the +Y straight centered on x=0.
"""
from claudecad.hardware.carabiner import CarabinerParams

# Visual pass, iteration 2 (vs Wikimedia refs: spring-gate snap hooks +
# 1970s steel snap-gate oval): the module defaults (70x40, gap 16) rendered
# squat, gate only ~23% of the side — read as a quick link, not a
# carabiner. References show ~2:1 length:width and the gate spanning
# ~40-45% of the long side. 80x38 (2.1:1) with gap 30 puts the rod at
# ~40% of body_l; wire/gate diameters kept (gate ~= wire, as in the refs).
P = CarabinerParams(
    body_l=80.0,
    body_w=38.0,
    wire_d=8.0,
    gap_l=30.0,
    gate_d=7.0,
    nose_depth=2.0,
    pin_d=2.0,
    clearance=0.3,
)

# path_clearance stations along ESCAPE_AXIS — matches the module tests
ESCAPE_STATIONS = 12
