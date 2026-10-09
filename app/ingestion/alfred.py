"""ALFRED real-time interval downloads with immutable raw response storage."""

import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import load_dotenv

from app.ingestion.fred import FRED_OBSERVATIONS_URL

EARLIEST_REALTIME = date(1776, 7, 4)
PAGE_SIZE = 10000
RAW_ROOT = Path(__file__).resolve().parents[2] / "data" / "raw" / "alfred"


def save_raw_response(series_id: str, payload: dict) -> Path:
    if not series_id.isalnum():
        raise ValueError("Invalid ALFRED series ID.")
    folder = RAW_ROOT / series_id
    folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = folder / f"{timestamp}_{uuid4().hex}.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)
        stream.write("\n")
    return path


def fetch_vintage_page(series_id: str, end_date: date, offset: int = 0) -> dict:
    """Output type 1 returns change intervals; start at the earliest API date."""
    load_dotenv()
    key = os.getenv("FRED_API_KEY")
    if not key:
        raise RuntimeError("Missing required environment variable: FRED_API_KEY")
    try:
        response = httpx.get(FRED_OBSERVATIONS_URL, params={
            "api_key": key, "series_id": series_id, "file_type": "json",
            "realtime_start": str(EARLIEST_REALTIME), "realtime_end": str(end_date),
            "observation_end": str(end_date), "output_type": 1, "units": "lin",
            "sort_order": "asc", "limit": PAGE_SIZE, "offset": offset,
        }, timeout=httpx.Timeout(90.0, connect=10.0))
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise RuntimeError(f"ALFRED request failed with HTTP {error.response.status_code}.") from None
    except httpx.HTTPError:
        # HTTP errors may contain the request URL/API key.
        raise RuntimeError("ALFRED network request failed.") from None
    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError("ALFRED returned invalid JSON.") from None
    if not isinstance(payload, dict):
        raise RuntimeError("ALFRED returned an invalid response object.")
    return payload


def parse_vintage_page(series_id: str, payload: dict, cutoff: date, offset: int) -> list:
    """Validate repeated observation dates across distinct vintages; retain nulls."""
    observations = payload.get("observations")
    count, limit = payload.get("count"), payload.get("limit")
    if (not isinstance(observations, list) or payload.get("output_type") != 1
            or payload.get("units") != "lin" or payload.get("offset") != offset
            or type(count) is not int or type(limit) is not int
            or limit != PAGE_SIZE or not 1 <= limit <= 100000
            or type(offset) is not int or not 0 <= offset <= count
            or len(observations) != min(limit, count - offset)
            or payload.get("realtime_start") != str(EARLIEST_REALTIME)
            or payload.get("realtime_end") != str(cutoff)):
        raise ValueError("Invalid ALFRED page metadata.")
    rows = []
    seen = set()
    for item in observations:
        try:
            observed = date.fromisoformat(item["date"])
            vintage = date.fromisoformat(item["realtime_start"])
            end = date.fromisoformat(item["realtime_end"])
            value = None if item["value"] == "." else Decimal(item["value"])
        except (KeyError, TypeError, ValueError, InvalidOperation):
            raise ValueError("Invalid ALFRED observation.") from None
        if (not EARLIEST_REALTIME <= vintage <= end <= cutoff
                or observed > cutoff or (value is not None and not value.is_finite())):
            raise ValueError("Invalid ALFRED observation dates or value.")
        identity = (observed, vintage)
        if identity in seen:
            raise ValueError("Duplicate ALFRED observation/vintage within a page.")
        seen.add(identity)
        rows.append((series_id, observed, vintage, value, end))
    return rows


def iter_vintage_pages(series_id: str, cutoff: date):
    """Replay matching immutable pages and prefetch at most three missing pages."""
    from collections import deque
    from concurrent.futures import ThreadPoolExecutor

    saved = {}
    folder = RAW_ROOT / series_id
    if folder.exists():
        for path in sorted(folder.glob("*.json")):
            try:
                with path.open("r", encoding="utf-8") as stream:
                    payload = json.load(stream)
                offset = payload.get("offset")
                if (isinstance(offset, int) and payload.get("realtime_start") == str(EARLIEST_REALTIME)
                        and payload.get("realtime_end") == str(cutoff)
                        and payload.get("limit") == PAGE_SIZE):
                    parse_vintage_page(series_id, payload, cutoff, offset)
                    saved[offset] = path
            except (OSError, ValueError):
                continue

    def get(offset):
        if offset in saved:
            with saved[offset].open("r", encoding="utf-8") as stream:
                return json.load(stream)
        payload = fetch_vintage_page(series_id, cutoff, offset)
        save_raw_response(series_id, payload)
        return payload

    first = get(0)
    parse_vintage_page(series_id, first, cutoff, 0)
    yield first
    count = first["count"]
    offsets = iter(range(len(first["observations"]), count, PAGE_SIZE))
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending = deque()
        for _ in range(3):
            offset = next(offsets, None)
            if offset is not None:
                pending.append(pool.submit(get, offset))
        while pending:
            yield pending.popleft().result()
            offset = next(offsets, None)
            if offset is not None:
                pending.append(pool.submit(get, offset))
