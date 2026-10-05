// Hand-rolled SVG charts. The app runs offline, so no chart library.

import { esc } from "./ui.js";

export function lineChart(points, { height = 220, fmt = (v) => v, label = "" } = {}) {
  // points: [{x: "2026-10-05", y: 12.3}]
  const pts = points.filter((p) => p.y != null);
  if (pts.length === 0) return `<div class="muted small">Not enough data yet.</div>`;
  const W = 1000, H = height, L = 52, R = 14, T = 14, B = 28;
  let lo = Math.min(...pts.map((p) => p.y)), hi = Math.max(...pts.map((p) => p.y));
  if (hi - lo < 1e-6) { lo -= 1; hi += 1; }
  const pad = (hi - lo) * 0.12;
  lo -= pad; hi += pad;
  const x = (i) => L + (pts.length === 1 ? (W - L - R) / 2 : (i * (W - L - R)) / (pts.length - 1));
  const y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  const ticks = [lo + pad, (lo + hi) / 2, hi - pad];
  const path = pts.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.y).toFixed(1)}`).join(" ");
  const area = `${path} L${x(pts.length - 1).toFixed(1)},${H - B} L${x(0).toFixed(1)},${H - B} Z`;
  const every = Math.max(1, Math.ceil(pts.length / 6));
  return `<div class="chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}">
    ${ticks.map((t) => `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(t)}" y2="${y(t)}"/>
      <text x="${L - 8}" y="${y(t) + 4}" text-anchor="end">${esc(fmt(t))}</text>`).join("")}
    <path class="area" d="${area}"/>
    <path class="line" d="${path}"/>
    ${pts.map((p, i) => `<circle class="pt" cx="${x(i)}" cy="${y(p.y)}" r="4"><title>${esc(p.x)}: ${esc(fmt(p.y))}</title></circle>`).join("")}
    ${pts.map((p, i) => (i % every === 0 || i === pts.length - 1)
      ? `<text x="${x(i)}" y="${H - 8}" text-anchor="middle">${esc(p.label ?? p.x)}</text>` : "").join("")}
  </svg></div>`;
}

export function sparkline(values) {
  const v = values.filter((x) => x != null);
  if (v.length < 2) return "";
  const W = 140, H = 36, P = 3;
  let lo = Math.min(...v), hi = Math.max(...v);
  if (hi - lo < 1e-6) { lo -= 1; hi += 1; }
  const d = v.map((y, i) => `${i ? "L" : "M"}${(P + (i * (W - 2 * P)) / (v.length - 1)).toFixed(1)},${(P + (1 - (y - lo) / (hi - lo)) * (H - 2 * P)).toFixed(1)}`).join(" ");
  return `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true"><path class="line" d="${d}"/></svg>`;
}
