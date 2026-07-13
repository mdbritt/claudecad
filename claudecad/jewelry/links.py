"""Chain link components. Pure geometry: params in, solids out."""
from __future__ import annotations

from dataclasses import dataclass

from build123d import Circle, Edge, Plane, Solid, Wire, loft, sweep

from claudecad.core.centerline import stadium_wire
from claudecad.core.twisted import twisted_centerline_points, twisted_stadium_frame


@dataclass(frozen=True)
class LinkParams:
    """Outer dimensions (mm) of a flat oval link, long axis X."""

    length: float = 20.0
    width: float = 14.0
    wire_d: float = 4.0
    n_centerline: int = 256

    def __post_init__(self):
        if not (0 < self.wire_d < self.width < self.length):
            raise ValueError(
                f"need 0 < wire_d < width < length, got "
                f"wire_d={self.wire_d} width={self.width} length={self.length}"
            )
        if self.n_centerline < 3:
            raise ValueError(f"need n_centerline >= 3, got {self.n_centerline}")

    @property
    def end_radius(self) -> float:
        """Centerline radius of the semicircular ends."""
        return (self.width - self.wire_d) / 2

    @property
    def straight(self) -> float:
        """Full length of each straight centerline segment."""
        return self.length - self.width


def curb_link(p: LinkParams) -> tuple[Solid, Wire]:
    """Flat oval link: circular wire profile swept along a stadium centerline.

    Returns (solid, centerline wire), both centered at the origin in the XY
    plane. The wire is returned untessellated so callers can transform solid
    and centerline together before discretizing.
    """
    w = stadium_wire(p.straight, p.end_radius)
    profile = Plane(origin=w @ 0, z_dir=w % 0) * Circle(p.wire_d / 2)
    return sweep(profile, path=w), w


@dataclass(frozen=True)
class CubanLinkParams:
    """Twisted cuban link, outer dimensions (mm), long axis X.

    twist_deg is limited to [20, 60]: the spike-verified range where the
    ruled-loft construction is boolean-robust (below 20 was only ever
    verified for the PLANAR curb_link; above 60 is unverified).
    """

    length: float = 20.0
    width: float = 14.0
    wire_d: float = 4.1
    twist_deg: float = 60.0
    n_sections: int = 144
    n_centerline: int = 256

    def __post_init__(self):
        if not (0 < self.wire_d < self.width < self.length):
            raise ValueError(
                f"need 0 < wire_d < width < length, got "
                f"wire_d={self.wire_d} width={self.width} length={self.length}"
            )
        if not (20.0 <= self.twist_deg <= 60.0):
            raise ValueError(
                f"need 20 <= twist_deg <= 60 (verified loft range), "
                f"got {self.twist_deg}"
            )
        if self.n_sections < 32:
            raise ValueError(f"need n_sections >= 32, got {self.n_sections}")
        if self.n_centerline < 3:
            raise ValueError(f"need n_centerline >= 3, got {self.n_centerline}")


def cuban_link(p: CubanLinkParams) -> tuple[Solid, Wire]:
    """Twisted link solid (two overlapping half-loop ruled lofts, fused —
    see the construction law in the 2026-07-13 spec) plus a measurement-only
    centerline Wire.

    A single closed loft (first section == last section) buries two
    coincident planar cap discs inside the tube at the seam; the uncut solid
    passes is_valid/is_manifold, but any downstream boolean re-processes the
    membrane into non-manifold topology. Building the tube as two open
    half-loop lofts avoids the buried seam discs entirely (open lofts have
    no closing caps), and overlapping the halves puts their union in generic
    position — each half's end caps lie strictly inside the other half's
    tube, so the boolean consumes them.

    The Wire is a periodic spline through exact map samples; it exists so
    placement transforms and discretization work identically to curb_link.
    It must NEVER be used as a sweep path (that construction is broken in
    OCCT for twisted closed curves; the loft is the only verified builder).
    """
    half = p.n_sections // 2
    ov = 1  # sections of overlap at each junction: generic-position union,
            # no coincident-face fuse, cap discs consumed inside the other half

    def section(idx: int):
        pt, t, xd = twisted_stadium_frame(
            p.length, p.width, p.wire_d, p.twist_deg, idx / p.n_sections
        )
        return Plane(origin=pt, z_dir=t, x_dir=xd) * Circle(p.wire_d / 2)

    first = [section(i) for i in range(-ov, half + ov + 1)]
    second = [section(i) for i in range(half - ov, p.n_sections + ov + 1)]
    solid = loft(first, ruled=True) + loft(second, ruled=True)

    pts = twisted_centerline_points(
        p.length, p.width, p.wire_d, p.twist_deg, p.n_centerline
    )
    wire = Wire([Edge.make_spline([tuple(q) for q in pts], periodic=True)])
    return solid, wire
