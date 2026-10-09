# WorkOut: a personal trainer that runs on your laptop

A guided, adaptive training program for your adjustable dumbbells (and the
barbell you build from them), with a webcam coach that counts reps and
checks form. It runs entirely offline on your own machine.

## Setup (once, after cloning)

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python scripts/download_models.py
```

Demo videos come from a local copy of the Asterisk exercise library (path set in
`trainer/catalog.py`). Without it the app still works, but shows instructions only.

## Start

Double-click **`coach.bat`**. Your browser opens the app. Keep the black window open while
you train, and close it when you are done.

Each day the app tells you what to do and how heavy to go, then walks you through it:

```
Warm-up (hands-free timer) -> for each exercise:
   intro: demo video, how to do it, the weight, which plates to load, where to stand
   sets:  camera counts your reps and calls out form faults
   rest:  rate the set, and the next set adjusts; countdown to the next one
-> Cool-down stretches -> Summary
```

| Key | During a workout |
|-----|------------------|
| `Space` | the main action: start, done, next |
| `1` `2` `3` `4` | rate the set: Easy, Good, Hard, Failed |
| `+` / `-` | fix the rep count |
| `[` / `]` | lighter / heavier for the next set |
| `N` / `R` | skip rest / add 30 s |
| `P` `V` `C` `F` | pause, voice, camera, full screen |
| `Esc` | end the workout (what you did is saved) |

## The program

Five days a week, Sunday to Thursday, with the upper and lower body alternating:

| Sun | Mon | Tue | Wed | Thu | Fri | Sat |
|---|---|---|---|---|---|---|
| Upper A | Lower A | Upper B | Lower B | Arms, Shoulders & Core | Mobility A | Mobility B |

**Where you train.** Before you start, pick a place on the Today page:

| Place | What it uses |
|---|---|
| **Home, with dumbbells** | the full program: dumbbells, barbell, bench, pull-up bar |
| **No dumbbells** | bodyweight, with a sturdy chair (split squats, dips, step-ups) and a table to row under |
| **Just the floor** | bodyweight with only a floor, a wall, a door and a towel |

The days, order and set counts stay the same. Only the moves change, and each bodyweight
move has its own rep range. Top the range on every set and the app offers the next harder
variation, but only one you can do at that place. Swaps you keep are saved per place, and the
Plan page shows the week for each place. Settings → *Training without dumbbells* lists what
each away place has.

Week 1 is a learning week with 2 sets and light weights. Weeks 2-7 build, and week 8 is a
deload. Then the cycle repeats. Full reasoning: [plan/app-redesign.md](plan/app-redesign.md).

**Progression.** Rate every working set. Hit the top of the rep range on every set and the
weight goes up next time. Inside the range, same weight and one more rep. Fail repeatedly
and it backs off. An easy first set bumps the second set up within the same session.

Weights only ever come from what your plates can actually make (see the Plan page). Weigh
your bare rod, connector and one collar once and enter them in **Settings**, because every
recommended weight depends on them.

## Why pose detection runs in the browser

Windows **Smart App Control** blocks MediaPipe's native DLL (`WinError 4551`), so the
original OpenCV coach cannot start on this machine. The app runs the same BlazePose model
in the browser instead (WebAssembly with WebGL acceleration), which Smart App Control does
not affect. Landmarks are posted to the Python rep engine, so the engine, rules and tests
are unchanged.

```
browser: webcam -> MediaPipe WASM -> 33 landmarks --POST--> python: One Euro filter -> rep engine -> cues
```

The first time you start a camera-tracked exercise, the browser asks for camera
permission. Choose Allow. The camera turns on only during tracked exercises.

## Camera tracking

Rep counters exist for squats, bench and floor press, rows, overhead presses, curls,
triceps extensions, lateral raises, Romanian deadlifts, split squats and lunges, hip thrusts
and bridges, push-ups, pull-ups and hanging knee raises. The camera count is a suggestion:
you confirm reps when you rate the set.

Each was checked against the demo videos with the tracker lab:

```js
// in the browser console on the app page
const lab = await import("/static/js/lab.js");
await lab.run([["dumbbell-goblet-squat", "squat"]]);
```

**Test mode** (Settings) feeds the demo video to the rep counter instead of your webcam.

## Layout

```
trainer/
  web/           Flask app, UI (static/), in-browser pose (static/js/pose.js)
  runner.py      the guided-workout state machine
  plan.py        the 5-day program, warm-ups, cool-downs, time estimates
  progression.py weight and rep recommendations
  equipment.py   what your plates can load, and how to load it
  library/       96 movements with English instructions and alternatives
  live.py        landmarks from the browser -> smoothing -> rep engine
  engine.py      rep state machine, view detection, cue policy
  exercises/     one tracker per movement family
  session.py     logs: data/sets.jsonl, data/sessions.jsonl
  profile.py     your settings: data/profile.json
  nutrition.py   calorie and protein targets, Nepali-food meal guide
  main.py        single-exercise OpenCV mode (needs Smart App Control off)
```

## Other commands

```
python tests/test_trainer.py         plates, progression, program, runner, API
python tests/test_core.py            geometry, smoothing, rep counting
python scripts/loading.py            every weight your plates can make
python -m trainer.nutrition --plan   today's eating, as a full sample day
python -m trainer.web --data-dir X   a trial run that never touches your real log
```

`scripts/smoke_test.py`, `scripts/camera_check.py` and `trainer.main` use the native
MediaPipe build, so they only work if Smart App Control is turned off.

The original version of the source is in `backup/original-2026-10-05.zip`.
