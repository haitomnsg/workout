"""Push-up family: standard, incline, decline, deficit, close-grip, pike.

The form check is the body line. A single side-on camera sees it well: the
hip should sit on the straight line from shoulder to ankle. Below it is a
sag (lower back takes the load), above it is a pike (shortchanges the chest).
"""
from __future__ import annotations

import numpy as np

from ..pose import PoseFrame
from .base import Exercise, Phase, Rule, View, scale
from .common import ARMS, body_line_offset


def _shoulder_rise(f: PoseFrame) -> float:
    """Shoulder height above the hands, in arm lengths: ~0.9 at the top,
    ~0.3 with the chest down.

    The elbow angle under-reads the bottom of a push-up badly once the
    hands are raised or lowered (the incline and decline demos never read
    below ~110 deg), while the shoulder dropping toward the hands is plain
    to see from the side in every variation.
    """
    rises = []
    for s, e, w in ARMS:
        if min(f.vis[s], f.vis[e], f.vis[w]) < 0.5:
            continue
        S, E, W = f.world[s], f.world[e], f.world[w]
        arm = float(np.linalg.norm(E - S) + np.linalg.norm(W - E))
        if arm < 0.05:
            continue
        rises.append(float(W[1] - S[1]) / arm)       # world y points down
    return max(rises) if rises else float("nan")


def _rep_signal(f: PoseFrame) -> float:
    return scale(_shoulder_rise(f), 0.35, 0.85)


def _sagging(f: PoseFrame, phase: Phase) -> bool | None:
    off = body_line_offset(f)
    if np.isnan(off):
        return None
    return off > 0.07


def _piking(f: PoseFrame, phase: Phase) -> bool | None:
    off = body_line_offset(f)
    if np.isnan(off):
        return None
    return off < -0.10


PUSHUP = Exercise(
    key="pushup",
    name="Push-Up",
    preferred_view=View.SIDE,
    setup_cue="Set up side on to the camera, about two metres away, whole body in frame.",
    rep_signal=_rep_signal,
    bottom_threshold=30.0,
    top_threshold=80.0,
    partial_threshold=60.0,
    partial_cue="Chest closer to the floor, that one did not count",
    required_sides=ARMS,
    rules=[
        Rule(id="hips_sag", cue="Squeeze your glutes, your hips are sagging",
             check=_sagging, view=View.SIDE, severity="critical"),
        Rule(id="hips_pike", cue="Lower your hips into a straight line",
             check=_piking, view=View.SIDE, cooldown=10.0),
    ],
)


# A pike push-up is piked on purpose, so it shares the signal but not the
# body-line rules (they fired on every frame of the demo).
PIKE_PUSHUP = Exercise(
    key="pike",
    name="Pike Push-Up",
    preferred_view=View.SIDE,
    setup_cue="Set up side on to the camera, about two metres away, whole body in frame.",
    rep_signal=_rep_signal,
    bottom_threshold=30.0,
    top_threshold=80.0,
    partial_threshold=60.0,
    partial_cue="Lower your head closer to the floor",
    required_sides=ARMS,
    rules=[],
)
