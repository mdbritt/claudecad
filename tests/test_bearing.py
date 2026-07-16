import math

import pytest

from claudecad.hardware.bearing import (
    BearingParams, ball, ball_ring, inner_race, outer_race,
)
from claudecad.verify import check_solid, clearance, intersection_volume


def test_derived_geometry_608():
    p = BearingParams()
    assert math.isclose(p.pitch_radius, 7.5, rel_tol=1e-12)
    assert math.isclose(p.groove_radius, 0.52 * 3.969, rel_tol=1e-12)
    assert math.isclose(p.rest_gap, p.groove_radius - p.ball_d / 2,
                        rel_tol=1e-12)  # 0.0794 at defaults
    # verified spike values
    assert math.isclose(p.inner_shoulder_radius, 6.825, abs_tol=5e-4)
    assert math.isclose(p.outer_shoulder_radius, 8.175, abs_tol=5e-4)


def test_params_validation():
    with pytest.raises(ValueError):
        BearingParams(bore=0.0)
    with pytest.raises(ValueError):
        # capture inequality: shoulder gap must be < ball_d
        BearingParams(shoulder_frac=0.01)
    with pytest.raises(ValueError):
        # balls must fit on the pitch circle (chord spacing > ball_d)
        BearingParams(n_balls=13)


def test_parts_clean():
    p = BearingParams()
    for name, s in (("inner", inner_race(p)), ("outer", outer_race(p)),
                    ("ball", ball(p, 0))):
        r = check_solid(s)
        assert r.ok, f"{name}: valid={r.is_valid} manifold={r.is_manifold} pieces={r.piece_count}"


def test_ball_placement_law():
    p = BearingParams()
    balls = [ball(p, i) for i in range(p.n_balls)]
    # centers on the pitch circle, equal chord spacing, pairwise clear
    chord = 2 * p.pitch_radius * math.sin(math.pi / p.n_balls)
    for i, b in enumerate(balls):
        c = b.center()
        assert math.isclose(math.hypot(c.X, c.Y), p.pitch_radius, abs_tol=1e-9)
        assert abs(c.Z) < 1e-9
    for i in range(p.n_balls):
        j = (i + 1) % p.n_balls
        d = (balls[i].center() - balls[j].center()).length
        assert math.isclose(d, chord, abs_tol=1e-9)
        assert intersection_volume(balls[i], balls[j]) == 0.0
    # spike-verified surface gap between neighbors: 2.5393
    assert math.isclose(clearance(balls[0], balls[1]), chord - p.ball_d,
                        abs_tol=1e-6)


def test_rest_clearance_band():
    """Proof 1: crisp 0 interference AND a positive near-contact gap band."""
    from claudecad.hardware.bearing import REST_MAX_GAP
    p = BearingParams()
    b0, ir, orc = ball(p, 0), inner_race(p), outer_race(p)
    for race in (ir, orc):
        assert intersection_volume(b0, race) == 0.0
        g = clearance(b0, race)
        assert 0 < g <= REST_MAX_GAP
        # spike-verified: gap == rest_gap == 0.0794 at defaults
        assert math.isclose(g, p.rest_gap, abs_tol=1e-3)


def test_orbital_free_spin():
    """Proof 2 (THE multi-body gate): the 7-ball ring, moved as one compound,
    sweeps one 360/n symmetry period with zero interference at every station."""
    from claudecad.hardware.bearing import AXIS, ORBIT_STATIONS
    from claudecad.verify import screw_clearance
    p = BearingParams()
    races = inner_race(p) + outer_race(p)
    vals = screw_clearance(ball_ring(p), races, AXIS, (0, 0, 0),
                           0.0, 1.0 / p.n_balls, ORBIT_STATIONS)
    assert max(vals) == 0.0


def test_capture_differential():
    """Proof 3: ball 0 (all balls congruent by the placement law) is blocked
    radially out/in and axially with both races present; removing the outer
    race frees the radial-out escape — the carabiner differential, per ball."""
    from claudecad.hardware.bearing import escape_distance
    from claudecad.verify import path_clearance
    p = BearingParams()
    b0, ir, orc = ball(p, 0), inner_race(p), outer_race(p)
    races = ir + orc
    d = escape_distance(p)
    assert max(path_clearance(b0, races, (1, 0, 0), d, 9)) > 0.0    # out: blocked
    assert max(path_clearance(b0, races, (-1, 0, 0), p.pitch_radius, 9)) > 0.0  # in
    assert max(path_clearance(b0, races, (0, 0, 1), p.width, 9)) > 0.0          # axial
    assert max(path_clearance(b0, ir, (1, 0, 0), d, 9)) == 0.0      # sans outer: FREE


def test_eccentric_groove_fails_orbit():
    """Negative control (pins the non-tautology claim): an outer race whose
    groove is displaced 0.15 mm off-axis must FAIL the orbital sweep — the
    gate detects broken axisymmetry (spike-verified: iv >= 0.146 at every
    station of the period)."""
    from claudecad.hardware.bearing import (AXIS, ORBIT_STATIONS,
                                            outer_race_eccentric)
    from claudecad.verify import screw_clearance
    p = BearingParams()
    races_bad = inner_race(p) + outer_race_eccentric(p, 0.15)
    vals = screw_clearance(ball_ring(p), races_bad, AXIS, (0, 0, 0),
                           0.0, 1.0 / p.n_balls, ORBIT_STATIONS)
    assert max(vals) > 0.0


def test_osculation_upper_bound():
    # deep-groove conformity runs ~0.515-0.53; a looser groove abandons
    # raceway guidance and only REST_MAX_GAP would catch it at gate time
    with pytest.raises(ValueError, match="osculation"):
        BearingParams(osculation=0.6)
