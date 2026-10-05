"""Exercise registry: one tracker per movement family.

The library (trainer/library) maps each of its moves onto one of these keys,
so a hammer curl and a barbell curl share the curl tracker.
"""
from __future__ import annotations

from .arms import CURL, TRICEPS
from .base import Exercise
from .bench_press import BENCH_PRESS
from .bridge import BRIDGE
from .hanging import KNEE_RAISE, PULLUP
from .hinge import HINGE
from .lateral import LATERAL
from .lunge import LUNGE
from .press import PRESS
from .pushup import PIKE_PUSHUP, PUSHUP
from .row import ROW
from .squat import SQUAT

REGISTRY: dict[str, Exercise] = {
    ex.key: ex for ex in (SQUAT, BENCH_PRESS, ROW, PRESS, CURL, TRICEPS, LATERAL,
                          HINGE, LUNGE, BRIDGE, PUSHUP, PIKE_PUSHUP, PULLUP,
                          KNEE_RAISE)
}


def get(key: str) -> Exercise:
    if key not in REGISTRY:
        raise KeyError(
            f"Unknown exercise {key!r}. Available: {', '.join(sorted(REGISTRY))}"
        )
    return REGISTRY[key]
