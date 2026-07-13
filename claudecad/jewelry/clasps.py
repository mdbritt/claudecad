"""Box clasp: hollow box, folded-spring tongue (two constructed states),
hinged safety latches with pins. Pure prismatic geometry, local frame:
insertion axis +X, box occupies x in [0, box_l] with the mouth at x=0
facing -X, z=0 the chain midplane. Functionality is proven statically
(see the 2026-07-13 box-clasp spec): compressed-tongue insertion sweep,
relaxed-vs-compressed lock differential, latch guard.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from build123d import Box, Cylinder, Pos, Rot, Solid


@dataclass(frozen=True)
class BoxClaspParams:
    """Driving dimensions, mm. Defaults sized to the verified chain
    (link width 15, diamond-cut height 2*2.6). wall and spring_lift were
    retuned from the plan's static prediction (1.2 / 1.6) down to 0.8 / 0.8:
    the original pair made 2*wall+blade_t+leaf_t+spring_lift=6.4 exceed
    box_h=5.2 by 1.2mm, an unconditional geometric impossibility (box_h is
    fixed by the chain interface, so it can't move) — see task-2-report.md."""

    box_l: float = 14.0
    box_w: float = 15.0
    box_h: float = 5.2
    wall: float = 0.8
    lip_depth: float = 1.2
    blade_l: float = 11.0
    blade_w: float = 10.0
    blade_t: float = 1.4
    leaf_t: float = 1.0
    spring_lift: float = 0.8
    button_w: float = 3.0
    button_l: float = 3.0
    button_h: float = 0.8
    lug_l: float = 5.0
    bar_d: float = 2.5
    latch_arm: float = 8.0
    latch_t: float = 1.0
    latch_w: float = 3.0
    pin_d: float = 1.4
    clearance: float = 0.15

    def __post_init__(self):
        vals = self.__dict__
        bad = {k: v for k, v in vals.items() if v <= 0}
        if bad:
            raise ValueError(f"all clasp params must be > 0, got {bad}")
        stack = 2 * self.wall + self.blade_t + self.leaf_t + self.spring_lift
        if stack > self.box_h:
            raise ValueError(
                f"relaxed leaf does not fit: 2*wall+blade_t+leaf_t+spring_lift="
                f"{stack} > box_h={self.box_h}"
            )
        if self.blade_w + 2 * self.clearance >= self.box_w - 2 * self.wall:
            raise ValueError(
                f"blade too wide for cavity: blade_w={self.blade_w} "
                f"cavity_w={self.box_w - 2 * self.wall}"
            )
        if self.blade_l >= self.box_l:
            raise ValueError(
                f"blade longer than box: blade_l={self.blade_l} box_l={self.box_l}"
            )


def _centered_box(l, w, h):
    """Box with x in [0, l], centered in Y and Z (local frame helper)."""
    return Pos(l / 2, 0, 0) * Box(l, w, h)


def clasp_box(p: BoxClaspParams) -> Solid:
    """Hollow box: cavity opening at x=0 (mouth), retention lip across the
    cavity top at the mouth, button slot through the top, rear lug + bar."""
    body = _centered_box(p.box_l, p.box_w, p.box_h)
    cav_w = p.box_w - 2 * p.wall
    cav_h = p.box_h - 2 * p.wall
    # cavity from the mouth to the rear wall
    cavity = _centered_box(p.box_l - p.wall, cav_w, cav_h)
    body = body - cavity
    # retention lip: the top wall keeps a bar of depth lip_depth at the
    # mouth; behind it, a relief pocket lets the relaxed leaf rise.
    relief_l = p.box_l - p.wall - p.lip_depth
    relief = Pos(p.lip_depth, 0, cav_h / 2) * _centered_box(
        relief_l, cav_w, p.wall + 1e-3
    )
    # keep the relief inside the top wall only (does not pierce the top skin
    # over its last 0.4mm so the box top stays closed except the button slot)
    relief = Pos(0, 0, -0.4) * relief
    body = body - relief
    # button slot through the top skin, near the mouth
    slot = Pos(p.lip_depth + p.button_l / 2 + p.clearance, 0,
               p.box_h / 2 - 0.5) * Box(
        p.button_l + 2 * p.clearance, p.button_w + 2 * p.clearance, 2.0
    )
    body = body - slot
    # rear lug: two ears + bar for the end link
    ear_gap = 6.0
    ear_w = (p.box_w - ear_gap) / 2 - 1.0
    for sy in (+1, -1):
        ear = Pos(p.box_l + p.lug_l / 2,
                  sy * (ear_gap / 2 + ear_w / 2), 0) * Box(p.lug_l, ear_w, p.box_h)
        body = body + ear
    bar = Pos(p.box_l + p.lug_l - p.bar_d / 2 - 0.5, 0, 0) * Rot(X=90) * Cylinder(
        p.bar_d / 2, ear_gap + 2 * ear_w
    )
    body = body + bar
    # pivot ear bosses: solid pads that thicken each side wall LOCALLY at
    # the pin axis, so the pin has real box material (not just the thin
    # 0.8mm wall) to seat in. The boss's outer face stays flush with the
    # box's existing outer Y face (bounding box unchanged -- see
    # test_box_outer_dims_match_chain) and grows INWARD instead, into the
    # slack between the cavity wall (box_w/2 - wall) and the tongue
    # blade/leaf's half-width (blade_w/2): that slack always exists
    # because __post_init__ requires blade_w + 2*clearance < cavity width.
    # The bore overshoots outward into open air (harmless, nothing there to
    # cut) and only slightly inward past the boss's own face (still well
    # clear of the blade/leaf).
    for side in (+1, -1):
        ax, _, az = _pin_axis(p, side)
        inner, outer = _boss_span(p, side)
        boss_r = p.pin_d / 2 + p.clearance + _BOSS_COLLAR
        bore_r = p.pin_d / 2 + p.clearance
        boss_len = outer - inner
        boss_center = side * (inner + outer) / 2
        bore_lo = inner - _BOSS_BORE_OVERSHOOT
        bore_hi = outer + _BOSS_BORE_OVERSHOOT
        bore_center = side * (bore_lo + bore_hi) / 2
        boss = Pos(ax, boss_center, az) * Rot(X=90) * Cylinder(boss_r, boss_len)
        bore = Pos(ax, bore_center, az) * Rot(X=90) * Cylinder(
            bore_r, bore_hi - bore_lo
        )
        body = body + boss - bore
    return body


def clasp_tongue(p: BoxClaspParams, state: str) -> Solid:
    """Folded-spring tongue, modeled SEATED. Blade on the cavity floor;
    leaf folds back from the deep (x+) end and rises toward the mouth.
    relaxed: leaf shoulder up by spring_lift (catches the lip);
    compressed: leaf parallel just above the blade (slides free)."""
    if state not in ("relaxed", "compressed"):
        raise ValueError(f"state must be 'relaxed' or 'compressed', got {state!r}")
    z_floor = -(p.box_h / 2) + p.wall + p.clearance
    blade_x0 = p.wall  # blade tip reaches near the rear wall when seated
    blade = Pos(blade_x0 + p.blade_l / 2, 0, z_floor + p.blade_t / 2) * Box(
        p.blade_l, p.blade_w, p.blade_t
    )
    # leaf: same footprint, folded back from the deep end
    lift = p.spring_lift if state == "relaxed" else 0.1
    # build leaf as a sheared prism: flat plate rotated about the fold line
    fold_x = blade_x0 + p.blade_l - 0.8
    angle = math.degrees(math.atan2(lift, p.blade_l - 1.6))
    leaf = Pos(-(p.blade_l - 1.6) / 2 - 0.0, 0, p.leaf_t / 2) * Box(
        p.blade_l - 1.6, p.blade_w, p.leaf_t
    )
    # fold_overlap: the leaf pivot is embedded fold_overlap into the blade
    # (rather than sitting exactly on its top face) so the tilted leaf
    # genuinely overlaps blade volume near the fold instead of touching it
    # along a single edge; edge-only contact leaves the union as two
    # separate solids (piece_count=2) instead of one manifold body.
    fold_overlap = 0.3
    pivot_z = z_floor + p.blade_t - fold_overlap
    leaf = Pos(fold_x, 0, pivot_z) * Rot(Y=angle) * leaf
    tongue = blade + leaf
    # release button on the leaf shoulder (mouth end); x aligned with the
    # box's button slot center (lip_depth + button_l/2 + clearance) so the
    # button doesn't overhang the slot and clip the box's top skin
    sh_x = p.lip_depth + p.button_l / 2 + p.clearance
    sh_z = z_floor + p.blade_t + lift
    button = Pos(sh_x, 0, sh_z + p.leaf_t + p.button_h / 2 - 0.2) * Box(
        p.button_l, p.button_w, p.button_h + 0.4
    )
    tongue = tongue + button
    # tongue lug + bar (mirror of the box lug, on -X side)
    ear_gap = 6.0
    ear_w = (p.box_w - ear_gap) / 2 - 1.0
    for sy in (+1, -1):
        ear = Pos(-p.lug_l / 2, sy * (ear_gap / 2 + ear_w / 2), 0) * Box(
            p.lug_l, ear_w, p.box_h
        )
        tongue = tongue + ear
    # web joining blade to the lug across the mouth
    web = Pos(blade_x0 / 2, 0, z_floor + p.blade_t / 2) * Box(
        blade_x0 + 1e-3, p.blade_w, p.blade_t
    )
    tongue = tongue + web
    bar = Pos(-p.lug_l + p.bar_d / 2 + 0.5, 0, 0) * Rot(X=90) * Cylinder(
        p.bar_d / 2, ear_gap + 2 * ear_w
    )
    return tongue + bar


# --- latches, pins, attachment loops -----------------------------------
#
# _BOSS_D sizes how far the pivot ear boss thickens each side wall, grown
# INWARD from the box's existing outer Y face into the slack between the
# cavity wall and the tongue blade/leaf's half-width -- the box's outer
# bounding box must stay exactly box_w (test_box_outer_dims_match_chain,
# an already-passing Task 2 test), so the boss cannot protrude past it.
# _BOSS_COLLAR is the extra radius around the pin bore so the boss stays
# solid. _LATCH_GAP is a deliberate small air gap between the box's outer
# face and the latch's inner face (avoids a coincident-face boolean
# between two DIFFERENT parts that must show exactly zero intersection).
# _BOSS_BORE_OVERSHOOT/_LATCH_BORE_OVERSHOOT lengthen a bore cut past a
# part's own face for a clean through-cut, into open air (latch side, no
# limit) or slightly into the cavity (box side, still clear of the
# blade/leaf). _PIN_END_MARGIN / _PIN_INSET size the pin within its bores.
_BOSS_D = 0.8
_BOSS_COLLAR = 0.5
_LATCH_GAP = 0.1
_BOSS_BORE_OVERSHOOT = 0.3
_LATCH_BORE_OVERSHOOT = 0.6
_PIN_END_MARGIN = 0.3
_PIN_INSET = 0.1


def _pin_axis(p: BoxClaspParams, side: int):
    """Shared pivot axis for the latch bore and pin, outboard of the box's
    (flush) outer wall face, near the mouth, mid-height. Returns (x, y, z)
    of the axis center; axis direction is Y."""
    ax = 2.5
    ay = side * (p.box_w / 2 + _LATCH_GAP + p.latch_t / 2)
    return (ax, ay, 0.0)


def _boss_span(p: BoxClaspParams, side: int):
    """Magnitude Y-span (unsigned, both < box_w/2 or == box_w/2) of the
    pivot ear boss added to clasp_box: outer_mag is flush with the box's
    existing outer face; inner_mag extends into the cavity by _BOSS_D
    beyond the cavity wall, staying clear of the tongue blade/leaf.
    Multiply by `side` to place on the +Y or -Y wall."""
    outer_mag = p.box_w / 2
    inner_mag = outer_mag - p.wall - _BOSS_D
    return inner_mag, outer_mag


def clasp_latch(p: BoxClaspParams, side: int) -> Solid:
    """U-flip latch, CLOSED position.

    A thin arm pivots at the ear boss and crosses the box/tongue seam at
    x=0. A Y-wide catch flange bridges inward from the arm to the tongue
    lug ear's Y-span, positioned in X just past the ear's seated rear edge
    (x < -lug_l) so it only fouls the ear once the tongue is pulled more
    than ~2mm past seated -- that differential (clear when seated, blocked
    when over-extracted) is the guard mechanism.
    """
    ax, ay, az = _pin_axis(p, side)

    # arm: crosses the seam, connects the pivot (near ax) to the catch zone
    arm_x_lo = -p.lug_l - 1.8
    arm_x_hi = ax
    arm = Pos((arm_x_lo + arm_x_hi) / 2, ay, az) * Box(
        arm_x_hi - arm_x_lo, p.latch_t, p.latch_w
    )

    # catch: spans Y from inside the tongue lug ear's span (ear_gap/2 to
    # ear_gap/2 + ear_w, see clasp_box/clasp_tongue) out to genuinely
    # overlap the arm's inner face (real volume overlap, not edge-touching,
    # so the union fuses into a single manifold piece).
    ear_gap = 6.0  # matches clasp_box / clasp_tongue lug ear layout
    catch_y_inner = side * (ear_gap / 2 + 1.0)
    catch_y_outer = side * (abs(ay) - p.latch_t / 2 + 0.3)
    catch_x_lo = -p.lug_l - 1.5
    catch_x_hi = -p.lug_l - 0.5
    catch = Pos(
        (catch_x_lo + catch_x_hi) / 2,
        (catch_y_inner + catch_y_outer) / 2,
        az,
    ) * Box(
        catch_x_hi - catch_x_lo, abs(catch_y_outer - catch_y_inner), p.latch_w
    )

    latch = arm + catch
    bore = Pos(ax, ay, az) * Rot(X=90) * Cylinder(
        p.pin_d / 2 + p.clearance, p.latch_t + 2 * _LATCH_BORE_OVERSHOOT
    )
    return latch - bore


def clasp_pin(p: BoxClaspParams, side: int) -> Solid:
    """Pivot pin, concentric with the latch bore and the box ear boss bore
    by construction (both built from the same _pin_axis / _boss_span).
    Spans from just inside the boss (recessed off the cavity-side bore
    overshoot) through the boss and latch bores to just past the latch's
    outer face."""
    ax, ay, az = _pin_axis(p, side)
    boss_inner, _ = _boss_span(p, side)
    y_lo = boss_inner + _PIN_INSET
    y_hi = abs(ay) + p.latch_t / 2 + _PIN_END_MARGIN
    center = side * (y_lo + y_hi) / 2
    return Pos(ax, center, az) * Rot(X=90) * Cylinder(p.pin_d / 2, y_hi - y_lo)


def attachment_loop(p: BoxClaspParams, end: str) -> np.ndarray:
    """Closed centerline along the lug bar axis, returning through the lug
    body -- the circuit an end link must thread.

    A purely flat (z=0) rectangle here is topologically useless: an end
    link built by curb_link also lies flat in z=0 (planar wire, "both
    centered at the origin in the XY plane" per its docstring), and two
    coplanar closed curves always have Lk=0 -- no in-plane translation of
    either curve can change that (verified: shifting the test's link along
    X keeps Lk exactly 0.0 at every offset). The loop must leave the
    plane. It dips through z=0 exactly ONCE under the bar (a single clean
    crossing at the bar's own x, where an end link resting flat over the
    bar would be) and dips back a second time at the far end of the
    return leg, deep inside the box/tongue body and outside any real end
    link's footprint -- so that crossing doesn't also land inside a link's
    hole and cancel the first one (two crossings under the SAME hole net
    to Lk=0, exactly like the flat rectangle; see task-3-report.md).
    """
    if end == "box":
        bx = p.box_l + p.lug_l - p.bar_d / 2 - 0.5
        rx = p.box_l - 2.0            # return leg inside the box rear
    elif end == "tongue":
        bx = -p.lug_l + p.bar_d / 2 + 0.5
        rx = 2.0                       # return leg inside the tongue web
    else:
        raise ValueError(f"end must be 'box' or 'tongue', got {end!r}")
    half_y = 5.0
    dz = 1.0
    corners = [
        (bx, -half_y, -dz),   # bar start, below the link's plane
        (bx, +half_y, +dz),   # bar end, above the link's plane -- the
                               # single clean crossing is mid-edge, at
                               # (bx, 0, 0), under the bar
        (rx, +half_y, +dz),   # into the return leg, still above
        (rx, -half_y, +dz),   # across the return leg, still above
        (rx, -half_y, -dz),   # back down -- crossing #2, at x=rx, far
                               # from any end link's hole
    ]
    pts = []
    n_edge = 32
    n = len(corners)
    for k in range(n):
        a = np.array(corners[k], float)
        b = np.array(corners[(k + 1) % n], float)
        for i in range(n_edge):
            pts.append(a + (b - a) * i / n_edge)
    return np.array(pts)


@dataclass(frozen=True)
class ClaspAssembly:
    parts: dict
    insertion_axis: tuple
    attachment_loops: tuple
    _params: BoxClaspParams

    def tongue_state(self, state: str) -> Solid:
        return clasp_tongue(self._params, state)


def box_clasp(p: BoxClaspParams) -> ClaspAssembly:
    return ClaspAssembly(
        parts={
            "clasp_box": clasp_box(p),
            "clasp_tongue": clasp_tongue(p, "relaxed"),
            "clasp_latch_l": clasp_latch(p, +1),
            "clasp_latch_r": clasp_latch(p, -1),
            "clasp_pin_l": clasp_pin(p, +1),
            "clasp_pin_r": clasp_pin(p, -1),
        },
        insertion_axis=(1.0, 0.0, 0.0),
        attachment_loops=(attachment_loop(p, "box"), attachment_loop(p, "tongue")),
        _params=p,
    )
