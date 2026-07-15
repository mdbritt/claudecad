import math

import pytest

from claudecad.hardware.snapbox import (
    HINGE_AXIS, SnapBoxParams, base, hinge_pin, lid,
)
from claudecad.verify import check_solid, clearance, intersection_volume


def test_derived_geometry():
    p = SnapBoxParams()
    # hinge height is DERIVED: base_h + knuckle radius + clearance — the
    # spike caught an exact knuckle-to-wall tangency at anything less
    assert p.hinge_center == (0.0, -15.0, 15.15)
    assert math.isclose(p.bore_radius, 1.15, rel_tol=1e-12)
    assert math.isclose(p.lid_z0, 12.15, rel_tol=1e-12)


def test_params_validation():
    with pytest.raises(ValueError):
        SnapBoxParams(wall=0.0)
    with pytest.raises(ValueError):
        # stop must lie beyond the swing range
        SnapBoxParams(stop_fin_deg=85.0)
    with pytest.raises(ValueError):
        # pin (+2*clearance) must fit inside the knuckle
        SnapBoxParams(pin_d=6.0)


def test_parts_clean():
    p = SnapBoxParams()
    for name, s in (("base", base(p)), ("lid_relaxed", lid(p, "relaxed")),
                    ("lid_deflected", lid(p, "deflected")),
                    ("pin", hinge_pin(p))):
        r = check_solid(s)
        assert r.ok, f"{name}: valid={r.is_valid} manifold={r.is_manifold} pieces={r.piece_count}"


def test_lid_states_differ_only_in_snap():
    # same volume to within the tilt's sliver; both single solids
    p = SnapBoxParams()
    vr, vd = lid(p, "relaxed").volume, lid(p, "deflected").volume
    assert abs(vr - vd) < 5.0
    with pytest.raises(ValueError):
        lid(p, "open")  # invalid state name


def test_shipped_pose_clearances():
    """Closed, relaxed, pin seated: crisp 0 everywhere, real air gaps."""
    p = SnapBoxParams()
    b, l, pin = base(p), lid(p, "relaxed"), hinge_pin(p)
    assert intersection_volume(b, l) == 0.0
    assert intersection_volume(b, pin) == 0.0
    assert intersection_volume(l, pin) == 0.0
    assert math.isclose(clearance(pin, b), p.clearance, abs_tol=1e-6)
    assert math.isclose(clearance(pin, l), p.clearance, abs_tol=1e-6)
    assert math.isclose(clearance(l, b), p.clearance, abs_tol=1e-2)
