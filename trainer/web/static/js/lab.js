// Tracker lab: runs the demo videos through the in-browser pose model and
// the Python rep counters, to check thresholds without anyone exercising.
//
// From the browser console on the app page:
//   const lab = await import("/static/js/lab.js");
//   await lab.run([["dumbbell-goblet-squat", "squat"]]);
//
// Frames are produced by seeking, not playback, so it works even when the
// window is in the background. Each clip is fed twice, like the looping demo.

import { FilesetResolver, PoseLandmarker } from "/static/vendor/tasks-vision/vision_bundle.mjs";

let model;
// MediaPipe requires timestamps to increase across EVERY call on a graph,
// not just within one clip -- one module-wide clock.
let clock = performance.now();

async function getModel(name = "full") {
  if (model) return model;
  const files = await FilesetResolver.forVisionTasks("/static/vendor/tasks-vision/wasm");
  model = await PoseLandmarker.createFromOptions(files, {
    baseOptions: { modelAssetPath: `/models/pose_landmarker_${name}.task`, delegate: "GPU" },
    runningMode: "VIDEO", numPoses: 1,
  });
  return model;
}

async function framesFor(slug, loops = 2, fps = 30) {
  const lm = await getModel();
  const v = document.createElement("video");
  v.muted = true;
  v.preload = "auto";
  v.src = `/media/video/${slug}`;
  await new Promise((res, rej) => { v.onloadeddata = res; v.onerror = rej; });
  const W = v.videoWidth, H = v.videoHeight, dur = v.duration;
  const frames = [];
  for (let loop = 0; loop < loops; loop++) {
    for (let t = 0; t < dur - 1e-3; t += 1 / fps) {
      v.currentTime = t;
      await new Promise((r) => { v.onseeked = r; });
      clock += 1000 / fps;
      const ts = clock;
      const res = lm.detectForVideo(v, ts);
      const p = res.landmarks?.[0], w = res.worldLandmarks?.[0];
      frames.push(p && w
        ? { t: ts / 1000, ok: true, px: p.flatMap((q) => [q.x * W, q.y * H]),
            world: w.flatMap((q) => [q.x, q.y, q.z]), vis: p.map((q) => q.visibility ?? 0) }
        : { t: ts / 1000, ok: false });
    }
  }
  return { frames, dur };
}

export async function run(cases, loops = 2) {
  const out = [];
  for (const [slug, tracker] of cases) {
    try {
      const { frames, dur } = await framesFor(slug, loops);
      const r = await fetch("/api/lab", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tracker, frames, save: slug }),
      }).then((x) => x.json());
      const seen = frames.filter((f) => f.ok).length;
      out.push({ slug, tracker, seconds: +(dur * loops).toFixed(1), detected: `${Math.round((100 * seen) / frames.length)}%`,
                 reps: r.reps, partials: r.partials, signal: [r.signal_min, r.signal_max], views: r.views, faults: r.faults });
    } catch (e) {
      model = null;           // a failed graph stays failed; rebuild it
      out.push({ slug, tracker, error: String(e).slice(0, 200) });
    }
  }
  return out;
}
