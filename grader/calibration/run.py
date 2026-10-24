"""Calibration: does the grader agree with an expert (Lucas) on made-up prompts?

Run: uv run python -m grader.calibration.run grader/calibration/set1.json
Scored prompts: agreement = |grader - expert| <= 1 (also reports <= 2).
Unscored types (confirmation, question, exploration): agreement = the grader
leaves them alone (no score, no nudge) and the expert rated them fine (>= 6).
"""
import json
import sys

from grader.prompt_score import grade_prompt

items = json.load(open(sys.argv[1]))
rows, within1, within2, scored_n, unscored_ok, unscored_n = [], 0, 0, 0, 0, 0
for it in items:
    g = grade_prompt(it["prompt"], it["context"])
    scored = g.get("type") in ("new_task", "follow_up") and g.get("score") is not None
    if scored:
        scored_n += 1
        d = abs(g["score"] - it["lucas"])
        within1 += d <= 1
        within2 += d <= 2
        verdict = "agree" if d <= 1 else ("close" if d <= 2 else "DISAGREE")
    else:
        unscored_n += 1
        ok = it["lucas"] >= 6
        unscored_ok += ok
        verdict = "agree (left alone)" if ok else "DISAGREE"
    rows.append((it["id"], it["lucas"], g.get("score"), g.get("type"), g.get("source"), verdict))
for r in rows:
    print(f"#{r[0]:>2}  expert {r[1]:>2}  grader {str(r[2]):>4}  {r[3]:<12} {r[4]:<9} {r[5]}")
total_ok = within1 + unscored_ok
print(f"\nscored prompts: within 1 point {within1}/{scored_n}, within 2 points {within2}/{scored_n}")
print(f"unscored prompts left alone and rated fine by expert: {unscored_ok}/{unscored_n}")
print(f"overall agreement: {total_ok}/{len(items)}")
json.dump({"items": len(items), "scored": scored_n, "within1": within1, "within2": within2,
           "unscored": unscored_n, "unscored_agree": unscored_ok, "overall_agree": total_ok,
           "rows": [dict(zip(["id", "expert", "grader", "type", "source", "verdict"], r)) for r in rows]},
          open("grader/calibration/results_set1.json", "w"), indent=1)
