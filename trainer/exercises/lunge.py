"""Split squat family: split squat, Bulgarian split squat, reverse lunge."""
from __future__ import annotations

import numpy as np

from ..pose import PoseFrame
from .base import Exercise, Phase, Rule, View, scale
from .common import LEFT_LEG, LEGS, RIGHT_LEG, torso_tilt


def _hip_height(f: PoseFrame) -> float:
    """How high the hips sit above the feet, in leg lengths: ~0.95 standing,
    ~0.5 at the bottom of a lunge.

    Knee angles are a poor signal here. On a Bulgarian split squat the rear
    foot is on the bench, so that knee stays deeply bent all set; on a
    reverse lunge the legs swap roles as you step. How far the hips drop is
    the same story whichever leg is doing what. The taller leg is used,
    since that is the one with its foot on the floor.
    """
    spans = []
    for hip, knee, ankle in (LEFT_LEG, RIGHT_LEG):
        if min(f.vis[hip], f.vis[knee], f.vis[ankle]) < 0.5:
            continue
        H, K, A = f.world[hip], f.world[knee], f.world[ankle]
        leg = float(np.linalg.norm(K - H) + np.linalg.norm(A - K))
        if leg < 0.1:
            continue
        spans.append(float(A[1] - H[1]) / leg)     # world y points down
    return max(spans) if spans else float("nan")


def _rep_signal(f: PoseFrame) -> float:
    return scale(_hip_height(f), 0.58, 0.93)


def _folding(f: PoseFrame, phase: Phase) -> bool | None:
    tilt = torso_tilt(f)
    if np.isnan(tilt):
        return None
    return tilt > 50.0


LUNGE = Exercise(
    key="lunge",
    name="Split Squat",
    preferred_view=View.SIDE,
    setup_cue="Stand side on to the camera, about two and a half metres away.",
    rep_signal=_rep_signal,
    bottom_threshold=32.0,
    top_threshold=75.0,
    partial_threshold=58.0,
    partial_cue="Lower until your front thigh is parallel",
    required_sides=LEGS,
    rules=[
        Rule(id="torso_fold", cue="Stay tall through your chest",
             check=_folding, view=View.SIDE,
             phases=(Phase.BOTTOM, Phase.ASCENDING), cooldown=10.0),
    ],
)
