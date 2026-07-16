"""Build, verify, export <YOUR DESIGN>.

Usage: uv run python -m designs._template.build
The shape of every claudeCAD design: build solids -> ALWAYS write the GLB
-> run the gate -> write STEP ONLY if the gate passes (exit 1 otherwise).
"""
import sys

from build123d import Box

from claudecad.verify import check_solid
from claudecad.export import export_design, export_glb

from .params import EXAMPLE_SIZE


def main() -> int:
    # 1) build your solids (library parts or raw build123d)
    parts = {"example": Box(EXAMPLE_SIZE, EXAMPLE_SIZE, EXAMPLE_SIZE)}

    # 2) GLB always — it's the render/preview artifact, even for failures
    export_glb(parts, "out/glb/_template.glb")

    # 3) the gate: compose the checks your design's claims require
    #    (check_chain for interlocking sequences; path_clearance +
    #    constructed-state differentials for mechanisms; clearance bands
    #    for fit — see claudecad/verify.py)
    ok = all(check_solid(s).ok for s in parts.values())
    print(f"gate: {'OK' if ok else 'FAILED'} ({len(parts)} parts)")

    # 4) STEP only on a passing gate
    if not ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1
    export_design(parts, "out/step/_template.step", assembly_label="template")
    print("exported out/step/_template.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
