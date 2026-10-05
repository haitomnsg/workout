"""Spoken cues on a background thread.

Two rules make the difference between a coach and a nag:
  1. Speaking must never block the capture loop, or the video stutters every
     time it opens its mouth.
  2. Each distinct cue has its own cooldown. Without that, a rule that is
     violated for 40 frames says the same sentence 40 times.
"""
from __future__ import annotations

import queue
import threading
import time


class Voice:
    def __init__(self, enabled: bool = True, rate: int = 185,
                 default_cooldown: float = 6.0) -> None:
        self.enabled = enabled
        self.default_cooldown = default_cooldown
        self._last_said: dict[str, float] = {}
        self._q: queue.Queue[str | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._rate = rate
        if enabled:
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def _worker(self) -> None:
        try:
            import pyttsx3
        except ImportError:
            self.enabled = False
            return
        engine = pyttsx3.init()
        engine.setProperty("rate", self._rate)
        while True:
            text = self._q.get()
            if text is None:
                break
            try:
                engine.say(text)
                engine.runAndWait()
            except RuntimeError:
                # pyttsx3 occasionally trips over an interrupted loop; a
                # dropped cue is not worth killing the session over.
                pass

    def say(self, text: str, key: str | None = None,
            cooldown: float | None = None, force: bool = False) -> bool:
        """Queue a cue. Returns True if it was actually spoken.

        `key` groups cues for cooldown purposes -- pass the rule id so that
        "knees caving" and "go deeper" have independent timers.
        """
        if not self.enabled:
            return False
        key = key or text
        cd = self.default_cooldown if cooldown is None else cooldown
        now = time.monotonic()
        if not force and now - self._last_said.get(key, -1e9) < cd:
            return False
        # Never let a backlog build up; stale cues are worse than no cues.
        # A forced announcement ("Set two, go") clears the backlog instead of
        # being dropped behind a queue of stale rep counts.
        if self._q.qsize() > 2:
            if not force:
                return False
            while True:
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    break
        self._last_said[key] = now
        self._q.put(text)
        return True

    def set_enabled(self, on: bool) -> None:
        """Mute or unmute; starts the speech thread if it never ran."""
        self.enabled = on
        if on and self._thread is None:
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def reset_cooldowns(self) -> None:
        self._last_said.clear()

    def close(self) -> None:
        if self._thread is not None:
            self._q.put(None)
