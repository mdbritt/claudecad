"""Geometry verification: validity, interference, and topological interlock.

Pure functions over build123d shapes and numpy point arrays. No I/O.
"""
from __future__ import annotations

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
