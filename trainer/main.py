"""Entry point: python -m trainer.main --exercise squat --weight 8

Keys while running:
    SPACE  start / end the current set
    n      skip the rest timer
    v      mute or unmute the voice
    m      toggle mirroring
    q      quit
"""
from __future__ import annotations

import argparse
import time
from collections import deque

import cv2
import numpy as np

from . import hud, session
from .engine import Engine
from .exercises import REGISTRY, get
from .pose import MediaPipeBackend
from .voice import Voice


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Personal form-checking gym trainer")
    p.add_argument("--exercise", "-e", default="squat", choices=sorted(REGISTRY))
    p.add_argument("--weight", "-w", type=float, default=None,
                   help="Load in kg, logged with each set")
    p.add_argument("--sets", "-s", type=int, default=3)
    p.add_argument("--reps", "-r", type=int, default=10, help="Target reps per set")
    p.add_argument("--rest", type=int, default=90, help="Rest seconds between sets")
    p.add_argument("--camera", "-c", type=int, default=0)
    p.add_argument("--model", default="heavy", choices=("lite", "full", "heavy"))
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--no-voice", action="store_true")
    p.add_argument("--no-mirror", action="store_true")
    return p.parse_args()


def open_camera(index: int, width: int, height: int) -> cv2.VideoCapture:
    # CAP_DSHOW avoids the several-second MSMF startup stall on Windows.
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise SystemExit(
            f"Could not open camera {index}. Close any app using the webcam, "
            f"or try --camera 1."
        )
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, 30)
    return cap


def main() -> int:
    args = parse_args()
    exercise = get(args.exercise)
    voice = Voice(enabled=not args.no_voice)
    backend = MediaPipeBackend(model=args.model)
    cap = open_camera(args.camera, args.width, args.height)
    mirror = not args.no_mirror

    window = "Trainer"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window, args.width, args.height)

    frame_times: deque[float] = deque(maxlen=30)
    engine = Engine(exercise, voice)
    set_index = 1
    running = False           # True while a set is live
    rest_until: float | None = None

    voice.say(exercise.setup_cue, key="setup", force=True)
    print(f"\n{exercise.name} -- {args.sets} sets of {args.reps}")
    print(f"{exercise.setup_cue}\nPress SPACE to start set 1.\n")

    try:
        while True:
            ok, bgr = cap.read()
            if not ok:
                print("Camera read failed.")
                break
            if mirror:
                bgr = cv2.flip(bgr, 1)

            t = time.perf_counter()
            frame_times.append(t)
            fps = (len(frame_times) - 1) / (frame_times[-1] - frame_times[0]) \
                if len(frame_times) > 1 else 0.0

            frame = backend(bgr)

            if running:
                engine.update(frame)
                if args.reps and engine.state.reps >= args.reps:
                    running = False
                    rest_until = time.monotonic() + args.rest
                    _end_set(engine, args, set_index, voice)
                    set_index += 1
                    if set_index > args.sets:
                        voice.say("Exercise complete. Well done.", force=True)
                        time.sleep(2.5)
                        break
                    engine = Engine(exercise, voice)

            bgr = hud.draw(bgr, frame, engine, fps)

            if rest_until is not None:
                left = int(rest_until - time.monotonic())
                if left <= 0:
                    rest_until = None
                    voice.say(f"Set {set_index}. Go.", force=True)
                    running = True
                else:
                    if left in (30, 10, 3):
                        voice.say(f"{left} seconds", key=f"rest{left}", cooldown=2.0)
                    bgr = hud.countdown_overlay(
                        bgr, left, f"Rest -- set {set_index} of {args.sets} next"
                    )
            elif not running:
                cv2.putText(bgr, "SPACE to start", (24, bgr.shape[0] // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.1, (245, 245, 245), 3, cv2.LINE_AA)

            cv2.imshow(window, bgr)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord(" "):
                if running:
                    running = False
                    _end_set(engine, args, set_index, voice)
                    set_index += 1
                    engine = Engine(exercise, voice)
                    if set_index > args.sets:
                        break
                    rest_until = time.monotonic() + args.rest
                else:
                    rest_until = None
                    running = True
                    voice.say("Go", force=True)
            elif key == ord("n") and rest_until is not None:
                rest_until = time.monotonic()
            elif key == ord("v"):
                voice.enabled = not voice.enabled
            elif key == ord("m"):
                mirror = not mirror
    finally:
        cap.release()
        cv2.destroyAllWindows()
        backend.close()
        voice.close()
    return 0


def _end_set(engine: Engine, args, set_index: int, voice: Voice) -> None:
    summary = engine.finish_set()
    if summary["reps"] == 0 and summary["partials"] == 0:
        return
    session.log_set(summary, weight_kg=args.weight)
    print(f"  set {set_index}: {summary['reps']} reps "
          f"({summary['clean_reps']} clean, {summary['partials']} partial)")
    if summary["faults"]:
        worst = max(summary["faults"].items(), key=lambda kv: kv[1])
        print(f"    most common fault: {worst[0]} ({worst[1]} frames)")
    voice.say(f"Set done. {summary['reps']} reps.", force=True)


if __name__ == "__main__":
    raise SystemExit(main())
