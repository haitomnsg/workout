"""Where you are training today, and what kit that place gives you.

    dumbbells   Home, with your dumbbells, bench and pull-up bar (Settings
                -> Equipment). The full program.
    furniture   No dumbbells, but ordinary home furniture: a sturdy chair or
                bed edge, a solid table to row under. Bodyweight versions of
                every session.
    floor       Nothing to rely on but the floor, a wall, a door and a towel.

You pick the place on the Today page before you start; the choice is
remembered until you change it. Each place has its own kept swaps, so
switching to table rows while away never changes your home program.
"""
from __future__ import annotations

DEFAULT_LOCATION = "dumbbells"

LOCATIONS: dict[str, dict] = {
    "dumbbells": {
        "label": "Home, with dumbbells",
        "short": "Dumbbells",
        "blurb": "Your full kit: dumbbells, barbell, bench and pull-up bar.",
    },
    "furniture": {
        "label": "No dumbbells",
        "short": "No dumbbells",
        "blurb": "Bodyweight, using a sturdy chair and a table.",
    },
    "floor": {
        "label": "Just the floor",
        "short": "Floor only",
        "blurb": "Bodyweight with only a floor, a wall, a door and a towel.",
    },
}

# What each away-from-home place has, as defaults for Settings. The keys are
# the `needs` tags in the library: "bench" is anything knee-high and sturdy
# (a chair, bed edge, low wall), "table" is something you can lie under and
# pull yourself up to.
DEFAULT_AWAY_KIT = {
    "furniture": {"bench": True, "table": True, "pullup_bar": False},
    "floor": {"bench": False, "table": False, "pullup_bar": False},
}

KIT_LABELS = {
    "bench": "A sturdy chair, bench or bed edge",
    "table": "A solid table to row under",
    "pullup_bar": "A pull-up bar",
}


def valid(location: str | None) -> str:
    return location if location in LOCATIONS else DEFAULT_LOCATION


def equipment(profile: dict, location: str | None = None) -> dict:
    """The `needs` flags available at a place, for library.available()."""
    loc = valid(location or profile.get("location"))
    if loc == "dumbbells":
        return {**profile.get("equipment", {}), "dumbbells": True}
    away = {**DEFAULT_AWAY_KIT[loc], **(profile.get("away_kit", {}).get(loc) or {})}
    return {**away, "dumbbells": False}


def swap_key(slot_key: str, location: str | None) -> str:
    """Kept swaps are per place; home keeps the bare slot key it always used."""
    loc = valid(location)
    return slot_key if loc == "dumbbells" else f"{loc}:{slot_key}"


def as_list() -> list[dict]:
    return [{"key": k, **v} for k, v in LOCATIONS.items()]
