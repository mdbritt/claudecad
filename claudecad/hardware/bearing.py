"""608-geometry cageless deep-groove ball bearing.

Local frame: bearing axis +Z (`AXIS`), races centered on the origin, balls on
the pitch circle at z=0. Races are exact solids of revolution — an annular
cylinder minus a groove TORUS whose tube radius is the osculation-scaled ball
radius — so raceway axisymmetry is by construction, and the orbital gate
(designs/bearing_608) exists to PROVE it rather than assume it. A bearing is a
CLEARANCE mechanism (balls never touch races; rest gap = groove_r − ball_r),
so every boolean gate must read crisp 0 — per the /cad method law, unlike the
fastener's contact mesh which needed an analytic gate.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from build123d import Compound, Cylinder, Pos, Shape, Solid, Sphere, Torus

AXIS: tuple[float, float, float] = (0.0, 0.0, 1.0)


@dataclass(frozen=True)
class BearingParams:
    """Driving dimensions, mm — 608 defaults. osculation is groove-to-ball
    conformity (raceway groove radius = osculation·ball_d; deep-groove
    standard band ≈ 0.515–0.53); shoulder_frac is shoulder height above the
    groove bottom as a fraction of ball_d. The rest radial gap is DERIVED:
    groove_radius − ball_d/2 (0.0794 at defaults) — a design value for robust
    booleans, not a manufacturing clearance."""

    bore: float = 8.0
    outer_d: float = 22.0
    width: float = 7.0
    n_balls: int = 7
    ball_d: float = 3.969
    osculation: float = 0.52
    shoulder_frac: float = 0.35

    def __post_init__(self):
        bad = {k: v for k, v in self.__dict__.items() if v <= 0}
        if bad:
            raise ValueError(f"all bearing params must be > 0, got {bad}")
        if not self.bore < 2 * self.inner_shoulder_radius:
            raise ValueError(
                f"bore={self.bore} leaves no inner race wall "
                f"(inner shoulder radius {self.inner_shoulder_radius:.3f})"
            )
        if not self.outer_shoulder_radius < self.outer_d / 2:
            raise ValueError(
                f"outer_d={self.outer_d} leaves no outer race wall "
                f"(outer shoulder radius {self.outer_shoulder_radius:.3f})"
            )
        shoulder_gap = self.outer_shoulder_radius - self.inner_shoulder_radius
        if not shoulder_gap < self.ball_d:
            raise ValueError(
                f"capture inequality violated: radial shoulder gap "
                f"{shoulder_gap:.3f} must be < ball_d={self.ball_d} or balls "
                "escape radially between the shoulders"
            )
        chord = 2 * self.pitch_radius * math.sin(math.pi / self.n_balls)
        if not chord > self.ball_d:
            raise ValueError(
                f"n_balls={self.n_balls} do not fit: pitch-circle chord "
                f"{chord:.3f} must exceed ball_d={self.ball_d}"
            )
        if self.rest_gap <= 0:
            raise ValueError(
                f"osculation={self.osculation} gives rest_gap "
                f"{self.rest_gap:.4f}; must be > 0 (groove must be wider "
                "than the ball)"
            )
        if self.osculation > 0.54:
            raise ValueError(
                f"osculation={self.osculation} exceeds 0.54: deep-groove "
                "conformity runs ~0.515-0.53; a looser groove abandons "
                "raceway guidance"
            )

    @property
    def pitch_radius(self) -> float:
        return (self.bore + self.outer_d) / 4

    @property
    def groove_radius(self) -> float:
        return self.osculation * self.ball_d

    @property
    def inner_shoulder_radius(self) -> float:
        return (self.pitch_radius - self.groove_radius
                + self.shoulder_frac * self.ball_d)

    @property
    def outer_shoulder_radius(self) -> float:
        return (self.pitch_radius + self.groove_radius
                - self.shoulder_frac * self.ball_d)

    @property
    def rest_gap(self) -> float:
        """Radial air gap between a centered ball and either raceway."""
        return self.groove_radius - self.ball_d / 2


def _groove_torus(p: BearingParams) -> Solid:
    return Torus(p.pitch_radius, p.groove_radius)


def inner_race(p: BearingParams) -> Solid:
    """Annulus bore/2..inner_shoulder_radius minus the groove torus."""
    return (Cylinder(p.inner_shoulder_radius, p.width)
            - Cylinder(p.bore / 2, p.width + 1)
            - _groove_torus(p))


def outer_race(p: BearingParams) -> Solid:
    """Annulus outer_shoulder_radius..outer_d/2 minus the groove torus."""
    return (Cylinder(p.outer_d / 2, p.width)
            - Cylinder(p.outer_shoulder_radius, p.width + 1)
            - _groove_torus(p))


def ball(p: BearingParams, i: int) -> Solid:
    """The i-th ball: rotation-copy placement law — ball i sits on the pitch
    circle at angle 2πi/n_balls, z=0. All balls congruent by construction, so
    symmetry arguments in the gates (capture checked on ball 0) are sound."""
    if not 0 <= i < p.n_balls:
        raise ValueError(f"ball index {i} out of range 0..{p.n_balls - 1}")
    a = 2 * math.pi * i / p.n_balls
    return Pos(p.pitch_radius * math.cos(a), p.pitch_radius * math.sin(a),
               0) * Sphere(p.ball_d / 2)


def ball_ring(p: BearingParams) -> Shape:
    """All n_balls as ONE multi-body moving set (a Compound — verified to
    work directly as `moving` in screw_clearance) for the orbital gate."""
    return Compound(children=[ball(p, i) for i in range(p.n_balls)])


# --- gate fixtures (one source for the design build and the tests) ---
ORBIT_STATIONS = 15   # stations across one 360/n_balls symmetry period
REST_MAX_GAP = 0.1    # mm — near-contact band ceiling on the rest gap
                      # (rest_gap 0.0794 at defaults sits inside it)


def escape_distance(p: BearingParams) -> float:
    """Radial translation that carries a ball clearly past the outer race's
    envelope (used by the capture differential)."""
    return p.outer_d / 2 + p.ball_d / 2 - p.pitch_radius + 1.0


def outer_race_eccentric(p: BearingParams, offset: float) -> Solid:
    """DEFECTIVE outer race for the negative control: the groove torus is
    displaced `offset` mm off-axis, breaking raceway axisymmetry. The orbital
    gate must fail on it — that failure is what proves the sweep checks
    axisymmetry rather than assuming it."""
    return (Cylinder(p.outer_d / 2, p.width)
            - Cylinder(p.outer_shoulder_radius, p.width + 1)
            - Pos(offset, 0, 0) * _groove_torus(p))
