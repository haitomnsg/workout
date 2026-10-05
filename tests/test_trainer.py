"""Tests for the trainer layer: plate maths, progression, the program, the
workout runner and the web API.

Run with: python tests/test_trainer.py

Everything writes to a temporary data folder -- your real training log in
data/ is never touched. No camera, no browser, no voice.
"""
from __future__ import annotations

import math
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trainer import profile, session                            # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="workout-test-"))
session.set_data_dir(TMP)
profile.set_data_dir(TMP)

from trainer import equipment as eq                             # noqa: E402
from trainer import plan as planner                             # noqa: E402
from trainer import progression                                 # noqa: E402
from trainer.exercises import REGISTRY                          # noqa: E402
from trainer.library import LIBRARY, get as get_move, options   # noqa: E402
from trainer.live import LiveTracker                            # noqa: E402
from trainer.runner import Runner                               # noqa: E402

FAILURES: list[str] = []
KIT = eq.DEFAULT_KIT


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"  {'PASS' if condition else 'FAIL'}  {label}" + ("" if condition else f" {detail}"))
    if not condition:
        FAILURES.append(label)


class Voice:
    enabled = True

    def __init__(self) -> None:
        self.said: list[str] = []

    def say(self, text, key=None, cooldown=None, force=False):
        self.said.append(text)
        return True


class Clock:
    def __init__(self) -> None:
        self.t = 1_000_000.0

    def __call__(self) -> float:
        return self.t


def reset_data() -> None:
    for f in TMP.iterdir():
        f.unlink()


# ------------------------------------------------------------- equipment

def test_equipment() -> None:
    print("\nequipment")
    db1, db2, bb = (eq.ladder(KIT, m) for m in ("db1", "db2", "bb"))
    check("single dumbbell tops out at 20.7 kg", db1[-1] == 20.7, f"got {db1[-1]}")
    check("barbell tops out at 23.9 kg", bb[-1] == 23.9, f"got {bb[-1]}")
    check("bare barbell is 4.9 kg", bb[0] == 4.9, f"got {bb[0]}")
    check("pair tops out at 11.2 kg each", db2[-1] == 11.2, f"got {db2[-1]}")
    # 9.7 needs mismatched plates (2+2 vs 1.5+1.25+1.25) -- the naive
    # split-the-pool maths misses it.
    check("pair solver finds mismatched-plate weights", 9.7 in db2, f"ladder {db2}")
    check("6.7 is impossible for a pair", 6.7 not in db2)

    for mode, ladder in (("db1", db1), ("db2", db2), ("bb", bb)):
        bad = []
        for w in ladder:
            ld = eq.loading(KIT, mode, w)
            ends = ld.ends
            plates = {p: 0 for p, _ in KIT.plates}
            per_end = [sum(p * c for (p, _), c in zip(KIT.plates, e)) for e in ends]
            base = KIT.barbell_bar if mode == "bb" else KIT.dumbbell_handle
            if any(abs(base + 2 * s - w) > 0.011 for s in per_end):
                bad.append(w)
            for e in ends:
                for (p, _), c in zip(KIT.plates, e):
                    plates[p] += 2 * c
            if any(plates[p] > n for p, n in KIT.plates):
                bad.append(("too many plates", w))
        check(f"every {mode} loading sums correctly and fits the plate set", not bad, f"{bad}")

    check("step_up never exceeds the max", eq.step_up(KIT, "bb", 23.9, 1.0) == 23.9)
    check("step_down is strictly lighter", eq.step_down(KIT, "db2", 7.2) < 7.2)
    check("bare handle described plainly", "no plates" in eq.describe_loading(KIT, "db2", 1.7))
    heavier = eq.Kit.from_dict({"rod_kg": 1.5})
    check("hardware weight shifts the ladder", eq.ladder(heavier, "db1")[0] == 1.9)


# ------------------------------------------------------------- progression

def sets(weight, reps, ratings):
    return [{"weight_kg": weight, "reps": r, "rating": g} for r, g in zip(reps, ratings)]


def test_progression() -> None:
    print("\nprogression")
    bench = get_move("db_bench_press")        # pair, 8-12
    rdl = get_move("bb_rdl")                  # barbell, lower body
    pushup = get_move("pushup")

    t = progression.recommend(bench, 8, 12, [], KIT)
    check("first time uses the start weight", t.status == "new" and t.weight == 5.7, f"{t}")

    t = progression.recommend(rdl, 8, 12, [sets(13.9, [12, 12, 12], ["good"] * 3)], KIT)
    check("top of range on every set -> weight up", t.status == "up" and t.weight > 13.9, f"{t}")
    check("after a jump the target resets to the bottom", t.goal == 8)

    t = progression.recommend(rdl, 8, 12, [sets(13.9, [12, 13, 14], ["easy"] * 3)], KIT)
    t1 = progression.recommend(rdl, 8, 12, [sets(13.9, [12, 12, 12], ["good"] * 3)], KIT)
    check("all easy jumps further than all good", t.weight > t1.weight, f"{t.weight} vs {t1.weight}")

    t = progression.recommend(rdl, 8, 12, [sets(13.9, [10, 9, 9], ["good", "good", "hard"])], KIT)
    check("inside the range -> same weight, more reps",
          t.status == "reps" and t.weight == 13.9 and t.goal == 10, f"{t}")

    t = progression.recommend(rdl, 8, 12, [sets(13.9, [5, 4, 4], ["failed"] * 3)], KIT)
    check("well below the range -> lighter", t.status == "down" and t.weight < 13.9, f"{t}")

    t = progression.recommend(rdl, 8, 12, [sets(13.9, [7, 8, 8], ["hard", "good", "hard"])], KIT)
    check("slightly below -> hold the weight", t.status == "hold" and t.weight == 13.9, f"{t}")

    stall = [sets(13.9, [8, 7, 7], ["hard", "failed", "failed"])] * 3
    t = progression.recommend(rdl, 8, 12, stall, KIT)
    check("three stuck sessions -> deload", t.status == "deload" and t.weight < 13.9, f"{t}")

    # Pair 5.7 -> 7.2 is +26%: build reps past 12 before jumping.
    t = progression.recommend(bench, 8, 12, [sets(5.7, [12, 12, 12], ["good"] * 3)], KIT)
    check("big plate jump stretches the rep target",
          t.status == "reps" and t.hi > 12 and t.weight == 5.7, f"{t}")
    t = progression.recommend(bench, 8, 12, [sets(5.7, [15, 15, 15], ["good"] * 3)], KIT)
    check("...then jumps once the stretched target is met", t.status == "up" and t.weight == 7.2, f"{t}")

    t = progression.recommend(bench, 8, 12, [sets(11.2, [20, 20, 20], ["good"] * 3)], KIT)
    check("maxed-out plates switch to reps", t.status == "maxed" and t.weight == 11.2, f"{t}")

    t = progression.recommend(get_move("goblet_squat"), 8, 12, [sets(7.0, [10], [None])], KIT)
    check("legacy off-ladder weight snaps to the plates", t.weight in eq.ladder(KIT, "db1")
          and "closest" in t.reason, f"{t}")

    t = progression.recommend(pushup, 8, 15, [sets(None, [15, 15, 15], ["good"] * 3)], KIT)
    check("bodyweight at the top -> suggest harder variation",
          t.status == "graduate" and t.graduate_to == "decline_pushup", f"{t}")

    plank = get_move("plank")
    t = progression.recommend(plank, 30, 60, [[{"seconds": 30, "rating": "good"}] * 3], KIT)
    check("holds add five seconds", t.goal == 35, f"{t}")

    a = progression.adjust_next_set(get_move("bb_ohp"), 6, 10, 8.9, 11, "easy", KIT)
    check("in-session: easy at the top -> heavier next set", a["weight"] > 8.9, f"{a}")
    a = progression.adjust_next_set(get_move("bb_ohp"), 6, 10, 8.9, 3, "failed", KIT)
    check("in-session: failed -> lighter next set", a["weight"] < 8.9, f"{a}")
    a = progression.adjust_next_set(bench, 8, 12, 5.7, 12, "easy", KIT)
    check("in-session: a big jump waits for more reps", a["weight"] == 5.7, f"{a}")

    w = progression.warmup_sets(KIT, bench, 8.2)
    check("ramp-up sets are lighter and on the ladder",
          w and all(s["weight"] < 8.2 and s["weight"] in eq.ladder(KIT, "db2") for s in w), f"{w}")


# ------------------------------------------------------------- library & plan

def test_library_and_plan() -> None:
    print("\nlibrary and plan")
    refs = [(m.id, r) for m in LIBRARY.values() for r in (*m.easier, *m.harder, *m.similar)
            if r not in LIBRARY]
    check("no dangling easier/harder/similar links", not refs, f"{refs}")
    trackers = [m.id for m in LIBRARY.values() if m.tracker and m.tracker not in REGISTRY]
    check("every tracker key exists", not trackers, f"{trackers}")
    check("every strength move has steps and cues",
          all(m.steps and m.cues for m in LIBRARY.values() if m.kind == "strength"))
    check("weighted moves have a start weight",
          all(m.start_kg for m in LIBRARY.values() if m.kind == "strength" and m.weighted))
    no_bench = options("db_bench_press", {"bench": False})
    check("options respect missing kit", all("bench" not in m.needs for v in no_bench.values()
                                              for m in v))

    prof = profile.load_profile()
    wm = planner.week_map(prof)
    check("Sun-Thu are training days",
          [wm[d].key for d in ("sun", "mon", "tue", "wed", "thu")] ==
          ["upper_a", "lower_a", "upper_b", "lower_b", "arms_core"])
    check("Fri and Sat are mobility", wm["fri"].kind == wm["sat"].kind == "mobility")

    for wk, phase in ((1, "intro"), (2, "build"), (8, "deload"), (9, "build"), (16, "deload")):
        check(f"week {wk} is {phase}", planner.phase_for(wk) == phase)

    prof["program_start"] = "2026-09-06"      # week 5 on 2026-10-05: build
    for d in planner.TRAINING_DAYS:
        s = planner.build_session(d, prof, date(2026, 10, 5), [])
        check(f"{d.title} fits in an hour (~{s['estimate_min']} min)",
              35 <= s["estimate_min"] <= 62, f"{s['estimate_min']}")
        for b in s["blocks"]:
            if b["type"] == "exercise":
                m = get_move(b["move"])
                if m.weighted:
                    ok = all(x["weight"] in eq.ladder(KIT, m.mode) for x in b["sets"])
                    if not ok:
                        check(f"{m.name} weights are loadable", False, f"{b['sets']}")

    intro = planner.build_session(planner.UPPER_A, {**prof, "program_start": None},
                                  date(2026, 10, 5), [])
    check("learning week uses two working sets",
          all(sum(1 for x in b["sets"] if x["kind"] == "work") <= 2
              for b in intro["blocks"] if b["type"] == "exercise"))

    no_bar = {**prof, "equipment": {**prof["equipment"], "pullup_bar": False}}
    m = planner.resolve_move(planner.SLOTS["ua.pull"], no_bar)
    check("missing pull-up bar falls back to a move you can do",
          "pullup_bar" not in m.needs, f"got {m.id}")


# ------------------------------------------------------------- runner

def run_session(runner: Runner, clock: Clock, rate=lambda n: "good", reps_bonus=0) -> dict:
    for _ in range(1000):
        s = runner.snapshot()
        if s["phase"] == "done":
            return s
        if s["phase"] == "rest" and s["pending"] and s["pending"]["kind"] == "work" \
                and not s["pending"]["rating"]:
            if reps_bonus:
                runner.act("reps", {"delta": reps_bonus})
            runner.act("rate", {"rating": rate(s["current"]["work_no"])})
        s = runner.snapshot()
        if s["until"]:
            clock.t = s["until"] + 0.1
            runner.tick()
        else:
            runner.act("next")
    raise AssertionError("runner never finished")


def test_runner() -> None:
    print("\nworkout runner")
    reset_data()
    clock, voice = Clock(), Voice()
    live = LiveTracker(voice)
    r = Runner(voice, live, clock)
    s = r.start("upper_a")
    check("starts at the overview", s["phase"] == "overview")
    check("resume file written", session.ACTIVE_PATH.exists())

    r.act("next")
    check("space enters the warm-up", r.snapshot()["phase"] == "timed")

    # Set 1 easy at the top of the range -> set 2 heavier (barbell press has small steps).
    while r.snapshot()["phase"] != "intro" or r.snapshot()["current"]["move"]["id"] != "bb_ohp":
        s = r.snapshot()
        if s["phase"] == "rest" and s["pending"] and not s["pending"]["rating"]:
            r.act("rate", {"rating": "good"})
        if s["until"]:
            clock.t = s["until"] + 0.1
            r.tick()
        else:
            r.act("next")
    r.act("weight", {"target": "next", "delta": 1})
    planned = r.snapshot()["current"]["sets"][-1]["weight"]
    check("[ ] changes the planned weight", planned == 9.9, f"got {planned}")
    r.act("weight", {"target": "next", "delta": -1})
    r.act("next")                                  # intro -> countdown (ramp-up set)
    while r.snapshot()["current"]["set"]["kind"] == "warmup" or r.snapshot()["phase"] != "active":
        s = r.snapshot()
        if s["phase"] in ("countdown",):
            r.act("next")
        elif s["phase"] == "active":
            r.act("next")
        elif s["phase"] == "rest":
            r.act("skip_rest")
    r.act("next")                                  # finish work set 1
    s = r.snapshot()
    check("finishing a set opens the rest with a pending log", s["phase"] == "rest" and s["pending"])
    r.act("reps", {"value": 11})
    r.act("rate", {"rating": "easy"})
    s = r.snapshot()
    check("easy set at the top raises the next set", s["advice"] and s["advice"]["to"] == 9.9,
          f"{s['advice']}")
    r.act("undo_advice")
    check("advice can be undone", r.snapshot()["next"]["set"]["weight"] == 8.9)
    r.act("rate", {"rating": "failed"})
    check("re-rating replans from the original weight",
          r.snapshot()["next"]["set"]["weight"] < 8.9, f"{r.snapshot()['next']['set']}")

    final = run_session(r, clock)
    sm = final["summary"]
    check("session completes with a summary", sm["status"] == "done" and sm["total_sets"] > 0)
    check("resume file removed when done", not session.ACTIVE_PATH.exists())
    logged = session.load_sets()
    check("every working set has a rating", all(x["rating"] for x in logged if x["kind"] == "work"))
    check("ramp-up sets are logged separately", any(x["kind"] == "warmup" for x in logged))
    check("session summary written", len(session.load_sessions()) == 1)
    check("voice announced the workout", any("Upper A" in t for t in voice.said))

    # Next time: history drives the targets.
    s2 = Runner(voice, live, clock).start("upper_a")
    statuses = {b["move"]["id"]: b["target"]["status"] for b in s2["blocks"] if b["type"] == "exercise"}
    check("second session uses history, not start weights",
          all(st != "new" for st in statuses.values()), f"{statuses}")

    # Crash/restart: a mid-workout runner resumes paused.
    r3 = Runner(voice, live, clock)
    r3.act("next")
    r4 = Runner(voice, live, clock)
    check("restart resumes the same workout, paused",
          r4.snapshot()["active"] and r4.snapshot()["paused"])
    r4.act("discard")
    check("discard clears it", not r4.snapshot()["active"] and not session.ACTIVE_PATH.exists())


def test_swap_and_skip() -> None:
    print("\nswap and skip")
    reset_data()
    clock, voice = Clock(), Voice()
    r = Runner(voice, LiveTracker(voice), clock)
    r.start("upper_a")
    r.act("next")
    while r.snapshot()["phase"] != "intro":
        r.act("next")
    first = r.snapshot()["current"]["move"]["id"]
    r.act("swap", {"move": "db_floor_press", "keep": True})
    s = r.snapshot()
    check("swap lands on the new move's intro",
          s["phase"] == "intro" and s["current"]["move"]["id"] == "db_floor_press", f"{first}")
    check("kept swap saved to the profile",
          profile.load_profile()["swaps"].get("ua.press") == "db_floor_press")
    r.act("skip_exercise")
    check("skip moves to the next exercise",
          r.snapshot()["current"]["move"]["id"] == "db_bent_row")
    r.act("end")
    check("ending early is recorded as partial", r.snapshot()["summary"]["status"] == "partial")
    prof = profile.load_profile()
    prof["swaps"] = {}
    profile.save_profile(prof)


# ------------------------------------------------------------- api

def test_api() -> None:
    print("\nweb api")
    reset_data()
    from trainer.web.server import create_app
    app = create_app(voice=Voice(), tick=False)
    c = app.test_client()
    for url in ("/", "/api/today", "/api/plan", "/api/library", "/api/library/bss",
                "/api/progress", "/api/nutrition", "/api/profile", "/api/session"):
        r = c.get(url)
        check(f"GET {url}", r.status_code == 200, f"status {r.status_code}")
    check("ES modules served as JavaScript",
          "javascript" in c.get("/static/js/app.js").content_type)
    check("wasm served as application/wasm",
          c.get("/static/vendor/tasks-vision/wasm/vision_wasm_internal.wasm").content_type
          == "application/wasm")
    check("media rejects path tricks", c.get("/media/video/..%2F..%2Fsecret").status_code == 404)
    r = c.put("/api/profile", json={"bodyweight_kg": 500, "training_days": ["xyz"]}).get_json()
    check("profile input is clamped and validated",
          r["profile"]["bodyweight_kg"] == 200 and len(r["profile"]["training_days"]) == 5)
    s = c.post("/api/session/start", json={"day": "lower_b"}).get_json()
    check("start a chosen day", s["plan"]["day_key"] == "lower_b")
    check("bad action rejected", c.post("/api/session/fly").status_code == 400)
    p = c.post("/api/pose", json={"t": 1.0, "ok": True, "px": [0] * 66, "world": [0] * 99,
                                  "vis": [1] * 33}).get_json()
    check("pose frames accepted", "reps" in p)
    c.post("/api/session/discard")


# ------------------------------------------------------------- trackers

def test_tracker_fixtures() -> None:
    """Every rep counter against real pose landmarks from the demo videos.

    The fixtures were captured by running the demo videos through the
    in-browser pose model (see scripts/tracker_lab.py).
    """
    print("\nrep trackers on demo-video landmarks")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import tracker_lab
    files = sorted(tracker_lab.FIXTURES.glob("*.json.gz"))
    check("pose fixtures present", len(files) >= 30, f"found {len(files)}")
    covered = set()
    for f in files:
        r = tracker_lab.replay(f)
        if r["slug"] in tracker_lab.KNOWN_DEMO_LIMITS:
            continue
        covered.add(r["tracker"])
        check(f"{r['tracker']:10s} {r['slug']}",
              tracker_lab.counted_right(r["slug"], r["reps"], r["partials"], r["loops"]),
              f"reps={r['reps']} partials={r['partials']} over {r['loops']} loops")
    used = {m.tracker for m in LIBRARY.values() if m.tracker}
    check("every tracker the library uses is verified on a demo",
          used <= covered, f"unverified: {used - covered}")


def main() -> int:
    test_tracker_fixtures()
    test_equipment()
    test_progression()
    test_library_and_plan()
    test_runner()
    test_swap_and_skip()
    test_api()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
