"""Task boundaries and session metrics from task-list tool calls. Counts only.

A task starts at a session's first prompt, or at a prompt whose turn opens a task list with scope
first_task / new_task (a fresh list with no scope also counts). It runs until the next task starts.
It is done at the last prompt in it whose turn had a completion signal (a step marked completed or a
wrap_up). Turns to done = prompts from the start through that one. No signal = left undone.
Usage: uv run python -m history.tasks
"""
import re
import statistics as st
from dataclasses import dataclass, field

from history.extract import Prompt, Session, load_sessions

CORRECTION = re.compile(r"^\W*(no\b|nope\b|still\b|wrong\b|that'?s not\b|that is not\b|try again\b|not quite\b|"
                        r"it'?s not\b|you didn'?t\b|you forgot\b|why did you\b|didn'?t work\b|doesn'?t work\b)", re.I)
ACTIVE_GAP_S = 5 * 60


def is_correction(text: str | None) -> bool:
    return bool(text) and bool(CORRECTION.match(text))


class PlanState:
    """Replays update_plan / wrap_up / TodoWrite calls; reports steps completed per turn."""

    def __init__(self):
        self.steps: list[str] = []

    def apply(self, kind: str, inp: dict | None) -> tuple[int, str | None]:
        """Returns (steps newly completed, scope if this op opened a new list)."""
        before = self.steps.count("completed")
        scope = None
        if kind == "wrap_up":
            self.steps = ["completed"] * len(self.steps)
        elif kind == "todo":
            self.steps = [t.get("status", "pending") for t in (inp or {}).get("todos", [])]
            before = min(before, self.steps.count("completed"))
        elif kind == "plan":
            inp = inp or {}
            if "items" in inp:
                was_empty = not self.steps or all(x == "completed" for x in self.steps)
                self.steps = [i.get("status", "pending") for i in inp["items"]]
                scope = inp.get("scope") or ("new_task" if was_empty else "continuation")
                before = 0
            if inp.get("advance") and self.steps:
                if "in_progress" in self.steps:
                    self.steps[self.steps.index("in_progress")] = "completed"
                if "pending" in self.steps:
                    self.steps[self.steps.index("pending")] = "in_progress"
            for n in inp.get("done") or []:
                if isinstance(n, int) and 0 < n <= len(self.steps):
                    self.steps[n - 1] = "completed"
            n = inp.get("start")
            if isinstance(n, int) and 0 < n <= len(self.steps):
                self.steps[n - 1] = "in_progress"
        return max(0, self.steps.count("completed") - before), scope

    def undone(self) -> int:
        return sum(1 for x in self.steps if x != "completed")


@dataclass
class Turn:
    prompt: Prompt
    task: int = 0
    starts_task: bool = False
    starts_request: bool = False   # opened a fresh task list (any scope)
    request_turns_to_done: int | None = None  # set on the request's first turn
    turns_to_signal: int | None = None  # prompts from this one to the next completion signal (1 = this turn)
    completed_steps: int = 0
    wrap_up: bool = False
    has_signal: bool = False
    next_is_correction: bool = False


@dataclass
class Task:
    session: str
    turns: list = field(default_factory=list)
    done_at: int | None = None  # index in turns of the last completion signal

    @property
    def done(self) -> bool:
        return self.done_at is not None

    @property
    def turns_to_done(self) -> int | None:
        return None if self.done_at is None else self.done_at + 1

    @property
    def corrections(self) -> int:
        return sum(1 for t in self.turns[1:] if is_correction(t.prompt.text))

    @property
    def tool_errors(self) -> int:
        return sum(t.prompt.tool_errors for t in self.turns)


@dataclass
class SessionStats:
    id: str
    prompts: int
    active_min: float
    length_min: float
    start_hour: int
    tasks: int
    tasks_done: int
    steps_left_undone: int
    used_task_list: bool


def active_seconds(timestamps: list) -> float:
    return sum(g for g in ((b - a).total_seconds() for a, b in zip(timestamps, timestamps[1:])) if g < ACTIVE_GAP_S)


def build_tasks(session: Session) -> tuple[list[Turn], list[Task], int]:
    """Turns, tasks and steps still not completed at session end."""
    plan, turns, tasks = PlanState(), [], []
    for p in session.prompts:
        t = Turn(prompt=p, next_is_correction=is_correction(p.next_text))
        for kind, inp in p.plan_ops:
            n, scope = plan.apply(kind, inp)
            t.completed_steps += n
            t.wrap_up |= kind == "wrap_up"
            if scope and t.completed_steps == 0:
                t.starts_request = True
                if scope in ("first_task", "new_task"):
                    t.starts_task = True
        t.has_signal = t.completed_steps > 0 or t.wrap_up
        if not tasks:
            t.starts_task = True
        if t.starts_task:
            tasks.append(Task(session=session.id))
        t.task = len(tasks) - 1
        tasks[-1].turns.append(t)
        if t.has_signal:
            tasks[-1].done_at = len(tasks[-1].turns) - 1
        turns.append(t)
    nxt = None
    for i in range(len(turns) - 1, -1, -1):
        if turns[i].has_signal:
            nxt = i
        turns[i].turns_to_signal = None if nxt is None else nxt - i + 1
    starts = [i for i, t in enumerate(turns) if t.starts_request or i == 0] + [len(turns)]
    for a, b in zip(starts, starts[1:]):
        sig = [i for i in range(a, b) if turns[i].has_signal]
        turns[a].request_turns_to_done = sig[-1] - a + 1 if sig else None
    return turns, tasks, plan.undone()


def session_stats(session: Session, tasks: list[Task], undone: int) -> SessionStats:
    ts = session.timestamps
    first = session.prompts[0].ts.astimezone() if session.prompts else ts[0].astimezone()
    return SessionStats(
        id=session.id, prompts=len(session.prompts), active_min=active_seconds(ts) / 60,
        length_min=(ts[-1] - ts[0]).total_seconds() / 60 if ts else 0.0, start_hour=first.hour,
        tasks=len(tasks), tasks_done=sum(t.done for t in tasks), steps_left_undone=undone,
        used_task_list=any(p.plan_ops for p in session.prompts))


def analyze(sessions: list[Session]):
    """(turns, tasks, session stats) for every session with at least one prompt."""
    all_turns, all_tasks, stats = [], [], []
    for s in sessions:
        if not s.prompts:
            continue
        turns, tasks, undone = build_tasks(s)
        all_turns += turns
        all_tasks += tasks
        stats.append(session_stats(s, tasks, undone))
    return all_turns, all_tasks, stats


def _med(xs):
    return round(st.median(xs), 1) if xs else None


def task_summary(tasks: list[Task], stats: list[SessionStats], turns: list[Turn]) -> dict:
    tracked = [t for t in tasks if any(x.prompt.plan_ops for x in t.turns)]
    done = [t for t in tracked if t.done]
    return {
        "sessions_with_prompts": len(stats),
        "sessions_using_task_lists": sum(s.used_task_list for s in stats),
        "tasks": len(tasks),
        "tasks_with_task_list": len(tracked),
        "tasks_done": len(done),
        "completion_rate": round(len(done) / len(tracked), 3) if tracked else None,
        "turns_to_done_median": _med([t.turns_to_done for t in done]),
        "turns_to_done_mean": round(st.mean([t.turns_to_done for t in done]), 2) if done else None,
        "requests": sum(1 for t in turns if t.starts_request or t.prompt.idx == 0),
        "requests_done": sum(1 for t in turns if t.request_turns_to_done),
        "request_turns_to_done_median": _med([t.request_turns_to_done for t in turns if t.request_turns_to_done]),
        "turns_with_completion_signal": sum(t.has_signal for t in turns),
        "corrections_per_task_mean": round(st.mean([t.corrections for t in tracked]), 2) if tracked else None,
        "tool_errors_per_task_mean": round(st.mean([t.tool_errors for t in tracked]), 2) if tracked else None,
        "correction_prompts": sum(is_correction(t.prompt.text) for t in turns),
        "interrupted_turns": sum(t.prompt.interrupted for t in turns),
        "session_active_min_median": _med([s.active_min for s in stats]),
        "session_active_min_max": round(max(s.active_min for s in stats), 1) if stats else None,
        "session_length_min_median": _med([s.length_min for s in stats]),
        "total_active_hours": round(sum(s.active_min for s in stats) / 60, 1),
        "steps_left_undone_total": sum(s.steps_left_undone for s in stats),
        "sessions_ending_with_undone_steps": sum(1 for s in stats if s.steps_left_undone),
        "sessions_by_start_hour": {str(h): sum(1 for s in stats if s.start_hour == h)
                                   for h in sorted({s.start_hour for s in stats})},
    }


def main() -> None:
    turns, tasks, stats = analyze(load_sessions())
    for k, v in task_summary(tasks, stats, turns).items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
