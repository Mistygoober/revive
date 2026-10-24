"""body/polar.py (nbz): Polar H10 heart-rate + RR reader over BLE.

Scans for a device whose name starts "Polar H10", subscribes to the standard
Heart Rate service (0x180D) / Heart Rate Measurement characteristic (0x2A37),
parses HR and RR intervals, and every 5 s appends a 'body' event whose RMSSD
and strain are computed over a rolling 60 s window of recent RR, using
body/rmssd.py.

Run:
    uv run python -m body.polar                        # live H10
    uv run python -m body.polar --record fixtures/squats_rr.jsonl
    uv run python -m body.polar --no-filter            # hero bug: raw RR, no cleaner
    DEMO_MODE=1 uv run python -m body.polar            # replay the fixture, no BT

Signatures matched: shared.events.append_event / now_iso, body.rmssd.rmssd /
classify_strain. bleak is imported lazily so importing this module (and
get_body_state) never requires Bluetooth.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from body.rmssd import classify_strain, rmssd
from shared.config import ROOT
from shared.events import append_event, now_iso

HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"  # 0x2A37
DEVICE_NAME_PREFIX = "Polar H10"
WINDOW_S = 60          # rolling window for RMSSD
EMIT_EVERY_S = 5       # body-event cadence
STALE_AFTER_S = 15     # get_body_state() falls back to fake past this age
HR_BASE = 68           # TODO: load from the 30-day Garmin table (data-private)
RMSSD_BASE = 41.0
RR_SCALE_MS = 1000.0 / 1024.0  # Polar RR units are 1/1024 s
DEFAULT_FIXTURE = ROOT / "fixtures" / "squats_rr.jsonl"


# --- packet parsing -------------------------------------------------------

def parse_hr_measurement(data: bytes) -> tuple[int | None, list[float]]:
    """Parse one Heart Rate Measurement packet -> (hr_bpm, [rr_ms, ...]).

    Flags (byte 0): bit0 = 16-bit HR if set else 8-bit; bit3 = energy expended
    present (skip 2 bytes); bit4 = RR intervals present (uint16 LE, 1/1024 s).
    Returns (None, []) on a short/garbled packet; never raises.
    """
    try:
        if not data:
            return None, []
        flags = data[0]
        i = 1
        if flags & 0x01:  # 16-bit HR
            if len(data) < i + 2:
                return None, []
            hr = int.from_bytes(data[i:i + 2], "little")
            i += 2
        else:             # 8-bit HR
            if len(data) < i + 1:
                return None, []
            hr = data[i]
            i += 1
        if flags & 0x08:  # energy expended present
            i += 2
        rr: list[float] = []
        if flags & 0x10:  # RR intervals present
            while i + 2 <= len(data):
                raw = int.from_bytes(data[i:i + 2], "little")
                i += 2
                rr.append(raw * RR_SCALE_MS)
        return hr, rr
    except Exception:
        return None, []


# --- rolling buffer -------------------------------------------------------

class RRBuffer:
    """Recent (monotonic_ts, rr_ms) beats plus the latest HR."""

    def __init__(self) -> None:
        self.beats: list[tuple[float, float]] = []
        self.hr: int | None = None

    def add(self, hr: int | None, rr_list: list[float]) -> None:
        if hr is not None:
            self.hr = hr
        now = time.monotonic()
        for rr in rr_list:
            self.beats.append((now, rr))

    def recent_rr(self, window_s: float = WINDOW_S) -> list[float]:
        cutoff = time.monotonic() - window_s
        self.beats = [(t, rr) for t, rr in self.beats if t >= cutoff]
        return [rr for _, rr in self.beats]


def emit_body_event(buf: RRBuffer, *, no_filter: bool, source: str) -> dict:
    """Compute RMSSD + strain over the rolling window and log a body event.

    no_filter=True skips the RR cleaner (already_clean=True) -> the hero bug:
    motion artifacts are left in and RMSSD explodes.
    """
    rr_list = buf.recent_rr()
    val = rmssd(rr_list, already_clean=no_filter)
    strain = classify_strain(buf.hr, val, HR_BASE, RMSSD_BASE)
    return append_event(
        "body",
        hr=buf.hr,
        rmssd=val,
        strain=strain,
        hr_base=HR_BASE,
        rmssd_base=RMSSD_BASE,
        source=source,
    )


# --- live reader ----------------------------------------------------------

async def run_live(record_path: str | None = None, no_filter: bool = False) -> None:
    from bleak import BleakClient, BleakScanner  # lazy: only live mode needs BT

    record_fh = open(record_path, "a", encoding="utf-8") if record_path else None
    backoff = 1.0
    try:
        while True:
            try:
                print("scanning for Polar H10...")
                devices = await BleakScanner.discover(timeout=8.0)
                device = next(
                    (d for d in devices if (d.name or "").startswith(DEVICE_NAME_PREFIX)),
                    None,
                )
                if device is None:
                    print(f"not found; retry in {backoff:.0f}s")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    continue

                buf = RRBuffer()

                def handler(_char, data: bytearray) -> None:
                    hr, rr = parse_hr_measurement(bytes(data))  # never raises
                    if hr is None and not rr:
                        return
                    buf.add(hr, rr)
                    if record_fh and rr:
                        record_fh.write(json.dumps({"ts": now_iso(), "hr": hr, "rr": rr}) + "\n")
                        record_fh.flush()

                async with BleakClient(device) as client:
                    print(f"connected: {device.name}")
                    backoff = 1.0
                    await client.start_notify(HR_MEASUREMENT_UUID, handler)
                    while client.is_connected:
                        await asyncio.sleep(EMIT_EVERY_S)
                        ev = emit_body_event(buf, no_filter=no_filter, source="h10")
                        print(f"hr={ev['hr']} rmssd={ev['rmssd']} strain={ev['strain']}")
                print("strap dropped; reconnecting")
            except Exception as e:  # never let the loop die
                print(f"connection error: {e!r}; retry in {backoff:.0f}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
    finally:
        if record_fh:
            record_fh.close()


# --- replay (DEMO_MODE=1) -------------------------------------------------

async def run_replay(fixture: str | Path = DEFAULT_FIXTURE, no_filter: bool = False) -> None:
    path = Path(fixture)
    if not path.exists():
        print(f"DEMO_MODE: fixture {path} not found; record one with --record first")
        return
    records = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not records:
        print(f"DEMO_MODE: fixture {path} is empty")
        return
    print(f"DEMO_MODE: replaying {len(records)} records from {path.name} (loops)")
    buf = RRBuffer()
    last_emit = time.monotonic()
    while True:  # loop the trace so the demo keeps running
        for rec in records:
            buf.add(rec.get("hr"), rec.get("rr", []))
            # pace to real time: the beats represent sum(rr) ms of elapsed time
            dur_s = sum(rec.get("rr", [])) / 1000.0 or 1.0
            await asyncio.sleep(min(dur_s, EMIT_EVERY_S))
            if time.monotonic() - last_emit >= EMIT_EVERY_S:
                ev = emit_body_event(buf, no_filter=no_filter, source="replay")
                print(f"[replay] hr={ev['hr']} rmssd={ev['rmssd']} strain={ev['strain']}")
                last_emit = time.monotonic()


# --- entry point ----------------------------------------------------------

def main() -> None:
    from shared.config import DEMO_MODE  # read at call time, not import time

    parser = argparse.ArgumentParser(description="Polar H10 reader / replayer")
    parser.add_argument("--record", metavar="PATH", help="save raw RR with timestamps")
    parser.add_argument("--no-filter", action="store_true", help="skip the RR cleaner (hero bug)")
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE), help="replay source for DEMO_MODE")
    args = parser.parse_args()

    try:
        if DEMO_MODE:
            asyncio.run(run_replay(args.fixture, no_filter=args.no_filter))
        else:
            asyncio.run(run_live(args.record, no_filter=args.no_filter))
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
