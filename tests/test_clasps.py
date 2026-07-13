import pytest
from build123d import Box, Pos

from claudecad.jewelry.clasps import BoxClaspParams, clasp_box, clasp_tongue
from claudecad.verify import check_solid, intersection_volume, path_clearance


def test_box_and_tongue_are_clean_solids():
    p = BoxClaspParams()
    for s in (clasp_box(p), clasp_tongue(p, "relaxed"), clasp_tongue(p, "compressed")):
        r = check_solid(s)
        assert r.ok, r


def test_box_outer_dims_match_chain():
    p = BoxClaspParams()
    bb = clasp_box(p).bounding_box()
    assert bb.max.Z - bb.min.Z == pytest.approx(p.box_h, abs=1e-6)
    assert bb.max.Y - bb.min.Y == pytest.approx(p.box_w, abs=1e-6)


def test_tongue_states_share_blade():
    """The two states differ only in the leaf: their intersection contains
    the full blade volume (blade is identical and identically placed)."""
    p = BoxClaspParams()
    relaxed = clasp_tongue(p, "relaxed")
    compressed = clasp_tongue(p, "compressed")
    common = intersection_volume(relaxed, compressed)
    blade_vol = p.blade_l * p.blade_w * p.blade_t
    assert common > blade_vol * 0.95


def test_insertion_sweep_clear_when_compressed():
    p = BoxClaspParams()
    box = clasp_box(p)
    compressed = clasp_tongue(p, "compressed")
    vols = path_clearance(
        compressed, box, axis=(-1, 0, 0), distance=p.blade_l + 1.0, n=12
    )
    assert all(v == 0.0 for v in vols), vols


def test_lock_differential():
    """Relaxed tongue is blocked at the lock station; compressed is free.
    This differential IS the click mechanism."""
    p = BoxClaspParams()
    box = clasp_box(p)
    e = p.lip_depth + 0.6
    relaxed_at = Pos(-e, 0, 0) * clasp_tongue(p, "relaxed")
    compressed_at = Pos(-e, 0, 0) * clasp_tongue(p, "compressed")
    assert intersection_volume(relaxed_at, box) > 0.0
    assert intersection_volume(compressed_at, box) == 0.0


def test_seated_relaxed_tongue_clears_box():
    """Worn state: relaxed tongue seated in the box without interference."""
    p = BoxClaspParams()
    assert intersection_volume(clasp_tongue(p, "relaxed"), clasp_box(p)) == 0.0


def test_params_validation():
    with pytest.raises(ValueError):
        BoxClaspParams(box_h=3.0)     # cavity can't fit the relaxed leaf
    with pytest.raises(ValueError):
        BoxClaspParams(blade_w=14.0)  # blade wider than cavity
    with pytest.raises(ValueError):
        BoxClaspParams(wall=-1.0)
