"""Save what users type into the app, one file per kind of input.

Files (JSON Lines, one record per line) are written to data/logs/:
  eligibility.jsonl, questions.jsonl, links.jsonl

Privacy rules built in: no IP address or name is stored, and anything that looks like a
CNIC (13 digits, with or without dashes) or a phone number is replaced before saving.
Set LOG_INPUTS=0 to turn saving off.
"""
import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(os.getenv("LOG_DIR", Path(__file__).parent / "data" / "logs"))
ENABLED = os.getenv("LOG_INPUTS", "1") == "1"
_lock = threading.Lock()

_CNIC = re.compile(r"\b\d{5}-?\d{7}-?\d\b")
_PHONE = re.compile(r"(?<!\d)(?:\+?92|0)?3\d{2}[- ]?\d{7}(?!\d)")


def scrub(value):
    if isinstance(value, str):
        return _PHONE.sub("[phone removed]", _CNIC.sub("[cnic removed]", value))
    return value


def save(kind, data):
    """Append one record to data/logs/<kind>.jsonl. Never raises: saving must not break the app."""
    if not ENABLED:
        return
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        record = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  **{k: scrub(v) for k, v in data.items()}}
        with _lock, open(LOG_DIR / f"{kind}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass
