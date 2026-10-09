"""When to add weight, how much, and when to back off.

The method is double progression, steered by how each set felt:

    Easy    4+ reps left in the tank
    Good    2-3 left            <- where most working sets should land
    Hard    1 left
    Failed  could not finish, or form broke

Between sessions:
  * every set at the top of the rep range, none Hard/Failed -> add the
    smallest sensible weight step (two steps if everything was Easy)
  * inside the range -> same weight, beat last time by a rep
  * below the range -> hold; well below or repeated failures -> drop ~10%
  * the same weight three sessions running without more reps -> deload 10%
    and build back up (the classic stall fix)

Two things specific to your kit:
  * Some weight steps are big (a pair of dumbbells jumps 5.7 -> 7.2 kg, +26%).
    Before a big jump the rep target is stretched so you arrive strong enough
    to make it, instead of failing the heavier weight.
  * When the plates max out on a lift, progression continues with reps and a
    slower lowering phase, and the app says it is time for more plates.

Within a session, `adjust_next_set` reacts to each rated set, so a bad
starting guess is fixed by set two rather than next week.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from . import equipment as eq
from .library import Move

RATING_RIR = {"easy": 4.0, "good": 2.5, "hard": 1.0, "failed": 0.0}
RATING_LABEL = {"easy": "Easy", "good": "Good", "hard": "Hard", "failed": "Failed"}

MAX_REPS = 20            # past this, more reps stop being strength work
MAX_BW_REPS = 25         # bodyweight moves with no harder variation left
HOLD_STEP = 5            # seconds added to a hold when it was comfortable
MAX_HOLD = 60


@dataclass
class Target:
    move: str
    weight: float | None
    lo: int
    hi: int                 # effective top of the range this session
    goal: int               # reps (or seconds) to aim for on each set
    status: str             # new | up | reps | hold | down | deload | maxed | graduate | hold_up
    reason: str
    loading: str = ""
    last: str = ""          # "5.7 kg x 12, 11, 10"
    graduate_to: str | None = None
    hold: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def min_jump(move: Move, weight: float) -> float:
    floor = 1.0 if move.mode == "bb" else 0.5
    return max(floor, weight * move.increment)


def _next_up(kit: eq.Kit, move: Move, weight: float, steps: int = 1) -> float:
    w = weight
    for _ in range(steps):
        w = eq.step_up(kit, move.mode, w, min_jump(move, w))
    return w


def _effective_hi(kit: eq.Kit, move: Move, weight: float | None, hi: int) -> int:
    """Stretch the rep target when the next plate step is a big jump."""
    if not move.weighted or weight is None:
        return hi
    nxt = _next_up(kit, move, weight)
    if nxt <= weight:
        return hi          # maxed; handled separately
    jump = (nxt - weight) / weight
    if jump > 0.30:
        return min(hi + 5, MAX_REPS)
    if jump > 0.15:
        return min(hi + 3, MAX_REPS)
    return hi


def _fmt_last(sets: list[dict], move: Move) -> str:
    if not sets:
        return ""
    if move.hold:
        return " / ".join(f"{s.get('seconds') or s.get('reps', 0)}s" for s in sets)
    reps = ", ".join(str(s.get("reps", 0)) for s in sets)
    w = sets[-1].get("weight_kg")
    if move.weighted and w:
        return f"{eq.format_weight(move.mode, w)} x {reps}"
    return f"{reps} reps"


def _working_weight(sets: list[dict]) -> float | None:
    ws = [s.get("weight_kg") for s in sets if s.get("weight_kg")]
    return ws[-1] if ws else None


def starting_weight(kit: eq.Kit, move: Move) -> float | None:
    if not move.weighted:
        return None
    return eq.nearest(kit, move.mode, move.start_kg or 0.0)


def recommend(move: Move, lo: int, hi: int, history: list[list[dict]],
              kit: eq.Kit, harder: tuple[str, ...] | None = None) -> Target:
    """Next session's target for one move, from its past working sessions.

    `harder` is the harder variations you can actually do where you are
    training (the move's own list, filtered to the kit at hand). With none
    left, a bodyweight move keeps progressing by reps instead.
    """
    harder = move.harder if harder is None else harder
    if move.hold:
        return _recommend_hold(move, lo, hi, history, harder)

    if not history:
        w = starting_weight(kit, move)
        reason = ("First time. This is a starting estimate — do set 1, rate it "
                  "honestly, and the app will adjust the next set.") if move.weighted else \
                 ("First time. Do clean reps and stop with about 2 left in the tank.")
        return Target(move.id, w, lo, _effective_hi(kit, move, w, hi), lo, "new", reason,
                      eq.describe_loading(kit, move.mode, w))

    last = history[-1]
    w = _working_weight(last) if move.weighted else None
    prefix = ""
    if move.weighted and w is None:
        w = starting_weight(kit, move)
    elif move.weighted and w not in eq.ladder(kit, move.mode):
        # Logged before the kit maths existed, or the hardware weights changed:
        # snap to the closest weight the plates can actually make.
        logged, w = w, eq.nearest(kit, move.mode, w)
        prefix = f"Your plates make {w:g} kg, the closest to the {logged:g} kg you logged. "
    reps = [int(s.get("reps") or 0) for s in last]
    ratings = [s.get("rating") for s in last]
    hi_eff = _effective_hi(kit, move, w, hi)
    last_txt = _fmt_last(last, move)

    failed = sum(1 for r in ratings if r == "failed")
    below = [r for r in reps if r < lo]
    all_top = bool(reps) and all(r >= hi_eff for r in reps)
    hard = any(r in ("hard", "failed") for r in ratings)
    all_easy = bool(ratings) and all(r == "easy" for r in ratings)

    def T(weight, goal, status, reason, graduate=None, hi_out=hi_eff):
        return Target(move.id, weight, lo, hi_out, goal, status, prefix + reason,
                      eq.describe_loading(kit, move.mode, weight), last_txt, graduate)

    # ---- bodyweight moves: reps, then a harder variation -------------------
    if not move.weighted:
        cap = hi if harder else MAX_BW_REPS
        if all_top and not hard and harder:
            return T(None, hi, "graduate",
                     f"You hit {hi}+ on every set. Ready for a harder variation — "
                     f"switch when you are, or keep adding reps here.",
                     graduate=harder[0])
        if below and (failed or max(reps) < lo - 2):
            easier = f" If it stays out of reach, switch to the easier variation." \
                if move.easier else ""
            return T(None, lo, "hold", f"Aim for at least {lo} clean reps per set.{easier}")
        goal = min(max(lo, min(reps) + 1), max(cap, hi))
        hi_out = hi if harder else max(hi, min(MAX_BW_REPS, max(reps) + 1))
        return T(None, goal, "reps", f"Beat last time: aim for {goal} reps per set.",
                 hi_out=hi_out)

    # ---- weighted moves ------------------------------------------------------
    if _stalled(history, w):
        down = eq.step_down(kit, move.mode, w, 0.10)
        return T(down, lo, "deload",
                 f"Stuck at {w:g} kg for three sessions. Drop to {down:g} kg and build "
                 f"back up — you will pass your old best within a few weeks.")

    if all_top and not failed:
        steps = 1
        if all_easy:
            # Everything felt easy: take a second step, unless that would be
            # a reckless jump (some plate steps are already large).
            two = _next_up(kit, move, w, 2)
            if (two - w) / w <= 0.15:
                steps = 2
        up = _next_up(kit, move, w, steps)
        if up <= w:
            goal = min(max(reps) + 1, MAX_REPS)
            return T(w, goal, "maxed",
                     f"Your plates max out at {w:g} kg for this lift. Keep adding reps "
                     f"(up to {MAX_REPS}) and lower each rep over 3 seconds. Time to "
                     f"think about buying more plates.", hi_out=MAX_REPS)
        why = "Every set felt easy — jumping two steps." if steps == 2 else \
              f"You hit {hi_eff}+ reps on every set."
        return T(up, lo, "up", f"{why} Up to {eq.format_weight(move.mode, up)} — "
                               f"aim for {lo}+ reps.", hi_out=_effective_hi(kit, move, up, hi))

    if below:
        if failed >= 2 or min(reps) < lo - 2:
            down = eq.step_down(kit, move.mode, w, 0.10)
            if down < w:
                return T(down, lo, "down",
                         f"Last time was too heavy ({last_txt}). Drop to "
                         f"{eq.format_weight(move.mode, down)} so every set lands in "
                         f"the {lo}-{hi} range.", hi_out=_effective_hi(kit, move, down, hi))
        return T(w, lo, "hold", f"Same weight. Goal: at least {lo} reps on every set.")

    goal = min(hi_eff, max(lo, min(reps) + 1))
    msg = f"Same weight — beat last time ({last_txt}): aim for {goal}+ reps per set."
    if hi_eff > hi:
        nxt = _next_up(kit, move, w)
        msg += (f" The next weight up ({nxt:g} kg) is a big jump, so build to "
                f"{hi_eff} reps first.")
    if all_top and failed:
        msg = f"Top of the range but a set failed — repeat {w:g} kg and own it."
    return T(w, goal, "reps" if not (all_top and failed) else "hold_up", msg)


def _stalled(history: list[list[dict]], w: float | None) -> bool:
    """Three sessions at the same weight with no gain in total reps, at least
    one of them falling below the bottom of the range."""
    if w is None or len(history) < 3:
        return False
    recent = history[-3:]
    if any(_working_weight(s) != w for s in recent):
        return False
    totals = [sum(int(x.get("reps") or 0) for x in s) for s in recent]
    struggled = any(x.get("rating") == "failed" for s in recent for x in s)
    return totals[2] <= totals[0] and struggled


def _recommend_hold(move: Move, lo: int, hi: int, history: list[list[dict]],
                    harder: tuple[str, ...]) -> Target:
    if not history:
        return Target(move.id, None, lo, hi, lo, "new",
                      f"First time. Hold {lo} seconds with perfect form.", hold=True)
    last = history[-1]
    secs = [int(s.get("seconds") or s.get("reps") or 0) for s in last]
    ratings = [s.get("rating") for s in last]
    last_txt = _fmt_last(last, move)
    if any(r == "failed" for r in ratings) or min(secs) < lo:
        goal = max(lo, min(secs))
        return Target(move.id, None, lo, hi, goal, "hold",
                      f"Hold {goal} seconds on every set before adding time.",
                      last=last_txt, hold=True)
    top = max(hi, MAX_HOLD if not harder else hi)
    goal = min(min(secs) + HOLD_STEP, top)
    if min(secs) >= hi and harder and not any(r == "hard" for r in ratings):
        return Target(move.id, None, lo, hi, hi, "graduate",
                      f"{hi} seconds is comfortable. Ready for a harder variation.",
                      last=last_txt, graduate_to=harder[0], hold=True)
    return Target(move.id, None, lo, max(hi, goal), goal, "reps",
                  f"Add {HOLD_STEP} seconds: hold {goal}s.", last=last_txt, hold=True)


# ------------------------------------------------------------ in-session

def adjust_next_set(move: Move, lo: int, hi: int, weight: float | None, reps: int,
                    rating: str | None, kit: eq.Kit) -> dict | None:
    """React to a just-rated set. Returns {"weight", "message"} or None."""
    if move.hold:
        return None
    if not move.weighted or weight is None:
        if rating == "failed" or reps < lo - 2:
            hint = " Tap Easier to switch variation." if move.easier else ""
            return {"weight": None, "message": f"Tough set. Rest fully and aim for {lo}.{hint}"}
        return None

    up1 = _next_up(kit, move, weight)
    jump = (up1 - weight) / weight if up1 > weight else 0.0
    hi_eff = _effective_hi(kit, move, weight, hi)

    if rating == "easy" and reps >= hi:
        if up1 <= weight:
            return {"weight": weight, "message": "That is the heaviest your plates go — "
                                                 "keep the weight and add reps."}
        if hi_eff > hi and reps < hi_eff:
            return {"weight": weight,
                    "message": f"The next step ({up1:g} kg) is a big jump. Stay here and "
                               f"push toward {hi_eff} reps first."}
        steps = 2 if reps >= hi + 4 and jump <= 0.10 else 1
        new = _next_up(kit, move, weight, steps)
        return {"weight": new, "message": f"Too light — go up to "
                                          f"{eq.format_weight(move.mode, new)} for the next set."}

    if rating == "failed" or reps < lo - 1:
        down = eq.step_down(kit, move.mode, weight, 0.10)
        if down < weight:
            return {"weight": down,
                    "message": f"Too heavy — drop to {eq.format_weight(move.mode, down)} "
                               f"so you stay in the {lo}-{hi} range."}
        return {"weight": weight, "message": "Already at the lightest setting — focus on "
                                             "clean reps, even if fewer."}

    if rating == "hard" and reps >= lo:
        return {"weight": weight, "message": "Good, hard set. Same weight — it is normal "
                                             "to lose a rep or two on later sets."}
    return {"weight": weight, "message": f"Stay at {eq.format_weight(move.mode, weight)}."}


# ------------------------------------------------------------ ramp-up sets

RAMP_TRACKERS = {"squat", "bench", "row", "press", "hinge", "lunge", "bridge"}


def warmup_sets(kit: eq.Kit, move: Move, weight: float | None) -> list[dict]:
    """Lighter sets before the first heavy lift: ~50% x 8, then ~75% x 4."""
    if not move.weighted or weight is None or move.tracker not in RAMP_TRACKERS:
        return []
    out: list[dict] = []
    for frac, reps in ((0.5, 8), (0.75, 4)):
        w = eq.at_or_below(kit, move.mode, weight * frac)
        if w is None or w >= weight or any(s["weight"] == w for s in out):
            continue
        out.append({"weight": w, "reps": reps})
    return out


def e1rm(weight: float | None, reps: int) -> float | None:
    """Epley estimate -- only for trend lines, never shown as a real max."""
    if not weight or reps <= 0:
        return None
    return round(weight * (1 + min(reps, 15) / 30.0), 2)
