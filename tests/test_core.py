"""Camera-free tests for the parts most likely to be subtly wrong.

Run with: python tests/test_core.py

Deliberately dependency-light -- geometry, smoothing and the rep state
machine are pure functions over numpy, so none of this needs mediapipe,
a webcam, or a person standing in front of one.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trainer import geometry as g                        # noqa: E402
from trainer.engine import Engine, detect_view           # noqa: E402
from trainer.exercises.base import View                  # noqa: E402
from trainer.exercises.squat import SQUAT                # noqa: E402
from trainer.pose import PoseFrame                       # noqa: E402
from trainer.smoothing import Hysteresis, OneEuroFilter  # noqa: E402

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label} {detail}")
        FAILURES.append(label)


class SilentVoice:
    """Stand-in so tests never open a TTS engine."""

    enabled = False

    def __init__(self) -> None:
        self.spoken: list[str] = []

    def say(self, text, key=None, cooldown=None, force=False):
        self.spoken.append(text)
        return True

    def reset_cooldowns(self):
        pass

    def close(self):
        pass


# ---------------------------------------------------------------- geometry

def test_geometry() -> None:
    print("\ngeometry")
    a = np.array([0.0, 1.0])
    b = np.array([0.0, 0.0])
    c = np.array([1.0, 0.0])
    check("right angle is 90", abs(g.angle(a, b, c) - 90.0) < 1e-6)

    straight = g.angle(np.array([0.0, 1.0]), b, np.array([0.0, -1.0]))
    check("straight line is 180", abs(straight - 180.0) < 1e-6)
    check("degenerate angle is nan", math.isnan(g.angle(b, b, c)))

    vert = g.tilt_from_vertical(np.array([0.0, 0.0]), np.array([0.0, 1.0]))
    check("vertical segment is 0 deg", abs(vert) < 1e-6)
    horiz = g.tilt_from_vertical(np.array([0.0, 0.0]), np.array([1.0, 0.0]))
    check("horizontal segment is 90 deg", abs(horiz - 90.0) < 1e-6)

    check("symmetry_delta is nan-safe",
          math.isnan(g.symmetry_delta(float("nan"), 10.0)))


# --------------------------------------------------------------- smoothing

def test_smoothing() -> None:
    print("\nsmoothing")
    f = OneEuroFilter(min_cutoff=1.0, beta=0.0)
    rng = np.random.default_rng(0)
    truth = np.array([[100.0, 100.0]])
    noisy = [truth + rng.normal(0, 3.0, size=(1, 2)) for _ in range(120)]

    raw_err = float(np.mean([np.linalg.norm(x - truth) for x in noisy]))
    smoothed = [f(x, i / 30.0) for i, x in enumerate(noisy)]
    sm_err = float(np.mean([np.linalg.norm(x - truth) for x in smoothed[30:]]))
    check("filter reduces jitter on a still joint", sm_err < raw_err * 0.6,
          f"(raw {raw_err:.2f} -> smoothed {sm_err:.2f})")

    h = Hysteresis(on_frames=3, off_frames=5)
    on = [h.update(True) for _ in range(3)]
    check("hysteresis needs 3 frames to turn on",
          on == [False, False, True], f"got {on}")
    off = [h.update(False) for _ in range(5)]
    check("hysteresis needs 5 frames to turn off",
          off == [True, True, True, True, False], f"got {off}")

    h2 = Hysteresis(on_frames=3, off_frames=5)
    flicker = [h2.update(i % 2 == 0) for i in range(20)]
    check("hysteresis ignores alternating noise", not any(flicker))


# ------------------------------------------------------------- synthetic body

def _skeleton(knee_deg: float, view: str = "side",
              torso_tilt_deg: float = 10.0) -> PoseFrame:
    """A synthetic standing figure with a given knee flexion.

    Just enough body to drive the squat rep signal and view detection.
    """
    world = np.zeros((33, 3), dtype=np.float32)
    px = np.zeros((33, 2), dtype=np.float32)

    hip = np.array([0.0, 0.0, 0.0])
    thigh = shin = 0.42
    knee = hip + np.array([0.0, thigh, 0.0])
    swing = math.pi - math.radians(knee_deg)
    ankle = knee + np.array([math.sin(swing) * shin, math.cos(swing) * shin, 0.0])

    tilt = math.radians(torso_tilt_deg)
    shoulder = hip - np.array([math.sin(tilt) * 0.45, math.cos(tilt) * 0.45, 0.0])

    for is_left, sign in ((True, -1.0), (False, 1.0)):
        off = np.array([sign * 0.10, 0.0, 0.0])
        world[g.L_HIP if is_left else g.R_HIP] = hip + off
        world[g.L_KNEE if is_left else g.R_KNEE] = knee + off
        world[g.L_ANKLE if is_left else g.R_ANKLE] = ankle + off
        world[g.L_SHOULDER if is_left else g.R_SHOULDER] = shoulder + off

    # Shoulder separation in the image plane is what view detection reads.
    half = 100.0 if view == "front" else 10.0
    px[g.L_SHOULDER] = [320 - half, 200]
    px[g.R_SHOULDER] = [320 + half, 200]
    px[g.L_HIP] = [320 - half, 400]
    px[g.R_HIP] = [320 + half, 400]

    return PoseFrame(px=px, world=world, vis=np.ones(33), ok=True, t=0.0)


def test_view_detection() -> None:
    print("\nview detection")
    check("front-on skeleton reads as FRONT",
          detect_view(_skeleton(170, "front")) is View.FRONT)
    check("side-on skeleton reads as SIDE",
          detect_view(_skeleton(170, "side")) is View.SIDE)
    blank = PoseFrame(np.zeros((33, 2)), np.zeros((33, 3)), np.zeros(33), False, 0.0)
    check("no detection reads as ANY", detect_view(blank) is View.ANY)


def test_rep_signal() -> None:
    print("\nsquat rep signal")
    standing = SQUAT.rep_signal(_skeleton(175))
    parallel = SQUAT.rep_signal(_skeleton(95))
    deep = SQUAT.rep_signal(_skeleton(62))
    check("standing reads near 100", standing > 95, f"got {standing:.1f}")
    check("deep squat reads near 0", deep < 5, f"got {deep:.1f}")
    check("parallel is below bottom threshold",
          parallel < SQUAT.bottom_threshold, f"got {parallel:.1f}")
    check("signal is monotonic in knee angle", standing > parallel > deep)


# ------------------------------------------------------------- rep counting

def _ramp(start: float, end: float, steps: int) -> list[float]:
    return list(np.linspace(start, end, steps))


def _run(engine: Engine, knee_sequence: list[float], dt: float = 1 / 30) -> None:
    for i, knee in enumerate(knee_sequence):
        frame = _skeleton(knee)
        frame.t = i * dt
        engine.update(frame)


def test_rep_counting() -> None:
    print("\nrep counting")

    engine = Engine(SQUAT, SilentVoice())
    seq = _ramp(175, 175, 10)
    for _ in range(3):
        seq += (_ramp(175, 65, 20) + _ramp(65, 65, 4)
                + _ramp(65, 175, 20) + _ramp(175, 175, 6))
    _run(engine, seq)
    check("counts 3 full reps", engine.state.reps == 3, f"got {engine.state.reps}")
    check("no partials recorded", engine.state.partials == 0,
          f"got {engine.state.partials}")

    voice2 = SilentVoice()
    engine2 = Engine(SQUAT, voice2)
    seq2 = _ramp(175, 175, 10)
    for _ in range(2):
        seq2 += _ramp(175, 130, 15) + _ramp(130, 175, 15) + _ramp(175, 175, 6)
    _run(engine2, seq2)
    check("shallow reps do not count", engine2.state.reps == 0,
          f"got {engine2.state.reps}")
    check("shallow reps register as partials", engine2.state.partials == 2,
          f"got {engine2.state.partials}")
    check("partial cue was spoken",
          any(SQUAT.partial_cue in s for s in voice2.spoken))

    engine3 = Engine(SQUAT, SilentVoice())
    seq3 = _ramp(175, 175, 10)
    for _ in range(8):
        seq3 += _ramp(175, 168, 3) + _ramp(168, 175, 3)
    _run(engine3, seq3)
    check("lockout twitching counts nothing", engine3.state.reps == 0,
          f"got {engine3.state.reps}")


def test_summary() -> None:
    print("\nset summary")
    engine = Engine(SQUAT, SilentVoice())
    seq = _ramp(175, 175, 10)
    for _ in range(5):
        seq += (_ramp(175, 65, 20) + _ramp(65, 65, 4)
                + _ramp(65, 175, 20) + _ramp(175, 175, 6))
    _run(engine, seq)
    summary = engine.finish_set()
    check("summary rep count matches", summary["reps"] == 5, f"got {summary}")
    check("summary reports depth", summary["best_depth"] is not None)
    check("summary reports rep duration",
          summary["mean_rep_seconds"] is not None and summary["mean_rep_seconds"] > 0)
    check("exercise key present", summary["exercise"] == "squat")


def test_occluded_limb_handling() -> None:
    """Side-on, the far limb must not drag the signal.

    Builds a frame where the near leg reads a deep squat and the occluded far
    leg reports a bogus straight leg with low visibility. Averaging would land
    halfway; visibility weighting must stay close to the near leg.
    """
    print("\nocclusion handling")
    frame = _skeleton(70)                      # both legs at 70 deg
    # Corrupt the RIGHT leg to look straight, and mark it barely visible.
    frame.world[g.R_ANKLE] = frame.world[g.R_KNEE] + np.array([0.0, 0.42, 0.0])
    frame.vis[g.R_HIP] = frame.vis[g.R_KNEE] = frame.vis[g.R_ANKLE] = 0.25

    from trainer.exercises.squat import _knee_angle
    measured = _knee_angle(frame)
    check("occluded limb is ignored, not averaged", abs(measured - 70.0) < 3.0,
          f"got {measured:.1f}, expected ~70 (mean of both would be ~125)")

    # Both visible and disagreeing -> blend, not pick one arbitrarily.
    frame2 = _skeleton(70)
    frame2.world[g.R_ANKLE] = frame2.world[g.R_KNEE] + np.array([0.0, 0.42, 0.0])
    both = _knee_angle(frame2)
    check("two visible limbs are blended", 70.0 < both < 180.0,
          f"got {both:.1f}")

    # Nothing visible at all -> abstain rather than invent a number.
    frame3 = _skeleton(70)
    frame3.vis[:] = 0.1
    check("no visible limb returns nan", math.isnan(_knee_angle(frame3)))


def main() -> int:
    test_geometry()
    test_smoothing()
    test_view_detection()
    test_rep_signal()
    test_occluded_limb_handling()
    test_rep_counting()
    test_summary()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
