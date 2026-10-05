"""Every weight your plate set can actually make.

Thin CLI over trainer/equipment.py, which is what the app itself uses to pick
weights. Reads your saved kit from data/profile.json unless overridden.

    python scripts/loading.py
    python scripts/loading.py --rod 1.4 --connector 1.6   # after weighing
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trainer import equipment as eq            # noqa: E402
from trainer.profile import load_profile       # noqa: E402


def show(title: str, kit: eq.Kit, mode: str, note: str = "") -> None:
    weights = eq.ladder(kit, mode)
    print(f"\n{title}")
    if note:
        print(f"  {note}")
    for i in range(0, len(weights), 10):
        print("  " + "".join(f"{w:6.2f}" for w in weights[i:i + 10]))
    if len(weights) > 1:
        gaps = [round(b - a, 2) for a, b in zip(weights, weights[1:])]
        print(f"  range {weights[0]:.2f} - {weights[-1]:.2f} kg, "
              f"steps {min(gaps):.2f} - {max(gaps):.2f} kg")


def main() -> int:
    saved = load_profile()["equipment"]
    p = argparse.ArgumentParser()
    p.add_argument("--rod", type=float, default=saved.get("rod_kg"),
                   help="weight of one bare dumbbell rod, kg")
    p.add_argument("--connector", type=float, default=saved.get("connector_kg"),
                   help="weight of the connector, kg")
    p.add_argument("--screw", type=float, default=saved.get("collar_kg"),
                   help="weight of one collar/screw, kg")
    args = p.parse_args()

    kit = eq.Kit.from_dict({**saved, "rod_kg": args.rod,
                            "connector_kg": args.connector, "collar_kg": args.screw})
    plates = ", ".join(f"{n}x{w:g}kg" for w, n in kit.plates)
    print(f"plates: {kit.total_plates:.2f} kg total ({plates})")
    print(f"hardware: rod {kit.rod} kg, connector {kit.connector} kg, "
          f"collar {kit.collar} kg  <-- weigh these once")

    show("ONE dumbbell, all plates available", kit, "db1",
         "goblet squat, one-arm row, hip thrust")
    show("EACH dumbbell of a matched pair", kit, "db2",
         "bench press, curls, lunges -- pairs match in weight, not necessarily in plates")
    show("BARBELL (both rods + connector)", kit, "bb",
         "overhead press, RDL, barbell row")

    print("\nhow to load a few common weights:")
    for mode, w in (("db2", 5.7), ("db2", 9.7), ("db1", 8.2), ("bb", 14.4)):
        print(f"  {eq.format_weight(mode, w):>14s}  {eq.describe_loading(kit, mode, w)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
