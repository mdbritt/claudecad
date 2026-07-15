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
