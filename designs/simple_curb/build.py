"""Build, verify, export the simple curb bracelet.
Usage: uv run python -m designs.simple_curb.build
"""
import sys

from claudecad.jewelry.chains import closed_loop
from claudecad.verify import check_chain
from claudecad.export import export_design, export_glb

from .params import CHAIN, TARGET_CIRCUMFERENCE


def main() -> int:
    links, info = closed_loop(CHAIN, TARGET_CIRCUMFERENCE)
    print(f"derived: {info.count} links, radius {info.radius:.2f} mm")
    parts = {f"link_{i:02d}": pl.solid for i, pl in enumerate(links)}
    export_glb(parts, "out/glb/simple_curb.glb")
    report = check_chain(links, closed=True)
    print(report.summary())
    if not report.ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1
    export_design(parts, "out/step/simple_curb.step", assembly_label="simple_curb")
    print("exported out/step/simple_curb.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
