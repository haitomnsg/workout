// Small shared helpers: escaping, formatting, icons, the plate diagram.

export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export async function api(url, opts = {}) {
  const init = { headers: { "Content-Type": "application/json" }, ...opts };
  if (opts.body && typeof opts.body !== "string") init.body = JSON.stringify(opts.body);
  const r = await fetch(url, init);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `${r.status} ${r.statusText}`);
  return data;
}
export const post = (url, body = {}) => api(url, { method: "POST", body });
export const put = (url, body = {}) => api(url, { method: "PUT", body });

let toastTimer;
export function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2400);
}

export const thumbURL = (slug) => (slug ? `/media/thumb/${slug}` : "");
export const imgURL = (slug) => (slug ? `/media/img/${slug}` : "");
export const videoURL = (slug) => (slug ? `/media/video/${slug}` : "");

export function fmtWeight(mode, w) {
  if (mode === "bw" || w == null) return "Bodyweight";
  return `${+w.toFixed(2)} kg${mode === "db2" ? " each" : ""}`;
}

export const MODE_LABEL = { db1: "One dumbbell", db2: "Pair of dumbbells", bb: "Barbell", bw: "Bodyweight" };

export function fmtClock(sec) {
  sec = Math.max(0, Math.round(sec));
  const m = Math.floor(sec / 60), s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function fmtDate(iso, opts = { weekday: "short", day: "numeric", month: "short" }) {
  if (!iso) return "";
  const d = new Date(iso.length <= 10 ? iso + "T12:00:00" : iso);
  return d.toLocaleDateString(undefined, opts);
}

export const WEEKDAY_SHORT = { sun: "Sun", mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat" };

export const RATINGS = [
  { key: "easy", name: "Easy", desc: "4+ reps left", k: "1" },
  { key: "good", name: "Good", desc: "2-3 left", k: "2" },
  { key: "hard", name: "Hard", desc: "1 left", k: "3" },
  { key: "failed", name: "Failed", desc: "Couldn't finish", k: "4" },
];

export const STATUS_LABEL = {
  new: "First time", up: "Weight up", reps: "Add reps", hold: "Hold weight",
  hold_up: "Repeat", down: "Lighter", deload: "Deload", maxed: "Plates maxed",
  graduate: "Ready to progress",
};

export function prescription(move, target, sets) {
  const work = (sets || []).filter((s) => s.kind === "work");
  const n = work.length;
  if (move.hold) return `${n} × ${work[0]?.goal ?? target.goal}s${move.per_side ? " / side" : ""}`;
  const side = move.per_side ? " / side" : "";
  const range = target.lo === target.hi ? `${target.lo}` : `${target.lo}–${target.hi}`;
  return `${n} × ${range}${side}`;
}

const ICON_PATHS = {
  warmup: '<path d="M12 3c2 3 5 5 5 9a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3-1-5 1-8z"/>',
  cooldown: '<path d="M12 2v20M4.9 4.9l14.2 14.2M2 12h20M4.9 19.1 19.1 4.9"/>',
  mobility: '<circle cx="12" cy="5" r="2"/><path d="M12 7v6l-4 7M12 13l4 7M6 10h12"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
  voice: '<path d="M11 5 6 9H3v6h3l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13"/>',
  mute: '<path d="M11 5 6 9H3v6h3l5 4V5z"/><path d="M22 9l-6 6M16 9l6 6"/>',
  camera: '<path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/>',
  camoff: '<path d="M1 1l22 22M16 16v1a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2m5 0h4a2 2 0 0 1 2 2v3.3l1 1L23 7v10"/>',
  pause: '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>',
  play: '<path d="M6 4l14 8-14 8z"/>',
  full: '<path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  dumbbell: '<path d="M6.5 6v12M3.5 9v6M17.5 6v12M20.5 9v6M6.5 12h11"/>',
  chair: '<path d="M7 3h10v8H7zM5 11h14v3H5zM7 14v7M17 14v7"/>',
  floor: '<path d="M2 20h20"/><circle cx="19" cy="9.5" r="1.6"/><path d="M4 16.5l9-3.5 4 .5M13 13l1 3.5"/>',
};
export const icon = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICON_PATHS[name] || ""}</svg>`;

// ---- plate diagram ----------------------------------------------------------

function plateEls(list) {
  return list.map((w) => {
    const known = ["2", "1.5", "1.25"].includes(String(w));
    return `<i class="plate${known ? "" : " other"}" data-w="${w}" title="${w} kg"></i>`;
  }).join("");
}

function oneBar(ends, kind) {
  const left = [...ends].reverse();
  const mid = kind === "bb" ? '<i class="bar" style="width:120px"></i>' : '<i class="handle"></i>';
  const stub = '<i class="bar" style="width:8px"></i>';
  return `<div class="plates">${stub}${plateEls(left)}${mid}${plateEls(ends)}${stub}</div>`;
}

export function platesHTML(p, { compact = false } = {}) {
  if (!p) return "";
  let body;
  if (p.mode === "db2") {
    const [a, b] = p.ends;
    body = (JSON.stringify(a) === JSON.stringify(b))
      ? `<div class="dbs"><div>${oneBar(a, "db")}<div class="tiny muted">× 2 dumbbells</div></div></div>`
      : `<div class="dbs"><div>${oneBar(a, "db")}<div class="tiny muted">Dumbbell 1</div></div>
         <div>${oneBar(b, "db")}<div class="tiny muted">Dumbbell 2</div></div></div>`;
  } else {
    body = `<div class="dbs"><div>${oneBar(p.ends[0], p.mode)}</div></div>`;
  }
  if (compact) return body;
  return `${body}<div class="plate-legend">
      <span><i style="background:#3b82f6"></i>2 kg</span>
      <span><i style="background:#f59e0b"></i>1.5 kg</span>
      <span><i style="background:#22c55e"></i>1.25 kg</span></div>`;
}

export function loadingBox(move, weightText, loading, plates) {
  if (!move.weighted) return "";
  return `<div class="loading-box">
    <div class="row"><span class="label">How to load</span><span class="spacer"></span>
      <b>${esc(weightText)}</b></div>
    ${platesHTML(plates)}
    <div class="small muted" style="margin-top:6px">${esc(loading)}</div>
  </div>`;
}

export function demoHTML(slug, { autoplay = true } = {}) {
  if (!slug) return `<div class="demo none"><span>No demo video</span></div>`;
  return `<div class="demo"><video src="${videoURL(slug)}" ${autoplay ? "autoplay" : ""} muted loop playsinline
    poster="${imgURL(slug)}" onerror="this.replaceWith(Object.assign(document.createElement('span'),{textContent:'Demo video not found',className:'muted'}))"></video></div>`;
}

export function moveInstructions(m) {
  const parts = [];
  if (m.steps?.length) parts.push(`<div class="label-sm">How to do it</div><ol class="steps">${m.steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ol>`);
  if (m.cues?.length) parts.push(`<div class="label-sm">Key cues</div><div class="cues">${m.cues.map((c) => `<span>${esc(c)}</span>`).join("")}</div>`);
  if (m.mistakes?.length) parts.push(`<div class="label-sm">Common mistakes</div><ul class="mistakes">${m.mistakes.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>`);
  return parts.join("");
}
