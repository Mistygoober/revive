"""Minimal tap until nbz's act/ lands. Never throws, returns within ~1 s."""
import os

import httpx


def tap(text: str) -> bool:
    topic = os.getenv("NTFY_TOPIC")
    if not topic:
        return False
    try:
        httpx.post(f"https://ntfy.sh/{topic}", content=text.encode(), headers={"Priority": "5", "Title": "Revive"}, timeout=1.5)
        return True
    except Exception:
        return False
