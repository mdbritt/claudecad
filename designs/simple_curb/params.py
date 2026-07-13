"""Simple planar curb bracelet — the gentle-entry example (~15 lines).

Uses the v1-verified planar config: see ChainParams' docstring for the
sweep evidence (pitch 10/tilt 55 is the verified planar combination).
"""
from claudecad.jewelry.chains import ChainParams
from claudecad.jewelry.links import LinkParams

TARGET_CIRCUMFERENCE = 200.0
CHAIN = ChainParams(link=LinkParams(length=20.0, width=14.0, wire_d=4.0),
                    tilt_deg=55.0, pitch=10.0)
