// Insights: the optional "when you're curious" page. Reads /events (today) and learned.json (aggregates).
// No prompt text is read or shown: grade `reason` and outcome `why` / `intent` are never touched.
// Query: ?who=nbz (one person) · ?date=2026-10-24 (another day)
(() => {
  const qs = new URLSearchParams(location.search);
  const WHO = qs.get('who');
  const DATE = qs.get('date');
  const GAP_MS = 5 * 60 * 1000;      // active time: gaps under 5 min merge
  const GROUP_MS = 10 * 1000;        // actions within 10 s are one intervention (same as judge view)
  const FOCUS_CAP_MS = 60 * 1000;    // a focus reading counts until the next one, at most 60 s
  const UNSCORED = new Set(['confirmation', 'question', 'exploration']);
  const ACTIVE_KINDS = new Set(['prompt', 'reply', 'grade', 'outcome']);
  const NUDGE_TYPES = ['fix', 'tap', 'hold', 'focus', 'break'];
  const CHECKS = ['context', 'done', 'goal', 'scope', 'why'];

  const $ = (id) => document.getElementById(id);
  const t = (e) => Date.parse(e.ts);
  const pad = (n) => String(n).padStart(2, '0');
  const dayKey = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const isDemo = (e) => e.demo === true || e.source === 'fake' || e.source === 'replay';
  const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;
  const pct = (x) => `${Math.round(x * 100)}%`;
  const fmtP = (p) => (p < 0.001 ? 'p<0.001' : `p=${p < 0.01 ? p.toFixed(3) : p.toFixed(2)}`);
  const scoreClass = (s) => (s >= 6 ? 'good' : s >= 4 ? 'mid' : 'bad');
  const hourLabel = (h) => `${h % 12 || 12}${h < 12 ? 'a' : 'p'}`;
  const dur = (ms) => {
    const m = Math.round(ms / 60000);
    return m < 60 ? `${m}<span class="u"> min</span>` : `${Math.floor(m / 60)}<span class="u"> h</span> ${m % 60}<span class="u"> min</span>`;
  };
  const durTxt = (ms) => dur(ms).replace(/<[^>]+>/g, '');

  function scoreOf(g) {
    if (UNSCORED.has(g.type) || g.scored === false || g.score == null) return null;
    const s = Number(g.score);
    return Number.isFinite(s) ? s : null;
  }

  // An intervention action has a level or channel(s); act receipts ({medium, sent}) are not nudges.
  function nudgeType(chs) {
    for (const k of ['focus', 'break', 'hold', 'tap', 'fix']) if (chs.has(k)) return k;
    return 'fix';
  }
  function channelsOf(a) {
    const ch = new Set(Array.isArray(a.channels) ? a.channels : []);
    if (a.channel) ch.add(a.channel);
    if (a.tapped === true) ch.add('tap');
    return ch;
  }

  function computeToday(all) {
    const today = DATE || dayKey(new Date());
    const ev = all
      .filter((e) => e && e.ts && e.kind && Number.isFinite(t(e)))
      .filter((e) => dayKey(new Date(t(e))) === today)
      .filter((e) => !WHO || e.who === WHO)
      .sort((a, b) => t(a) - t(b));
    const of = (k) => ev.filter((e) => e.kind === k);
    const counted = ev.filter((e) => e.kind !== 'mark');

    // active time
    const act = ev.filter((e) => ACTIVE_KINDS.has(e.kind)).map(t);
    let activeMs = 0;
    for (let i = 0, start = null; i < act.length; i++) {
      if (start === null) start = act[i];
      const end = act[i];
      if (i === act.length - 1 || act[i + 1] - end >= GAP_MS) { activeMs += Math.max(end - start, 60000); start = null; }
    }

    // prompts and scores
    const prompts = of('prompt');
    const scored = of('grade').map((g) => ({ g, s: scoreOf(g) })).filter((x) => x.s !== null);
    const missed = {};
    for (const { g } of scored) for (const m of g.missing || []) missed[m] = (missed[m] || 0) + 1;
    const topMissed = Object.entries(missed).sort((a, b) => b[1] - a[1])[0];
    const byHour = {};
    for (const { g, s } of scored) (byHour[new Date(t(g)).getHours()] ||= []).push(s);

    // nudges, grouped, and whether the next outcome was achieved
    const actions = of('action').filter((a) => a.level != null || a.channel || Array.isArray(a.channels));
    const groups = [];
    for (const a of actions) {
      const last = groups[groups.length - 1];
      if (last && t(a) - last.end <= GROUP_MS) { last.end = t(a); channelsOf(a).forEach((c) => last.ch.add(c)); }
      else groups.push({ start: t(a), end: t(a), ch: channelsOf(a) });
    }
    const outcomes = of('outcome');
    const nudges = Object.fromEntries(NUDGE_TYPES.map((k) => [k, { n: 0, achieved: 0 }]));
    for (const grp of groups) {
      const k = nudgeType(grp.ch);
      nudges[k].n++;
      const next = outcomes.find((o) => t(o) >= grp.start);
      if (next && next.outcome === 'achieved') nudges[k].achieved++;
    }

    // focus: on vs off task
    const focus = of('focus');
    let onMs = 0, offMs = 0;
    focus.forEach((f, i) => {
      const nxt = focus[i + 1];
      const span = Math.min(nxt ? t(nxt) - t(f) : FOCUS_CAP_MS, FOCUS_CAP_MS);
      if (f.distracted) offMs += span; else onMs += span;
    });

    // strain minutes: distinct minutes with a strained body reading
    const body = of('body');
    const strainedMin = new Set(body.filter((b) => b.strain === 'strained').map((b) => Math.floor(t(b) / 60000))).size;
    const bodyMin = new Set(body.map((b) => Math.floor(t(b) / 60000))).size;

    return {
      today, n: counted.length, demo: counted.some(isDemo),
      activeMs, prompts: prompts.length, scored: scored.length,
      avgScore: scored.length ? mean(scored.map((x) => x.s)) : null,
      topMissed, byHour, nudges, nGroups: groups.length,
      nAchieved: Object.values(nudges).reduce((a, x) => a + x.achieved, 0),
      focusN: focus.length, onMs, offMs, strainedMin, bodyMin,
    };
  }

  function renderToday(d) {
    $('todayDate').textContent = `· ${d.today}`;
    $('who').textContent = WHO || 'everyone';
    const badge = $('badge');
    badge.hidden = d.n === 0;
    badge.textContent = d.demo ? 'DEMO DATA' : 'REAL';
    badge.className = 'badge ' + (d.demo ? 'demo' : 'real');

    $('todayEmpty').hidden = d.n > 0;
    $('todayBody').hidden = d.n === 0;

    $('sActive').innerHTML = d.activeMs ? dur(d.activeMs) : '0<span class="u"> min</span>';
    $('sPrompts').textContent = d.prompts;
    $('sScored').textContent = `${d.scored} scored · questions and confirmations aren't`;
    if (d.avgScore === null) {
      $('sScore').innerHTML = '—';
      $('sMissed').textContent = 'no scored prompt yet';
    } else {
      $('sScore').innerHTML = `<span class="${scoreClass(d.avgScore)}-t">${d.avgScore.toFixed(1)}</span><span class="u">/10</span>`;
      $('sMissed').textContent = d.topMissed ? `most missed: ${d.topMissed[0]} (${d.topMissed[1]}×)` : 'no check missed';
    }
    $('sNudges').textContent = d.nGroups;
    $('sFollowed').textContent = d.nGroups ? `${d.nAchieved} followed by an achieved outcome` : 'none needed yet';

    // score by hour: from the first to the last hour with a scored prompt
    const hours = Object.keys(d.byHour).map(Number);
    $('hourEmpty').hidden = hours.length > 0;
    const chart = $('hourChart');
    chart.hidden = hours.length === 0;
    if (hours.length) {
      const lo = Math.min(...hours), hi = Math.max(...hours);
      let bars = '', labels = '';
      for (let h = lo; h <= hi; h++) {
        const xs = d.byHour[h];
        if (xs) {
          const m = mean(xs);
          bars += `<div class="bar ${scoreClass(m)}" title="${hourLabel(h)}: ${m.toFixed(1)}/10, n=${xs.length}"><span class="v">${m.toFixed(1)}<span class="dim"> ·${xs.length}</span></span><div class="fill" style="height:${Math.max(m * 10, 3)}%"></div></div>`;
        } else bars += '<div class="bar none"><div class="fill"></div></div>';
        labels += `<span>${hourLabel(h)}</span>`;
      }
      chart.innerHTML = bars;
      let lab = chart.nextElementSibling;
      if (!lab || !lab.classList.contains('hours')) { lab = document.createElement('div'); lab.className = 'hours'; chart.after(lab); }
      lab.innerHTML = labels;
    }

    $('nudgeTypes').innerHTML = NUDGE_TYPES.map((k) => {
      const x = d.nudges[k];
      return `<div class="kv"><span>${k}</span><b>${x.n}${x.n ? ` <span class="dim">· ${x.achieved} achieved</span>` : ''}</b></div>`;
    }).join('');
    $('focus').innerHTML = d.focusN
      ? `<div class="kv"><span>on task</span><b>${durTxt(d.onMs)}</b></div><div class="kv"><span>off task</span><b>${durTxt(d.offMs)}</b></div>`
      : '<div class="dim small">Appears during a focus block (focus watcher running).</div>';
    $('strain').innerHTML = d.bodyMin
      ? `<div class="kv"><span>strained</span><b>${d.strainedMin} min <span class="dim">of ${d.bodyMin} measured</span></b></div>`
      : '<div class="dim small">Appears when the heart-rate strap is streaming.</div>';

    $('bStrain').innerHTML = d.bodyMin ? `${d.strainedMin}<span class="u"> min</span>` : '—';
    $('bStrainSub').textContent = d.bodyMin ? `strained, of ${d.bodyMin} min measured today` : 'no heart-rate data today yet';
  }

  function renderLearned(L) {
    const h = L && L.history;
    $('learnedEmpty').hidden = !!h;
    $('learnedBody').hidden = !h;
    if (h) {
      const td = h.turns_to_done, ac = h.achieved;
      $('learnedFrom').textContent = `· ${h.who}'s ${h.sessions} sessions, ${h.dates}`;
      $('lTurns').innerHTML = `${td.ratio_low_over_high}×<span class="u"> more</span>`;
      $('lTurnsSub').textContent = `weak prompts: ${td.mean_low.toFixed(2)} vs ${td.mean_high.toFixed(2)} turns · n=${td.n_low}/${td.n_high} · ${fmtP(td.permutation_p)} · δ=${td.cliffs_delta_low_vs_high}`;
      $('lAch').innerHTML = `${pct(ac.rate_low)} <span class="u">vs</span> ${pct(ac.rate_high)}`;
      $('lAchSub').textContent = `weak vs strong prompts · n=${ac.n_low}/${ac.n_high} · ${fmtP(ac.permutation_p)} · δ=${ac.cliffs_delta_low_vs_high}`;
      $('lN').textContent = h.prompts_graded;
      $('lNSub').textContent = `${h.prompts_scored} scored · average ${h.mean_score}/10`;

      const rows = CHECKS.filter((c) => h.checks[c]).map((c) => {
        const r = h.checks[c], turns = -r.turns_to_done, ach = r.achieved;
        return { c, turns, ach, zero: h.check_zero_rate[c], key: turns + ach };
      }).sort((a, b) => b.key - a.key);
      const bar = (v) => `<span class="rho ${v < 0.15 ? 'weak' : ''}" style="width:${Math.max(Math.abs(v) * 200, 4)}px"></span>${v.toFixed(2).replace(/^-0\.00$/, '0.00')}`;
      $('checks').innerHTML = rows.map((r) =>
        `<tr><td class="c">${r.c}</td><td>${bar(r.turns)}</td><td>${bar(r.ach)}</td><td class="dim">${pct(r.zero)}</td></tr>`).join('');
    }

    const b = L && L.body;
    $('bodyEmpty').hidden = !!b;
    $('bodyBody').hidden = !b;
    if (b) {
      $('bodyFrom').textContent = `· ${b.who}'s Garmin, ${b.n_days} days (${b.date_range[0]} to ${b.date_range[1]})`;
      $('bHr').innerHTML = `${Math.round(b.resting_hr)}<span class="u"> bpm</span>`;
      $('bHrSub').textContent = `typical, n=${b.n_resting_hr} days${b.last_day.resting_hr ? ` · last day ${b.last_day.resting_hr}` : ''}`;
      $('bBb').innerHTML = `${b.bb_low}–${b.bb_high}`;
      $('bBbSub').textContent = `typical daily low–high, n=${b.n_bb} days${b.last_day.body_battery != null ? ` · last day peak ${b.last_day.body_battery}` : ''}`;
      $('bStress').textContent = b.stress;
      $('bStressSub').textContent = `typical daily average, n=${b.n_stress} days${b.last_day.stress != null ? ` · last day ${b.last_day.stress}` : ''}`;
      $('bodyMissing').textContent = b.missing.length ? `Not in the exports: ${b.missing.map((m) => m.split(' (')[0]).join(', ')}.` : '';
    }
  }

  async function loadToday() {
    let events = [];
    try { events = await (await fetch('/events?last=5000')).json(); } catch { /* server down: empty state */ }
    renderToday(computeToday(Array.isArray(events) ? events : []));
  }

  async function init() {
    let L = null;
    try { L = await (await fetch('learned.json')).json(); } catch { /* not built yet: empty state */ }
    renderLearned(L);
    await loadToday();
    setInterval(loadToday, 30000);
  }
  init();
})();
