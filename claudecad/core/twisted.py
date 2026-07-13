"""Exact twisted-stadium centerline: the cuban link's spine.

Map: planar stadium point (x, y, 0) -> (x, y cos(kx), y sin(kx)) with
k = radians(twist_deg) / (2 * x_max), x_max = h + r — a linear twist ramp
about the long (X) axis reaching +-twist_deg/2 at the ends. Everything here
is closed-form; no geometry kernel calls.
"""
from __future__ import annotations

import math

import numpy as np
from build123d import Vector


def _params(length: float, width: float, wire_d: float):
    if not (0 < wire_d < width < length):
        raise ValueError(
            f"need 0 < wire_d < width < length, got "
            f"wire_d={wire_d} width={width} length={length}"
        )
    r = (width - wire_d) / 2
    h = (length - width) / 2
    return r, h


def twisted_stadium_frame(
    length: float, width: float, wire_d: float, twist_deg: float, u: float
) -> tuple[Vector, Vector, Vector]:
    """Exact (point, unit tangent, section x_dir) at arc-parameter u in [0,1).

    x_dir is derived from the twisted vertical (0, -sin(kx), cos(kx)) —
    smooth and periodic around the loop, so consecutive loft sections
    never flip orientation.
    """
    r, h = _params(length, width, wire_d)
    x_max = h + r
    k = math.radians(twist_deg) / (2 * x_max)
    seg = [2 * h, math.pi * r, 2 * h, math.pi * r]
    total = sum(seg)
    d = (u % 1.0) * total
    if d < seg[0]:                                   # top straight
        x, y = -h + d, r
        dx, dy = 1.0, 0.0
    elif d < seg[0] + seg[1]:                        # right arc
        a = (d - seg[0]) / r
        x, y = h + r * math.sin(a), r * math.cos(a)
        dx, dy = math.cos(a), -math.sin(a)
    elif d < seg[0] + seg[1] + seg[2]:               # bottom straight
        x, y = h - (d - seg[0] - seg[1]), -r
        dx, dy = -1.0, 0.0
    else:                                            # left arc
        a = (d - seg[0] - seg[1] - seg[2]) / r
        x, y = -h - r * math.sin(a), -r * math.cos(a)
        dx, dy = -math.cos(a), math.sin(a)
    phi = k * x
    c, s = math.cos(phi), math.sin(phi)
    p = Vector(x, y * c, y * s)
    dphi = k * dx
    t = Vector(dx, dy * c - y * s * dphi, dy * s + y * c * dphi).normalized()
    up = Vector(0, -s, c)
    x_dir = t.cross(up).normalized()
    return p, t, x_dir


def twisted_centerline_points(
    length: float, width: float, wire_d: float, twist_deg: float, n: int
) -> np.ndarray:
    """(n,3) exact samples of the twisted centerline (endpoint-exclusive)."""
    return np.array(
        [
            tuple(twisted_stadium_frame(length, width, wire_d, twist_deg, i / n)[0])
            for i in range(n)
        ]
    )
