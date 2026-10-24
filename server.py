"""Revive server: body state, the event log, the judge view, and the fast hook path.

Run: uv run uvicorn server:app --host 0.0.0.0 --port 8000
"""
import asyncio
import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Body, FastAPI
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from body.state import get_body_state
from capture import hook as capture_hook
from shared.config import EVENTS_PATH
from shared.events import read_events

app = FastAPI(title="Revive")
WEB = Path(__file__).parent / "web"


@app.get("/")
def root():
    return RedirectResponse("/web/judge/")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/body")
def body():
    return get_body_state()


@app.get("/events")
def events(last: int = 200):
    return read_events(last)


_hook_lock = threading.Lock()


@contextmanager
def _hook_env(env: dict):
    """Apply the hook process's FAKE_STRAIN / REVIVE_TAP / ... for one call, then restore."""
    env = {k: str(v) for k, v in (env or {}).items() if k in capture_hook.FORWARD_ENV}
    with _hook_lock:
        old = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        try:
            yield
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def _score_outcome(data: dict, env: dict) -> None:
    with _hook_env(env):
        capture_hook.score_outcome(data)


@app.on_event("startup")
def _warm():
    """Import the grader and open the Anthropic connection now, not on the first prompt."""
    def run():
        try:
            from grader import _llm
            _llm._get_client().messages.count_tokens(model=_llm.MODEL, messages=[{"role": "user", "content": "hi"}])
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


@app.post("/hook")
def hook(background: BackgroundTasks, payload: dict = Body(...)):
    """What capture/hook.py does, in this warm process. Same events, same additionalContext.
    The Stop hook's outcome score runs after the response, so Claude Code isn't kept waiting."""
    data, env = payload.get("data") or {}, payload.get("env") or {}
    out = None
    try:
        with _hook_env(env):
            out = capture_hook.handle(data, outcome=False)
        if data.get("hook_event_name") == "Stop":
            background.add_task(_score_outcome, data, env)
    except Exception:
        capture_hook._log_error("server /hook")
    return {"output": out}


@app.get("/stream")
async def stream():
    """Server-sent events: every new line of data/events.jsonl, as it's written."""
    async def gen():
        pos = EVENTS_PATH.stat().st_size if EVENTS_PATH.exists() else 0
        while True:
            size = EVENTS_PATH.stat().st_size if EVENTS_PATH.exists() else 0
            if size < pos:  # file was trimmed (demo_check cleanup): carry on from the new end
                pos = size
            if size > pos:
                with EVENTS_PATH.open("r", encoding="utf-8") as f:
                    f.seek(pos)
                    chunk = f.read()
                    pos = f.tell()
                for line in chunk.splitlines():
                    if line.strip():
                        yield f"data: {line}\n\n"
            else:
                yield ": keepalive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(gen(), media_type="text/event-stream")


app.mount("/web", StaticFiles(directory=WEB, html=True), name="web")
