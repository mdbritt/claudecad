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
