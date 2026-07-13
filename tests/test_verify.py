import pytest
from build123d import Box, Pos, Torus

from claudecad.verify import SolidReport, check_solid, intersection_volume


def test_check_solid_valid_torus():
    r = check_solid(Torus(20, 3))
    assert r.is_valid and r.is_manifold
    assert r.volume == pytest.approx(3553.06, rel=1e-3)
    assert r.ok


def test_intersection_volume_disjoint_is_exactly_zero():
    assert intersection_volume(Box(10, 10, 10), Pos(100, 0, 0) * Box(10, 10, 10)) == 0.0


def test_intersection_volume_overlapping():
    # unit-offset boxes overlap in a 5x10x10 slab
    v = intersection_volume(Box(10, 10, 10), Pos(5, 0, 0) * Box(10, 10, 10))
    assert v == pytest.approx(500.0, rel=1e-6)
