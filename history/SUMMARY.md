# History validity: Lucas's past prompts, Oct 17–24 (aggregates only, no prompt text)

1. **Data:** 70 sessions, 665 typed prompts. The confidentiality filter dropped **53** before grading (49 customer name, 3 over 4,000 chars, 1 Portuguese). The other 612 were graded by Claude Haiku 5.5 (611 by the LLM, 1 by the heuristic fallback). 239 were real asks (new task or follow-up) and got a score.
2. **Headline:** across all scored prompts, a higher score is **associated with** fewer turns to done (Spearman −0.24, p=0.003, n=170) and a higher achieved rate (Spearman +0.23, p=0.001, n=229).
3. **Bottom vs top tertile** (score ≤2, n=60, vs ≥4, n=48): **1.8 vs 1.27 turns to done (1.42×, permutation p=0.034, Cliff's δ 0.24)**. Achieved: 45% vs 73% (n=83 vs 56, p=0.0007).
4. **The rubric's split (≤4 vs ≥7) is underpowered:** only 3 prompts scored ≥7. Result: 1.23× turns, p=0.82.
5. **What predicts outcomes:** the done check and the goal check carry the signal (ρ ≈ ±0.25–0.29). Context, as graded here, carries none (ρ ≈ 0), probably because the grader never saw Claude's previous reply (see 9).
6. **Scores:** mean 2.75/10, 76% under 4. Scope and why are missing in about 90% of asks. 18% of asks bundle unrelated requests.
7. **Time of day and fatigue:** no association found. Hour vs score ρ=0.03. Score vs active time into a session: slope +0.12 points per hour, p=0.33.
8. **Work:** 30.8 active hours. Median session is 21 active minutes. 191 requests (fresh task lists), median 1 turn to done. 39 of 40 tracked tasks reached a completion signal.
9. **Caveats:** one person, one week, observational. "Achieved" is a proxy: the turn ended with a step completed or a wrap-up, and the next prompt was not a correction. Explicit corrections are rare (4 of 665). To meet the data rules, the grader saw prompt text only (Claude's reply as length only), which pushes context scores down. The tertile cut was the second cut tried; the first, buggy one (≤2 vs ≥3) gave 1.24×, p=0.095.
10. Reproduce with `uv run python -m history.validity` (it reads the grade cache in data-private/). Full numbers are in `history/results.json`.
