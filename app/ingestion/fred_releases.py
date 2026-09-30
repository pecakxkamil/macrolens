"""Focused FRED release metadata client and response parsing."""

import os
from datetime import date

import httpx
from dotenv import load_dotenv

from app.ingestion.fred import REQUEST_TIMEOUT_SECONDS


FRED_BASE_URL = "https://api.stlouisfed.org/fred"
RELEASE_DATE_PAGE_SIZE = 1000


def _fetch_json(path: str, params: dict) -> dict:
    load_dotenv()
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("Missing required environment variable: FRED_API_KEY")
    try:
        response = httpx.get(
            f"{FRED_BASE_URL}/{path}",
            params={**params, "api_key": api_key, "file_type": "json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as error:
        raise RuntimeError(f"FRED release request failed with HTTP {error.response.status_code}") from error
    except httpx.HTTPError as error:
        raise RuntimeError("FRED release request failed.") from error
    except ValueError as error:
        raise RuntimeError("FRED returned invalid release JSON.") from error
    if not isinstance(payload, dict):
        raise ValueError("FRED release response must be an object.")
    return payload


def fetch_series_release(series_id: str) -> dict:
    return _fetch_json("series/release", {"series_id": series_id})


def fetch_release_dates_page(release_id: int, offset: int) -> dict:
    return _fetch_json("release/dates", {
        "release_id": release_id,
        "include_release_dates_with_no_data": "true",
        "sort_order": "desc",
        "limit": RELEASE_DATE_PAGE_SIZE,
        "offset": offset,
    })


def parse_series_releases(payload: dict) -> list[dict]:
    releases = payload.get("releases")
    if not isinstance(releases, list) or not releases:
        raise ValueError("FRED series release response has no releases.")
    parsed = []
    for item in releases:
        if not isinstance(item, dict):
            raise ValueError("Invalid FRED release metadata.")
        release_id = item.get("id")
        name = item.get("name")
        if type(release_id) is not int or release_id <= 0 or not isinstance(name, str) or not name.strip():
            raise ValueError("Invalid FRED release id or name.")
        link = item.get("link")
        press_release = item.get("press_release")
        parsed.append({
            "release_id": release_id,
            "name": name.strip(),
            "source_link": link if isinstance(link, str) and link else None,
            "press_release": press_release if isinstance(press_release, bool) else None,
        })
    return parsed


def parse_release_dates(payload: dict, release_id: int) -> list[dict]:
    items = payload.get("release_dates")
    if not isinstance(items, list):
        raise ValueError("FRED release dates response is missing release_dates.")
    parsed = []
    for item in items:
        if not isinstance(item, dict) or item.get("release_id") != release_id:
            raise ValueError("FRED release date has an invalid release id.")
        raw_date = item.get("date")
        try:
            release_date = date.fromisoformat(raw_date)
        except (TypeError, ValueError) as error:
            raise ValueError("FRED release date is invalid.") from error
        last_updated = item.get("release_last_updated")
        parsed.append({
            "release_id": release_id,
            "release_date": release_date,
            "release_last_updated": last_updated if isinstance(last_updated, str) and last_updated else None,
        })
    return parsed
