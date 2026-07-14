"""Assembly finishing: operations that fit parts of an assembly to each
other. Domain-neutral.
"""
from __future__ import annotations

from build123d import Pos, Solid

_DIRS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


def expand(solid, delta: float) -> Solid:
    """Minkowski-lite outward expansion: `solid` unioned with six
    axis-translated copies (+delta and -delta along each of X, Y, Z).

    Cheap and robust compared to a true offset (no OCCT offset-surface
    computation, and no self-intersection risk on complex surfaces), at the
    cost of directional coverage: the axes themselves get the full `delta`
    of growth, but the guaranteed clearance in an arbitrary direction is
    only ~delta/sqrt(3). Typically used to grow a cutter shape before
    subtracting it from a target, so the target keeps at least `delta` of
    clearance from the unexpanded cutter along the axes (see `relieve`).
    """
    out = solid
    for dx, dy, dz in _DIRS:
        out = out + Pos(dx * delta, dy * delta, dz * delta) * solid
    return out


def relieve(target, cutters, clearance: float) -> Solid:
    """Cut `target` clear of every shape in `cutters`, keeping at least
    `clearance` of separation from each (subject to `expand`'s directional
    coverage caveat).

    Two-tier cut, in this order:
    1. Subtract the union of every cutter expanded by `clearance` (see
       `expand`) — a single cheap, robust cut that provides the clearance
       margin.
    2. Subtract each exact (un-expanded) cutter as well.

    Tier 2 exists because `expand`'s axis-translation union is an
    approximation, not a true offset: on complex (e.g. curved or
    finely-tessellated) cutter geometry it can leave microscopic slivers of
    the exact cutter uncut — near tangencies between the translated copies,
    or in directions where the expansion's coverage falls short of the
    nominal clearance. Subtracting the exact cutter directly guarantees
    zero intersection against it, regardless of tier 1's precision.

    Raises ValueError if `clearance` is negative or `cutters` is empty.

    Caveat: clearance=0.0 passes validation but makes `expand` a degenerate
    coincident-copy fuse (forbidden by the construction laws); use a
    positive clearance.
    """
    if clearance < 0:
        raise ValueError(f"need clearance >= 0, got {clearance}")
    if not cutters:
        raise ValueError(f"relieve needs at least one cutter, got {cutters!r}")
    expanded = expand(cutters[0], clearance)
    for c in cutters[1:]:
        expanded = expanded + expand(c, clearance)
    shape = target - expanded
    for c in cutters:
        shape = shape - c
    return shape
