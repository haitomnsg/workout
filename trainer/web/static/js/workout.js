// The guided workout player.
//
// The server owns the state machine (trainer/runner.py); this file polls it,
// renders whatever phase it is in, and sends actions. Space is always the
// main action, so a whole session can be run from one key.

import {
  $, esc, api, post, toast, icon, fmtClock, fmtWeight, RATINGS, STATUS_LABEL,
  prescription, thumbURL, videoURL, imgURL, loadingBox, platesHTML, moveInstructions,
} from "./ui.js";
import { PoseCamera } from "./pose.js";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export class Player {
  constructor(root, { onClose }) {
    this.root = root;
    this.onClose = onClose;
    this.snap = null;
    this.live = null;
    this.offset = 0;
    this.open_ = false;
    this.busy = false;
    this.stageKey = null;
    this.panelKey = null;
    this.cameraOn = localStorage.getItem("cameraOn") !== "0";
    this.cam = new PoseCamera((s) => { this.live = s; this.updateLive(); });
    this.holder = document.createElement("div");
    this.holder.style.cssText = "position:fixed;left:0;top:0;width:4px;height:4px;opacity:0;overflow:hidden;pointer-events:none";
    this.onKey = this.onKey.bind(this);
    this.onVisible = () => { if (document.visibilityState === "visible" && this.open_) this.wake(); };
    this.root.addEventListener("click", (e) => this.onClick(e));
  }

  // ---------------------------------------------------------------- lifecycle

  async open(snapshot) {
    try { this.profile = (await api("/api/profile")).profile; } catch { this.profile = { camera: {}, voice: { enabled: true } }; }
    this.voiceOn = this.profile.voice?.enabled !== false;
    this.testVideo = !!this.profile.camera?.test_video;
    this.cam.setMirror(this.profile.camera?.mirror !== false && !this.testVideo);
    this.open_ = true;
    this.stageKey = this.panelKey = null;
    this.root.hidden = false;
    document.body.style.overflow = "hidden";
    this.root.innerHTML = `
      <div class="p-top"></div>
      <div class="p-main">
        <div class="p-stage"></div>
        <aside class="p-panel"></aside>
      </div>
      <div class="p-bottom"></div>`;
    document.body.appendChild(this.holder);
    this.holder.appendChild(this.cam.el);
    document.addEventListener("keydown", this.onKey);
    document.addEventListener("visibilitychange", this.onVisible);
    this.wake();
    this.apply(snapshot);
    this.timer = setInterval(() => this.frame(), 200);
    this.pollLoop();
  }

  close() {
    if (!this.open_) return;
    this.open_ = false;
    clearInterval(this.timer);
    document.removeEventListener("keydown", this.onKey);
    document.removeEventListener("visibilitychange", this.onVisible);
    this.cam.stop();
    this.holder.remove();
    this.root.hidden = true;
    this.root.innerHTML = "";
    document.body.style.overflow = "";
    this.lock?.release?.().catch(() => {});
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    this.onClose?.();
  }

  async wake() {
    try { this.lock = await navigator.wakeLock?.request("screen"); } catch { /* not critical */ }
  }

  async pollLoop() {
    while (this.open_) {
      if (!this.busy) {
        try { this.apply(await api("/api/session")); } catch { /* server restarting */ }
      }
      await sleep(300);
    }
  }

  apply(s) {
    if (!this.open_) return;
    if (!s.active) { this.close(); return; }
    this.snap = s;
    this.offset = s.now - Date.now() / 1000;
    if (s.live && this.cam.status !== "running") this.live = s.live;
    this.syncCamera();
    this.render();
  }

  async act(action, data = {}) {
    this.busy = true;
    try {
      this.apply(await post(`/api/session/${action}`, data));
    } catch (e) {
      toast(e.message);
    } finally {
      this.busy = false;
    }
  }

  // ---------------------------------------------------------------- time

  now() { return Date.now() / 1000 + this.offset; }

  remaining() {
    const s = this.snap;
    if (!s?.until) return null;
    const ref = s.paused ? s.paused_at : this.now();
    return Math.max(0, s.until - ref);
  }

  // ---------------------------------------------------------------- camera

  trackedMove() {
    const s = this.snap;
    const cur = s.current, nxt = s.next;
    if (["countdown", "active"].includes(s.phase)) return cur?.move?.tracker ? cur.move : null;
    if (s.phase === "intro") return cur?.move?.tracker ? cur.move : null;
    if (s.phase === "rest" && nxt && nxt.t !== "timed") return nxt.move?.tracker ? nxt.move : null;
    return null;
  }

  syncCamera() {
    const m = this.trackedMove();
    if (!this.cameraOn || !m) {
      // Keep it running between sets of a tracked exercise; stop otherwise.
      if (this.cam.running && (!this.cameraOn || ["timed", "overview", "done"].includes(this.snap.phase))) this.cam.stop();
      return;
    }
    const source = this.testVideo ? videoURL(m.slug) : "webcam";
    // After a failure (e.g. permission denied) wait for the user to toggle
    // the camera rather than retrying -- and re-prompting -- every poll.
    if (this.cam.status === "error" && this.cam.failedSource === source) return;
    if (this.cam.source !== source && this.cam.status !== "starting") {
      this.cam.start({ source, model: this.profile.camera?.model || "full" }).then(() => this.render());
    }
  }

  // ---------------------------------------------------------------- render

  stageKeyFor(s) {
    if (s.phase === "done") return "summary";
    const cur = s.current;
    if (["countdown", "active"].includes(s.phase) && cur?.move?.tracker && this.cameraOn) return "camera";
    let slug = cur?.move?.slug || "";
    if (s.phase === "rest" && s.next) slug = s.next.move?.slug || slug;
    if (s.phase === "overview") {
      const first = (s.blocks || []).find((b) => b.type === "exercise");
      slug = first?.move?.slug || "";
    }
    return `demo:${slug}`;
  }

  render() {
    const s = this.snap;
    this.renderTop();
    if (s.phase === "done") {
      if (this.stageKey !== "summary") { this.stageKey = "summary"; this.renderSummary(); }
      return;
    }
    const sk = this.stageKeyFor(s);
    if (sk !== this.stageKey) { this.stageKey = sk; this.renderStage(sk); }
    const pk = JSON.stringify([s.phase, s.pos, s.side, s.paused, s.pending, s.advice, s.current, s.next?.move?.id, this.cameraOn, this.cam.status]);
    if (pk !== this.panelKey) { this.panelKey = pk; this.renderPanel(); }
    this.renderBottom();
    this.frame();
  }

  renderTop() {
    const s = this.snap, top = $(".p-top", this.root);
    if (!top) return;
    const rail = (s.outline || []).map((r) => `<i class="${r.state}" title="${esc(r.label)}"></i>`).join("");
    top.innerHTML = `
      <button class="icon-btn" data-act="end" title="End workout (Esc)">${icon("close")}</button>
      <span class="title">${esc(s.plan.title)}</span>
      <span class="clock num" id="p-elapsed"></span>
      <div class="p-rail">${rail}</div>
      ${s.phase !== "done" ? `<button class="icon-btn" data-act="pause" title="Pause (P)">${icon(s.paused ? "play" : "pause")}</button>` : ""}
      <button class="icon-btn ${this.voiceOn ? "" : "off"}" data-act="voice" title="Voice (V)">${icon(this.voiceOn ? "voice" : "mute")}</button>
      <button class="icon-btn ${this.cameraOn ? "" : "off"}" data-act="camera" title="Camera (C)">${icon(this.cameraOn ? "camera" : "camoff")}</button>
      <button class="icon-btn" data-act="fullscreen" title="Full screen (F)">${icon("full")}</button>`;
  }

  renderStage(key) {
    const stage = $(".p-stage", this.root);
    const overlays = `<div class="stage-badges"></div><div class="stage-count hidden"></div>
      <div class="stage-cue hidden"></div><div class="stage-overlay hidden"></div>`;
    if (key === "camera") {
      stage.classList.remove("light");
      stage.innerHTML = overlays;
      stage.prepend(this.cam.el);
      return;
    }
    if (this.cam.el.parentElement !== this.holder) this.holder.appendChild(this.cam.el);
    const slug = key.slice(5);
    stage.classList.toggle("light", !!slug);
    stage.innerHTML = slug
      ? `<video class="demo-v" src="${videoURL(slug)}" poster="${imgURL(slug)}" autoplay muted loop playsinline></video>${overlays}`
      : `<div class="stage-msg"><h3>No demo video</h3>Follow the steps on the right.</div>${overlays}`;
  }

  renderBottom() {
    const s = this.snap, el = $(".p-bottom", this.root);
    if (!el) return;
    const keys = {
      overview: [["Space", "Start"]],
      timed: [["Space", "Next move"], ["P", "Pause"]],
      intro: [["Space", "Start"], ["[ ]", "Weight"], ["Esc", "End"]],
      countdown: [["Space", "Start now"]],
      active: [["Space", s.current?.move?.per_side && s.side === 1 ? "Switch sides" : "Done"]],
      rest: [["1-4", "Rate"], ["+ −", "Reps"], ["[ ]", "Next weight"], ["N", "Skip rest"], ["R", "+30 s"]],
    }[s.phase] || [];
    let cam = "";
    if (this.cameraOn && this.cam.status === "running") cam = `Camera on · ${this.cam.fps.toFixed(0)} fps`;
    else if (this.cam.status === "starting") cam = "Starting camera and pose model…";
    else if (this.cam.status === "error") cam = `<span style="color:var(--bad)">Camera: ${esc(this.cam.error)}</span>`;
    else if (!this.cameraOn) cam = "Camera off — reps are logged manually";
    el.innerHTML = `<div class="keys">${keys.map(([k, l]) => `<span><kbd>${k}</kbd> ${l}</span>`).join("")}</div>
      <span class="spacer"></span><span id="cam-status">${cam}</span>`;
  }

  // ---------------------------------------------------------------- panels

  renderPanel() {
    const s = this.snap, panel = $(".p-panel", this.root);
    const fn = {
      overview: this.pOverview, timed: this.pTimed, intro: this.pIntro,
      countdown: this.pSet, active: this.pSet, rest: this.pRest,
    }[s.phase];
    const keepScroll = panel.dataset.pos === String(s.pos) ? panel.scrollTop : 0;
    panel.innerHTML = fn ? fn.call(this, s) : "";
    panel.dataset.pos = String(s.pos);
    panel.scrollTop = keepScroll;
  }

  exerciseNumber(s) {
    const rows = s.outline || [];
    const ex = rows.filter((r) => r.type === "exercise");
    const idx = ex.findIndex((r) => r.state === "current");
    return [idx + 1, ex.length];
  }

  pOverview(s) {
    const items = (s.blocks || []).map((b) => {
      if (b.type !== "exercise") {
        const mins = Math.round(b.items.reduce((a, it) => a + it.seconds * (it.per_side ? 2 : 1), 0) / 60);
        return `<div class="ov-item"><div class="block-head" style="padding:0"><span class="ico">${icon(b.type === "cooldown" ? "cooldown" : b.type === "mobility" ? "mobility" : "warmup")}</span></div>
          <div><b>${esc(b.title)}</b><div class="small muted">${b.items.length} moves · about ${mins} min</div></div></div>`;
      }
      const m = b.move;
      return `<div class="ov-item"><img class="thumb" src="${thumbURL(m.slug)}" alt="">
        <div style="min-width:0"><b>${esc(m.name)}</b><div class="small muted">${esc(prescription(m, b.target, b.sets))} · ${esc(fmtWeight(m.mode, b.target.weight))}</div></div></div>`;
    }).join("");
    return `<div class="kicker">Week ${s.plan.week} · ${esc(s.plan.focus)}${s.plan.location_label ? ` · ${esc(s.plan.location_label)}` : ""}</div>
      <h1>${esc(s.plan.title)}</h1>
      <div class="muted">About ${s.plan.estimate_min} minutes. ${esc(s.plan.phase_text)}</div>
      ${(s.plan.notes || []).map((n) => `<div class="phase-note">${esc(n)}</div>`).join("")}
      <div class="overview-list">${items}</div>
      <div class="p-actions"><button class="btn primary big" data-act="next">Start <kbd>Space</kbd></button></div>`;
  }

  pTimed(s) {
    const c = s.current, m = c.move;
    const next = s.next;
    const nextTxt = !next ? "Last one" : next.t === "timed" ? `Next: ${esc(next.move.name)}`
      : `Then: ${esc(next.move.name)}`;
    return `<div class="kicker">${esc(c.block_title || "")} · ${c.item} of ${c.count}</div>
      <h1>${esc(m.name)}</h1>
      ${m.purpose ? `<div class="muted">${esc(m.purpose)}</div>` : ""}
      <div class="ring" id="ring"><svg viewBox="0 0 120 120"><circle class="track" cx="60" cy="60" r="52" fill="none" stroke-width="10"/>
        <circle class="prog" cx="60" cy="60" r="52" fill="none" stroke-width="10" stroke-dasharray="326.7" stroke-dashoffset="0"/></svg>
        <div class="label"><div class="v num" id="ring-v">–</div><div class="s" id="ring-s">${c.per_side ? "Side 1 of 2" : "seconds"}</div></div></div>
      ${m.reps_hint ? `<div class="rx-line"><span class="chip">${esc(m.reps_hint)}</span></div>` : ""}
      ${m.steps?.length ? `<ol class="steps">${m.steps.map((x) => `<li>${esc(x)}</li>`).join("")}</ol>` : ""}
      <div class="p-section muted">${nextTxt}</div>
      <div class="p-actions"><button class="btn primary big" data-act="next">Next <kbd>Space</kbd></button></div>`;
  }

  pIntro(s) {
    const c = s.current, m = c.move, t = c.target;
    const [k, n] = this.exerciseNumber(s);
    const opts = c.options || {};
    const grad = t.status === "graduate" && t.graduate_to
      ? `<div class="advice change p-section"><div class="t">Ready to progress</div>
          <div class="small">${esc(t.reason)}</div>
          <div class="row" style="margin-top:8px"><button class="btn small primary" data-act="swap" data-move="${esc(t.graduate_to)}" data-keep="1">Switch to the harder variation</button></div></div>` : "";
    return `<div class="kicker">Exercise ${k} of ${n} · ${esc(m.group_label)}</div>
      <h1>${esc(m.name)}</h1>
      <div class="muted">${esc(m.purpose)}</div>
      <div class="rx-line">
        <span class="chip">${esc(prescription(m, t, c.sets))}</span>
        <span class="chip">${esc(fmtWeight(m.mode, t.weight))}</span>
        <span class="chip">Rest ${c.rest}s</span>
        ${m.tracker ? `<span class="chip" style="color:var(--info)">Camera counts reps</span>` : ""}
      </div>
      <div class="row wrap"><span class="badge ${t.status}">${esc(STATUS_LABEL[t.status] || t.status)}</span>
        <span class="small muted" style="flex:1;min-width:200px">${esc(t.reason)}</span></div>
      ${grad}
      ${c.first_time && m.weighted ? `<div class="advice p-section"><div class="t">New exercise</div><div class="small">Start light. After set 1 you rate how it felt, and the next set's weight adjusts automatically.</div></div>` : ""}
      <div class="p-section">${loadingBox(m, c.weight_text, c.loading, c.plates)}</div>
      ${m.tracker ? `<div class="p-section small"><b>Camera:</b> <span class="muted">${esc(m.view_text)}</span></div>` : ""}
      <div class="p-section">${moveInstructions(m)}</div>
      <div class="p-actions">
        <button class="btn primary big" data-act="next">Start <kbd>Space</kbd></button>
        ${opts.easier?.length ? `<button class="btn" data-act="swapmenu" data-kind="easier">Too hard?</button>` : ""}
        ${(opts.similar?.length || opts.harder?.length) ? `<button class="btn" data-act="swapmenu" data-kind="all">Swap</button>` : ""}
        <button class="btn ghost" data-act="skip_exercise">Skip</button>
      </div>`;
  }

  pSet(s) {
    const c = s.current, m = c.move, set = c.set;
    const sideTxt = m.per_side ? ` · Side ${s.side} of 2` : "";
    const label = set.kind === "warmup" ? "Ramp-up set" : `Set ${c.work_no} of ${c.work_total}`;
    const tracked = m.tracker && this.cameraOn;
    let main;
    if (m.hold) {
      main = `<div class="ring" id="ring"><svg viewBox="0 0 120 120"><circle class="track" cx="60" cy="60" r="52" fill="none" stroke-width="10"/>
        <circle class="prog" cx="60" cy="60" r="52" fill="none" stroke-width="10" stroke-dasharray="326.7" stroke-dashoffset="0"/></svg>
        <div class="label"><div class="v num" id="ring-v">${set.goal}</div><div class="s">seconds</div></div></div>`;
    } else if (tracked) {
      main = `<div class="counter"><div class="v num" id="live-reps">0</div>
        <div><div class="lbl">reps counted</div><div class="small muted">Aim for ${set.goal}${set.lo !== set.hi ? ` (range ${set.lo}–${set.hi})` : ""}</div>
        <div class="small" id="live-partials"></div></div></div>`;
    } else {
      main = `<div class="counter"><div class="v num">${set.goal}</div>
        <div><div class="lbl">reps to aim for</div><div class="small muted">${set.lo !== set.hi ? `Range ${set.lo}–${set.hi}. ` : ""}Count them yourself — you'll confirm when you finish.</div></div></div>`;
    }
    const primary = s.phase === "countdown" ? "Start now"
      : (m.per_side && s.side === 1) ? "Switch sides" : "Done";
    return `<div class="kicker">${label}${sideTxt}</div>
      <h1>${esc(m.name)}</h1>
      <div class="rx-line">
        <span class="chip">${esc(fmtWeight(m.mode, set.weight))}</span>
        ${set.kind === "warmup" ? `<span class="chip">Light ramp-up: ${set.goal} easy reps</span>` : ""}
      </div>
      ${s.phase === "countdown" ? `<div class="advice"><div class="t">Get in position</div><div class="small">${esc(m.view_text || "Get set up.")}</div></div>` : ""}
      ${main}
      ${m.weighted ? `<div class="p-section">${loadingBox(m, c.weight_text, c.loading, c.plates)}</div>` : ""}
      ${m.cues?.length ? `<div class="p-section"><div class="label-sm">Focus on</div><div class="cues">${m.cues.map((x) => `<span>${esc(x)}</span>`).join("")}</div></div>` : ""}
      <div class="p-actions"><button class="btn primary big" data-act="next">${primary} <kbd>Space</kbd></button></div>`;
  }

  pRest(s) {
    const p = s.pending, c = s.current, m = c.move, next = s.next;
    const rating = p && p.kind === "work" ? `
      <div class="p-section"><div class="label-sm">How did that set feel?</div>
        <div class="rate-grid">${RATINGS.map((r) => `
          <button class="rate ${p.rating === r.key ? "on" : ""} ${!p.rating ? "rate-pulse" : ""}" data-act="rate" data-r="${r.key}">
            <div class="k">${r.k}</div><div class="n">${r.name}</div><div class="d">${r.desc}</div></button>`).join("")}
        </div></div>` : "";
    const unit = p?.hold ? "Seconds held" : "Reps done";
    const camNote = p?.camera_reps != null ? `<span class="tiny muted">camera counted ${p.camera_reps}${p.reps_by_side ? ` (${p.reps_by_side.join(" / ")})` : ""}</span>` : "";
    const edit = p ? `<div class="p-section">
        <div class="mini-row"><span class="lbl">${p.set_label}: ${unit} ${camNote}</span>
          <button class="mini-step" data-act="reps" data-d="-1">−</button><span class="val">${p.reps}</span>
          <button class="mini-step" data-act="reps" data-d="1">+</button></div>
        ${m.weighted ? `<div class="mini-row"><span class="lbl">Weight used</span>
          <button class="mini-step" data-act="weight" data-target="last" data-d="-1">−</button>
          <span class="val">${esc(fmtWeight(m.mode, p.weight))}</span>
          <button class="mini-step" data-act="weight" data-target="last" data-d="1">+</button></div>` : ""}
      </div>` : "";
    const a = s.advice;
    const advice = a && a.message ? `<div class="p-section advice ${a.to != null ? "change" : ""}">
        <div class="t">${a.to != null ? `Next set: ${esc(fmtWeight(m.mode, a.to))}` : "Coach"}</div>
        <div class="small">${esc(a.message)}</div>
        ${a.to != null ? `${platesHTML(a.plates, { compact: true })}<div class="small muted">${esc(a.loading)}</div>
          <button class="btn small ghost" data-act="undo_advice" style="margin-top:6px">Keep ${esc(fmtWeight(m.mode, a.from))} instead</button>` : ""}
      </div>` : "";
    let upNext = "";
    if (next && next.t === "set") {
      const ns = next.set;
      upNext = `<div class="up-next"><div style="flex:1"><div class="tiny muted">UP NEXT</div>
          <b>${ns.kind === "warmup" ? "Ramp-up set" : `Set ${next.work_no} of ${next.work_total}`}</b>
          <div class="small muted">${next.move.hold ? `${ns.goal}s` : `aim ${ns.goal} reps`} · ${esc(fmtWeight(next.move.mode, ns.weight))}</div></div>
          ${next.move.weighted ? `<div class="row"><button class="mini-step" data-act="weight" data-target="next" data-d="-1" title="Lighter ([)">−</button>
            <button class="mini-step" data-act="weight" data-target="next" data-d="1" title="Heavier (])">+</button></div>` : ""}
        </div>`;
    } else if (next && next.t === "intro") {
      upNext = `<div class="up-next"><img src="${thumbURL(next.move.slug)}" alt="">
        <div><div class="tiny muted">NEXT EXERCISE</div><b>${esc(next.move.name)}</b>
        <div class="small muted">${esc(prescription(next.move, next.target, next.sets))} · ${esc(next.weight_text)}</div></div></div>
        ${next.move.weighted ? `<div class="p-section">${loadingBox(next.move, next.weight_text, next.loading, next.plates)}</div>` : ""}`;
    } else if (next && next.t === "timed") {
      upNext = `<div class="up-next"><div><div class="tiny muted">NEXT</div><b>Cool-down</b><div class="small muted">Stretches, about 5 minutes, hands-free.</div></div></div>`;
    } else {
      upNext = `<div class="up-next"><div><div class="tiny muted">NEXT</div><b>All done</b></div></div>`;
    }
    return `<div class="kicker">Rest</div>
      <div class="ring rest" id="ring"><svg viewBox="0 0 120 120"><circle class="track" cx="60" cy="60" r="52" fill="none" stroke-width="10"/>
        <circle class="prog" cx="60" cy="60" r="52" fill="none" stroke-width="10" stroke-dasharray="326.7" stroke-dashoffset="0"/></svg>
        <div class="label"><div class="v num" id="ring-v">–</div><div class="s">rest</div></div></div>
      <div class="row" style="justify-content:center;gap:8px">
        <button class="btn small" data-act="add_rest">+30 s <kbd>R</kbd></button>
        <button class="btn small" data-act="skip_rest">Skip rest <kbd>N</kbd></button></div>
      ${rating}${edit}${advice}
      <div class="p-section">${upNext}</div>`;
  }

  renderSummary() {
    const sm = this.snap.summary || {};
    const main = $(".p-main", this.root);
    $(".p-bottom", this.root).innerHTML = "";
    const r = sm.ratings || {};
    const total = Object.values(r).reduce((a, b) => a + b, 0) || 1;
    const bar = ["easy", "good", "hard", "failed"].map((k) => `<i style="width:${(100 * (r[k] || 0)) / total}%;background:var(--${k})"></i>`).join("");
    const ex = (sm.exercises || []).map((e) => `<tr><td><b>${esc(e.name)}</b> ${e.pr ? '<span class="badge pr">New best</span>' : ""}</td>
      <td>${e.sets.map((x) => `<span class="rating-dot ${x.rating || ""}"></span>${x.seconds ? x.seconds + "s" : (x.weight ? `${x.weight}×${x.reps}` : `${x.reps}`)}`).join(" &nbsp; ")}</td></tr>`).join("");
    main.style.gridTemplateColumns = "1fr";
    main.innerHTML = `<div class="summary">
      <div class="hero"><div class="eyebrow">${esc(sm.title)} · ${sm.status === "done" ? "Complete" : "Ended early"}</div>
        <h1>${sm.status === "done" ? "Great work." : "Saved what you did."}</h1>
        <div class="focus">Everything is logged. Your next session's weights already account for today.</div></div>
      <div class="stats" style="margin-top:16px">
        <div class="stat"><div class="l">Duration</div><div class="v">${Math.round(sm.duration_min || 0)}<span class="small muted"> min</span></div></div>
        <div class="stat"><div class="l">Working sets</div><div class="v">${sm.total_sets || 0}</div></div>
        <div class="stat"><div class="l">Reps</div><div class="v">${sm.total_reps || 0}</div></div>
        <div class="stat"><div class="l">Volume</div><div class="v">${Math.round(sm.volume_kg || 0)}<span class="small muted"> kg</span></div></div>
      </div>
      ${sm.total_sets ? `<div class="card" style="margin-top:16px"><h3>How the sets felt</h3><div class="ratings-bar">${bar}</div>
        <div class="row wrap small muted" style="margin-top:8px">${["easy", "good", "hard", "failed"].map((k) => `<span><span class="rating-dot ${k}"></span>${k[0].toUpperCase() + k.slice(1)} ${r[k] || 0}</span>`).join("")}</div></div>` : ""}
      ${ex ? `<div class="card" style="margin-top:16px"><h3>Exercises</h3><div class="table-wrap"><table class="t">${ex}</table></div></div>` : ""}
      <div class="p-actions" style="justify-content:center"><button class="btn primary big" data-act="close">Back to Today</button></div>
    </div>`;
  }

  // ---------------------------------------------------------------- per frame

  frame() {
    const s = this.snap;
    if (!s || !this.open_) return;
    const el = $("#p-elapsed", this.root);
    if (el) el.textContent = fmtClock((s.paused ? s.paused_at : this.now()) - s.started_at);
    const left = this.remaining();
    const ring = $("#ring", this.root);
    if (ring && left != null) {
      let total = s.until - s.phase_started, shown = left;
      if (s.phase === "timed" && s.current?.per_side) {
        total = s.current.seconds;
        shown = s.side === 1 ? Math.max(0, left - total) : left;
        const lbl = $("#ring-s", this.root);
        if (lbl) lbl.textContent = `Side ${s.side} of 2`;
      }
      const v = $("#ring-v", this.root);
      if (v) v.textContent = Math.ceil(shown);
      const frac = total > 0 ? shown / total : 0;
      const prog = $(".prog", ring);
      if (prog) prog.style.strokeDashoffset = String(326.7 * (1 - frac));
    }
    // Stage overlay: countdowns and pause.
    const ov = $(".stage-overlay", this.root);
    if (ov) {
      let html = "";
      if (s.paused) html = `<div><div class="msg">Paused</div><div class="small" style="opacity:.8;margin-top:6px">Press P or Space to continue</div></div>`;
      else if (s.phase === "countdown" && left != null) {
        const view = this.live && this.live.want_view !== "any"
          ? (this.live.view_ok ? "Position looks good" : `Turn ${this.live.want_view === "side" ? "side-on" : "to face the camera"}`) : "Get in position";
        html = `<div><div class="big">${Math.ceil(left)}</div><div class="msg">${esc(s.side === 2 ? "Switch sides" : view)}</div></div>`;
      }
      ov.innerHTML = html;
      ov.classList.toggle("hidden", !html);
    }
    this.updateLive();
  }

  updateLive() {
    const s = this.snap, L = this.live;
    if (!s || !this.open_) return;
    const counting = s.phase === "active" && this.stageKey === "camera";
    const reps = L?.counting ? L.reps : 0;
    const big = $("#live-reps", this.root);
    if (big) big.textContent = String(reps);
    const part = $("#live-partials", this.root);
    if (part) part.innerHTML = L?.partials ? `<span style="color:var(--warn)">${L.partials} partial${L.partials > 1 ? "s" : ""} not counted</span>` : "";
    const cnt = $(".stage-count", this.root);
    if (cnt) { cnt.textContent = String(reps); cnt.classList.toggle("hidden", !counting || !s.current?.move?.tracker || s.current?.move?.hold); }
    const cue = $(".stage-cue", this.root);
    if (cue) {
      const txt = counting && L?.cues?.length ? L.cues[0] : "";
      cue.textContent = txt;
      cue.classList.toggle("hidden", !txt);
    }
    const badges = $(".stage-badges", this.root);
    if (badges && this.stageKey === "camera") {
      let b = "";
      if (this.cam.status === "starting") b += `<span class="stage-badge">Loading pose model…</span>`;
      else if (this.cam.status === "error") b += `<span class="stage-badge warn">${esc(this.cam.error)}</span>`;
      else if (L && !L.person) b += `<span class="stage-badge warn">Step into the frame</span>`;
      else if (L && L.want_view !== "any") b += `<span class="stage-badge ${L.view_ok ? "ok" : "warn"}">${L.view_ok ? "View OK" : `Turn ${L.want_view === "side" ? "side-on" : "to face the camera"}`}</span>`;
      if (this.testVideo) b += `<span class="stage-badge">Test video</span>`;
      if (badges.innerHTML !== b) badges.innerHTML = b;
    }
  }

  // ---------------------------------------------------------------- input

  onClick(e) {
    const btn = e.target.closest("[data-act]");
    if (!btn || !this.root.contains(btn)) return;
    const a = btn.dataset.act;
    switch (a) {
      case "next": case "skip_rest": case "skip_exercise": case "undo_advice": case "close":
        this.act(a); break;
      case "add_rest": this.act("add_rest", { seconds: 30 }); break;
      case "rate": this.act("rate", { rating: btn.dataset.r }); break;
      case "reps": this.act("reps", { delta: +btn.dataset.d }); break;
      case "weight": this.act("weight", { target: btn.dataset.target, delta: +btn.dataset.d }); break;
      case "swap": this.act("swap", { move: btn.dataset.move, keep: btn.dataset.keep === "1" }); break;
      case "swapmenu": this.swapMenu(btn.dataset.kind); break;
      case "pause": this.act(this.snap.paused ? "resume" : "pause"); break;
      case "voice": this.toggleVoice(); break;
      case "camera": this.toggleCamera(); break;
      case "fullscreen": this.toggleFullscreen(); break;
      case "end": this.confirmEnd(); break;
    }
  }

  onKey(e) {
    if (!this.open_ || e.target.closest?.("input, select, textarea")) return;
    const modal = $("#modal");
    if (!modal.hidden) { if (e.key === "Escape") modal.hidden = true; return; }
    const s = this.snap;
    if (!s) return;
    const resting = s.phase === "rest" && s.pending;
    const k = e.key;
    if (k === " " || k === "Enter") {
      e.preventDefault();
      if (s.phase === "done") this.act("close");
      else if (s.paused) this.act("resume");
      else this.act("next");
    } else if (["1", "2", "3", "4"].includes(k) && resting && s.pending.kind === "work") {
      this.act("rate", { rating: ["easy", "good", "hard", "failed"][+k - 1] });
    } else if ((k === "+" || k === "=" || e.code === "NumpadAdd") && resting) this.act("reps", { delta: 1 });
    else if ((k === "-" || k === "_" || e.code === "NumpadSubtract") && resting) this.act("reps", { delta: -1 });
    else if (k === "[" || k === "]") this.act("weight", { target: "next", delta: k === "]" ? 1 : -1 });
    else if ((k === "n" || k === "N") && s.phase === "rest") this.act("skip_rest");
    else if ((k === "r" || k === "R") && s.phase === "rest") this.act("add_rest", { seconds: 30 });
    else if (k === "p" || k === "P") this.act(s.paused ? "resume" : "pause");
    else if (k === "v" || k === "V") this.toggleVoice();
    else if (k === "c" || k === "C") this.toggleCamera();
    else if (k === "f" || k === "F") this.toggleFullscreen();
    else if (k === "Escape") this.confirmEnd();
  }

  async toggleVoice() {
    this.voiceOn = !this.voiceOn;
    try { await post("/api/voice", { enabled: this.voiceOn }); } catch {}
    this.renderTop();
    toast(this.voiceOn ? "Voice on" : "Voice muted");
  }

  toggleCamera() {
    this.cameraOn = !this.cameraOn;
    localStorage.setItem("cameraOn", this.cameraOn ? "1" : "0");
    if (!this.cameraOn) this.cam.stop();
    this.cam.failedSource = null;       // toggling is how you retry after an error
    this.stageKey = null;
    this.syncCamera();
    this.render();
    toast(this.cameraOn ? "Camera on" : "Camera off — log reps by hand");
  }

  toggleFullscreen() {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    else document.documentElement.requestFullscreen?.().catch(() => {});
  }

  swapMenu(kind) {
    const opts = this.snap.current?.options || {};
    const groups = kind === "easier" ? [["Easier", opts.easier]]
      : [["Easier", opts.easier], ["Similar", opts.similar], ["Harder", opts.harder]];
    const modal = $("#modal");
    modal.innerHTML = `<div class="sheet" style="max-width:460px"><div class="sheet-head"><h3>${kind === "easier" ? "Make it easier" : "Swap exercise"}</h3>
      <span class="spacer"></span><button class="icon-btn" data-close>${icon("close")}</button></div>
      <div style="padding:16px 20px 20px">
        ${groups.filter(([, l]) => l?.length).map(([h, l]) => `<div class="label-sm">${h}</div>
          <div class="stack">${l.map((o) => `<button class="btn" style="width:100%;justify-content:flex-start" data-move="${esc(o.id)}">${esc(o.name)}</button>`).join("")}</div>`).join("")}
        <label class="row small" style="margin-top:16px"><input type="checkbox" id="keep-swap"> Keep this swap in future workouts</label>
      </div></div>`;
    modal.hidden = false;
    modal.onclick = (e) => {
      if (e.target === modal || e.target.closest("[data-close]")) { modal.hidden = true; return; }
      const b = e.target.closest("[data-move]");
      if (b) {
        modal.hidden = true;
        this.act("swap", { move: b.dataset.move, keep: $("#keep-swap").checked });
      }
    };
  }

  confirmEnd() {
    if (this.snap?.phase === "done") { this.act("close"); return; }
    const modal = $("#modal");
    const done = this.snap.sets_logged || 0;
    modal.innerHTML = `<div class="sheet" style="max-width:440px"><div class="sheet-head"><h3>End workout?</h3></div>
      <div style="padding:16px 20px 20px" class="stack">
        <p class="muted">${done ? `${done} working set${done > 1 ? "s are" : " is"} already saved.` : "Nothing has been logged yet."}</p>
        <button class="btn primary" data-x="end" style="width:100%">End and save</button>
        <button class="btn" data-x="pause" style="width:100%">Pause instead</button>
        <button class="btn danger" data-x="discard" style="width:100%">Discard this workout</button>
        <button class="btn ghost" data-x="cancel" style="width:100%">Keep going</button>
      </div></div>`;
    modal.hidden = false;
    modal.onclick = (e) => {
      const b = e.target.closest("[data-x]");
      if (e.target === modal) { modal.hidden = true; return; }
      if (!b) return;
      modal.hidden = true;
      if (b.dataset.x === "end") this.act("end");
      if (b.dataset.x === "pause") this.act("pause");
      if (b.dataset.x === "discard") this.act("discard");
    };
  }
}
