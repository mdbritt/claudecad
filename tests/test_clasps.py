import numpy as np
import pytest
from build123d import Box, Pos, Rot

from claudecad.core.centerline import discretize
from claudecad.jewelry.clasps import (
    BoxClaspParams,
    ClaspAssembly,
    attachment_loop,
    box_clasp,
    clasp_box,
    clasp_latch,
    clasp_pin,
    clasp_tongue,
)
from claudecad.jewelry.links import LinkParams, curb_link
from claudecad.verify import (
    check_solid,
    intersection_volume,
    linking_number,
    path_clearance,
)


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
    with pytest.raises(ValueError):
        BoxClaspParams(latch_arm=4.0)  # too short to fuse arm+catch


def test_assembly_parts_clean_and_clear():
    asm = box_clasp(BoxClaspParams())
    assert set(asm.parts) == {
        "clasp_box", "clasp_tongue", "clasp_latch_l", "clasp_latch_r",
        "clasp_pin_l", "clasp_pin_r",
    }
    for name, s in asm.parts.items():
        assert check_solid(s).ok, name
    names = list(asm.parts)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            iv = intersection_volume(asm.parts[names[i]], asm.parts[names[j]])
            assert iv == 0.0, (names[i], names[j], iv)


def test_latch_guards_extraction():
    """With latches closed, even the compressed tongue cannot leave."""
    p = BoxClaspParams()
    asm = box_clasp(p)
    guarded = Pos(-2.0, 0, 0) * asm.tongue_state("compressed")
    hit = intersection_volume(guarded, asm.parts["clasp_latch_l"]) + \
        intersection_volume(guarded, asm.parts["clasp_latch_r"])
    assert hit > 0.0


def test_pin_concentric_with_clearance():
    p = BoxClaspParams()
    latch = clasp_latch(p, +1)
    pin = clasp_pin(p, +1)
    assert intersection_volume(latch, pin) == 0.0   # radial clearance in bore


def test_attachment_loop_links_end_link():
    """A curb link hung on the box lug bar is topologically attached."""
    p = BoxClaspParams()
    loop = attachment_loop(p, "box")
    assert loop.shape[1] == 3
    # place a planar link so its opening wraps the bar: bar is at
    # x ~ box_l + lug_l - bar_d/2 - 0.5, axis along Y
    lp = LinkParams(length=20.0, width=15.0, wire_d=4.0)
    _, wire = curb_link(lp)
    bar_x = p.box_l + p.lug_l - p.bar_d / 2 - 0.5
    link_curve = discretize(
        Pos(bar_x + 10.0 - lp.wire_d, 0, 0) * Rot(Z=0) * wire, 256
    )
    lk = linking_number(loop, np.asarray(link_curve))
    assert abs(round(lk)) == 1 and abs(lk - round(lk)) < 0.1


def test_attachment_loop_tongue_end_links():
    """Mirror of test_attachment_loop_links_end_link for the tongue-side lug."""
    p = BoxClaspParams()
    loop = attachment_loop(p, "tongue")
    lp = LinkParams(length=20.0, width=15.0, wire_d=4.0)
    _, wire = curb_link(lp)
    bar_x = -p.lug_l + p.bar_d / 2 + 0.5
    link_curve = discretize(Pos(bar_x - (10.0 - lp.wire_d), 0, 0) * wire, 256)
    lk = linking_number(loop, np.asarray(link_curve))
    assert abs(round(lk)) == 1 and abs(lk - round(lk)) < 0.1
