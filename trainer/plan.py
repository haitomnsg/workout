"""The training program, as data, and the builder that turns it into today's
session.

Five training days a week, Sunday to Thursday by default:

    Sun  Upper A     chest, back, shoulders (horizontal focus)
    Mon  Lower A     squat and hinge
    Tue  Upper B     shoulders, back, chest (vertical focus)
    Wed  Lower B     single-leg strength
    Thu  Arms, Shoulders & Core   (lighter)
    Fri  Rest        Mobility A: hips and legs
    Sat  Rest        Mobility B: spine and shoulders

Upper and lower alternate, so no muscle is trained hard two days running,
and every muscle gets about two sessions a week.

Cycle: week 1 is a learning week (2 sets, lighter), weeks 2-7 build, week 8
deloads (one set fewer, ~10% lighter), then it repeats.

`Slot.key` is stable: if you swap an exercise and keep the swap, the profile
remembers it against the slot, not the day.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from . import equipment as eq
from . import progression
from .library import LIBRARY, Move, available, get
from .profile import WEEKDAYS, kit as profile_kit, week_start, weekday_key
from .session import work_sessions

CYCLE_WEEKS = 8


@dataclass(frozen=True)
class Slot:
    key: str
    move: str
    sets: int
    reps: tuple[int, int]        # rep range, or seconds range for holds
    rest: int                    # seconds between sets
    ramp: bool = False           # lighter ramp-up sets first


@dataclass(frozen=True)
class Day:
    key: str
    title: str
    focus: str
    kind: str                                    # workout | mobility
    warmup: tuple[str, ...] = ()
    slots: tuple[Slot, ...] = ()
    cooldown: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


UPPER_A = Day(
    "upper_a", "Upper A", "Chest, back & shoulders", "workout",
    warmup=("march", "arm_circles", "wrist_circles", "cat_cow", "thoracic_rotation",
            "prone_y_raise", "warmup_pushup"),
    slots=(
        Slot("ua.press", "db_bench_press", 3, (8, 12), 120, ramp=True),
        Slot("ua.row", "db_bent_row", 3, (8, 12), 90),
        Slot("ua.ohp", "bb_ohp", 3, (6, 10), 120, ramp=True),
        Slot("ua.pull", "pullup_negative", 3, (3, 5), 120),
        Slot("ua.delts", "lateral_raise", 3, (12, 15), 60),
    ),
    cooldown=("chest_stretch", "lat_stretch", "cross_body_shoulder", "triceps_stretch",
              "breathing"),
)

LOWER_A = Day(
    "lower_a", "Lower A", "Squat & hinge", "workout",
    warmup=("march", "leg_swings", "side_leg_swings", "hip_circles", "warmup_squat",
            "warmup_bridge", "worlds_greatest"),
    slots=(
        Slot("la.squat", "goblet_squat", 3, (8, 12), 120, ramp=True),
        Slot("la.hinge", "bb_rdl", 3, (8, 12), 120, ramp=True),
        Slot("la.lunge", "reverse_lunge", 3, (8, 10), 90),
        Slot("la.glute", "db_hip_thrust", 3, (10, 15), 90),
        Slot("la.calf", "calf_raise", 2, (12, 20), 45),
        Slot("la.core", "plank", 3, (30, 60), 45),
    ),
    cooldown=("quad_stretch", "hamstring_stretch", "hip_flexor_stretch", "figure_four",
              "child_pose"),
)

UPPER_B = Day(
    "upper_b", "Upper B", "Shoulders, back & chest", "workout",
    warmup=("jumping_jacks", "arm_circles", "wrist_circles", "cat_cow",
            "thoracic_rotation", "inchworm"),
    slots=(
        Slot("ub.ohp", "db_seated_press", 3, (8, 12), 90, ramp=True),
        Slot("ub.row", "one_arm_row", 3, (10, 12), 60),
        Slot("ub.push", "pushup", 3, (8, 15), 90),
        Slot("ub.pull", "pullup_negative", 3, (3, 5), 120),
        Slot("ub.rear", "rear_delt_fly", 3, (12, 15), 60),
        Slot("ub.fly", "db_floor_fly", 2, (10, 15), 60),
    ),
    cooldown=("chest_stretch", "cross_body_shoulder", "lat_stretch", "neck_stretch",
              "breathing"),
)

LOWER_B = Day(
    "lower_b", "Lower B", "Single-leg strength", "workout",
    warmup=("march", "leg_swings", "hip_circles", "warmup_lunge", "warmup_bridge",
            "worlds_greatest"),
    slots=(
        Slot("lb.split", "bss", 3, (8, 12), 90, ramp=True),
        Slot("lb.hinge", "sl_rdl", 3, (8, 12), 75),
        Slot("lb.step", "step_up", 2, (8, 12), 60),
        Slot("lb.glute", "sl_hip_thrust", 3, (10, 15), 60),
        Slot("lb.calf", "calf_raise", 2, (12, 20), 45),
        Slot("lb.core", "hanging_knee_raise", 3, (8, 12), 60),
    ),
    cooldown=("quad_stretch", "hamstring_stretch", "hip_flexor_stretch", "butterfly",
              "child_pose"),
)

ARMS_CORE = Day(
    "arms_core", "Arms, Shoulders & Core", "Lighter day: arms, delts, abs", "workout",
    warmup=("jumping_jacks", "arm_circles", "wrist_circles", "inchworm", "bird_dog",
            "cat_cow"),
    slots=(
        Slot("ac.curl", "db_curl", 3, (10, 12), 60),
        Slot("ac.tri", "oh_triceps_ext", 3, (10, 12), 60),
        Slot("ac.curl2", "hammer_curl", 3, (10, 12), 60),
        Slot("ac.tri2", "bench_dip", 3, (8, 15), 60),
        Slot("ac.delts", "lateral_raise", 3, (12, 15), 60),
        Slot("ac.core", "dead_bug", 3, (8, 12), 45),
        Slot("ac.core2", "side_plank", 2, (20, 40), 45),
    ),
    cooldown=("triceps_stretch", "wrist_stretch", "chest_stretch", "cobra", "lying_twist",
              "breathing"),
)

MOBILITY_A = Day(
    "mobility_a", "Mobility A", "Hips & legs — recovery", "mobility",
    warmup=("cat_cow", "worlds_greatest", "ninety_ninety", "squat_hold",
            "hip_flexor_stretch", "pigeon", "hamstring_stretch", "down_dog", "butterfly",
            "warmup_bridge", "ankle_circles", "lying_twist", "child_pose", "breathing"),
    notes=("Rest days are when muscle is actually built. Eat the same as a training day.",
           "Optional: a 20-30 minute easy walk.", "Sleep 7-9 hours."),
)

MOBILITY_B = Day(
    "mobility_b", "Mobility B", "Spine & shoulders — recovery", "mobility",
    warmup=("cat_cow", "thread_needle", "open_book", "thoracic_rotation", "arm_circles",
            "prone_y_raise", "chest_stretch", "lat_stretch", "cross_body_shoulder",
            "hang_decompress", "cobra", "child_pose", "neck_stretch", "breathing"),
    notes=("Rest days are when muscle is actually built. Eat the same as a training day.",
           "Optional: a 20-30 minute easy walk.", "Sleep 7-9 hours."),
)

TRAINING_DAYS = (UPPER_A, LOWER_A, UPPER_B, LOWER_B, ARMS_CORE)
REST_DAYS = (MOBILITY_A, MOBILITY_B)
DAYS: dict[str, Day] = {d.key: d for d in (*TRAINING_DAYS, *REST_DAYS)}
SLOTS: dict[str, Slot] = {s.key: s for d in TRAINING_DAYS for s in d.slots}


# ------------------------------------------------------------------ schedule

def week_map(profile: dict) -> dict[str, Day]:
    """Weekday key -> Day, for a Sunday-first week."""
    order = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
    train = [d for d in order if d in profile.get("training_days", [])]
    out: dict[str, Day] = {}
    for i, wd in enumerate(train):
        out[wd] = TRAINING_DAYS[i] if i < len(TRAINING_DAYS) else REST_DAYS[i % 2]
    rest = [d for d in order if d not in out]
    for i, wd in enumerate(rest):
        out[wd] = REST_DAYS[i % 2]
    return out


def day_for(profile: dict, day: date) -> Day:
    return week_map(profile)[weekday_key(day)]


def program_week(profile: dict, today: date) -> int:
    start = profile.get("program_start")
    if not start:
        return 1
    return max(1, (today - date.fromisoformat(start)).days // 7 + 1)


def phase_for(week: int) -> str:
    if week == 1:
        return "intro"
    if (week - 1) % CYCLE_WEEKS + 1 == CYCLE_WEEKS:
        return "deload"
    return "build"


PHASE_TEXT = {
    "intro": "Learning week: 2 sets per exercise and lighter weights. Focus on form.",
    "build": "Build phase: beat last week by a rep or a little weight.",
    "deload": "Deload week: one set fewer and about 10% lighter. Let your body catch up.",
}


# ---------------------------------------------------------------- building

def resolve_move(slot: Slot, profile: dict) -> Move:
    """The move for a slot: your kept swap if any, else the default, falling
    back to an alternative when the kit for it is missing."""
    equip = profile.get("equipment", {})
    move = LIBRARY.get(profile.get("swaps", {}).get(slot.key, slot.move)) or get(slot.move)
    if available(move, equip):
        return move
    for alt in (*move.easier, *move.similar, *move.harder):
        m = LIBRARY.get(alt)
        if m and available(m, equip):
            return m
    return move


def timed_item(move_id: str) -> dict:
    m = get(move_id)
    return {"move": m.id, "seconds": m.seconds or 30, "per_side": m.per_side}


def build_exercise(slot: Slot, move: Move, profile: dict, phase: str,
                   sets_log: list[dict] | None = None) -> dict:
    kit = profile_kit(profile)
    lo, hi = slot.reps
    history = work_sessions(move.id, sets_log)
    target = progression.recommend(move, lo, hi, history, kit)

    n_sets = slot.sets
    weight = target.weight
    if phase == "intro":
        n_sets = min(n_sets, 2)
    elif phase == "deload":
        n_sets = max(2, n_sets - 1)
        if weight is not None:
            weight = eq.step_down(kit, move.mode, weight, 0.10)
        target.reason = "Deload week: lighter and one set fewer. " + target.reason

    sets = []
    if slot.ramp:
        for w in progression.warmup_sets(kit, move, weight):
            sets.append({"kind": "warmup", "weight": w["weight"], "lo": w["reps"],
                         "hi": w["reps"], "goal": w["reps"]})
    for _ in range(n_sets):
        sets.append({"kind": "work", "weight": weight, "lo": target.lo, "hi": target.hi,
                     "goal": target.goal})

    t = target.to_dict()
    t["weight"] = weight
    t["loading"] = eq.describe_loading(kit, move.mode, weight)
    return {
        "type": "exercise",
        "slot": slot.key,
        "default_move": slot.move,
        "move": move.id,
        "rest": slot.rest,
        "sets": sets,
        "target": t,
        "first_time": not history,
    }


def build_session(day: Day, profile: dict, today: date,
                  sets_log: list[dict] | None = None) -> dict:
    week = program_week(profile, today)
    phase = phase_for(week)
    blocks: list[dict] = []
    if day.kind == "mobility":
        blocks.append({"type": "mobility", "title": day.title,
                       "items": [timed_item(m) for m in day.warmup
                                 if available(get(m), profile.get("equipment", {}))]})
    else:
        blocks.append({"type": "warmup", "title": "Warm-up",
                       "items": [timed_item(m) for m in day.warmup]})
        for slot in day.slots:
            blocks.append(build_exercise(slot, resolve_move(slot, profile), profile,
                                         phase, sets_log))
        blocks.append({"type": "cooldown", "title": "Cool-down",
                       "items": [timed_item(m) for m in day.cooldown]})
    session = {
        "day_key": day.key,
        "title": day.title,
        "focus": day.focus,
        "kind": day.kind,
        "date": today.isoformat(),
        "week": week,
        "phase": phase,
        "phase_text": PHASE_TEXT[phase],
        "notes": list(day.notes),
        "blocks": blocks,
    }
    session["estimate_min"] = round(estimate_seconds(session) / 60)
    return session


# ---------------------------------------------------------------- timing

TRANSITION = 6          # seconds between timed items
EXERCISE_CHANGE = 75    # reading the intro, loading plates, getting set up
SET_SETUP = 15


def estimate_seconds(session: dict) -> int:
    total = 0
    for b in session["blocks"]:
        if b["type"] in ("warmup", "cooldown", "mobility"):
            for it in b["items"]:
                total += it["seconds"] * (2 if it["per_side"] else 1) + TRANSITION
            continue
        m = get(b["move"])
        total += EXERCISE_CHANGE
        sides = 2 if m.per_side else 1
        for i, s in enumerate(b["sets"]):
            work = s["goal"] if m.hold else s["goal"] * m.rep_seconds
            total += work * sides + SET_SETUP + (8 if sides == 2 else 0)
            last = i == len(b["sets"]) - 1
            if not last:
                total += 45 if s["kind"] == "warmup" else b["rest"]
    return int(total)


# --------------------------------------------------------------- the week

def week_overview(profile: dict, today: date, sessions_log: list[dict]) -> list[dict]:
    """Sunday-to-Saturday strip with what was planned and what happened."""
    start = week_start(today)
    # Days before your first workout are not "missed" -- the program had not
    # started yet.
    began = profile.get("program_start")
    began = date.fromisoformat(began) if began else today
    done = {}
    for s in sessions_log:
        if s.get("status") in ("done", "partial"):
            done.setdefault(s.get("date"), []).append(s)
    out = []
    wm = week_map(profile)
    for i in range(7):
        d = start + timedelta(days=i)
        day = wm[weekday_key(d)]
        logged = done.get(d.isoformat(), [])
        out.append({
            "date": d.isoformat(),
            "weekday": weekday_key(d),
            "day_key": day.key,
            "title": day.title,
            "kind": day.kind,
            "is_today": d == today,
            "past": d < today,
            "before_start": d < began,
            "done": [{"day_key": s.get("day_key"), "title": s.get("title"),
                      "status": s.get("status")} for s in logged],
        })
    return out


def missed_this_week(profile: dict, today: date, sessions_log: list[dict]) -> list[dict]:
    """Training days earlier this week whose workout was never done -- this
    week at all, on any day. Offered as a catch-up."""
    week = week_overview(profile, today, sessions_log)
    done_keys = {d["day_key"] for day in week for d in day["done"]}
    return [{"day_key": d["day_key"], "title": d["title"], "date": d["date"],
             "weekday": d["weekday"]}
            for d in week
            if d["past"] and not d["before_start"] and d["kind"] == "workout"
            and d["day_key"] not in done_keys]


def day_summary(day: Day, profile: dict) -> dict:
    """Light description for the Plan page -- no progression maths."""
    return {
        "key": day.key, "title": day.title, "focus": day.focus, "kind": day.kind,
        "notes": list(day.notes),
        "slots": [{"slot": s.key, "move": m.id, "sets": s.sets, "reps": list(s.reps),
                   "rest": s.rest, "hold": m.hold, "per_side": m.per_side}
                  for s in day.slots for m in (resolve_move(s, profile),)],
        "warmup": list(day.warmup), "cooldown": list(day.cooldown),
    }


__all__ = ["DAYS", "TRAINING_DAYS", "REST_DAYS", "WEEKDAYS", "build_session", "day_for",
           "week_map", "week_overview", "missed_this_week", "program_week", "phase_for",
           "day_summary", "resolve_move", "Slot", "Day"]
