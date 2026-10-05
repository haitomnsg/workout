"""One Euro filter for landmark streams.

Raw pose landmarks jitter by a few pixels every frame even when you hold
perfectly still. Feeding that straight into a threshold check produces
false "bad form" alerts many times per second. The One Euro filter adapts
its cutoff to speed: heavy smoothing when a joint is slow (removing jitter),
light smoothing when it moves fast (preserving responsiveness).

Reference: Casiez et al., "1e Filter" (CHI 2012).
"""
from __future__ import annotations

import math

import numpy as np


class _LowPass:
    def __init__(self) -> None:
        self.prev: np.ndarray | None = None

    def __call__(self, x: np.ndarray, alpha: float) -> np.ndarray:
        if self.prev is None:
            self.prev = x
        else:
            self.prev = alpha * x + (1.0 - alpha) * self.prev
        return self.prev

    def reset(self) -> None:
        self.prev = None


class OneEuroFilter:
    """Smooths an array of landmarks of fixed shape.

    min_cutoff: lower = smoother when still, but more lag.
    beta:       higher = more responsive during fast movement.
    """

    def __init__(self, min_cutoff: float = 1.2, beta: float = 0.35,
                 d_cutoff: float = 1.0) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x = _LowPass()
        self._dx = _LowPass()
        self._prev_x: np.ndarray | None = None
        self._prev_t: float | None = None

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x: np.ndarray, t: float) -> np.ndarray:
        if self._prev_t is None:
            self._prev_t, self._prev_x = t, x
            self._x(x, 1.0)
            return x

        dt = t - self._prev_t
        if dt <= 0:
            dt = 1.0 / 30.0
        self._prev_t = t

        dx = (x - self._prev_x) / dt
        self._prev_x = x
        edx = self._dx(dx, self._alpha(self.d_cutoff, dt))

        speed = np.linalg.norm(edx, axis=-1, keepdims=True)
        cutoff = self.min_cutoff + self.beta * speed
        # Per-landmark alpha, broadcast back over the coordinate axis.
        tau = 1.0 / (2.0 * math.pi * cutoff)
        alpha = 1.0 / (1.0 + tau / dt)
        return self._x(x, alpha)

    def reset(self) -> None:
        self._x.reset()
        self._dx.reset()
        self._prev_x = None
        self._prev_t = None


class Hysteresis:
    """Debounces a boolean signal so it must hold for N frames to flip.

    Stops a rule flickering between violated/clean on borderline reps, which
    is what makes a form coach feel nagging rather than helpful.
    """

    def __init__(self, on_frames: int = 4, off_frames: int = 6) -> None:
        self.on_frames = on_frames
        self.off_frames = off_frames
        self._state = False
        self._count = 0

    def update(self, raw: bool) -> bool:
        if raw == self._state:
            self._count = 0
        else:
            self._count += 1
            needed = self.on_frames if raw else self.off_frames
            if self._count >= needed:
                self._state = raw
                self._count = 0
        return self._state

    @property
    def state(self) -> bool:
        return self._state

    def reset(self) -> None:
        self._state = False
        self._count = 0
