"""Your settings, in one small JSON file you can read and edit.

Everything the planner needs to know about you lives here: body stats for
nutrition, which days you train, what your plates and bars weigh, where you
are training (and what kit those places have), and any exercise swaps you
chose to keep. Missing keys fall back to the defaults
below, so an old or hand-edited file never breaks the app.
"""
from __future__ import annotations

import copy
import json
from datetime import date, timedelta
from pathlib import Path

from .equipment import Kit
from .locations import DEFAULT_AWAY_KIT, DEFAULT_LOCATION, LOCATIONS

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROFILE_PATH = DATA_DIR / "profile.json"


def set_data_dir(path: Path) -> None:
    global DATA_DIR, PROFILE_PATH
    DATA_DIR = Path(path)
    PROFILE_PATH = DATA_DIR / "profile.json"

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

DEFAULT_PROFILE: dict = {
    "age": 22,
    "height_cm": 162.0,
    "bodyweight_kg": 47.0,
    "sex": "male",
    "goal": "muscle",
    "level": "beginner",
    "training_days": ["sun", "mon", "tue", "wed", "thu"],
    "session_minutes": 60,
    # Sunday of the week the program started; set by the first workout.
    "program_start": None,
    "equipment": {
        "plates": {"2.0": 4, "1.5": 4, "1.25": 4},
        "rod_kg": 1.3,
        "connector_kg": 1.5,
        "collar_kg": 0.2,
        "bench": True,
        "pullup_bar": True,
    },
    # Where you train: dumbbells | furniture | floor (see locations.py).
    # Picked on the Today page and remembered until you change it.
    "location": DEFAULT_LOCATION,
    "away_kit": copy.deepcopy(DEFAULT_AWAY_KIT),
    "camera": {"model": "full", "mirror": True, "test_video": False},
    "voice": {"enabled": True},
    # Slot key -> exercise id, for swaps you chose to keep in future weeks.
    # Swaps made away from the dumbbells are keyed "<place>:<slot>".
    "swaps": {},
}


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict) and k != "plates":
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_profile() -> dict:
    if not PROFILE_PATH.exists():
        return copy.deepcopy(DEFAULT_PROFILE)
    try:
        saved = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        saved = {}
    return _merge(DEFAULT_PROFILE, saved)


def save_profile(profile: dict) -> dict:
    DATA_DIR.mkdir(exist_ok=True)
    clean = _merge(DEFAULT_PROFILE, profile)
    PROFILE_PATH.write_text(json.dumps(clean, indent=2), encoding="utf-8")
    return clean


def update_profile(patch: dict) -> dict:
    """Merge a partial update from the Settings screen, with light validation."""
    profile = _merge(load_profile(), patch)
    days = [d for d in profile.get("training_days", []) if d in WEEKDAYS]
    profile["training_days"] = [d for d in WEEKDAYS if d in days] or \
        list(DEFAULT_PROFILE["training_days"])
    for key, lo, hi in (("bodyweight_kg", 30, 200), ("height_cm", 120, 230), ("age", 12, 90)):
        try:
            profile[key] = min(hi, max(lo, float(profile[key])))
        except (TypeError, ValueError):
            profile[key] = DEFAULT_PROFILE[key]
    plates = {}
    for w, n in (profile["equipment"].get("plates") or {}).items():
        try:
            if float(w) > 0 and int(n) > 0:
                plates[f"{float(w):g}"] = int(n)
        except (TypeError, ValueError):
            continue
    profile["equipment"]["plates"] = plates or dict(DEFAULT_PROFILE["equipment"]["plates"])
    if profile.get("location") not in LOCATIONS:
        profile["location"] = DEFAULT_LOCATION
    profile["away_kit"] = {
        loc: {k: bool((profile.get("away_kit") or {}).get(loc, {}).get(k, v))
              for k, v in kit_.items()}
        for loc, kit_ in DEFAULT_AWAY_KIT.items()}
    return save_profile(profile)


def kit(profile: dict | None = None) -> Kit:
    return Kit.from_dict((profile or load_profile())["equipment"])


def week_start(day: date) -> date:
    """Sunday on or before `day` -- weeks run Sunday to Saturday."""
    return day - timedelta(days=(day.weekday() + 1) % 7)


def ensure_program_start(profile: dict, today: date) -> dict:
    if not profile.get("program_start"):
        profile["program_start"] = week_start(today).isoformat()
        profile = save_profile(profile)
    return profile


def weekday_key(day: date) -> str:
    return WEEKDAYS[day.weekday()]
