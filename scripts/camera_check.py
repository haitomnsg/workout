"""Check your camera and framing before you train.

No rep counting, no voice, no exercise. It answers one question: can the
system see you well enough to coach you? Run this first, and any time you
move the laptop to a new spot.

    python scripts/camera_check.py

Press q to quit.
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trainer import geometry as g          # noqa: E402
from trainer.engine import detect_view     # noqa: E402
from trainer.exercises.base import View    # noqa: E402
from trainer.hud import SKELETON           # noqa: E402
from trainer.pose import MediaPipeBackend  # noqa: E402

GREEN = (120, 240, 120)
AMBER = (60, 190, 255)
RED = (70, 70, 255)
WHITE = (245, 245, 245)

# Landmarks that must be visible for the squat rules to work at all.
NEEDED = {
    "head": [g.NOSE],
    "shoulders": [g.L_SHOULDER, g.R_SHOULDER],
    "hips": [g.L_HIP, g.R_HIP],
    "knees": [g.L_KNEE, g.R_KNEE],
    "ankles": [g.L_ANKLE, g.R_ANKLE],
    "feet": [g.L_FOOT, g.R_FOOT],
}


def assess(frame, w: int, h: int) -> tuple[list[tuple[str, bool, str]], bool]:
    """Returns (checks, all_good) where each check is (label, ok, detail)."""
    checks: list[tuple[str, bool, str]] = []

    if not frame.ok:
        return [("person detected", False, "step into frame")], False
    checks.append(("person detected", True, ""))

    # Every body part the rules need must be visible.
    for name, idx in NEEDED.items():
        ok = all(frame.vis[i] >= 0.6 for i in idx)
        checks.append((f"{name} visible", ok, "" if ok else "out of frame or occluded"))

    # Body should fill a good share of the frame height. Too small and the
    # landmarks get noisy; too large and you will walk out of shot mid-rep.
    ys = [frame.px[i][1] for i in range(33) if frame.vis[i] > 0.5]
    if ys:
        span = (max(ys) - min(ys)) / h
        if span < 0.45:
            checks.append(("distance", False, f"too far ({span:.0%} of frame) -- come closer"))
        elif span > 0.92:
            checks.append(("distance", False, f"too close ({span:.0%} of frame) -- step back"))
        else:
            checks.append(("distance", True, f"{span:.0%} of frame"))

    # Horizontal centring, so you do not drift out of shot during a set.
    xs = [frame.px[i][0] for i in range(33) if frame.vis[i] > 0.5]
    if xs:
        centre = (min(xs) + max(xs)) / 2 / w
        ok = 0.25 < centre < 0.75
        checks.append(("centred", ok, "" if ok else "move to the middle of the frame"))

    # Margin at top and bottom -- you get taller and shorter during a rep.
    if ys:
        ok = min(ys) > h * 0.04 and max(ys) < h * 0.97
        checks.append(("head/feet margin", ok,
                       "" if ok else "tilt the laptop or step back"))

    return checks, all(c[1] for c in checks)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--camera", "-c", type=int, default=0)
    p.add_argument("--model", default="lite", choices=("lite", "full", "heavy"))
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    args = p.parse_args()

    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"Could not open camera {args.camera}.")
        print("Close Zoom/Teams/Camera app, or try --camera 1")
        return 1
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    backend = MediaPipeBackend(model=args.model)
    times: deque[float] = deque(maxlen=30)
    print("Camera open. Stand back so your whole body is in frame.")
    print("Press q to quit.\n")

    try:
        while True:
            ok, bgr = cap.read()
            if not ok:
                print("Camera read failed.")
                break
            bgr = cv2.flip(bgr, 1)
            h, w = bgr.shape[:2]

            t = time.perf_counter()
            times.append(t)
            fps = (len(times) - 1) / (times[-1] - times[0]) if len(times) > 1 else 0.0

            frame = backend(bgr)
            checks, all_good = assess(frame, w, h)
            view = detect_view(frame)

            if frame.ok:
                colour = GREEN if all_good else AMBER
                for a, b in SKELETON:
                    if frame.vis[a] > 0.5 and frame.vis[b] > 0.5:
                        cv2.line(bgr, tuple(frame.px[a].astype(int)),
                                 tuple(frame.px[b].astype(int)), colour, 3, cv2.LINE_AA)
                for i in range(33):
                    if frame.vis[i] > 0.5:
                        cv2.circle(bgr, tuple(frame.px[i].astype(int)), 4,
                                   WHITE, -1, cv2.LINE_AA)

            # Checklist panel.
            panel = bgr[0:len(checks) * 30 + 70, 0:440]
            bgr[0:len(checks) * 30 + 70, 0:440] = cv2.addWeighted(
                panel, 0.35, np.full_like(panel, 25, dtype=np.uint8), 0.65, 0)

            cv2.putText(bgr, "SETUP CHECK", (16, 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, WHITE, 2, cv2.LINE_AA)
            cv2.putText(bgr, f"{fps:4.1f} fps   view: {view.value.upper()}", (16, 56),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)

            for i, (label, ok, detail) in enumerate(checks):
                y = 86 + i * 30
                mark = "OK " if ok else "X  "
                text = f"{mark}{label}" + (f"  -- {detail}" if detail else "")
                cv2.putText(bgr, text, (16, y), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, GREEN if ok else RED, 2, cv2.LINE_AA)

            if all_good:
                cv2.putText(bgr, "READY", (w - 170, h - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.1, GREEN, 3, cv2.LINE_AA)

            cv2.imshow("Setup check", bgr)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        backend.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
