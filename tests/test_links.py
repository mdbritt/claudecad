import math

import pytest

from claudecad.jewelry.links import LinkParams, curb_link
from claudecad.verify import check_solid


def test_curb_link_valid_solid():
    solid, wire = curb_link(LinkParams())
    assert check_solid(solid).ok


def test_curb_link_outer_dimensions():
    p = LinkParams(length=20.0, width=14.0, wire_d=4.0)
    solid, _ = curb_link(p)
    bb = solid.bounding_box()
    assert bb.max.X - bb.min.X == pytest.approx(p.length, abs=1e-4)
    assert bb.max.Y - bb.min.Y == pytest.approx(p.width, abs=1e-4)
    assert bb.max.Z - bb.min.Z == pytest.approx(p.wire_d, abs=1e-4)


def test_curb_link_volume_matches_sweep():
    p = LinkParams(length=20.0, width=14.0, wire_d=4.0)
    solid, wire = curb_link(p)
    expected = math.pi * (p.wire_d / 2) ** 2 * wire.length
    assert solid.volume == pytest.approx(expected, rel=1e-2)


def test_link_params_validation():
    with pytest.raises(ValueError):
        LinkParams(length=10.0, width=14.0, wire_d=4.0)  # length <= width
    with pytest.raises(ValueError):
        LinkParams(length=20.0, width=4.0, wire_d=4.0)  # wire_d >= width
    with pytest.raises(ValueError):
        LinkParams(length=20.0, width=14.0, wire_d=0.0)  # zero wire
    with pytest.raises(ValueError):
        LinkParams(length=-4.0, width=-14.0, wire_d=-20.0)  # all negative
    with pytest.raises(ValueError):
        LinkParams(length=14.0, width=14.0, wire_d=4.0)  # width == length boundary
    with pytest.raises(ValueError):
        LinkParams(n_centerline=2)
