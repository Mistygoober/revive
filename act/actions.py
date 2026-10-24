"""tap() and say(): the two interventions. Return fast, never throw.

- tap -> HTTP POST to ntfy.sh/<NTFY_TOPIC>; the phone/Garmin buzzes.
- say -> macOS `say`; one spoken sentence.
The network call and the subprocess each run on a daemon thread, so the
caller gets control back in well under a second no matter the network or OS.
Every call is logged to the shared event log as kind "action".
"""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
import urllib.request

from shared.events import append_event

NTFY_BASE = os.getenv("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
_HTTP_TIMEOUT_S = 3  # the POST runs off-thread, so this never blocks the caller


def _truncate_words(text: str, limit: int) -> str:
    words = text.split()
    return " ".join(words[:limit]) if len(words) > limit else text


def _first_sentence(text: str) -> str:
    text = text.strip()
    for end in (". ", "! ", "? "):
        i = text.find(end)
        if i != -1:
            return text[: i + 1].strip()
    return text


def _post_ntfy(topic: str, message: str) -> None:
    """Fire-and-forget POST. Swallows every error; this is best-effort."""
    try:
        req = urllib.request.Request(
            f"{NTFY_BASE}/{topic}",
            data=message.encode("utf-8"),
            headers={"Title": "Revive", "Priority": "high", "Tags": "vibration_mode"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S).close()
    except Exception:
        pass


def _speak(message: str) -> None:
    """Speak via macOS `say`. No-op (swallowed) where `say` is absent."""
    try:
        if shutil.which("say"):
            subprocess.run(["say", message], timeout=15, check=False)
    except Exception:
        pass


def tap(text: str, *, send: bool = True) -> dict:
    """Buzz the user's wrist with a <=5-word nudge. Returns the logged event."""
    text = _truncate_words((text or "").strip(), 5)
    topic = os.getenv("NTFY_TOPIC", "").strip()
    will_send = bool(send and topic)
    if will_send:
        threading.Thread(target=_post_ntfy, args=(topic, text), daemon=True).start()
    try:
        return append_event("action", medium="tap", text=text, sent=will_send)
    except Exception:
        return {"kind": "action", "medium": "tap", "text": text, "sent": will_send}


def say(text: str, *, speak: bool = True) -> dict:
    """Speak one sentence through the Mac. Returns the logged event."""
    text = _first_sentence(text or "")
    if speak and text:
        threading.Thread(target=_speak, args=(text,), daemon=True).start()
    try:
        return append_event("action", medium="say", text=text, sent=bool(speak and text))
    except Exception:
        return {"kind": "action", "medium": "say", "text": text, "sent": bool(speak and text)}
