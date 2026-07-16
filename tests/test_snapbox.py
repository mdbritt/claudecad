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


def test_swing_arc_free():
    """Proof 1 (off-origin partial arc): the deflected lid sweeps the full
    swing about the hinge axis — center far from the origin — clear of
    base + pin at every station."""
    from claudecad.hardware.snapbox import SWING_STATIONS
    from claudecad.verify import screw_clearance
    p = SnapBoxParams()
    fixed = base(p) + hinge_pin(p)
    vals = screw_clearance(lid(p, "deflected"), fixed, HINGE_AXIS,
                           p.hinge_center, 0.0, p.swing_deg / 360.0,
                           SWING_STATIONS)
    assert max(vals) == 0.0


def test_travel_limit_differential():
    """Proof 2 (same-parameter differential): from the open pose, further
    opening is free through OPEN_FREE_MAX_DEG and blocked by BLOCKED_BY_DEG
    — the stop fin actually limits travel."""
    from claudecad.hardware.snapbox import (
        BLOCKED_BY_DEG, OPEN_FREE_MAX_DEG, OVERTRAVEL_SPAN_DEG,
        OVERTRAVEL_STATIONS, _rot_about)
    from claudecad.verify import screw_clearance
    p = SnapBoxParams()
    fixed = base(p) + hinge_pin(p)
    lid_open = _rot_about(p.hinge_center, HINGE_AXIS, p.swing_deg,
                          lid(p, "deflected"))
    vals = screw_clearance(lid_open, fixed, HINGE_AXIS, p.hinge_center,
                           0.0, OVERTRAVEL_SPAN_DEG / 360.0,
                           OVERTRAVEL_STATIONS)
    step = OVERTRAVEL_SPAN_DEG / (OVERTRAVEL_STATIONS - 1)
    for i, v in enumerate(vals):
        ang = p.swing_deg + i * step
        if ang <= OPEN_FREE_MAX_DEG:
            assert v == 0.0, f"blocked inside travel at {ang} deg: {v}"
        if ang >= BLOCKED_BY_DEG:
            assert v > 0.0, f"free past the stop at {ang} deg"


def test_snap_retention_differential():
    """Proof 3 (the click): over the first RETENTION_SPAN_DEG of opening,
    the RELAXED latch is blocked at some station (nub arcs into the catch)
    while the DEFLECTED latch runs free. Station 0 (at rest) is clear for
    both — the latch holds by blocking MOTION, not by touching."""
    from claudecad.hardware.snapbox import (RETENTION_SPAN_DEG,
                                            RETENTION_STATIONS)
    from claudecad.verify import screw_clearance
    p = SnapBoxParams()
    fixed = base(p) + hinge_pin(p)
    rel = screw_clearance(lid(p, "relaxed"), fixed, HINGE_AXIS,
                          p.hinge_center, 0.0, RETENTION_SPAN_DEG / 360.0,
                          RETENTION_STATIONS)
    dfl = screw_clearance(lid(p, "deflected"), fixed, HINGE_AXIS,
                          p.hinge_center, 0.0, RETENTION_SPAN_DEG / 360.0,
                          RETENTION_STATIONS)
    assert rel[0] == 0.0            # at rest: air gap, not contact
    assert max(rel) > 0.0           # opening arcs the nub into the catch
    assert max(dfl) == 0.0          # deflected: sweeps open free


def test_pin_capture():
    """Proof 4: pin blocked radially both ways and axially both ways
    (blind-ended bore); the escape distances clear the box envelope."""
    from claudecad.hardware.snapbox import pin_escape_distance
    from claudecad.verify import path_clearance
    p = SnapBoxParams()
    fixed = base(p) + lid(p, "relaxed")
    pin = hinge_pin(p)
    d = pin_escape_distance(p)
    for axis in ((0, 0, 1), (0, 1, 0), (1, 0, 0), (-1, 0, 0)):
        assert max(path_clearance(pin, fixed, axis, d, 7)) > 0.0, axis


def test_displaced_center_fails_swing():
    """Negative control (pins the off-origin claim): sweeping about a
    center displaced NEG_CENTER_OFFSET off the true hinge axis must FAIL —
    the gate detects a mis-built hinge. This control would have caught the
    original screw_clearance center bug."""
    from claudecad.hardware.snapbox import NEG_CENTER_OFFSET, SWING_STATIONS
    from claudecad.verify import screw_clearance
    p = SnapBoxParams()
    fixed = base(p) + hinge_pin(p)
    hc = p.hinge_center
    bad_center = (hc[0], hc[1] + NEG_CENTER_OFFSET, hc[2])
    vals = screw_clearance(lid(p, "deflected"), fixed, HINGE_AXIS,
                           bad_center, 0.0, p.swing_deg / 360.0,
                           SWING_STATIONS)
    assert max(vals) > 0.0


def test_pin_axial_free_leg_control():
    """Causality control for pin capture: the axial escape is BLOCKED by the
    shipped blind-bored base and FREE through a through-bored variant — the
    blind ends are WHY the pin stays (outer_race_eccentric pattern)."""
    from claudecad.hardware.snapbox import (base_through_bored,
                                            pin_escape_distance)
    from claudecad.verify import path_clearance
    p = SnapBoxParams()
    pin = hinge_pin(p)
    d = pin_escape_distance(p)
    l = lid(p, "relaxed")
    blocked = max(path_clearance(pin, base(p) + l, (1, 0, 0), d, 7))
    free = max(path_clearance(pin, base_through_bored(p) + l, (1, 0, 0),
                              d, 7))
    assert blocked > 0.0
    assert free == 0.0
