"""Exercise definition types.

An exercise is data, not code: a rep signal, two thresholds, and a list of
rules. Adding a movement means writing one small file like squat.py and
never touching the engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

import numpy as np

from ..pose import PoseFrame


class View(str, Enum):
    """Camera angle a rule needs in order to mean anything.

    This is not cosmetic. Squat depth read from the front is guesswork, and
    knee cave read from the side is invisible. The engine detects the actual
    view each frame and silently skips rules that cannot be judged from it,
    which is far better than confidently giving wrong cues.
    """

    SIDE = "side"
    FRONT = "front"
    ANY = "any"

    def matches(self, actual: "View") -> bool:
        return self is View.ANY or actual is View.ANY or self is actual


class Phase(str, Enum):
    TOP = "top"
    DESCENDING = "descending"
    BOTTOM = "bottom"
    ASCENDING = "ascending"


@dataclass
class Rule:
    """One form check. check() returns True when the form is WRONG.

    Returning None means "abstain" -- the landmarks this rule needs are not
    visible enough to judge. Abstaining is always better than guessing.
    """

    id: str
    cue: str
    check: Callable[[PoseFrame, Phase], bool | None]
    view: View = View.ANY
    phases: tuple[Phase, ...] = ()  # empty = every phase
    cooldown: float = 6.0
    severity: str = "warn"  # "warn" | "critical"

    def applies_in(self, phase: Phase) -> bool:
        return not self.phases or phase in self.phases


@dataclass
class Exercise:
    key: str
    name: str
    preferred_view: View
    setup_cue: str
    # Maps a pose frame to one scalar: 0 at the bottom of the rep, 100 at
    # lockout. Everything about rep counting derives from this.
    rep_signal: Callable[[PoseFrame], float]
    # The signal must fall below bottom_threshold and rise back above
    # top_threshold to count a rep. The gap is the hysteresis band that stops
    # a twitch at lockout counting as five reps.
    bottom_threshold: float = 35.0
    top_threshold: float = 75.0
    # If the signal descends past this but never reaches bottom_threshold,
    # the engine calls it a partial rep and speaks partial_cue.
    partial_threshold: float = 60.0
    partial_cue: str = "Not deep enough, that one did not count"
    rules: list[Rule] = field(default_factory=list)
    required_landmarks: tuple[int, ...] = ()
    # Alternative landmark groups, any ONE of which being visible is enough.
    # Side-on the far limb is hidden, so demanding a specific side would fail
    # every time you happen to face the other way.
    required_sides: tuple[tuple[int, ...], ...] = ()
    # Shown in the HUD so you know where to stand before starting.
    setup_distance_m: float = 2.5

    def can_track(self, frame: PoseFrame) -> bool:
        if not frame.ok:
            return False
        if self.required_landmarks and not frame.visible(*self.required_landmarks):
            return False
        if self.required_sides:
            return any(frame.visible(*side) for side in self.required_sides)
        return True


def scale(value: float, lo: float, hi: float) -> float:
    """Map a raw measurement onto the 0-100 rep-signal scale.

    Passing lo > hi inverts the scale, for movements that start at the
    bottom of their joint range (presses from the shoulders, bridges).
    """
    if np.isnan(value):
        return float("nan")
    return float(np.clip((value - lo) / (hi - lo), 0.0, 1.0) * 100.0)
