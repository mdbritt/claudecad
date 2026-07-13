"""Chain assemblies built from links. Pure geometry: params in, placed solids out."""
from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

import numpy as np
from build123d import Pos, Rot, Solid

from claudecad.core.centerline import discretize
from claudecad.jewelry.links import LinkParams, curb_link


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

    link: LinkParams = LinkParams()
    tilt_deg: float = 55.0
    pitch: float = 10.0


class PlacedLink(NamedTuple):
    solid: Solid
    centerline: np.ndarray  # (n,3) points, world coordinates


def straight_chain(p: ChainParams, count: int) -> list[PlacedLink]:
    """Chain along +X: link i at x=i*pitch, tilted about X, alternating sign."""
    base_solid, base_wire = curb_link(p.link)
    placed = []
    for i in range(count):
        tilt = p.tilt_deg if i % 2 == 0 else -p.tilt_deg
        loc = Pos(i * p.pitch, 0, 0) * Rot(X=tilt)
        placed.append(
            PlacedLink(loc * base_solid, discretize(loc * base_wire, p.link.n_centerline))
        )
    return placed
