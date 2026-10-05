"""Joint measurements shared by several trackers.

Rep-signal orientation rule: the engine counts a rep as TOP -> BOTTOM -> TOP,
so whatever position you START a set in must read as 100. For a squat that is
standing; for an overhead press it is the bar at your shoulders, which is why
the press signal is inverted. Get this backwards and the first rep of every
set goes uncounted.
"""
from __future__ import annotations

import numpy as np

from .. import geometry as g
from ..pose import PoseFrame

LEFT_ARM = (g.L_SHOULDER, g.L_ELBOW, g.L_WRIST)
RIGHT_ARM = (g.R_SHOULDER, g.R_ELBOW, g.R_WRIST)
LEFT_LEG = (g.L_HIP, g.L_KNEE, g.L_ANKLE)
RIGHT_LEG = (g.R_HIP, g.R_KNEE, g.R_ANKLE)
LEFT_HIP = (g.L_SHOULDER, g.L_HIP, g.L_KNEE)
RIGHT_HIP = (g.R_SHOULDER, g.R_HIP, g.R_KNEE)
LEFT_ABDUCTION = (g.L_HIP, g.L_SHOULDER, g.L_ELBOW)
RIGHT_ABDUCTION = (g.R_HIP, g.R_SHOULDER, g.R_ELBOW)

# Either side being visible is enough to track: side-on, the far limb is hidden.
ARMS = (LEFT_ARM, RIGHT_ARM)
LEGS = (LEFT_LEG, RIGHT_LEG)
TRUNK = ((g.L_SHOULDER, g.L_HIP, g.L_KNEE), (g.R_SHOULDER, g.R_HIP, g.R_KNEE))


def elbow_angle(f: PoseFrame) -> float:
    return g.visible_limb_angle(f.world, f.vis, LEFT_ARM, RIGHT_ARM)


def knee_angle(f: PoseFrame) -> float:
    return g.visible_limb_angle(f.world, f.vis, LEFT_LEG, RIGHT_LEG)


def hip_angle(f: PoseFrame) -> float:
    """Shoulder-hip-knee: ~175 standing tall, smaller as you fold."""
    return g.visible_limb_angle(f.world, f.vis, LEFT_HIP, RIGHT_HIP)


def abduction_angle(f: PoseFrame) -> float:
    """Hip-shoulder-elbow: ~15 with arms down, ~90 at shoulder height."""
    return g.visible_limb_angle(f.world, f.vis, LEFT_ABDUCTION, RIGHT_ABDUCTION)


def side_angles(f: PoseFrame, left: tuple, right: tuple,
                min_vis: float = 0.6) -> tuple[float, float]:
    """The same joint angle on each side separately, NaN where not visible."""
    out = []
    for a, b, c in (left, right):
        if min(f.vis[a], f.vis[b], f.vis[c]) < min_vis:
            out.append(float("nan"))
        else:
            out.append(g.angle(f.world[a], f.world[b], f.world[c]))
    return out[0], out[1]


def torso_tilt(f: PoseFrame) -> float:
    """Degrees the hip->shoulder line leans away from vertical."""
    if not f.visible(g.L_SHOULDER, g.R_SHOULDER, g.L_HIP, g.R_HIP, threshold=0.5):
        return float("nan")
    shoulders = g.midpoint(f.world[g.L_SHOULDER], f.world[g.R_SHOULDER])
    hips = g.midpoint(f.world[g.L_HIP], f.world[g.R_HIP])
    return g.tilt_from_vertical(hips, shoulders)


def nearest_side(f: PoseFrame, left: tuple, right: tuple) -> tuple | None:
    """The better-visible of two landmark groups, or None if neither is."""
    lv = min(f.vis[i] for i in left)
    rv = min(f.vis[i] for i in right)
    best, vis = (left, lv) if lv >= rv else (right, rv)
    return best if vis >= 0.5 else None


def body_line_offset(f: PoseFrame) -> float:
    """How far the hip sits off the shoulder->ankle line, image plane.

    Positive = hip below the line (sagging), negative = above it (piked).
    Scaled by body length so it reads the same at any distance. NaN when the
    near side is not visible.
    """
    side = nearest_side(f, (g.L_SHOULDER, g.L_HIP, g.L_ANKLE),
                        (g.R_SHOULDER, g.R_HIP, g.R_ANKLE))
    if side is None:
        return float("nan")
    s, h, a = (f.px[i].astype(float) for i in side)
    line = a - s
    length = float(np.linalg.norm(line))
    if length < 1e-3:
        return float("nan")
    # Signed perpendicular distance; image y grows downward.
    t = np.clip(np.dot(h - s, line) / (length ** 2), 0.0, 1.0)
    closest = s + t * line
    offset = h - closest
    sign = 1.0 if offset[1] > 0 else -1.0
    return sign * float(np.linalg.norm(offset)) / length
