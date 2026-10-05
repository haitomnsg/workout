"""Pure geometry helpers over pose landmarks.

Everything here takes plain numpy arrays so it can be unit-tested without a
camera or a pose model in the loop.
"""
from __future__ import annotations

import numpy as np

# MediaPipe Pose landmark indices (33-point BlazePose GHUM topology).
NOSE = 0
L_EAR, R_EAR = 7, 8
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28
L_HEEL, R_HEEL = 29, 30
L_FOOT, R_FOOT = 31, 32


def angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Interior angle at vertex `b`, in degrees. Works in 2D or 3D."""
    ba = a - b
    bc = c - b
    denom = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denom < 1e-9:
        return float("nan")
    cosine = np.clip(np.dot(ba, bc) / denom, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


def midpoint(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return (a + b) / 2.0


def tilt_from_vertical(a: np.ndarray, b: np.ndarray) -> float:
    """Angle in degrees between segment a->b and the world vertical (+Y down).

    0 = perfectly upright, 90 = horizontal. Sign-free on purpose: rules that
    care about direction should compare raw coordinates instead.
    """
    v = b - a
    vertical = np.zeros_like(v)
    vertical[1] = 1.0
    denom = np.linalg.norm(v)
    if denom < 1e-9:
        return float("nan")
    cosine = np.clip(abs(np.dot(v, vertical)) / denom, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


def symmetry_delta(left: float, right: float) -> float:
    """Absolute difference between a left/right pair, NaN-safe."""
    if np.isnan(left) or np.isnan(right):
        return float("nan")
    return abs(left - right)


def torso_length(lm: np.ndarray) -> float:
    """Shoulder-midpoint to hip-midpoint distance.

    Used to normalise pixel distances into body-relative units so thresholds
    survive the user standing closer to or further from the camera.
    """
    shoulders = midpoint(lm[L_SHOULDER], lm[R_SHOULDER])
    hips = midpoint(lm[L_HIP], lm[R_HIP])
    return float(np.linalg.norm(shoulders - hips))


def visible_limb_angle(world: np.ndarray, vis: np.ndarray,
                       left: tuple[int, int, int],
                       right: tuple[int, int, int],
                       min_vis: float = 0.5) -> float:
    """Joint angle from whichever side the camera can actually see.

    Averaging the left and right limb is correct face-on and actively harmful
    side-on: the far limb is occluded, so its landmarks are the model's guess
    rather than an observation, and averaging drags the good side toward the
    bad one.

    Instead, weight each side by its own visibility. Face-on both sides score
    highly and this reduces to the mean; side-on the near limb dominates and
    the occluded one contributes almost nothing.
    """
    out: list[tuple[float, float]] = []
    for triplet in (left, right):
        a, b, c = triplet
        conf = float(min(vis[a], vis[b], vis[c]))
        if conf < min_vis:
            continue
        val = angle(world[a], world[b], world[c])
        if not np.isnan(val):
            # Cubed so a clearly-visible limb dominates a marginal one rather
            # than the two being treated as near-equal evidence.
            out.append((val, conf ** 3))

    if not out:
        return float("nan")
    total = sum(w for _, w in out)
    if total < 1e-9:
        return float("nan")
    return float(sum(v * w for v, w in out) / total)
