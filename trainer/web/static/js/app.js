// Router and pages. Each page fetches its own data and renders into #page.

import {
  $, $$, esc, api, post, put, toast, icon, fmtDate, WEEKDAY_SHORT,
  STATUS_LABEL, RATINGS, MODE_LABEL, prescription, thumbURL, demoHTML, moveInstructions,
} from "./ui.js";
import { lineChart, sparkline } from "./charts.js";
import { Player } from "./workout.js";

const page = $("#page");
const player = new Player($("#player"), { onClose: () => route() });

const PAGES = { today, plan, progress, library, nutrition, settings };

async function route() {
  const [name, arg] = (location.hash.replace(/^#\/?/, "") || "today").split("/");
  const fn = PAGES[name] || today;
  $$(".tabs a").forEach((a) => a.classList.toggle("active", a.dataset.tab === (PAGES[name] ? name : "today")));
  page.innerHTML = `<div class="empty muted">Loading…</div>`;
  try {
    await fn(arg);
  } catch (e) {
    page.innerHTML = `<div class="empty"><h3>Something went wrong</h3><p>${esc(e.message)}</p>
      <p class="small">Is the WorkOut window still running?</p></div>`;
  }
}
window.addEventListener("hashchange", route);

async function startWorkout(day, location) {
  try {
    const snap = await post("/api/session/start", { ...(day ? { day } : {}), ...(location ? { location } : {}) });
    player.open(snap);
  } catch (e) { toast(e.message); }
}

async function resumeWorkout() {
  const snap = await api("/api/session");
  if (snap.active) player.open(snap);
}

// ============================================================== TODAY

async function today() {
  const d = await api("/api/today");
  const p = d.plan;
  const s = d.session;
  const isRest = p.kind === "mobility";
  const doneToday = d.done_today.length > 0;
  const active = s.active && s.phase !== "done";

  let action;
  if (active) {
    action = `<button class="btn primary big" id="resume">Resume ${esc(s.plan.title)}</button>
      <span class="muted small">${s.paused ? "Paused" : "In progress"}${s.plan.location_label ? ` · ${esc(s.plan.location_label)}` : ""} · ${s.sets_logged} sets logged</span>`;
  } else if (doneToday) {
    action = `<span class="chip" style="color:var(--accent)">${icon("check").replace("<svg", '<svg style="width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:3"')} Done today</span>
      <button class="btn" id="start">${isRest ? "Do it again" : "Train again"}</button>`;
  } else {
    action = `<button class="btn primary big" id="start">${isRest ? "Start mobility" : "Start workout"}</button>
      <span class="muted small">Space works as the main button once you start.</span>`;
  }

  const week = d.week.map((w) => {
    const done = w.done.length > 0;
    let dot = `<span class="dot"></span>`;
    if (done) dot = `<span class="dot done" title="Done"></span>`;
    else if (w.is_today) dot = `<span class="dot today"></span>`;
    else if (w.past && !w.before_start && w.kind === "workout") dot = `<span class="dot missed" title="Missed"></span>`;
    return `<div class="wday ${w.is_today ? "today" : ""} ${w.kind === "mobility" ? "rest" : ""}" title="${esc(w.title)}">
      <div class="d">${WEEKDAY_SHORT[w.weekday]}</div><div class="t">${esc(w.kind === "mobility" ? "Rest" : w.title.replace("Arms, Shoulders & Core", "Arms & Core"))}</div><div class="s">${dot}</div></div>`;
  }).join("");

  const missed = d.missed.filter((m) => !active);
  const missedHTML = missed.length ? `<div class="notice">
      <div style="flex:1;min-width:220px"><b>Missed this week:</b> ${missed.map((m) => `${esc(m.title)} (${WEEKDAY_SHORT[m.weekday]})`).join(", ")}.
      <div class="small muted">${isRest ? "Rest days are a good time to catch up, if you feel fresh." : "You can do one instead of today's session — don't do both."}</div></div>
      ${missed.map((m) => `<button class="btn small" data-day="${m.day_key}">Do ${esc(m.title)}</button>`).join("")}
    </div>` : "";

  const blocks = p.blocks.map((b) => {
    if (b.type === "exercise") {
      const m = b.move, t = b.target;
      return `<div class="ex-row" data-move="${m.id}">
        <img class="thumb" src="${thumbURL(m.slug)}" alt="" loading="lazy">
        <div style="min-width:0"><div class="name">${esc(m.name)}</div>
          <div class="rx">${esc(prescription(m, t, b.sets))}${b.sets.some((x) => x.kind === "warmup") ? " · with ramp-up sets" : ""} · rest ${b.rest}s</div>
          <div class="why"><span class="badge ${t.status}">${esc(STATUS_LABEL[t.status] || t.status)}</span> ${esc(t.reason)}</div></div>
        <div class="right"><div class="w num">${esc(m.weighted ? b.weight_text : "Bodyweight")}</div>
          ${m.tracker ? `<span class="badge tracked">Camera</span>` : ""}</div></div>`;
    }
    const mins = Math.round(b.items.reduce((a, it) => a + it.seconds * (it.per_side ? 2 : 1), 0) / 60);
    const ico = b.type === "cooldown" ? "cooldown" : b.type === "mobility" ? "mobility" : "warmup";
    return `<div class="block" style="${b.type !== "warmup" && b.type !== "mobility" ? "border-top:1px solid var(--border)" : ""}">
      <div class="block-head" data-toggle><span class="ico">${icon(ico)}</span>
        <div style="flex:1"><b>${esc(b.title)}</b><div class="small muted">${b.items.length} moves · about ${mins} min · runs hands-free</div></div>
        <span class="muted small">Show</span></div>
      <div class="block-items closed">${b.items.map((it) => `<div>${esc(it.name)} · ${it.seconds}s${it.per_side ? " each side" : ""}</div>`).join("")}</div></div>`;
  }).join("");

  const notes = (p.notes || []).map((n) => `<div class="kv"><span>${esc(n)}</span></div>`).join("");
  // Pick the place before starting; the plan below rebuilds for it.
  const places = isRest || active ? "" : placePicker(d.locations, d.location, "Where are you training today?");

  page.innerHTML = `
    <div class="grid-2">
      <div>
        <div class="hero">
          <div class="eyebrow">${esc(d.weekday)} · Week ${p.week}${isRest ? " · Rest day" : ""}</div>
          <h1>${esc(p.title)}</h1>
          <div class="focus">${esc(p.focus)}</div>
          <div class="meta">
            <span class="chip">About ${p.estimate_min} min</span>
            ${isRest ? "" : `<span class="chip">${p.blocks.filter((b) => b.type === "exercise").length} exercises</span>`}
            <span class="chip">${esc({ intro: "Learning week", build: "Build phase", deload: "Deload week" }[p.phase])}</span>
          </div>
          ${places}
          <div class="actions">${action}</div>
          <div class="phase-note"><span>${esc(p.phase_text)}</span></div>
        </div>
        <div class="week-strip">${week}</div>
        ${missedHTML}
        <div class="section-title"><h2>${isRest ? "Today's routine" : "Today's plan"}</h2>
          <span class="muted small">${isRest ? "Gentle, 30-45 seconds per move" : d.location === "dumbbells" ? "Weights update from your last session" : "Bodyweight version · reps update from your last session"}</span></div>
        <div class="card flush">${blocks}</div>
      </div>
      <aside class="stack">
        <div class="card side-card">
          <h3>Eat today</h3>
          <div class="row" style="gap:24px;margin:6px 0 10px">
            <div><div class="big-stat">${d.nutrition.kcal.toLocaleString()}</div><div class="small muted">kcal</div></div>
            <div><div class="big-stat">${d.nutrition.protein}</div><div class="small muted">g protein</div></div>
          </div>
          <div class="small muted">${d.nutrition.training_day ? "Training day: a carb snack 60-90 min before, your biggest protein meal after." : "Rest day: eat the same as a training day. Muscle is built today."}</div>
          <a class="btn small" href="#/nutrition" style="margin-top:12px">Meal guide</a>
        </div>
        ${isRest ? `<div class="card side-card"><h3>Recovery</h3>${notes}</div>` : `
        <div class="card side-card"><h3>How a session works</h3>
          <div class="kv"><span>Warm-up runs hands-free with a timer</span></div>
          <div class="kv"><span>Each exercise shows a demo, weight, and how to load your plates</span></div>
          <div class="kv"><span>Press <kbd>Space</kbd> when a set is done, then rate it <kbd>1</kbd>–<kbd>4</kbd></span></div>
          <div class="kv"><span>The next set adjusts to your rating</span></div>
        </div>`}
        ${d.history_count === 0 ? `<div class="card side-card"><h3>First session?</h3>
          <p class="small muted">Week 1 is a learning week: two sets each, weights on the light side. Rate every set honestly — that is how the app learns what you can lift.</p></div>` : ""}
      </aside>
    </div>`;

  $("#start")?.addEventListener("click", () => startWorkout(null, d.location));
  $("#resume")?.addEventListener("click", resumeWorkout);
  $$("[data-day]", page).forEach((b) => b.addEventListener("click", () => startWorkout(b.dataset.day, d.location)));
  $$("[data-place]", page).forEach((b) => b.addEventListener("click", async () => {
    if (b.dataset.place === d.location) return;
    try { await put("/api/profile", { location: b.dataset.place }); await today(); } catch (e) { toast(e.message); }
  }));
  $$("[data-toggle]", page).forEach((h) => h.addEventListener("click", () => {
    const items = h.nextElementSibling;
    items.classList.toggle("closed");
    h.querySelector(".muted.small").textContent = items.classList.contains("closed") ? "Show" : "Hide";
  }));
  $$(".ex-row", page).forEach((r) => r.addEventListener("click", () => openMove(r.dataset.move)));
}

// ============================================================== PLAN

const PLACE_ICON = { dumbbells: "dumbbell", furniture: "chair", floor: "floor" };

function placePicker(locations, current, title) {
  return `<div class="place-pick"><div class="label-sm">${esc(title)}</div>
    <div class="places" role="radiogroup" aria-label="${esc(title)}">${locations.map((l) => `<button class="place ${l.key === current ? "on" : ""}"
      data-place="${l.key}" role="radio" aria-checked="${l.key === current}">
      <span class="ico">${icon(PLACE_ICON[l.key])}</span>
      <span class="txt"><b>${esc(l.label)}</b><span>${esc(l.blurb)}</span></span></button>`).join("")}</div></div>`;
}

let planPlace = null;

async function plan() {
  const d = await api(`/api/plan${planPlace ? `?location=${planPlace}` : ""}`);
  const now = new Date();
  const todayISO = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  const days = d.days.map((day) => {
    const isToday = day.date === todayISO;
    const list = day.kind === "mobility"
      ? `<ul><li>${day.warmup_names.length} gentle moves<span>about 12-15 minutes</span></li>${day.notes.slice(1, 2).map((n) => `<li>${esc(n)}</li>`).join("")}</ul>`
      : `<ul>${day.slots.map((s) => `<li>${esc(s.name)}<span>${s.sets} × ${s.reps[0]}–${s.reps[1]}${s.hold ? " s" : ""}${s.per_side ? " / side" : ""}</span></li>`).join("")}</ul>`;
    return `<div class="day-card ${day.kind === "mobility" ? "rest" : ""} ${isToday ? "today" : ""}">
      <div class="wd">${WEEKDAY_SHORT[day.weekday]}</div><h3>${esc(day.title)}</h3><div class="f">${esc(day.focus)}</div>${list}
      ${day.kind === "workout" ? `<button class="btn small ghost" data-preview="${day.key}" style="margin-top:10px;padding-left:0">Preview</button>` : ""}</div>`;
  }).join("");

  const ladders = Object.entries(d.ladders).map(([mode, l]) => `<div style="margin-top:14px">
      <b>${esc(l.label)}</b> <span class="muted small">· ${l.weights[0]}–${l.weights[l.weights.length - 1]} kg${mode === "db2" ? " each" : ""}</span>
      <div class="ladder">${l.weights.map((w) => `<span>${w}</span>`).join("")}</div></div>`).join("");

  page.innerHTML = `
    <div class="hero">
      <div class="eyebrow">Week ${d.week} · cycle week ${d.cycle_week} of ${d.cycle_len}</div>
      <h1>Upper / Lower, 5 days</h1>
      <div class="focus">${esc(d.phase_text)} ${d.phase !== "deload" ? `Next deload: week ${d.next_deload}.` : ""}</div>
      ${placePicker(d.locations, d.location, "Show the week for")}
      ${d.location !== "dumbbells" ? `<p class="small muted" style="margin-top:12px">Same days, same order, same set counts — bodyweight moves instead of dumbbells. Each move has its own rep range; when you top it on every set the app offers the harder variation.</p>` : ""}
    </div>

    <div class="section-title"><h2>This week</h2><span class="muted small">Upper and lower alternate, so nothing is trained hard two days in a row</span></div>
    <div class="week-grid">${days}</div>

    <div class="section-title"><h2>How you progress</h2></div>
    <div class="card">
      <p class="muted" style="margin-bottom:14px">After every working set you tap how it felt. That rating, plus your reps, decides your next weight.</p>
      <div class="rating-key">${RATINGS.map((r) => `<div style="border-color:var(--${r.key})"><b>${r.name}</b> <kbd>${r.k}</kbd><div class="small muted">${r.desc}</div></div>`).join("")}</div>
      <div class="label-sm" style="margin-top:20px">The rules</div>
      <ol class="rules">
        <li><b>Hit the top of the rep range on every set</b> (none Hard or Failed) → next time the weight goes up by the smallest sensible step.</li>
        <li><b>Inside the range</b> → same weight, aim for one more rep per set.</li>
        <li><b>Below the range</b> → hold the weight. Well below, or failing twice → drop about 10%.</li>
        <li><b>Stuck three sessions</b> → deload 10% and build back up. You'll pass your old best within weeks.</li>
        <li><b>Within a session</b> → an Easy set at the top of the range bumps the next set up; a Failed set brings it down.</li>
        <li><b>Big plate jumps</b> → some steps are large (5.7 → 7.2 kg per dumbbell is +26%), so the app has you build extra reps before jumping.</li>
        <li><b>Bodyweight moves</b> → add reps, then the app suggests the next harder variation.</li>
      </ol>
    </div>

    ${d.location !== "dumbbells" ? "" : `<div class="section-title"><h2>What your plates can make</h2><span class="muted small">${Object.entries(d.kit.plates).map(([w, n]) => `${n}×${w} kg`).join(" + ")} = ${d.kit.total} kg of plates</span></div>
    <div class="card">
      <p class="muted small">Every recommended weight comes from these lists, so you are never told to lift something you can't load. Edit plates and bar weights in Settings.</p>
      ${ladders}
    </div>`}`;

  $$("[data-preview]", page).forEach((b) => b.addEventListener("click", () => previewDay(b.dataset.preview, d.location)));
  $$("[data-place]", page).forEach((b) => b.addEventListener("click", () => { planPlace = b.dataset.place; plan(); }));
}

async function previewDay(key, location) {
  const p = await api(`/api/day/${key}?location=${location || ""}`);
  const rows = p.blocks.filter((b) => b.type === "exercise").map((b) => `<tr>
      <td><b>${esc(b.move.name)}</b><div class="small muted">${esc(b.target.reason)}</div></td>
      <td>${esc(prescription(b.move, b.target, b.sets))}</td><td class="n">${esc(b.move.weighted ? b.weight_text : "BW")}</td></tr>`).join("");
  showModal(`<div class="sheet-head"><div><h3>${esc(p.title)} · ${esc(p.focus)}</h3><div class="small muted">${esc(p.location_label)}</div></div><span class="spacer"></span>
      <button class="btn small primary" data-start="${key}">Do this workout now</button>
      <button class="icon-btn" data-close>${icon("close")}</button></div>
    <div style="padding:16px 20px 20px"><p class="muted small">About ${p.estimate_min} minutes including warm-up and cool-down.</p>
      <div class="table-wrap"><table class="t"><tr><th>Exercise</th><th>Sets</th><th style="text-align:right">Weight</th></tr>${rows}</table></div></div>`,
  (e) => {
    const b = e.target.closest("[data-start]");
    if (b) { hideModal(); startWorkout(b.dataset.start, p.location); }
  });
}

// ============================================================== PROGRESS

async function progress() {
  const d = await api("/api/progress");
  const todayStr = d.calendar[d.calendar.length - 1]?.date;
  // Pad the grid so columns are Sunday-first weeks.
  const first = new Date(d.calendar[0].date + "T12:00:00").getDay();
  const cells = Array(first).fill(`<i style="visibility:hidden"></i>`).concat(
    d.calendar.map((c) => `<i class="${c.kind || ""} ${c.date === todayStr ? "today" : ""}" title="${esc(fmtDate(c.date))}${c.kind ? ": " + c.kind : ""}"></i>`));

  const ex = d.exercises.map((e, i) => {
    const vals = e.series.map((s) => e.hold ? s.seconds : e.weighted ? s.e1rm : s.best_reps);
    const cur = e.hold ? `${e.series[e.series.length - 1].seconds || 0}s` : e.weighted ? `${e.current_weight ?? "–"} kg` : `${Math.max(...e.last_reps)} reps`;
    return `<div class="ex-prog" data-i="${i}"><div><div class="name">${esc(e.name)}</div>
        <div class="small muted">${e.sessions} session${e.sessions > 1 ? "s" : ""} · last ${esc(fmtDate(e.last_date))}${e.weighted && e.first_weight && e.current_weight > e.first_weight ? ` · <span style="color:var(--accent)">+${+(e.current_weight - e.first_weight).toFixed(2)} kg</span>` : ""}</div></div>
      <div class="spark">${sparkline(vals)}</div><div class="num" style="text-align:right;font-weight:700">${esc(cur)}</div></div>
      <div class="ex-detail hidden" id="exd-${i}"></div>`;
  }).join("");

  const recent = d.recent.map((s) => `<tr><td>${esc(fmtDate(s.date))}</td><td><b>${esc(s.title)}</b>${s.status === "partial" ? ' <span class="badge">ended early</span>' : ""}${s.location && s.location !== "dumbbells" ? ` <span class="badge">${s.location === "floor" ? "Floor only" : "No dumbbells"}</span>` : ""}</td>
      <td class="n">${s.total_sets}</td><td class="n">${Math.round(s.duration_min)} min</td><td class="n">${Math.round(s.volume_kg)} kg</td></tr>`).join("");

  page.innerHTML = `
    <div class="stats">
      <div class="stat"><div class="l">Workouts</div><div class="v">${d.total_workouts}</div><div class="s">all time</div></div>
      <div class="stat"><div class="l">This week</div><div class="v">${d.this_week}<span class="small muted"> / 5</span></div><div class="s">training days</div></div>
      <div class="stat"><div class="l">Streak</div><div class="v">${d.streak_weeks}</div><div class="s">weeks with 3+ workouts</div></div>
      <div class="stat"><div class="l">Volume lifted</div><div class="v">${d.total_volume.toLocaleString()}</div><div class="s">kg total</div></div>
    </div>
    <div class="section-title"><h2>Consistency</h2><span class="muted small">Last 12 weeks · <span style="color:var(--accent)">■</span> workout <span style="color:var(--info)">■</span> mobility</span></div>
    <div class="card"><div class="heat">${cells.join("")}</div></div>
    <div class="section-title"><h2>Strength by exercise</h2><span class="muted small">Trend uses an estimated one-rep max, for direction only</span></div>
    <div class="card flush">${ex || `<div class="empty"><h3>No lifts logged yet</h3><p>Finish your first workout and your progress appears here.</p></div>`}</div>
    <div class="section-title"><h2>Recent sessions</h2></div>
    <div class="card flush">${recent ? `<div class="table-wrap"><table class="t"><tr><th>Date</th><th>Workout</th><th style="text-align:right">Sets</th><th style="text-align:right">Time</th><th style="text-align:right">Volume</th></tr>${recent}</table></div>`
      : `<div class="empty"><p>Completed workouts are listed here.</p></div>`}</div>`;

  $$(".ex-prog", page).forEach((row) => row.addEventListener("click", () => {
    const i = +row.dataset.i, e = d.exercises[i], box = $(`#exd-${i}`);
    if (!box.classList.contains("hidden")) { box.classList.add("hidden"); return; }
    const pts = e.series.map((s) => ({ x: s.date, label: fmtDate(s.date, { day: "numeric", month: "short" }),
      y: e.hold ? s.seconds : e.weighted ? s.e1rm : s.best_reps }));
    const unit = e.hold ? "s" : e.weighted ? " kg" : " reps";
    const rows = [...e.series].reverse().slice(0, 8).map((s) => `<tr><td>${esc(fmtDate(s.date))}</td>
      <td>${s.reps.map((r, j) => `<span class="rating-dot ${s.ratings[j] || ""}"></span>${e.hold ? (s.seconds || r) + "s" : r}`).join(" &nbsp;")}</td>
      <td class="n">${s.weight ? s.weight + " kg" : "–"}</td></tr>`).join("");
    box.innerHTML = `${lineChart(pts, { fmt: (v) => `${+v.toFixed(1)}${unit}`, label: e.name })}
      <div class="table-wrap" style="margin-top:10px"><table class="t"><tr><th>Date</th><th>Sets (reps)</th><th style="text-align:right">Weight</th></tr>${rows}</table></div>
      <button class="btn small" style="margin-top:10px" data-open="${e.id}">How to do it</button>`;
    box.classList.remove("hidden");
    $("[data-open]", box).addEventListener("click", (ev) => { ev.stopPropagation(); openMove(e.id); });
  }));
}

// ============================================================== LIBRARY

let libState = { q: "", group: "", kind: "strength", place: "" };

async function library() {
  const d = await api("/api/library");
  const kinds = [["strength", "Strength"], ["warmup", "Warm-up"], ["stretch", "Stretches"], ["mobility", "Mobility"], ["", "All"]];
  const groups = ["chest", "back", "shoulders", "arms", "legs", "glutes", "core"];

  page.innerHTML = `
    <div class="section-title"><h1>Exercise library</h1><span class="muted small">${d.moves.length} movements for your equipment</span></div>
    <div class="filters">
      <input class="search" id="q" placeholder="Search exercises or muscles…" value="${esc(libState.q)}">
      ${kinds.map(([k, l]) => `<button class="chip ${libState.kind === k ? "on" : ""}" data-kind="${k}">${l}</button>`).join("")}
    </div>
    <div class="filters" id="groups" ${libState.kind === "strength" || libState.kind === "" ? "" : "hidden"}>
      <button class="chip ${!libState.group ? "on" : ""}" data-group="">All muscles</button>
      ${groups.map((g) => `<button class="chip ${libState.group === g ? "on" : ""}" data-group="${g}">${esc(d.groups[g])}</button>`).join("")}
    </div>
    <div class="filters">
      <span class="small muted">Can do it with:</span>
      <button class="chip ${!libState.place ? "on" : ""}" data-lplace="">Anything</button>
      ${d.locations.map((l) => `<button class="chip ${libState.place === l.key ? "on" : ""}" data-lplace="${l.key}">${esc(l.short)}</button>`).join("")}
    </div>
    <div class="grid-cards" id="lib"></div>`;

  const draw = () => {
    const q = libState.q.toLowerCase();
    const list = d.moves.filter((m) =>
      (!libState.kind || m.kind === libState.kind) &&
      (!libState.group || m.group === libState.group) &&
      (!libState.place || m.places.includes(libState.place)) &&
      (!q || m.name.toLowerCase().includes(q) || m.muscles.join(" ").toLowerCase().includes(q)));
    $("#lib").innerHTML = list.map((m) => `<button class="lib-card" data-id="${m.id}">
        <div class="img">${m.slug ? `<img src="${thumbURL(m.slug)}" alt="" loading="lazy">` : `<span class="muted">No image</span>`}</div>
        <div class="body"><div class="n">${esc(m.name)}</div><div class="m">${esc(m.muscles.slice(0, 3).join(", "))}</div>
          <div class="tags"><span class="badge">${esc(MODE_LABEL[m.mode])}</span>${m.tracker ? `<span class="badge tracked">Camera</span>` : ""}</div></div></button>`).join("")
      || `<div class="empty">No matches.</div>`;
  };
  draw();
  $("#q").addEventListener("input", (e) => { libState.q = e.target.value; draw(); });
  $$("[data-kind]", page).forEach((b) => b.addEventListener("click", () => { libState.kind = b.dataset.kind; libState.group = ""; library(); }));
  $$("[data-group]", page).forEach((b) => b.addEventListener("click", () => { libState.group = b.dataset.group; library(); }));
  $$("[data-lplace]", page).forEach((b) => b.addEventListener("click", () => { libState.place = b.dataset.lplace; library(); }));
  $("#lib").addEventListener("click", (e) => { const c = e.target.closest("[data-id]"); if (c) openMove(c.dataset.id); });
}

async function openMove(id) {
  const d = await api(`/api/library/${id}`);
  const m = d.move;
  const opt = (label, list) => list.length ? `<div class="label-sm">${label}</div><div class="link-list">${list.map((o) => `<button class="chip" data-move="${o.id}">${esc(o.name)}</button>`).join("")}</div>` : "";
  const hist = d.history.length ? `<div class="label-sm">Your recent sessions</div><table class="t">${d.history.map((h) => `<tr><td>${esc(fmtDate(h.date))}</td><td>${h.sets.map((s) => `<span class="rating-dot ${s.rating || ""}"></span>${s.seconds ? s.seconds + "s" : (s.weight ? `${s.weight}×${s.reps}` : s.reps)}`).join(" &nbsp;")}</td></tr>`).join("")}</table>` : "";
  showModal(`<div class="sheet-head"><div><h3>${esc(m.name)}</h3><div class="small muted">${esc(m.muscles.join(" · "))}</div></div>
      <span class="spacer"></span><button class="icon-btn" data-close>${icon("close")}</button></div>
    <div class="sheet-body">
      <div>${demoHTML(m.slug)}
        <div class="row wrap" style="margin-top:12px">
          <span class="badge">${esc(MODE_LABEL[m.mode])}</span>
          ${m.per_side ? `<span class="badge">Each side</span>` : ""}
          ${m.hold ? `<span class="badge">Timed hold</span>` : ""}
          ${m.tracker ? `<span class="badge tracked">Camera counts reps</span>` : ""}
        </div>
        ${m.purpose ? `<p class="muted" style="margin-top:12px">${esc(m.purpose)}</p>` : ""}
        ${m.tracker ? `<p class="small" style="margin-top:8px"><b>Camera:</b> <span class="muted">${esc(m.view_text)}</span></p>` : ""}
        ${opt("Easier", d.options.easier)}${opt("Harder", d.options.harder)}${opt("Similar", d.options.similar)}
      </div>
      <div>${moveInstructions(m)}${hist}</div>
    </div>`, (e) => {
    const b = e.target.closest("[data-move]");
    if (b) openMove(b.dataset.move);
  });
}

// ============================================================== NUTRITION

let nutDay = null;

async function nutrition() {
  const d = await api(`/api/nutrition${nutDay ? `?day=${nutDay}` : ""}`);
  const meals = d.sample_day.map((m) => `<tr><td><b>${esc(m.meal)}</b></td>
      <td>${m.items.map((i) => `${esc(i.name)} <span class="muted small">${esc(i.qty)}</span>${i.note ? ` <span class="small" style="color:var(--accent)">${esc(i.note)}</span>` : ""}`).join("<br>")}</td>
      <td class="n">${m.kcal}</td><td class="n">${m.protein} g</td></tr>`).join("");
  page.innerHTML = `
    <div class="section-title"><h1>Nutrition</h1>
      <div class="row"><button class="chip ${d.training_day ? "on" : ""}" data-nd="training">Training day</button>
      <button class="chip ${!d.training_day ? "on" : ""}" data-nd="rest">Rest day</button></div></div>
    <div class="stats">
      <div class="stat"><div class="l">Calories</div><div class="v">${d.kcal.toLocaleString()}</div><div class="s">per day, for slow lean gain</div></div>
      <div class="stat"><div class="l">Protein</div><div class="v">${d.protein} g</div><div class="s">1.8 g per kg bodyweight</div></div>
      <div class="stat"><div class="l">Bodyweight</div><div class="v">${d.bodyweight} kg</div><div class="s">update it in Settings</div></div>
      <div class="stat"><div class="l">Goal pace</div><div class="v">+0.3</div><div class="s">kg per week</div></div>
    </div>
    <div class="grid-2" style="margin-top:20px">
      <div>
        <div class="section-title"><h2>A day that hits the target</h2><span class="muted small">${d.sample_kcal} kcal · ${d.sample_protein} g protein</span></div>
        <div class="card flush"><div class="table-wrap"><table class="t"><tr><th>Meal</th><th>Food</th><th style="text-align:right">kcal</th><th style="text-align:right">Protein</th></tr>${meals}</table></div></div>
      </div>
      <aside class="stack">
        <div class="card"><h3>Three changes that matter most</h3>
          ${d.changes.map((c, i) => `<div class="kv" style="display:block"><b>${i + 1}. ${esc(c.what)}</b>
            <div class="small muted">${esc(c.why)}</div><div class="small" style="color:var(--accent)">+${c.kcal} kcal, +${c.protein} g protein</div></div>`).join("")}</div>
        <div class="card"><h3>${d.training_day ? "On training days" : "On rest days"}</h3>
          ${d.notes.map((n) => `<div class="kv" style="display:block"><b>${esc(n.title)}</b><div class="small muted">${esc(n.body)}</div></div>`).join("")}</div>
      </aside>
    </div>`;
  $$("[data-nd]", page).forEach((b) => b.addEventListener("click", () => { nutDay = b.dataset.nd; nutrition(); }));
}

// ============================================================== SETTINGS

async function settings() {
  const d = await api("/api/profile");
  const p = d.profile;
  const days = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];
  const plates = Object.entries(p.equipment.plates).sort((a, b) => b[0] - a[0]);
  const sw = (id, on) => `<label class="switch"><input type="checkbox" id="${id}" ${on ? "checked" : ""}><span></span></label>`;

  page.innerHTML = `
    <div class="section-title"><h1>Settings</h1><button class="btn primary" id="save">Save changes</button></div>
    ${d.media_ok ? "" : `<div class="notice">The exercise video library (Asterisk) was not found at its usual location, so demos are unavailable. Instructions still work.</div>`}

    <div class="section-title"><h2>You</h2></div>
    <div class="card"><div class="form-grid">
      <div class="field"><label>Bodyweight (kg)</label><input type="number" step="0.1" id="bw" value="${p.bodyweight_kg}"><div class="hint">Drives your calorie and protein targets</div></div>
      <div class="field"><label>Height (cm)</label><input type="number" id="height" value="${p.height_cm}"></div>
      <div class="field"><label>Age</label><input type="number" id="age" value="${p.age}"></div>
      <div class="field"><label>Sex (for calorie maths)</label><select id="sex">
        <option value="male" ${p.sex === "male" ? "selected" : ""}>Male</option><option value="female" ${p.sex === "female" ? "selected" : ""}>Female</option></select></div>
    </div></div>

    <div class="section-title"><h2>Training days</h2><span class="muted small">The program is built for 5 days. Workouts fill your training days in order: Upper A, Lower A, Upper B, Lower B, Arms & Core.</span></div>
    <div class="card"><div class="daypick">${days.map((dd) => `<button class="chip ${p.training_days.includes(dd) ? "on" : ""}" data-day="${dd}">${WEEKDAY_SHORT[dd]}</button>`).join("")}</div></div>

    <div class="section-title"><h2>Equipment</h2><span class="muted small">Weigh the bare rod, connector and a collar once — every recommended weight depends on them</span></div>
    <div class="card">
      <div class="form-grid">
        <div class="field"><label>Dumbbell rod (kg)</label><input type="number" step="0.05" id="rod" value="${p.equipment.rod_kg}"></div>
        <div class="field"><label>Connector (kg)</label><input type="number" step="0.05" id="connector" value="${p.equipment.connector_kg}"></div>
        <div class="field"><label>One collar / screw (kg)</label><input type="number" step="0.05" id="collar" value="${p.equipment.collar_kg}"></div>
      </div>
      <div class="label-sm" style="margin-top:20px">Plates</div>
      <div id="plates" class="stack">${plates.map(([w, n]) => plateRow(w, n)).join("")}</div>
      <button class="btn small" id="add-plate" style="margin-top:10px">Add a plate size</button>
      <div class="small muted" style="margin-top:12px">Current ranges: one dumbbell ${d.ranges.db1.join("–")} kg · pair ${d.ranges.db2.join("–")} kg each · barbell ${d.ranges.bb.join("–")} kg</div>
      <div style="margin-top:16px">
        <div class="toggle-row"><div><b>Flat bench</b></div>${sw("bench", p.equipment.bench)}</div>
        <div class="toggle-row"><div><b>Pull-up bar</b></div>${sw("bar", p.equipment.pullup_bar)}</div>
      </div>
    </div>

    <div class="section-title"><h2>Training without dumbbells</h2><span class="muted small">What you can count on at each place — the bodyweight program uses what is there</span></div>
    <div class="card"><div class="form-grid">${d.locations.filter((l) => l.key !== "dumbbells").map((l) => `<div>
        <div class="row" style="gap:10px;margin-bottom:4px"><span class="place-ico">${icon(PLACE_ICON[l.key])}</span><b>${esc(l.label)}</b></div>
        ${Object.entries(d.kit_labels).map(([k, label]) => `<div class="toggle-row"><div class="small">${esc(label)}</div>${sw(`away-${l.key}-${k}`, p.away_kit[l.key][k])}</div>`).join("")}
      </div>`).join("")}</div></div>

    <div class="section-title"><h2>Camera and voice</h2></div>
    <div class="card">
      <div class="toggle-row"><div><b>Voice coach</b><div class="small muted">Spoken cues, rep counts and rest countdowns</div></div>${sw("voice", p.voice.enabled)}</div>
      <div class="toggle-row"><div><b>Mirror camera</b><div class="small muted">Shows you like a mirror</div></div>${sw("mirror", p.camera.mirror)}</div>
      <div class="toggle-row"><div><b>Pose model</b><div class="small muted">Full is the best balance. Lite is faster on a slow laptop; Heavy is the most accurate.</div></div>
        <select id="model" class="field" style="width:auto;padding:8px 10px;border-radius:9px;border:1px solid var(--border);background:var(--surface-2)">
          ${["lite", "full", "heavy"].map((m) => `<option ${p.camera.model === m ? "selected" : ""}>${m}</option>`).join("")}</select></div>
      <div class="toggle-row"><div><b>Test mode</b><div class="small muted">Feed the demo video to the rep counter instead of your webcam — for checking the camera features without standing up.</div></div>${sw("testvid", p.camera.test_video)}</div>
    </div>
    <p class="small muted" style="margin-top:16px">Everything stays on this computer: settings in <code>data/profile.json</code>, your log in <code>data/sets.jsonl</code> and <code>data/sessions.jsonl</code>.</p>`;

  $$("[data-day]", page).forEach((b) => b.addEventListener("click", () => b.classList.toggle("on")));
  $("#add-plate").addEventListener("click", () => $("#plates").insertAdjacentHTML("beforeend", plateRow("", 2)));
  $("#plates").addEventListener("click", (e) => { if (e.target.closest("[data-rm]")) e.target.closest(".row").remove(); });
  $("#save").addEventListener("click", async () => {
    const plateMap = {};
    $$("#plates .row").forEach((r) => {
      const w = parseFloat($(".pw", r).value), n = parseInt($(".pn", r).value, 10);
      if (w > 0 && n > 0) plateMap[String(w)] = n;
    });
    const patch = {
      bodyweight_kg: +$("#bw").value, height_cm: +$("#height").value, age: +$("#age").value, sex: $("#sex").value,
      training_days: $$("[data-day].on", page).map((b) => b.dataset.day),
      equipment: { rod_kg: +$("#rod").value, connector_kg: +$("#connector").value, collar_kg: +$("#collar").value,
        plates: plateMap, bench: $("#bench").checked, pullup_bar: $("#bar").checked },
      away_kit: Object.fromEntries(Object.entries(p.away_kit).map(([loc, kit]) =>
        [loc, Object.fromEntries(Object.keys(kit).map((k) => [k, $(`#away-${loc}-${k}`).checked]))])),
      camera: { model: $("#model").value, mirror: $("#mirror").checked, test_video: $("#testvid").checked },
      voice: { enabled: $("#voice").checked },
    };
    try { await put("/api/profile", patch); toast("Saved"); settings(); } catch (e) { toast(e.message); }
  });
}

function plateRow(w, n) {
  return `<div class="row"><div class="field" style="flex:1"><input class="pw" type="number" step="0.25" value="${esc(w)}" placeholder="Plate kg"></div>
    <span class="muted">×</span><div class="field" style="width:110px"><input class="pn" type="number" value="${esc(n)}" placeholder="Count"></div>
    <button class="btn small ghost" data-rm title="Remove">Remove</button></div>`;
}

// ============================================================== modal

function showModal(html, onClick) {
  const modal = $("#modal");
  modal.innerHTML = `<div class="sheet">${html}</div>`;
  modal.hidden = false;
  modal.onclick = (e) => {
    if (e.target === modal || e.target.closest("[data-close]")) { hideModal(); return; }
    onClick?.(e);
  };
}
function hideModal() {
  const modal = $("#modal");
  modal.hidden = true;
  modal.innerHTML = "";
}
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("#modal").hidden && $("#player").hidden) hideModal();
});

// ============================================================== boot

(async () => {
  await route();
  // Reopen a workout in progress after a page refresh.
  try {
    const s = await api("/api/session");
    if (s.active && s.phase !== "done" && !s.paused) player.open(s);
  } catch { /* fine */ }
})();
