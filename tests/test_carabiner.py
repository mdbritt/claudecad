import numpy as np
import pytest

from claudecad.hardware.carabiner import (
    CarabinerParams, carabiner_body, carabiner_gate, carabiner_pin, escape_ring,
)
from claudecad.verify import (
    check_solid, intersection_volume, linking_number, path_clearance,
)


def test_parts_clean():
    p = CarabinerParams()
    for s in (carabiner_body(p), carabiner_gate(p, "closed"),
              carabiner_gate(p, "open"), carabiner_pin(p)):
        assert check_solid(s).ok


def test_closed_assembly_clear():
    p = CarabinerParams()
    body, gate, pin = carabiner_body(p), carabiner_gate(p, "closed"), carabiner_pin(p)
    assert intersection_volume(body, gate) == 0.0
    assert intersection_volume(body, pin) == 0.0
    assert intersection_volume(gate, pin) == 0.0


def test_ring_linked_through_closed_carabiner():
    p = CarabinerParams()
    ring, curve = escape_ring(p)
    body, _ = carabiner_body(p), None
    # body centerline circuit: with the gate CLOSED the aperture is a closed
    # loop topologically; prove by linking the ring against the body's own
    # closed circuit through the spine and gate line. The carabiner module
    # provides it:
    from claudecad.hardware.carabiner import closed_circuit
    lk = linking_number(closed_circuit(p), curve)
    assert abs(round(lk)) == 1 and abs(lk - round(lk)) < 0.1
    assert intersection_volume(ring, body) == 0.0


def test_escape_differential():
    """THE carabiner property: with the gate closed the ring cannot leave
    (its escape path collides); with the gate open the same path is clear
    of body+gate at every station."""
    p = CarabinerParams()
    ring, _ = escape_ring(p)
    body = carabiner_body(p)
    closed_g = carabiner_gate(p, "closed")
    open_g = carabiner_gate(p, "open")
    # escape path: out through the gap, +Y then away — the module provides
    # the axis and distance so the test and the design gate share it
    from claudecad.hardware.carabiner import ESCAPE_AXIS, escape_distance
    d = escape_distance(p)
    blocked = path_clearance(ring, body + closed_g, ESCAPE_AXIS, d, 12)
    assert max(blocked) > 0.0
    free_body = path_clearance(ring, body, ESCAPE_AXIS, d, 12)
    free_gate = path_clearance(ring, open_g, ESCAPE_AXIS, d, 12)
    assert max(free_body) == 0.0 and max(free_gate) == 0.0


def test_params_validation():
    with pytest.raises(ValueError):
        CarabinerParams(gap_l=0.0)
    with pytest.raises(ValueError):
        # gate_d == wire_d: the nose-recess bore radius is gate_d/2+clearance,
        # which must stay under wire_d/2 or it perforates the tube wall
        # instead of leaving a pocket (see CarabinerParams.__post_init__).
        CarabinerParams(gate_d=8.0)
