import pytest

from claudecad.jewelry.chains import ChainParams, straight_chain
from claudecad.jewelry.finishing import diamond_cut
from claudecad.jewelry.links import CubanLinkParams
from claudecad.verify import check_chain


def _chain():
    p = ChainParams(link=CubanLinkParams(), tilt_deg=20.0, pitch=10.0)
    return straight_chain(p, count=2)


def test_diamond_cut_flattens_to_exact_height():
    links = _chain()
    cut = diamond_cut(links, cut_z=2.8)
    for pl in cut:
        bb = pl.solid.bounding_box()
        assert bb.max.Z - bb.min.Z == pytest.approx(2 * 2.8, abs=0.01)
        assert pl.solid.is_valid
    # centerlines untouched
    for before, after in zip(links, cut):
        assert (before.centerline == after.centerline).all()
    # still a passing chain after the cut
    report = check_chain(cut)
    assert report.ok, report.summary()


def test_diamond_cut_severing_is_caught_by_chain_report():
    links = _chain()
    cut = diamond_cut(links, cut_z=0.6)     # slices through the whole wire
    report = check_chain(cut)
    assert not report.ok
    assert any("pieces=" in f for f in report.failures())


def test_diamond_cut_rejects_bad_cut_z():
    links = _chain()
    with pytest.raises(ValueError):
        diamond_cut(links, cut_z=0.0)
    with pytest.raises(ValueError):
        diamond_cut(links, cut_z=50.0)      # taller than the chain: no-op
