"""Fetch MediaPipe pose models into models/.

Run once after installing dependencies:
    python scripts/download_models.py
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

BASE = "https://storage.googleapis.com/mediapipe-models/pose_landmarker"
MODELS = {
    "lite": f"{BASE}/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
    "full": f"{BASE}/pose_landmarker_full/float16/1/pose_landmarker_full.task",
    "heavy": f"{BASE}/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task",
}

OUT = Path(__file__).resolve().parent.parent / "models"


def main(which: list[str]) -> int:
    OUT.mkdir(exist_ok=True)
    for name in which:
        url = MODELS[name]
        dest = OUT / url.rsplit("/", 1)[-1]
        if dest.exists():
            print(f"  already have {dest.name}")
            continue
        print(f"  downloading {dest.name} ...", end="", flush=True)
        urllib.request.urlretrieve(url, dest)
        print(f" {dest.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:] or ["lite", "full"]
    raise SystemExit(main(args))
