"""Rep counting state machine and rule evaluation.

This is the only file that knows about time, phases and cue policy. Exercises
stay declarative; the engine decides when a rep happened and which cue, if
any, is worth interrupting the set for.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import geometry as g
from .exercises.base import Exercise, Phase, View
from .pose import PoseFrame
from .smoothing import Hysteresis
from .voice import Voice

# A turnaround counts as a partial rep only if the signal fell at least this
# far from where the rep started; smaller dips are tracking noise.
MIN_PARTIAL_DROP = 30.0
PARTIAL_MARGIN = 6.0


def detect_view(frame: PoseFrame) -> View:
    """Infer camera angle from how wide the shoulders read on screen.

    Face on, shoulder separation is comparable to torso length. Side on, the
    shoulders project almost on top of each other. The band between the two
    is reported as ANY, which disables the view-specific rules rather than
    guessing wrong.
    """
    if not frame.ok or not frame.visible(g.L_SHOULDER, g.R_SHOULDER, g.L_HIP, g.R_HIP):
        return View.ANY
    torso = g.torso_length(frame.px)
    if torso < 1e-3:
        return View.ANY
    shoulder_sep = float(np.linalg.norm(frame.px[g.L_SHOULDER] - frame.px[g.R_SHOULDER]))
    ratio = shoulder_sep / torso
    if ratio < 0.42:
        return View.SIDE
    if ratio > 0.78:
        return View.FRONT
    return View.ANY


@dataclass
class RepRecord:
    index: int
    duration: float
    depth: float           # lowest rep-signal value reached, 0 = deepest
    faults: list[str] = field(default_factory=list)


@dataclass
class SetState:
    reps: int = 0
    partials: int = 0
    phase: Phase = Phase.TOP
    records: list[RepRecord] = field(default_factory=list)
    fault_counts: dict[str, int] = field(default_factory=dict)


class Engine:
    def __init__(self, exercise: Exercise, voice: Voice,
                 cooldown_cap: float | None = None) -> None:
        self.ex = exercise
        self.voice = voice
        # Practice rounds cap every cue's cooldown so you get corrected often
        # while it is cheap -- without mutating the shared Rule objects.
        self.cooldown_cap = cooldown_cap
        self.state = SetState()
        self._hysteresis = {r.id: Hysteresis(on_frames=4, off_frames=8) for r in exercise.rules}
        self._rep_start_t: float | None = None
        self._rep_min_signal = 100.0
        self._top_peak = 0.0          # highest signal seen while at the top
        self._armed = False           # set once the start position is seen
        self._rep_faults: set[str] = set()
        self._reached_bottom = False
        self._descended = False
        self.view = View.ANY
        self.signal = float("nan")
        self.active_cues: list[str] = []

    # ---- rep state machine -------------------------------------------------

    def _advance_phase(self, signal: float, t: float) -> None:
        ex, st = self.ex, self.state
        prev = self.signal

        if np.isnan(signal):
            return

        descending = not np.isnan(prev) and signal < prev - 0.4
        ascending = not np.isnan(prev) and signal > prev + 0.4

        # Nothing counts until you have been seen in the start position once.
        # Walking into frame, settling under the weight, or the filter
        # converging on its first frames would otherwise score a phantom rep.
        if not self._armed:
            self._armed = signal > ex.partial_threshold + PARTIAL_MARGIN
            return

        # Transitions fire on movement direction OR on a clear change of level.
        # Direction alone misses very slow reps (a five-second negative moves
        # the signal less than the per-frame direction threshold).
        if st.phase is Phase.TOP:
            self._top_peak = max(self._top_peak, signal)
            if signal < ex.partial_threshold and (
                    descending or signal < ex.partial_threshold - 12.0):
                st.phase = Phase.DESCENDING
                self._rep_start_t = t
                self._rep_min_signal = signal
                self._rep_faults.clear()
                self._reached_bottom = False
                self._descended = True

        elif st.phase is Phase.DESCENDING:
            self._rep_min_signal = min(self._rep_min_signal, signal)
            if signal <= ex.bottom_threshold:
                st.phase = Phase.BOTTOM
                self._reached_bottom = True
            elif ascending and signal > ex.partial_threshold + PARTIAL_MARGIN:
                # Turned around early. The margin stops a wobble across the
                # partial line mid-descent being read as a turnaround, and
                # only a real attempt counts as a
                # partial: jitter around the partial line at lockout (common
                # when arms point at the camera) would otherwise nag
                # "go deeper" every few seconds.
                if self._top_peak - self._rep_min_signal >= MIN_PARTIAL_DROP:
                    self._register_partial()
                else:
                    st.phase = Phase.TOP
                    self._reset_rep()

        elif st.phase is Phase.BOTTOM:
            self._rep_min_signal = min(self._rep_min_signal, signal)
            if signal > ex.bottom_threshold + 6.0 and (
                    ascending or signal > ex.bottom_threshold + 15.0):
                st.phase = Phase.ASCENDING

        elif st.phase is Phase.ASCENDING:
            if signal >= ex.top_threshold:
                self._register_rep(t)
            elif signal <= ex.bottom_threshold:
                st.phase = Phase.BOTTOM

    def _register_rep(self, t: float) -> None:
        st = self.state
        st.reps += 1
        st.phase = Phase.TOP
        duration = (t - self._rep_start_t) if self._rep_start_t else float("nan")
        st.records.append(RepRecord(
            index=st.reps,
            duration=duration,
            depth=self._rep_min_signal,
            faults=sorted(self._rep_faults),
        ))
        clean = not self._rep_faults
        # Only call out clean reps occasionally; constant praise stops landing.
        if clean and st.reps % 5 == 0:
            self.voice.say(f"{st.reps}. Good", key="count", cooldown=2.0)
        else:
            self.voice.say(str(st.reps), key="count", cooldown=0.8)
        self._reset_rep()

    def _register_partial(self) -> None:
        st = self.state
        st.partials += 1
        st.phase = Phase.TOP
        self.voice.say(self.ex.partial_cue, key="partial", cooldown=8.0)
        self._reset_rep()

    def _reset_rep(self) -> None:
        self._rep_start_t = None
        self._rep_min_signal = 100.0
        self._top_peak = 0.0
        self._reached_bottom = False
        self._descended = False
        self._rep_faults.clear()

    # ---- rule evaluation ---------------------------------------------------

    def _evaluate_rules(self, frame: PoseFrame) -> None:
        self.active_cues = []
        violations: list[tuple[str, str, float, str]] = []

        for rule in self.ex.rules:
            hyst = self._hysteresis[rule.id]
            # A view-specific rule needs that view positively detected. An
            # ambiguous angle (ANY) abstains, as detect_view promises -- a
            # side-only check judged from a three-quarter angle is a guess.
            view_ok = rule.view is View.ANY or rule.view is self.view
            if not view_ok or not rule.applies_in(self.state.phase):
                hyst.update(False)
                continue
            raw = rule.check(frame, self.state.phase)
            if raw is None:      # abstain: not enough visibility to judge
                continue
            if hyst.update(bool(raw)):
                cooldown = rule.cooldown if self.cooldown_cap is None \
                    else min(rule.cooldown, self.cooldown_cap)
                violations.append((rule.id, rule.cue, cooldown, rule.severity))

        for rule_id, cue, cooldown, severity in violations:
            self.active_cues.append(cue)
            self._rep_faults.add(rule_id)
            self.state.fault_counts[rule_id] = self.state.fault_counts.get(rule_id, 0) + 1

        # Speak at most one cue at a time. Two voices talking over each other
        # mid-set is worse than staying quiet about the lesser fault.
        if violations:
            violations.sort(key=lambda v: 0 if v[3] == "critical" else 1)
            rule_id, cue, cooldown, _ = violations[0]
            self.voice.say(cue, key=rule_id, cooldown=cooldown)

    # ---- public ------------------------------------------------------------

    def update(self, frame: PoseFrame) -> None:
        if not self.ex.can_track(frame):
            self.active_cues = []
            self.voice.say(
                "I cannot see you properly. Step back into frame.",
                key="visibility", cooldown=10.0,
            )
            return

        self.view = detect_view(frame)
        signal = self.ex.rep_signal(frame)
        self._evaluate_rules(frame)
        self._advance_phase(signal, frame.t)
        if not np.isnan(signal):
            self.signal = signal

    def finish_set(self) -> dict:
        st = self.state
        clean = sum(1 for r in st.records if not r.faults)
        depths = [r.depth for r in st.records if not np.isnan(r.depth)]
        durations = [r.duration for r in st.records if not np.isnan(r.duration)]
        return {
            "exercise": self.ex.key,
            "reps": st.reps,
            "partials": st.partials,
            "clean_reps": clean,
            "mean_depth": float(np.mean(depths)) if depths else None,
            "best_depth": float(np.min(depths)) if depths else None,
            "mean_rep_seconds": float(np.mean(durations)) if durations else None,
            "faults": dict(st.fault_counts),
        }
