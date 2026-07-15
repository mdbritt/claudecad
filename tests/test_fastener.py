import math

import pytest

from claudecad.hardware.fastener import FastenerParams


def test_iso_radii_m8():
    p = FastenerParams()  # M8×1.25
    assert math.isclose(p.H, 1.25 * math.sqrt(3) / 2, rel_tol=1e-9)
    assert math.isclose(p.pitch_radius, 4.0 - 3 * p.H / 8, rel_tol=1e-9)
    assert math.isclose(p.minor_radius, 4.0 - 5 * p.H / 8, rel_tol=1e-9)


def test_params_validation():
    with pytest.raises(ValueError):
        FastenerParams(pitch=0.0)
    with pytest.raises(ValueError):
        # allowance must stay under the crest FLAT width or the flank-normal
        # offset erodes the crest away entirely (for M8 the crest flat ≈ 0.156)
        FastenerParams(allowance=0.2)
    with pytest.raises(ValueError):
        # the nut must be shorter than the shank so it runs down a longer bolt
        FastenerParams(bolt_turns=3, nut_turns=3)


def test_threads_are_clean_manifold_solids():
    from claudecad.verify import check_solid
    from claudecad.hardware.fastener import external_thread, internal_thread
    p = FastenerParams()
    for name, s in (("external", external_thread(p)), ("internal", internal_thread(p))):
        r = check_solid(s)
        assert r.ok, f"{name} not clean: valid={r.is_valid} manifold={r.is_manifold} pieces={r.piece_count}"


def test_parts_clean():
    from claudecad.verify import check_solid
    from claudecad.hardware.fastener import bolt, nut
    p = FastenerParams()
    for name, s in (("bolt", bolt(p)), ("nut", nut(p))):
        r = check_solid(s)
        assert r.ok, f"{name} not a clean solid: {r}"


def test_thread_mesh_differential():
    from claudecad.hardware.fastener import (
        AXIAL_SHIFT, WRONG_PITCH_FACTOR, thread_mesh_gap)
    p = FastenerParams()
    assert thread_mesh_gap(p) > 0                              # mesh: real air gap
    assert math.isclose(thread_mesh_gap(p), p.allowance, abs_tol=1e-6)  # gap == clearance
    assert thread_mesh_gap(p, bolt_dz=AXIAL_SHIFT) < 0         # axial-only: jam
    assert thread_mesh_gap(p, nut_pitch_factor=WRONG_PITCH_FACTOR) < 0  # wrong pitch: jam


def test_seated_assembly_meshes():
    """The shipped export assembly (bolt + seated_nut) must actually clear:
    an origin-pose bolt+nut jams (head overlaps nut, iv=32.8 mm^3) even
    though the analytic mesh gate passes, because nothing checked the
    shipped 3D geometry. seated_nut seats the nut up the shank by whole
    pitches (phase-preserving) so it meshes instead of jamming."""
    from claudecad.hardware.fastener import SEATED_MAX_IV, bolt, seated_nut
    from claudecad.verify import intersection_volume
    p = FastenerParams()
    iv = intersection_volume(bolt(p), seated_nut(p))
    assert iv < SEATED_MAX_IV, f"seated assembly interferes by {iv:.3f} mm^3"
