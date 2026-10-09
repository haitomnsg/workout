"""The guided workout: one state machine from warm-up to summary.

    overview -> timed (warm-up items, hands-free) ->
      per exercise:  intro -> [countdown -> active -> rest] x sets ->
    timed (cool-down) -> done

Space ("next") is always the main action, so the whole session can be driven
from one key. Timers, side switches and rest countdowns run server-side in
`tick()`, so voice cues keep coming even if the browser tab is in the
background.

A finished set stays editable during its rest (reps, weight, rating) and is
only written to the log when the rest ends -- that is when your rating is
known, and it is what the progression engine needs.

State is saved to data/active_session.json after every change: close the
browser or crash mid-workout and it resumes where you were.
"""
from __future__ import annotations

import threading
import time
from datetime import date, datetime

from . import equipment as eq
from . import plan as planner
from . import locations, progression, session
from .library import get as get_move
from .profile import ensure_program_start, kit as profile_kit, load_profile, save_profile

COUNTDOWN = 5            # seconds to get into position before a set
SWITCH_COUNTDOWN = 6     # seconds to switch sides
WARMUP_SET_REST = 45
TEACH_COOLDOWN = 3.0     # cue cooldown cap while learning a movement


def speak_weight(mode: str, w: float | None) -> str:
    if w is None or mode == "bw":
        return "bodyweight"
    return f"{w:g} kilos" + (" each" if mode == "db2" else "")


class Runner:
    def __init__(self, voice, live, clock=time.time) -> None:
        self.voice = voice
        self.live = live
        self.clock = clock
        self.lock = threading.RLock()
        self.st: dict | None = session.load_active()
        self._marks: set[str] = set()
        if self.st and self.st.get("phase") != "done":
            # Never let timers fire on their own after a restart.
            if not self.st.get("paused_at"):
                self.st["paused_at"] = self.clock()
            self._configure_live()
        elif self.st:
            self.st = None

    # ================================================================ setup

    def start(self, day_key: str | None = None, location: str | None = None) -> dict:
        with self.lock:
            today = date.today()
            profile = load_profile()
            if location in locations.LOCATIONS and location != profile.get("location"):
                profile["location"] = location        # remembered for next time
                profile = save_profile(profile)
            profile = ensure_program_start(profile, today)
            day = planner.DAYS[day_key] if day_key else planner.day_for(profile, today)
            plan = planner.build_session(day, profile, today, session.load_sets(),
                                         profile["location"])
            now = self.clock()
            self.st = {
                "id": f"{today.isoformat()}-{day.key}-{datetime.now():%H%M%S}",
                "plan": plan,
                "steps": self._flatten(plan),
                "pos": -1,
                "phase": "overview",
                "started_at": now,
                "phase_started": now,
                "until": None,
                "paused_at": None,
                "side": 1,
                "pending": None,
                "advice": None,
                "log": [],
                "summary": None,
            }
            self._save()
            where = "" if plan["location"] == locations.DEFAULT_LOCATION else \
                " Bodyweight version, no dumbbells."
            self.voice.say(f"Today is {plan['title']}. {plan['focus']}.{where} "
                           f"About {plan['estimate_min']} minutes. Press space to begin.",
                           key="overview", force=True)
            return self.snapshot()

    @staticmethod
    def _flatten(plan: dict) -> list[dict]:
        steps = []
        for bi, b in enumerate(plan["blocks"]):
            if b["type"] == "exercise":
                steps.append({"t": "intro", "block": bi})
                for si in range(len(b["sets"])):
                    steps.append({"t": "set", "block": bi, "set": si})
            else:
                for ii in range(len(b["items"])):
                    steps.append({"t": "timed", "block": bi, "item": ii})
        return steps

    # ============================================================= helpers

    def _step(self, pos: int | None = None) -> dict | None:
        st = self.st
        pos = st["pos"] if pos is None else pos
        return st["steps"][pos] if 0 <= pos < len(st["steps"]) else None

    def _block(self, step: dict) -> dict:
        return self.st["plan"]["blocks"][step["block"]]

    def _set(self, step: dict) -> dict:
        return self._block(step)["sets"][step["set"]]

    def _move(self, step: dict):
        b = self._block(step)
        if step["t"] == "timed":
            return get_move(b["items"][step["item"]]["move"])
        return get_move(b["move"])

    def _work_index(self, step: dict) -> tuple[int, int]:
        """(1-based number among working sets, total working sets)."""
        sets = self._block(step)["sets"]
        work = [i for i, s in enumerate(sets) if s["kind"] == "work"]
        n = work.index(step["set"]) + 1 if step["set"] in work else 0
        return n, len(work)

    def _save(self) -> None:
        # A finished workout lives only in sessions.jsonl; never re-create the
        # resume file for it.
        if self.st is not None and self.st["phase"] != "done":
            session.save_active(self.st)

    def _set_phase(self, phase: str, seconds: float | None = None) -> None:
        now = self.clock()
        self.st["phase"] = phase
        self.st["phase_started"] = now
        self.st["until"] = now + seconds if seconds is not None else None
        self._marks = set()

    def _configure_live(self, step: dict | None = None) -> None:
        """Tell the camera what movement to expect for the current or next set."""
        step = step or self._step()
        if step is None or step["t"] == "timed":
            self.live.configure(None)
            return
        m = self._move(step)
        self.live.configure(m.tracker, m.view)

    def _teach_cap(self, step: dict) -> float | None:
        b = self._block(step)
        learning = (b.get("first_time") or self.st["plan"]["phase"] == "intro"
                    or self._set(step)["kind"] == "warmup")
        return TEACH_COOLDOWN if learning else None

    # ========================================================= transitions

    def _enter(self, pos: int) -> None:
        st = self.st
        st["pos"] = pos
        st["side"] = 1
        step = self._step()
        if step is None:
            self._finish()
            return
        self._configure_live()
        m = self._move(step)
        b = self._block(step)

        if step["t"] == "timed":
            item = b["items"][step["item"]]
            secs = item["seconds"] * (2 if item["per_side"] else 1)
            self._set_phase("timed", secs)
            if step["item"] == 0:
                intro = {"warmup": "Warm-up", "cooldown": "Cool-down. Well done",
                         "mobility": b.get("title", "Mobility")}.get(b["type"], "")
                n = len(b["items"])
                self.voice.say(f"{intro}. {n} moves.", key="block", force=True)
            sides = " First side." if item["per_side"] else ""
            self.voice.say(f"{m.name}. {item['seconds']} seconds.{sides}",
                           key="timed", force=True)
        elif step["t"] == "intro":
            self._set_phase("intro")
            t = b["target"]
            work = [s for s in b["sets"] if s["kind"] == "work"]
            if m.hold:
                rx = f"{len(work)} sets of {work[0]['goal']} seconds"
            else:
                side = " per side" if m.per_side else ""
                rx = f"{len(work)} sets of {t['lo']} to {t['hi']}{side}"
            cue = f" {m.cues[0]}." if m.cues else ""
            self.voice.say(f"Next: {m.name}. {rx}, {speak_weight(m.mode, work[0]['weight'])}."
                           f"{cue} Press space when you are ready.", key="intro", force=True)
        else:  # set
            self._begin_countdown()
        self._save()

    def _begin_countdown(self) -> None:
        step = self._step()
        s = self._set(step)
        m = self._move(step)
        if s["kind"] == "warmup":
            what = f"Ramp-up set. {s['goal']} reps at {speak_weight(m.mode, s['weight'])}"
        else:
            n, total = self._work_index(step)
            what = f"Set {n} of {total}, {speak_weight(m.mode, s['weight'])}"
        self._set_phase("countdown", COUNTDOWN)
        self.voice.say(f"{what}. Get in position.", key="countdown", force=True)

    def _go_active(self) -> None:
        step = self._step()
        s = self._set(step)
        m = self._move(step)
        if self.st["side"] == 1:
            self.live.begin(self._teach_cap(step))
        if m.hold:
            self._set_phase("active", s["goal"])
        else:
            self._set_phase("active")
        self.voice.say("Go.", key="go", force=True)

    def _finish_set(self, elapsed: float | None = None) -> None:
        st = self.st
        step = self._step()
        s = self._set(step)
        b = self._block(step)
        m = self._move(step)
        summary = self.live.end()
        camera_reps = summary["reps"] if summary else None
        if m.hold:
            done_secs = int(round(elapsed if elapsed is not None else s["goal"]))
            reps = done_secs
        else:
            reps = camera_reps if camera_reps else s["goal"]
        n, total = self._work_index(step)
        st["pending"] = {
            "pos": st["pos"],
            "kind": s["kind"],
            "set_label": "Ramp-up set" if s["kind"] == "warmup" else f"Set {n} of {total}",
            "weight": s["weight"],
            "reps": reps,
            "camera_reps": camera_reps,
            "reps_by_side": summary["reps_by_side"] if summary else None,
            "tracked": summary is not None,
            "partials": summary["partials"] if summary else 0,
            "clean_reps": summary["clean_reps"] if summary else None,
            "faults": summary["faults"] if summary else {},
            "mean_rep_seconds": summary["mean_rep_seconds"] if summary else None,
            "rating": None if s["kind"] == "work" else "good",
            "hold": m.hold,
        }
        st["advice"] = None

        nxt = self._step(st["pos"] + 1)
        same = nxt is not None and nxt["t"] == "set" and nxt["block"] == step["block"]
        if s["kind"] == "warmup":
            rest = WARMUP_SET_REST
        elif same:
            rest = b["rest"]
        elif nxt is None:
            rest = 20
        else:
            rest = 60 if nxt["t"] == "intro" else 30
        self._set_phase("rest", rest)
        unit = "seconds" if m.hold else "reps"
        ask = " Rate the set." if s["kind"] == "work" else ""
        self.voice.say(f"Set done. {reps} {unit}.{ask}", key="setdone", force=True)
        # Point the camera's position check at whatever comes after the rest.
        if nxt is not None and nxt["t"] != "timed":
            self._configure_live(nxt)
        self._save()

    def _commit_pending(self) -> None:
        st = self.st
        p = st.get("pending")
        if not p:
            return
        step = self._step(p["pos"])
        b = self._block(step)
        s = self._set(step)
        m = get_move(b["move"])
        n, _ = self._work_index(step)
        plan = st["plan"]
        record = {
            "session_id": st["id"],
            "date": plan["date"],
            "day_key": plan["day_key"],
            "exercise_id": m.id,
            "exercise": m.tracker or m.id,
            "slot": b["slot"],
            "mode": m.mode,
            "kind": p["kind"],
            "set_no": n if p["kind"] == "work" else 0,
            "weight_kg": p["weight"],
            "reps": p["reps"] if not p["hold"] else 0,
            "seconds": p["reps"] if p["hold"] else None,
            "reps_by_side": p["reps_by_side"],
            "target_lo": s["lo"], "target_hi": s["hi"], "goal": s["goal"],
            "rating": p["rating"],
            "tracked": p["tracked"],
            "camera_reps": p["camera_reps"],
            "partials": p["partials"],
            "clean_reps": p["clean_reps"],
            "faults": p["faults"],
            "mean_rep_seconds": p["mean_rep_seconds"],
        }
        session.append_set(record)
        st["log"].append(record)
        st["pending"] = None

    def _after_rest(self) -> None:
        self._commit_pending()
        self.st["advice"] = None
        nxt = self.st["pos"] + 1
        step = self._step(nxt)
        if step is not None and step["t"] == "set":
            self.st["pos"] = nxt
            self.st["side"] = 1
            self._configure_live()
            self._begin_countdown()
            self._save()
        else:
            self._enter(nxt)

    def _finish(self, status: str = "done") -> None:
        st = self.st
        self._commit_pending()
        self.live.cancel()
        self.live.configure(None)
        now = self.clock()
        st["phase"] = "done"
        st["until"] = None
        st["summary"] = self._summary(status, now)
        session.log_session(st["summary"])
        session.clear_active()
        if status == "done":
            self.voice.say("Workout complete. Great work today.", key="done", force=True)

    def _summary(self, status: str, now: float) -> dict:
        st = self.st
        plan = st["plan"]
        history = [r for r in session.load_sets() if r.get("session_id") != st["id"]]
        best_before: dict[str, float] = {}
        for r in history:
            if r.get("kind") != "work":
                continue
            e = progression.e1rm(r.get("weight_kg"), int(r.get("reps") or 0))
            if e:
                best_before[r["exercise_id"]] = max(best_before.get(r["exercise_id"], 0), e)
        exercises: dict[str, dict] = {}
        volume = 0.0
        for r in st["log"]:
            if r["kind"] != "work":
                continue
            m = get_move(r["exercise_id"])
            ex = exercises.setdefault(m.id, {"move": m.id, "name": m.name, "sets": [],
                                             "pr": False, "best_e1rm": None})
            ex["sets"].append({"weight": r["weight_kg"], "reps": r["reps"],
                               "seconds": r.get("seconds"), "rating": r["rating"]})
            if r["weight_kg"]:
                volume += r["weight_kg"] * r["reps"] * (2 if r["mode"] == "db2" else 1)
            e = progression.e1rm(r["weight_kg"], int(r["reps"] or 0))
            if e and (ex["best_e1rm"] is None or e > ex["best_e1rm"]):
                ex["best_e1rm"] = e
        for ex in exercises.values():
            prev = best_before.get(ex["move"])
            ex["pr"] = bool(ex["best_e1rm"] and prev and ex["best_e1rm"] > prev + 1e-6)
        work_sets = [r for r in st["log"] if r["kind"] == "work"]
        return {
            "id": st["id"],
            "date": plan["date"],
            "day_key": plan["day_key"],
            "title": plan["title"],
            "kind": plan["kind"],
            "location": plan.get("location", locations.DEFAULT_LOCATION),
            "status": status,
            "week": plan["week"],
            "phase": plan["phase"],
            "started": datetime.fromtimestamp(st["started_at"]).isoformat(timespec="seconds"),
            "ended": datetime.fromtimestamp(now).isoformat(timespec="seconds"),
            "duration_min": round((now - st["started_at"]) / 60, 1),
            "total_sets": len(work_sets),
            "total_reps": sum(r["reps"] for r in work_sets),
            "volume_kg": round(volume, 1),
            "exercises": list(exercises.values()),
            "ratings": {k: sum(1 for r in work_sets if r["rating"] == k)
                        for k in ("easy", "good", "hard", "failed")},
        }

    # ============================================================== ticking

    def tick(self) -> None:
        with self.lock:
            st = self.st
            if not st or st["phase"] in ("done", "overview", "intro") or st.get("paused_at"):
                return
            now = self.clock()
            until = st.get("until")
            phase = st["phase"]
            step = self._step()

            if phase == "timed" and step is not None:
                item = self._block(step)["items"][step["item"]]
                if item["per_side"] and st["side"] == 1 and \
                        now >= st["phase_started"] + item["seconds"]:
                    st["side"] = 2
                    self.voice.say("Switch sides.", key="switch", force=True)
                    self._save()
                left = (until or now) - now
                if 3.5 > left > 2.5 and "t3" not in self._marks:
                    self._marks.add("t3")
                    nxt = self._step(st["pos"] + 1)
                    if nxt and nxt["t"] == "timed":
                        self.voice.say(f"Next: {self._move(nxt).name}.", key="next", force=True)
                if left <= 0:
                    self._enter(st["pos"] + 1)
                return

            if phase == "countdown" and until is not None and now >= until:
                self._go_active()
                self._save()
                return

            if phase == "active" and until is not None:
                left = until - now
                if 10.5 > left > 9.5 and "a10" not in self._marks:
                    self._marks.add("a10")
                    self.voice.say("Ten seconds.", key="a10", force=True)
                if left <= 0:
                    m = self._move(step)
                    if m.per_side and st["side"] == 1:
                        st["side"] = 2
                        self.live.switch_side(self._teach_cap(step))
                        self._set_phase("countdown", SWITCH_COUNTDOWN)
                        self.voice.say("Switch sides.", key="switch", force=True)
                    else:
                        self._finish_set(elapsed=self._set(step)["goal"])
                    self._save()
                return

            if phase == "rest" and until is not None:
                left = until - now
                for mark in (30, 10):
                    if mark + 0.5 > left > mark - 0.5 and f"r{mark}" not in self._marks \
                            and until - st["phase_started"] > mark + 5:
                        self._marks.add(f"r{mark}")
                        self.voice.say(f"{mark} seconds.", key=f"r{mark}", force=True)
                if left <= 0:
                    self._after_rest()
                return

    # ============================================================== actions

    def act(self, action: str, data: dict | None = None) -> dict:
        data = data or {}
        with self.lock:
            st = self.st
            if st is None:
                if action == "start":
                    return self.start(data.get("day"), data.get("location"))
                raise ValueError("no active workout")
            handler = getattr(self, f"_a_{action}", None)
            if handler is None:
                raise ValueError(f"unknown action {action!r}")
            if st.get("paused_at") and action not in ("resume", "end", "discard", "pause"):
                self._a_resume(data)
            handler(data)
            if self.st is not None and self.st.get("phase") != "done":
                self._save()
            return self.snapshot()

    def _a_start(self, data: dict) -> None:
        if self.st["phase"] == "overview":
            self._enter(0)

    def _a_next(self, data: dict) -> None:
        """Space: whatever the obvious next thing is."""
        st = self.st
        phase = st["phase"]
        if phase == "overview":
            self._enter(0)
        elif phase == "timed":
            self._enter(st["pos"] + 1)
        elif phase == "intro":
            self._enter(st["pos"] + 1)
        elif phase == "countdown":
            self._go_active()
        elif phase == "active":
            step = self._step()
            m = self._move(step)
            elapsed = self.clock() - st["phase_started"]
            if m.per_side and st["side"] == 1:
                st["side"] = 2
                self.live.switch_side(self._teach_cap(step))
                self._set_phase("countdown", SWITCH_COUNTDOWN)
                self.voice.say("Switch sides.", key="switch", force=True)
            else:
                self._finish_set(elapsed=elapsed if m.hold else None)
        elif phase == "rest":
            self._after_rest()

    def _a_skip_rest(self, data: dict) -> None:
        if self.st["phase"] == "rest":
            self._after_rest()

    def _a_add_rest(self, data: dict) -> None:
        st = self.st
        if st["phase"] == "rest" and st["until"]:
            st["until"] += float(data.get("seconds", 30))

    def _a_rate(self, data: dict) -> None:
        p = self.st.get("pending")
        rating = data.get("rating")
        if not p or rating not in progression.RATING_RIR:
            return
        p["rating"] = rating
        self._advise()

    def _a_reps(self, data: dict) -> None:
        p = self.st.get("pending")
        if not p:
            return
        if "value" in data:
            p["reps"] = max(0, int(data["value"]))
        else:
            p["reps"] = max(0, p["reps"] + int(data.get("delta", 0)))
        if p.get("rating"):
            self._advise()

    def _a_weight(self, data: dict) -> None:
        """Change the logged weight of the set you just did, or the weight of
        the remaining sets (`target: "next"`), one plate step at a time."""
        st = self.st
        if st["phase"] == "rest" and st.get("pending"):
            step = self._step(st["pending"]["pos"])
        else:
            step = self._step()
        if step is None or step["t"] == "timed":
            return
        m = self._move(step)
        if not m.weighted:
            return
        kit = profile_kit()
        ladder = eq.ladder(kit, m.mode)
        direction = int(data.get("delta", 0))

        def moved(w: float) -> float:
            if "value" in data:
                return eq.nearest(kit, m.mode, float(data["value"]))
            i = min(range(len(ladder)), key=lambda k: abs(ladder[k] - w))
            return ladder[max(0, min(len(ladder) - 1, i + direction))]

        if data.get("target") == "last" and st.get("pending"):
            st["pending"]["weight"] = moved(st["pending"]["weight"] or ladder[0])
            if st["pending"].get("rating"):
                self._advise()
            return
        # Remaining sets of this exercise: from the next set when resting,
        # otherwise including the current one.
        b = self._block(step)
        if step["t"] == "intro":
            start = 0
        else:
            start = step["set"] + (1 if st["phase"] == "rest" else 0)
        for s in b["sets"][start:]:
            if s["kind"] == "work":
                s["weight"] = moved(s["weight"] or ladder[0])
        st["advice"] = None

    def _advise(self) -> None:
        """Re-plan the remaining sets from the rating of the one just done."""
        st = self.st
        p = st["pending"]
        if p["kind"] != "work":
            return
        step = self._step(p["pos"])
        b = self._block(step)
        m = get_move(b["move"])
        remaining = [s for s in b["sets"][step["set"] + 1:] if s["kind"] == "work"]
        prev = st.get("advice")
        if prev and prev.get("pos") == p["pos"]:
            for s, w in zip(remaining, prev["original"]):
                s["weight"] = w
        original = [s["weight"] for s in remaining]
        s = self._set(step)
        adv = progression.adjust_next_set(m, s["lo"], s["hi"], p["weight"], p["reps"],
                                          p["rating"], profile_kit())
        if adv is None or not remaining:
            st["advice"] = {"pos": p["pos"], "original": original,
                            "message": adv["message"] if adv else "", "from": None, "to": None} \
                if adv else None
            return
        new_w = adv["weight"]
        changed = new_w is not None and remaining and new_w != remaining[0]["weight"]
        if changed:
            for r in remaining:
                r["weight"] = new_w
            self.voice.say(f"Next set: {speak_weight(m.mode, new_w)}.", key="advice", force=True)
        st["advice"] = {"pos": p["pos"], "original": original, "message": adv["message"],
                        "from": original[0] if original else None,
                        "to": new_w if changed else None,
                        "loading": eq.describe_loading(profile_kit(), m.mode, new_w)
                        if changed else "",
                        "plates": eq.plates(profile_kit(), m.mode, new_w) if changed else None}

    def _a_undo_advice(self, data: dict) -> None:
        st = self.st
        adv, p = st.get("advice"), st.get("pending")
        if not adv or not p:
            return
        step = self._step(p["pos"])
        b = self._block(step)
        remaining = [s for s in b["sets"][step["set"] + 1:] if s["kind"] == "work"]
        for s, w in zip(remaining, adv["original"]):
            s["weight"] = w
        adv["to"] = None
        adv["message"] = "Kept your planned weight."

    def _a_skip_exercise(self, data: dict) -> None:
        st = self.st
        self._commit_pending()
        self.live.cancel()
        step = self._step()
        if step is None:
            return
        block = step["block"]
        pos = st["pos"]
        while self._step(pos) is not None and self._step(pos)["block"] == block:
            pos += 1
        self._enter(pos)

    def _a_swap(self, data: dict) -> None:
        """Replace the current exercise's remaining sets with another move."""
        st = self.st
        step = self._step()
        if step is None or step["t"] == "timed" or st["phase"] in ("active", "countdown"):
            return
        new = get_move(data.get("move"))
        b = self._block(step)
        slot = planner.SLOTS.get(b["slot"])
        if slot is None:
            return
        profile = load_profile()
        loc = st["plan"].get("location")
        rebuilt = planner.build_exercise(slot, new, profile, st["plan"]["phase"], location=loc)
        # Sets already done stay in the block (and the log) as they were.
        n_done = step["set"] + 1 if step["t"] == "set" else 0
        done = b["sets"][:n_done]
        if done:
            work_done = sum(1 for s in done if s["kind"] == "work")
            fresh = [s for s in rebuilt["sets"] if s["kind"] == "work"][work_done:]
            if not fresh:
                return        # exercise already finished -- swap the next one at its intro
        else:
            fresh = rebuilt["sets"]
        self._commit_pending()
        b.update({"move": new.id, "target": rebuilt["target"],
                  "first_time": rebuilt["first_time"], "sets": done + fresh})

        # Re-flatten this block: an intro for the new move, then the undone sets.
        bi = step["block"]
        before = [s for s in st["steps"] if s["block"] < bi]
        after = [s for s in st["steps"] if s["block"] > bi]
        mine = [{"t": "intro", "block": bi}] + \
               [{"t": "set", "block": bi, "set": i} for i in range(len(done), len(b["sets"]))]
        st["steps"] = before + mine + after
        st["pos"] = len(before)
        st["advice"] = None
        if data.get("keep"):
            profile["swaps"][locations.swap_key(b["slot"], loc)] = new.id
            save_profile(profile)
        self.live.cancel()
        self._configure_live()
        self._set_phase("intro")
        self.voice.say(f"Switched to {new.name}.", key="swap", force=True)

    def _a_pause(self, data: dict) -> None:
        if not self.st.get("paused_at"):
            self.st["paused_at"] = self.clock()

    def _a_resume(self, data: dict) -> None:
        st = self.st
        if st.get("paused_at"):
            shift = self.clock() - st["paused_at"]
            if st.get("until"):
                st["until"] += shift
            st["phase_started"] += shift
            st["paused_at"] = None

    def _a_end(self, data: dict) -> None:
        if self.st["phase"] == "done":
            return
        done_all = self.st["pos"] >= len(self.st["steps"])
        self._finish("done" if done_all else "partial")

    def _a_discard(self, data: dict) -> None:
        self.live.cancel()
        session.clear_active()
        self.st = None

    def _a_close(self, data: dict) -> None:
        """Dismiss the summary screen."""
        if self.st and self.st["phase"] == "done":
            self.st = None

    # ============================================================ snapshot

    def snapshot(self) -> dict:
        with self.lock:
            st = self.st
            if st is None:
                return {"active": False}
            out = {
                "active": True,
                "id": st["id"],
                "phase": st["phase"],
                "paused": bool(st.get("paused_at")),
                "paused_at": st.get("paused_at"),
                "now": self.clock(),
                "until": st.get("until"),
                "phase_started": st.get("phase_started"),
                "started_at": st["started_at"],
                "side": st.get("side", 1),
                "pos": st["pos"],
                "total_steps": len(st["steps"]),
                "plan": {**{k: st["plan"][k] for k in ("title", "focus", "week", "phase",
                                                       "phase_text", "estimate_min", "kind",
                                                       "day_key", "notes")},
                         "location": st["plan"].get("location", locations.DEFAULT_LOCATION),
                         "location_label": st["plan"].get("location_label", "")},
                "outline": self._outline(),
                "pending": st.get("pending"),
                "advice": {k: v for k, v in (st.get("advice") or {}).items() if k != "original"}
                if st.get("advice") else None,
                "summary": st.get("summary"),
                "sets_logged": len([r for r in st["log"] if r["kind"] == "work"]),
            }
            if st["phase"] == "overview":
                out["blocks"] = self._blocks_view()
            step = self._step()
            if step is not None and st["phase"] != "done":
                out["current"] = self._step_view(step)
                nxt_pos = st["pos"] + 1
                nxt = self._step(nxt_pos)
                out["next"] = self._step_view(nxt) if nxt else None
            return out

    def _outline(self) -> list[dict]:
        """One row per block for the progress rail."""
        st = self.st
        cur = self._step()
        rows = []
        for bi, b in enumerate(st["plan"]["blocks"]):
            if b["type"] == "exercise":
                label = get_move(b["move"]).name
            else:
                label = b.get("title", b["type"].title())
            state = "todo"
            if st["phase"] == "done" or (cur and bi < cur["block"]):
                state = "done"
            elif cur and bi == cur["block"]:
                state = "current"
            rows.append({"label": label, "type": b["type"], "state": state})
        return rows

    def _blocks_view(self) -> list[dict]:
        out = []
        for b in self.st["plan"]["blocks"]:
            if b["type"] == "exercise":
                m = get_move(b["move"])
                out.append({"type": "exercise", "move": m.to_dict(), "sets": b["sets"],
                            "target": b["target"], "rest": b["rest"]})
            else:
                out.append({"type": b["type"], "title": b.get("title"),
                            "items": [{**it, "name": get_move(it["move"]).name}
                                      for it in b["items"]]})
        return out

    def _step_view(self, step: dict) -> dict:
        b = self._block(step)
        m = self._move(step)
        view = {"t": step["t"], "move": m.to_dict(), "block_type": b["type"]}
        if step["t"] == "timed":
            item = b["items"][step["item"]]
            view.update({"item": step["item"] + 1, "count": len(b["items"]),
                         "seconds": item["seconds"], "per_side": item["per_side"],
                         "block_title": b.get("title")})
            return view
        kit = profile_kit()
        work = [s for s in b["sets"] if s["kind"] == "work"]
        view.update({"target": b["target"], "rest": b["rest"], "slot": b["slot"],
                     "first_time": b.get("first_time"),
                     "options": self._options(m.id, self.st["plan"].get("location")),
                     "sets": b["sets"],
                     "work_sets": len(work)})
        if step["t"] == "set":
            s = self._set(step)
            n, total = self._work_index(step)
            view.update({"set_index": step["set"], "set": s, "work_no": n,
                         "work_total": total,
                         "loading": eq.describe_loading(kit, m.mode, s["weight"]),
                         "plates": eq.plates(kit, m.mode, s["weight"]),
                         "weight_text": eq.format_weight(m.mode, s["weight"])})
        else:
            w = work[0]["weight"] if work else None
            view.update({"loading": eq.describe_loading(kit, m.mode, w),
                         "plates": eq.plates(kit, m.mode, w),
                         "weight_text": eq.format_weight(m.mode, w)})
        return view

    @staticmethod
    def _options(move_id: str, location: str | None) -> dict:
        from .library import options
        eqp = locations.equipment(load_profile(), location)
        return {k: [{"id": m.id, "name": m.name} for m in v]
                for k, v in options(move_id, eqp).items()}
