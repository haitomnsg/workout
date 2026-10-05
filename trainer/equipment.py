"""What your plates can actually load, and how to load it.

Three ways to use the same kit:

    db1  one dumbbell, every plate available to it   (goblet squat, one-arm row)
    db2  a matched pair                               (bench press, curls, lunges)
    bb   both rods joined by the connector            (overhead press, RDL)

Two physical constraints shape every number:

  * A rod is loaded symmetrically -- the same plates on each end (or, for the
    barbell, on each side of the connector).
  * A pair only has to MATCH IN WEIGHT, not in plates. One dumbbell can carry
    2+2 per end while the other carries 1.5+1.25+1.25 -- both 4 kg per end.
    Solving it that way finds noticeably more pair weights than splitting the
    plate pool in half, which is what the first version of this maths did.

Every weight the app recommends comes from these ladders, so you are never
told to lift something your plates cannot make.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product

MODES = ("db1", "db2", "bb", "bw")
MODE_LABEL = {
    "db1": "one dumbbell",
    "db2": "pair of dumbbells",
    "bb": "barbell",
    "bw": "bodyweight",
}

# Defaults match plan/program.md. Weigh the bare hardware once and enter it in
# Settings -- every number below shifts by exactly that much.
DEFAULT_PLATES = {2.0: 4, 1.5: 4, 1.25: 4}
DEFAULT_ROD = 1.3
DEFAULT_CONNECTOR = 1.5
DEFAULT_COLLAR = 0.2


@dataclass(frozen=True)
class Kit:
    plates: tuple[tuple[float, int], ...]    # (plate kg, how many), heaviest first
    rod: float = DEFAULT_ROD
    connector: float = DEFAULT_CONNECTOR
    collar: float = DEFAULT_COLLAR

    @classmethod
    def from_dict(cls, eq: dict | None) -> "Kit":
        eq = eq or {}
        raw = eq.get("plates") or DEFAULT_PLATES
        plates = tuple(sorted(((float(w), int(n)) for w, n in raw.items() if int(n) > 0),
                              reverse=True))
        return cls(
            plates=plates,
            rod=float(eq.get("rod_kg", DEFAULT_ROD)),
            connector=float(eq.get("connector_kg", DEFAULT_CONNECTOR)),
            collar=float(eq.get("collar_kg", DEFAULT_COLLAR)),
        )

    @property
    def dumbbell_handle(self) -> float:
        return round(self.rod + 2 * self.collar, 2)

    @property
    def barbell_bar(self) -> float:
        # Kept consistent with the original loading script: four collars.
        return round(2 * self.rod + self.connector + 4 * self.collar, 2)

    @property
    def total_plates(self) -> float:
        return round(sum(w * n for w, n in self.plates), 2)


DEFAULT_KIT = Kit.from_dict({})

# One end of a rod: a tuple of plate counts aligned with kit.plates.
End = tuple[int, ...]


def _end_sum(kit: Kit, end: End) -> float:
    return round(sum(w * c for (w, _), c in zip(kit.plates, end)), 3)


def _ends(kit: Kit, cap: tuple[int, ...]) -> list[End]:
    return [tuple(c) for c in product(*(range(m + 1) for m in cap))]


@dataclass(frozen=True)
class Loading:
    """How to build one achievable weight."""
    mode: str
    weight: float           # per dumbbell for db2, the dumbbell for db1, total for bb
    ends: tuple[End, ...]   # db1/bb: (one end,)   db2: (dumbbell A end, dumbbell B end)

    def plates_text(self, kit: Kit, end: End) -> str:
        parts = []
        for (w, _), c in zip(kit.plates, end):
            parts += [f"{w:g}"] * c
        return " + ".join(parts) if parts else "no plates"

    def describe(self, kit: Kit) -> str:
        if not any(sum(e) for e in self.ends):
            what = "Bare bar" if self.mode == "bb" else \
                   "Bare handles" if self.mode == "db2" else "Bare handle"
            return f"{what}, no plates ({self.weight:g} kg)"
        if self.mode == "db1":
            return (f"Each end: {self.plates_text(kit, self.ends[0])} kg "
                    f"(handle {kit.dumbbell_handle:g} kg)")
        if self.mode == "bb":
            return (f"Each side: {self.plates_text(kit, self.ends[0])} kg "
                    f"(bar {kit.barbell_bar:g} kg)")
        a, b = self.ends
        if a == b:
            return (f"Both dumbbells, each end: {self.plates_text(kit, a)} kg "
                    f"(handle {kit.dumbbell_handle:g} kg)")
        return (f"Dumbbell 1, each end: {self.plates_text(kit, a)} kg  |  "
                f"Dumbbell 2, each end: {self.plates_text(kit, b)} kg")


@lru_cache(maxsize=64)
def _solve(kit: Kit, mode: str) -> dict[float, Loading]:
    """Every achievable weight for a mode, mapped to its simplest loading."""
    out: dict[float, Loading] = {}
    counts = tuple(n for _, n in kit.plates)

    if mode in ("db1", "bb"):
        # Each end/side may use at most half of each plate size.
        base = kit.dumbbell_handle if mode == "db1" else kit.barbell_bar
        for end in _ends(kit, tuple(n // 2 for n in counts)):
            w = round(base + 2 * _end_sum(kit, end), 2)
            best = out.get(w)
            if best is None or sum(end) < sum(best.ends[0]):
                out[w] = Loading(mode, w, (end,))
        return out

    if mode == "db2":
        cap = tuple(n // 2 for n in counts)
        ends = _ends(kit, cap)
        by_sum: dict[float, list[End]] = {}
        for e in ends:
            by_sum.setdefault(_end_sum(kit, e), []).append(e)
        for s, group in by_sum.items():
            w = round(kit.dumbbell_handle + 2 * s, 2)
            choice: tuple[End, End] | None = None
            best_key: tuple[bool, int] | None = None
            for a in group:
                for b in group:
                    # Each dumbbell has two ends, so plate usage is 2*(a+b).
                    if any(2 * (x + y) > n for x, y, n in zip(a, b, counts)):
                        continue
                    # Prefer identical dumbbells (easier to load), then fewest plates.
                    key = (a != b, sum(a) + sum(b))
                    if best_key is None or key < best_key:
                        best_key, choice = key, (a, b)
            if choice is not None:
                out[w] = Loading(mode, w, choice)
        return out

    return out


def ladder(kit: Kit, mode: str) -> list[float]:
    """Sorted achievable weights. Empty for bodyweight."""
    return sorted(_solve(kit, mode))


def loading(kit: Kit, mode: str, weight: float) -> Loading | None:
    return _solve(kit, mode).get(round(weight, 2))


def describe_loading(kit: Kit, mode: str, weight: float | None) -> str:
    if mode == "bw" or weight is None:
        return ""
    ld = loading(kit, mode, weight)
    return ld.describe(kit) if ld else ""


def plates(kit: Kit, mode: str, weight: float | None) -> dict | None:
    """Plate lists per end, for drawing the loading diagram in the UI."""
    if mode == "bw" or weight is None:
        return None
    ld = loading(kit, mode, weight)
    if ld is None:
        return None

    def expand(end: End) -> list[float]:
        out: list[float] = []
        for (w, _), c in zip(kit.plates, end):
            out += [w] * c
        return out

    return {
        "mode": mode,
        "weight": weight,
        "base": kit.barbell_bar if mode == "bb" else kit.dumbbell_handle,
        "ends": [expand(e) for e in ld.ends],
    }


def nearest(kit: Kit, mode: str, target: float) -> float | None:
    steps = ladder(kit, mode)
    if not steps:
        return None
    return min(steps, key=lambda w: (abs(w - target), w))


def at_or_below(kit: Kit, mode: str, target: float) -> float | None:
    steps = ladder(kit, mode)
    if not steps:
        return None
    below = [w for w in steps if w <= target + 1e-9]
    return below[-1] if below else steps[0]


def step_up(kit: Kit, mode: str, weight: float, min_jump: float) -> float:
    """Smallest achievable weight at least `min_jump` heavier.

    Returns the input unchanged when the kit is already maxed out -- the
    caller detects that and switches to rep progression.
    """
    steps = ladder(kit, mode)
    for w in steps:
        if w >= weight + min_jump - 1e-9:
            return w
    return steps[-1] if steps and steps[-1] > weight else weight


def step_down(kit: Kit, mode: str, weight: float, fraction: float = 0.10) -> float:
    """Achievable weight roughly `fraction` lighter, always strictly lighter
    unless already at the bare handle."""
    steps = ladder(kit, mode)
    if not steps:
        return weight
    target = weight * (1 - fraction)
    below = [w for w in steps if w <= target + 1e-9]
    if below:
        return below[-1]
    lighter = [w for w in steps if w < weight - 1e-9]
    return lighter[-1] if lighter else steps[0]


def is_max(kit: Kit, mode: str, weight: float | None) -> bool:
    steps = ladder(kit, mode)
    return bool(steps) and weight is not None and weight >= steps[-1] - 1e-9


def format_weight(mode: str, weight: float | None) -> str:
    if mode == "bw" or weight is None:
        return "bodyweight"
    suffix = " each" if mode == "db2" else ""
    return f"{weight:g} kg{suffix}"
