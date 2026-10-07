"use strict";
/* ============================================================
   Panorama Sales Intelligence: client
   ============================================================ */
const $ = (s, e = document) => e.querySelector(s);
const $$ = (s, e = document) => [...e.querySelectorAll(s)];
const FONT = '"Inter","Segoe UI Variable","Segoe UI",system-ui,sans-serif';
const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const NET = "Delivered,Processing", ALLST = "Delivered,Processing,Returned,Cancelled";
const NATURAL = ["year","quarter","year_month","discount","season"];
const S = { token: sessionStorage.getItem("tok") || "", me: null, meta: null, view: "overview", nav: 0, charts: [], timer: null,
  f: { year:"", category:"", region:"", segment:"", status: NET },
  explore: { dim:"category", metric:"revenue", type:"bar", top:10 },
  compare: { dim:"region", a:"", b:"" },
  table: { page:0, size:15, search:"", sort:"", dir:"desc" },
  chat: [], busy:false, health:null };

/* ---------- formatting ---------- */
const nf = new Intl.NumberFormat("en-US"), nf2 = new Intl.NumberFormat("en-US", {minimumFractionDigits:2, maximumFractionDigits:2});
const esc = t => String(t ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function compact(x){ const a = Math.abs(x); return a>=1e9 ? (x/1e9).toFixed(2)+"B" : a>=1e6 ? (x/1e6).toFixed(2)+"M" : a>=1e4 ? (x/1e3).toFixed(1)+"K" : nf.format(Math.round(x)); }
function fmtBy(k){ return k==="pct" ? v => (+v).toFixed(1)+"%" : k==="money2" ? v => Math.abs(v)<1e4 ? nf2.format(v) : compact(v) : k==="money" ? compact : v => nf.format(Math.round(v)); }
const full = (k, v) => k==="pct" ? (+v).toFixed(1)+"%" : k==="count" ? nf.format(Math.round(v)) : nf2.format(v);
const pretty = c => c.replace(/_pct$/, " %").replace(/_/g, " ").replace(/\b\w/g, m => m.toUpperCase()).replace(/\bId\b/, "ID");
const cssv = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const hexA = (hex, a) => { if (hex[0] !== "#") return hex; const n = parseInt(hex.slice(1), 16); return `rgba(${n>>16&255},${n>>8&255},${n&255},${a})`; };
const palette = () => [cssv("--accent"), cssv("--accent2"), "#34d399", "#fbbf24", "#fb7185", "#c084fc", "#f472b6", "#60a5fa"];

/* ---------- icons ---------- */
const ICON = {
  overview:'<rect x="3" y="3" width="7" height="9" rx="2"/><rect x="14" y="3" width="7" height="5" rx="2"/><rect x="14" y="12" width="7" height="9" rx="2"/><rect x="3" y="16" width="7" height="5" rx="2"/>',
  explore:'<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5z"/>',
  compare:'<path d="M8 3 4 7l4 4"/><path d="M4 7h16"/><path d="m16 21 4-4-4-4"/><path d="M20 17H4"/>',
  insights:'<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.4 1 2.5h6c0-1.1.3-1.8 1-2.5A6 6 0 0 0 12 3z"/>',
  data:'<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 10h18M9 4v16"/>',
  chat:'<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
  access:'<path d="M12 3 4 6v6c0 5 3.4 8 8 9 4.6-1 8-4 8-9V6z"/><path d="m9 12 2 2 4-4"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon:'<path d="M21 13A9 9 0 1 1 11 3a7 7 0 0 0 10 10z"/>',
  logout:'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
  lock:'<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  download:'<path d="M12 3v12m0 0 4-4m-4 4-4-4M4 21h16"/>',
  send:'<path d="m22 2-11 11M22 2l-7 20-4-9-9-4z"/>',
  swap:'<path d="M7 4 3 8l4 4M3 8h14M17 20l4-4-4-4M21 16H7"/>',
  orders:'<path d="M6 7h12l1 13H5z"/><path d="M9 7a3 3 0 0 1 6 0"/>',
  revenue:'<path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/>',
  profit:'<path d="m3 17 6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
  margin:'<path d="m19 5-14 14"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
  aov:'<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.2"/>',
  discount:'<path d="m19 5-14 14"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
  returns:'<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
  risk:'<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17.5v.01"/>',
  geo:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
  loss:'<path d="m3 7 6 6 4-4 8 8"/><path d="M15 17h6v-6"/>',
  ship:'<path d="M2 6h12v10H2zM14 10h4l4 3v3h-8"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
  segment:'<circle cx="9" cy="8" r="3.5"/><path d="M2 20c0-4 3-6 7-6s7 2 7 6M17 5a3.5 3.5 0 0 1 0 6.5M22 20c0-3-1.5-5-4-5.5"/>',
  product:'<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
  time:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'
};
const svg = (n, cls = "") => `<svg viewBox="0 0 24 24" class="${cls}">${ICON[n] || ""}</svg>`;

/* ---------- small UI helpers ---------- */
function toast(msg, tone = "") { const t = document.createElement("div"); t.className = "toast " + tone; t.textContent = msg; $("#toasts").appendChild(t);
  setTimeout(() => { t.style.transition = "all .4s"; t.style.opacity = 0; t.style.transform = "translateX(30px)"; setTimeout(() => t.remove(), 400); }, 3600); }
function countUp(el) { const to = +el.dataset.to, f = fmtBy(el.dataset.fmt || "count"), t0 = performance.now(), dur = 1400;
  const tick = t => { const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 4); el.textContent = f(to * e); if (p < 1) requestAnimationFrame(tick); }; requestAnimationFrame(tick); }
function spark(vals, color) { if (!vals || vals.length < 2) return ""; const w = 200, h = 46, mn = Math.min(...vals), mx = Math.max(...vals), rg = (mx - mn) || 1;
  const pts = vals.map((v, i) => [i / (vals.length - 1) * w, h - 6 - ((v - mn) / rg) * (h - 16)]);
  const line = "M" + pts.map(p => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" L"), id = "g" + Math.random().toString(36).slice(2, 8);
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="--c:${color}"><defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity=".35"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs><path class="ar" style="fill:url(#${id})" d="${line} L${w},${h} L0,${h}Z"/><path class="ln" pathLength="1" d="${line}"/></svg>`; }
function ring(label, val, color) { return `<div class="rg"><div class="ring" style="--c:${color}"><svg viewBox="0 0 36 36"><circle class="tr" cx="18" cy="18" r="15.9155"/><circle class="pg" cx="18" cy="18" r="15.9155" pathLength="100" data-p="${Math.min(100, val)}"/></svg><b class="num" data-to="${val}" data-fmt="pct">0%</b></div><span class="rl">${label}</span></div>`; }
function miniBars(bars, fk) { const mx = Math.max(...bars.map(b => Math.abs(b.value))) || 1, f = fmtBy(fk);
  return `<div class="mbars">` + bars.map(b => `<div class="mb"><span class="l" title="${esc(b.label)}">${esc(b.label)}</span><div class="t"><i data-w="${Math.abs(b.value) / mx * 100}" ${b.value < 0 ? 'style="background:linear-gradient(90deg,#fb7185,#f43f5e)"' : ""}></i></div><span class="v">${f(b.value)}</span></div>`).join("") + `</div>`; }
function animateBars(root) { $$("[data-w]", root).forEach((i, k) => setTimeout(() => i.style.width = i.dataset.w + "%", 150 + k * 45)); }
function animateRings(root) { setTimeout(() => $$(".pg", root).forEach(c => c.style.strokeDashoffset = 100 - (+c.dataset.p)), 80); }
const skeleton = () => `<div class="grid kpis">${'<div class="skel" style="height:132px"></div>'.repeat(5)}</div><div class="grid"><div class="skel" style="grid-column:span 8;height:320px"></div><div class="skel" style="grid-column:span 4;height:320px"></div><div class="skel" style="grid-column:span 6;height:300px"></div><div class="skel" style="grid-column:span 6;height:300px"></div></div>`;

/* ---------- API ---------- */
async function api(path, opt = {}) {
  const r = await fetch(path, { ...opt, headers: { "Content-Type": "application/json", Authorization: "Bearer " + S.token, ...(opt.headers || {}) } });
  if (r.status === 401) { sessionStorage.removeItem("tok"); location.reload(); throw new Error("401"); }
  if (!r.ok) { const e = await r.json().catch(() => ({})); toast(e.detail || "Request failed", "bad"); throw new Error(e.detail || r.status); }
  return r;
}
const getJ = async p => (await api(p)).json();
function qs(extra = {}, mode = "") {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(S.f)) if (v) p.set(k, v);
  if (mode === "nostatus" || (mode === "table" && S.f.status === NET)) p.delete("status");
  for (const [k, v] of Object.entries(extra)) p.set(k, v);
  return p.toString();
}
const statusNote = () => S.f.status === NET ? "net of cancelled and returned" : S.f.status === ALLST ? "all orders, gross" : S.f.status === "Delivered" ? "delivered orders only" : "selected statuses";

/* ---------- charts ---------- */
function destroyCharts() { S.charts.forEach(c => { try { c.destroy(); } catch (e) {} }); S.charts = []; }
function makeChart(cv, c) {
  const P = palette(), ink = cssv("--muted"), grid = cssv("--grid"), bad = "#fb7185";
  const isDo = c.type === "doughnut", isLine = c.type === "line", hz = c.type === "hbar", f = fmtBy(c.fmt);
  const datasets = c.series.map((s, i) => {
    const col = P[i % P.length];
    const SEM = { Delivered: "#34d399", Processing: P[0], Returned: "#fbbf24", Cancelled: "#fb7185" };
    if (isDo) return { label: s.name, data: s.values, backgroundColor: c.labels.map((l, j) => SEM[l] || P[j % P.length]), borderWidth: 0, spacing: 3, borderRadius: 7, hoverOffset: 10 };
    if (isLine) return { label: s.name, data: s.values, borderColor: col, borderWidth: 2.6, tension: .38, pointRadius: 0, pointHoverRadius: 5, pointHoverBackgroundColor: col, fill: true,
      backgroundColor: x => { const a = x.chart.chartArea; if (!a) return "transparent"; const g = x.chart.ctx.createLinearGradient(0, a.top, 0, a.bottom); g.addColorStop(0, hexA(col, .34)); g.addColorStop(1, hexA(col, 0)); return g; } };
    return { label: s.name, data: s.values, borderRadius: 9, borderSkipped: false, maxBarThickness: hz ? 22 : 38,
      backgroundColor: x => { const a = x.chart.chartArea; if (!a) return col; if (x.raw < 0) return hexA(bad, .85);
        const g = hz ? x.chart.ctx.createLinearGradient(a.left, 0, a.right, 0) : x.chart.ctx.createLinearGradient(0, a.top, 0, a.bottom);
        if (hz) { g.addColorStop(0, hexA(col, .35)); g.addColorStop(1, col); } else { g.addColorStop(0, col); g.addColorStop(1, hexA(col, .5)); } return g; } };
  });
  const total = isDo ? c.series[0].values.reduce((a, b) => a + b, 0) : 0;
  const center = { id: "center", afterDatasetsDraw(ch) { const a = ch.getDatasetMeta(0).data[0]; if (!a) return; const x = ch.ctx; x.save(); x.textAlign = "center"; x.textBaseline = "middle";
    x.fillStyle = cssv("--text"); x.font = "800 24px " + FONT; x.fillText(f(total), a.x, a.y - 6); x.fillStyle = ink; x.font = "700 10px " + FONT; x.fillText(c.series[0].name.toUpperCase(), a.x, a.y + 16); x.restore(); } };
  const axis = { grid: { color: grid }, border: { display: false }, ticks: { color: ink, font: { size: 11 } } };
  const scales = isDo ? {} : hz ? { x: { ...axis, beginAtZero: true, ticks: { ...axis.ticks, callback: v => f(v) } }, y: { ...axis, grid: { display: false } } }
    : { x: { ...axis, grid: { display: false }, ticks: { ...axis.ticks, maxRotation: 0, autoSkip: isLine || c.labels.length > 14, maxTicksLimit: 10 } }, y: { ...axis, beginAtZero: true, ticks: { ...axis.ticks, callback: v => f(v) } } };
  const ch = new Chart(cv.getContext("2d"), { type: isDo ? "doughnut" : isLine ? "line" : "bar", data: { labels: c.labels, datasets }, plugins: isDo ? [center] : [],
    options: { responsive: true, maintainAspectRatio: false, indexAxis: hz ? "y" : "x", cutout: isDo ? "72%" : undefined, interaction: { mode: isDo ? "nearest" : "index", intersect: false },
      animation: { duration: 1300, easing: "easeOutQuart", delay: x => x.type === "data" && x.mode === "default" ? x.dataIndex * 42 + x.datasetIndex * 150 : 0 },
      plugins: { legend: { display: c.series.length > 1 || isDo, position: isDo ? "bottom" : "top", align: isDo ? "center" : "end", labels: { color: ink, usePointStyle: true, pointStyle: "circle", boxWidth: 7, padding: 14, font: { size: 11, family: FONT } } },
        tooltip: { backgroundColor: cssv("--tip"), titleColor: cssv("--text"), bodyColor: cssv("--text"), borderColor: cssv("--line"), borderWidth: 1, padding: 12, cornerRadius: 12, boxPadding: 5,
          callbacks: { label: x => ` ${isDo ? x.label : x.dataset.label}: ${full(c.fmt, x.raw)}` } } }, scales } });
  S.charts.push(ch); return ch;
}
function lazyCharts(root, specs) {
  const build = card => { const c = specs[+card.dataset.ix]; if (c && !card.dataset.done) { card.dataset.done = 1; makeChart($("canvas", card), c); } };
  const cards = $$("[data-ix]", root);
  if (!("IntersectionObserver" in window)) return cards.forEach(build);
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { io.unobserve(e.target); build(e.target); } }), { threshold: .12 });
  cards.forEach(c => io.observe(c));
}
function heatmap(h) { const mx = Math.max(...h.values.flat()) || 1, f = fmtBy(h.fmt); let k = 0;
  let html = `<div class="heat"><span></span>${h.cols.map(c => `<span>${MON[c - 1]}</span>`).join("")}`;
  h.rows.forEach((y, ri) => { html += `<span class="yr">${y}</span>`; h.values[ri].forEach((v, ci) => { html += `<div class="hm" style="--a:${(v / mx).toFixed(3)};--d:${k++}" title="${y} ${MON[ci]}: ${f(v)}"></div>`; }); });
  return html + "</div>"; }

/* ============================================================
   VIEWS
   ============================================================ */
const VIEWS = {
  overview: { title: "Overview", sub: "Performance at a glance", filters: true, render: vOverview },
  explore:  { title: "Explore",  sub: "Slice any metric by any dimension", filters: true, render: vExplore },
  compare:  { title: "Compare",  sub: "Put two segments side by side", filters: true, render: vCompare },
  insights: { title: "Insights", sub: "Findings from the data analysis", filters: true, render: vInsights },
  data:     { title: "Orders",   sub: "Browse, sort and export the rows you may access", filters: true, render: vData },
  chat:     { title: "Ask AI",   sub: "Plain-English questions, answered from your data", filters: false, render: vChat },
  access:   { title: "Access",   sub: "What this account can see, and why", filters: false, render: vAccess }
};

/* ----- Overview ----- */
async function vOverview(el, alive) {
  const d = await getJ("/api/dashboard?" + qs()); if (!alive()) return;
  const K = d.kpis, sp = d.spark, P = palette();
  const defs = [["orders","Orders","count","orders","orders","orders in view"], ["revenue",S.f.status===NET?"Net revenue":"Revenue","money2","revenue","revenue",statusNote()],
    ["profit","Profit","money2","profit","profit","revenue minus cost"], ["margin_pct","Margin","pct","margin_pct","margin","profit ÷ revenue"],
    ["avg_order_value","Avg order","money2","avg_order_value","aov","revenue per order"]].filter(x => K[x[0]] !== undefined);
  const hasHealth = K.return_rate_pct !== undefined, span = Math.floor(12 / (defs.length + (hasHealth ? 1 : 0))) || 12;
  let h = `<div class="grid kpis">`;
  defs.forEach((x, i) => h += `<article class="card kpi lift rise" style="--i:${i};grid-column:span ${span}"><div class="label">${svg(x[4])}${x[1]}</div><div class="value num" data-to="${K[x[0]]}" data-fmt="${x[2]}" title="${full(x[2], K[x[0]])}">0</div><div class="sub">${x[5]}</div>${spark(sp[x[3]], P[i % 2])}</article>`);
  if (hasHealth) h += `<article class="card kpi lift rise" style="--i:5;grid-column:span ${12 - span * defs.length}"><div class="label">${svg("returns")}Order health</div><div class="health" style="margin-top:6px">${ring("Returned", K.return_rate_pct, "#fbbf24")}${ring("Cancelled", K.cancel_rate_pct, "#fb7185")}</div></article>`;
  h += `</div><div class="grid">`;
  d.charts.forEach((c, i) => h += `<article class="card chart-card rise" data-ix="${i}" style="grid-column:span ${c.span};--i:${i + 4}"><header><h3>${esc(c.title)}</h3>${c.note ? `<span class="note">${esc(c.note)}</span>` : ""}</header><div class="chart"><canvas></canvas></div></article>`);
  h += `<article class="card chart-card rise" style="grid-column:span 6;--i:${d.charts.length + 4}"><header><h3>${esc(d.heatmap.title)}</h3><span class="note">darker = more</span></header>${heatmap(d.heatmap)}</article></div>`;
  el.innerHTML = h;
  $$(".num[data-to]", el).forEach(countUp); animateRings(el); lazyCharts(el, d.charts);
}

/* ----- Explore ----- */
async function vExplore(el, alive) {
  const m = S.meta, ex = S.explore;
  if (!m.dims.find(x => x.key === ex.dim)) ex.dim = m.dims[0].key;
  if (!m.metrics.find(x => x.key === ex.metric)) ex.metric = m.metrics[0].key;
  const opt = (arr, cur) => arr.map(o => `<option value="${o.key}" ${o.key === cur ? "selected" : ""}>${esc(o.label)}</option>`).join("");
  el.innerHTML = `<div class="card controls rise" style="--i:0">
    <label>Group by<select id="ex-dim">${opt(m.dims, ex.dim)}</select></label>
    <label>Measure<select id="ex-met">${opt(m.metrics, ex.metric)}</select></label>
    <label>Show<select id="ex-top">${[[0,"All"],[5,"Top 5"],[8,"Top 8"],[10,"Top 10"],[15,"Top 15"],[25,"Top 25"]].map(o => `<option value="${o[0]}" ${o[0] === ex.top ? "selected" : ""}>${o[1]}</option>`).join("")}</select></label>
    <label>Chart<div class="seg" id="ex-type">${[["bar","Bars"],["hbar","Horizontal"],["line","Line"],["doughnut","Donut"]].map(o => `<button data-t="${o[0]}" class="${o[0] === ex.type ? "on" : ""}">${o[1]}</button>`).join("")}</div></label></div>
    <div class="split"><div class="card rise" style="--i:1"><div class="chart tall"><canvas id="ex-c"></canvas></div></div><div class="card rise" style="--i:2;overflow:auto;max-height:430px" id="ex-t"></div></div>`;
  let chart = null;
  async function load() {
    const nat = NATURAL.includes(ex.dim);
    const d = await getJ("/api/explore?" + qs({ dim: ex.dim, metric: ex.metric, top: nat ? 0 : ex.top, sort: nat ? "natural" : "desc" })); if (!alive()) return;
    if (chart) { chart.destroy(); S.charts = S.charts.filter(c => c !== chart); }
    chart = makeChart($("#ex-c"), { type: ex.type, labels: d.labels, series: [{ name: d.metric_label, values: d.values }], fmt: d.fmt });
    const f = fmtBy(d.fmt === "money" ? "money2" : d.fmt);
    $("#ex-t").innerHTML = `<table><thead><tr><th>#</th><th>${esc(d.dim_label)}</th><th class="num">${esc(d.metric_label)}</th>${d.share ? "<th>Share</th>" : ""}</tr></thead><tbody>` +
      d.labels.map((l, i) => `<tr><td class="muted">${i + 1}</td><td>${esc(l)}</td><td class="num">${f(d.values[i])}</td>${d.share ? `<td><div class="shbar"><i data-w="${d.share[i]}" style="width:0"></i><small>${d.share[i]}%</small></div></td>` : ""}</tr>`).join("") + "</tbody></table>";
    $$(".shbar i", el).forEach((i, k) => setTimeout(() => i.style.width = Math.min(100, i.dataset.w * 1.6) + "%", 120 + k * 35));
  }
  $("#ex-dim").onchange = e => { ex.dim = e.target.value; load(); };
  $("#ex-met").onchange = e => { ex.metric = e.target.value; load(); };
  $("#ex-top").onchange = e => { ex.top = +e.target.value; load(); };
  $$("#ex-type button").forEach(b => b.onclick = () => { ex.type = b.dataset.t; $$("#ex-type button").forEach(x => x.classList.toggle("on", x === b)); load(); });
  await load();
}

/* ----- Compare ----- */
async function vCompare(el, alive) {
  const cmp = S.meta.compare, dims = Object.keys(cmp).filter(k => cmp[k].length > 1), c = S.compare;
  if (!dims.length) { el.innerHTML = `<div class="card">There is nothing to compare for this account.</div>`; return; }
  if (!dims.includes(c.dim)) c.dim = dims.includes("year") ? "year" : dims[0];
  const vals = () => cmp[c.dim];
  if (!vals().includes(c.a)) c.a = vals().includes("2022") ? "2022" : vals()[0];
  if (!vals().includes(c.b) || c.b === c.a) c.b = vals().includes("2023") && c.a !== "2023" ? "2023" : vals().find(v => v !== c.a);
  const labels = { region:"Region", country:"Country", category:"Category", sub_category:"Sub-category", year:"Year", customer_segment:"Customer segment", shipping_method:"Shipping method", payment_method:"Payment method", customer_gender:"Customer gender" };
  const sel = (id, cur) => `<select id="${id}">${vals().map(v => `<option ${v === cur ? "selected" : ""}>${esc(v)}</option>`).join("")}</select>`;
  el.innerHTML = `<div class="card controls rise" style="--i:0"><label>Compare by<select id="cp-dim">${dims.map(k => `<option value="${k}" ${k === c.dim ? "selected" : ""}>${labels[k] || k}</option>`).join("")}</select></label>
    <label><span style="color:var(--accent)">● Side A</span>${sel("cp-a", c.a)}</label><button class="btn" id="cp-swap" title="Swap sides">${svg("swap")}</button>
    <label><span style="color:var(--accent2)">● Side B</span>${sel("cp-b", c.b)}</label></div><div id="cp-out"></div>`;
  async function load() {
    const d = await getJ("/api/compare?" + qs({ dim: c.dim, a: c.a, b: c.b })); if (!alive()) return;
    const defs = [["orders","Orders","count"],["revenue","Revenue","money2"],["avg_order_value","Avg order value","money2"],["profit","Profit","money2"],["margin_pct","Margin","pct"],["return_rate_pct","Return rate","pct",1],["cancel_rate_pct","Cancel rate","pct",1]].filter(x => d.a.kpis[x[0]] !== undefined);
    const rows = defs.map(([k, l, fk, lower]) => { const a = d.a.kpis[k], b = d.b.kpis[k], mx = Math.max(a, b) || 1, f = fmtBy(fk);
      const isPct = fk === "pct", diff = isPct ? a - b : (b ? (a - b) / Math.abs(b) * 100 : 0), better = lower ? a < b : a > b;
      const cls = Math.abs(diff) < .05 ? "flat" : better ? "up" : "down", txt = (diff > 0 ? "+" : "") + diff.toFixed(1) + (isPct ? " pts" : "%");
      return `<div class="vs-row"><div class="top"><b>${l}</b><span class="delta ${cls}">${txt}</span></div>
        <div class="bar a"><i data-w="${a / mx * 100}"></i></div><div class="bar b"><i data-w="${b / mx * 100}"></i></div>
        <div class="vals"><span>${esc(d.a.name)}: <b style="color:var(--text)">${f(a)}</b></span><span>${esc(d.b.name)}: <b style="color:var(--text)">${f(b)}</b></span></div></div>`; }).join("");
    const xl = c.dim === "year" ? d.x.map(m => MON[m - 1]) : d.x;
    $("#cp-out").innerHTML = `<div class="split"><div class="card rise" style="--i:1"><div class="legend" style="margin-bottom:16px"><span><i style="background:var(--accent)"></i>${esc(d.a.name)}</span><span><i style="background:var(--accent2)"></i>${esc(d.b.name)}</span></div><div class="vs">${rows}</div></div>
      <div style="display:grid;gap:16px"><div class="card rise" style="--i:2"><h3 style="font-size:15px;margin-bottom:12px">${d.metric} over time</h3><div class="chart"><canvas id="cp-c1"></canvas></div></div>
      ${d.mix.labels.length ? `<div class="card rise" style="--i:3"><h3 style="font-size:15px;margin-bottom:12px">Mix by ${esc(d.mix.dim.toLowerCase())} <span class="note">(share of each side)</span></h3><div class="chart"><canvas id="cp-c2"></canvas></div></div>` : ""}</div></div>`;
    animateBars($("#cp-out"));
    makeChart($("#cp-c1"), { type: "line", labels: xl, series: [{ name: d.a.name, values: d.sa }, { name: d.b.name, values: d.sb }], fmt: d.fmt });
    if (d.mix.labels.length) makeChart($("#cp-c2"), { type: "bar", labels: d.mix.labels, series: [{ name: d.a.name, values: d.mix.a }, { name: d.b.name, values: d.mix.b }], fmt: "pct" });
  }
  const refill = () => { $("#cp-a").innerHTML = vals().map(v => `<option ${v === c.a ? "selected" : ""}>${esc(v)}</option>`).join(""); $("#cp-b").innerHTML = vals().map(v => `<option ${v === c.b ? "selected" : ""}>${esc(v)}</option>`).join(""); };
  $("#cp-dim").onchange = e => { c.dim = e.target.value; c.a = vals()[0]; c.b = vals()[1]; refill(); destroyCharts(); load(); };
  $("#cp-a").onchange = e => { c.a = e.target.value; if (c.a === c.b) { c.b = vals().find(v => v !== c.a); $("#cp-b").value = c.b; } destroyCharts(); load(); };
  $("#cp-b").onchange = e => { c.b = e.target.value; if (c.a === c.b) { c.a = vals().find(v => v !== c.b); $("#cp-a").value = c.a; } destroyCharts(); load(); };
  $("#cp-swap").onclick = () => { [c.a, c.b] = [c.b, c.a]; $("#cp-a").value = c.a; $("#cp-b").value = c.b; destroyCharts(); load(); };
  await load();
}

/* ----- Insights ----- */
async function vInsights(el, alive) {
  const d = await getJ("/api/insights?" + qs({}, "nostatus")); if (!alive()) return;
  el.innerHTML = `<div class="grid insights">` + d.insights.map((x, i) => `<article class="card ins lift rise" data-tone="${x.tone}" style="--i:${i}">
    <div class="head"><span class="ico">${svg(x.id)}</span><div><h3>${esc(x.title)}</h3><div class="stat">${esc(x.stat.label)}: <b>${esc(x.stat.value)}</b></div></div></div>
    <p>${esc(x.text)}</p>${miniBars(x.bars, x.fmt)}</article>`).join("") + `</div>
    <article class="card notes rise" style="--i:${d.insights.length}"><h3 style="font-size:15px">Data notes and definitions</h3><ul>${d.notes.map(n => `<li>${esc(n)}</li>`).join("")}</ul></article>`;
  animateBars(el);
}

/* ----- Data table ----- */
const MONEY = new Set(["unit_price","revenue","cost","profit","shipping_cost","gross_sales","discount_amount","profit_after_shipping"]);
function cell(c, v) { if (v === null || v === undefined) return ""; if (c === "order_status") return `<span class="badge b-${esc(v)}">${esc(v)}</span>`; if (c === "discount") return Math.round(v * 100) + "%";
  if (c === "profit_margin_pct") return (+v).toFixed(1) + "%"; if (MONEY.has(c)) return nf2.format(v); if (c === "is_loss") return v ? '<span class="badge b-Cancelled">Loss</span>' : "–"; return esc(v); }
async function vData(el, alive) {
  const T = S.table;
  el.innerHTML = `<div class="card rise"><div class="tools"><input type="search" id="tq" placeholder="Search order ID, product or country…" value="${esc(T.search)}"><span class="grow"></span><span class="pill" id="tcount"></span><button class="btn" id="tex">${svg("download")}Export CSV</button></div><div class="tbl-wrap" id="twrap"></div><div class="pager" id="tpg"></div></div>`;
  async function load() {
    const d = await getJ("/api/table?" + qs({ page: T.page, size: T.size, search: T.search, sort: T.sort, dir: T.dir }, "table")); if (!alive()) return;
    const pages = Math.max(1, Math.ceil(d.total / T.size)), num = d.rows[0] ? d.cols.map((_, i) => typeof d.rows[0][i] === "number") : [];
    $("#tcount").textContent = nf.format(d.total) + " orders";
    $("#twrap").innerHTML = `<table><thead><tr>${d.cols.map((c, i) => `<th data-c="${c}" class="${num[i] ? "num" : ""}">${pretty(c)}${T.sort === c ? `<span class="ar">${T.dir === "asc" ? "▲" : "▼"}</span>` : ""}</th>`).join("")}</tr></thead>
      <tbody>${d.rows.map((r, ri) => `<tr style="--r:${ri}">${r.map((v, i) => `<td class="${num[i] ? "num" : ""}">${cell(d.cols[i], v)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    $("#tpg").innerHTML = `<span>Page ${T.page + 1} of ${nf.format(pages)}</span><div class="btns"><button class="btn" id="pp" ${T.page <= 0 ? "disabled" : ""}>Previous</button><button class="btn" id="pn" ${T.page + 1 >= pages ? "disabled" : ""}>Next</button></div>`;
    $("#pp").onclick = () => { T.page--; load(); }; $("#pn").onclick = () => { T.page++; load(); };
    $$("#twrap th").forEach(th => th.onclick = () => { const c = th.dataset.c; T.dir = T.sort === c && T.dir === "desc" ? "asc" : "desc"; T.sort = c; T.page = 0; load(); });
  }
  let t; $("#tq").oninput = e => { clearTimeout(t); t = setTimeout(() => { T.search = e.target.value; T.page = 0; load(); }, 260); };
  $("#tex").onclick = async () => { const b = await (await api("/api/export?" + qs({ search: T.search }, "table"))).blob(); const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = "orders_export.csv"; a.click(); toast("Export ready: only the columns your role can see", "good"); };
  await load();
}

/* ----- AI chat ----- */
function chatTable(t) { const f = v => typeof v === "number" ? nf.format(Math.round(v * 100) / 100) : esc(v);
  return `<div class="res"><table><thead><tr>${t.cols.map((c, i) => `<th class="${t.rows[0] && typeof t.rows[0][i] === "number" ? "rt" : ""}">${esc(pretty(c))}</th>`).join("")}</tr></thead><tbody>${t.rows.map(r => `<tr>${r.map(v => `<td class="${typeof v === "number" ? "num" : ""}">${f(v)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`; }
function chatBars(t) { if (t.cols.length !== 2 || t.rows.length < 2 || t.rows.length > 15 || !t.rows.every(r => typeof r[1] === "number")) return "";
  const mx = Math.max(...t.rows.map(r => Math.abs(r[1]))) || 1;
  return `<div class="cbars">` + t.rows.map(r => `<div class="cb"><span class="l">${esc(r[0])}</span><div class="t"><i data-w="${Math.abs(r[1]) / mx * 100}"></i></div><span class="v">${nf.format(Math.round(r[1] * 100) / 100)}</span></div>`).join("") + `</div>`; }
function msgNode(m, animate) {
  const w = document.createElement("div"); w.className = "msg " + (m.role === "user" ? "user" : "ai");
  const ini = m.role === "user" ? (S.me.username[0] || "U").toUpperCase() : "AI";
  const extras = m.role === "ai" ? (m.table ? chatTable(m.table) + chatBars(m.table) : "") : "";
  w.innerHTML = `<div class="av">${ini}</div><div class="bubble"><div class="tx"></div><div class="ex"></div></div>`;
  const tx = $(".tx", w), ex = $(".ex", w), text = m.text || "";
  const showEx = () => { ex.innerHTML = extras; animateBars(ex); };
  if (animate && m.role === "ai" && text) { let i = 0; const step = Math.max(1, Math.ceil(text.length / 70)); const iv = setInterval(() => { i += step; tx.textContent = text.slice(0, i); box().scrollTop = box().scrollHeight; if (i >= text.length) { clearInterval(iv); showEx(); box().scrollTop = box().scrollHeight; } }, 16); }
  else { tx.textContent = text; showEx(); }
  return w;
}
const box = () => $("#msgs");
async function send(q, preset, label) {
  if (S.busy) return; S.busy = true; $("#cin").disabled = true;
  const qs = $(".qs"); if (qs) qs.remove();
  const um = { role: "user", text: label || q }; S.chat.push(um); box().appendChild(msgNode(um, false));
  const ty = document.createElement("div"); ty.className = "msg ai"; ty.innerHTML = `<div class="av">AI</div><div class="bubble"><div class="typing"><i></i><i></i><i></i></div></div>`; box().appendChild(ty); box().scrollTop = box().scrollHeight;
  try {
    const r = await (await api("/api/chat", { method: "POST", body: JSON.stringify({ question: q || "", preset: preset || "" }) })).json();
    ty.remove(); const m = { role: "ai", text: r.answer, table: r.table, sql: r.sql, source: r.source, ms: r.ms }; S.chat.push(m); box().appendChild(msgNode(m, true));
    if (r.offline) pollHealth();
  } catch (e) { ty.remove(); const m = { role: "ai", text: "Something went wrong while answering. Please try again." }; S.chat.push(m); box().appendChild(msgNode(m, false)); }
  S.busy = false; const i = $("#cin"); if (i) { i.disabled = false; i.focus(); }
}
async function vChat(el, alive) {
  const pr = await getJ("/api/chat/presets"); if (!alive()) return;
  if (!S.chat.length) S.chat.push({ role: "ai", text: `Hi, ${S.me.username} (${S.me.label}), How can I help you?` });
  el.innerHTML = `<div class="chat-layout"><div class="card chatbox rise"><div class="msgs" id="msgs"></div>${S.chat.length > 1 ? "" : `<div class="qs">${pr.map(p => `<button data-id="${p.id}">${esc(p.label)}</button>`).join("")}</div>`}<form class="composer" id="cf"><input type="text" id="cin" placeholder="Ask about revenue, returns, discounts, shipping…" autocomplete="off"><button class="btn primary" type="submit">${svg("send")}Send</button></form></div>
    <div class="side-col">
    <div class="card rise" style="--i:2"><h4>AI engine</h4><div id="chat-health" class="muted" style="font-size:13px;line-height:1.55"></div></div></div></div>`;
  S.chat.forEach(m => box().appendChild(msgNode(m, false))); box().scrollTop = box().scrollHeight;
  $("#cf").onsubmit = e => { e.preventDefault(); const q = $("#cin").value.trim(); if (!q) return; $("#cin").value = ""; send(q, "", ""); };
  $$(".qs button", el).forEach(b => b.onclick = () => send("", b.dataset.id, b.textContent));
  paintHealth(); $("#cin").focus();
}

/* ----- Access ----- */
async function vAccess(el, alive) {
  const d = await getJ("/api/access"); if (!alive()) return;
  const pct = d.rows_visible / d.rows_total * 100, scope = d.scope_col ? `${pretty(d.scope_col)} = ${d.scope}` : "No row restriction";
  let h = `<div class="grid access-grid"><article class="card rise" style="grid-column:span 12"><div class="muted" style="font-size:12px;font-weight:800;letter-spacing:.07em;text-transform:uppercase">Signed in as</div>
    <div class="big" style="margin-top:8px">${esc(S.me.username)}</div><div style="margin:6px 0 14px"><span class="badge role-badge">${esc(d.label)}</span></div><p class="muted" style="line-height:1.6;font-size:14px">${esc(d.desc)}</p></article>
    <article class="card rise" style="grid-column:span 12;--i:3;overflow:auto"><h3 style="font-size:15px;margin-bottom:12px">Role matrix</h3><table><thead><tr><th>Role</th><th>Row scope</th><th>What it is for</th></tr></thead><tbody>${d.matrix.map(r => `<tr><td><b>${esc(r.label)}</b></td><td>${r.row_scope ? "Own " + r.row_scope : "All rows"}</td><td class="muted" style="white-space:normal">${esc(r.desc)}</td></tr>`).join("")}</tbody></table></article>`;
  if (d.users) h += `<article class="card rise" style="grid-column:span 5;--i:4"><h3 style="font-size:15px;margin-bottom:12px">Users</h3><table><thead><tr><th>User</th><th>Role</th><th>Scope</th></tr></thead><tbody>${d.users.map(u => `<tr><td>${esc(u.username)}</td><td>${esc(u.role)}</td><td>${esc(u.scope || "all")}</td></tr>`).join("")}</tbody></table></article>
    <article class="card rise" style="grid-column:span 7;--i:5;overflow:auto;max-height:420px"><h3 style="font-size:15px;margin-bottom:12px">Audit log <span class="note">(live, newest first)</span></h3><table><thead><tr><th>Time (UTC)</th><th>User</th><th>Action</th><th>Detail</th></tr></thead><tbody id="audit-body"></tbody></table></article>`;
  el.innerHTML = h + `</div>`;
  const fill = list => $("#audit-body") && ($("#audit-body").innerHTML = list.map(a => `<tr><td class="muted">${esc(a.ts)}</td><td>${esc(a.username)}</td><td><span class="badge role-badge">${esc(a.action)}</span></td><td class="muted" style="white-space:normal">${esc(a.detail)}</td></tr>`).join(""));
  if (d.audit) { fill(d.audit); S.timer = setInterval(async () => { try { const x = await getJ("/api/access"); fill(x.audit); } catch (e) {} }, 5000); }
  $$(".num[data-to]", el).forEach(countUp); animateBars(el);
}

/* ============================================================
   SHELL
   ============================================================ */
async function go(view, soft) {
  clearInterval(S.timer); S.view = view; const my = ++S.nav, alive = () => my === S.nav, V = VIEWS[view];
  $$("#nav button").forEach(b => b.classList.toggle("on", b.dataset.view === view)); placeIndicator();
  $("#view-title").textContent = V.title; $("#view-sub").textContent = V.sub + (S.me.scope_col ? `  ·  ${pretty(S.me.scope_col)}: ${S.me.scope}` : "");
  $("#filters").classList.toggle("hide", !V.filters); history.replaceState(null, "", "#" + view);
  const el = $("#view"); el.classList.remove("in"); destroyCharts();
  if (V.filters && view !== "explore" && view !== "compare") el.innerHTML = skeleton();
  try { await V.render(el, alive); } catch (e) { if (alive() && e.message !== "401") el.innerHTML = `<div class="card">Could not load this view: ${esc(e.message)}</div>`; }
  if (alive()) requestAnimationFrame(() => el.classList.add("in"));
}
function placeIndicator() { const b = $("#nav button.on"), i = $(".nav-ind"); if (b && i) i.style.transform = `translateY(${b.offsetTop}px)`; }
function buildNav() { const items = [["overview","Overview"],["explore","Explore"],["compare","Compare"],["insights","Insights"],["data","Orders"],["chat","Ask AI"]];
  if (S.me.role === "admin") items.push(["access","Access"]);
  $("#nav").insertAdjacentHTML("beforeend", items.map((x, i) => `<button data-view="${x[0]}" class="rise" style="--i:${i}">${svg(x[0])}<span>${x[1]}</span></button>`).join(""));
  $$("#nav button").forEach(b => b.onclick = () => go(b.dataset.view)); }
function buildFilters() {
  const m = S.meta, mk = (id, label, opts) => `<select id="f-${id}" aria-label="${label}"><option value="">${label}</option>${opts.map(o => `<option>${esc(o)}</option>`).join("")}</select>`;
  $("#filters").innerHTML = `<span class="lbl">Filters</span>${mk("year","All years",m.years)}${mk("category","All categories",m.categories)}${m.regions.length > 1 ? mk("region","All regions",m.regions) : ""}${mk("segment","All segments",m.segments)}<span class="grow"></span>
    <div class="seg" id="f-status" title="Which order statuses count"><button data-s="${NET}" class="on">Net</button><button data-s="${ALLST}">All orders</button><button data-s="Delivered">Delivered</button></div><button class="btn" id="f-reset">Reset</button>`;
  let t; const refresh = () => { clearTimeout(t); t = setTimeout(() => { S.table.page = 0; go(S.view); }, 160); };
  $$("#filters select").forEach(s => s.onchange = () => { S.f[s.id.slice(2)] = s.value; refresh(); });
  $$("#f-status button").forEach(b => b.onclick = () => { S.f.status = b.dataset.s; $$("#f-status button").forEach(x => x.classList.toggle("on", x === b)); refresh(); });
  $("#f-reset").onclick = () => { S.f = { year:"", category:"", region:"", segment:"", status: NET }; $$("#filters select").forEach(s => s.value = ""); $$("#f-status button").forEach((x, i) => x.classList.toggle("on", i === 0)); refresh(); };
}
function buildUser() { const me = S.me; $("#user-chip").innerHTML = `<div class="avatar">${esc(me.username.slice(0, 2).toUpperCase())}</div><div><b>${esc(me.username)}</b><span class="badge role-badge">${esc(me.label)}</span></div><button class="icon-btn" id="logout" title="Sign out">${svg("logout")}</button>`;
  $("#logout").onclick = () => { sessionStorage.removeItem("tok"); location.reload(); }; }
function paintHealth() { const h = S.health; if (!h) return; const dot = $("#llm-pill .dot"), tx = $("#llm-txt");
  dot.className = "dot " + (h.online && h.ready ? "on" : "off"); tx.textContent = h.online ? (h.ready ? `AI online · ${h.model}` : `Model "${h.model}" not pulled`) : "AI offline · quick questions still work";
  const c = $("#chat-health"); if (c) c.innerHTML = h.online ? (h.ready ? `<b style="color:var(--good)">Online.</b> ${esc(h.backend)} model <b>${esc(h.model)}</b> is ready. Free-text questions use text-to-SQL, with a retrieval fallback.` : `Ollama is running but model <b>${esc(h.model)}</b> is not downloaded. Run <code>ollama pull ${esc(h.model)}</code>.`) : `<b style="color:var(--warn)">Offline.</b> Start the Ollama app to enable free-text questions. The quick questions use fixed SQL and keep working.`; }
async function pollHealth() { try { S.health = await (await fetch("/api/health")).json(); } catch (e) { S.health = { online: false, model: "?", backend: "?", ready: false }; } paintHealth(); }
function setTheme(t) { document.documentElement.dataset.theme = t; localStorage.setItem("theme", t); $("#theme-btn").innerHTML = svg(t === "dark" ? "sun" : "moon"); }
async function boot() {
  S.me = await getJ("/api/me"); S.meta = await getJ("/api/meta");
  const L = $("#login-screen"); L.classList.add("out"); setTimeout(() => L.hidden = true, 600);
  $("#app").hidden = false; buildNav(); buildFilters(); buildUser(); pollHealth(); setInterval(pollHealth, 15000);
  const start = location.hash.slice(1); go(VIEWS[start] ? start : "overview");
  window.addEventListener("resize", placeIndicator);
}
function wireLogin() {
  const bars = $("#hero-bars"); for (let i = 0; i < 16; i++) bars.insertAdjacentHTML("beforeend", `<i style="--h:${22 + Math.round(Math.abs(Math.sin(i * .7 + 1)) * 72)}%;--k:${i}"></i>`);
  $$(".demo button").forEach(b => b.onclick = () => { $("#u").value = b.dataset.u; $("#p").value = b.dataset.p; $("#login-form").requestSubmit(); });
  $("#login-screen").addEventListener("mousemove", e => { const x = e.clientX / innerWidth - .5, y = e.clientY / innerHeight - .5; $("#tilt").style.transform = `rotateY(${x * 9}deg) rotateX(${-y * 9}deg)`; });
  $("#login-form").onsubmit = async e => { e.preventDefault(); const err = $("#login-err"), tx = $("#login-txt"); err.textContent = ""; tx.textContent = "Signing in…";
    try { const r = await fetch("/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: $("#u").value.trim(), password: $("#p").value }) });
      if (!r.ok) { err.textContent = "Invalid username or password"; $("#login-form").classList.remove("shake"); void $("#login-form").offsetWidth; $("#login-form").classList.add("shake"); tx.textContent = "Sign in"; return; }
      const d = await r.json(); S.token = d.token; sessionStorage.setItem("tok", d.token); tx.textContent = "Welcome"; await boot();
    } catch (x) { err.textContent = "Cannot reach the server"; tx.textContent = "Sign in"; } };
}
document.addEventListener("mousemove", e => { const c = e.target.closest && e.target.closest(".card"); if (c) { const r = c.getBoundingClientRect(); c.style.setProperty("--mx", (e.clientX - r.left) + "px"); c.style.setProperty("--my", (e.clientY - r.top) + "px"); } });
(function init() {
  const saved = localStorage.getItem("theme") || "dark"; document.documentElement.dataset.theme = saved; setTheme(saved);
  $("#theme-btn").onclick = () => { setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"); if (S.me) go(S.view); };
  wireLogin();
  if (S.token) { $("#login-screen").hidden = true; boot().catch(() => { sessionStorage.removeItem("tok"); S.token = ""; $("#login-screen").hidden = false; $("#login-screen").classList.remove("out"); }); }
})();
