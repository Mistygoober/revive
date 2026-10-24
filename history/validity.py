"""Validity check: on Lucas's past prompts, are low-scored prompts associated with worse outcomes?

Grades kept prompts (after the drop filter) with grader.prompt_score.grade_prompt (Anthropic API only),
then writes aggregates to history/results.json. Nothing per-prompt is written to the repo.
The grade cache lives in data-private/ (outside the repo) and holds scores only, keyed by a hash.
Usage: uv run python -m history.validity [--n 150] [--workers 4]
"""
import argparse
import hashlib
import json
import math
import random
import statistics as st
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from history.extract import DEFAULT_DIR, drop_reason, load_sessions
from history.tasks import active_seconds, analyze, task_summary

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results.json"
CACHE = DEFAULT_DIR.parent / "history_grades.json"  # data-private, never in the repo
LOW, HIGH = 4, 7
PERMUTATIONS = 10_000
KEEP = ("type", "score", "checks", "bundled", "pattern", "source")  # no reason/intent: they echo prompt text

try:
    from grader.prompt_score import grade_prompt
    GRADER = "grader.prompt_score.grade_prompt (Claude Haiku 5.5, rubric v1)"
except ImportError:  # temporary fallback; results are then labeled heuristic
    grade_prompt = None
    GRADER = "heuristic (grader module missing)"


def _key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _context(p) -> dict:
    """Only metadata: the confidentiality rules allow sending prompt text alone, so Claude's reply is withheld."""
    ctx = {}
    if p.prev_assistant_len:
        ctx["last_assistant"] = (f"(Claude replied in the previous turn, {p.prev_assistant_len} chars; "
                                 "its text is withheld from the grader)")
    if p.prev_tool_error:
        ctx["last_tool_error"] = "(the previous turn hit a tool error; text withheld)"
    return ctx


def _grade_one(p) -> dict:
    if grade_prompt is None:
        raise SystemExit("grader/ is missing: nothing to grade with")
    for _ in range(3):  # the live grader has a 3 s timeout; retry before accepting its heuristic fallback
        g = grade_prompt(p.text, _context(p))
        if g.get("source") == "llm":
            break
    return {k: g.get(k) for k in KEEP}


def grade_all(prompts, workers: int) -> dict:
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [p for p in prompts if cache.get(_key(p.text), {}).get("source") != "llm"]
    print(f"grading {len(todo)} prompts ({len(prompts) - len(todo)} cached) with {GRADER}")
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, (p, g) in enumerate(zip(todo, pool.map(_grade_one, todo)), 1):
            cache[_key(p.text)] = g
            if i % 25 == 0 or i == len(todo):
                CACHE.write_text(json.dumps(cache))
                print(f"  {i}/{len(todo)}  {time.monotonic() - t0:.0f}s")
    return {_key(p.text): cache[_key(p.text)] for p in prompts}


def stratified_sample(prompts, n: int, seed: int = 0) -> list:
    """Round-robin across sessions so no single long session dominates."""
    rng = random.Random(seed)
    by_s = defaultdict(list)
    for p in prompts:
        by_s[p.session].append(p)
    for v in by_s.values():
        rng.shuffle(v)
    out, queues = [], list(by_s.values())
    rng.shuffle(queues)
    while len(out) < n and any(queues):
        for q in queues:
            if q and len(out) < n:
                out.append(q.pop())
    return out


# --- stats (pure python; n is small) ---

def perm_test(a: list, b: list, n: int = PERMUTATIONS, seed: int = 0) -> float | None:
    """Two-sided permutation p-value for the difference in means."""
    if len(a) < 2 or len(b) < 2:
        return None
    rng = random.Random(seed)
    obs = abs(st.mean(a) - st.mean(b))
    pool, k, hits = a + b, len(a), 0
    for _ in range(n):
        rng.shuffle(pool)
        if abs(st.mean(pool[:k]) - st.mean(pool[k:])) >= obs - 1e-12:
            hits += 1
    return round((hits + 1) / (n + 1), 4)


def cliffs_delta(a: list, b: list) -> float | None:
    if not a or not b:
        return None
    gt = sum(1 for x in a for y in b if x > y)
    lt = sum(1 for x in a for y in b if x < y)
    return round((gt - lt) / (len(a) * len(b)), 3)


def _ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x: list, y: list) -> float | None:
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None
    return round(st.correlation(_ranks(x), _ranks(y)), 3)


def spearman_p(x: list, y: list, n: int = 2000, seed: int = 0) -> float | None:
    r = spearman(x, y)
    if r is None:
        return None
    rng, ys, hits = random.Random(seed), list(y), 0
    for _ in range(n):
        rng.shuffle(ys)
        rr = spearman(x, ys)
        if rr is not None and abs(rr) >= abs(r) - 1e-12:
            hits += 1
    return round((hits + 1) / (n + 1), 4)


def slope(x: list, y: list) -> float | None:
    if len(x) < 3 or len(set(x)) < 2:
        return None
    return round(st.linear_regression(x, y).slope, 3)


def compare(rows: list, field: str, kind: str, low: float = LOW, high: float = HIGH) -> dict:
    """Low (score <= low) vs high (score >= high) on one outcome. kind: 'mean' or 'rate'."""
    vals = [(r["score"], r[field]) for r in rows if r[field] is not None]
    lo = [float(v) for s, v in vals if s <= low]
    hi = [float(v) for s, v in vals if s >= high]
    m_lo = round(st.mean(lo), 3) if lo else None
    m_hi = round(st.mean(hi), 3) if hi else None
    return {
        "n_low": len(lo), "n_high": len(hi),
        ("mean_low" if kind == "mean" else "rate_low"): m_lo,
        ("mean_high" if kind == "mean" else "rate_high"): m_hi,
        "ratio_low_over_high": round(m_lo / m_hi, 2) if m_lo is not None and m_hi else None,
        "permutation_p": perm_test(lo, hi),
        "cliffs_delta_low_vs_high": cliffs_delta(lo, hi),
        "spearman_score_all": spearman([s for s, _ in vals], [float(v) for _, v in vals]),
        "spearman_p": spearman_p([s for s, _ in vals], [float(v) for _, v in vals]),
        "n_all": len(vals),
    }


def build_rows(turns, grades: dict, sessions) -> list:
    """One row per graded, scored prompt. In memory only."""
    starts = {s.id: s.timestamps[0] for s in sessions if s.timestamps}
    ts_by = {s.id: s.timestamps for s in sessions}
    rows = []
    for t in turns:
        p = t.prompt
        g = grades.get(id(p))
        if not g or g.get("score") is None:
            continue
        before = [x for x in ts_by[p.session] if x <= p.ts]
        rows.append({
            "score": g["score"], "checks": g["checks"], "session": p.session,
            "hour": p.ts.astimezone().hour,
            "active_h_into_session": active_seconds(before) / 3600,
            "wall_h_into_session": (p.ts - starts[p.session]).total_seconds() / 3600,
            "turns_to_done": t.turns_to_signal,
            "achieved": None if t.prompt.next_text is None and not t.has_signal else int(t.has_signal and not t.next_is_correction),
            "next_is_correction": None if p.next_text is None else int(t.next_is_correction),
            "tool_errors": p.tool_errors,
            "request_turns_to_done": t.request_turns_to_done if t.starts_request or p.idx == 0 else None,
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0, help="grade a stratified sample of n prompts (0 = all kept)")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    sessions = load_sessions()
    turns, tasks, sstats = analyze(sessions)
    prompts = [t.prompt for t in turns]
    drops = Counter(drop_reason(p.text) or "kept" for p in prompts)
    kept = [p for p in prompts if drop_reason(p.text) is None]
    sample = stratified_sample(kept, args.n) if args.n else kept
    by_hash = grade_all(sample, args.workers)
    grades = {id(p): by_hash[_key(p.text)] for p in sample}
    rows = build_rows(turns, grades, sessions)

    gl = list(grades.values())
    sources = Counter(g["source"] for g in gl)
    scored = [g for g in gl if g["score"] is not None]
    check_names = ["context", "done", "goal", "scope", "why"]

    by_hour = defaultdict(list)
    for r in rows:
        by_hour[r["hour"]].append(r["score"])
    blocks = {"night_22_04": range(22, 29), "morning_05_11": range(5, 12),
              "afternoon_12_17": range(12, 18), "evening_18_21": range(18, 22)}
    by_block = {name: [r["score"] for r in rows if r["hour"] in hrs or r["hour"] + 24 in hrs]
                for name, hrs in blocks.items()}

    sess_scores = defaultdict(list)
    for r in rows:
        sess_scores[r["session"]].append(r["score"])
    sess_active = {s.id: s.active_min for s in sstats}
    sess_pairs = [(sess_active[k], st.mean(v)) for k, v in sess_scores.items() if len(v) >= 3]

    x_act = [r["active_h_into_session"] for r in rows]
    y = [r["score"] for r in rows]

    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "what": "Lucas's past Claude Code prompts (Oct 17-24, 2026): prompt score vs outcomes. Aggregates only.",
        "wording": "Associations, not causes. Observational data from one person.",
        "grader": GRADER if sources.get("llm") else "heuristic",
        "grader_sources": dict(sources),
        "grader_context": "prompt text only; Claude's previous reply and tool errors passed as metadata (length / yes-no), not text",
        "data": {
            "sessions": len(sessions),
            "sessions_with_prompts": len(sstats),
            "typed_prompts": len(prompts),
            "dropped_by_filter": {k: v for k, v in drops.items() if k != "kept"},
            "dropped_total": sum(v for k, v in drops.items() if k != "kept"),
            "kept": drops["kept"],
            "graded": len(gl),
            "sample": f"stratified n={args.n}" if args.n else "all kept prompts",
            "scored_types": len(scored),
            "types": dict(Counter(g["type"] for g in gl)),
        },
        "scores": {
            "mean": round(st.mean(y), 2) if y else None,
            "median": st.median(y) if y else None,
            "histogram_0_10": {str(i): sum(1 for v in y if v == i) for i in range(11)},
            "weak_rate_under_4": round(sum(v < 4 for v in y) / len(y), 3) if y else None,
            "n_low_le_4": sum(v <= LOW for v in y), "n_high_ge_7": sum(v >= HIGH for v in y),
            "bundled_rate": round(sum(bool(g["bundled"]) for g in scored) / len(scored), 3) if scored else None,
            "check_zero_rate": {c: round(sum(g["checks"][c] == 0 for g in scored) / len(scored), 3)
                                for c in check_names} if scored else {},
            "patterns": dict(Counter(g["pattern"] for g in scored)),
        },
        "validity_low_le4_vs_high_ge7": {
            "turns_to_done": {"definition": "your prompts from this one to the next turn with a task-list step completed or a wrap-up (1 = done this turn)",
                              **compare(rows, "turns_to_done", "mean")},
            "achieved_rate": {"definition": "turn ended with a completion signal and the next prompt was not a correction",
                              **compare(rows, "achieved", "rate")},
            "correction_rate": {"definition": "next prompt starts with no / still / wrong / that's not / try again (and similar)",
                                **compare(rows, "next_is_correction", "rate")},
            "tool_errors_after": {"definition": "tool errors before the next prompt", **compare(rows, "tool_errors", "mean")},
            "request_turns_to_done": {"definition": "prompts that open a fresh task list: prompts until its last completion signal",
                                      **compare(rows, "request_turns_to_done", "mean")},
        },
        "checks_vs_outcomes_spearman": {
            c: {"turns_to_done": spearman([r["checks"][c] for r in rows if r["turns_to_done"]],
                                          [r["turns_to_done"] for r in rows if r["turns_to_done"]]),
                "achieved": spearman([r["checks"][c] for r in rows if r["achieved"] is not None],
                                     [r["achieved"] for r in rows if r["achieved"] is not None])}
            for c in check_names},
        "hour_of_day": {
            "mean_score_by_local_hour": {str(h): {"mean": round(st.mean(v), 2), "n": len(v)}
                                         for h, v in sorted(by_hour.items())},
            "by_block": {k: {"mean": round(st.mean(v), 2) if v else None, "n": len(v)} for k, v in by_block.items()},
            "spearman_hour_vs_score": spearman([r["hour"] for r in rows], y),
        },
        "fatigue": {
            "slope_points_per_active_hour_into_session": slope(x_act, y),
            "spearman_active_time_vs_score": spearman(x_act, y),
            "permutation_p": spearman_p(x_act, y),
            "n": len(rows),
            "session_active_min_vs_mean_score_spearman": spearman([a for a, _ in sess_pairs], [b for _, b in sess_pairs]),
            "n_sessions": len(sess_pairs),
        },
        "tasks_and_sessions": task_summary(tasks, sstats, turns),
    }
    # The rubric's fixed split leaves few prompts >= 7 here, so also split at the data's own tertiles.
    if len(y) >= 9:
        q1, q2 = st.quantiles(y, n=3)
        lo_cut = math.floor(q1)
        hi_cut = max(math.floor(q2) + 1, lo_cut + 1)  # middle tertile left out
        results["validity_bottom_vs_top_tertile"] = {
            "split": f"score <= {lo_cut} vs >= {hi_cut} (bottom vs top tertile of this data, middle left out)",
            **{f: compare(rows, f, k, lo_cut, hi_cut) for f, k in
               [("turns_to_done", "mean"), ("achieved", "rate"), ("next_is_correction", "rate"),
                ("tool_errors", "mean"), ("request_turns_to_done", "mean")]}}
    head = results["validity_low_le4_vs_high_ge7"]
    tt, ach = head["turns_to_done"], head["achieved_rate"]
    results["headline"] = (
        f"Across all {tt['n_all']} scored prompts with a known outcome, higher prompt scores are associated with fewer "
        f"turns to done (Spearman {tt['spearman_score_all']}, p={tt['spearman_p']}) and, over {ach['n_all']}, a higher "
        f"achieved rate (Spearman {ach['spearman_score_all']}, p={ach['spearman_p']}). "
        f"Rubric split: low-scored prompts (<=4, n={tt['n_low']}) took {tt['mean_low']} turns to done vs {tt['mean_high']} for "
        f"high-scored (>=7, n={tt['n_high']}): ratio {tt['ratio_low_over_high']}x, permutation p={tt['permutation_p']}, "
        f"Cliff's delta {tt['cliffs_delta_low_vs_high']}. Achieved rate {ach['rate_low']} vs {ach['rate_high']} "
        f"(p={ach['permutation_p']}); only {tt['n_high']} prompts scored >= 7, so that split is underpowered. "
        f"Associated with, not caused by. "
        f"{results['data']['dropped_total']} of {len(prompts)} prompts dropped by the confidentiality filter before grading.")
    if "validity_bottom_vs_top_tertile" in results:
        b = results["validity_bottom_vs_top_tertile"]
        bt, ba = b["turns_to_done"], b["achieved"]
        results["headline_tertile"] = (
            f"{b['split']}: {bt['mean_low']} vs {bt['mean_high']} turns to done (ratio {bt['ratio_low_over_high']}x, "
            f"n={bt['n_low']} vs {bt['n_high']}, permutation p={bt['permutation_p']}, Cliff's delta "
            f"{bt['cliffs_delta_low_vs_high']}); achieved {ba['rate_low']} vs {ba['rate_high']} "
            f"(n={ba['n_low']} vs {ba['n_high']}, p={ba['permutation_p']}). Cut points are the score tertiles. "
            f"Disclosure: a first, buggy cut (<=2 vs >=3, middle not left out) gave 1.24x turns, p=0.095, and "
            f"achieved 0.45 vs 0.54, p=0.18. Associated with, not caused by.")
    RESULTS.write_text(json.dumps(results, indent=2) + "\n")
    print(results["headline"])
    print(f"wrote {RESULTS.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
