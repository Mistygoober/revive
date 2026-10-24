"""Copy the few aggregate numbers the insights page needs into web/insights/learned.json.

Sources (both aggregates only): history/results.json, body/baselines_nbz.json.
Run once after either changes: uv run python web/insights/build_learned.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name("learned.json")


def main() -> None:
    r = json.loads((ROOT / "history/results.json").read_text())
    b = json.loads((ROOT / "body/baselines_nbz.json").read_text())

    t = r["validity_bottom_vs_top_tertile"]
    v = r["validity_low_le4_vs_high_ge7"]
    checks = r["checks_vs_outcomes_spearman"]
    learned = {
        "history": {
            "generated_at": r["generated_at"],
            "dates": "Oct 17–24, 2026",
            "who": "lucas",
            "prompts_graded": r["data"]["graded"],
            "prompts_scored": r["data"]["scored_types"],
            "sessions": r["data"]["sessions_with_prompts"],
            "mean_score": r["scores"]["mean"],
            "split": t["split"],
            "turns_to_done": {k: t["turns_to_done"][k] for k in
                              ("n_low", "n_high", "mean_low", "mean_high", "ratio_low_over_high",
                               "permutation_p", "cliffs_delta_low_vs_high")},
            "achieved": {k: t["achieved"][k] for k in
                         ("n_low", "n_high", "rate_low", "rate_high", "permutation_p",
                          "cliffs_delta_low_vs_high")},
            "spearman": {
                "turns_to_done": {"rho": v["turns_to_done"]["spearman_score_all"],
                                  "p": v["turns_to_done"]["spearman_p"], "n": v["turns_to_done"]["n_all"]},
                "achieved": {"rho": v["achieved_rate"]["spearman_score_all"],
                             "p": v["achieved_rate"]["spearman_p"], "n": v["achieved_rate"]["n_all"]},
            },
            # rho per rubric check vs outcomes (turns_to_done: negative = fewer turns)
            "checks": {c: checks[c] for c in checks},
            "check_zero_rate": r["scores"]["check_zero_rate"],
        },
        "body": {
            "who": b["who"],
            "date_range": b["date_range"],
            "n_days": b["n_days"],
            "resting_hr": b["baseline"]["resting_hr"], "n_resting_hr": b["baseline"]["n_resting_hr"],
            "stress": b["baseline"]["stress"], "n_stress": b["baseline"]["n_stress"],
            "bb_high": b["baseline"]["bb_high"], "bb_low": b["baseline"]["bb_low"],
            "n_bb": b["baseline"]["n_bb_high"],
            "last_day": b["last_day"],
            "missing": b.get("missing", []),
        },
    }
    OUT.write_text(json.dumps(learned, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
