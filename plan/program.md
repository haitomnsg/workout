# Training Program — Beginner Upper/Lower, 5 days/week

> Updated 2026-10-05. The program now lives in the app (`coach.bat`), which
> picks weights, sets and progressions for you. The design reasoning is in
> [app-redesign.md](app-redesign.md). This page keeps the background:
> equipment limits, nutrition, and what to track.

**You:** 22 years old, 47 kg, 162 cm, BMI ~17.9 (underweight). 10+ pushups,
full-range bodyweight squats, no injuries. Terai region, Nepal.
**Goal:** gain muscle and bodyweight. Target ~0.25–0.4 kg/week →
roughly 52–54 kg in six months.
**Equipment:** 19 kg of plates (2 kg ×4, 1.5 kg ×4, 1.25 kg ×4), 2 dumbbell
rods, 1× 40 cm connector, **flat bench**, doorway pull-up bar, mat.

At 22 with no injuries you have the best recovery you will ever have. The
program can be more aggressive than a standard beginner template.

---

## What your equipment can actually load

Run `python scripts/loading.py` any time. The short version:

| Setup | Range | Smallest step |
|---|---|---|
| **One dumbbell** (all plates) | 1.7 – **20.7 kg** | 0.5 kg |
| **Each of a matched pair** | 1.7 – **11.2 kg** | 0.5 – 2.5 kg (only 9 weights) |
| **Barbell** (both rods + connector) | 4.9 – **23.9 kg** | 0.5 kg |

Three things fall out of this:

**The good news: 0.5 kg steps for one dumbbell and the barbell.** Mixed plate
sizes give finer jumps than most commercial sets, which matters at your
bodyweight — a 2.5 kg jump on a 10 kg lift is 25%.

**The catch: pairs jump in big steps.** A matched pair can only make 1.7,
4.2, 4.7, 5.7, 7.2, 8.2, 8.7, 9.7 and 11.2 kg each (the first version of this
page wrongly claimed 0.5 kg steps for pairs too). 5.7 → 7.2 is +26%. The app
handles this by having you build extra reps before a big jump instead of
failing the heavier weight.

**The bad news: a hard 23.9 kg ceiling, and legs hit it first.** A 22-year-old
will Romanian deadlift 40 kg+ within two months. Your barbell stops at 23.9 kg.

### Why the program is built around unilateral leg work

The naive fix is "do more reps." That is a bad fix — endless high-rep sets
with a light load are a poor stimulus and a boring way to train.

The good fix is **single-leg work**. A Bulgarian split squat loads one leg
with the weight your two hands can hold, which roughly doubles the effective
load per leg. 22.4 kg across two hands on one leg is a genuinely hard set,
and it will stay hard for over a year. So single-leg movements are the main
leg work from day one, not a later substitution.

| Lift | Your max | Outgrown in |
|---|---|---|
| Romanian deadlift (barbell) | 23.9 kg | ~6–8 weeks ← first to cap |
| Goblet squat (one DB) | 20.7 kg | ~6–10 weeks |
| Barbell back squat | 23.9 kg | ~8–12 weeks |
| Bent-over row (pair) | 22.4 kg | ~4–6 months |
| Bench press (pair) | 22.4 kg | ~5–8 months |
| Overhead press (barbell) | 23.9 kg | ~6–10 months |
| **Bulgarian split squat (pair)** | 22.4 kg | **12+ months** |
| **Single-leg RDL (pair)** | 22.4 kg | **12+ months** |

**Weigh your bare rod, connector and one screw**, then rerun with
`--rod X --connector Y --screw Z`. Every number above shifts by that amount.

---

## Schedule

Five days, Sunday to Thursday. Upper and lower alternate, so no muscle is
trained hard two days running; Friday and Saturday are rest days with a
short guided mobility routine.

| Sun | Mon | Tue | Wed | Thu | Fri | Sat |
|---|---|---|---|---|---|---|
| Upper A | Lower A | Upper B | Lower B | Arms, Shoulders & Core | Mobility A | Mobility B |

The exercises, sets and rep ranges for each day are on the app's **Plan**
page. Every session starts with a day-specific warm-up and ramp-up sets
before the first heavy lift, and ends with stretches for what you trained.

Week 1 is a learning week (2 sets, light). Weeks 2–7 build. Week 8 deloads.

**Flat bench only**, so there is no incline press. Decline push-ups (feet on
the bench) cover the upper chest instead.

---

## Progression

Double progression, steered by how each set felt. After every working set you
rate it Easy / Good / Hard / Failed:

1. Every set at the **top** of the range, none Hard or Failed → the smallest
   sensible weight step next time (two steps if everything felt Easy).
2. Inside the range → same weight, one more rep per set.
3. Below the range → hold. Well below, or repeated failures → about 10% lighter.
4. Stuck for three sessions → deload 10% and build back up.

Within a session, an Easy first set at the top of the range bumps the next
set up, and a Failed set brings it down. Starting weights are estimates; the
first set of a new exercise is effectively a calibration set.

---

## Nutrition

You gave me your actual diet, so here is what to change rather than a
generic plan. Current intake looks like roughly **1,900–2,100 kcal and
55–60 g protein**. Targets: **2,300–2,500 kcal, 75–95 g protein**.

**Your breakfast is the weak link.** Milk with biscuits or cookies is nearly
all refined carbohydrate and almost no protein — and it is the meal where you
have the most room to improve. Everything else you eat is genuinely fine.

### Three changes, in priority order

**1. Add 3 eggs to breakfast.** `+18 g protein, +210 kcal`
Single biggest fix available. Boiled, omelette, however you like them.
Keep the milk; swap most of the biscuits for the eggs.

**2. Add 500 ml more milk across the day.** `+16 g protein, +300 kcal`
Liquid calories are far easier to get down than another plate of rice, and
appetite — not access — is your real obstacle at 47 kg.

**3. Swap daytime biscuit snacks for roasted chana or peanuts.**
`+8 g protein, +100 kcal net`
Same convenience, dramatically better macros.

That lands you around **2,400 kcal and 95 g protein**. Do these for two
weeks and check the scale before adding anything else.

### Already good — keep doing it

Dal bhat with vegetables and salad, roti, and evening meat/eggs/mutton is a
solid base. Two easy upgrades within what you already eat:
- Take a **second serving of dal** at lunch (+9 g protein)
- Add a **teaspoon of ghee** to your dal (+45 kcal, no effort, no volume)

### Supplements

- **Creatine monohydrate, 3–5 g/day**, any time, with water. No loading
  phase. Most evidence-backed supplement that exists, and cheap. Expect
  1–2 kg of scale weight in the first weeks that is water, not muscle —
  do not let it confuse your weekly tracking.
- **Whey**: only to fill a gap on days you miss protein. Food first. With
  the three changes above you may not need it at all.

### Sleep

7–9 hours. More important than any supplement, and free.

---

## Tracking

The app logs every set to `data/sets.jsonl`. Alongside that, weekly:

- **Bodyweight** — same time, same conditions, once a week. This is the
  primary metric. If it is not moving, nothing else matters.
- **Working weight** for each main lift.

| What you see | What it means |
|---|---|
| Weight ↑, lifts ↑ | Working. Change nothing. |
| Lifts ↑, weight flat | Eat more — add ~200 kcal/day |
| Both flat | Check sleep, and check you are actually hitting 3 sessions |
| Weight ↑ fast (>0.6 kg/wk) | Too much surplus — pull back slightly |

---

## Month 3–4: buy more plates

Around then, squats and RDLs will be capped. Another ~20 kg of plates is
cheap and roughly doubles your runway on every barbell lift. Budget for it
now so it is not a surprise.
