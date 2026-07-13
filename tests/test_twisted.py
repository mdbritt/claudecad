import math

import numpy as np
import pytest

from claudecad.core.centerline import discretize, stadium_wire
from claudecad.core.twisted import twisted_centerline_points, twisted_stadium_frame


def test_zero_twist_matches_planar_stadium():
    """twist=0 must reproduce the planar stadium centerline exactly."""
    L, W, D = 20.0, 14.0, 4.1
    pts = twisted_centerline_points(L, W, D, 0.0, 256)
    wire_pts = discretize(stadium_wire(L - W, (W - D) / 2), 256)
    # same closed curve; sampling may start at a different point, so compare
    # as sets via nearest-neighbour distance
    for p in pts[:: 16]:
        d = np.linalg.norm(wire_pts - p, axis=1).min()
        assert d < 0.02, f"point {p} is {d} from the planar stadium"


def test_frame_properties():
    L, W, D, T = 20.0, 14.0, 4.1, 45.0
    for u in (0.0, 0.13, 0.35, 0.5, 0.77, 0.99):
        p, t, xd = twisted_stadium_frame(L, W, D, T, u)
        assert abs(t.length - 1.0) < 1e-9          # unit tangent
        assert abs(xd.length - 1.0) < 1e-9         # unit x_dir
        assert abs(t.dot(xd)) < 1e-9               # orthogonal frame


def test_extents_and_closure():
    L, W, D, T = 20.0, 14.0, 4.1, 60.0
    pts = twisted_centerline_points(L, W, D, T, 512)
    xmax = (L - D) / 2
    assert pts[:, 0].max() == pytest.approx(xmax, abs=1e-6)
    assert pts[:, 0].min() == pytest.approx(-xmax, abs=1e-6)
    # closure: first and last samples are one step apart, not far apart
    step = np.linalg.norm(pts[1] - pts[0])
    assert np.linalg.norm(pts[0] - pts[-1]) < 3 * step


def test_twist_rotates_material_out_of_plane():
    """At x=0 the twist is zero (point stays in-plane); at the end of the
    top straight (x = h) the material is clearly rotated out of plane."""
    L, W, D, T = 20.0, 14.0, 4.1, 60.0
    pts = twisted_centerline_points(L, W, D, T, 1024)
    r, h = (W - D) / 2, (L - W) / 2
    mid_top = pts[np.argmin(np.abs(pts[:, 0]))]      # x ~ 0, pre-twist (0, +-r, 0)
    assert abs(mid_top[2]) < 0.05                    # still in-plane at the center
    assert abs(abs(mid_top[1]) - r) < 0.05
    near_end = pts[np.argmin(np.abs(pts[:, 0] - h))]  # straight/arc junction
    phi = math.atan2(near_end[2], near_end[1])
    # expected twist at x=h: T/2 * h/(h+r) ~ 11.3 deg for these dims
    assert phi > math.radians(5)


def test_degenerate_params_rejected():
    with pytest.raises(ValueError):
        twisted_stadium_frame(10.0, 14.0, 4.1, 45.0, 0.0)   # length <= width
    with pytest.raises(ValueError):
        twisted_centerline_points(20.0, 14.0, 0.0, 45.0, 64)  # wire_d <= 0
