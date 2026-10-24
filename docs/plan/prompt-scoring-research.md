# 07 – Prompt scoring: what the big labs and research say

Researched Sat 2026-10-24 for Revive (prompt grade 0–10 + heart rate). Primary sources were fetched today unless a line says otherwise. Anything marked **(inference)** is our reading, not something the source says.

---

## (a) Sources

### Anthropic – prompt engineering (API docs)
- Overview: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview
  - Prerequisites before prompt engineering: (1) clear **success criteria**, (2) a way to **test empirically** against them, (3) a first draft prompt. Links to "Define success criteria and build evaluations": https://platform.claude.com/docs/en/test-and-evaluate/develop-tests
  - The overview has no technique list of its own. It points to the best-practices page (clarity, examples, XML, role, thinking, chaining) and the metaprompt/prompt-generator notebook.
- Best practices: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
  - **Be clear and direct.** Treat Claude like "a brilliant but new employee who lacks context". The key test is to show the prompt to a colleague with minimal context; if they'd be confused, Claude will be too.
  - **Add context or motivation** (the *why* behind an instruction) for more targeted responses.
  - Be specific about **output format and constraints**. Use numbered steps when order matters. Use examples, XML tags and role. Say what to do rather than what not to do.
  - Agentic and coding: "Ask Claude to self-check… verify your answer against [test criteria]" and "provide verification tools". **Caveat:** the page says Claude Opus 5 verifies its own work without being told, and that carried-over verification instructions can cause *over-verification*.
- Prompt improver and Console tools: the old prompt-improver docs URL (`…/prompt-engineering/prompt-improver`) now redirects to the best-practices page (seen today). We couldn't confirm its current Console form in the time available. The metaprompt notebook is the documented prompt generator: https://colab.research.google.com/github/anthropics/claude-cookbooks/blob/main/misc/metaprompt.ipynb

### Anthropic – Claude Code best practices
- Docs (current, maintained): https://code.claude.com/docs/en/best-practices. The original engineering-blog version is https://www.anthropic.com/engineering/claude-code-best-practices (not re-fetched today).
  - The core constraint is that context fills fast and performance degrades as it fills.
  - **Give Claude a way to verify its work:** tests, a build, a screenshot. "Describe the symptom… the likely location, and what 'fixed' looks like."
  - **Explore → Plan → Implement → Commit.** Skip the plan when "you could describe the diff in one sentence".
  - **Provide specific context:** scope the task (which file, which scenario, testing preferences such as "avoid mocks"), point to sources, reference existing patterns (for example "HotDogWidget.php is a good example"), and paste errors, screenshots or `@file`.
  - "Vague prompts can be useful when you're exploring and can afford to course-correct."
  - **Course-correct early.** "If you've corrected Claude more than twice on the same issue… /clear and start fresh with a more specific prompt."
  - Named failure patterns: kitchen-sink session (unrelated tasks in one session), correcting over and over, trust-then-verify gap, infinite exploration (unscoped "investigate").
  - Specs should "name the files and interfaces involved, state what is out of scope, and end with an end-to-end verification step".

### Anthropic – Economic Index (interaction patterns)
- Original report (Feb 2025): https://www.anthropic.com/news/the-anthropic-economic-index
  - **Automation:** *Directive* (the user delegates with minimal back-and-forth) 27.8%; *Feedback loop* (task done while adjusting to environment feedback) 14.8%.
  - **Augmentation:** *Task iteration* (refining output together) 31.3%; *Learning* 23.3%; *Validation* (checking the user's own work) 2.8%.
  - Overall split: augmentation 57%, automation 43% (Claude.ai).
- Software development report (Apr 2025): https://www.anthropic.com/research/impact-software-development
  - Claude Code is **79% automation**, against 49% on Claude.ai. On Claude Code, directive is 43.8% and feedback loop 35.8%; on Claude.ai, 27.5% and 21.3%.
  - Feedback loop = "Task completion guided by environmental feedback", for example the user pasting errors back.
- Later reports put Claude.ai at 52% augmentation and 45% automation (Nov 2025 data) and enterprise API use at about 75% automated. These figures come from secondary summaries (https://arxiv.org/pdf/2511.15080 and press coverage) and weren't re-verified against the primary report.

### Anthropic – Claude Code analytics and OpenTelemetry
- OTel docs: https://code.claude.com/docs/en/monitoring-usage
  - Metrics: `session.count`, `lines_of_code.count` (added/removed), `pull_request.count`, `commit.count`, `cost.usage` (USD), `token.usage`, `code_edit_tool.decision` (accept/reject), `active_time.total` (seconds, idle excluded).
  - Events: `user_prompt`, `assistant_response`, `tool_result`, `tool_decision`, `api_request`, `api_error`, `api_refusal`, `safety_event`, and others.
  - Prompt text is **redacted by default**; set `OTEL_LOG_USER_PROMPTS=1` to log it.
- Analytics dashboard: https://code.claude.com/docs/en/analytics. It shows lines of code accepted, **suggestion accept rate** (Edit/Write/NotebookEdit accepts ÷ decisions), daily active users, sessions per day, PRs with Claude Code (merged PRs with at least one Claude Code line), % of PRs with Claude Code, PRs per user (merged PRs per day ÷ DAU), a leaderboard and spend. The docs suggest using it "alongside DORA metrics".

### OpenAI – prompt engineering guide
- https://developers.openai.com/api/docs/guides/prompt-engineering (`platform.openai.com/docs/guides/prompt-engineering` redirects here)
  - Structure developer messages as **Identity → Instructions → Examples → Context**. Use few-shot examples with "a diverse range of possible inputs". Supply relevant context or RAG.
  - Store prompts in code with tests, and build **evals** to measure prompt changes.
  - Coding tips: define the role, **require testing and validate patches**, because tools "may return 'Done' even on failure". For agentic work, plan sub-tasks and resolve the full query.
  - Reasoning models do well with high-level goals; GPT models need precise, explicit instructions.
  - The older six "strategies" list (clear instructions, reference text, split complex tasks, give time to think, external tools, test systematically) isn't on the current page. We didn't verify where it lives now.

### Google – Gemini prompting strategies
- https://ai.google.dev/gemini-api/docs/prompting-strategies
  - Clear and specific instructions; **constraints** (what to do and not do); response **format**; zero-shot or few-shot examples; **add context**; **break down prompts** (one instruction per prompt, chaining); iterate.
  - Persona / task / context / format: the page uses `<role>`, `<task>` and `<context>` tags plus output-format requirements. With long context, put the context first and the instructions last.

### Microsoft / GitHub
- Microsoft 365 Copilot "Write effective prompts" (Microsoft Learn): https://learn.microsoft.com/en-us/training/modules/write-effective-prompts-do-more-prompting
  - Four elements: **Goal** (what you want), **Context** (why and who), **Source** (which files or data to use), **Expectations** (format, tone, audience). "A clear goal is the foundation." The same four appear in Security Copilot: https://learn.microsoft.com/en-us/copilot/security/prompting-tips
- GitHub Copilot best practices: https://docs.github.com/en/copilot/get-started/best-practices
  - "Break down complex tasks", "Be specific about your requirements", "Provide examples" (inputs, outputs, implementations). Keep relevant files open and close unrelated ones. Start a new conversation when the current context isn't helping.
- GitHub Copilot usage metrics: https://docs.github.com/en/copilot/concepts/copilot-usage-metrics/copilot-metrics
  - DAU/WAU/MAU, engaged users, **acceptance rate** ("how often developers accept Copilot's suggestions"), lines suggested, accepted and deleted, chat requests per active user, agent adoption, PRs created and merged (all vs Copilot), median time to merge, code-review adoption.
- DORA: https://dora.dev/guides/dora-metrics/
  - Throughput: change lead time, deployment frequency, failed-deployment recovery time.
  - Instability: change fail rate, deployment rework rate.
- SPACE (Forsgren et al., ACM Queue 2021): https://queue.acm.org/detail.cfm?id=3454124 (returned a 403 today; summarized from our knowledge)
  - Satisfaction and well-being, Performance, Activity, Communication and collaboration, Efficiency and flow.
  - Its core advice is to use several dimensions, including perceptual ones, and never activity counts alone.

### Research
1. **Laban et al. 2025, "LLMs Get Lost In Multi-Turn Conversation"**: https://arxiv.org/abs/2505.06120. Over 200k simulated conversations, all top models do worse when the instruction is **spread across underspecified turns** than when it is fully specified up front: "an average drop of 39% across six generation tasks". Most of the drop is unreliability, not lost aptitude.
2. **Mu et al. 2023, ClarifyGPT**: https://arxiv.org/abs/2310.10996. Clarifying ambiguous requirements before generating code raised GPT-4 pass@1 on MBPP-sanitized from 70.96% to 80.80% (human evaluation). Across 4 benchmarks, GPT-4 went from 68.02% to 75.75% and ChatGPT from 58.55% to 67.22%. This is direct evidence that **requirement clarity causes code success**.
3. **DevGPT (Xiao et al. 2023)**: https://arxiv.org/abs/2309.03914. A dataset of real developer–ChatGPT conversations shared on GitHub and Hacker News. It poses (but doesn't answer) whether prompt patterns correlate with issue resolution. Champa et al. (MSR 2024) find developers rely on follow-ups, prompt refinement and clarification turns. A possible benchmark for Revive (inference).
4. **METR, Becker et al. 2025**: https://arxiv.org/abs/2507.09089. In an RCT with 16 experienced OSS developers and 246 tasks, AI use **increased** completion time by 19%. Developers forecast a 24% speedup and afterwards believed they'd been 20% faster. Self-reported productivity is unreliable, so measure.
5. **LLM-as-judge, Zheng et al. 2023 (MT-Bench)**: https://arxiv.org/abs/2306.05685. GPT-4 judges reach over 80% agreement with human preferences, about the same as human–human agreement. The paper documents **position, verbosity and self-enhancement biases**.
- **Gap:** in the time available we found no study that scores the specificity of real developer prompts and links it to merged or working code. The ClarifyGPT and Laban results are the closest causal evidence.

---

## (b) Merged table: criterion → who backs it

| Criterion | Anthropic API docs | Claude Code docs | OpenAI | Google Gemini | Microsoft / GitHub | Research |
|---|---|---|---|---|---|---|
| **Goal / specific outcome** | yes (clear, direct, "colleague test") | yes ("be specific", "what fixed looks like") | yes (explicit instructions) | yes (clear, specific) | yes (Goal = "foundation"; "be specific") | ClarifyGPT (clarity raises pass@1) |
| **Context** (error, files, situation) | yes (add context) | yes (paste error, `@file`, symptom + location) | yes (Context section, RAG) | yes (add context) | yes (Context; open the relevant files) | Laban (underspecification −39%) |
| **Point to sources / examples / existing patterns** | yes (examples) | yes ("point to sources", "reference existing patterns") | yes (few-shot) | yes (few-shot) | yes (Source; "provide examples") | – |
| **Done check / verification** | yes (success criteria; self-check, with an Opus 5 caveat) | **strongest** ("give Claude a way to verify") | yes (require testing, validate patches) | – | – | – |
| **Constraints / scope** (what to touch or avoid) | yes (constraints) | yes (scope the task; out-of-scope list; "avoid mocks") | partial | yes (constraints) | partial (Expectations) | – |
| **Output format / expectations** | yes | low relevance for code edits (inference) | yes | yes (format) | yes (Expectations) | – |
| **Why / motivation** | yes (explain why) | implicit | – | – | yes (Context = "why") | – |
| **One task / break down** | partial (prompt chaining) | yes, session-level ("kitchen sink", `/clear` between tasks) | partial | yes (break down prompts) | yes ("break down complex tasks") | – |
| **Plan before big changes** | partial (let Claude think) | yes (explore → plan → code; skip if one-sentence diff) | yes (plan sub-tasks) | – | – | ClarifyGPT (clarify first) |
| **Course-correct early / restart after 2 failed corrections** | – | yes | – | yes (iterate) | yes (new conversation) | Laban (models don't recover once lost) |

---

## (c) Usage and productivity metrics in use

| Metric | Who uses it | Definition (per source) |
|---|---|---|
| Sessions | Claude Code OTel `session.count`; dashboard "sessions per day" | CLI sessions started; active sessions per day |
| Active time | Claude Code `active_time.total` | Seconds of active use, idle excluded |
| DAU / WAU / MAU | Claude Code dashboard; GitHub Copilot | Unique users who used the tool that day, week or month |
| Engaged users | GitHub Copilot | Users active on a given day (API `total_engaged_users`) |
| Suggestion / acceptance rate | Claude Code (Edit/Write/NotebookEdit accept ÷ decisions); GitHub Copilot | Share of suggested edits the developer accepts |
| Tool accept/reject | Claude Code `code_edit_tool.decision`, `tool_decision` event | Each permission decision on a tool call |
| Lines of code | Claude Code `lines_of_code.count`, "lines accepted"; Copilot lines suggested, accepted, deleted | Lines added or removed; Claude Code doesn't track later deletions |
| Commits / PRs | Claude Code `commit.count`, `pull_request.count`, "PRs with CC", "PRs per user"; Copilot PRs created, merged, median time to merge | Merged PRs with at least one AI-attributed line; PRs per day ÷ DAU |
| Cost / tokens | Claude Code `cost.usage`, `token.usage` | USD and tokens per session |
| Chat requests per user | GitHub Copilot | Average chat requests per active user |
| Interaction pattern mix | Anthropic Economic Index | Share of directive, feedback-loop, task-iteration, learning and validation conversations |
| DORA five | DORA / Google | Lead time, deploy frequency, recovery time, change fail rate, rework rate |
| SPACE five | Microsoft Research / GitHub (Forsgren) | Satisfaction and well-being, performance, activity, collaboration, efficiency and flow |

What this means for Revive (inference):
- A hook on `UserPromptSubmit` already receives the prompt text, so we don't need `OTEL_LOG_USER_PROMPTS`.
- Our per-prompt score plus heart rate fills a gap: every vendor metric above is an **output or activity** count. None measures **input quality** or **well-being**, and well-being is the "S" in SPACE.
- METR argues for showing measured data rather than asking people how productive they felt.

---

## (d) Suggested changes to our draft rubric

Draft: classify the prompt (new task, follow-up, confirmation, question), score only tasks and follow-ups, with 5 checks at 0–2 each (Goal, Context, Done check, Scope, One task), judged against what Claude already knows. The grader never sees heart data.

**Keep as is (strongly backed):**
1. **Goal**. Every source backs it; Microsoft calls it "the foundation".
2. **Context, judged against what the conversation already has**. Anthropic's colleague test and Claude Code's "paste the error, @file" back it. Grading against conversation state, not prompt length, is right: Zheng et al. show LLM judges have **verbosity bias**, so a length-blind rule guards against it.
3. **Done check**. Claude Code's top tip, and OpenAI also says to require tests. Refine it as below.
4. **Grader never sees heart data**. Good for avoiding judge bias (inference; no source tests it directly).

**Change:**
5. **Fold "points to a source, example or existing pattern" into Context and say so explicitly.** A 2 needs either the failing evidence (error, log) or a pointer (`@file`, "follow HotDogWidget.php", a URL). Backed by Claude Code ("point to sources", "reference existing patterns"), Microsoft (Source), OpenAI and Gemini (few-shot), GitHub ("provide examples").
6. **Rename Scope to "Scope and constraints"** and count stated constraints ("no new deps", "avoid mocks", "don't touch the migrations"). Backed by Gemini constraints, the Anthropic constraints line, and Claude Code's "avoid mocks" and "state what is out of scope".
7. **Reweight "One task" from 0–2 to 0–1 and redefine it as "no unrelated asks bundled".** Multi-step prompts within one task are *recommended* by Claude Code ("implement… write tests… run the test suite and fix failures"), so don't penalize them. Mixing unrelated work is the "kitchen sink" failure. Backed by Claude Code, GitHub ("break down complex tasks") and Gemini ("break down prompts").
8. **Use the freed point for "Why / intent" (0–1)**: does the prompt say what the change is for, or who it's for? Backed by Anthropic ("add context or motivation") and Microsoft (Context = "why"). New weights: Goal 2, Context 2, Done 2, Scope 2, Focus 1, Why 1 = 10.
9. **Make the Done check size-aware.** For a trivial edit (typo, rename, a one-sentence diff), score the Done check as satisfied by default; Claude Code says to skip the plan for those. For multi-file work, a request to "plan first" or "interview me" also earns Done or Scope credit (Claude Code explore → plan; ClarifyGPT). Count outcome criteria ("what fixed looks like", an expected value, a test to pass) as a 2. Don't require the literal words "run tests", since Anthropic warns Opus 5 can over-verify when told to.
10. **Add an "exploration" class, left unscored.** Claude Code: "Vague prompts can be useful when you're exploring." This keeps us from penalizing "what would you improve here?". Questions already go unscored, so make sure open-ended exploration requests count as questions too.
11. **Track corrections as a session signal, not a per-prompt score.** Count follow-ups that correct Claude on the same issue. At 3 or more, nudge toward `/clear` and a fuller prompt (Claude Code's "more than twice" rule). Laban shows models rarely recover once lost in multi-turn conversations. This also maps to the Economic Index *feedback loop* vs *task iteration* patterns, which we could tag per session.
12. **Tag each scored prompt with an Economic Index pattern** (directive, feedback loop, task iteration, learning, validation) so our stats line up with Anthropic's published shares, such as Claude Code at 43.8% directive and 35.8% feedback loop. This is cheap for the grader and gives a credible comparison chart (inference).
13. **Judge reliability:**
    - Use a fixed rubric with anchored 0/1/2 examples for each check, temperature 0, and the classify-then-score order.
    - Hand-label about 30 real prompts and report agreement. Zheng et al. found over 80% human agreement is achievable for strong judges, but measure ours rather than assume it.
    - Don't let the grader see Claude's reply. That avoids grading the prompt by its outcome. This is our own inference, related to the biases Zheng documents.

**Drop:** no check needs dropping. Output format / expectations (Microsoft, Gemini, OpenAI) is the one widely backed criterion we leave out on purpose, because it matters little for code-edit prompts (inference). Mention it in the pitch as a deliberate choice.
