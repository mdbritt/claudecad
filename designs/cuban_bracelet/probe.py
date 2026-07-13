"""Fast pairwise frontier probe for tuning this design without full builds.

Usage: uv run python -m designs.cuban_bracelet.probe '[[twist,pitch,tilt], ...]'
Entries may extend to [twist,pitch,tilt,wire,width]; omitted values fall back
to params.CHAIN.link. Builds links 0..3 of the real bracelet arc — including
the library's chirality alternation (odd links mirrored, see chains._link_bases)
— and reports pair clearances and threading depth as JSON lines: the same
criteria the full gate enforces, at a fraction of the cost. The twisted link
is chiral, so BOTH adjacent junction types are measured: pair (0,1) is the
(+tilt,-tilt) junction, pair (1,2) the (-tilt,+tilt) one. Numbers are ground
truth; renders are not.
"""
import json
import math
import sys

import numpy as np
from build123d import Plane, Pos, Rot, mirror

from claudecad.core.twisted import twisted_centerline_points
from claudecad.jewelry.links import CubanLinkParams, cuban_link
from claudecad.verify import intersection_volume, linking_number

from .params import CHAIN, TARGET_CIRCUMFERENCE


def _is_linked(lk):
    return abs(round(lk)) >= 1 and abs(lk - round(lk)) < 0.1


def probe(twist, pitch, tilt, wire=None, width=None):
    lp = CHAIN.link
    p = CubanLinkParams(length=lp.length, width=width or lp.width,
                        wire_d=wire or lp.wire_d, twist_deg=twist)
    solid_e, _ = cuban_link(p)
    pts_e = twisted_centerline_points(p.length, p.width, p.wire_d, twist, 256)
    # odd links alternate handedness, exactly as chains._link_bases places them
    solid_o = mirror(solid_e, about=Plane.XY)
    pts_o = pts_e * np.array([1.0, 1.0, -1.0])
    n = round(TARGET_CIRCUMFERENCE / pitch)
    radius = n * pitch / (2 * math.pi)
    solids, curves = [], []
    for i in range(4):
        t = tilt if i % 2 == 0 else -tilt
        sol = solid_e if i % 2 == 0 else solid_o
        pts = pts_e if i % 2 == 0 else pts_o
        loc = Rot(Z=360.0 * i / n) * Pos(0, -radius, 0) * Rot(X=t)
        solids.append(loc * sol)
        a = math.radians(t)
        c, s = math.cos(a), math.sin(a)
        rx = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
        q = pts @ rx.T + np.array([0, -radius, 0])
        phi = math.radians(360.0 * i / n)
        c2, s2 = math.cos(phi), math.sin(phi)
        rz = np.array([[c2, -s2, 0], [s2, c2, 0], [0, 0, 1]])
        curves.append(q @ rz.T)
    iv = [intersection_volume(solids[0], solids[j]) for j in (1, 2, 3)]
    lk = [linking_number(curves[0], curves[j]) for j in (1, 2, 3)]
    iv12 = intersection_volume(solids[1], solids[2])
    lk12 = linking_number(curves[1], curves[2])
    linked = [_is_linked(v) for v in lk]
    depth = {(True, False, False): 1, (True, True, False): 2}.get(tuple(linked), 0)
    return {"twist": twist, "pitch": pitch, "tilt": tilt,
            "wire": p.wire_d, "width": p.width,
            "iv": [round(v, 4) for v in iv], "lk": [round(v, 4) for v in lk],
            "iv12": round(iv12, 4), "lk12": round(lk12, 4),
            "depth": depth,
            "ok": all(v == 0.0 for v in iv) and depth > 0
                  and iv12 == 0.0 and _is_linked(lk12)}


if __name__ == "__main__":
    for combo in json.loads(sys.argv[1]):
        print(json.dumps(probe(*combo)), flush=True)
