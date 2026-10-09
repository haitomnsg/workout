"""The local web app.

    python -m trainer.web            (or double-click coach.bat)

Serves the UI, the JSON API, your demo videos and the pose model, on
127.0.0.1 only -- nothing is reachable from other machines and nothing is
sent anywhere. A background thread ticks the workout runner so timers and
voice cues keep going even when the browser tab is in the background.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import threading
import time
import webbrowser
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file, send_from_directory

from .. import catalog, equipment as eq, locations, nutrition, plan as planner, progression
from .. import session
from ..library import GROUPS, LIBRARY, available, get as get_move, options
from ..live import LiveTracker
from ..pose import MODEL_DIR, MODEL_FILES
from ..profile import (DEFAULT_PROFILE, kit as profile_kit, load_profile, update_profile,
                       week_start)
from ..runner import Runner
from ..voice import Voice

STATIC = Path(__file__).resolve().parent / "static"
SLUG = re.compile(r"^[a-z0-9-]{1,120}$")
MEDIA_EXT = {"video": "mp4", "img": "webp", "thumb": "webp"}

# Windows' registry often lacks these. Browsers refuse to run an ES module
# served as text/plain, and WebAssembly streaming needs application/wasm.
for _ext, _type in ((".mjs", "text/javascript"), (".js", "text/javascript"),
                    (".wasm", "application/wasm"), (".webp", "image/webp"),
                    (".mp4", "video/mp4"), (".task", "application/octet-stream")):
    mimetypes.add_type(_type, _ext)


def create_app(voice=None, clock=time.time, tick: bool = True) -> Flask:
    app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
    app.json.sort_keys = False
    # Revalidate static files every load (a cheap 304 when unchanged), so an
    # update to the app never runs against stale cached JavaScript.
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    profile = load_profile()
    voice = voice or Voice(enabled=profile["voice"]["enabled"])
    live = LiveTracker(voice)
    runner = Runner(voice, live, clock)
    app.config.update(VOICE=voice, LIVE=live, RUNNER=runner)

    if tick:
        def ticker() -> None:
            while True:
                try:
                    runner.tick()
                except Exception as exc:          # a bad tick must not kill the loop
                    app.logger.exception("tick failed: %s", exc)
                time.sleep(0.2)
        threading.Thread(target=ticker, daemon=True, name="runner-tick").start()

    # ------------------------------------------------------------ static

    @app.get("/")
    def index():
        resp = send_from_directory(STATIC, "index.html")
        resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.get("/models/<name>")
    def model(name: str):
        if name not in MODEL_FILES.values():
            abort(404)
        return send_from_directory(MODEL_DIR, name, max_age=7 * 86400)

    @app.get("/media/<kind>/<slug>")
    def media(kind: str, slug: str):
        slug = slug.rsplit(".", 1)[0]
        if kind not in MEDIA_EXT or not SLUG.match(slug):
            abort(404)
        path = catalog.MEDIA_ROOT / kind / f"{slug}.{MEDIA_EXT[kind]}"
        if not path.exists():
            abort(404)
        # conditional=True gives Range support, so videos seek and loop smoothly.
        return send_file(path, conditional=True, max_age=7 * 86400)

    # ------------------------------------------------------------ today

    @app.get("/api/today")
    def today():
        d = date.today()
        prof = load_profile()
        sets = session.load_sets()
        sessions = session.load_sessions()
        day = planner.day_for(prof, d)
        loc = planner.location_of(prof, request.args.get("location"))
        plan = planner.build_session(day, prof, d, sets, loc)
        done_today = [s for s in sessions if s.get("date") == d.isoformat()
                      and s.get("status") in ("done", "partial")]
        return jsonify({
            "date": d.isoformat(),
            "weekday": d.strftime("%A"),
            "location": loc,
            "locations": locations.as_list(),
            "plan": expand_plan(plan),
            "week": planner.week_overview(prof, d, sessions),
            "missed": planner.missed_this_week(prof, d, sessions),
            "done_today": done_today,
            "nutrition": {**dict(zip(("kcal", "protein"), nutrition.targets(prof))),
                          "training_day": day.kind == "workout"},
            "session": runner.snapshot(),
            "history_count": len(sessions),
        })

    @app.get("/api/day/<key>")
    def day_preview(key: str):
        if key not in planner.DAYS:
            abort(404)
        d = date.today()
        prof = load_profile()
        plan = planner.build_session(planner.DAYS[key], prof, d, session.load_sets(),
                                     request.args.get("location"))
        return jsonify(expand_plan(plan))

    # ------------------------------------------------------------ plan

    @app.get("/api/plan")
    def plan_view():
        d = date.today()
        prof = load_profile()
        kit = profile_kit(prof)
        loc = planner.location_of(prof, request.args.get("location"))
        start = week_start(d)
        wm = planner.week_map(prof)
        days = []
        for i, wd in enumerate(["sun", "mon", "tue", "wed", "thu", "fri", "sat"]):
            day = wm[wd]
            summary = planner.day_summary(day, prof, loc)
            for s in summary["slots"]:
                s["name"] = get_move(s["move"]).name
            summary["date"] = (start + timedelta(days=i)).isoformat()
            summary["weekday"] = wd
            summary["warmup_names"] = [get_move(m).name for m in day.warmup]
            summary["cooldown_names"] = [get_move(m).name for m in day.cooldown]
            days.append(summary)
        week = planner.program_week(prof, d)
        ladders = {m: {"label": eq.MODE_LABEL[m], "weights": eq.ladder(kit, m),
                       "base": kit.dumbbell_handle if m != "bb" else kit.barbell_bar}
                   for m in ("db1", "db2", "bb")}
        return jsonify({
            "location": loc, "current_location": planner.location_of(prof),
            "locations": locations.as_list(),
            "days": days, "week": week, "phase": planner.phase_for(week),
            "phase_text": planner.PHASE_TEXT[planner.phase_for(week)],
            "cycle_week": (week - 1) % planner.CYCLE_WEEKS + 1,
            "cycle_len": planner.CYCLE_WEEKS,
            "next_deload": week + (planner.CYCLE_WEEKS - ((week - 1) % planner.CYCLE_WEEKS + 1))
            if planner.phase_for(week) != "deload" else week,
            "ladders": ladders, "kit": {"plates": dict(kit.plates), "total": kit.total_plates},
        })

    # ------------------------------------------------------------ library

    @app.get("/api/library")
    def library():
        prof = load_profile()
        kit_at = {loc: locations.equipment(prof, loc) for loc in locations.LOCATIONS}
        rows = [{"id": m.id, "name": m.name, "kind": m.kind, "group": m.group,
                 "group_label": GROUPS.get(m.group, m.group), "mode": m.mode,
                 "tracker": m.tracker, "slug": m.slug, "muscles": m.muscles,
                 "per_side": m.per_side, "hold": m.hold, "needs": m.needs,
                 "places": [loc for loc, kit in kit_at.items() if available(m, kit)]}
                for m in LIBRARY.values()]
        return jsonify({"moves": rows, "groups": GROUPS, "locations": locations.as_list()})

    @app.get("/api/library/<move_id>")
    def library_item(move_id: str):
        if move_id not in LIBRARY:
            abort(404)
        m = LIBRARY[move_id]
        prof = load_profile()
        hist = session.work_sessions(m.id)
        return jsonify({
            "move": m.to_dict(),
            "options": {k: [{"id": o.id, "name": o.name} for o in v]
                        for k, v in options(m.id, prof["equipment"]).items()},
            "history": [{"date": s[0]["date"],
                         "sets": [{"weight": r.get("weight_kg"), "reps": r.get("reps"),
                                   "seconds": r.get("seconds"), "rating": r.get("rating")}
                                  for r in s]} for s in hist[-6:]][::-1],
            "loading_mode": eq.MODE_LABEL[m.mode],
        })

    # ------------------------------------------------------------ progress

    @app.get("/api/progress")
    def progress():
        return jsonify(progress_data())

    # ------------------------------------------------------------ nutrition

    @app.get("/api/nutrition")
    def nutrition_view():
        prof = load_profile()
        training = planner.day_for(prof, date.today()).kind == "workout"
        if request.args.get("day") in ("rest", "training"):
            training = request.args["day"] == "training"
        return jsonify(nutrition.as_dict(training, prof))

    # ------------------------------------------------------------ profile

    @app.get("/api/profile")
    def profile_get():
        prof = load_profile()
        kit = profile_kit(prof)
        return jsonify({"profile": prof, "defaults": DEFAULT_PROFILE,
                        "locations": locations.as_list(), "kit_labels": locations.KIT_LABELS,
                        "ranges": {m: [eq.ladder(kit, m)[0], eq.ladder(kit, m)[-1]]
                                   for m in ("db1", "db2", "bb")},
                        "media_ok": catalog.MEDIA_ROOT.exists()})

    @app.put("/api/profile")
    def profile_put():
        patch = request.get_json(force=True, silent=True) or {}
        prof = update_profile(patch)
        set_voice(prof["voice"]["enabled"])
        return jsonify({"profile": prof})

    # ------------------------------------------------------------ workout

    @app.get("/api/session")
    def session_get():
        snap = runner.snapshot()
        snap["live"] = live.state()
        return jsonify(snap)

    @app.post("/api/session/<action>")
    def session_act(action: str):
        data = request.get_json(force=True, silent=True) or {}
        try:
            snap = runner.act(action, data)
        except (ValueError, KeyError) as exc:
            return jsonify({"error": str(exc)}), 400
        snap["live"] = live.state()
        return jsonify(snap)

    @app.post("/api/pose")
    def pose():
        data = request.get_json(force=True, silent=True) or {}
        return jsonify(live.update(data))

    @app.post("/api/lab")
    def lab():
        """Run recorded landmark frames through a fresh tracker.

        Used to check the rep counters against the demo videos (see
        tests/tracker_lab.md). Same code path as a live set, silent voice.
        """
        data = request.get_json(force=True, silent=True) or {}
        name = data.get("save")
        if name and SLUG.match(name):
            # Keep the landmarks so trackers can be re-tuned offline with
            # scripts/tracker_lab.py, without re-running the pose model.
            out = session.DATA_DIR / "lab"
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{name}.json").write_text(json.dumps(
                {"tracker": data.get("tracker"), "frames": data.get("frames", [])}))
        tracker = LiveTracker(_SilentVoice())
        tracker.configure(data.get("tracker"))
        tracker.begin()
        views: dict[str, int] = defaultdict(int)
        signals = []
        for f in data.get("frames", []):
            st = tracker.update(f)
            views[st["view"]] += 1
            if st["signal"] is not None:
                signals.append(st["signal"])
        state = tracker.state()
        summary = tracker.end()
        return jsonify({"reps": state["reps"], "partials": state["partials"],
                        "frames": len(data.get("frames", [])), "views": views,
                        "signal_min": min(signals) if signals else None,
                        "signal_max": max(signals) if signals else None,
                        "faults": summary["faults"] if summary else {}})

    @app.post("/api/voice")
    def voice_toggle():
        data = request.get_json(force=True, silent=True) or {}
        set_voice(bool(data.get("enabled", not voice.enabled)))
        return jsonify({"enabled": voice.enabled})

    def set_voice(on: bool) -> None:
        if hasattr(voice, "set_enabled"):
            voice.set_enabled(on)
        else:
            voice.enabled = on

    return app


class _SilentVoice:
    enabled = False

    def say(self, *args, **kwargs) -> bool:
        return False


def expand_plan(plan: dict) -> dict:
    """Attach move details to a built session for display."""
    out = dict(plan)
    blocks = []
    kit = profile_kit()
    for b in plan["blocks"]:
        if b["type"] == "exercise":
            m = get_move(b["move"])
            w = b["target"].get("weight")
            blocks.append({**b, "move": m.to_dict(),
                           "weight_text": eq.format_weight(m.mode, w),
                           "plates": eq.plates(kit, m.mode, w)})
        else:
            blocks.append({**b, "items": [{**it, "name": get_move(it["move"]).name,
                                          "slug": get_move(it["move"]).slug}
                                         for it in b["items"]]})
    out["blocks"] = blocks
    return out


def progress_data() -> dict:
    sets = session.load_sets()
    sessions = session.load_sessions()
    today = date.today()

    # Every day with logged work counts as a workout, including days from
    # before session summaries existed.
    trained_days: dict[str, str] = {}
    for s in sessions:
        if s.get("status") in ("done", "partial"):
            trained_days[s["date"]] = "mobility" if s.get("kind") == "mobility" else "workout"
    for r in sets:
        if r.get("kind") == "work" and r.get("date"):
            trained_days.setdefault(r["date"], "workout")

    workouts = sorted(d for d, k in trained_days.items() if k == "workout")
    ws = week_start(today)
    this_week = sum(1 for d in workouts if date.fromisoformat(d) >= ws)

    # Streak: consecutive weeks (ending this week or last) with 3+ workouts.
    per_week: dict[date, int] = defaultdict(int)
    for d in workouts:
        per_week[week_start(date.fromisoformat(d))] += 1
    streak = 0
    wk = ws if per_week.get(ws, 0) >= 3 else ws - timedelta(days=7)
    while per_week.get(wk, 0) >= 3:
        streak += 1
        wk -= timedelta(days=7)

    calendar = []
    for i in range(83, -1, -1):
        d = today - timedelta(days=i)
        calendar.append({"date": d.isoformat(), "kind": trained_days.get(d.isoformat())})

    # Per exercise series.
    by_move: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in sets:
        if r.get("kind") == "work" and r["exercise_id"] in LIBRARY:
            by_move[r["exercise_id"]][r["session_id"]].append(r)
    exercises = []
    volume = 0.0
    for mid, groups in by_move.items():
        m = LIBRARY[mid]
        series = []
        best = None
        for sid, rs in groups.items():
            weights = [x.get("weight_kg") for x in rs if x.get("weight_kg")]
            reps = [int(x.get("reps") or 0) for x in rs]
            secs = [int(x.get("seconds") or 0) for x in rs]
            e = max((progression.e1rm(x.get("weight_kg"), int(x.get("reps") or 0)) or 0)
                    for x in rs) or None
            vol = sum((x.get("weight_kg") or 0) * int(x.get("reps") or 0) *
                      (2 if m.mode == "db2" else 1) for x in rs)
            volume += vol
            series.append({"date": rs[0]["date"], "weight": max(weights) if weights else None,
                           "reps": reps, "best_reps": max(reps) if reps else 0,
                           "seconds": max(secs) if any(secs) else None,
                           "e1rm": e, "volume": round(vol, 1),
                           "ratings": [x.get("rating") for x in rs]})
            if e and (best is None or e > best):
                best = e
        series.sort(key=lambda s: s["date"])
        last = series[-1]
        exercises.append({
            "id": mid, "name": m.name, "group": m.group, "mode": m.mode, "hold": m.hold,
            "weighted": m.weighted, "sessions": len(series), "series": series,
            "current_weight": last["weight"], "best_e1rm": best,
            "last_date": last["date"], "last_reps": last["reps"],
            "first_weight": series[0]["weight"],
        })
    exercises.sort(key=lambda e: e["last_date"], reverse=True)

    recent = sorted((s for s in sessions if s.get("status") in ("done", "partial")),
                    key=lambda s: s.get("ended", ""), reverse=True)[:20]
    return {
        "total_workouts": len(workouts),
        "this_week": this_week,
        "streak_weeks": streak,
        "total_volume": round(volume),
        "total_sets": sum(1 for r in sets if r.get("kind") == "work"),
        "calendar": calendar,
        "exercises": exercises,
        "recent": recent,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="WorkOut personal trainer (local web app)")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--no-voice", action="store_true")
    p.add_argument("--data-dir", type=Path, default=None,
                   help="use a different data folder (trial runs that must not touch your log)")
    args = p.parse_args()

    if args.data_dir:
        from .. import profile as profile_mod
        args.data_dir.mkdir(parents=True, exist_ok=True)
        session.set_data_dir(args.data_dir)
        profile_mod.set_data_dir(args.data_dir)
        print(f"  using data folder {args.data_dir}")

    voice = Voice(enabled=not args.no_voice and load_profile()["voice"]["enabled"])
    app = create_app(voice=voice)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"\n  WorkOut is running at {url}\n  Close this window to stop it.\n")
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    # threaded: pose frames, polling and actions arrive concurrently.
    # No reloader: it would start a second process and a second voice.
    app.run(host="127.0.0.1", port=args.port, threaded=True, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
