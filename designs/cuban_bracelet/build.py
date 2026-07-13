"""Build, verify, and export the cuban link bracelet.

Usage: uv run python -m designs.cuban_bracelet.build
Writes out/glb/cuban_bracelet.glb always; out/step/cuban_bracelet.step only
if verification passes (exit 1 otherwise).
"""
import sys

from claudecad.jewelry.chains import closed_loop
from claudecad.verify import check_chain
from tools.export import export_design, export_glb

from .params import CHAIN, TARGET_CIRCUMFERENCE


def main() -> int:
    links, info = closed_loop(CHAIN, TARGET_CIRCUMFERENCE)
    print(
        f"derived: {info.count} links, radius {info.radius:.2f} mm, "
        f"circumference {info.circumference:.1f} mm"
    )
    parts = {f"link_{i:02d}": pl.solid for i, pl in enumerate(links)}
    export_glb(parts, "out/glb/cuban_bracelet.glb")

    report = check_chain(links, closed=True)
    print(report.summary())
    if not report.ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1

    export_design(parts, "out/step/cuban_bracelet.step", assembly_label="cuban_bracelet")
    print("exported out/step/cuban_bracelet.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
