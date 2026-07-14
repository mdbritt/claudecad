"""Spring-gate carabiner: planar stadium-sweep body, rod gate (two
constructed states), pin -- all analytic (Box/Cylinder cuts, no shells, no
twisted lofts). Local frame: body in the XY plane, z=0 the midplane, long
axis X. The stadium centerline (see `curb_link`) has two straight runs at
y = +-end_radius; the gate opening is cut from the +Y straight, centered on
x=0, spanning x in [-gap_l/2, +gap_l/2]. The pivot lives at the opening's
-X end (a boss added to the body, offset clear of the gap by `_BOSS_GAP` so
body and gate never share a boolean face); the nose recess (a bore) lives
at the +X end and seats the closed gate's tip with `clearance`.

Functionality is proven statically per the /cad skill: parts are separate
manifold solids with real air gaps at every joint (never touching booleans
between DIFFERENT parts), and the mechanism is proven by constructed states
-- `carabiner_gate` closed vs. open -- gated on `verify.path_clearance`
along `ESCAPE_AXIS`: closed blocks a ring's escape, open does not. The
pose and margin are empirically tuned and verified in tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from build123d import Box, Circle, Cylinder, Plane, Pos, Rot, Solid, Torus, sweep

from claudecad.core.centerline import discretize, stadium_wire

# --- shared fixture constants (tests and the future design gate both
# import these, so there is exactly one source for the escape geometry) ---
ESCAPE_AXIS: tuple[float, float, float] = (0.0, 1.0, 0.0)
GATE_OPEN_DEG = 30.0  # brief-specified swing magnitude, rotated INWARD (-Z)

# construction-only margins (not physically meaningful, just robust cuts)
_BOSS_GAP = 0.1          # air gap between the pivot boss and the gate rod
_BOSS_COLLAR = 1.5       # boss pad radius beyond wire_d/2, and its Z-height margin
_NOSE_BORE_MARGIN = 0.2  # nose bore overshoot past the tube's cut face, each side
_PIVOT_BORE_MARGIN = 1.5  # pivot bore overshoot past boss/gate, each side


@dataclass(frozen=True)
class CarabinerParams:
    """Driving dimensions, mm. body_l/body_w are OUTER stadium dimensions
    (long axis X); wire_d is the swept tube diameter -- same convention as
    jewelry.links.LinkParams. gap_l is the gate opening's length along the
    +Y straight. gate_d is the gate rod diameter; nose_depth how far its tip
    seats into the body's nose recess; pin_d the pivot pin; clearance the
    uniform air gap at every mating pair.
    """

    body_l: float = 70.0
    body_w: float = 40.0
    wire_d: float = 8.0
    gap_l: float = 16.0
    gate_d: float = 7.0
    nose_depth: float = 2.0
    pin_d: float = 2.0
    clearance: float = 0.3

    def __post_init__(self):
        vals = self.__dict__
        bad = {k: v for k, v in vals.items() if v <= 0}
        if bad:
            raise ValueError(f"all carabiner params must be > 0, got {bad}")
        if self.body_l <= self.body_w:
            raise ValueError(
                f"need body_l > body_w (stadium straight = body_l-body_w), "
                f"got body_l={self.body_l} body_w={self.body_w}"
            )
        if self.body_w <= self.wire_d:
            raise ValueError(
                f"need body_w > wire_d (end_radius = (body_w-wire_d)/2), "
                f"got body_w={self.body_w} wire_d={self.wire_d}"
            )
        if self.gap_l >= self.straight:
            raise ValueError(
                f"gap_l={self.gap_l} does not fit the +Y straight "
                f"(body_l-body_w={self.straight})"
            )
        if self.gate_d + 2 * self.clearance >= self.wire_d:
            raise ValueError(
                f"gate_d={self.gate_d} (+2*clearance={self.clearance}) too fat "
                f"for the nose recess: the bore radius gate_d/2+clearance must "
                f"be < wire_d/2 (wire_d={self.wire_d}) or it perforates the "
                "tube wall instead of leaving a pocket"
            )
        if self.pin_d + 2 * self.clearance >= self.gate_d:
            raise ValueError(
                f"pin_d={self.pin_d} (+2*clearance={self.clearance}) too fat "
                f"for the gate's own pivot bore: must be < gate_d={self.gate_d}"
            )

    @property
    def straight(self) -> float:
        """Full length of each stadium centerline straight run."""
        return self.body_l - self.body_w

    @property
    def end_radius(self) -> float:
        """Centerline radius of the semicircular ends == the +Y/-Y straights'
        y-coordinate (the gate opening sits on the +Y straight, at this y)."""
        return (self.body_w - self.wire_d) / 2


def _pivot_x(p: CarabinerParams) -> float:
    """-X end of the gap: where the pivot boss / gate hinge lives."""
    return -p.gap_l / 2


def _nose_x(p: CarabinerParams) -> float:
    """+X end of the gap: where the nose recess starts."""
    return p.gap_l / 2


def _y_gap(p: CarabinerParams) -> float:
    """Y-coordinate of the gate opening on the +Y straight (== end_radius)."""
    return p.end_radius


def _pin_bore_r(p: CarabinerParams) -> float:
    return p.pin_d / 2 + p.clearance


def carabiner_body(p: CarabinerParams) -> Solid:
    """Stadium tube (curb_link-style: circular profile swept on
    `stadium_wire`), gap cut from the +Y straight, nose recess bored at the
    gap's +X end, pivot boss added and bored at the gap's -X end.

    The boss is placed entirely on the far side of the pivot line (its
    footprint tops out at `_pivot_x - _BOSS_GAP`, never crossing into the
    gap), so it can never share a boolean face with the gate rod -- that is
    what keeps `intersection_volume(carabiner_body(p), carabiner_gate(p,
    "closed")) == 0` (see test_closed_assembly_clear) robust rather than a
    coincident-face fluke.

    The boss's own bore (pivot_bore below) only holds ~half the pin's
    length; the gate's coaxial bore (carabiner_gate) completes it -- the
    pin is jointly captured by both bores only once body and gate are
    assembled at the hinge.
    """
    y_gap = _y_gap(p)
    x_piv, x_nose = _pivot_x(p), _nose_x(p)

    w = stadium_wire(p.straight, p.end_radius)
    profile = Plane(origin=w @ 0, z_dir=w % 0) * Circle(p.wire_d / 2)
    body = sweep(profile, path=w)

    gap_cut = Pos(0, y_gap, 0) * Box(p.gap_l, p.wire_d + 4, p.wire_d + 4)
    body -= gap_cut

    nose_bore_r = p.gate_d / 2 + p.clearance
    nose_bore = Pos(x_nose + p.nose_depth / 2, y_gap, 0) * Rot(Y=90) * Cylinder(
        nose_bore_r, p.nose_depth + 2 * _NOSE_BORE_MARGIN
    )
    body -= nose_bore

    boss_r = p.wire_d / 2 + _BOSS_COLLAR
    boss_center_x = x_piv - _BOSS_GAP - boss_r
    boss = Pos(boss_center_x, y_gap, 0) * Cylinder(boss_r, p.wire_d + _BOSS_COLLAR)
    body += boss

    pivot_bore = Pos(x_piv, y_gap, 0) * Cylinder(
        _pin_bore_r(p), p.wire_d + 2 * _PIVOT_BORE_MARGIN
    )
    body -= pivot_bore
    return body


def carabiner_gate(p: CarabinerParams, state: Literal["closed", "open"]) -> Solid:
    """Rod pivoting at the gap's -X end (Z-axis hinge). Closed: spans the
    opening at y=end_radius, tip poking `nose_depth - clearance` into the
    nose recess (so the tip never touches the recess's floor or walls).
    Open: rotated `GATE_OPEN_DEG` INWARD -- empirically, negative Z-rotation
    swings the tip toward -Y (into the loop interior) given the pivot sits
    at the -X end and the rod runs toward +X; verified by probing the tip's
    transformed position."""
    if state not in ("closed", "open"):
        raise ValueError(f"state must be 'closed' or 'open', got {state!r}")
    y_gap = _y_gap(p)
    x_piv, x_nose = _pivot_x(p), _nose_x(p)
    x_tip = x_nose + p.nose_depth - p.clearance
    length = x_tip - x_piv

    rod = Pos((x_piv + x_tip) / 2, y_gap, 0) * Rot(Y=90) * Cylinder(p.gate_d / 2, length)
    rod -= Pos(x_piv, y_gap, 0) * Cylinder(
        _pin_bore_r(p), p.wire_d + 2 * _PIVOT_BORE_MARGIN
    )
    if state == "open":
        rod = Pos(x_piv, y_gap, 0) * Rot(Z=-GATE_OPEN_DEG) * Pos(-x_piv, -y_gap, 0) * rod
    return rod


def carabiner_pin(p: CarabinerParams) -> Solid:
    """Pivot pin, concentric with the body boss bore and the gate's own
    pivot bore (both built from the same axis in carabiner_body /
    carabiner_gate); radius pin_d/2 stays inside both bores' pin_d/2+
    clearance, so it never touches either -- zero intersection with body
    or gate by construction, same pattern as jewelry.clasps.clasp_pin."""
    y_gap = _y_gap(p)
    x_piv = _pivot_x(p)
    return Pos(x_piv, y_gap, 0) * Cylinder(p.pin_d / 2, p.wire_d + _BOSS_COLLAR)


def closed_circuit(p: CarabinerParams, n: int = 256) -> np.ndarray:
    """Body centerline (the pure stadium curve, gap included) with the
    points that fall in the gap replaced by the straight gate chord --
    the closed loop a captured ring links against when the gate is closed.
    `stadium_wire`/`discretize` trace the +Y straight first and left-to-
    right, so the masked run is contiguous and already x-increasing; the
    chord resample preserves that order."""
    y_gap = _y_gap(p)
    x_piv, x_nose = _pivot_x(p), _nose_x(p)
    pts = discretize(stadium_wire(p.straight, p.end_radius), n)
    mask = (
        (np.abs(pts[:, 1] - y_gap) < 1e-6)
        & (pts[:, 0] >= x_piv - 1e-6)
        & (pts[:, 0] <= x_nose + 1e-6)
    )
    idx = np.where(mask)[0]
    if len(idx):
        pts[idx, 0] = np.linspace(x_piv, x_nose, len(idx))
        pts[idx, 1] = y_gap
        pts[idx, 2] = 0.0
    return pts


def _ring_geometry(p: CarabinerParams) -> tuple[float, float, float, float]:
    """Escape ring pose (x, y, major_r, minor_r), derived from p and
    empirically verified against the default params:
    offset toward the nose side of the gap (0.75 of the way out) where the
    pivot-to-point lever arm is longest, so the open gate's swept position
    is furthest from the gate line in Y -- that margin is what keeps the
    ring's translated path clear of the OPEN gate while still being
    blocked by the CLOSED one. y sits just above end_radius so one z=0
    crossing of the ring's core circle lands inside the body's enclosed
    loop and the other lands outside (required for Lk=+-1 against a
    flat, z=0 closed_circuit -- see jewelry.clasps.attachment_loop for the
    same coplanar-curves-can't-link reasoning). These constants are
    numerically tuned at CarabinerParams defaults only and are unverified
    for arbitrary param overrides."""
    x_ring = 0.75 * (p.gap_l / 2)
    y_ring = p.end_radius + 0.5
    major_r = p.gate_d / 2 - 1.0
    minor_r = 0.45 * p.pin_d
    return x_ring, y_ring, major_r, minor_r


def escape_ring(p: CarabinerParams, n: int = 256) -> tuple[Solid, np.ndarray]:
    """A torus (axis along X, so its plane crosses z=0) plus its core-circle
    centerline, positioned to link once with `closed_circuit` and to clear
    the aperture along `ESCAPE_AXIS` per the gate state (see
    test_escape_differential / escape_distance)."""
    x_ring, y_ring, major_r, minor_r = _ring_geometry(p)
    ring = Pos(x_ring, y_ring, 0) * Rot(Y=90) * Torus(major_r, minor_r)
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    curve = np.stack(
        [
            np.full_like(theta, x_ring),
            y_ring + major_r * np.cos(theta),
            major_r * np.sin(theta),
        ],
        axis=1,
    )
    return ring, curve


def escape_distance(p: CarabinerParams) -> float:
    """Translation distance along ESCAPE_AXIS that carries the escape ring
    from its resting pose to clearly past the body's outer envelope
    (body_w/2 past the gap line clears every boss/recess feature, verified
    empirically for the default params)."""
    return p.body_w / 2
