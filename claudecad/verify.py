"""Geometry verification: validity, interference, and topological interlock.

Pure functions over build123d shapes and numpy point arrays. No I/O.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from build123d import Pos, Vector


@dataclass(frozen=True)
class SolidReport:
    is_valid: bool
    is_manifold: bool
    volume: float
    piece_count: int = 1

    @property
    def ok(self) -> bool:
        return (
            self.is_valid
            and self.is_manifold
            and self.volume > 0.0
            and self.piece_count == 1
        )


def check_solid(shape) -> SolidReport:
    return SolidReport(
        shape.is_valid, shape.is_manifold, shape.volume, len(shape.solids())
    )


def intersection_volume(a, b) -> float:
    inter = a & b
    return 0.0 if inter is None else inter.volume


def clearance(a, b) -> float:
    """Exact minimum distance between two shapes (0.0 if touching or
    penetrating — combine with intersection_volume to distinguish)."""
    return float(a.distance_to(b))


LINKING_TOL = 0.1  # max deviation of discretized Gauss integral from an integer


def linking_number(c1: np.ndarray, c2: np.ndarray) -> float:
    """Gauss linking integral of two closed curves given as (N,3) point loops.

    Nonzero integer => the loops are topologically inseparable. Midpoint
    quadrature over all segment pairs; exact in the limit, within ~1e-2 of
    an integer at >=256 points for well-separated curves.
    """
    r1, r2 = np.asarray(c1, float), np.asarray(c2, float)
    d1 = np.roll(r1, -1, axis=0) - r1
    d2 = np.roll(r2, -1, axis=0) - r2
    m1, m2 = r1 + 0.5 * d1, r2 + 0.5 * d2
    diff = m1[:, None, :] - m2[None, :, :]
    dist3 = np.linalg.norm(diff, axis=2) ** 3
    cross = np.cross(d1[:, None, :], d2[None, :, :])
    integrand = np.einsum("nmk,nmk->nm", cross, diff) / dist3
    return float(integrand.sum() / (4 * np.pi))


@dataclass(frozen=True)
class PairCheck:
    i: int
    j: int
    adjacent: bool
    intersection: float
    linking: float
    adjacent_distance: int = 0
    gap: float | None = None
    gap_ok: bool = True

    @property
    def is_linked(self) -> bool:
        return (
            abs(round(self.linking)) >= 1
            and abs(self.linking - round(self.linking)) < LINKING_TOL
        )

    @property
    def ok(self) -> bool:
        if self.intersection > 0.0:
            return False
        if not self.gap_ok:
            return False
        return self.is_linked if self.adjacent else not self.is_linked


@dataclass(frozen=True)
class ChainReport:
    solids: list[SolidReport]
    pairs: list[PairCheck]

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.solids) and all(p.ok for p in self.pairs)

    def failures(self) -> list[str]:
        msgs = []
        for i, s in enumerate(self.solids):
            if not s.ok:
                msgs.append(
                    f"link {i}: invalid solid (valid={s.is_valid} "
                    f"manifold={s.is_manifold} volume={s.volume:.3f} "
                    f"pieces={s.piece_count})"
                )
        for p in self.pairs:
            if p.intersection > 0.0:
                msgs.append(
                    f"links {p.i},{p.j}: interpenetrates by {p.intersection:.3f} mm^3"
                )
            if p.adjacent and not p.is_linked:
                msgs.append(
                    f"links {p.i},{p.j}: not interlocked (Lk={p.linking:.3f})"
                )
            if not p.adjacent and p.is_linked:
                msgs.append(
                    f"links {p.i},{p.j}: unexpectedly linked (Lk={p.linking:.3f})"
                )
            if not p.gap_ok:
                msgs.append(
                    f"links {p.i},{p.j}: gap {p.gap:.3f} mm exceeds max_gap"
                )
        return msgs

    def summary(self) -> str:
        status = "OK" if self.ok else "FAILED"
        lines = [
            f"chain verification: {status} "
            f"({len(self.solids)} solids, {len(self.pairs)} pairs checked)"
        ]
        lines += self.failures()
        return "\n".join(lines)


def _bboxes_disjoint(a, b) -> bool:
    ba, bb = a.bounding_box(), b.bounding_box()
    return (
        ba.max.X < bb.min.X or bb.max.X < ba.min.X
        or ba.max.Y < bb.min.Y or bb.max.Y < ba.min.Y
        or ba.max.Z < bb.min.Z or bb.max.Z < ba.min.Z
    )


def check_chain(items: Sequence[tuple], closed: bool = False, interlock_depth: int = 1, max_gap: float | None = None) -> ChainReport:
    """Verify a chain of (solid, centerline_points) pairs.

    Pairs within `interlock_depth` cyclic index distance must interlock
    (|Lk| >= 1); pairs beyond must be unlinked; ALL pairs must have zero
    intersection. Dense cuban chains thread depth 2; classic curb chains
    are depth 1 (the default, which preserves the original behavior).
    Disjoint bounding boxes prove zero intersection (a separating
    axis-aligned plane exists), so the boolean is skipped there.

    If max_gap is set, adjacent pairs (within interlock_depth) must satisfy
    clearance <= max_gap (near-contact band: 0.0 for touching up to max_gap).
    max_gap must be positive; raises ValueError if max_gap <= 0.
    Penetration is still caught by the intersection check regardless of max_gap.
    """
    if interlock_depth < 1:
        raise ValueError(f"need interlock_depth >= 1, got {interlock_depth}")
    if max_gap is not None and max_gap <= 0:
        raise ValueError(f"max_gap must be positive, got {max_gap}")
    items = list(items)
    n = len(items)
    solids = [check_solid(s) for s, _ in items]
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            dist = j - i
            if closed and n > 2:
                dist = min(dist, n - (j - i))
            si, ci = items[i]
            sj, cj = items[j]
            inter = 0.0 if _bboxes_disjoint(si, sj) else intersection_volume(si, sj)
            g = None
            g_ok = True
            if max_gap is not None and dist <= interlock_depth:
                g = clearance(si, sj)
                g_ok = g <= max_gap
            pairs.append(
                PairCheck(i, j, dist <= interlock_depth, inter, linking_number(ci, cj), dist, g, g_ok)
            )
    return ChainReport(solids, pairs)


def path_clearance(moving, fixed, axis, distance: float, n: int) -> list[float]:
    """Intersection volume of `moving` translated along `axis` at n stations.

    Station i is a translation of distance * i/(n-1); station 0 is the
    untranslated pose. Returns raw volumes (mm^3) — callers decide pass/fail.
    """
    if n < 2:
        raise ValueError(f"need n >= 2 stations, got {n}")
    a = Vector(*axis) if not isinstance(axis, Vector) else axis
    if a.length == 0:
        raise ValueError(f"axis must be nonzero, got {tuple(a)}")
    a = a.normalized()
    out = []
    for i in range(n):
        d = distance * i / (n - 1)
        placed = Pos(a.X * d, a.Y * d, a.Z * d) * moving
        out.append(intersection_volume(placed, fixed))
    return out
