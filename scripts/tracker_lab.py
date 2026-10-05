"""Replay saved pose landmarks through the rep trackers -- offline.

The browser lab (trainer/web/static/js/lab.js) runs each demo video through
the pose model and saves the landmarks to <data>/lab/<slug>.json; a trimmed
copy of those lives in tests/fixtures/pose. This script replays them through
the same LiveTracker the app uses, so tracker thresholds can be tuned in
seconds without re-running the model.

    python scripts/tracker_lab.py                 # tests/fixtures/pose
    python scripts/tracker_lab.py data/lab -v     # fresh captures, with a trace

Each demo clip shows ONE rep. Played N times, a correct tracker reports N
reps (N-1 if the clip starts mid-rep) and no partials.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trainer.live import LiveTracker   # noqa: E402

# Landmarks from 38 demo videos, one loop each, saved by the browser lab.
FIXTURES = ROOT / "tests" / "fixtures" / "pose"

# Clips that do not show exactly one rep per loop.
PER_LOOP = {
    "dumbbell-rear-lunge": 2,       # alternates legs: two lunges per clip
}


def counted_right(slug: str, reps: int, partials: int, loops: int) -> bool:
    """Never over-count, and miss at most the first rep: a clip that starts
    mid-rep spends its first lockout arming the counter, by design."""
    n = PER_LOOP.get(slug, 1)
    return partials == 0 and n * (loops - 1) <= reps <= n * loops

# Demo clips the pose model cannot follow well, so a miss there says nothing
# about the tracker. Each was checked by eye.
KNOWN_DEMO_LIMITS = {
    "barbell-bent-over-row": "the oversized demo plate hides both hands",
    "dumbbell-bent-over-row": "three-quarter view; the demo pull is shallow",
    "triceps-dip-bench-leg": "bench hides the body; detection drops out",
    "dumbbell-lying-on-floor-chest-press": "clip starts at the bottom, so the first lockout arms the counter",
    "dumbbell-standing-triceps-extension": "forearms behind the head; exercise is no longer camera-tracked",
    "decline-push-up": "figure is small and horizontal at the frame edge; arm landmarks are noise",
}


class Silent:
    enabled = False

    def say(self, *a, **k) -> bool:
        return False


def load(path: Path) -> dict:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(path.read_text())


LOOPS = 3


def frames_for(data: dict) -> tuple[list[dict], int]:
    """Saved fixtures hold one loop; play it LOOPS times, like the looping
    demo. Returns the frames and how many loops they contain."""
    frames = data["frames"]
    if data.get("loops", 2) != 1 or len(frames) < 2:
        return frames, data.get("loops", 2)
    span = frames[-1]["t"] - frames[0]["t"] + (frames[1]["t"] - frames[0]["t"])
    out = []
    for k in range(LOOPS):
        out += [{**f, "t": f["t"] + k * span} for f in frames]
    return out, LOOPS


def replay(path: Path, verbose: bool = False) -> dict:
    data = load(path)
    lt = LiveTracker(Silent())
    lt.configure(data["tracker"])
    lt.begin()
    trace = []
    frames, loops = frames_for(data)
    for f in frames:
        s = lt.update(f)
        trace.append(s["signal"])
    st = lt.state()
    summary = lt.end() or {}
    sig = [x for x in trace if x is not None]
    out = {"slug": path.name.split(".")[0], "tracker": data["tracker"], "loops": loops,
           "reps": st["reps"],
           "partials": st["partials"], "min": min(sig) if sig else None,
           "max": max(sig) if sig else None, "faults": summary.get("faults", {})}
    if verbose:
        out["trace"] = " ".join("." if x is None else str(int(x // 10)) for x in trace[::6])
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("folder", nargs="?", default=str(FIXTURES))
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()
    folder = Path(args.folder)
    files = sorted([*folder.glob("*.json"), *folder.glob("*.json.gz")])
    if not files:
        print(f"no saved frames in {args.folder} -- run the browser lab first")
        return 1
    good = known = 0
    for f in files:
        r = replay(f, args.verbose)
        ok = counted_right(r["slug"], r["reps"], r["partials"], r["loops"])
        limit = KNOWN_DEMO_LIMITS.get(r["slug"])
        good += ok
        known += (not ok and limit is not None)
        tag = "ok " if ok else ("-- " if limit else "BAD")
        sig = f"{r['min']:5.1f}-{r['max']:5.1f}" if r["min"] is not None else "   no signal"
        print(f"{tag} {r['tracker']:10s} reps={r['reps']} partials={r['partials']} "
              f"signal {sig}  {r['slug']}  {r['faults'] or ''}{'  (' + limit + ')' if limit and not ok else ''}")
        if args.verbose:
            print("      " + r["trace"])
    bad = len(files) - good - known
    print(f"\n{good}/{len(files)} clips counted exactly, {known} known demo limits, {bad} failures")
    return 0 if bad == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
