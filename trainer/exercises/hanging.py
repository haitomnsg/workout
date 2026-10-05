"""Bar work: pull-ups, chin-ups, negatives, hanging knee raises.

Pull-up negatives count correctly without special handling: you jump to the
top (signal drops fast -> BOTTOM), lower slowly to a hang (signal climbs back
-> rep). The engine only needs the hang to read as the top.
"""
from __future__ import annotations

from ..pose import PoseFrame
from .base import Exercise, View, scale
from .common import ARMS, TRUNK, elbow_angle, hip_angle


def _pull_signal(f: PoseFrame) -> float:
    # 70 deg (chin over bar) -> 0, 160 deg (dead hang) -> 100.
    return scale(elbow_angle(f), 70.0, 160.0)


PULLUP = Exercise(
    key="pullup",
    name="Pull-Up",
    preferred_view=View.FRONT,
    setup_cue="Face the camera from the doorway, so your arms and the bar are in frame.",
    rep_signal=_pull_signal,
    bottom_threshold=25.0,
    top_threshold=78.0,
    partial_threshold=55.0,
    partial_cue="All the way, chin over the bar and straight arms at the bottom",
    required_sides=ARMS,
    rules=[],
)


def _knee_raise_signal(f: PoseFrame) -> float:
    # 100 deg (knees up) -> 0, 165 deg (hanging straight) -> 100.
    return scale(hip_angle(f), 100.0, 165.0)


KNEE_RAISE = Exercise(
    key="knee_raise",
    name="Hanging Knee Raise",
    preferred_view=View.SIDE,
    setup_cue="Hang side on to the camera so your hips and knees are visible.",
    rep_signal=_knee_raise_signal,
    bottom_threshold=30.0,
    top_threshold=80.0,
    partial_threshold=60.0,
    partial_cue="Bring your knees higher",
    required_sides=TRUNK,
    rules=[],
)
