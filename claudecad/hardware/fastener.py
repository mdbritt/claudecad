"""Threaded fastener: M8×1.25 hex bolt + hex nut, modeled as helical sweeps.

Local frame: thread axis is +Z (`AXIS`). The thread is built by stacking
exact-pitch-spaced copies of a single swept turn so the solid is truly
pitch-periodic (a continuous multi-turn sweep drifts turn-to-turn and reads
as interference under an ideal screw motion — see the design spec). The nut is
the BASIC-profile negative; the bolt is the same profile offset undersize along
the flank normal — so the run-down gate proves an undersize bolt clears a basic
nut rather than that a solid fits its own negative.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from build123d import Cylinder, Helix, Location, Plane, Polygon, Pos, Solid, sweep

AXIS: tuple[float, float, float] = (0.0, 0.0, 1.0)
FLANK_DEG: float = 60.0  # ISO metric included flank angle


@dataclass(frozen=True)
class FastenerParams:
    """Driving dimensions, mm. major_d/pitch are the nominal ISO thread size
    (M8×1.25). allowance is the single radial+flank clearance that stands in
    for ISO tolerance classes. bolt_turns/nut_turns are thread lengths in
    turns; the nut is shorter so it runs down a longer shank."""

    major_d: float = 8.0
    pitch: float = 1.25
    allowance: float = 0.08  # flank-normal clearance; 0.08 gives rest iv==0 for M8 (verified)
    bolt_turns: int = 6
    nut_turns: int = 3
    hex_across_flats: float = 13.0
    head_height: float = 5.3

    def __post_init__(self):
        bad = {k: v for k, v in self.__dict__.items() if v <= 0}
        if bad:
            raise ValueError(f"all fastener params must be > 0, got {bad}")
        crest_flat = 2 * (self.pitch / 4 - (self.major_d / 2 - self.pitch_radius)
                          * math.tan(math.radians(FLANK_DEG / 2)))
        if self.allowance >= crest_flat:
            raise ValueError(
                f"allowance={self.allowance} must be < the crest flat width "
                f"({crest_flat:.4f}); a larger flank-normal offset erodes the "
                "crest flat away entirely"
            )
        if self.bolt_turns <= self.nut_turns:
            raise ValueError(
                f"need bolt_turns > nut_turns (the nut runs down a longer "
                f"shank), got bolt_turns={self.bolt_turns} "
                f"nut_turns={self.nut_turns}"
            )

    @property
    def H(self) -> float:
        """ISO 68-1 fundamental triangle height."""
        return self.pitch * math.sqrt(3) / 2

    @property
    def pitch_radius(self) -> float:
        return self.major_d / 2 - 3 * self.H / 8

    @property
    def minor_radius(self) -> float:
        """External thread root == internal thread minor radius."""
        return self.major_d / 2 - 5 * self.H / 8


_SEGMENTS_PER_TURN = 1
_CORE_OVERLAP = 0.02  # core sits this far above the ridge root -> manifold fuse
                      # (a tangent core makes non-manifold seams; verified)


def _half_width(p: FastenerParams, r: float) -> float:
    """Axial half-width of the 60-deg thread at radius r."""
    return p.pitch / 4 - (r - p.pitch_radius) * math.tan(math.radians(FLANK_DEG / 2))


def _profile(p: FastenerParams, allowance: float) -> list[tuple[float, float]]:
    """Undersize trapezoid: crest & root radii reduced by `allowance`, flank
    half-widths taken at the SHIFTED radii and inset by `allowance`. Evaluating
    the half-widths at the shifted (not basic) radii is what keeps the flanks
    60 deg through the pitch line, so the bolt stays pitch-aligned with the
    basic nut (a plain 2D offset raises the root above the nut crest; a naive
    radial shift misaligns the pitch diameter)."""
    crest_r = p.major_d / 2 - allowance
    root_r = p.minor_radius - allowance
    return [
        (root_r - p.pitch_radius, -(_half_width(p, root_r) - allowance)),
        (crest_r - p.pitch_radius, -(_half_width(p, crest_r) - allowance)),
        (crest_r - p.pitch_radius, _half_width(p, crest_r) - allowance),
        (root_r - p.pitch_radius, _half_width(p, root_r) - allowance),
    ]


def _one_turn(p: FastenerParams, allowance: float) -> Solid:
    """One turn of thread ridge, K sub-segments placed by exact fractional
    screws (K=1 is a single 1-turn sweep)."""
    k = _SEGMENTS_PER_TURN
    h = Helix(pitch=p.pitch, height=p.pitch / k, radius=p.pitch_radius)
    plane = Plane(origin=h @ 0, x_dir=(1, 0, 0), z_dir=h % 0)
    seg = sweep(plane * Polygon(*_profile(p, allowance), align=None), path=h)
    ridge = seg
    for i in range(1, k):
        ridge = ridge + Pos(0, 0, i * p.pitch / k) * \
            Location((0, 0, 0), AXIS, i * 360.0 / k) * seg
    return ridge


def _thread(p: FastenerParams, turns: int, allowance: float) -> Solid:
    """Pitch-periodic thread: one turn stacked at exact integer-pitch spacing
    (a continuous multi-turn sweep drifts), unioned with a core cylinder that
    overlaps the ridge root by _CORE_OVERLAP for a manifold fuse."""
    one = _one_turn(p, allowance)
    ridge = one
    for t in range(1, turns):
        ridge = ridge + Pos(0, 0, t * p.pitch) * one
    core_r = (p.minor_radius - allowance) + _CORE_OVERLAP
    core = Pos(0, 0, turns * p.pitch / 2) * Cylinder(core_r, turns * p.pitch)
    return core + ridge


def external_thread(p: FastenerParams) -> Solid:
    """Bolt threaded shank (undersize by `allowance`)."""
    return _thread(p, p.bolt_turns, p.allowance)


def internal_thread(p: FastenerParams) -> Solid:
    """Nut tap cutter (basic thread), subtracted from the nut blank."""
    return _thread(p, p.nut_turns, 0.0)
