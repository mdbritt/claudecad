"""Build, verify, export <YOUR DESIGN>.

Usage: uv run python -m designs._template.build
The shape of every claudeCAD design: build solids -> ALWAYS write the GLB
-> run the gate -> write STEP ONLY if the gate passes (exit 1 otherwise).

This starter is a PEG-AND-SOCKET fit demonstrating the three core gate
patterns (see the /cad skill's verification laws):
  1. parts clean    — check_solid(...).ok for every part
  2. clearance fit  — zero interference AND a real air gap in a band
  3. mechanism      — a free/blocked differential: the peg withdraws
                      axially (free) but cannot escape sideways (blocked)
"""
import sys

from build123d import Box, Cylinder, Pos

from claudecad.export import export_design, export_glb
from claudecad.verify import (check_solid, clearance, intersection_volume,
                              path_clearance)

from .params import (BASE_H, BASE_L, BASE_W, BORE_DEPTH, FIT_CLEARANCE,
                     PEG_D, PEG_STICKOUT)


def main() -> int:
    # 1) build the solids (library parts or raw build123d)
    bore_floor = BASE_H - BORE_DEPTH
    base = Pos(0, 0, BASE_H / 2) * Box(BASE_L, BASE_W, BASE_H) \
        - Pos(0, 0, BASE_H - BORE_DEPTH / 2 + 0.5) * Cylinder(
            PEG_D / 2 + FIT_CLEARANCE, BORE_DEPTH + 1)
    peg_len = BORE_DEPTH + PEG_STICKOUT
    # seat the peg FIT_CLEARANCE above the bore floor: nothing ever touches
    # (a coplanar face is a defect — see the /cad clearance law)
    peg = Pos(0, 0, bore_floor + FIT_CLEARANCE + peg_len / 2) * Cylinder(
        PEG_D / 2, peg_len)
    parts = {"base": base, "peg": peg}

    # 2) GLB always — the render/preview artifact, even for failures
    export_glb(parts, "out/glb/_template.glb")

    ok = True

    # 3a) parts clean
    for name, s in parts.items():
        r = check_solid(s)
        print(f"{name}: valid={r.is_valid} manifold={r.is_manifold} "
              f"pieces={r.piece_count} volume={r.volume:.1f}")
        ok = ok and r.ok

    # 3b) clearance fit: crisp zero interference AND a real air gap
    iv = intersection_volume(peg, base)
    gap = clearance(peg, base)
    print(f"fit: iv {iv:.4f} (==0), gap {gap:.4f} "
          f"(0 < gap <= {FIT_CLEARANCE})")
    ok = ok and iv == 0.0 and 0 < gap <= FIT_CLEARANCE

    # 3c) the smallest mechanism differential: withdrawing the peg axially
    # is FREE (0 at every station); pushing it sideways is BLOCKED (>0).
    # Note the distances: blocked legs sample the BLOCKING BAND densely
    # (band-scale distance, here one peg diameter), never envelope-scale.
    out_free = path_clearance(peg, base, (0, 0, 1), peg_len + 2, 8)
    lateral = path_clearance(peg, base, (1, 0, 0), PEG_D, 8)
    print(f"withdraw max {max(out_free):.4f} (==0) | "
          f"lateral max {max(lateral):.2f} (>0)")
    ok = ok and max(out_free) == 0.0 and max(lateral) > 0.0

    if not ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1
    export_design(parts, "out/step/_template.step",
                  assembly_label="_template")
    print("exported out/step/_template.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
