"""Immutable raw FRED release response snapshots."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


RAW_RELEASE_ROOT = Path(__file__).resolve().parents[2] / "data" / "raw" / "fred" / "releases"
KINDS = {"series_release", "release_dates"}


def save_release_response(kind: str, identifier: str, payload: dict) -> Path:
    if kind not in KINDS or not re.fullmatch(r"[A-Za-z0-9_-]+", identifier):
        raise ValueError("Invalid raw release response location.")
    target = RAW_RELEASE_ROOT / kind / identifier
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = target / f"{stamp}_{uuid4().hex}.json"
    with path.open("x", encoding="utf-8") as raw_file:
        json.dump(payload, raw_file, indent=2)
        raw_file.write("\n")
    return path
