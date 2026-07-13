import math

import numpy as np
import pytest

from claudecad.core.centerline import discretize, stadium_wire


def test_stadium_wire_closed_and_length():
    w = stadium_wire(straight=12.0, radius=5.0)
    assert w.is_closed
    assert w.length == pytest.approx(2 * 12.0 + 2 * math.pi * 5.0, rel=1e-6)


def test_stadium_wire_extents():
    w = stadium_wire(straight=12.0, radius=5.0)
    bb = w.bounding_box()
    assert bb.max.X - bb.min.X == pytest.approx(12.0 + 2 * 5.0, rel=1e-6)
    assert bb.max.Y - bb.min.Y == pytest.approx(2 * 5.0, rel=1e-6)
    assert abs(bb.max.Z) < 1e-6 and abs(bb.min.Z) < 1e-6


def test_stadium_wire_centered():
    bb = stadium_wire(straight=12.0, radius=5.0).bounding_box()
    assert bb.center().length == pytest.approx(0.0, abs=1e-6)


def test_discretize_shape_and_closure():
    w = stadium_wire(straight=12.0, radius=5.0)
    pts = discretize(w, n=200)
    assert pts.shape == (200, 3)
    # endpoint=False: last point must not duplicate the first
    assert np.linalg.norm(pts[0] - pts[-1]) > 1e-3


def test_degenerate_params_rejected():
    with pytest.raises(ValueError):
        stadium_wire(straight=0.0, radius=5.0)
    with pytest.raises(ValueError):
        stadium_wire(straight=10.0, radius=0.0)
