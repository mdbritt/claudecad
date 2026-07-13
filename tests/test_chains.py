import math

import numpy as np
import pytest

from claudecad.jewelry.chains import ChainParams, LoopInfo, PlacedLink, closed_loop, straight_chain
from claudecad.verify import check_chain


def test_straight_chain_count_and_type():
    links = straight_chain(ChainParams(), count=3)
    assert len(links) == 3
    assert all(isinstance(pl, PlacedLink) for pl in links)


def test_straight_chain_spacing():
    p = ChainParams()
    links = straight_chain(p, count=3)
    c0 = links[0].centerline.mean(axis=0)
    c1 = links[1].centerline.mean(axis=0)
    assert c1[0] - c0[0] == pytest.approx(p.pitch, abs=1e-6)


def test_straight_chain_verifies():
    """The core benchmark property: interlocked, untouching, only neighbors linked."""
    report = check_chain(straight_chain(ChainParams(), count=4))
    assert report.ok, report.summary()


def test_closed_loop_derived_values():
    p = ChainParams()
    links, info = closed_loop(p, target_circumference=200.0)
    assert isinstance(info, LoopInfo)
    assert info.count % 2 == 0
    assert info.count == round(200.0 / p.pitch) or info.count == round(200.0 / p.pitch) + 1
    assert info.circumference == pytest.approx(info.count * p.pitch)
    assert info.radius == pytest.approx(info.circumference / (2 * math.pi))
    assert len(links) == info.count


def test_closed_loop_links_lie_on_circle():
    links, info = closed_loop(ChainParams(), target_circumference=200.0)
    for pl in links:
        center = pl.centerline.mean(axis=0)
        assert np.hypot(center[0], center[1]) == pytest.approx(info.radius, rel=0.02)


def test_closed_loop_verifies_including_wraparound():
    """Benchmark property on the full bracelet: every neighbor pair (incl.
    last-first) interlocked, zero interpenetration anywhere."""
    links, _ = closed_loop(ChainParams(), target_circumference=200.0)
    report = check_chain(links, closed=True)
    assert report.ok, report.summary()


def test_closed_loop_count_rounds_to_nearest_even():
    p = ChainParams()  # pitch 10.0
    # x = 4.8: nearest even is 4 (|4.8-4| = 0.8 < |4.8-6| = 1.2)
    _, info = closed_loop(p, target_circumference=48.0)
    assert info.count == 4
    # x = 5.2: nearest even is 6
    _, info = closed_loop(p, target_circumference=52.0)
    assert info.count == 6
    # x = 5.0: exact odd tie rounds up
    _, info = closed_loop(p, target_circumference=50.0)
    assert info.count == 6


def test_closed_loop_too_few_links_raises():
    with pytest.raises(ValueError) as exc:
        closed_loop(ChainParams(), target_circumference=20.0)  # x = 2 -> n = 2
    msg = str(exc.value)
    assert "20.0" in msg and "10.0" in msg  # values present in message
