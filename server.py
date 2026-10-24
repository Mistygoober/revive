"""Revive server: body state, the event log, and the judge view.

Run: uv run uvicorn server:app --host 0.0.0.0 --port 8000
"""
import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from body.state import get_body_state
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


@app.get("/stream")
async def stream():
    """Server-sent events: every new line of data/events.jsonl, as it's written."""
    async def gen():
        pos = EVENTS_PATH.stat().st_size if EVENTS_PATH.exists() else 0
        while True:
            if EVENTS_PATH.exists() and EVENTS_PATH.stat().st_size > pos:
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
