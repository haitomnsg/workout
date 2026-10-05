"""Goblet / dumbbell squat.

Rep signal is knee flexion. Thresholds are set so that a squat counts only
when the thigh reaches roughly parallel -- anything shallower is reported as
a partial rather than silently counted.
"""
from __future__ import annotations

import numpy as np

from .. import geometry as g
from ..pose import PoseFrame
from .base import Exercise, Phase, Rule, View, scale


def _knee_angle(f: PoseFrame) -> float:
    """Knee flexion from whichever leg the camera can actually see.

    Side-on, the far leg is occluded and its landmarks are inferred rather
    than observed, so it is weighted down hard instead of averaged in.
    """
    return g.visible_limb_angle(
        f.world, f.vis,
        (g.L_HIP, g.L_KNEE, g.L_ANKLE),
        (g.R_HIP, g.R_KNEE, g.R_ANKLE),
    )


def _rep_signal(f: PoseFrame) -> float:
    # 60 deg (deep) -> 0, 175 deg (locked out) -> 100.
    return scale(_knee_angle(f), 60.0, 175.0)


def _torso_too_folded(f: PoseFrame, phase: Phase) -> bool | None:
    """Chest collapsing forward turns a squat into a good-morning."""
    if not f.visible(g.L_SHOULDER, g.R_SHOULDER, g.L_HIP, g.R_HIP):
        return None
    shoulders = g.midpoint(f.world[g.L_SHOULDER], f.world[g.R_SHOULDER])
    hips = g.midpoint(f.world[g.L_HIP], f.world[g.R_HIP])
    tilt = g.tilt_from_vertical(hips, shoulders)
    if np.isnan(tilt):
        return None
    return tilt > 50.0


def _knees_caving(f: PoseFrame, phase: Phase) -> bool | None:
    """Knees tracking inside the feet -- the classic beginner squat fault.

    Measured as knee separation relative to ankle separation, so it is scale
    free. Only judgeable from the front.
    """
    if not f.visible(g.L_KNEE, g.R_KNEE, g.L_ANKLE, g.R_ANKLE):
        return None
    knee_sep = abs(f.world[g.L_KNEE][0] - f.world[g.R_KNEE][0])
    ankle_sep = abs(f.world[g.L_ANKLE][0] - f.world[g.R_ANKLE][0])
    if ankle_sep < 1e-4:
        return None
    return (knee_sep / ankle_sep) < 0.85


def _uneven_depth(f: PoseFrame, phase: Phase) -> bool | None:
    """One leg working harder than the other, visible near the bottom."""
    left = g.angle(f.world[g.L_HIP], f.world[g.L_KNEE], f.world[g.L_ANKLE])
    right = g.angle(f.world[g.R_HIP], f.world[g.R_KNEE], f.world[g.R_ANKLE])
    delta = g.symmetry_delta(left, right)
    if np.isnan(delta):
        return None
    return delta > 18.0


SQUAT = Exercise(
    key="squat",
    name="Goblet Squat",
    preferred_view=View.SIDE,
    setup_cue=(
        "Stand side on to the camera, about two and a half metres away. "
        "Whole body in frame, feet shoulder width."
    ),
    rep_signal=_rep_signal,
    bottom_threshold=35.0,
    top_threshold=78.0,
    partial_threshold=62.0,
    partial_cue="Go deeper, that rep did not count",
    required_sides=((g.L_HIP, g.L_KNEE, g.L_ANKLE), (g.R_HIP, g.R_KNEE, g.R_ANKLE)),
    rules=[
        Rule(
            id="torso_fold",
            cue="Chest up, stay tall",
            check=_torso_too_folded,
            view=View.SIDE,
            phases=(Phase.DESCENDING, Phase.BOTTOM, Phase.ASCENDING),
        ),
        Rule(
            id="knee_cave",
            cue="Push your knees out",
            check=_knees_caving,
            view=View.FRONT,
            phases=(Phase.DESCENDING, Phase.BOTTOM, Phase.ASCENDING),
            severity="critical",
        ),
        Rule(
            id="uneven",
            cue="Even it out, you are favouring one leg",
            check=_uneven_depth,
            view=View.FRONT,
            phases=(Phase.BOTTOM,),
            cooldown=12.0,
        ),
    ],
)
