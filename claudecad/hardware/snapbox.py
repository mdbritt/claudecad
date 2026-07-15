"""Hinged snap-latch parts-box: base, lid on a pin hinge, cantilever snap.

Local frame: box centered on XY, base z in [0, base_h], lid plate above it
with `clearance` air; hinge axis parallel X along the back top edge at the
DERIVED height base_h + knuckle_d/2 + clearance (anything lower makes the
lid knuckles exactly tangent to the wall top — a coincident contact the
spike caught). The lid is built CLOSED with two constructed latch states
(relaxed / deflected, the box-clasp tongue convention); gates swing it about
the hinge with screw_clearance(lead=0) and an OFF-ORIGIN center. The travel
stop is a fin constructed AT the stop angle by rotating a radial block about
the hinge — the stop angle is parametric by construction. Prismatic
construction throughout: generic-position fuses only, nothing touches
(clearance mechanism -> every boolean gate reads crisp 0).

Knuckle layout, latch, and catch positions are tuned at the default
dimensions (carabiner _ring_geometry precedent) and are unverified for
arbitrary overrides; the driving dims and the gate laws are parametric.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from build123d import Box, Cylinder, Location, Pos, Rot, Solid

HINGE_AXIS: tuple[float, float, float] = (1.0, 0.0, 0.0)

# construction-only layout constants, tuned at defaults (mm)
_KNUCKLE_XC_BASE = (-15.0, 0.0, 15.0)   # 3 base knuckles
_KNUCKLE_XC_LID = (-7.5, 7.5)           # 2 lid knuckles, interleaved
_BORE_LEN = 33.0    # single through-bore; ends short of the outer knuckle
                    # faces -> blind ends give the pin axial retention
_PIN_LEN = 32.0
_RISER = (3.0, 3.0)         # base knuckle riser (y-depth, z-height)
_CATCH = (10.0, 1.2, 1.5, 15.5, 9.4)   # ridge w, t, h, y-center, z-center
_BRIDGE = (8.0, 3.5, 1.0, 16.1, 14.65)  # w, depth, t, y-center, z-center
_TAB = (8.0, 1.6, 8.5, 17.15, 10.9)     # w, t, drop, y-center, z-center
_NUB = (8.0, 1.6, 1.5, 15.95, 7.75)     # w, t, h, y-center, z-center
_TAB_PIVOT_Z = 15.15   # deflection tilts the snap about its top edge
_FIN = (6.35, 1.9, 0.6, 1.175, 3.65)    # stop fin: w, radial depth, thickness,
                                        # x-center, radial center from hinge


def _rot_about(center, axis, deg: float, shape):
    """Rotate `shape` by `deg` about the line through `center` along `axis`
    (the same conjugation screw_clearance uses internally)."""
    cx, cy, cz = center
    return Pos(cx, cy, cz) * Location((0, 0, 0), axis, deg) * \
        Pos(-cx, -cy, -cz) * shape


@dataclass(frozen=True)
class SnapBoxParams:
    """Driving dimensions, mm. clearance is the single design air gap at
    every mating pair. swing_deg is the working travel; stop_fin_deg places
    the travel-stop fin (contact begins a few degrees before it — verified
    free at 100, blocked by 105 at defaults). deflect_deg tilts the snap tab
    outward about its top edge for the deflected constructed state."""

    outer_l: float = 40.0
    outer_w: float = 30.0
    base_h: float = 12.0
    lid_t: float = 3.0
    wall: float = 2.0
    knuckle_d: float = 6.0
    knuckle_w: float = 6.0
    pin_d: float = 2.0
    clearance: float = 0.15
    swing_deg: float = 90.0
    stop_fin_deg: float = 108.0
    deflect_deg: float = 14.0

    def __post_init__(self):
        bad = {k: v for k, v in self.__dict__.items() if v <= 0}
        if bad:
            raise ValueError(f"all snapbox params must be > 0, got {bad}")
        if self.stop_fin_deg <= self.swing_deg + 5.0:
            raise ValueError(
                f"stop_fin_deg={self.stop_fin_deg} must exceed swing_deg="
                f"{self.swing_deg} by > 5 deg or the stop intrudes into the "
                "working travel"
            )
        if self.pin_d + 2 * self.clearance >= self.knuckle_d:
            raise ValueError(
                f"pin_d={self.pin_d} (+2*clearance) must fit inside "
                f"knuckle_d={self.knuckle_d}"
            )
        if self.wall >= min(self.outer_l, self.outer_w) / 4:
            raise ValueError(
                f"wall={self.wall} too thick for outer "
                f"{self.outer_l}x{self.outer_w}"
            )

    @property
    def hinge_center(self) -> tuple[float, float, float]:
        """Point on the hinge axis: back top edge, at the DERIVED height
        base_h + knuckle radius + clearance (lower is tangent — forbidden)."""
        return (0.0, -self.outer_w / 2,
                self.base_h + self.knuckle_d / 2 + self.clearance)

    @property
    def bore_radius(self) -> float:
        return self.pin_d / 2 + self.clearance

    @property
    def lid_z0(self) -> float:
        """Lid plate underside: clearance above the base top."""
        return self.base_h + self.clearance


def _knuckle(p: SnapBoxParams, xc: float) -> Solid:
    hc = p.hinge_center
    return Pos(xc, hc[1], hc[2]) * Rot(Y=90) * Cylinder(
        p.knuckle_d / 2, p.knuckle_w)


def _bore(p: SnapBoxParams) -> Solid:
    hc = p.hinge_center
    return Pos(0, hc[1], hc[2]) * Rot(Y=90) * Cylinder(
        p.bore_radius, _BORE_LEN)


def base(p: SnapBoxParams) -> Solid:
    """Open-top shell + 3 hinge knuckles on risers + catch ridge + travel
    stop fin. The fin is CONSTRUCTED AT stop_fin_deg by rotating a radial
    block about the hinge — the lid's plate top face meets it just past
    swing_deg (verified: free at 100 deg, blocked by 105 at defaults)."""
    hc = p.hinge_center
    b = Pos(0, 0, p.base_h / 2) * Box(p.outer_l, p.outer_w, p.base_h)
    b -= Pos(0, 0, p.wall + p.base_h / 2) * Box(
        p.outer_l - 2 * p.wall, p.outer_w - 2 * p.wall, p.base_h)
    ry, rz = _RISER
    for xc in _KNUCKLE_XC_BASE:
        b += Pos(xc, hc[1] + 1.0, p.base_h + 0.2) * Box(p.knuckle_w, ry, rz)
        b += _knuckle(p, xc)
    b -= _bore(p)
    cw, ct, ch, cy, cz = _CATCH
    b += Pos(0, cy, cz) * Box(cw, ct, ch)
    fw, fd, ft, fxc, frc = _FIN
    fin0 = Pos(fxc, hc[1] + frc, hc[2]) * Box(fw, fd, ft)
    b += _rot_about(hc, HINGE_AXIS, p.stop_fin_deg, fin0)
    return b


def lid(p: SnapBoxParams, state: Literal["relaxed", "deflected"]) -> Solid:
    """Lid in the CLOSED pose: plate (back edge held clear of the base
    knuckles) + 2 interleaved knuckles on arms + the cantilever snap
    (bridge over the front wall, hanging tab, inward nub). The deflected
    state tilts tab+nub outward by deflect_deg about the tab's top edge —
    the tilt preserves the bridge overlap so the state stays one solid."""
    if state not in ("relaxed", "deflected"):
        raise ValueError(f"state must be 'relaxed' or 'deflected', got {state!r}")
    hc = p.hinge_center
    plate_back = hc[1] + 3.0 + p.clearance      # clear of knuckle band (r=3)
    plate_w = p.outer_w / 2 - plate_back
    l = Pos(0, plate_back + plate_w / 2, p.lid_z0 + p.lid_t / 2) * Box(
        p.outer_l, plate_w, p.lid_t)
    for xc in _KNUCKLE_XC_LID:
        l += Pos(xc, hc[1] + 1.75, hc[2] - 1.15) * Box(p.knuckle_w, 4.3, 2.0)
        l += _knuckle(p, xc)
    l -= _bore(p)
    bw, bd, bt, by, bz = _BRIDGE
    bridge = Pos(0, by, bz) * Box(bw, bd, bt)
    tw, tt, td, ty, tz = _TAB
    tab = Pos(0, ty, tz) * Box(tw, tt, td)
    nw, nt, nh, ny, nz = _NUB
    nub = Pos(0, ny, nz) * Box(nw, nt, nh)
    snap = tab + nub
    if state == "deflected":
        snap = _rot_about((0, ty, _TAB_PIVOT_Z), HINGE_AXIS,
                          +p.deflect_deg, snap)
    return l + bridge + snap


def hinge_pin(p: SnapBoxParams) -> Solid:
    """Slip-fit pin: clearance-fitted in every bore, axially captured by the
    blind outer ends of the through-bore (bore len < knuckle span)."""
    hc = p.hinge_center
    return Pos(0, hc[1], hc[2]) * Rot(Y=90) * Cylinder(p.pin_d / 2, _PIN_LEN)


# --- gate fixtures (one source for the design build and the tests) ---
SWING_STATIONS = 10        # stations across the working swing
OVERTRAVEL_SPAN_DEG = 25.0  # sweep past the open pose for the travel limit
OVERTRAVEL_STATIONS = 11
OPEN_FREE_MAX_DEG = 100.0  # verified free through here at defaults
BLOCKED_BY_DEG = 105.0     # verified blocked from here at defaults
RETENTION_SPAN_DEG = 8.0   # opening arc that must catch the relaxed nub
RETENTION_STATIONS = 9     # (verified: blocked 1-5 deg, max ~7.0 mm^3)
NEG_CENTER_OFFSET = 0.5    # mm hinge-axis displacement for the neg control


def pin_escape_distance(p: SnapBoxParams) -> float:
    """Sweep distance for the pin's BLOCKED escape checks. A blocked
    assertion must sample the blocking band densely — for the pin that band
    is the bore-wall-to-knuckle-exit region, knuckle_d wide (verified: with
    an envelope-scale distance the 7 stations straddle the band and the
    check passes on a 0.02 mm^3 sliver; at knuckle_d the same stations read
    ~16-80 mm^3 deep). Envelope-scale distances are only needed for FREE
    legs, and every pin direction here is blocked."""
    return p.knuckle_d
