"""Lateral raise.

The signal is shoulder abduction, inverted so arms-down reads 100. Seen from
the front both arms are visible, which is what the two form rules need.
"""
from __future__ import annotations

import numpy as np

from ..pose import PoseFrame
from .base import Exercise, Phase, Rule, View, scale
from .common import (LEFT_ABDUCTION, RIGHT_ABDUCTION, abduction_angle,
                     side_angles)


def _rep_signal(f: PoseFrame) -> float:
    # 20 deg (arms down) -> 100, 85 deg (shoulder height) -> 0.
    return scale(abduction_angle(f), 85.0, 20.0)


def _too_high(f: PoseFrame, phase: Phase) -> bool | None:
    a = abduction_angle(f)
    if np.isnan(a):
        return None
    return a > 108.0


def _uneven(f: PoseFrame, phase: Phase) -> bool | None:
    left, right = side_angles(f, LEFT_ABDUCTION, RIGHT_ABDUCTION)
    if np.isnan(left) or np.isnan(right):
        return None
    return abs(left - right) > 22.0


LATERAL = Exercise(
    key="lateral",
    name="Lateral Raise",
    preferred_view=View.FRONT,
    setup_cue="Face the camera, about two and a half metres away.",
    rep_signal=_rep_signal,
    bottom_threshold=25.0,
    top_threshold=75.0,
    partial_threshold=55.0,
    partial_cue="Raise your arms to shoulder height",
    required_sides=(LEFT_ABDUCTION, RIGHT_ABDUCTION),
    rules=[
        Rule(id="too_high", cue="Stop at shoulder height", check=_too_high,
             view=View.FRONT, phases=(Phase.BOTTOM,), cooldown=10.0),
        Rule(id="uneven_raise", cue="Raise both arms evenly", check=_uneven,
             view=View.FRONT, phases=(Phase.BOTTOM,), cooldown=10.0),
    ],
)
