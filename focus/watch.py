"""Watch the frontmost app during a work block; tap on a rabbit hole or a long stretch without a break.

Run:  uv run python -m focus.watch --minutes 45 [--demo]

Every 5 s: frontmost app (AppKit) and, for a browser, the active tab's domain (osascript).
Writes a `focus` event every 30 s or on change: {app, site, distracted, block_left_min}.

Distraction rule: a listed site/app in front continuously for 90 s during a block
  -> tap("Back to task, 32m left") + action {level 1, channels ["focus","tap"]}. Cooldown 5 min.
Break rule: active for 90 min with no 10 min gap (prompt/reply events + this watcher's own
  activity) -> tap("Take 5, 90 min straight") + action {channels ["break","tap"]}. Cooldown 30 min.
--demo: 20 s / 2 min thresholds (break counts only this run's activity, gap 1 min);
  every event carries demo_thresholds: true.

Tap texts use commas, not "·": act.tap keeps 5 words and counts "·" as one.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable
from urllib.parse import urlsplit

from shared.config import WHO
from shared.events import append_event, read_events

TICK_S = 5
EMIT_EVERY_S = 30
IDLE_S = 60  # no keyboard/mouse for this long = idle tick

DISTRACTING_SITES = ("youtube.com", "youtu.be", "x.com", "twitter.com", "instagram.com",
                     "reddit.com", "tiktok.com", "netflix.com", "facebook.com")
DISTRACTING_APPS = {"youtube", "x", "twitter", "instagram", "reddit", "tiktok", "netflix", "facebook"}

# osascript per browser; each returns the active tab's URL, which never leaves domain_of()
BROWSERS = {
    "Google Chrome": 'tell application "Google Chrome" to get URL of active tab of front window',
    "Brave Browser": 'tell application "Brave Browser" to get URL of active tab of front window',
    "Arc": 'tell application "Arc" to get URL of active tab of front window',
    "Safari": 'tell application "Safari" to get URL of front document',
}


@dataclass(frozen=True)
class Rules:
    distract_s: float = 90
    distract_cooldown_s: float = 5 * 60
    break_s: float = 90 * 60
    break_gap_s: float = 10 * 60
    break_cooldown_s: float = 30 * 60
    demo: bool = False


DEMO_RULES = Rules(distract_s=20, break_s=2 * 60, break_gap_s=60, demo=True)


# ---------- privacy: domain only ----------
def domain_of(url: str | None) -> str | None:
    """'https://www.youtube.com/watch?v=x#t' -> 'youtube.com'. No path, query, fragment or user."""
    if not url:
        return None
    try:
        parts = urlsplit(url.strip())
        if parts.scheme not in ("http", "https"):
            return None
        host = (parts.hostname or "").lower().rstrip(".")
    except ValueError:
        return None
    if not re.fullmatch(r"[a-z0-9.-]+", host or "-"):
        return None
    for prefix in ("www.", "m.", "mobile."):
        if host.startswith(prefix):
            host = host[len(prefix):]
    return host or None


def is_distracting(app: str | None, site: str | None) -> bool:
    if site and any(site == d or site.endswith("." + d) for d in DISTRACTING_SITES):
        return True
    return bool(app) and app.strip().lower() in DISTRACTING_APPS


# ---------- macOS probes (replaced by fakes in tests) ----------
_denied: set[str] = set()  # browsers whose Automation permission was refused: app name only


def frontmost_app() -> str | None:
    try:
        from AppKit import NSWorkspace
        from Foundation import NSDate, NSRunLoop
        # without a spin of the run loop, frontmostApplication() never updates in a plain script
        NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.05))
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        return str(app.localizedName()) if app else None
    except Exception:
        return None


def browser_domain(app: str) -> str | None:
    script = BROWSERS.get(app)
    if not script or app in _denied:
        return None
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
    except Exception:
        return None
    if r.returncode != 0:
        # -1743: not authorized to send Apple events. Keep working with app names only.
        if "-1743" in r.stderr or "not allowed" in r.stderr.lower():
            _denied.add(app)
            print(f"focus: no Automation permission for {app}; using the app name only")
        return None
    return domain_of(r.stdout)


def probe() -> tuple[str | None, str | None]:
    app = frontmost_app()
    return app, browser_domain(app) if app in BROWSERS else None


def idle_seconds() -> float:
    """Seconds since the last keyboard/mouse input (IOHIDSystem). 0 if unknown."""
    try:
        out = subprocess.run(["ioreg", "-c", "IOHIDSystem", "-d", "4"], capture_output=True,
                             text=True, timeout=2).stdout
        m = re.search(r'"HIDIdleTime" = (\d+)', out)
        return int(m.group(1)) / 1e9 if m else 0.0
    except Exception:
        return 0.0


def logged_activity() -> list[float]:
    """Times of this person's prompt/reply events from the shared log."""
    out = []
    for e in read_events(last=3000):
        if e.get("kind") in ("prompt", "reply") and e.get("who", WHO) == WHO:
            try:
                out.append(datetime.fromisoformat(e["ts"]).timestamp())
            except (KeyError, TypeError, ValueError):
                continue
    return out


def send_tap(text: str) -> dict:
    from act import tap
    return tap(text, send=os.getenv("REVIVE_TAP", "1") == "1")


# ---------- the watcher ----------
def streak_start(times: list[float], now: float, gap_s: float) -> float | None:
    """Start of the current unbroken run of activity, or None if the last activity is gap_s old."""
    ts = sorted(t for t in times if t <= now)
    if not ts or now - ts[-1] >= gap_s:
        return None
    start = ts[-1]
    for prev in reversed(ts[:-1]):
        if start - prev >= gap_s:
            break
        start = prev
    return start


class Watcher:
    def __init__(self, *, minutes: float | None, rules: Rules = Rules(),
                 clock: Callable[[], float] = time.time,
                 probe: Callable[[], tuple[str | None, str | None]] = probe,
                 idle: Callable[[], float] = idle_seconds,
                 tap: Callable[[str], dict] = send_tap,
                 activity_log: Callable[[], list[float]] = logged_activity,
                 emit: Callable[..., dict] = append_event):
        self.rules, self.clock, self.probe, self.idle = rules, clock, probe, idle
        self.tap, self.activity_log, self.emit = tap, activity_log, emit
        self.started = clock()
        self.block_end = self.started + minutes * 60 if minutes else None
        self.last_state: tuple | None = None
        self.last_emit = -math.inf
        self.distract_key: str | None = None
        self.distract_since: float | None = None
        self.last_focus_tap = -math.inf
        self.last_break_tap = -math.inf
        self.active: list[float] = []

    def _extra(self) -> dict:
        return {"demo_thresholds": True} if self.rules.demo else {}

    def block_left_min(self, now: float) -> int | None:
        if self.block_end is None or now >= self.block_end:
            return None
        return math.ceil((self.block_end - now) / 60)

    def tick(self) -> list[dict]:
        """One 5 s step. Returns the events written this tick."""
        now = self.clock()
        app, site = self.probe()
        distracted = is_distracting(app, site)
        left = self.block_left_min(now)
        written = []

        key = (site or app) if distracted else None
        if key != self.distract_key:
            self.distract_key, self.distract_since = key, (now if key else None)

        state = (app, site, distracted)
        if state != self.last_state or now - self.last_emit >= EMIT_EVERY_S:
            written.append(self.emit("focus", app=app, site=site, distracted=distracted,
                                     block_left_min=left, **self._extra()))
            self.last_state, self.last_emit = state, now

        if self.idle() < IDLE_S:
            self.active.append(now)
            self.active = [t for t in self.active if now - t < 4 * 3600]

        written += self._distraction(now, left)
        written += self._break(now)
        return written

    def _distraction(self, now: float, left: int | None) -> list[dict]:
        r = self.rules
        if left is None or self.distract_since is None:  # no block running: never nudge
            return []
        if now - self.distract_since < r.distract_s or now - self.last_focus_tap < r.distract_cooldown_s:
            return []
        self.last_focus_tap = now
        sent = self.tap(f"Back to task, {left}m left")
        return [self.emit("action", level=1, channels=["focus", "tap"],
                          message=sent.get("text") or f"Back to task, {left}m left",
                          reason=f"distracted {int(r.distract_s)} s on {self.distract_key}",
                          **self._extra())]

    def _break(self, now: float) -> list[dict]:
        r = self.rules
        if now - self.last_break_tap < r.break_cooldown_s:
            return []
        times = self.active + [t for t in self.activity_log() if t >= self.started or not r.demo]
        start = streak_start(times, now, r.break_gap_s)
        if start is None or now - start < r.break_s:
            return []
        self.last_break_tap = now
        mins = int((now - start) // 60)
        sent = self.tap(f"Take 5, {mins} min straight")
        return [self.emit("action", level=1, channels=["break", "tap"],
                          message=sent.get("text") or f"Take 5, {mins} min straight",
                          reason=f"active {mins} min with no {int(r.break_gap_s // 60)} min break",
                          **self._extra())]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Revive focus watcher")
    ap.add_argument("--minutes", type=float, default=None, help="length of the work block")
    ap.add_argument("--demo", action="store_true", help="20 s / 2 min thresholds, tagged demo_thresholds")
    args = ap.parse_args(argv)
    w = Watcher(minutes=args.minutes, rules=DEMO_RULES if args.demo else Rules())
    print(f"focus: watching{f' a {args.minutes:g} min block' if args.minutes else ' (no block: no distraction nudges)'}"
          f"{' with demo timing' if args.demo else ''}. Ctrl-C to stop.")
    try:
        while True:
            for e in w.tick():
                if e.get("kind") == "action":
                    print(f"focus: {e['message']} ({e['reason']})")
                else:
                    print(f"focus: {e.get('app')} · {e.get('site') or '-'}"
                          f"{' · DISTRACTED' if e.get('distracted') else ''}")
            if w.block_end and w.clock() >= w.block_end:
                print("focus: block over")
                return
            time.sleep(TICK_S)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
