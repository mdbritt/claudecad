import numpy as np
import pytest
from build123d import Box, Pos, Rot, Torus

from claudecad.verify import ChainReport, SolidReport, check_chain, check_solid, intersection_volume, linking_number


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


def _circle(n=400, radius=1.0, center=(0, 0, 0), plane="xy"):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    zeros = np.zeros_like(t)
    if plane == "xy":
        pts = np.stack([np.cos(t), np.sin(t), zeros], axis=1)
    else:  # xz
        pts = np.stack([np.cos(t), zeros, np.sin(t)], axis=1)
    return radius * pts + np.asarray(center)


def test_linking_number_hopf_link():
    lk = linking_number(_circle(), _circle(center=(1, 0, 0), plane="xz"))
    assert round(lk) in (-1, 1)
    assert abs(lk - round(lk)) < 0.01


def test_linking_number_unlinked():
    assert abs(linking_number(_circle(), _circle(center=(10, 0, 0), plane="xz"))) < 0.01


def test_linking_number_coplanar_unthreaded():
    # overlapping projections but not threaded
    assert abs(linking_number(_circle(), _circle(center=(1.5, 0, 0)))) < 0.01


def _hopf_tori():
    """Two interlocked tori (solid Hopf link) + their centerline circles."""
    a = Torus(10, 1.5)
    b = Pos(10, 0, 0) * Rot(X=90) * Torus(10, 1.5)
    ca = 10 * _circle()
    cb = _circle(radius=10, center=(10, 0, 0), plane="xz")
    return [(a, ca), (b, cb)]


def test_check_chain_interlocked_pair_passes():
    report = check_chain(_hopf_tori())
    assert isinstance(report, ChainReport)
    assert report.ok, report.failures()


def test_check_chain_fails_on_unlinked_adjacent():
    a = Torus(10, 1.5)
    b = Pos(50, 0, 0) * Torus(10, 1.5)
    report = check_chain([(a, 10 * _circle()), (b, 10 * _circle() + (50, 0, 0))])
    assert not report.ok
    assert any("not interlocked" in f for f in report.failures())


def test_check_chain_fails_on_interpenetration():
    a = Torus(10, 1.5)
    b = Pos(2, 0, 0) * Torus(10, 1.5)  # same plane, overlapping tubes
    report = check_chain([(a, 10 * _circle()), (b, 10 * _circle() + (2, 0, 0))])
    assert not report.ok
    assert any("interpenetrates" in f for f in report.failures())


def test_check_chain_closed_adds_wraparound_adjacency():
    """closed=True makes (first, last) adjacent: three disjoint tori in a row
    must then fail with THREE 'not interlocked' pairs, including (0, 2)."""
    items = [
        (Pos(50 * i, 0, 0) * Torus(10, 1.5), 10 * _circle() + (50 * i, 0, 0))
        for i in range(3)
    ]
    open_report = check_chain(items, closed=False)
    closed_report = check_chain(items, closed=True)
    open_failures = [f for f in open_report.failures() if "not interlocked" in f]
    closed_failures = [f for f in closed_report.failures() if "not interlocked" in f]
    assert len(open_failures) == 2   # (0,1), (1,2)
    assert len(closed_failures) == 3  # + wraparound (0,2)
    assert any("0,2" in f for f in closed_failures)
