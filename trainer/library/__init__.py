"""The exercise library: every movement the app can program, in plain English.

Each `Move` ties together what the rest of the app needs:
  * the Asterisk demo video (`slug`) -- the descriptions there are Italian,
    so the instructions here are written fresh,
  * how it is loaded (`mode`, see equipment.py) and a sensible first weight,
  * which camera tracker counts its reps, and where to stand,
  * easier / harder / similar moves, so the app can offer a regression when
    something is too hard and a progression when it gets easy.

Adding a move is one entry in strength.py, bodyweight.py or mobility.py.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

GROUPS = {
    "chest": "Chest", "back": "Back", "shoulders": "Shoulders", "arms": "Arms",
    "legs": "Legs", "glutes": "Glutes & hamstrings", "core": "Core",
    "warmup": "Warm-up", "stretch": "Stretch", "mobility": "Mobility",
}

# Where to put yourself relative to the camera, by tracker view.
VIEW_TEXT = {
    "side": "Turn side-on to the camera, 2-3 m away, whole body in frame.",
    "front": "Face the camera, 2-3 m away, whole body in frame.",
    "": "",
}


@dataclass(frozen=True)
class Move:
    id: str
    name: str
    slug: str                       # Asterisk demo video slug; "" if none
    kind: str                       # strength | warmup | stretch | mobility
    group: str                      # key of GROUPS
    muscles: tuple[str, ...] = ()
    purpose: str = ""               # one line: why this is in your program
    mode: str = "bw"                # db1 | db2 | bb | bw
    needs: tuple[str, ...] = ()     # "bench", "table", "pullup_bar", "dumbbells"
    tracker: str | None = None      # trainer.exercises key that counts reps
    view: str = ""                  # side | front
    steps: tuple[str, ...] = ()
    cues: tuple[str, ...] = ()      # short, spoken during the intro
    mistakes: tuple[str, ...] = ()
    per_side: bool = False
    hold: bool = False              # timed hold rather than reps
    reps: tuple[int, int] | None = None  # own rep (or seconds) range; overrides the slot's
    start_kg: float | None = None   # first-session weight before any history
    increment: float = 0.025        # target load jump as a fraction
    rep_seconds: float = 3.0        # tempo, for session time estimates
    seconds: int = 0                # default duration for warm-up / stretch items
    reps_hint: str = ""             # e.g. "10 slow reps" for warm-up items
    easier: tuple[str, ...] = ()
    harder: tuple[str, ...] = ()
    similar: tuple[str, ...] = ()

    @property
    def weighted(self) -> bool:
        return self.mode != "bw"

    @property
    def view_text(self) -> str:
        return VIEW_TEXT.get(self.view, "")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["weighted"] = self.weighted
        d["view_text"] = self.view_text
        d["group_label"] = GROUPS.get(self.group, self.group)
        return d


LIBRARY: dict[str, Move] = {}


def register(*moves: Move) -> None:
    for m in moves:
        if m.id in LIBRARY:
            raise ValueError(f"duplicate move id {m.id!r}")
        LIBRARY[m.id] = m


def get(move_id: str) -> Move:
    try:
        return LIBRARY[move_id]
    except KeyError:
        raise KeyError(f"unknown move {move_id!r}") from None


def find(move_id: str) -> Move | None:
    return LIBRARY.get(move_id)


def available(move: Move, equipment: dict) -> bool:
    """False when the move needs kit you have told the app you lack.

    Anything loaded (mode other than bodyweight) needs the dumbbells, so a
    no-dumbbell place filters it out without every entry having to say so.
    """
    needs = (*move.needs, "dumbbells") if move.weighted else move.needs
    return all(equipment.get(n, True) for n in needs)


def options(move_id: str, equipment: dict | None = None) -> dict[str, list[Move]]:
    """Easier, harder and similar moves, filtered to kit you have."""
    m = get(move_id)
    eq = equipment or {}
    pick = lambda ids: [LIBRARY[i] for i in ids if i in LIBRARY and available(LIBRARY[i], eq)]
    # Similar is symmetric: if A lists B, B offers A too.
    similar = list(m.similar) + [o.id for o in LIBRARY.values()
                                 if m.id in o.similar and o.id not in m.similar]
    return {"easier": pick(m.easier), "harder": pick(m.harder), "similar": pick(similar)}


# Registration happens on import.
from . import mobility, strength, bodyweight  # noqa: E402,F401,I001
