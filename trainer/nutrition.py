"""Daily eating guidance, built on Terai Nepali food.

The Asterisk recipe database has 311k recipes with full nutrition, but all of
them are Italian. Rather than pretend risotto is relevant, this is a small
hand-built table of what is actually on the table in a Nepali household, plus
the arithmetic that turns it into a day's target.

Small on purpose: forty foods you eat beats 311,000 you never will.

    python -m trainer.nutrition
    python -m trainer.nutrition --plan
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date

# Fallbacks only -- the app reads your current stats from data/profile.json
# (Settings screen), so update your bodyweight there as it changes.
BODYWEIGHT_KG = 47.0
HEIGHT_CM = 162.0
AGE = 22

PROTEIN_PER_KG = 1.8          # 1.6-2.0 is the useful band for muscle gain
SURPLUS_KCAL = 350            # ~0.3 kg/week


def _stats(profile: dict | None) -> tuple[float, float, float, str]:
    if profile is None:
        try:
            from .profile import load_profile
            profile = load_profile()
        except Exception:
            profile = {}
    return (float(profile.get("bodyweight_kg", BODYWEIGHT_KG)),
            float(profile.get("height_cm", HEIGHT_CM)),
            float(profile.get("age", AGE)),
            profile.get("sex", "male"))


@dataclass(frozen=True)
class Food:
    name: str
    serving: str
    kcal: int
    protein: float
    note: str = ""


# Per typical household serving, not per 100 g -- you eat servings, not grams.
FOODS: list[Food] = [
    # staples
    Food("Bhat (cooked rice)", "1 cup", 205, 4.3),
    Food("Dal (lentil soup)", "1 cup", 180, 9.0, "take a second serving"),
    Food("Roti", "1 medium", 120, 3.5),
    Food("Vegetable curry (tarkari)", "1 cup", 130, 3.0),
    Food("Aloo (potato) curry", "1 cup", 180, 3.5),
    # protein
    Food("Egg, boiled or fried", "1 egg", 70, 6.0, "cheapest reliable protein"),
    Food("Chicken curry", "100 g", 190, 25.0),
    Food("Mutton curry", "100 g", 250, 24.0),
    Food("Buff (buffalo) curry", "100 g", 180, 26.0),
    Food("Fish curry", "100 g", 170, 22.0),
    Food("Paneer", "50 g", 145, 9.0),
    Food("Soybean (bhatmas)", "50 g dry", 190, 18.0),
    # dairy
    Food("Whole milk", "250 ml", 150, 8.0, "easiest calories to add"),
    Food("Curd (dahi)", "1 cup", 150, 10.0),
    Food("Lassi", "1 glass", 260, 8.0, "liquid calories go down easy"),
    Food("Ghee", "1 tsp", 45, 0.0, "add to dal, zero effort"),
    # snacks
    Food("Roasted chana", "50 g", 180, 10.0, "better than biscuits"),
    Food("Peanuts", "handful (30 g)", 170, 7.5),
    Food("Banana", "1 medium", 105, 1.3),
    Food("Chiura (beaten rice)", "1 cup", 220, 4.5),
    Food("Sel roti", "1 piece", 200, 3.0),
    Food("Biscuits / cookies", "4 pieces", 180, 2.5, "swap these out"),
    # supplements
    Food("Whey protein", "1 scoop", 120, 24.0, "only to fill a gap"),
    Food("Creatine monohydrate", "5 g", 0, 0.0, "daily, any time, with water"),
]

BY_NAME = {f.name.lower(): f for f in FOODS}


def maintenance_kcal(profile: dict | None = None) -> float:
    """Mifflin-St Jeor. Activity factor 1.55: five training days a week."""
    bw, height, age, sex = _stats(profile)
    bmr = 10 * bw + 6.25 * height - 5 * age + (5 if sex == "male" else -161)
    return bmr * 1.55


def targets(profile: dict | None = None) -> tuple[int, int]:
    bw = _stats(profile)[0]
    kcal = round(maintenance_kcal(profile) + SURPLUS_KCAL)
    protein = round(bw * PROTEIN_PER_KG)
    return kcal, protein


# The three changes that matter, in priority order. Deliberately additive:
# telling someone to overhaul their whole diet is how they change nothing.
PRIORITY_CHANGES = [
    ("Add 3 eggs at breakfast",
     "Milk and biscuits is nearly all refined carbohydrate. This is the single "
     "biggest fix available to you.", 210, 18.0),
    ("Add 500 ml more milk across the day",
     "Appetite is your obstacle, not access. Liquid calories go down far more "
     "easily than another plate of rice.", 300, 16.0),
    ("Swap daytime biscuits for roasted chana or peanuts",
     "Same convenience, dramatically better macros.", 100, 8.0),
]

TRAINING_DAY_NOTES = [
    ("Before training (60-90 min)",
     "Something with carbohydrate: chiura, a banana, or rice. Do not train "
     "on an empty stomach at your bodyweight."),
    ("After training (within ~2 hours)",
     "Your largest protein meal of the day. Dal bhat with eggs or meat is "
     "exactly right — no special post-workout window panic needed."),
    ("Creatine", "5 g, any time. Consistency matters, timing does not."),
]

REST_DAY_NOTES = [
    ("Eat the same as a training day",
     "Muscle is built on rest days. Cutting calories because you did not "
     "train is the most common way beginners stall."),
    ("Protein spread across meals",
     "Aim for 20-25 g at each of four points in the day rather than one "
     "large hit at dinner."),
]


def daily_brief(training_day: bool = True, profile: dict | None = None) -> str:
    kcal, protein = targets(profile)
    lines = [
        "",
        "--- today's eating ---",
        f"  target: {kcal} kcal, {protein} g protein "
        f"(bodyweight {_stats(profile)[0]:.0f} kg)",
        "",
        "  priority changes:",
    ]
    for i, (what, _why, k, p) in enumerate(PRIORITY_CHANGES, 1):
        lines.append(f"    {i}. {what}  (+{k} kcal, +{p:.0f} g protein)")

    lines.append("")
    for title, body in (TRAINING_DAY_NOTES if training_day else REST_DAY_NOTES):
        lines.append(f"  {title}:")
        lines.append(f"    {body}")
    return "\n".join(lines)


def sample_day() -> list[tuple[str, list[tuple[Food, float]]]]:
    """A concrete day that hits the target, using food already in the house."""
    def f(name: str) -> Food:
        return BY_NAME[name.lower()]

    return [
        ("Breakfast", [
            (f("Whole milk"), 1), (f("Egg, boiled or fried"), 3),
            (f("Chiura (beaten rice)"), 1),
        ]),
        ("Mid-morning", [(f("Roasted chana"), 1)]),
        ("Lunch", [
            (f("Bhat (cooked rice)"), 2), (f("Dal (lentil soup)"), 1),
            (f("Vegetable curry (tarkari)"), 1), (f("Ghee"), 1),
        ]),
        ("Afternoon", [(f("Curd (dahi)"), 1), (f("Banana"), 1)]),
        ("Dinner", [
            (f("Roti"), 2), (f("Chicken curry"), 1),
            (f("Vegetable curry (tarkari)"), 1),
        ]),
        ("Before bed", [(f("Whole milk"), 1)]),
    ]


def as_dict(training_day: bool = True, profile: dict | None = None) -> dict:
    """Everything the Nutrition screen shows."""
    kcal, protein = targets(profile)
    meals = []
    total_k = total_p = 0.0
    for meal, items in sample_day():
        rows = [{"name": f.name, "qty": f"{n:g} x {f.serving}", "kcal": round(f.kcal * n),
                 "protein": round(f.protein * n, 1), "note": f.note} for f, n in items]
        mk, mp = sum(r["kcal"] for r in rows), sum(r["protein"] for r in rows)
        total_k += mk
        total_p += mp
        meals.append({"meal": meal, "items": rows, "kcal": mk, "protein": round(mp)})
    notes = TRAINING_DAY_NOTES if training_day else REST_DAY_NOTES
    return {
        "kcal": kcal, "protein": protein, "bodyweight": _stats(profile)[0],
        "training_day": training_day,
        "changes": [{"what": w, "why": y, "kcal": k, "protein": p}
                    for w, y, k, p in PRIORITY_CHANGES],
        "notes": [{"title": t, "body": b} for t, b in notes],
        "sample_day": meals, "sample_kcal": round(total_k), "sample_protein": round(total_p),
        "foods": [{"name": f.name, "serving": f.serving, "kcal": f.kcal,
                   "protein": f.protein, "note": f.note} for f in FOODS],
    }


def print_plan() -> None:
    kcal_t, protein_t = targets()
    total_k = total_p = 0.0
    print(f"\nsample day -- target {kcal_t} kcal, {protein_t} g protein\n")
    for meal, items in sample_day():
        mk = sum(f.kcal * n for f, n in items)
        mp = sum(f.protein * n for f, n in items)
        total_k += mk
        total_p += mp
        print(f"  {meal}  ({mk:.0f} kcal, {mp:.0f} g protein)")
        for food, n in items:
            qty = f"{n:g} x {food.serving}"
            note = f"   <- {food.note}" if food.note else ""
            print(f"      {food.name:30s} {qty:18s}"
                  f"{food.kcal * n:5.0f} kcal  {food.protein * n:4.0f} g{note}")
        print()
    print(f"  TOTAL  {total_k:.0f} kcal, {total_p:.0f} g protein")
    dk, dp = total_k - kcal_t, total_p - protein_t
    print(f"  vs target: {dk:+.0f} kcal, {dp:+.0f} g protein")
    if abs(dk) < 200 and dp > -5:
        print("  -> on target")
    elif dk >= 200:
        print("  -> over: trim a serving of rice or the bedtime milk")
    else:
        print("  -> under: add a glass of milk or a second serving of dal")
    if dp > 25:
        print("     protein runs above target, which is fine -- it leaves "
              "margin on days you eat less")


def main() -> int:
    p = argparse.ArgumentParser(description="Daily nutrition guidance")
    p.add_argument("--plan", action="store_true", help="print a full sample day")
    p.add_argument("--rest-day", action="store_true")
    args = p.parse_args()

    print(daily_brief(training_day=not args.rest_day))
    if args.plan:
        print_plan()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
