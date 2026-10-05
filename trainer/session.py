"""Training logs.

Plain JSON lines, one object per set (`sets.jsonl`) and one per workout
(`sessions.jsonl`). Boring on purpose: progression reads months of history,
and nothing beats a file you can open and read yourself.

Records written before the app had a library (the first version logged
`"exercise": "squat"` with no rating) are normalised on read, so old history
still feeds the progression engine.
"""
from __future__ import annotations

import json
import os
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SETS_PATH = DATA_DIR / "sets.jsonl"
SESSIONS_PATH = DATA_DIR / "sessions.jsonl"
ACTIVE_PATH = DATA_DIR / "active_session.json"


def set_data_dir(path: Path) -> None:
    """Point the logs somewhere else -- for tests and trial runs, so they
    never touch your real training history."""
    global DATA_DIR, SETS_PATH, SESSIONS_PATH, ACTIVE_PATH
    DATA_DIR = Path(path)
    SETS_PATH = DATA_DIR / "sets.jsonl"
    SESSIONS_PATH = DATA_DIR / "sessions.jsonl"
    ACTIVE_PATH = DATA_DIR / "active_session.json"

# Tracker keys the first version logged, mapped to the library move they were.
LEGACY_IDS = {"squat": "goblet_squat", "bench": "db_bench_press", "row": "db_bent_row"}


def _append(path: Path, record: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue      # a half-written line from a crash is not worth dying over
    return out


# ---------------------------------------------------------------- sets

def log_set(summary: dict, weight_kg: float | None = None,
            notes: str = "") -> Path:
    """Append a set from the single-exercise OpenCV mode (trainer.main)."""
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "weight_kg": weight_kg,
        "notes": notes,
        **summary,
    }
    record.setdefault("exercise_id", LEGACY_IDS.get(summary.get("exercise", ""), ""))
    _append(SETS_PATH, record)
    return SETS_PATH


def append_set(record: dict) -> None:
    record = {"timestamp": datetime.now().isoformat(timespec="seconds"), **record}
    _append(SETS_PATH, record)


def load_history(exercise: str | None = None) -> list[dict]:
    """Raw records, optionally filtered by the legacy tracker key."""
    recs = _read(SETS_PATH)
    if exercise is None:
        return recs
    return [r for r in recs if r.get("exercise") == exercise]


def _slug_map() -> dict[str, str]:
    from .library import LIBRARY
    return {m.slug: m.id for m in LIBRARY.values() if m.slug}


def normalise(rec: dict, slugs: dict[str, str] | None = None) -> dict:
    """Fill in fields that older records lack."""
    r = dict(rec)
    if not r.get("exercise_id"):
        ex = r.get("exercise", "")
        slugs = slugs if slugs is not None else _slug_map()
        r["exercise_id"] = LEGACY_IDS.get(ex) or slugs.get(ex) or ex
    r.setdefault("kind", "work")
    r.setdefault("rating", None)
    r.setdefault("date", (r.get("timestamp") or "")[:10])
    r.setdefault("session_id", r["date"])
    return r


def load_sets() -> list[dict]:
    slugs = _slug_map()
    return [normalise(r, slugs) for r in _read(SETS_PATH)]


def work_sessions(exercise_id: str, sets: list[dict] | None = None) -> list[list[dict]]:
    """Working sets for one move, grouped per session, oldest first."""
    sets = load_sets() if sets is None else sets
    groups: "OrderedDict[str, list[dict]]" = OrderedDict()
    for r in sets:
        if r["exercise_id"] != exercise_id or r.get("kind") != "work":
            continue
        groups.setdefault(r["session_id"], []).append(r)
    return list(groups.values())


# ------------------------------------------------------------ sessions

def log_session(summary: dict) -> None:
    _append(SESSIONS_PATH, summary)


def load_sessions() -> list[dict]:
    return _read(SESSIONS_PATH)


# ------------------------------------------------- in-progress workout

def save_active(state: dict) -> None:
    """Persist the running workout so a closed tab or crash can resume.

    Written to a temp file then renamed, so a crash mid-write never leaves a
    truncated file behind.
    """
    DATA_DIR.mkdir(exist_ok=True)
    tmp = ACTIVE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    os.replace(tmp, ACTIVE_PATH)


def load_active() -> dict | None:
    if not ACTIVE_PATH.exists():
        return None
    try:
        return json.loads(ACTIVE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def clear_active() -> None:
    try:
        ACTIVE_PATH.unlink()
    except FileNotFoundError:
        pass
