"""Build, verify, and export the cuban link bracelet (twisted + diamond-cut).

Usage: uv run python -m designs.cuban_bracelet.build
Writes out/glb/cuban_bracelet.glb always; out/step/cuban_bracelet.step only
if verification passes (exit 1 otherwise).
"""
import math
import sys
from dataclasses import replace

import numpy as np
from build123d import Pos, Rot

from claudecad.assembly import expand
from claudecad.jewelry.chains import open_arc
from claudecad.jewelry.clasps import box_clasp, clasp_tongue
from claudecad.verify import (
    check_chain, check_solid, intersection_volume, linking_number,
    path_clearance,
)
from claudecad.jewelry.finishing import diamond_cut
from tools.export import export_design, export_glb

from .params import (
    CHAIN, CLASP, CUT_Z, GAP_ARC_LENGTH, INTERLOCK_DEPTH, RELIEF_CLEARANCE,
    TARGET_CIRCUMFERENCE,
)


def _placed_points(loc, pts):
    """Apply a build123d Location to an (n,3) numpy point array."""
    return np.array([tuple((loc * Pos(*p)).position) for p in pts])


def main() -> int:
    links, info = open_arc(CHAIN, TARGET_CIRCUMFERENCE, GAP_ARC_LENGTH)
    print(
        f"derived: {info.count} links (open arc), radius {info.radius:.2f} mm, "
        f"circumference {info.circumference:.1f} mm"
    )
    links = diamond_cut(links, CUT_Z)
    print(f"diamond-cut at |z| <= {CUT_Z}")

    # clasp placement, resolved against info.gap_start/gap_end (2026-07-13
    # probe on the real arc). The gap is symmetric about angle 0, so the
    # frame midway between gap_start and gap_end is the identity rotation at
    # x=0, y = chord height; the clasp's local +X runs along that chord.
    # Rot(Z=180) picks the one orientation whose attachment-loop crossings
    # match the chirality of BOTH twisted end-link eyes -- the two eyes are
    # NOT mirror images (twist), and the identity orientation threads only
    # one of them (probed |Lk| = 0.0/1.0 identity vs 1.0/1.0 flipped).
    # Pos centers the part span (span center = box_l/2 after the flip) and
    # seats the box-end corners on the band-centerline chord:
    # y_c = -sqrt(R^2 - (box_l/2)^2).
    # gap_start/gap_end are probe-only; y_c chord math is authoritative.
    asm = box_clasp(CLASP)
    y_c = -math.sqrt(info.radius**2 - (CLASP.box_l / 2) ** 2)
    clasp_loc = Pos(CLASP.box_l / 2, y_c, 0) * Rot(Z=180)

    # relief slots: the clasp overlaps the end-link eye zones by construction
    # (the lug bars thread the eyes), so -- exactly like the manufactured
    # part -- the box/tongue/latch bodies get link-shaped slots where the
    # chain enters. Cutters are the four nearest links, expanded by
    # RELIEF_CLEARANCE, pulled into the clasp's LOCAL frame so every
    # functional gate below runs on the true relieved geometry.
    # The cutters are rebuilt at a coarser tessellation of the SAME links:
    # OCC's fuse returns a Null shape unioning near-tangent copies of the
    # 256-section loft, and a clearance cutter doesn't need render-grade
    # sections -- the surface difference is microns, far under the 0.4 mm
    # clearance. The clearance gate below still measures the real links.
    coarse_chain = replace(CHAIN, link=replace(CHAIN.link, n_sections=96))
    coarse_links, _ = open_arc(coarse_chain, TARGET_CIRCUMFERENCE, GAP_ARC_LENGTH)
    near4 = diamond_cut([coarse_links[i] for i in (0, 1, -2, -1)], CUT_Z)
    # (assembly.relieve bundles this expand-and-subtract into one call, but
    # it recomputes the expansion from scratch every call; since the SAME
    # cutter is reused across all 5 relief applications below -- and
    # expanding these near-tangent coarse lofts is itself expensive -- the
    # expand step is done once here with the library's expand() and reused,
    # exactly like the pre-promotion code.)
    cutter_w = expand(near4[0].solid, RELIEF_CLEARANCE)
    for pl in near4[1:]:
        cutter_w = cutter_w + expand(pl.solid, RELIEF_CLEARANCE)
    cutter = clasp_loc.inverse() * cutter_w
    # ... and the coarse surface sits up to ~0.01 mm inside the fine one in
    # places, which left a 0.0003 mm^3 clasp-vs-chain sliver on the first
    # gate run -- so the EXACT links are subtracted as well (single-body
    # cuts, no self-fuse, so OCC handles the 256-section loft fine here).
    exact_local = [
        clasp_loc.inverse() * links[i].solid for i in (0, 1, -2, -1)
    ]

    def _relieve(shape):
        shape = shape - cutter
        for ex in exact_local:
            shape = shape - ex
        return shape

    parts_local = dict(asm.parts)
    for name in ("clasp_box", "clasp_tongue", "clasp_latch_l", "clasp_latch_r"):
        parts_local[name] = _relieve(parts_local[name])
    placed_clasp = {name: clasp_loc * s for name, s in parts_local.items()}

    parts = {f"link_{i:02d}": pl.solid for i, pl in enumerate(links)}
    parts.update(placed_clasp)
    # finer-than-default tessellation: at the defaults the glossy render's
    # detail view showed banding from mesh chords on the Ø4 wire
    export_glb(parts, "out/glb/cuban_bracelet.glb",
               linear_deflection=0.01, angular_deflection=0.1)

    report = check_chain(links, closed=False, interlock_depth=INTERLOCK_DEPTH)
    print(report.summary())
    ok = report.ok

    # clasp part integrity (post-relief: each part one valid solid)
    for name, s in parts_local.items():
        r = check_solid(s)
        print(f"{name}: valid={r.is_valid} pieces={r.piece_count} "
              f"volume={r.volume:.1f}")
        ok = ok and r.ok

    # clasp functional gate -- run in the clasp's LOCAL frame (the checks are
    # rigid-invariant, so verify BEFORE placement; no world-axis mapping),
    # on the RELIEVED geometry that actually ships
    tongue_c = _relieve(clasp_tongue(CLASP, "compressed"))
    tongue_r = parts_local["clasp_tongue"]
    box_local = parts_local["clasp_box"]
    ins = path_clearance(tongue_c, box_local,
                         axis=(-1, 0, 0), distance=CLASP.blade_l + 1.0, n=12)
    print(f"insertion sweep max iv: {max(ins):.4f}")
    ok = ok and max(ins) == 0.0
    e = CLASP.lip_depth + 0.6
    lock_r = intersection_volume(Pos(-e, 0, 0) * tongue_r, box_local)
    lock_c = intersection_volume(Pos(-e, 0, 0) * tongue_c, box_local)
    print(f"lock differential: relaxed {lock_r:.4f} (>0), compressed {lock_c:.4f} (==0)")
    ok = ok and lock_r > 0.0 and lock_c == 0.0
    guard = sum(
        intersection_volume(Pos(-2.0, 0, 0) * tongue_c, parts_local[l])
        for l in ("clasp_latch_l", "clasp_latch_r")
    )
    print(f"latch guard iv: {guard:.4f} (>0)")
    ok = ok and guard > 0.0

    # pairwise clearance: every relieved local part vs every other (15
    # pairs over the 6 relieved-local parts), plus the seated RELAXED
    # relieved tongue against the relieved box -- all at the SHIPPED
    # (relieved) geometry
    names = list(parts_local)
    worst_pair = 0.0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            worst_pair = max(worst_pair, intersection_volume(
                parts_local[names[i]], parts_local[names[j]]))
    seated = intersection_volume(tongue_r, parts_local["clasp_box"])
    worst_pair = max(worst_pair, seated)
    print(f"clasp pairwise worst iv: {worst_pair:.4f} (==0)")
    ok = ok and worst_pair == 0.0

    # attachment linking: each placed lug bar must thread the nearest end
    # link (box lug faces -X after the flip -> last link; tongue -> first)
    loop_box, loop_tongue = (
        _placed_points(clasp_loc, l) for l in asm.attachment_loops
    )
    lk_box = linking_number(loop_box, links[-1].centerline)
    lk_tongue = linking_number(loop_tongue, links[0].centerline)
    print(f"attachment linking: box lk {lk_box:.3f}, tongue lk {lk_tongue:.3f} "
          f"(|round| == 1)")
    ok = ok and abs(round(lk_box)) == 1 and abs(round(lk_tongue)) == 1

    # clasp vs chain clearance
    worst = max(
        intersection_volume(s, pl.solid)
        for s in placed_clasp.values() for pl in links
    )
    print(f"clasp-vs-chain worst iv: {worst:.4f} (==0)")
    ok = ok and worst == 0.0

    if not ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1
    export_design(parts, "out/step/cuban_bracelet.step", assembly_label="cuban_bracelet")
    print("exported out/step/cuban_bracelet.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
