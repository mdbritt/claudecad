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

import numpy as np
from build123d import Cylinder, Helix, Location, Plane, Polygon, Pos, RegularPolygon, Solid, extrude, sweep

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
    allowance: float = 0.08  # flank-normal clearance; the analytic mesh gap equals this allowance
    bolt_turns: int = 6
    nut_turns: int = 3
    hex_across_flats: float = 13.0
    head_height: float = 5.3

    def __post_init__(self):
        bad = {k: v for k, v in self.__dict__.items() if v <= 0}
        if bad:
            raise ValueError(f"all fastener params must be > 0, got {bad}")
        if self.minor_radius <= 0:
            raise ValueError(
                f"minor_radius={self.minor_radius:.4f} must be > 0; pitch "
                f"({self.pitch}) is too large relative to major_d "
                f"({self.major_d})"
            )
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
                      # (a tangent core makes non-manifold seams; verified).
                      # This is the one place the swept 3D solid and the
                      # analytic 2D profile (thread_mesh_gap) differ: the
                      # built solid's root sits _CORE_OVERLAP above the
                      # analytic model's root, but symmetrically on both
                      # bolt and nut, so it cancels out of the mesh gap.


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


def _hex_prism(p: FastenerParams, height: float) -> Solid:
    """Hex prism across `hex_across_flats`, base at z=0, extruded +Z."""
    return extrude(
        RegularPolygon(p.hex_across_flats / 2, 6, major_radius=False), height
    )


def bolt(p: FastenerParams) -> Solid:
    """Hex head (below z=0) ∪ threaded shank (z=0..bolt_turns*pitch). The head
    overlaps the shank base by 0.3 mm so the union fuses to a single solid
    rather than joining on a coincident face (verified: solids==1)."""
    shank = external_thread(p)
    head = Pos(0, 0, -p.head_height) * _hex_prism(p, p.head_height + 0.3)
    return shank + head


def nut(p: FastenerParams) -> Solid:
    """Hex prism (nut_turns*pitch tall) with a threaded bore."""
    return _hex_prism(p, p.nut_turns * p.pitch) - internal_thread(p)


NUT_SEAT_TURNS = 2  # whole pitches to seat the nut up the shank for export


def seated_nut(p: FastenerParams) -> Solid:
    """The nut threaded onto the bolt, seated NUT_SEAT_TURNS whole pitches up
    the shank so it clears the head and meshes (an integer-pitch shift is
    phase-preserving; rotating it would jam). For the export assembly."""
    return Pos(0, 0, NUT_SEAT_TURNS * p.pitch) * nut(p)


SEATED_MAX_IV = 2.0  # mm^3 facet-noise ceiling on the shipped assembly's 3D
                      # interference (the K=1 swept helicoid meshes to ~1.1;
                      # the analytic gate proves the real air gap)


# analytic mesh-gate fixtures (shared by the design build and the test)
AXIAL_SHIFT = 0.15        # mm of pure-axial shift (past the ~0.08 backlash) -> jam
WRONG_PITCH_FACTOR = 1.05  # nut pitch error over the engagement -> jam
_GAP_SAMPLES = 20000


def _surf(z, phase: float, crest_r: float, root_r: float, crest_hw: float,
          pitch: float):
    """Single-valued thread surface r(z) in the axial section: crest flat ->
    60-deg flank -> root flat, period `pitch`, crest centered at `phase`."""
    u = np.abs((z - phase + pitch / 2) % pitch - pitch / 2)
    fz = abs(crest_r - root_r) * math.tan(math.radians(FLANK_DEG / 2))
    return np.where(u <= crest_hw, crest_r,
           np.where(u <= crest_hw + fz,
                    crest_r + (root_r - crest_r) * (u - crest_hw) / fz, root_r))


def thread_mesh_gap(p: FastenerParams, bolt_dz: float = 0.0,
                    nut_pitch_factor: float = 1.0) -> float:
    """Exact min axial-section clearance (mm) between the meshed bolt and nut
    threads over the nut's engagement. >0 is a real air gap (free); <=0 is
    interference (jam). The nut inner surface is a basic external-thread
    sawtooth; the bolt is the undersize sawtooth at the same phase (+bolt_dz).
    Coaxial same-pitch helical symmetry makes this 2D section exact for the
    equal-pitch mesh call and the bolt_dz axial-shift call. When
    `nut_pitch_factor != 1` the two pitches share no common screw symmetry,
    so that leg instead computes interference along the single phi=0 axial
    line — a valid conservative one-sided jam detector, not an exact
    clearance."""
    z = np.linspace(0.0, p.nut_turns * p.pitch, _GAP_SAMPLES)
    hw = lambda r: _half_width(p, r)
    a = p.allowance
    rn = _surf(z, 0.0, p.major_d / 2, p.minor_radius, hw(p.major_d / 2),
               p.pitch * nut_pitch_factor)
    rb = _surf(z, bolt_dz, p.major_d / 2 - a, p.minor_radius - a,
               hw(p.major_d / 2 - a) - a, p.pitch)
    return float(np.min(rn - rb))
