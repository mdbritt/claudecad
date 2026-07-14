"""Build, verify, and export the snap-gate carabiner.

Usage: uv run python -m designs.carabiner.build
Writes out/glb/carabiner.glb always; out/step/carabiner.step only if the
gate passes (exit 1 otherwise). The gate recomputes the hardware pack's
four proofs on the design instance: parts clean, closed-assembly pairwise
clear, escape ring linked through the closed circuit, and THE carabiner
property — the escape differential (ring blocked when closed, free when
open). Mechanism proof is constructed states, never simulation (/cad).
"""
import sys

from claudecad.hardware.carabiner import (
    ESCAPE_AXIS, carabiner_body, carabiner_gate, carabiner_pin,
    closed_circuit, escape_distance, escape_ring,
)
from claudecad.verify import (
    check_solid, intersection_volume, linking_number, path_clearance,
)
from tools.export import export_design, export_glb

from .params import ESCAPE_STATIONS, P


def main() -> int:
    body = carabiner_body(P)
    gate_closed = carabiner_gate(P, "closed")
    gate_open = carabiner_gate(P, "open")
    pin = carabiner_pin(P)

    # shipped parts: closed-state assembly (open gate is a PROOF state)
    parts = {"carabiner_body": body, "carabiner_gate": gate_closed,
             "carabiner_pin": pin}

    # GLB always — the render/preview artifact, even for failures
    export_glb(parts, "out/glb/carabiner.glb",
               linear_deflection=0.01, angular_deflection=0.1)

    ok = True

    # 1) parts clean (both gate states: open is load-bearing for the proof)
    for name, s in [*parts.items(), ("carabiner_gate_open", gate_open)]:
        r = check_solid(s)
        print(f"{name}: valid={r.is_valid} pieces={r.piece_count} "
              f"volume={r.volume:.1f}")
        ok = ok and r.ok

    # 2) closed-assembly pairwise clearance (real air gaps at every joint)
    names = list(parts)
    worst = 0.0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            worst = max(worst, intersection_volume(
                parts[names[i]], parts[names[j]]))
    print(f"closed-assembly pairwise worst iv: {worst:.4f} (==0)")
    ok = ok and worst == 0.0

    # 3) captured ring links the closed circuit once (and floats clear)
    ring, curve = escape_ring(P)
    lk = linking_number(closed_circuit(P), curve)
    iv_ring = intersection_volume(ring, body)
    print(f"ring linked: lk={lk:.3f} (|round|==1, residual<0.1), "
          f"ring-vs-body iv={iv_ring:.4f} (==0)")
    ok = ok and abs(round(lk)) == 1 and abs(lk - round(lk)) < 0.1
    ok = ok and iv_ring == 0.0

    # 4) escape differential along ESCAPE_AXIS — closed blocks, open frees
    d = escape_distance(P)
    blocked = path_clearance(ring, body + gate_closed, ESCAPE_AXIS, d,
                             ESCAPE_STATIONS)
    free_body = path_clearance(ring, body, ESCAPE_AXIS, d, ESCAPE_STATIONS)
    free_gate = path_clearance(ring, gate_open, ESCAPE_AXIS, d,
                               ESCAPE_STATIONS)
    print(f"escape differential over {d:.1f} mm: closed max iv "
          f"{max(blocked):.4f} (>0); open: body max {max(free_body):.4f}, "
          f"gate max {max(free_gate):.4f} (both ==0)")
    ok = ok and max(blocked) > 0.0
    ok = ok and max(free_body) == 0.0 and max(free_gate) == 0.0

    if not ok:
        print("verification FAILED — STEP not exported", file=sys.stderr)
        return 1
    export_design(parts, "out/step/carabiner.step",
                  assembly_label="carabiner")
    print("exported out/step/carabiner.step")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
