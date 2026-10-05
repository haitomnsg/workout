# WorkOut 2.0: from exercise viewer to personal trainer

Written 2026-10-05 from your answers. This is the design the code follows.

## What you told me

| | |
|---|---|
| Goal | Build muscle + gain bodyweight (22 y, 47 kg, 162 cm) |
| Schedule | 5 days x 60 min, **Sun-Thu**, rest Fri + Sat |
| Split | Upper A / Lower A / Upper B / Lower B / Arms-Shoulders-Core |
| Level | Beginner: 10 push-ups, no pull-up yet, no injuries |
| Equipment | Unchanged: 4x2 + 4x1.5 + 4x1.25 kg plates, 2 rods, connector, flat bench, pull-up bar, mat |
| Progression | Smart auto: rate each set Easy / Good / Hard / Failed |
| Camera | Rep counting + form checks on as many lifts as possible |
| UI | Local web app in the browser, keyboard + mouse |
| Extras | Rest-day mobility routine, nutrition targets |

## A problem found while exploring

**Windows Smart App Control is on and blocks MediaPipe's native DLL**
(`WinError 4551`). The old OpenCV coach cannot start on this machine any more.
Turning Smart App Control off would fix it, but it is a security setting and
on most Windows builds it cannot be turned back on without a reinstall.

So the new app runs pose detection **in the browser** with MediaPipe's
WebAssembly build. Smart App Control does not apply there. It uses the same
BlazePose model files already in `models/`, with GPU acceleration through
WebGL, which the Windows Python build never had. The browser sends the 33
landmarks to the existing Python rep engine. `engine.py`, `geometry.py`,
`smoothing.py` and the exercise rules are unchanged in spirit and still unit
tested.

## Architecture

```
browser                                    python (Flask, 127.0.0.1 only)
-------                                    ------------------------------
webcam -> MediaPipe WASM -> landmarks --->  live.py      smoothing -> Engine (reps, form cues)
           canvas skeleton overlay  <---    runner.py    workout state machine, timers, voice
UI: Today / Workout / Plan / Progress /     plan.py      5-day program, warm-ups, cool-downs
    Library / Nutrition / Settings          progression.py  weight + rep recommendations
                                            equipment.py    what your plates can load, how to load it
                                            library/        ~90 exercises with English instructions
                                            session.py      set + session logs (JSONL)
                                            profile.py      your settings
```

## The training program

Weekly, every muscle trained about twice:

| Day | Workout | Main lifts |
|---|---|---|
| Sun | Upper A | DB bench press, bent-over DB row, barbell overhead press, pull-up negatives, lateral raise |
| Mon | Lower A | Goblet squat, barbell RDL, DB reverse lunge, DB hip thrust, calf raise, plank |
| Tue | Upper B | Push-ups, one-arm DB row, seated DB press, pull-up negatives, rear-delt fly, DB fly |
| Wed | Lower B | Bulgarian split squat, single-leg RDL, step-up, single-leg hip thrust, calf raise, hanging knee raise |
| Thu | Arms, Shoulders & Core | Curls, overhead triceps extension, hammer curls, bench dips, lateral raise, dead bug, side plank |
| Fri | Rest | Mobility A: hips and legs, 15 min |
| Sat | Rest | Mobility B: spine and shoulders, 15 min, plus an optional easy walk |

Every session: warm-up (about 6 min, specific to the day) -> ramp-up sets
before the first heavy lift -> working sets -> cool-down stretches for the
muscles you trained (about 5 min). The estimated time is shown before you
start and is kept around 60 minutes.

**Weeks.** Week 1 is a learning week: 2 sets per exercise, lighter, with a
coached practice round on camera-tracked lifts. Weeks 2-7 are normal. Week 8
is a deload (one fewer set, 10% lighter), then the cycle repeats.

## Smart progression

After each set you rate it: **Easy** (4+ reps left), **Good** (2-3 left),
**Hard** (1 left), **Failed** (could not finish).

*Within a session:* if set 1 is Easy and you hit the top of the rep range,
the next set goes up. If you fail or fall short of the range, it comes down.
The rest screen tells you the new weight and exactly which plates to load.

*Between sessions* (double progression, informed by the ratings):
- Every set at the top of the range, none Hard or Failed -> add the smallest
  sensible step (about 2.5% for upper body, 5% for legs). Two steps if every
  set was Easy.
- Inside the range -> same weight, aim for +1 rep per set.
- Below the range or Failed -> hold the weight. Stalled 2 sessions in a row ->
  drop 10% and build back up.
- Bodyweight moves add reps, then the app suggests the next harder variation
  (incline push-up -> push-up -> decline -> deficit).
- When your plates max out on a lift, the app switches to adding reps or a
  slower lowering phase, and tells you it is time to buy more plates.

Weights are only ever ones your plates can actually make. Pairs are solved
properly: two dumbbells can match in weight with different plate combinations,
which opens up more steps than the old calculator assumed.

## The guided workout

`Overview -> Warm-up (timed, hands-free) -> per exercise: Intro (video, how-to,
weight, plate loading, where to stand) -> Set (camera counts reps, voice form
cues) -> Done -> Rate + Rest (countdown, next-set advice) -> ... ->
Cool-down -> Summary`

- **Space** is always the main action (start / done / next). Keys **1-4** rate
  the set, **+/-** fix the rep count, **[ ]** change the weight, **N** skips
  rest.
- "Too hard?" offers an easier variation; "Swap" offers alternatives. A swap
  can be kept for future weeks.
- Per-side moves count each side separately, with a "switch sides" prompt.
- Holds (planks) get a countdown.
- If you close the browser mid-workout, it resumes where you left off.

## Camera rep tracking

The existing trackers are squat, bench and row. New ones:

| Tracker | Covers |
|---|---|
| overhead press | barbell/DB press, Arnold press |
| curl | DB curl, hammer, barbell, concentration |
| triceps | overhead extension, skull crusher, bench dip |
| lateral raise | lateral raise |
| hinge | barbell/DB RDL, single-leg RDL |
| lunge | split squat, Bulgarian split squat, reverse lunge |
| bridge | hip thrust, glute bridge (both + single-leg) |
| push-up | all push-up variants, with a sagging-hips check |
| pull-up | pull-ups, chin-ups, negatives |
| knee raise | hanging knee raise |

The camera count is a suggestion. You confirm reps when you rate the set, so
the log stays accurate even if tracking misses one.

## Other screens

- **Today**: this week's strip, today's plan with recommended weights and
  their reasons, catch-up for missed days, rest-day mobility, nutrition target.
- **Plan**: the week, the cycle, how progression works, what your plates can load.
- **Progress**: consistency, per-exercise strength charts (estimated 1RM),
  personal records, session history.
- **Library**: every exercise, filterable, with demo video, steps, cues,
  common mistakes, and easier/harder alternatives.
- **Nutrition**: daily targets from your bodyweight, plus the existing
  Nepali-food guidance and sample day.
- **Settings**: profile, training days, plates and bar weights, camera model,
  voice.

## Kept, changed, removed

- Kept: pose geometry, smoothing, engine, exercise rules, voice, catalog,
  nutrition data, `trainer.main` (single-exercise OpenCV mode, which works
  again if Smart App Control is ever turned off).
- Changed: `session.py` (richer logs, reads the old format), `nutrition.py`
  (reads your profile), `scripts/loading.py` (uses the new equipment solver).
  `coach.bat` now opens the web app.
- Removed: `trainer/coach.py` and `trainer/program.py`, replaced by
  `runner.py` and `plan.py`. The original source is in
  `backup/original-2026-10-05.zip`.
