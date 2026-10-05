"""Dumbbell bench press (or floor press if you have no bench yet).

Camera goes at chest height, side on. The rep signal is elbow extension, so
a half-lockout registers as a partial instead of quietly counting.
"""
from __future__ import annotations

import numpy as np

from .. import geometry as g
from ..pose import PoseFrame
from .base import Exercise, Phase, Rule, View, scale


def _elbow_angle(f: PoseFrame) -> float:
    """Elbow angle from whichever arm the camera can see clearly."""
    return g.visible_limb_angle(
        f.world, f.vis,
        (g.L_SHOULDER, g.L_ELBOW, g.L_WRIST),
        (g.R_SHOULDER, g.R_ELBOW, g.R_WRIST),
    )


def _rep_signal(f: PoseFrame) -> float:
    # 55 deg (dumbbells at chest) -> 0, 172 deg (locked out) -> 100.
    return scale(_elbow_angle(f), 55.0, 172.0)


def _elbows_flared(f: PoseFrame, phase: Phase) -> bool | None:
    """Elbows at 90 degrees to the torso is the shoulder-impingement position.

    Measured as the angle at the shoulder between the upper arm and the
    torso line; roughly 45-70 degrees is the target.
    """
    if not f.visible(g.L_SHOULDER, g.R_SHOULDER, g.L_ELBOW, g.R_ELBOW, g.L_HIP, g.R_HIP):
        return None
    hips = g.midpoint(f.world[g.L_HIP], f.world[g.R_HIP])
    angles = []
    for sh, el in ((g.L_SHOULDER, g.L_ELBOW), (g.R_SHOULDER, g.R_ELBOW)):
        a = g.angle(hips, f.world[sh], f.world[el])
        if not np.isnan(a):
            angles.append(a)
    if not angles:
        return None
    return float(np.mean(angles)) > 78.0


def _uneven_press(f: PoseFrame, phase: Phase) -> bool | None:
    """One dumbbell finishing ahead of the other."""
    left = g.angle(f.world[g.L_SHOULDER], f.world[g.L_ELBOW], f.world[g.L_WRIST])
    right = g.angle(f.world[g.R_SHOULDER], f.world[g.R_ELBOW], f.world[g.R_WRIST])
    delta = g.symmetry_delta(left, right)
    if np.isnan(delta):
        return None
    return delta > 20.0


BENCH_PRESS = Exercise(
    key="bench",
    name="Dumbbell Bench Press",
    preferred_view=View.SIDE,
    setup_cue=(
        "Camera side on at chest height, about two metres away. "
        "Head to hips must be in frame."
    ),
    rep_signal=_rep_signal,
    bottom_threshold=32.0,
    # Arms pointing up at the ceiling foreshorten in a side-on camera, so
    # the model under-reads lockout (a straight-armed demo reads ~142 deg).
    # 66 here is ~132 deg measured, which is a real lockout in practice.
    top_threshold=66.0,
    partial_threshold=58.0,
    partial_cue="Lower it further, full range",
    required_sides=((g.L_SHOULDER, g.L_ELBOW, g.L_WRIST), (g.R_SHOULDER, g.R_ELBOW, g.R_WRIST)),
    setup_distance_m=2.0,
    rules=[
        Rule(
            id="elbow_flare",
            cue="Tuck your elbows in, not straight out",
            check=_elbows_flared,
            view=View.ANY,
            phases=(Phase.DESCENDING, Phase.BOTTOM),
            severity="critical",
        ),
        Rule(
            id="uneven_press",
            cue="Keep both arms level",
            check=_uneven_press,
            view=View.FRONT,
            phases=(Phase.ASCENDING, Phase.TOP),
            cooldown=10.0,
        ),
    ],
)
