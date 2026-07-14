"""Threaded fastener: M8×1.25 hex bolt + hex nut, modeled as helical sweeps.

Local frame: thread axis is +Z (`AXIS`). The thread is built by stacking
exact-pitch-spaced copies of a single swept turn so the solid is truly
pitch-periodic (a continuous multi-turn sweep drifts turn-to-turn and reads
as interference under an ideal screw motion — see the design spec). The nut is
the BASIC-profile negative; the bolt is the same profile offset undersize along
the flank normal — so the run-down gate proves an undersize bolt clears a basic
nut rather than that a solid fits its own negative.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

AXIS: tuple[float, float, float] = (0.0, 0.0, 1.0)
FLANK_DEG: float = 60.0  # ISO metric included flank angle


@dataclass(frozen=True)
class FastenerParams:
    """Driving dimensions, mm. major_d/pitch are the nominal ISO thread size
    (M8×1.25). allowance is the single radial+flank clearance that stands in
    for ISO tolerance classes. bolt_turns/nut_turns are thread lengths in
    turns; the nut is shorter so it runs down a longer shank."""

    major_d: float = 8.0
    pitch: float = 1.25
    allowance: float = 0.08  # flank-normal clearance; 0.08 gives rest iv==0 for M8 (verified)
    bolt_turns: int = 6
    nut_turns: int = 3
    hex_across_flats: float = 13.0
    head_height: float = 5.3

    def __post_init__(self):
        bad = {k: v for k, v in self.__dict__.items() if v <= 0}
        if bad:
            raise ValueError(f"all fastener params must be > 0, got {bad}")
        crest_flat = 2 * (self.pitch / 4 - (self.major_d / 2 - self.pitch_radius)
                          * math.tan(math.radians(FLANK_DEG / 2)))
        if self.allowance >= crest_flat:
            raise ValueError(
                f"allowance={self.allowance} must be < the crest flat width "
                f"({crest_flat:.4f}); a larger flank-normal offset erodes the "
                "crest flat away entirely"
            )
        if self.bolt_turns <= self.nut_turns:
            raise ValueError(
                f"need bolt_turns > nut_turns (the nut runs down a longer "
                f"shank), got bolt_turns={self.bolt_turns} "
                f"nut_turns={self.nut_turns}"
            )

    @property
    def H(self) -> float:
        """ISO 68-1 fundamental triangle height."""
        return self.pitch * math.sqrt(3) / 2

    @property
    def pitch_radius(self) -> float:
        return self.major_d / 2 - 3 * self.H / 8

    @property
    def minor_radius(self) -> float:
        """External thread root == internal thread minor radius."""
        return self.major_d / 2 - 5 * self.H / 8
