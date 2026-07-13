"""Chain assemblies built from links. Pure geometry: params in, placed solids out."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np
from build123d import Location, Plane, Pos, Rot, Solid, Wire, mirror

from claudecad.core.centerline import discretize
from claudecad.jewelry.links import CubanLinkParams, LinkParams, cuban_link, curb_link


def build_link(params: LinkParams | CubanLinkParams) -> tuple[Solid, Wire]:
    """Single dispatch point from link parameters to (solid, centerline wire)."""
    if isinstance(params, CubanLinkParams):
        return cuban_link(params)
    if isinstance(params, LinkParams):
        return curb_link(params)
    raise TypeError(f"unknown link params type: {type(params).__name__}")


def _link_bases(params) -> tuple[tuple[Solid, Wire], tuple[Solid, Wire]]:
    """(even, odd) base geometry for alternating-tilt placement.

    Chiral links (twisted cubans) must alternate handedness: with identical
    chiral links, the (+tilt,-tilt) junction and the (-tilt,+tilt) junction
    are NOT congruent (no link symmetry maps one to the other), and the
    second junction type fails — at the 2026-07-13 bracelet config every
    (odd,even) neighbor pair interpenetrated by an identical 119.531 mm^3
    with Lk=0 while every (even,odd) pair was clean (first caught by the
    full 20-link closed-loop gate; the 4-link probe only ever measured the
    (0,1) junction). Mirroring odd links through their local XY plane makes
    the two junction types mirror images of each other, hence congruent —
    measured identical intersection volumes on the real arc. Physically this
    is how Miami cubans are made: pressing a curb chain flat imparts
    opposite twist to alternately-oriented links.

    Achiral links (planar curbs) are Rot(X=180)-symmetric, so both junction
    types were already congruent; they keep a single base.
    """
    base = build_link(params)
    if isinstance(params, CubanLinkParams):
        # mirror() returns a Curve compound for 1D input; rewrap as Wire so
        # downstream discretize() keeps working
        return base, (
            mirror(base[0], about=Plane.XY),
            Wire(mirror(base[1], about=Plane.XY).edges()),
        )
    return base, base


def _place_links(bases, locs, n_centerline, parities=None) -> list[PlacedLink]:
    if parities is None:
        parities = list(range(len(locs)))
    return [
        PlacedLink(
            loc * bases[par % 2][0],
            discretize(loc * bases[par % 2][1], n_centerline),
        )
        for par, loc in zip(parities, locs)
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
    bases = _link_bases(p.link)
    locs = [
        Pos(i * p.pitch, 0, 0) * Rot(X=(p.tilt_deg if i % 2 == 0 else -p.tilt_deg))
        for i in range(count)
    ]
    return _place_links(bases, locs, p.link.n_centerline)


@dataclass(frozen=True)
class LoopInfo:
    """Derived (read-only) values of a closed loop or open arc."""

    count: int
    radius: float
    circumference: float
    gap_start: Location | None = None
    gap_end: Location | None = None


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
    bases = _link_bases(p.link)
    # at angle 0 the link sits at (0,-radius) with its long axis (X)
    # along the circle tangent; Rot(Z) walks it around the loop
    locs = [
        Rot(Z=360 * i / n)
        * Pos(0, -radius, 0)
        * Rot(X=(p.tilt_deg if i % 2 == 0 else -p.tilt_deg))
        for i in range(n)
    ]
    placed = _place_links(bases, locs, p.link.n_centerline)
    return placed, LoopInfo(count=n, radius=radius, circumference=n * p.pitch)


def open_arc(
    p: ChainParams, target_circumference: float, gap_arc_length: float
) -> tuple[list[PlacedLink], LoopInfo]:
    """Closed-loop placement minus the links inside a gap centered at
    angle 0 (the (0,-radius) point). Chirality parity follows the ORIGINAL
    position index so the arc is a strict subset of the closed loop.
    gap_start/gap_end are tangent frames at the gap edges: gap_end is the
    edge the chain ENTERS the gap (last omitted boundary clockwise),
    gap_start where it LEAVES; both with local +X along the chain tangent
    and local Z up — the frames a clasp bridges between.
    """
    if gap_arc_length <= 0:
        raise ValueError(f"need gap_arc_length > 0, got {gap_arc_length}")
    n = 2 * math.floor(target_circumference / (2 * p.pitch) + 0.5)
    if n < 4:
        raise ValueError(
            f"loop needs >=4 links, got {n} from "
            f"target_circumference={target_circumference} pitch={p.pitch}"
        )
    radius = n * p.pitch / (2 * math.pi)
    gap_half_deg = math.degrees((gap_arc_length / 2) / radius)
    if gap_half_deg >= 90:
        raise ValueError(
            f"gap_arc_length={gap_arc_length} spans {2 * gap_half_deg:.1f} deg "
            f"of a {radius:.1f}mm-radius loop — too large"
        )
    bases = _link_bases(p.link)
    locs, parities = [], []
    for i in range(n):
        phi = 360 * i / n
        # signed angular distance from the gap center at 0 deg
        dist = min(phi, 360 - phi)
        if dist <= gap_half_deg:
            continue
        locs.append(
            Rot(Z=phi)
            * Pos(0, -radius, 0)
            * Rot(X=(p.tilt_deg if i % 2 == 0 else -p.tilt_deg))
        )
        parities.append(i)
    if not locs:
        raise ValueError(
            f"gap_arc_length={gap_arc_length} leaves no links on the loop"
        )
    placed = _place_links(bases, locs, p.link.n_centerline, parities)
    gap_start = Rot(Z=+gap_half_deg) * Pos(0, -radius, 0)
    gap_end = Rot(Z=-gap_half_deg) * Pos(0, -radius, 0)
    return placed, LoopInfo(
        count=len(placed), radius=radius, circumference=n * p.pitch,
        gap_start=gap_start, gap_end=gap_end,
    )
