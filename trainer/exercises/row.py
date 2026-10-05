"""Rows: bent-over dumbbell, one-arm, barbell.

The rep signal runs the other way from a press: 100 is the arm hanging at
full stretch, 0 is the weight pulled to the ribs.

It is measured as how far the hand hangs below the shoulder, in arm lengths
-- not as the elbow angle. Bent over, the arms hang under the torso and are
half hidden, and the pose model's elbow angle there is poor (on the demo
videos it never read below ~120 degrees, so no rep ever counted). The hand
holding the weight is almost always clearly visible. Taking the HIGHER of
the two hands also makes one-arm rows work: the free hand rests on the bench.

The dominant fault is not the arm at all -- it is the torso rising as you
pull, turning a row into a shrug-and-heave.
"""
from __future__ import annotations

import numpy as np

from .. import geometry as g
from ..pose import PoseFrame
from .base import Exercise, Phase, Rule, View, scale
from .common import ARMS


def _hand_drop(f: PoseFrame) -> float:
    """Wrist height below the shoulder in arm lengths (world y points down):
    ~0.9 with the arm hanging, ~0.3 with the weight at the ribs."""
    drops = []
    for s, e, w in ARMS:
        if min(f.vis[s], f.vis[e], f.vis[w]) < 0.5:
            continue
        S, E, W = f.world[s], f.world[e], f.world[w]
        arm = float(np.linalg.norm(E - S) + np.linalg.norm(W - E))
        if arm < 0.05:
            continue
        drops.append(float(W[1] - S[1]) / arm)
    return min(drops) if drops else float("nan")


def _rep_signal(f: PoseFrame) -> float:
    return scale(_hand_drop(f), 0.40, 0.85)


def _torso_rising(f: PoseFrame, phase: Phase) -> bool | None:
    """Hip hinge collapsing upward during the pull.

    A correct bent-over row holds the torso between roughly 15 and 60 degrees
    from horizontal. Standing up past that means the weight is too heavy.
    """
    if not f.visible(g.L_SHOULDER, g.R_SHOULDER, g.L_HIP, g.R_HIP):
        return None
    shoulders = g.midpoint(f.world[g.L_SHOULDER], f.world[g.R_SHOULDER])
    hips = g.midpoint(f.world[g.L_HIP], f.world[g.R_HIP])
    tilt = g.tilt_from_vertical(hips, shoulders)
    if np.isnan(tilt):
        return None
    # tilt is degrees away from vertical; a good hinge sits above 40.
    return tilt < 35.0


def _rounded_back(f: PoseFrame, phase: Phase) -> bool | None:
    """Rough spinal-flexion proxy: neck dropping below the shoulder line.

    A single camera cannot see the lumbar spine, so this deliberately only
    catches the gross version of the fault rather than pretending to measure
    spinal curvature.
    """
    if not f.visible(g.NOSE, g.L_SHOULDER, g.R_SHOULDER, g.L_HIP, g.R_HIP):
        return None
    shoulders = g.midpoint(f.world[g.L_SHOULDER], f.world[g.R_SHOULDER])
    hips = g.midpoint(f.world[g.L_HIP], f.world[g.R_HIP])
    spine = shoulders - hips
    head = f.world[g.NOSE] - shoulders
    a = g.angle(hips, shoulders, f.world[g.NOSE])
    if np.isnan(a):
        return None
    # Near 180 means head continues the spine line; well under means dropped.
    return a < 130.0


ROW = Exercise(
    key="row",
    name="Bent-Over Dumbbell Row",
    preferred_view=View.SIDE,
    setup_cue=(
        "Stand side on to the camera, about two and a half metres away. "
        "Hinge at the hips, back flat, dumbbells hanging."
    ),
    rep_signal=_rep_signal,
    bottom_threshold=38.0,
    top_threshold=75.0,
    partial_threshold=60.0,
    partial_cue="Pull it all the way to your ribs",
    required_sides=((g.L_SHOULDER, g.L_ELBOW, g.L_HIP), (g.R_SHOULDER, g.R_ELBOW, g.R_HIP)),
    rules=[
        Rule(
            id="torso_rising",
            cue="Stay hinged over, do not stand up",
            check=_torso_rising,
            view=View.SIDE,
            severity="critical",
        ),
        Rule(
            id="rounded_back",
            cue="Head up, flatten your back",
            check=_rounded_back,
            view=View.SIDE,
            cooldown=8.0,
            severity="critical",
        ),
    ],
)
