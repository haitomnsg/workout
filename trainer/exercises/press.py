"""Overhead press: barbell, seated dumbbell, Arnold.

A press starts with the weight at your shoulders, so that is the TOP of the
signal (100) and lockout is the BOTTOM (0). The rep counts when the weight
comes back down to your shoulders -- which also means a press you never lock
out is caught as a partial.
"""
from __future__ import annotations

import numpy as np

from .base import Exercise, Phase, Rule, View, scale
from .common import ARMS, LEFT_ARM, RIGHT_ARM, elbow_angle, side_angles, torso_tilt
from ..pose import PoseFrame


def _rep_signal(f: PoseFrame) -> float:
    # Elbow 165 deg (locked out) -> 0, 75 deg (weight at shoulders) -> 100.
    return scale(elbow_angle(f), 165.0, 75.0)


def _leaning_back(f: PoseFrame, phase: Phase) -> bool | None:
    """Leaning back turns an overhead press into a standing incline press."""
    tilt = torso_tilt(f)
    if np.isnan(tilt):
        return None
    return tilt > 22.0


def _uneven(f: PoseFrame, phase: Phase) -> bool | None:
    left, right = side_angles(f, LEFT_ARM, RIGHT_ARM)
    if np.isnan(left) or np.isnan(right):
        return None
    return abs(left - right) > 28.0


PRESS = Exercise(
    key="press",
    name="Overhead Press",
    preferred_view=View.FRONT,
    setup_cue="Face the camera, about two and a half metres away, whole body in frame.",
    rep_signal=_rep_signal,
    bottom_threshold=20.0,
    top_threshold=72.0,
    partial_threshold=55.0,
    partial_cue="Press all the way up to straight arms",
    required_sides=ARMS,
    rules=[
        Rule(id="lean_back", cue="Squeeze your glutes, do not lean back",
             check=_leaning_back, view=View.SIDE,
             phases=(Phase.DESCENDING, Phase.BOTTOM), severity="critical"),
        Rule(id="uneven_press", cue="Press both arms evenly",
             check=_uneven, view=View.FRONT, phases=(Phase.BOTTOM,), cooldown=10.0),
    ],
)
