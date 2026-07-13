"""Centerline curves for swept components."""
from __future__ import annotations

import numpy as np
from build123d import BuildLine, JernArc, Line, Wire


def stadium_wire(straight: float, radius: float) -> Wire:
    """Closed stadium (slot) curve in XY: two straights joined by semicircles.

    Long axis along X, centered at the origin. `straight` is the full length
    of each straight segment; total X extent is straight + 2*radius.
    """
    if straight <= 0 or radius <= 0:
        raise ValueError(
            f"stadium_wire needs straight > 0 and radius > 0, got {straight=} {radius=}"
        )
    h = straight / 2
    with BuildLine() as path:
        Line((-h, radius), (h, radius))
        JernArc(start=(h, radius), tangent=(1, 0), radius=radius, arc_size=-180)
        Line((h, -radius), (-h, -radius))
        JernArc(start=(-h, -radius), tangent=(-1, 0), radius=radius, arc_size=-180)
    return path.wire()


def discretize(wire: Wire, n: int = 256) -> np.ndarray:
    """Sample a wire into an (n,3) point array (open sampling of a closed loop)."""
    return np.array(
        [tuple(wire.position_at(t)) for t in np.linspace(0, 1, n, endpoint=False)]
    )
