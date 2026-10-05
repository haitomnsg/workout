"""Live rep tracking fed by landmarks from the browser.

Pose detection runs in the browser (MediaPipe's WebAssembly build), because
Windows Smart App Control blocks the native MediaPipe DLL. The browser posts
the 33 landmarks here every frame and this module does what the OpenCV loop
used to: One Euro smoothing, view detection, and the rep engine.

Everything downstream of `PoseFrame` is unchanged, so the engine, rules and
tests do not know or care where the landmarks came from.
"""
from __future__ import annotations

import threading
import time

import numpy as np

from .engine import Engine, detect_view
from .exercises import REGISTRY
from .exercises.base import View
from .pose import PoseFrame
from .smoothing import OneEuroFilter

STALE_AFTER = 1.5        # seconds without frames before the camera counts as off


class LiveTracker:
    def __init__(self, voice) -> None:
        self.voice = voice
        self.lock = threading.Lock()
        self.engine: Engine | None = None
        self.tracker: str | None = None
        self.want_view = View.ANY
        self._px_filter = OneEuroFilter(min_cutoff=1.5, beta=0.4)
        self._world_filter = OneEuroFilter(min_cutoff=1.2, beta=0.35)
        self._last_t: float | None = None
        self.last_frame_at = 0.0
        self.frame_ok = False
        self.view = View.ANY
        self.side_results: list[dict] = []

    # ---- control (called by the workout runner) --------------------------

    def configure(self, tracker: str | None, view: str = "") -> None:
        """Which movement the camera should expect next (for the position check)."""
        with self.lock:
            self.tracker = tracker if tracker in REGISTRY else None
            self.want_view = {"side": View.SIDE, "front": View.FRONT}.get(view, View.ANY)

    def begin(self, cooldown_cap: float | None = None) -> None:
        with self.lock:
            self.side_results = []
            self.engine = Engine(REGISTRY[self.tracker], self.voice, cooldown_cap) \
                if self.tracker else None

    def switch_side(self, cooldown_cap: float | None = None) -> None:
        """Bank the first side's count and start a fresh one for the second."""
        with self.lock:
            if self.engine is not None:
                self.side_results.append(self.engine.finish_set())
                self.engine = Engine(REGISTRY[self.tracker], self.voice, cooldown_cap)

    def end(self) -> dict | None:
        """Stop counting. Returns the set summary, or None if nothing tracked."""
        with self.lock:
            if self.engine is None:
                return None
            results = self.side_results + [self.engine.finish_set()]
            self.engine = None
            self.side_results = []
        if not any(r["reps"] or r["partials"] for r in results):
            return None
        reps = [r["reps"] for r in results]
        faults: dict[str, int] = {}
        for r in results:
            for k, v in r["faults"].items():
                faults[k] = faults.get(k, 0) + v
        return {
            "reps": min(reps),
            "reps_by_side": reps if len(reps) > 1 else None,
            "partials": sum(r["partials"] for r in results),
            "clean_reps": min(r["clean_reps"] for r in results),
            "mean_rep_seconds": results[-1]["mean_rep_seconds"],
            "faults": faults,
        }

    def cancel(self) -> None:
        with self.lock:
            self.engine = None
            self.side_results = []

    # ---- frames (called by the browser) ----------------------------------

    def update(self, payload: dict) -> dict:
        t = float(payload.get("t", time.perf_counter()))
        ok = bool(payload.get("ok"))
        with self.lock:
            self.last_frame_at = time.monotonic()
            # A gap means the camera restarted; stale filter state would drag
            # the first frames toward wherever you stood last time.
            if self._last_t is None or t - self._last_t > 0.5 or t < self._last_t:
                self._px_filter = OneEuroFilter(min_cutoff=1.5, beta=0.4)
                self._world_filter = OneEuroFilter(min_cutoff=1.2, beta=0.35)
            self._last_t = t

            if ok:
                try:
                    px = np.asarray(payload["px"], dtype=np.float32).reshape(33, 2)
                    world = np.asarray(payload["world"], dtype=np.float32).reshape(33, 3)
                    vis = np.asarray(payload["vis"], dtype=np.float32).reshape(33)
                except (KeyError, ValueError):
                    ok = False
            if ok:
                px = self._px_filter(px, t)
                world = self._world_filter(world, t)
                frame = PoseFrame(px=px, world=world, vis=vis, ok=True, t=t)
            else:
                frame = PoseFrame(px=np.zeros((33, 2)), world=np.zeros((33, 3)),
                                  vis=np.zeros(33), ok=False, t=t)

            self.frame_ok = frame.ok
            self.view = detect_view(frame)
            if self.engine is not None:
                self.engine.update(frame)
            return self._state()

    # ---- state -----------------------------------------------------------

    @property
    def camera_live(self) -> bool:
        return time.monotonic() - self.last_frame_at < STALE_AFTER

    def _state(self) -> dict:
        e = self.engine
        sig = None if e is None or np.isnan(e.signal) else round(float(e.signal), 1)
        return {
            "camera_live": self.camera_live,
            "person": self.frame_ok,
            "view": self.view.value,
            "want_view": self.want_view.value,
            "view_ok": self.want_view.matches(self.view) if self.frame_ok else False,
            "tracker": self.tracker,
            "counting": e is not None,
            "reps": e.state.reps if e else 0,
            "partials": e.state.partials if e else 0,
            "phase": e.state.phase.value if e else None,
            "signal": sig,
            "cues": list(e.active_cues) if e else [],
            "side": len(self.side_results) + 1,
            "side_reps": [r["reps"] for r in self.side_results],
        }

    def state(self) -> dict:
        with self.lock:
            return self._state()
