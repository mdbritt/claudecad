"""Chain assemblies built from links. Pure geometry: params in, placed solids out."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np
from build123d import Pos, Rot, Solid, Wire

from claudecad.core.centerline import discretize
from claudecad.jewelry.links import CubanLinkParams, LinkParams, cuban_link, curb_link


def build_link(params: LinkParams | CubanLinkParams) -> tuple[Solid, Wire]:
    """Single dispatch point from link parameters to (solid, centerline wire)."""
    if isinstance(params, CubanLinkParams):
        return cuban_link(params)
    if isinstance(params, LinkParams):
        return curb_link(params)
    raise TypeError(f"unknown link params type: {type(params).__name__}")


def _place_links(base_solid, base_wire, locs, n_centerline) -> list[PlacedLink]:
    return [
        PlacedLink(loc * base_solid, discretize(loc * base_wire, n_centerline))
        for loc in locs
    ]


@dataclass(frozen=True)
class ChainParams:
    """Curb chain: links tilted alternately +/-tilt_deg about the chain axis.

    A prior parameter sweep (2026-07-12) verified pitch 8-11 x tilt 45-60
    interlock without intersection for the default 20x14x4 link, but only
    checked adjacent-pair interlock. That sweep did not check non-adjacent
    pairs: at pitch=9.0/tilt=55.0, same-tilt links two apart (0-2, 1-3;
    2*pitch=18mm apart, same sign of tilt so same orientation) interpenetrate
    by 21.328 mm^3 (see check_chain's full-chain report, which the earlier
    per-pair spike didn't run). Re-swept holding tilt=55.0 and raising pitch
    in 0.5mm steps (8-11mm) with the full 4-link check_chain verification:
    9.0 and 9.5 both fail on the (0,2)/(1,3) pairs; 10.0 is the first passing
    value. Confirmed clean at pitch=10.0, tilt=55.0: all 6 pairs of a 4-link
    chain have zero intersection; adjacent pairs interlock at Lk=+/-1.000112,
    non-adjacent pairs are unlinked at Lk=0.000000.
    """

    link: LinkParams | CubanLinkParams = LinkParams()
    tilt_deg: float = 55.0
    pitch: float = 10.0

    def __post_init__(self):
        if self.pitch <= 0:
            raise ValueError(f"need pitch > 0, got pitch={self.pitch}")


class PlacedLink(NamedTuple):
    solid: Solid
    centerline: np.ndarray  # (n,3) points, world coordinates


def straight_chain(p: ChainParams, count: int) -> list[PlacedLink]:
    """Chain along +X: link i at x=i*pitch, tilted about X, alternating sign."""
    base_solid, base_wire = build_link(p.link)
    locs = [
        Pos(i * p.pitch, 0, 0) * Rot(X=(p.tilt_deg if i % 2 == 0 else -p.tilt_deg))
        for i in range(count)
    ]
    return _place_links(base_solid, base_wire, locs, p.link.n_centerline)


@dataclass(frozen=True)
class LoopInfo:
    """Derived (read-only) values of a closed loop."""

    count: int
    radius: float
    circumference: float


def closed_loop(
    p: ChainParams, target_circumference: float
) -> tuple[list[PlacedLink], LoopInfo]:
    """Closed bracelet: links around a circle in XY, faces up +/-Z.

    Link count = target_circumference/pitch rounded to the nearest even
    integer (odd counts cannot close an alternating +/-tilt pattern); exact
    odd ties round up. The actual radius is then count*pitch / 2*pi, so the
    realized circumference tracks the pitch exactly and the target approximately.
    """
    # nearest even integer to target/pitch (odd counts cannot close an
    # alternating +/-tilt pattern); exact-odd ties round up
    n = 2 * math.floor(target_circumference / (2 * p.pitch) + 0.5)
    if n < 4:
        raise ValueError(
            f"loop needs >=4 links, got {n} from "
            f"target_circumference={target_circumference} pitch={p.pitch}"
        )
    radius = n * p.pitch / (2 * math.pi)
    base_solid, base_wire = build_link(p.link)
    # at angle 0 the link sits at (0,-radius) with its long axis (X)
    # along the circle tangent; Rot(Z) walks it around the loop
    locs = [
        Rot(Z=360 * i / n)
        * Pos(0, -radius, 0)
        * Rot(X=(p.tilt_deg if i % 2 == 0 else -p.tilt_deg))
        for i in range(n)
    ]
    placed = _place_links(base_solid, base_wire, locs, p.link.n_centerline)
    return placed, LoopInfo(count=n, radius=radius, circumference=n * p.pitch)
