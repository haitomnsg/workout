"""On-screen overlay.

Designed to be readable from three metres away while you are upside down
under a dumbbell, which rules out small text and subtle colours.
"""
from __future__ import annotations

import cv2
import numpy as np

from . import geometry as g
from .engine import Engine
from .exercises.base import Phase, View
from .pose import PoseFrame

SKELETON = [
    (g.L_SHOULDER, g.R_SHOULDER), (g.L_SHOULDER, g.L_ELBOW), (g.L_ELBOW, g.L_WRIST),
    (g.R_SHOULDER, g.R_ELBOW), (g.R_ELBOW, g.R_WRIST),
    (g.L_SHOULDER, g.L_HIP), (g.R_SHOULDER, g.R_HIP), (g.L_HIP, g.R_HIP),
    (g.L_HIP, g.L_KNEE), (g.L_KNEE, g.L_ANKLE), (g.L_ANKLE, g.L_FOOT),
    (g.R_HIP, g.R_KNEE), (g.R_KNEE, g.R_ANKLE), (g.R_ANKLE, g.R_FOOT),
]

GREEN = (120, 240, 120)
AMBER = (60, 190, 255)
RED = (70, 70, 255)
WHITE = (245, 245, 245)
DARK = (28, 28, 28)


def _panel(img, x, y, w, h, alpha=0.55):
    sub = img[y:y + h, x:x + w]
    if sub.size:
        img[y:y + h, x:x + w] = cv2.addWeighted(
            sub, 1 - alpha, np.full_like(sub, DARK, dtype=np.uint8), alpha, 0
        )


def draw(img: np.ndarray, frame: PoseFrame, engine: Engine, fps: float) -> np.ndarray:
    h, w = img.shape[:2]
    colour = RED if engine.active_cues else GREEN

    if frame.ok:
        for a, b in SKELETON:
            if frame.vis[a] > 0.5 and frame.vis[b] > 0.5:
                cv2.line(img, tuple(frame.px[a].astype(int)),
                         tuple(frame.px[b].astype(int)), colour, 3, cv2.LINE_AA)
        for i in range(33):
            if frame.vis[i] > 0.5:
                cv2.circle(img, tuple(frame.px[i].astype(int)), 4, WHITE, -1, cv2.LINE_AA)

    # Header: reps, phase, view.
    _panel(img, 0, 0, w, 96)
    cv2.putText(img, f"{engine.state.reps}", (24, 74),
                cv2.FONT_HERSHEY_SIMPLEX, 2.2, WHITE, 4, cv2.LINE_AA)
    cv2.putText(img, "REPS", (28, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (170, 170, 170), 1, cv2.LINE_AA)
    cv2.putText(img, engine.ex.name, (150, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, WHITE, 2, cv2.LINE_AA)

    view_ok = engine.ex.preferred_view.matches(engine.view)
    view_txt = f"VIEW: {engine.view.value.upper()}"
    cv2.putText(img, view_txt, (150, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                GREEN if view_ok else AMBER, 2, cv2.LINE_AA)
    cv2.putText(img, f"{engine.state.phase.value.upper()}", (400, 74),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (190, 190, 190), 2, cv2.LINE_AA)
    if engine.state.partials:
        cv2.putText(img, f"partials {engine.state.partials}", (560, 74),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, AMBER, 2, cv2.LINE_AA)
    cv2.putText(img, f"{fps:4.1f} fps", (w - 120, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1, cv2.LINE_AA)

    # Rep-signal bar down the right edge, with threshold markers.
    bx, by, bw, bh = w - 58, 120, 26, h - 200
    _panel(img, bx - 6, by - 6, bw + 12, bh + 12, alpha=0.4)
    if not np.isnan(engine.signal):
        fill = int(bh * (1 - engine.signal / 100.0))
        cv2.rectangle(img, (bx, by + fill), (bx + bw, by + bh), colour, -1)
    for thresh, col in ((engine.ex.bottom_threshold, GREEN), (engine.ex.top_threshold, AMBER)):
        y = by + int(bh * (1 - thresh / 100.0))
        cv2.line(img, (bx - 8, y), (bx + bw + 8, y), col, 2, cv2.LINE_AA)

    # Cue banner.
    if engine.active_cues:
        _panel(img, 0, h - 96, w, 96, alpha=0.7)
        for i, cue in enumerate(engine.active_cues[:2]):
            cv2.putText(img, cue, (24, h - 58 + i * 38),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, RED if i == 0 else AMBER,
                        2, cv2.LINE_AA)
    elif not view_ok:
        _panel(img, 0, h - 60, w, 60, alpha=0.6)
        cv2.putText(img, f"Move camera to {engine.ex.preferred_view.value} view for full feedback",
                    (24, h - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, AMBER, 2, cv2.LINE_AA)

    return img


def countdown_overlay(img: np.ndarray, seconds_left: int, message: str) -> np.ndarray:
    h, w = img.shape[:2]
    _panel(img, 0, 0, w, h, alpha=0.6)
    cv2.putText(img, str(seconds_left), (w // 2 - 40, h // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 4.0, WHITE, 6, cv2.LINE_AA)
    cv2.putText(img, message, (40, h // 2 + 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, WHITE, 2, cv2.LINE_AA)
    return img
