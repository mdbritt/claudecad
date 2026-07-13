import pytest

from claudecad.jewelry.chains import ChainParams, PlacedLink, straight_chain
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
