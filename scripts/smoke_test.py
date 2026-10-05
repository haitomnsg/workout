"""End-to-end pipeline check that never opens the camera.

Verifies the model loads, VIDEO mode accepts monotonic timestamps, the
no-person path returns cleanly rather than throwing, and measures real
inference throughput on this machine.

    python scripts/smoke_test.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trainer.engine import Engine          # noqa: E402
from trainer.exercises import REGISTRY     # noqa: E402
from trainer.pose import MediaPipeBackend  # noqa: E402


class SilentVoice:
    enabled = False

    def say(self, *a, **k):
        return False

    def close(self):
        pass


def bench(model: str, frames: int = 40) -> float:
    backend = MediaPipeBackend(model=model)
    rng = np.random.default_rng(0)
    # Textured noise rather than flat black: a solid frame is an unrealistically
    # easy input and would overstate throughput.
    img = rng.integers(0, 255, size=(720, 1280, 3), dtype=np.uint8)

    backend(img)  # warm up: first call pays one-time graph setup
    start = time.perf_counter()
    last = None
    for _ in range(frames):
        last = backend(img)
    elapsed = time.perf_counter() - start
    backend.close()

    fps = frames / elapsed
    print(f"  {model:5s}  {fps:5.1f} fps  ({1000 * elapsed / frames:.1f} ms/frame)"
          f"  detected={last.ok}")
    return fps


def main() -> int:
    print("exercises registered:", ", ".join(sorted(REGISTRY)))

    print("\nno-person path")
    backend = MediaPipeBackend(model="lite")
    blank = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame = backend(blank)
    ok = (not frame.ok and frame.px.shape == (33, 2)
          and frame.world.shape == (33, 3) and frame.vis.shape == (33,))
    print(f"  returns empty PoseFrame without throwing: {ok}")
    backend.close()
    if not ok:
        return 1

    print("\nengine tolerates untracked frames")
    engine = Engine(REGISTRY["squat"], SilentVoice())
    for i in range(30):
        frame.t = i / 30
        engine.update(frame)
    print(f"  no crash, reps={engine.state.reps} (expected 0)")

    print("\nthroughput on this machine (1280x720)")
    bench("lite")
    full_fps = bench("full")
    try:
        bench("heavy")
    except FileNotFoundError:
        print("  heavy  not downloaded")

    print()
    if full_fps >= 24:
        print(f"full model runs at {full_fps:.0f} fps -- use --model full")
    else:
        print(f"full model is {full_fps:.0f} fps -- prefer --model lite for live use")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
