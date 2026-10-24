"""Paths and settings shared by every part of Revive."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"                # git-ignored: live logs
EVENTS_PATH = DATA_DIR / "events.jsonl"  # the shared event log (no prompt text)
RAW_DIR = ROOT / "memory" / "raw"        # git-ignored: raw facts, never altered
INSIGHTS_DIR = ROOT / "memory" / "insights"  # generated, labeled

WHO = os.getenv("REVIVE_WHO", "lucas")   # set REVIVE_WHO=nbz on Noam's laptop
DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"
