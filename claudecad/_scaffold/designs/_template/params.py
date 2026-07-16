"""<YOUR DESIGN> — every driving dimension, in mm.

Rules (see .claude/skills/cad/SKILL.md): driving params only; derived
values are computed by the library and printed by build.py, never set here.
This starter is a PEG-AND-SOCKET fit — replace it with your design, but
keep the shape: params here, parts + gate in build.py.
"""
BASE_L = 30.0          # base block footprint
BASE_W = 30.0
BASE_H = 14.0
PEG_D = 8.0            # peg diameter
PEG_STICKOUT = 12.0    # how far the peg stands proud of the base top
BORE_DEPTH = 10.0      # socket depth into the base
FIT_CLEARANCE = 0.2    # radial + seat air gap: parts NEVER touch
