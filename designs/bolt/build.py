"""Build, verify, and export the M8 hex bolt + nut.

Usage: uv run python -m designs.bolt.build
GLB always; STEP only if the gate passes (exit 1 otherwise). The gate: parts
are clean manifold solids, the analytic thread mesh has a real air gap on
the true pitch (free) but jams under a pure-axial shift and a wrong pitch,
and the SHIPPED assembly (bolt + seated_nut) has near-zero 3D boolean
interference. The analytic leg alone doesn't catch an unseated export — an
origin-pose bolt+nut still passes it while the physical parts jam (head
overlaps nut) — so the shipped-geometry boolean check closes that gap.
Mesh proof is the exact 2D axial section (helical symmetry), not booleans.
"""
import sys

from claudecad.hardware.fastener import (
    AXIAL_SHIFT, SEATED_MAX_IV, WRONG_PITCH_FACTOR, bolt, seated_nut,
    thread_mesh_gap,
)
from claudecad.verify import check_solid, intersection_volume
from tools.export import export_design, export_glb

from .params import P


def main() -> int:
    b, n = bolt(P), seated_nut(P)
    parts = {"bolt": b, "nut": n}
    export_glb(parts, "out/glb/bolt.glb", linear_deflection=0.01,
               angular_deflection=0.1)

    ok = True
    for name, s in parts.items():
        r = check_solid(s)
        print(f"{name}: valid={r.is_valid} manifold={r.is_manifold} "
              f"pieces={r.piece_count} volume={r.volume:.1f}")
        ok = ok and r.ok

    mesh = thread_mesh_gap(P)
    axial = thread_mesh_gap(P, bolt_dz=AXIAL_SHIFT)
    wrong = thread_mesh_gap(P, nut_pitch_factor=WRONG_PITCH_FACTOR)
    print(f"mesh air gap {mesh:+.4f} (free, >0) | axial-shift {axial:+.4f} "
          f"(jam, <0) | wrong-pitch {wrong:+.4f} (jam, <0)")
    ok = ok and mesh > 0 and axial < 0 and wrong < 0

    seated_iv = intersection_volume(b, n)
    print(f"seated 3D interference {seated_iv:.4f} mm^3 "
          f"(< {SEATED_MAX_IV} ceiling, shipped-geometry gate)")
    ok = ok and seated_iv < SEATED_MAX_IV

    if not ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1
    export_design(parts, "out/step/bolt.step", assembly_label="bolt")
    print("exported out/step/bolt.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
