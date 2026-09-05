"""RAW API response persistence."""

import json
from datetime import datetime, timezone
from pathlib import Path


RAW_ROOT = Path(__file__).resolve().parents[2] / "data" / "raw" / "fred"


def save_raw_response(series_id: str, response_data: dict) -> Path:
    """Save a complete FRED JSON response and return the created file path."""
    series_dir = RAW_ROOT / series_id
    series_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    file_path = series_dir / f"{series_id}_{timestamp}.json"

    with file_path.open("w", encoding="utf-8") as raw_file:
        json.dump(response_data, raw_file, indent=2)
        raw_file.write("\n")

    return file_path
