"""Chain link components. Pure geometry: params in, solids out."""
from __future__ import annotations

from dataclasses import dataclass

from build123d import Circle, Plane, Solid, Wire, sweep

from claudecad.core.centerline import stadium_wire


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
