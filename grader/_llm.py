"""One forced-tool Haiku call with a hard wall-clock timeout. Raises on any failure; callers fall back."""
import os
import time
from concurrent.futures import ThreadPoolExecutor

import shared.config  # noqa: F401  (loads .env)

MODEL = "claude-haiku-5-5"
TIMEOUT_S = 5.0  # hotspot latency: 3 s fell back to the heuristic in Test 2

_pool = ThreadPoolExecutor(max_workers=4)
_client = None


def _get_client():
    global _client
    key = os.getenv("REVIVE_ANTHROPIC_KEY")
    if not key:
        raise RuntimeError("no_key")
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=key, timeout=TIMEOUT_S, max_retries=0)
    return _client


def call_tool(system: str, user: str, tool: dict, timeout: float | None = None) -> tuple[dict, int]:
    """Force Haiku to answer through `tool`; return (tool input, latency_ms)."""
    client = _get_client()
    t0 = time.monotonic()

    def run():
        return client.messages.create(
            model=MODEL,
            max_tokens=600,  # no temperature: SDK 2.x dropped sampling params; the forced tool keeps output stable
            system=system,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": user}],
        )

    msg = _pool.submit(run).result(timeout=timeout or TIMEOUT_S)  # TimeoutError if slower
    latency_ms = int((time.monotonic() - t0) * 1000)
    for block in msg.content:
        if block.type == "tool_use":
            return dict(block.input), latency_ms
    raise RuntimeError("no_tool_use")
