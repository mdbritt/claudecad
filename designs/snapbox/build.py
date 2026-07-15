"""Build, verify, and export the hinged snap enclosure.

Usage: uv run python -m designs.snapbox.build
GLB always; STEP only if the gate passes (exit 1 otherwise). The gate: parts
clean, shipped-pose crisp-0 with real air gaps, the off-origin swing arc,
THE box properties — the travel-limit differential (free within travel,
blocked past the stop, same angular parameter) and the snap retention
differential (relaxed blocked / deflected free) — pin capture, and the
displaced-center negative control. Clearance mechanism: every boolean
reads exactly 0 at free stations.
"""
import sys

from claudecad.hardware.snapbox import (
    BLOCKED_BY_DEG, HINGE_AXIS, NEG_CENTER_OFFSET, OPEN_FREE_MAX_DEG,
    OVERTRAVEL_SPAN_DEG, OVERTRAVEL_STATIONS, RETENTION_SPAN_DEG,
    RETENTION_STATIONS, SWING_STATIONS, _rot_about, base, hinge_pin, lid,
    pin_escape_distance,
)
from claudecad.verify import (
    check_solid, clearance, intersection_volume, path_clearance,
    screw_clearance,
)
from tools.export import export_design, export_glb

from .params import P


def main() -> int:
    b = base(P)
    l_relaxed = lid(P, "relaxed")
    l_deflected = lid(P, "deflected")
    pin = hinge_pin(P)
    parts = {"snapbox_base": b, "snapbox_lid": l_relaxed, "snapbox_pin": pin}

    export_glb(parts, "out/glb/snapbox.glb",
               linear_deflection=0.01, angular_deflection=0.1)

    ok = True

    # 1) parts clean (deflected lid is a load-bearing proof state)
    for name, s in [*parts.items(), ("snapbox_lid_deflected", l_deflected)]:
        r = check_solid(s)
        print(f"{name}: valid={r.is_valid} manifold={r.is_manifold} "
              f"pieces={r.piece_count} volume={r.volume:.1f}")
        ok = ok and r.ok

    # 2) shipped pose: crisp 0, real air gaps
    worst = max(intersection_volume(b, l_relaxed),
                intersection_volume(b, pin),
                intersection_volume(l_relaxed, pin))
    g_pin = clearance(pin, b)
    print(f"shipped pose: worst pairwise iv {worst:.6f} (==0), "
          f"pin-bore gap {g_pin:.4f} (== clearance {P.clearance})")
    ok = ok and worst == 0.0 and abs(g_pin - P.clearance) < 1e-6

    # 3) swing arc (off-origin center — the hinge axis, not the origin)
    fixed = b + pin
    sw = screw_clearance(l_deflected, fixed, HINGE_AXIS, P.hinge_center,
                         0.0, P.swing_deg / 360.0, SWING_STATIONS)
    print(f"swing 0..{P.swing_deg:.0f} deg about {P.hinge_center}: "
          f"max iv {max(sw):.6f} (==0)")
    ok = ok and max(sw) == 0.0

    # 4) travel-limit differential (same-parameter free/blocked)
    l_open = _rot_about(P.hinge_center, HINGE_AXIS, P.swing_deg, l_deflected)
    ot = screw_clearance(l_open, fixed, HINGE_AXIS, P.hinge_center,
                         0.0, OVERTRAVEL_SPAN_DEG / 360.0,
                         OVERTRAVEL_STATIONS)
    step = OVERTRAVEL_SPAN_DEG / (OVERTRAVEL_STATIONS - 1)
    free_ok = all(v == 0.0 for i, v in enumerate(ot)
                  if P.swing_deg + i * step <= OPEN_FREE_MAX_DEG)
    blocked_ok = all(v > 0.0 for i, v in enumerate(ot)
                     if P.swing_deg + i * step >= BLOCKED_BY_DEG)
    print(f"travel limit: free through {OPEN_FREE_MAX_DEG} deg "
          f"({free_ok}), blocked from {BLOCKED_BY_DEG} deg ({blocked_ok}), "
          f"max {max(ot):.3f}")
    ok = ok and free_ok and blocked_ok

    # 5) snap retention differential
    rel = screw_clearance(l_relaxed, fixed, HINGE_AXIS, P.hinge_center,
                          0.0, RETENTION_SPAN_DEG / 360.0,
                          RETENTION_STATIONS)
    dfl = screw_clearance(l_deflected, fixed, HINGE_AXIS, P.hinge_center,
                          0.0, RETENTION_SPAN_DEG / 360.0,
                          RETENTION_STATIONS)
    print(f"retention over {RETENTION_SPAN_DEG} deg: relaxed max "
          f"{max(rel):.3f} (>0, rest {rel[0]:.3f}==0) vs deflected max "
          f"{max(dfl):.6f} (==0)")
    ok = ok and rel[0] == 0.0 and max(rel) > 0.0 and max(dfl) == 0.0

    # 6) pin capture (blind-ended bore)
    d = pin_escape_distance(P)
    caps = [max(path_clearance(pin, b + l_relaxed, ax, d, 7))
            for ax in ((0, 0, 1), (0, 1, 0), (1, 0, 0), (-1, 0, 0))]
    print(f"pin capture +Z/+Y/+X/-X: "
          f"{' / '.join(f'{c:.2f}' for c in caps)} (all >0)")
    ok = ok and all(c > 0.0 for c in caps)

    # 7) negative control: displaced hinge center must fail the swing
    hc = P.hinge_center
    bad = screw_clearance(l_deflected, fixed, HINGE_AXIS,
                          (hc[0], hc[1] + NEG_CENTER_OFFSET, hc[2]),
                          0.0, P.swing_deg / 360.0, SWING_STATIONS)
    print(f"negative control (center +{NEG_CENTER_OFFSET} y): max "
          f"{max(bad):.3f} (>0 — the gate detects a mis-built hinge)")
    ok = ok and max(bad) > 0.0

    if not ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1
    export_design(parts, "out/step/snapbox.step", assembly_label="snapbox")
    print("exported out/step/snapbox.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
