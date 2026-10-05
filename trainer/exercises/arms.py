"""Arm isolation: curls and triceps extensions.

Both start with the arm straight, so the straight arm reads 100 and the bent
arm 0. The curl rules catch the two ways people cheat a curl: swinging the
body, and letting the elbows drift forward so the shoulders do the lifting.
"""
from __future__ import annotations

import numpy as np

from .. import geometry as g
from ..pose import PoseFrame
from .base import Exercise, Phase, Rule, View, scale
from .common import ARMS, elbow_angle, nearest_side, torso_tilt


def _curl_signal(f: PoseFrame) -> float:
    # 45 deg (fully curled) -> 0, 155 deg (arm straight) -> 100.
    return scale(elbow_angle(f), 45.0, 155.0)


def _elbow_drift(f: PoseFrame, phase: Phase) -> bool | None:
    """Upper arm swinging forward away from the torso."""
    side = nearest_side(f, (g.L_HIP, g.L_SHOULDER, g.L_ELBOW),
                        (g.R_HIP, g.R_SHOULDER, g.R_ELBOW))
    if side is None:
        return None
    hip, sh, el = (f.world[i] for i in side)
    a = g.angle(hip, sh, el)
    if np.isnan(a):
        return None
    return a > 38.0


def _body_swing(f: PoseFrame, phase: Phase) -> bool | None:
    tilt = torso_tilt(f)
    if np.isnan(tilt):
        return None
    return tilt > 16.0


CURL = Exercise(
    key="curl",
    name="Curl",
    preferred_view=View.SIDE,
    setup_cue="Stand side on to the camera, about two and a half metres away.",
    rep_signal=_curl_signal,
    # The pose model under-reads peak elbow flexion (forearm foreshortened
    # toward the camera): a full demo curl reads ~85-90 deg, i.e. ~40 here.
    bottom_threshold=45.0,
    top_threshold=78.0,
    partial_threshold=60.0,
    partial_cue="Curl it all the way up",
    required_sides=ARMS,
    rules=[
        Rule(id="elbow_drift", cue="Keep your elbows at your sides",
             check=_elbow_drift, view=View.SIDE,
             phases=(Phase.ASCENDING, Phase.BOTTOM, Phase.DESCENDING)),
        Rule(id="body_swing", cue="Stand still, do not swing",
             check=_body_swing, view=View.SIDE, severity="critical"),
    ],
)


def _triceps_signal(f: PoseFrame) -> float:
    # 60 deg (deep bend) -> 0, 165 deg (locked out) -> 100.
    return scale(elbow_angle(f), 60.0, 165.0)


TRICEPS = Exercise(
    key="triceps",
    name="Triceps Extension",
    preferred_view=View.SIDE,
    setup_cue="Stand or lie side on to the camera so your elbow is clearly visible.",
    rep_signal=_triceps_signal,
    # Same under-reading at the deep stretch: a full overhead extension reads
    # ~100 deg (37 here) on the demo.
    bottom_threshold=42.0,
    top_threshold=75.0,
    partial_threshold=60.0,
    partial_cue="Bend all the way down for the full stretch",
    required_sides=ARMS,
    rules=[],
)
