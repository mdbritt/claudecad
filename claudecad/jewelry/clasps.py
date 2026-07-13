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
    return body + bar


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
