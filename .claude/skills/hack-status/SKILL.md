---
name: hack-status
description: Hackathon timekeeper and triage. Use when I ask for status, what's next, or what to cut.
disable-model-invocation: true
---
Timeline (Pacific):
- 2:00 PM: build starts
- 3:45 PM: walking skeleton works end to end (tag demo-1)
- 4:15 PM: gate. If there's no end-to-end moment yet, switch to the fallback.
- 5:00 PM: 60-second backup video recorded
- 6:15 PM: feature freeze (tag demo-final)
- 6:50 PM: video recorded
- 7:10 PM: submitted (deadline 7:30 PM)

Judging criteria: see RUBRIC.md.

Triage rules:
- Protect the freeze.
- Demo path before polish.
- Proof (a number or a before/after) before new features.
- When a fancy path fails twice, take the simple fallback.

When invoked:
1. Run `date` and `git log --oneline -10`. Read SPEC.md and DEMO_NOTES.md.
2. Report in 6 lines max:
   - time to the next milestone
   - what works end to end, with evidence
   - the single next action
   - what to cut if behind
   - any risk to the demo
