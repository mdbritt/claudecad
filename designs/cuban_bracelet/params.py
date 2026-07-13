"""Cuban link bracelet — every driving dimension, in mm.

Derived values (link count, loop radius) are computed by closed_loop()
and printed by build.py; they are outputs, not inputs.
"""
from claudecad.jewelry.chains import ChainParams
from claudecad.jewelry.links import LinkParams

# bracelet centerline circumference: wrist + wearing ease
TARGET_CIRCUMFERENCE = 200.0

# tilt/wire chosen from a closed-loop clearance probe (2026-07-12, pitch 10,
# link 20x14): wire 4.2 grazes at tilt 36, wire 4.0 at tilt 30, wire >=4.3
# never clears. tilt 34/wire 4.1 is the flattest-lying clean combo with
# margin; flat lie + thick wire are what make the chain read as cuban.
CHAIN = ChainParams(
    link=LinkParams(length=20.0, width=14.0, wire_d=4.1),
    tilt_deg=34.0,
    pitch=10.0,
)
