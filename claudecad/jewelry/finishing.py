"""Chain-level finishing: operations on assembled (placed) links.

diamond_cut mirrors real cuban manufacturing: the assembled chain is ground
flat top and bottom. One shared slab guarantees a uniform world-space cut.
"""
from __future__ import annotations

from build123d import Box, Pos

from claudecad.jewelry.chains import PlacedLink


def diamond_cut(links: list[PlacedLink], cut_z: float) -> list[PlacedLink]:
    """Keep material within |z| <= cut_z on every link; centerlines untouched.

    The slab spans the whole chain's XY footprint (single grind, like the
    real process). Severed links are NOT detected here — check_chain's
    piece_count does that; this function only rejects parameter mistakes.
    """
    if cut_z <= 0:
        raise ValueError(f"need cut_z > 0, got {cut_z}")
    if not links:
        raise ValueError("diamond_cut needs at least one link")
    boxes = [pl.solid.bounding_box() for pl in links]
    zmax = max(max(abs(b.max.Z), abs(b.min.Z)) for b in boxes)
    if zmax <= cut_z:
        raise ValueError(
            f"cut_z={cut_z} does not cut: chain z-half-extent is {zmax:.3f}"
        )
    xmin = min(b.min.X for b in boxes)
    xmax = max(b.max.X for b in boxes)
    ymin = min(b.min.Y for b in boxes)
    ymax = max(b.max.Y for b in boxes)
    margin = 2.0
    slab = Pos((xmin + xmax) / 2, (ymin + ymax) / 2, 0) * Box(
        (xmax - xmin) + 2 * margin, (ymax - ymin) + 2 * margin, 2 * cut_z
    )
    out = []
    for i, pl in enumerate(links):
        cut = pl.solid & slab
        if cut is None or not cut.solids():
            raise ValueError(f"diamond_cut emptied link {i} (cut_z={cut_z})")
        out.append(PlacedLink(cut, pl.centerline))
    return out
