"""Pose backend abstraction.

Only this file knows which model produces the landmarks. Swapping MediaPipe
for an ONNX/CUDA RTMPose backend later means adding a second class here and
nothing else in the codebase changes.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .smoothing import OneEuroFilter

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"

# Filenames as published by Google; scripts/download_models.py fetches these.
MODEL_FILES = {
    "lite": "pose_landmarker_lite.task",
    "full": "pose_landmarker_full.task",
    "heavy": "pose_landmarker_heavy.task",
}


@dataclass
class PoseFrame:
    """One frame of tracked body position.

    px:      (33, 2) landmarks in pixel coordinates, for drawing and for any
             rule that reasons about the image plane.
    world:   (33, 3) landmarks in metres, origin at the hip midpoint. Camera
             independent, so angle thresholds hold at any distance.
    vis:     (33,) visibility scores in [0, 1].
    ok:      False when no person was detected this frame.
    """

    px: np.ndarray
    world: np.ndarray
    vis: np.ndarray
    ok: bool
    t: float

    def visible(self, *indices: int, threshold: float = 0.6) -> bool:
        return all(self.vis[i] >= threshold for i in indices)


class MediaPipeBackend:
    """MediaPipe Pose Landmarker in VIDEO mode.

    VIDEO mode (rather than IMAGE) lets the model use temporal context, which
    measurably reduces jitter and recovers faster from partial occlusion --
    e.g. when a dumbbell crosses in front of your hip.
    """

    def __init__(self, model: str = "full", smooth: bool = True) -> None:
        # Imported lazily so `--help` and the tests work without mediapipe.
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        path = MODEL_DIR / MODEL_FILES[model]
        if not path.exists():
            raise FileNotFoundError(
                f"Missing pose model: {path}\n"
                f"Run: python scripts/download_models.py"
            )

        self._vision = vision
        options = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(path)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.6,
            min_pose_presence_confidence=0.6,
            min_tracking_confidence=0.6,
            output_segmentation_masks=False,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)
        self._px_filter = OneEuroFilter(min_cutoff=1.5, beta=0.4) if smooth else None
        self._world_filter = OneEuroFilter(min_cutoff=1.2, beta=0.35) if smooth else None
        self._t0 = time.perf_counter()

    def __call__(self, bgr: np.ndarray) -> PoseFrame:
        import mediapipe as mp

        h, w = bgr.shape[:2]
        rgb = bgr[:, :, ::-1]
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        now = time.perf_counter() - self._t0
        result = self._landmarker.detect_for_video(image, int(now * 1000))

        if not result.pose_landmarks:
            return PoseFrame(
                px=np.zeros((33, 2)), world=np.zeros((33, 3)),
                vis=np.zeros(33), ok=False, t=now,
            )

        lms = result.pose_landmarks[0]
        wlms = result.pose_world_landmarks[0]
        px = np.array([[lm.x * w, lm.y * h] for lm in lms], dtype=np.float32)
        world = np.array([[lm.x, lm.y, lm.z] for lm in wlms], dtype=np.float32)
        vis = np.array([lm.visibility for lm in lms], dtype=np.float32)

        if self._px_filter is not None:
            px = self._px_filter(px, now)
            world = self._world_filter(world, now)

        return PoseFrame(px=px, world=world, vis=vis, ok=True, t=now)

    def close(self) -> None:
        self._landmarker.close()
