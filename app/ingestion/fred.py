"""FRED API client helpers."""

import os

import httpx
from dotenv import load_dotenv


FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"
REQUEST_TIMEOUT_SECONDS = 20.0


def fetch_series_observations(series_id: str) -> dict:
    """Fetch observations for a FRED series and return the decoded JSON response."""
    load_dotenv()

    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("Missing required environment variable: FRED_API_KEY")

    try:
        response = httpx.get(
            FRED_OBSERVATIONS_URL,
            params={
                "series_id": series_id,
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
        raise RuntimeError(f"FRED request failed: {error}") from error

    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError("FRED returned invalid JSON.") from error

    observations = data.get("observations")
    if not isinstance(observations, list):
        raise RuntimeError("FRED response is missing an observations list.")

    return data
