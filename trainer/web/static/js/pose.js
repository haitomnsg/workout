// In-browser pose detection.
//
// Windows Smart App Control blocks MediaPipe's native DLL, so the model runs
// here instead, as WebAssembly (with WebGL acceleration where available). It
// is the same BlazePose model the Python app used, loaded from /models. Each
// frame's 33 landmarks are posted to the Python rep engine, which answers
// with the rep count and any form cue.

import { FilesetResolver, PoseLandmarker } from "/static/vendor/tasks-vision/vision_bundle.mjs";

const EDGES = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16], [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [27, 31], [27, 29], [29, 31], [24, 26], [26, 28], [28, 32], [28, 30], [30, 32],
];

let cached = { model: null, promise: null };

function landmarker(model) {
  if (cached.promise && cached.model === model) return cached.promise;
  cached.model = model;
  cached.promise = (async () => {
    const files = await FilesetResolver.forVisionTasks("/static/vendor/tasks-vision/wasm");
    const opts = (delegate) => ({
      baseOptions: { modelAssetPath: `/models/pose_landmarker_${model}.task`, delegate },
      runningMode: "VIDEO",
      numPoses: 1,
      minPoseDetectionConfidence: 0.6,
      minPosePresenceConfidence: 0.6,
      minTrackingConfidence: 0.6,
    });
    try {
      return await PoseLandmarker.createFromOptions(files, opts("GPU"));
    } catch (err) {
      console.warn("GPU pose delegate unavailable, falling back to CPU:", err);
      return await PoseLandmarker.createFromOptions(files, opts("CPU"));
    }
  })();
  cached.promise.catch(() => { cached = { model: null, promise: null }; });
  return cached.promise;
}

export class PoseCamera {
  constructor(onState) {
    this.onState = onState;
    this.el = document.createElement("div");
    this.el.className = "cam";
    this.video = document.createElement("video");
    this.video.muted = true;
    this.video.playsInline = true;
    this.canvas = document.createElement("canvas");
    this.el.append(this.video, this.canvas);
    this.ctx = this.canvas.getContext("2d");
    this.status = "idle";        // idle | starting | running | error
    this.error = "";
    this.state = null;
    this.source = null;
    this.running = false;
    this.inflight = false;
    this.lastVideoTime = -1;
    this.lastTs = 0;
    this.frames = 0;
    this.fps = 0;
    this._fpsT = performance.now();
    // Browsers pause muted media to save power when the window is hidden;
    // pick straight back up so tracking does not silently stop.
    this.video.addEventListener("pause", () => {
      if (this.running) this.video.play().catch(() => {});
    });
    document.addEventListener("visibilitychange", () => {
      if (this.running && this.video.paused) this.video.play().catch(() => {});
    });
  }

  async _play() {
    for (let i = 0; i < 20; i++) {
      try {
        await this.video.play();
        return;
      } catch (err) {
        if (err?.name === "NotAllowedError" || err?.name === "NotSupportedError") throw err;
        await new Promise((r) => setTimeout(r, 500));     // interrupted; try again
      }
    }
    throw new Error("The video would not start. Bring this window to the front and press C twice to retry.");
  }

  setMirror(on) { this.el.classList.toggle("mirror", !!on); }

  async start({ source = "webcam", model = "full" } = {}) {
    if (this.running && this.source === source) return;
    this.stop();
    this.source = source;
    this.status = "starting";
    this.error = "";
    try {
      if (source === "webcam") {
        if (!navigator.mediaDevices?.getUserMedia) throw new Error("This browser cannot access a camera.");
        this.stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" }, audio: false,
        });
        this.video.srcObject = this.stream;
        this.video.loop = false;
      } else {
        this.video.srcObject = null;
        this.video.src = source;
        this.video.loop = true;
      }
      await this._play();
      this.model = await landmarker(model);
      if (this.source !== source) return;      // superseded while loading
      this.running = true;
      this.status = "running";
      this._loop();
    } catch (err) {
      this.failedSource = source;
      this.status = "error";
      this.error = err?.name === "NotAllowedError"
        ? "Camera permission was blocked. Allow the camera for this page in the browser's address bar."
        : err?.name === "NotFoundError" ? "No camera found." : (err?.message || String(err));
      this.stop(false);
    }
  }

  stop(resetStatus = true) {
    this.running = false;
    if (this.stream) this.stream.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.video.pause();
    this.video.removeAttribute("src");
    this.video.srcObject = null;
    this.source = null;
    this.state = null;
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    if (resetStatus) this.status = "idle";
  }

  _loop() {
    // A timer, not requestAnimationFrame: rAF stops whenever the window is
    // not being painted (covered by another window), which would freeze
    // rep counting mid-set. The currentTime check skips duplicate frames.
    const step = () => {
      if (!this.running) return;
      const v = this.video;
      if (v.readyState >= 2 && v.currentTime !== this.lastVideoTime) {
        this.lastVideoTime = v.currentTime;
        let ts = performance.now();
        if (ts <= this.lastTs) ts = this.lastTs + 1;
        this.lastTs = ts;
        try {
          this._handle(this.model.detectForVideo(v, ts), ts);
        } catch (err) {
          console.error("pose detection failed", err);
        }
        this.frames++;
        const now = performance.now();
        if (now - this._fpsT > 1000) {
          this.fps = (this.frames * 1000) / (now - this._fpsT);
          this.frames = 0;
          this._fpsT = now;
        }
      }
      setTimeout(step, 12);
    };
    setTimeout(step, 0);
  }

  _handle(res, ts) {
    const v = this.video;
    const W = v.videoWidth, H = v.videoHeight;
    const lms = res?.landmarks?.[0];
    const world = res?.worldLandmarks?.[0];
    const payload = { t: ts / 1000, ok: !!(lms && world) };
    if (payload.ok) {
      payload.px = lms.flatMap((p) => [p.x * W, p.y * H]);
      payload.world = world.flatMap((p) => [p.x, p.y, p.z]);
      payload.vis = lms.map((p) => p.visibility ?? 0);
    }
    this._draw(lms, W, H);
    if (this.inflight) return;
    this.inflight = true;
    fetch("/api/pose", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })
      .then((r) => r.json())
      .then((s) => { this.state = s; this.onState?.(s); })
      .catch(() => {})
      .finally(() => { this.inflight = false; });
  }

  _draw(lms, W, H) {
    const c = this.canvas, ctx = this.ctx;
    if (c.width !== W || c.height !== H) { c.width = W; c.height = H; }
    ctx.clearRect(0, 0, W, H);
    if (!lms) return;
    const s = this.state;
    const colour = s?.cues?.length ? "#ef4444" : (s && s.want_view !== "any" && !s.view_ok) ? "#f59e0b" : "#22c55e";
    const lw = Math.max(3, W / 240);
    ctx.lineWidth = lw;
    ctx.lineCap = "round";
    ctx.strokeStyle = colour;
    for (const [a, b] of EDGES) {
      const p = lms[a], q = lms[b];
      if ((p.visibility ?? 1) < 0.5 || (q.visibility ?? 1) < 0.5) continue;
      ctx.beginPath();
      ctx.moveTo(p.x * W, p.y * H);
      ctx.lineTo(q.x * W, q.y * H);
      ctx.stroke();
    }
    ctx.fillStyle = "#ffffff";
    for (let i = 11; i < 33; i++) {
      const p = lms[i];
      if ((p.visibility ?? 1) < 0.5) continue;
      ctx.beginPath();
      ctx.arc(p.x * W, p.y * H, lw * 1.2, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}
