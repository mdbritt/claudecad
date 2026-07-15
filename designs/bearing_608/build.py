"""Build, verify, and export the 608 deep-groove ball bearing.

Usage: uv run python -m designs.bearing_608.build
GLB always; STEP only if the gate passes (exit 1 otherwise). The gate: all 9
parts clean, rest clearance crisp 0 with a positive near-contact gap, THE
bearing property — the 7-ball ring swept as one compound about the axis
(orbital free-spin, one 360/7 symmetry period) with zero interference — the
per-ball capture differential, and the shipped-pose all-pairs guard. A
bearing is a clearance mechanism: every boolean here must read exactly 0.
"""
import sys

from claudecad.hardware.bearing import (
    AXIS, ORBIT_STATIONS, REST_MAX_GAP, ball, ball_ring, escape_distance,
    inner_race, outer_race,
)
from claudecad.verify import (
    check_solid, clearance, intersection_volume, path_clearance,
    screw_clearance,
)
from tools.export import export_design, export_glb

from .params import P


def main() -> int:
    ir, orc = inner_race(P), outer_race(P)
    balls = [ball(P, i) for i in range(P.n_balls)]
    parts = {"bearing_inner": ir, "bearing_outer": orc}
    parts.update({f"ball_{i + 1}": b for i, b in enumerate(balls)})

    # GLB always — the render/preview artifact, even for failures
    export_glb(parts, "out/glb/bearing_608.glb",
               linear_deflection=0.01, angular_deflection=0.1)

    ok = True

    # 1) parts clean
    for name, s in parts.items():
        r = check_solid(s)
        print(f"{name}: valid={r.is_valid} manifold={r.is_manifold} "
              f"pieces={r.piece_count} volume={r.volume:.1f}")
        ok = ok and r.ok

    # 2) rest clearance: crisp 0 + positive near-contact band (ball 0 vs
    #    each race; all balls congruent by the placement law)
    for name, race in (("inner", ir), ("outer", orc)):
        iv = intersection_volume(balls[0], race)
        g = clearance(balls[0], race)
        print(f"rest vs {name}: iv {iv:.4f} (==0), gap {g:.4f} "
              f"(0 < gap <= {REST_MAX_GAP})")
        ok = ok and iv == 0.0 and 0 < g <= REST_MAX_GAP

    # 3) THE bearing property — multi-body orbital free-spin over one
    #    360/n symmetry period, the ball ring moved as ONE compound
    races = ir + orc
    orbit = screw_clearance(ball_ring(P), races, AXIS, (0, 0, 0),
                            0.0, 1.0 / P.n_balls, ORBIT_STATIONS)
    print(f"orbital free-spin over 360/{P.n_balls} deg x {ORBIT_STATIONS} "
          f"stations: max iv {max(orbit):.6f} (==0)")
    ok = ok and max(orbit) == 0.0

    # 4) capture differential (ball 0): blocked out/in/axial; free sans outer
    d = escape_distance(P)
    b_out = max(path_clearance(balls[0], races, (1, 0, 0), d, 9))
    b_in = max(path_clearance(balls[0], races, (-1, 0, 0), P.pitch_radius, 9))
    b_ax = max(path_clearance(balls[0], races, (0, 0, 1), P.width, 9))
    free = max(path_clearance(balls[0], ir, (1, 0, 0), d, 9))
    print(f"capture: out {b_out:.3f} / in {b_in:.3f} / axial {b_ax:.3f} "
          f"(all >0) | sans outer {free:.6f} (==0)")
    ok = ok and b_out > 0 and b_in > 0 and b_ax > 0 and free == 0.0

    # 5) shipped-pose guard: the exported assembly has zero interference
    #    across ALL part pairs (clearance mechanism -> crisp 0)
    names = list(parts)
    worst = max(
        intersection_volume(parts[names[i]], parts[names[j]])
        for i in range(len(names)) for j in range(i + 1, len(names))
    )
    print(f"shipped-pose all-pairs worst iv: {worst:.6f} (==0)")
    ok = ok and worst == 0.0

    if not ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1
    export_design(parts, "out/step/bearing_608.step",
                  assembly_label="bearing_608")
    print("exported out/step/bearing_608.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
