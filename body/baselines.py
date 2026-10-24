"""body/baselines.py: nbz's personal baselines + "today" from daily Garmin exports.

Reads the unzipped daily exports in ../data-private/nbz/garmin/<date>/*.fit
(raw data, never in the repo) and writes body/baselines_nbz.json (aggregates
only). Stdlib-only FIT reader, so no new dependency.

    uv run python -I body/baselines.py [--inspect] [garmin_dir]
"""
import json
import statistics
import struct
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DIR = HERE.parent.parent / "data-private" / "nbz" / "garmin"
OUT = HERE / "baselines_nbz.json"
FIT_EPOCH = 631065600  # 1989-12-31T00:00:00Z

# base type -> (struct code, size, invalid value)
_BASE = {
    0x00: ("B", 1, 0xFF), 0x01: ("b", 1, 0x7F), 0x02: ("B", 1, 0xFF),
    0x83: ("h", 2, 0x7FFF), 0x84: ("H", 2, 0xFFFF), 0x85: ("i", 4, 0x7FFFFFFF),
    0x86: ("I", 4, 0xFFFFFFFF), 0x88: ("f", 4, None), 0x89: ("d", 8, None),
    0x0A: ("B", 1, 0), 0x8B: ("H", 2, 0), 0x8C: ("I", 4, 0), 0x0D: ("B", 1, 0xFF),
    0x8E: ("q", 8, 0x7FFFFFFFFFFFFFFF), 0x8F: ("Q", 8, 0xFFFFFFFFFFFFFFFF),
    0x90: ("Q", 8, 0),
}


def read_fit(path: Path) -> list[tuple[int, dict]]:
    """Return [(global_msg_num, {field_num: value})]. Invalid values are dropped;
    field 253 (timestamp) is made absolute, including compressed timestamps."""
    data = path.read_bytes()
    out: list[tuple[int, dict]] = []
    pos = 0
    while pos + 12 <= len(data):
        hsize = data[pos]
        if data[pos + 8:pos + 12] != b".FIT":
            break
        size = struct.unpack_from("<I", data, pos + 4)[0]
        p, end = pos + hsize, pos + hsize + size
        defs: dict[int, tuple] = {}
        last_ts = 0
        while p < end:
            h = data[p]; p += 1
            if h & 0x80:  # compressed timestamp header
                local, offset = (h >> 5) & 0x03, h & 0x1F
                ts = (last_ts & ~0x1F) + offset
                if offset < (last_ts & 0x1F):
                    ts += 0x20
                last_ts = ts
                compressed = ts
            else:
                local, compressed = h & 0x0F, None
                if h & 0x40:  # definition message
                    arch = data[p + 1]
                    endian = ">" if arch == 1 else "<"
                    gnum = struct.unpack_from(endian + "H", data, p + 2)[0]
                    nf = data[p + 4]; p += 5
                    fields = [tuple(data[p + 3 * i:p + 3 * i + 3]) for i in range(nf)]
                    p += 3 * nf
                    dev = 0
                    if h & 0x20:
                        nd = data[p]; p += 1
                        dev = sum(data[p + 3 * i + 1] for i in range(nd))
                        p += 3 * nd
                    defs[local] = (endian, gnum, fields, dev)
                    continue
            endian, gnum, fields, dev = defs[local]
            msg = {}
            for fnum, fsize, btype in fields:
                raw = data[p:p + fsize]; p += fsize
                bt = _BASE.get(btype)
                if bt is None or fsize != bt[1]:
                    continue  # arrays/strings: not needed here
                val = struct.unpack(endian + bt[0], raw)[0]
                if val == bt[2]:
                    continue
                msg[fnum] = val
            p += dev
            if 253 in msg:
                last_ts = msg[253]
            elif compressed is not None:
                msg[253] = compressed
            out.append((gnum, msg))
        pos = end + 2  # skip CRC; files may be chained
    return out


def _ts(v: int) -> datetime:
    return datetime.fromtimestamp(v + FIT_EPOCH, tz=timezone.utc)


def inspect(root: Path) -> None:
    """Print message/field coverage only (counts and ranges, no records)."""
    stats: dict[tuple, list] = defaultdict(list)
    msgs = Counter()
    for f in sorted(root.glob("*/*.fit")):
        kind = f.stem.split("_", 1)[-1]
        for gnum, m in read_fit(f):
            msgs[(kind, gnum)] += 1
            for k, v in m.items():
                if k != 253:
                    stats[(kind, gnum, k)].append(v)
    for (kind, gnum), n in sorted(msgs.items()):
        print(f"{kind} msg {gnum}: {n}")
        for (k2, g2, fnum), vals in sorted(stats.items()):
            if (k2, g2) == (kind, gnum):
                print(f"    f{fnum}: n={len(vals)} range {min(vals)}..{max(vals)}")


MIN_SAMPLES = 60  # a day needs >= 60 stress / Body Battery samples (~1 h) to count


def daily(root: Path) -> dict[str, dict]:
    """Per local day: resting HR, mean stress, Body Battery high/low.

    Fields found in nbz's exports (reverse-engineered, checked by time-of-day shape):
      msg 211 f1   current-day resting heart rate (bpm)
      msg 227 f0   stress level 0-100 (negative = off-wrist / too much motion)
      msg 227 f1   sample time; msg 227 f3 Body Battery (rises overnight, drains by day)
      msg 103      local_timestamp - timestamp = UTC offset
    No sleep (sleep_level / sleep_assessment) or overnight HRV (hrv_status) messages
    exist in these exports, so those stay null.
    """
    rhr: dict[str, int] = {}
    stress: dict[str, list] = defaultdict(list)
    bb: dict[str, list] = defaultdict(list)
    for f in sorted(root.glob("*/*.fit")):
        recs = read_fit(f)
        off = next((m[0] - m[253] for g, m in recs if g == 103 and 0 in m and 253 in m), 0)
        day = lambda t: _ts(t + off).date().isoformat()  # noqa: E731
        for g, m in sorted(recs, key=lambda r: r[1].get(253, r[1].get(1, 0))):
            if g == 211 and 1 in m and 253 in m:
                rhr[day(m[253])] = m[1]  # last value of the day wins
            elif g == 227 and 1 in m:
                d = day(m[1])
                if 0 in m and 0 <= m[0] <= 100:
                    stress[d].append(m[0])
                if 3 in m and 0 < m[3] <= 100:
                    bb[d].append(m[3])
    days = sorted(set(rhr) | set(stress) | set(bb))
    out = {}
    for d in days:
        s, b = stress.get(d, []), bb.get(d, [])
        out[d] = {
            "resting_hr": rhr.get(d),
            "stress": round(statistics.mean(s)) if len(s) >= MIN_SAMPLES else None,
            "bb_high": max(b) if len(b) >= MIN_SAMPLES else None,
            "bb_low": min(b) if len(b) >= MIN_SAMPLES else None,
        }
    return out


def _median(days: dict, key: str) -> tuple[float | None, int]:
    vals = [v[key] for v in days.values() if v[key] is not None]
    return (round(statistics.median(vals), 1) if vals else None), len(vals)


def compute(root: Path) -> dict:
    days = daily(root)
    used = {d: v for d, v in days.items() if any(x is not None for x in v.values())}
    last_day = max(d for d, v in used.items() if v["bb_high"] is not None or v["stress"] is not None)
    last = used[last_day]
    rhr, n_rhr = _median(used, "resting_hr")
    st, n_st = _median(used, "stress")
    bbh, n_bbh = _median(used, "bb_high")
    bbl, n_bbl = _median(used, "bb_low")
    return {
        "who": "nbz",
        "source": "garmin daily exports (FIT), aggregates only",
        "date_range": [min(used), max(used)],
        "n_days": len(used),
        "baseline": {
            "resting_hr": rhr, "n_resting_hr": n_rhr,
            "stress": st, "n_stress": n_st,
            "bb_high": bbh, "n_bb_high": n_bbh,
            "bb_low": bbl, "n_bb_low": n_bbl,
            "overnight_hrv": None, "n_overnight_hrv": 0,
            "sleep_h": None, "n_sleep_h": 0,
        },
        "last_day": {
            "date": last_day,
            "sleep_h": None, "sleep_score": None,
            "body_battery": last["bb_high"], "body_battery_low": last["bb_low"],
            "stress": last["stress"], "resting_hr": last["resting_hr"],
        },
        "missing": ["sleep (no sleep messages in exports)",
                    "overnight HRV (no hrv_status messages in exports)"],
    }


def coverage(root: Path) -> None:
    days = daily(root)
    print(f"days with any data: {len(days)}")
    for k in ("resting_hr", "stress", "bb_high", "bb_low"):
        print(f"  {k}: {sum(v[k] is not None for v in days.values())} days")
    print("  sleep_h: 0 days, sleep_score: 0 days, overnight_hrv: 0 days")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = Path(args[0]) if args else DEFAULT_DIR
    if "--inspect" in sys.argv:
        inspect(root)
    elif "--coverage" in sys.argv:
        coverage(root)
    else:
        result = compute(root)
        OUT.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
