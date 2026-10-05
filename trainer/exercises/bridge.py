"""Hip thrust and glute bridge.

These start with the hips down, so the signal is inverted: a bent hip reads
100 and full extension reads 0. Stopping short of full extension -- the part
that actually loads the glutes -- shows up as a partial.
"""
from __future__ import annotations

import numpy as np

from ..pose import PoseFrame
from .base import Exercise, View, scale
from .common import LEFT_HIP, RIGHT_HIP, TRUNK, side_angles


def _hip_extension(f: PoseFrame) -> float:
    """Hip extension, robust to one leg being lifted.

    Both legs working: the two sides agree and are averaged (taking the max
    there makes 'hips down' read half-raised). One leg lifted: the sides
    differ wildly and the lifted leg's hip stays flexed, so averaging would
    never reach full extension -- use the planted, more extended side.
    """
    left, right = side_angles(f, LEFT_HIP, RIGHT_HIP, min_vis=0.5)
    vals = [a for a in (left, right) if not np.isnan(a)]
    if not vals:
        return float("nan")
    if len(vals) == 1:
        return vals[0]
    # Blend smoothly from mean to max as the sides disagree. A hard switch
    # makes the signal jump when the difference crosses the cut-off, which
    # reads as a turnaround.
    diff = abs(vals[0] - vals[1])
    w = float(np.clip((diff - 12.0) / 20.0, 0.0, 1.0))
    return (1 - w) * (sum(vals) / 2) + w * max(vals)


def _rep_signal(f: PoseFrame) -> float:
    # 172 deg (hips fully extended) -> 0, 128 deg (hips down) -> 100.
    return scale(_hip_extension(f), 172.0, 128.0)


BRIDGE = Exercise(
    key="bridge",
    name="Hip Thrust",
    preferred_view=View.SIDE,
    setup_cue="Set up side on to the camera so your hips and knees are visible.",
    rep_signal=_rep_signal,
    bottom_threshold=30.0,
    # A floor bridge rests at ~140 deg of hip angle (vs ~110 on a bench hip
    # thrust), so "back down" has to be recognised from there.
    top_threshold=58.0,
    partial_threshold=42.0,
    partial_cue="Hips all the way up, squeeze your glutes",
    required_sides=TRUNK,
    rules=[],
)
