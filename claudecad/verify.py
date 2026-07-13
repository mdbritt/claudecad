"""Geometry verification: validity, interference, and topological interlock.

Pure functions over build123d shapes and numpy point arrays. No I/O.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SolidReport:
    is_valid: bool
    is_manifold: bool
    volume: float

    @property
    def ok(self) -> bool:
        return self.is_valid and self.is_manifold and self.volume > 0.0


def check_solid(shape) -> SolidReport:
    return SolidReport(shape.is_valid, shape.is_manifold, shape.volume)


def intersection_volume(a, b) -> float:
    inter = a & b
    return 0.0 if inter is None else inter.volume


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
                    f"manifold={s.is_manifold} volume={s.volume:.3f})"
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


def check_chain(items, closed: bool = False) -> ChainReport:
    """Verify a chain of (solid, centerline_points) pairs.

    Adjacent = consecutive indices (+ wraparound when closed). Adjacent pairs
    must interlock (|Lk|>=1) without touching; all other pairs must be
    unlinked and disjoint. Disjoint bounding boxes prove zero intersection
    (a separating axis-aligned plane exists), so the boolean is skipped.
    """
    items = list(items)
    n = len(items)
    solids = [check_solid(s) for s, _ in items]
    adjacent = {(i, i + 1) for i in range(n - 1)}
    if closed and n > 2:
        adjacent.add((0, n - 1))
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            si, ci = items[i]
            sj, cj = items[j]
            inter = 0.0 if _bboxes_disjoint(si, sj) else intersection_volume(si, sj)
            pairs.append(
                PairCheck(i, j, (i, j) in adjacent, inter, linking_number(ci, cj))
            )
    return ChainReport(solids, pairs)
