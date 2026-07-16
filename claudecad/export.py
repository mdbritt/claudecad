"""Disk export: named STEP assemblies (for Plasticity) and GLB (for rendering).

Part of the installed claudecad package — consumer projects import
claudecad.export."""
from __future__ import annotations

import os

from build123d import Compound, export_gltf, export_step


def _labeled_compound(parts: dict, assembly_label: str) -> Compound:
    shapes = []
    for name, shape in parts.items():
        shape.label = name  # mutates caller's shape label; geometry untouched
        shapes.append(shape)
    comp = Compound(children=shapes)
    comp.label = assembly_label
    return comp


def export_design(parts: dict, path, assembly_label: str = "design") -> None:
    """Write parts as a named STEP assembly. Keys become Plasticity part names."""
    os.makedirs(os.path.dirname(str(path)) or ".", exist_ok=True)
    if not export_step(_labeled_compound(parts, assembly_label), str(path)):
        raise RuntimeError(f"STEP export failed: {path}")


def export_glb(
    parts: dict,
    path,
    linear_deflection: float = 0.02,
    angular_deflection: float = 0.2,
) -> None:
    """Write parts as binary glTF for rendering. Deflections in mm/radians."""
    os.makedirs(os.path.dirname(str(path)) or ".", exist_ok=True)
    comp = _labeled_compound(parts, "render")
    if not export_gltf(
        comp,
        str(path),
        binary=True,
        linear_deflection=linear_deflection,
        angular_deflection=angular_deflection,
    ):
        raise RuntimeError(f"GLB export failed: {path}")
