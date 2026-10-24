"""Interventions owned by nbz: the only ways Revive reaches the user.

tap(text): a wrist buzz on the Garmin via an ntfy push (<= 5 words).
say(text): one spoken sentence through the Mac's voice.

Both return within 1 s and never throw. The real side effect (network or
subprocess) runs on a daemon thread so a slow phone or no network can never
stall the demo. Only the user's own devices are ever contacted (CLAUDE.md).
"""
from act.actions import say, tap

__all__ = ["tap", "say"]
