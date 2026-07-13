import math

import numpy as np
import pytest
from build123d import Box

from claudecad.core.twisted import twisted_centerline_points
from claudecad.jewelry.links import LinkParams, curb_link, CubanLinkParams, cuban_link
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


def test_cuban_link_valid_single_solid():
    solid, wire = cuban_link(CubanLinkParams())
    r = check_solid(solid)
    assert r.ok, r


def test_cuban_link_volume_matches_tube_theorem():
    p = CubanLinkParams()
    solid, _ = cuban_link(p)
    pts = twisted_centerline_points(p.length, p.width, p.wire_d, p.twist_deg, 4000)
    clen = float(np.linalg.norm(np.roll(pts, -1, axis=0) - pts, axis=1).sum())
    expected = math.pi * (p.wire_d / 2) ** 2 * clen
    assert solid.volume == pytest.approx(expected, rel=5e-3)  # spike: <=0.05%


def test_cuban_link_is_boolean_robust_to_slab_cut():
    """The construction law's acid test: a mid-tube slab cut must produce a
    valid, correctly-trimmed result (this is what every forbidden
    construction failed)."""
    solid, _ = cuban_link(CubanLinkParams())
    bb = solid.bounding_box()
    cz = 2.0
    slab = Box((bb.max.X - bb.min.X) + 4, (bb.max.Y - bb.min.Y) + 4, 2 * cz)
    cut = solid & slab
    cbb = cut.bounding_box()
    assert cut.is_valid
    assert cbb.max.Z - cbb.min.Z == pytest.approx(2 * cz, abs=0.01)
    assert 0 < cut.volume < solid.volume


def test_cuban_link_measurement_wire_matches_map():
    p = CubanLinkParams()
    _, wire = cuban_link(p)
    pts = twisted_centerline_points(p.length, p.width, p.wire_d, p.twist_deg, 64)
    from claudecad.core.centerline import discretize
    wpts = discretize(wire, 256)
    for q in pts[::8]:
        assert np.linalg.norm(wpts - q, axis=1).min() < 0.05


def test_cuban_link_params_validation():
    with pytest.raises(ValueError):
        CubanLinkParams(twist_deg=10.0)     # below verified loft range
    with pytest.raises(ValueError):
        CubanLinkParams(twist_deg=75.0)     # above verified loft range
    with pytest.raises(ValueError):
        CubanLinkParams(n_sections=16)
    with pytest.raises(ValueError):
        CubanLinkParams(wire_d=0.0)
