// Revive judge view: reads /events (history), /stream (live lines) and /body (poll).
// Every number on the page comes from the event log or /body. Prompt text is never shown.
"use strict";

const params = new URLSearchParams(location.search);
const WINDOW_MS = (Number(params.get("window")) || 10) * 60_000;
const POLL_MS = 2000;
const GROUP_MS = 10_000;   // actions this close together are one intervention
const LINK_MS = 30_000;    // an action this soon after a grade/loop answers it
const FRESH_MS = 2500;

const CH = { fix: "SILENT FIX", tap: "WRIST TAP", voice: "VOICE", hold: "HOLD" };
const UNSCORED = new Set(["confirmation", "question", "exploration"]);
const COLORS = {};

let events = [];           // sorted by time
const seen = new Set();
const freshAt = new Map(); // event key -> ms it arrived live
let polls = [];            // /body readings {t, hr, rmssd, strain, source}
let bodyState = null;
let bodyOk = false;
let streamOk = false;

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);
const tOf = (e) => { const t = Date.parse(e?.ts); return Number.isFinite(t) ? t : Date.now(); };
const fmtTime = (t) => new Date(t).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" });
const fmtHM = (t) => new Date(t).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
const scoreClass = (s) => (s == null ? "" : s >= 6 ? "good" : s >= 4 ? "mid" : "bad");
const sameDay = (t) => new Date(t).toDateString() === new Date().toDateString();

// ---------- event intake ----------
function addEvent(e, live) {
  if (!e || typeof e !== "object" || Array.isArray(e)) return false;
  const key = JSON.stringify(e);
  if (seen.has(key)) return false;
  seen.add(key);
  e._t = tOf(e);
  e._key = key;
  if (live) freshAt.set(key, Date.now());
  if (events.length && events[events.length - 1]._t > e._t) {
    events.push(e);
    events.sort((a, b) => a._t - b._t);
  } else {
    events.push(e);
  }
  return true;
}

async function loadHistory() {
  try {
    const r = await fetch("/events?last=3000", { cache: "no-store" });
    const list = await r.json();
    let changed = false;
    for (const e of Array.isArray(list) ? list : []) changed = addEvent(e, false) || changed;
    if (changed) renderAll();
  } catch (err) {
    console.warn("history load failed", err);
  }
}

function connectStream() {
  const es = new EventSource("/stream");
  es.onopen = () => { streamOk = true; loadHistory(); renderHeader(); };
  es.onerror = () => { streamOk = false; renderHeader(); };   // EventSource retries by itself
  es.onmessage = (m) => {
    let e;
    try { e = JSON.parse(m.data); } catch { return; }
    if (addEvent(e, true)) renderAll();
  };
}

async function pollBody() {
  try {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), 1800);
    const r = await fetch("/body", { cache: "no-store", signal: ctl.signal });
    clearTimeout(timer);
    if (!r.ok) throw new Error(r.status);
    bodyState = await r.json();
    bodyOk = true;
    const hr = num(bodyState.hr), rm = num(bodyState.rmssd);
    if (hr != null || rm != null) {
      const now = Date.now();
      polls.push({ t: now, hr, rmssd: rm, strain: bodyState.strain, source: bodyState.source, poll: true });
      polls = polls.filter((p) => p.t > now - WINDOW_MS - 60_000);
    }
  } catch {
    bodyOk = false;
  }
  renderAll();
}

// ---------- derived state ----------
function bodySamples() {
  const ev = events
    .filter((e) => e.kind === "body" && (num(e.hr) != null || num(e.rmssd) != null || e.rmssd === null))
    .map((e) => ({ t: e._t, hr: num(e.hr), rmssd: num(e.rmssd), strain: e.strain, source: e.source, demo: e.demo === true, e }));
  // /body polls only fill gaps where no body event is being written
  const fill = polls.filter((p) => !ev.some((s) => Math.abs(s.t - p.t) < 10_000));
  return ev.concat(fill).sort((a, b) => a.t - b.t);
}

function baselines() {
  let hrB = null, rmB = null;
  for (let i = events.length - 1; i >= 0 && (hrB == null || rmB == null); i--) {
    const e = events[i];
    if (e.kind !== "body") continue;
    if (hrB == null) hrB = num(e.hr_base);
    if (rmB == null) rmB = num(e.rmssd_base);
  }
  return {
    hr: hrB ?? num(bodyState?.hr_base),
    rmssd: rmB ?? num(bodyState?.rmssd_base),
  };
}

function strainOf(s, base) {
  if (!s) return null;
  if (["calm", "elevated", "strained"].includes(s.strain)) return s.strain;
  if (s.hr == null && s.rmssd == null) return null;
  const dHr = s.hr != null && base.hr != null ? s.hr - base.hr : 0;
  const rel = s.rmssd != null && base.rmssd ? s.rmssd / base.rmssd : 1;
  if (dHr >= 20 || rel < 0.6) return "strained";
  if (dHr >= 10 || rel < 0.8) return "elevated";
  return "calm";
}

function sampleAt(samples, t) {
  let best = null;
  for (const s of samples) { if (s.t <= t + 1000) best = s; else break; }
  return best;
}

function actionGroups(list) {
  const groups = [];
  for (const e of list) {
    if (e.kind !== "action") continue;
    const g = groups[groups.length - 1];
    if (g && e._t - g.last <= GROUP_MS) { g.items.push(e); g.last = e._t; }
    else groups.push({ t: e._t, last: e._t, items: [e] });
  }
  return groups;
}

// actions log `channel: "tap"` or `channels: ["fix", "tap"]`
const chans = (a) => (Array.isArray(a.channels) ? a.channels : a.channel ? [a.channel] : []).map(String);
const chanLabel = (c) => CH[c] || c.toUpperCase();
const actionLabel = (a) => chans(a).map(chanLabel).join(" + ") || "ACTION";
const groupLabel = (g) => [...new Set(g.items.flatMap((a) => chans(a).map(chanLabel)))].join(" + ") || "ACTION";

function intentText(intent) {
  if (!intent) return "";
  if (typeof intent === "string") return intent;
  if (typeof intent === "object") return intent.immediate || Object.values(intent).filter((v) => typeof v === "string")[0] || "";
  return String(intent);
}

// ---------- rendering ----------
function renderHeader() {
  $("clock").textContent = fmtHM(Date.now());
  const live = $("live");
  live.textContent = streamOk ? "live" : "reconnecting…";
  live.className = "live" + (streamOk ? "" : " off");

  const last = [...events].reverse().find((e) => e.kind !== "body" && e.who) || events[events.length - 1];
  $("who").textContent = last?.who || bodyState?.who || "—";

  const samples = bodySamples();
  const s = samples[samples.length - 1];
  const src = String((s?.source ?? bodyState?.source) || "").toLowerCase();
  const stale = !s || Date.now() - s.t > 30_000;
  const sensor = $("sensor");
  if (!bodyOk && stale) { sensor.textContent = "body offline"; sensor.className = "sensor off"; }
  else if (src === "h10") { sensor.textContent = stale ? "H10 ○ stale" : "H10 ● live"; sensor.className = "sensor " + (stale ? "off" : "live"); }
  else if (src === "replay") { sensor.textContent = "REPLAY"; sensor.className = "sensor replay"; }
  else if (src === "fake") { sensor.textContent = "fake"; sensor.className = "sensor fake"; }
  else if (src) { sensor.textContent = src; sensor.className = "sensor"; }
  else { sensor.textContent = "no sensor"; sensor.className = "sensor off"; }

  const cutoff = Date.now() - WINDOW_MS;
  const demo = src === "fake" || src === "replay" ||
    events.some((e) => e._t >= cutoff && e.demo === true);
  const badge = $("badge");
  badge.textContent = demo ? "DEMO DATA" : "REAL";
  badge.className = "badge " + (demo ? "demo" : "real");
}

function renderNow() {
  const samples = bodySamples();
  const base = baselines();
  const s = samples[samples.length - 1];

  $("hrNow").textContent = s?.hr != null ? Math.round(s.hr) : "—";
  $("rmNow").textContent = s?.rmssd != null ? Math.round(s.rmssd) : "—";
  $("hrBase").textContent = base.hr != null ? `(base ${Math.round(base.hr)})` : "";
  $("rmBase").textContent = base.rmssd != null ? `(base ${Math.round(base.rmssd)})` : "";

  const st = strainOf(s, base);
  const strainEl = $("strainTxt").parentElement;
  strainEl.className = "strain" + (st ? " st-" + st : "");
  $("strainTxt").textContent = st ? st.toUpperCase() : "—";
  if (s) {
    const parts = [];
    if (s.hr != null && base.hr != null) {
      const d = Math.round(s.hr - base.hr);
      parts.push(`${d >= 0 ? "+" : "−"}${Math.abs(d)} bpm`);
    }
    if (s.rmssd != null && base.rmssd) {
      const p = Math.round((s.rmssd / base.rmssd - 1) * 100);
      parts.push(`HRV ${p >= 0 ? "+" : "−"}${Math.abs(p)}%`);
    } else if (s.rmssd == null) {
      parts.push("HRV — (moving)");
    }
    $("strainDelta").textContent = parts.join(", ") || "—";
  } else {
    $("strainDelta").textContent = "waiting for body data";
  }

  const td = bodyState?.today;
  const tp = [];
  if (td && typeof td === "object") {
    if (num(td.sleep_h) != null) tp.push(`sleep ${td.sleep_h} h`);
    if (num(td.body_battery) != null) tp.push(`Body Battery ${td.body_battery}`);
    if (num(td.stress) != null) tp.push(`stress ${td.stress}`);
  }
  $("today").textContent = tp.length ? "Today (Garmin): " + tp.join(" · ") : "";

  // last prompt
  const g = [...events].reverse().find((e) => e.kind === "grade");
  const scoreEl = $("score");
  if (g) {
    const sc = num(g.score);
    const unscored = sc == null || UNSCORED.has(g.type);
    scoreEl.textContent = unscored ? "not scored" : `${sc}/10`;
    scoreEl.className = "score " + (unscored ? "" : scoreClass(sc));
    $("ptype").textContent = [g.type ? String(g.type).replace(/_/g, " ") : "", g.pattern ? String(g.pattern).replace(/_/g, " ") : "",
      num(g.latency_ms) != null ? `graded in ${(g.latency_ms / 1000).toFixed(1)} s` : ""].filter(Boolean).join(" · ");
    const miss = Array.isArray(g.missing) ? g.missing : [];
    $("missing").innerHTML = unscored ? "" : miss.length
      ? '<span class="dim small">missing</span> ' + miss.map((m) => `<span class="chip">${esc(m)}</span>`).join("")
      : '<span class="chip ok">all checks</span>';

    const it = intentText(g.intent);
    $("intent").textContent = it ? "Intent: " + it : "Intent: —";
    const o = events.find((e) => e.kind === "outcome" && e._t >= g._t);
    if (o) {
      const oc = String(o.outcome || "?");
      const pts = num(o.points) != null ? ` (${o.points}/3)` : "";
      $("got").innerHTML = `→ Got: <span class="${esc(oc.replace(/\s+/g, "_"))}">${esc(oc.replace(/_/g, " "))}${esc(pts)}</span>` +
        (o.why ? ` <span class="dim">· ${esc(o.why)}</span>` : "");
    } else {
      $("got").innerHTML = '<span class="dim">→ Got: waiting for the reply…</span>';
    }
  } else {
    scoreEl.textContent = "—"; scoreEl.className = "score";
    $("ptype").textContent = ""; $("missing").innerHTML = "";
    $("intent").textContent = "—"; $("got").innerHTML = "";
  }

  // last action
  const groups = actionGroups(events);
  const ag = groups[groups.length - 1];
  const act = $("action");
  if (ag) {
    act.className = "action";
    act.textContent = "→ " + groupLabel(ag);
    $("actionMsg").innerHTML = ag.items.filter((a) => a.message)
      .map((a) => `<div>“${esc(a.message)}”</div>`).join("") + `<div class="dim small">at ${esc(fmtTime(ag.t))}</div>`;
  } else {
    act.className = "action dim"; act.textContent = "none yet"; $("actionMsg").innerHTML = "";
  }
}

let lastLogHtml = "";
function renderLog() {
  const samples = bodySamples();
  const base = baselines();
  const rows = [];
  const linkable = [];  // rows an action can attach to
  const now = Date.now();
  const fresh = (e) => freshAt.has(e._key) && now - freshAt.get(e._key) < FRESH_MS;

  for (const e of events) {
    const k = e.kind;
    if (k === "body" || k === "prompt" || k === "reply") continue;
    const row = { t: e._t, seen: "", did: "", none: false, demo: e.demo === true, fresh: fresh(e) };
    if (k === "grade") {
      const sc = num(e.score);
      const st = strainOf(sampleAt(samples, e._t), base);
      if (sc == null || UNSCORED.has(e.type)) {
        row.seen = `prompt (${esc(String(e.type || "?").replace(/_/g, " "))}) · not scored`;
      } else {
        const miss = Array.isArray(e.missing) && e.missing.length ? ` · missing ${esc(e.missing.join(", "))}` : "";
        row.seen = `prompt <b class="${scoreClass(sc)}-t">${sc}/10</b>${miss}${st ? " · " + st : ""}`;
      }
      row.did = "no action"; row.none = true;
      linkable.push(row);
    } else if (k === "loop") {
      const sig = Array.isArray(e.signals) ? e.signals.join(", ") : e.signals || "";
      row.seen = `loop: ${esc(sig)}${num(e.minutes) != null ? ` · ${e.minutes} min` : ""}`;
      row.did = "no action"; row.none = true;
      linkable.push(row);
    } else if (k === "action") {
      const text = `${esc(actionLabel(e))}${e.message ? ` “${esc(e.message)}”` : ""}`;
      const target = [...linkable].reverse().find((r) => e._t - r.t <= LINK_MS && e._t >= r.t - 1000);
      if (target) {
        target.did = target.none ? text : target.did + " + " + text;
        target.none = false;
        target.fresh = target.fresh || row.fresh;
        continue;
      }
      row.seen = "coach"; row.did = text;
      linkable.push(row);
    } else if (k === "outcome") {
      const pts = num(e.points) != null ? ` (${e.points}/3)` : "";
      row.seen = `outcome: <b>${esc(String(e.outcome || "?").replace(/_/g, " "))}${esc(pts)}</b>`;
      row.did = esc(e.why || ""); row.none = true;
    } else if (k === "mark") {
      row.seen = `mark: ${esc(e.note || "")}`; row.none = true;
    } else {
      // unknown kind: short scalar fields only, so no free text lands on the judge screen
      const extra = Object.entries(e)
        .filter(([key, v]) => !["ts", "who", "kind", "demo", "_t", "_key", "session"].includes(key) &&
          (typeof v === "number" || typeof v === "boolean" || (typeof v === "string" && v.length <= 24)))
        .map(([key, v]) => `${key}=${v}`).join(" ");
      row.seen = `${esc(k || "event")} <span class="dim">${esc(extra.slice(0, 120))}</span>`; row.none = true;
    }
    rows.push(row);
  }

  const html = rows.slice(-14).reverse().map((r) =>
    `<tr class="${r.fresh ? "fresh" : ""}"><td class="t">${esc(fmtTime(r.t))}</td>` +
    `<td>${r.seen}${r.demo ? '<span class="tag">DEMO</span>' : ""}</td>` +
    `<td class="arrow">${r.did ? "→" : ""}</td><td class="did${r.none ? " none" : ""}">${r.did}</td></tr>`
  ).join("") || '<tr><td class="dim">No decisions yet. Waiting for the first prompt.</td></tr>';
  if (html !== lastLogHtml) { $("logRows").innerHTML = html; lastLogHtml = html; }
}

function renderToday() {
  const today = events.filter((e) => sameDay(e._t));
  const prompts = today.filter((e) => e.kind === "prompt").length ||
    today.filter((e) => e.kind === "grade").length;
  const groups = actionGroups(today);
  $("tPrompts").textContent = prompts;
  $("tNudges").textContent = groups.length;

  // "accepted": an explicit accepted flag if the coach logs one; otherwise nudges whose next outcome was achieved
  const flagged = today.filter((e) => e.kind === "action" && typeof e.accepted === "boolean");
  const acceptedLabel = $("tAccepted").nextSibling;
  if (flagged.length) {
    $("tAccepted").textContent = flagged.filter((e) => e.accepted).length;
    acceptedLabel.textContent = " accepted";
  } else {
    let n = 0;
    groups.forEach((g, i) => {
      const end = groups[i + 1]?.t ?? Infinity;
      const o = today.find((e) => e.kind === "outcome" && e._t > g.t && e._t < end);
      if (o && o.outcome === "achieved") n++;
    });
    $("tAccepted").textContent = n;
    acceptedLabel.textContent = " solved after a nudge";
  }

  const saved = today.map((e) => (e.kind === "outcome" ? num(e.turns_saved) : null)).filter((v) => v != null);
  $("tSaved").textContent = saved.length ? "≈ " + saved.reduce((a, b) => a + b, 0) : "—";
}

// ---------- charts ----------
function cssVar(name) {
  if (!COLORS[name]) COLORS[name] = getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888";
  return COLORS[name];
}

function setupCanvas(cv) {
  const dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth, h = cv.clientHeight;
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
  }
  const ctx = cv.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  return { ctx, w, h };
}

function drawChart(cv, opts) {
  const { ctx, w, h } = setupCanvas(cv);
  if (w < 50 || h < 30) return;
  const padL = 44, padR = 12, padT = 22, padB = opts.timeAxis ? 22 : 6;
  const t1 = Date.now(), t0 = t1 - WINDOW_MS;
  const pts = opts.samples.filter((s) => s.t >= t0 - 30_000);
  const vals = pts.map((s) => s[opts.key]).filter((v) => v != null);
  let lo = Math.min(...vals, opts.base ?? Infinity);
  let hi = Math.max(...vals, opts.base ?? -Infinity);
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) { lo = opts.lo; hi = opts.hi; }
  lo = Math.max(0, Math.floor((Math.min(lo, opts.base != null ? opts.base - opts.pad : lo) - opts.pad / 2) / 5) * 5);
  hi = Math.ceil((Math.max(hi, opts.base != null ? opts.base + opts.pad : hi) + opts.pad / 2) / 5) * 5;
  if (hi - lo < 10) hi = lo + 10;
  const X = (t) => padL + ((t - t0) / WINDOW_MS) * (w - padL - padR);
  const Y = (v) => padT + (1 - (v - lo) / (hi - lo)) * (h - padT - padB);

  // grid + y labels
  ctx.font = "13px ui-sans-serif, system-ui, sans-serif";
  ctx.fillStyle = cssVar("--dim");
  ctx.strokeStyle = cssVar("--line");
  ctx.lineWidth = 1;
  ctx.textAlign = "right"; ctx.textBaseline = "middle";
  for (let i = 0; i <= 3; i++) {
    const v = lo + ((hi - lo) * i) / 3;
    const y = Y(v);
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke();
    ctx.fillText(Math.round(v), padL - 6, y);
  }
  if (opts.timeAxis) {
    ctx.textAlign = "center"; ctx.textBaseline = "top";
    const step = WINDOW_MS <= 5 * 60_000 ? 60_000 : 2 * 60_000;
    for (let t = Math.ceil(t0 / step) * step; t <= t1; t += step) ctx.fillText(fmtHM(t), X(t), h - padB + 6);
  }

  // strained stretches, faint red
  ctx.fillStyle = "rgba(255,84,104,0.08)";
  for (let i = 0; i < pts.length; i++) {
    if (pts[i].strain !== "strained") continue;
    const a = Math.max(X(pts[i].t), padL), b = Math.min(X(pts[i + 1]?.t ?? t1), w - padR);
    if (b > a) ctx.fillRect(a, padT, b - a, h - padT - padB);
  }

  // baseline
  if (opts.base != null) {
    ctx.save();
    ctx.setLineDash([8, 6]); ctx.strokeStyle = cssVar("--dim"); ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(padL, Y(opts.base)); ctx.lineTo(w - padR, Y(opts.base)); ctx.stroke();
    ctx.restore();
    ctx.fillStyle = cssVar("--dim"); ctx.textAlign = "left"; ctx.textBaseline = "bottom";
    ctx.fillText(`base ${Math.round(opts.base)}`, padL + 4, Y(opts.base) - 3);
  }

  // action markers (labels step down when two land close together)
  let labelX = -Infinity, labelRow = 0;
  for (const g of opts.actions) {
    if (g.t < t0) continue;
    const x = X(g.t);
    ctx.strokeStyle = cssVar("--act"); ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(x, padT - (opts.labels ? 4 : 0)); ctx.lineTo(x, h - padB); ctx.stroke();
    if (opts.labels) {
      ctx.fillStyle = cssVar("--act"); ctx.font = "bold 14px ui-sans-serif, system-ui, sans-serif";
      labelRow = x - labelX < 200 ? labelRow + 1 : 0;
      labelX = x;
      ctx.textAlign = x > w - 220 ? "right" : "left"; ctx.textBaseline = "top";
      ctx.fillText(groupLabel(g), x + (x > w - 220 ? -6 : 6), 2 + labelRow * 16);
      ctx.font = "13px ui-sans-serif, system-ui, sans-serif";
    }
  }

  // the line (gaps over 20 s or null = motion)
  ctx.save();
  ctx.beginPath(); ctx.rect(padL, 0, w - padL - padR, h); ctx.clip();
  ctx.strokeStyle = opts.color; ctx.lineWidth = 3; ctx.lineJoin = "round";
  ctx.beginPath();
  let prev = null;
  for (const s of pts) {
    const v = s[opts.key];
    if (v == null) { prev = null; continue; }
    if (prev && s.t - prev.t <= 20_000) ctx.lineTo(X(s.t), Y(v)); else ctx.moveTo(X(s.t), Y(v));
    prev = s;
  }
  ctx.stroke();
  ctx.restore();

  // prompt dots on the line
  if (opts.grades) {
    let scoreX = Infinity;   // newest first, so the latest score keeps its label
    for (const g of [...opts.grades].reverse()) {
      if (g._t < t0) continue;
      const sc = num(g.score);
      const unscored = sc == null || UNSCORED.has(g.type);
      const s = sampleAt(pts, g._t);
      const v = s?.[opts.key] ?? (lo + hi) / 2;
      const x = X(g._t), y = Y(v);
      ctx.fillStyle = unscored ? cssVar("--dim") : cssVar(sc >= 6 ? "--good" : sc >= 4 ? "--mid" : "--bad");
      ctx.beginPath(); ctx.arc(x, y, 9, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = cssVar("--bg"); ctx.lineWidth = 2; ctx.stroke();
      if (opts.labels && !unscored && scoreX - x > 44) {
        scoreX = x;
        ctx.font = "bold 15px ui-sans-serif, system-ui, sans-serif";
        ctx.textAlign = "center"; ctx.textBaseline = "bottom";
        ctx.fillText(`${sc}/10`, x, y - 12);
        ctx.font = "13px ui-sans-serif, system-ui, sans-serif";
      }
    }
  }
}

function drawCharts() {
  const samples = bodySamples();
  const base = baselines();
  const grades = events.filter((e) => e.kind === "grade");
  const actions = actionGroups(events);
  drawChart($("hrChart"), { samples, key: "hr", base: base.hr, color: cssVar("--hr"), pad: 10, lo: 50, hi: 110, grades, actions, labels: true });
  drawChart($("rmChart"), { samples, key: "rmssd", base: base.rmssd, color: cssVar("--hrv"), pad: 10, lo: 0, hi: 60, grades, actions, timeAxis: true });
}

function renderAll() {
  renderHeader();
  renderNow();
  renderLog();
  renderToday();
  drawCharts();
}

// ---------- start ----------
$("window").textContent = `last ${WINDOW_MS / 60_000} min`;
connectStream();
loadHistory();
pollBody();
setInterval(pollBody, POLL_MS);
setInterval(() => { renderHeader(); renderLog(); drawCharts(); }, 1000);
window.addEventListener("resize", drawCharts);
