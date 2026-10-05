"""Hip hinge: Romanian deadlift, single-leg RDL.

Signal is hip flexion (shoulder-hip-knee). The beginner fault worth catching
is bending the knees until the RDL becomes a squat -- the hamstrings stop
working and the lower back takes over.
"""
from __future__ import annotations

import numpy as np

from ..pose import PoseFrame
from .base import Exercise, Phase, Rule, View, scale
from .common import TRUNK, hip_angle, knee_angle


def _rep_signal(f: PoseFrame) -> float:
    # 95 deg (deep hinge) -> 0, 168 deg (standing tall) -> 100.
    return scale(hip_angle(f), 95.0, 168.0)


def _squatting_it(f: PoseFrame, phase: Phase) -> bool | None:
    k = knee_angle(f)
    if np.isnan(k):
        return None
    return k < 128.0


HINGE = Exercise(
    key="hinge",
    name="Romanian Deadlift",
    preferred_view=View.SIDE,
    setup_cue="Stand side on to the camera, about two and a half metres away.",
    rep_signal=_rep_signal,
    bottom_threshold=35.0,
    top_threshold=80.0,
    partial_threshold=62.0,
    partial_cue="Push your hips further back",
    required_sides=TRUNK,
    rules=[
        Rule(id="knees_bend", cue="Soft knees only, push your hips back",
             check=_squatting_it, view=View.SIDE,
             phases=(Phase.DESCENDING, Phase.BOTTOM), severity="critical"),
    ],
)
