"""FRED API client helpers."""

import os

import httpx
from dotenv import load_dotenv
from app.ingestion.request_budget import before_request


FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"
REQUEST_TIMEOUT_SECONDS = 20.0


def _fetch(path: str, params: dict) -> dict:
    """Fetch observations for a FRED series and return the decoded JSON response."""
    load_dotenv()

    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("Missing required environment variable: FRED_API_KEY")

    before_request("FRED")
    try:
        response = httpx.get(
            "https://api.stlouisfed.org/fred/" + path,
            params={
                **params,
                "api_key": api_key,
                "file_type": "json",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        status_code = error.response.status_code
        raise RuntimeError(f"FRED request failed with HTTP {status_code}") from error
    except httpx.HTTPError as error:
        raise RuntimeError("FRED request failed.") from error

    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError("FRED returned invalid JSON.") from error

    if not isinstance(data, dict):
        raise RuntimeError("FRED response must be an object.")
    return data


def fetch_series_metadata(series_id: str) -> dict:
    payload = _fetch("series", {"series_id": series_id})
    rows = payload.get("seriess", [])
    if len(rows) != 1 or rows[0].get("id") != series_id or not rows[0].get("last_updated"):
        raise RuntimeError("FRED returned incomplete series metadata.")
    return rows[0]


def fetch_series_observations(series_id: str, observation_start=None) -> dict:
    params = {"series_id": series_id, "limit": 100000, "offset": 0}
    if observation_start:
        params["observation_start"] = str(observation_start)
    first, observations = None, []
    while True:
        page = _fetch("series/observations", params)
        rows = page.get("observations")
        if not isinstance(rows, list):
            raise RuntimeError("FRED response is missing an observations list.")
        if first is None:
            first = page
        expected = int(page.get("count", len(rows)))
        if int(page.get("offset", params['offset'])) != params['offset']:
            raise RuntimeError("FRED observation pagination returned the wrong offset.")
        observations.extend(rows)
        if len(observations) >= expected:
            break
        if not rows:
            raise RuntimeError("FRED observation pagination ended before its count.")
        params['offset'] += len(rows)
    return {**first, "observations": observations}
