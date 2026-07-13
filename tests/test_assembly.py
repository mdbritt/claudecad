import pytest
from build123d import Box, Pos

from claudecad.assembly import expand, relieve
from claudecad.verify import check_solid, clearance, intersection_volume


def test_expand_grows_in_axis_directions():
    e = expand(Box(10, 10, 10), 1.0)
    bb = e.bounding_box()
    assert bb.max.X - bb.min.X == pytest.approx(12.0, abs=1e-6)
    assert check_solid(e).ok


def test_relieve_cuts_clearance_pocket():
    target = Box(30, 30, 30)
    cutter = Pos(15, 0, 0) * Box(10, 10, 10)   # overlaps the +X face region
    relieved = relieve(target, [cutter], clearance=0.4)
    assert check_solid(relieved).ok
    assert relieved.volume < target.volume
    assert intersection_volume(relieved, cutter) == 0.0
    # axis-direction clearance is the guaranteed bound
    assert clearance(relieved, cutter) <= 0.4 + 1e-6


def test_relieve_validation():
    with pytest.raises(ValueError):
        relieve(Box(1, 1, 1), [], clearance=0.4)
    with pytest.raises(ValueError):
        relieve(Box(1, 1, 1), [Box(1, 1, 1)], clearance=-0.1)
