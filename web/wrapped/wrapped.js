// AI Wrapped: one-screen summary of today, computed from /events. No prompt text is read or shown.
// Query: ?who=nbz (one person) · ?date=2026-10-24 (another day) · ?real=1 (drop demo events)
(() => {
  const qs = new URLSearchParams(location.search);
  const WHO = qs.get('who');
  const DATE = qs.get('date');      // YYYY-MM-DD, local
  const REAL_ONLY = qs.get('real') === '1';
  const BODY_EVERY_S = 5;           // body events land once every 5 s (GAMEPLAN §3)
  const GROUP_S = 10;               // actions within 10 s are one intervention (same as judge view)
  const BODY_MATCH_S = 60;          // a prompt takes the strain of the latest body reading ≤ 60 s before it
  const MIN_PATTERN_N = 5;
  const MIN_HOUR_N = 2;

  const $ = (id) => document.getElementById(id);
  const t = (e) => Date.parse(e.ts);
  const pad = (n) => String(n).padStart(2, '0');
  const dayKey = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const isDemo = (e) => e.demo === true || e.source === 'fake' || e.source === 'replay';
  const plural = (n, one, many) => `${n} ${n === 1 ? one : (many || one + 's')}`;
  const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;
  const sd = (xs) => { const m = mean(xs); return Math.sqrt(xs.reduce((a, x) => a + (x - m) ** 2, 0) / (xs.length - 1)); };
  const hourLabel = (h) => `${h % 12 || 12} ${h < 12 ? 'AM' : 'PM'}`;
  const scoreClass = (s) => (s >= 7 ? 'good' : s >= 4 ? 'mid' : 'bad');

  function scoreOf(g) {
    if (g.scored === false) return null;
    const s = typeof g.score === 'number' ? g.score : Number(g.score);
    return g.score != null && Number.isFinite(s) ? s : null;
  }

  function channelsOf(a) {
    const ch = new Set(Array.isArray(a.channels) ? a.channels : []);
    if (a.channel) ch.add(a.channel);
    if (a.tapped === true) ch.add('tap');
    return ch;
  }

  function compute(all, today = DATE || dayKey(new Date())) {
    const ev = all
      .filter((e) => e && e.ts && e.kind && Number.isFinite(t(e)))
      .filter((e) => dayKey(new Date(t(e))) === today)
      .filter((e) => !WHO || e.who === WHO)
      .filter((e) => !REAL_ONLY || !isDemo(e))
      .sort((a, b) => t(a) - t(b));
    const of = (k) => ev.filter((e) => e.kind === k);
    const prompts = of('prompt'), grades = of('grade'), actions = of('action');
    const outcomes = of('outcome'), body = of('body');
    const counted = [...prompts, ...grades, ...actions, ...outcomes, ...body];

    const scored = grades.map((g) => ({ ts: t(g), s: scoreOf(g) })).filter((g) => g.s !== null);

    // interventions: actions within GROUP_S of the previous one merge; hold > tap > silent fix
    const groups = [];
    for (const a of actions) {
      const last = groups[groups.length - 1];
      if (last && t(a) - last.end <= GROUP_S * 1000) { last.end = t(a); channelsOf(a).forEach((c) => last.ch.add(c)); last.level = Math.max(last.level, a.level || 0); }
      else groups.push({ start: t(a), end: t(a), ch: channelsOf(a), level: a.level || 0 });
    }
    const kinds = { tap: 0, fix: 0, hold: 0 };
    let followed = 0;
    for (const g of groups) {
      g.kind = g.ch.has('hold') ? 'hold' : (g.ch.has('tap') || g.level >= 1) ? 'tap' : 'fix';
      kinds[g.kind]++;
      const next = outcomes.find((o) => t(o) >= g.start);
      if (next && next.outcome === 'achieved') followed++;
    }

    const achieved = outcomes.filter((o) => o.outcome === 'achieved').length;
    const partial = outcomes.filter((o) => o.outcome === 'partial').length;

    const strainedN = body.filter((b) => b.strain === 'strained').length;
    const bodyWithState = body.filter((b) => b.strain).length;

    // score by hour of day
    const byHour = new Map();
    for (const g of scored) {
      const h = new Date(g.ts).getHours();
      if (!byHour.has(h)) byHour.set(h, []);
      byHour.get(h).push(g.s);
    }
    const hours = [...byHour].filter(([, xs]) => xs.length >= MIN_HOUR_N)
      .map(([h, xs]) => ({ h, avg: mean(xs), n: xs.length }))
      .sort((a, b) => b.avg - a.avg || a.h - b.h);

    // pattern: score while strained vs calm (only if each group has ≥ MIN_PATTERN_N)
    let pattern = null;
    if (body.length) {
      const groupsByState = { strained: [], calm: [] };
      let i = 0;
      for (const g of scored) {
        while (i + 1 < body.length && t(body[i + 1]) <= g.ts) i++;
        const b = body[i];
        if (!b || t(b) > g.ts || g.ts - t(b) > BODY_MATCH_S * 1000) continue;
        if (b.strain in groupsByState) groupsByState[b.strain].push(g.s);
      }
      const { strained: S, calm: C } = groupsByState;
      if (S.length >= MIN_PATTERN_N && C.length >= MIN_PATTERN_N) {
        const ms = mean(S), mc = mean(C);
        const pooled = Math.sqrt(((S.length - 1) * sd(S) ** 2 + (C.length - 1) * sd(C) ** 2) / (S.length + C.length - 2));
        pattern = { ms, mc, nS: S.length, nC: C.length, d: pooled > 0 ? (ms - mc) / pooled : null };
      }
    }

    return {
      today, empty: counted.length === 0, demo: counted.some(isDemo),
      prompts: prompts.length, sessions: new Set(prompts.map((p) => p.session).filter(Boolean)).size,
      scoredN: scored.length, avg: scored.length ? mean(scored.map((g) => g.s)) : null,
      weak: scored.filter((g) => g.s < 4).length,
      nudges: groups.length, kinds, followed,
      outcomes: outcomes.length, achieved, partial,
      strainMin: (strainedN * BODY_EVERY_S) / 60, bodyMin: (bodyWithState * BODY_EVERY_S) / 60,
      hours, pattern,
    };
  }

  const fmtMin = (m) => (m < 10 ? m.toFixed(1) : String(Math.round(m)));
  const fmtDay = (key) => {
    const [y, m, d] = key.split('-').map(Number);
    return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  };

  function render(r) {
    $('day').textContent = fmtDay(r.today);
    $('who').textContent = WHO || '';
    $('badge').hidden = !r.demo;
    $('grid').hidden = r.empty;
    $('empty').hidden = !r.empty;
    $('pattern').hidden = r.empty || !r.pattern;
    if (r.empty) return;

    $('vPrompts').textContent = r.prompts;
    $('lPrompts').innerHTML = `${r.sessions ? `across <b>${plural(r.sessions, 'session')}</b> · ` : ''}<b>${r.scoredN}</b> scored by the grader`;

    const vs = $('vScore');
    vs.textContent = r.avg === null ? '—' : r.avg.toFixed(1);
    vs.className = r.avg === null ? '' : scoreClass(r.avg);
    $('lScore').innerHTML = r.scoredN
      ? `<b>${r.weak}</b> of ${r.scoredN} were weak (under 4)`
      : 'no prompts scored yet';

    $('vNudges').textContent = r.nudges;
    $('lNudges').innerHTML = r.nudges
      ? `${plural(r.kinds.tap, 'wrist tap')} · ${plural(r.kinds.fix, 'silent fix', 'silent fixes')} · ${plural(r.kinds.hold, 'hold')}<br><b>${r.followed}</b> followed by an achieved outcome`
      : 'Revive stayed quiet';

    $('vTasks').textContent = r.achieved;
    $('lTasks').innerHTML = r.outcomes
      ? `of <b>${r.outcomes}</b> graded outcomes${r.partial ? ` · ${r.partial} partial` : ''}`
      : 'no outcomes graded yet';

    $('vStrain').textContent = r.bodyMin ? fmtMin(r.strainMin) : '—';
    $('uStrain').hidden = !r.bodyMin;
    $('lStrain').innerHTML = r.bodyMin
      ? `of <b>${fmtMin(r.bodyMin)} min</b> with a heart-rate strap on`
      : 'no body data today';

    const best = r.hours[0], worst = r.hours[r.hours.length - 1];
    $('vBest').textContent = best ? hourLabel(best.h) : '—';
    $('lBest').innerHTML = !best
      ? `needs ${MIN_HOUR_N}+ scored prompts in an hour`
      : r.hours.length === 1
        ? `avg <b>${best.avg.toFixed(1)}</b> (n=${best.n}) · only hour with ${MIN_HOUR_N}+ scored prompts`
        : `avg <b>${best.avg.toFixed(1)}</b> (n=${best.n}) · worst ${hourLabel(worst.h)} at <b>${worst.avg.toFixed(1)}</b> (n=${worst.n})`;

    if (r.pattern) {
      const p = r.pattern, diff = p.ms - p.mc;
      $('patternTxt').innerHTML =
        `Prompts written while strained averaged <b>${p.ms.toFixed(1)}</b> vs <b>${p.mc.toFixed(1)}</b> when calm ` +
        `(${diff >= 0 ? '+' : '−'}${Math.abs(diff).toFixed(1)} pts) ` +
        `<span class="n">n = ${p.nS} strained / ${p.nC} calm${p.d === null ? '' : ` · d = ${p.d.toFixed(2)}`}</span>`;
    }
  }

  function fit() {
    const s = Math.min(innerWidth / 1600, innerHeight / 900);
    $('stage').style.transform = `translate(-50%, -50%) scale(${s})`;
  }

  let shown = false;
  async function load() {
    let events;
    try {
      const res = await fetch('/events?last=5000', { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      events = await res.json();
    } catch (err) {
      // keep the last good card on a blip; show "no data yet" only if nothing was ever shown
      console.warn('wrapped: /events failed', err);
      if (shown) return;
      events = [];
    }
    render(compute(events));
    shown = true;
  }

  addEventListener('resize', fit);
  fit();
  load();
  const timer = setInterval(load, 10000);
  // for checking with synthetic events in the console: wrapped.stop(); wrapped.render(wrapped.compute(events))
  window.wrapped = { compute, render, load, stop: () => clearInterval(timer) };
})();
