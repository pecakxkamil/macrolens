"""Sync FRED releases relevant to active MacroLens series into PostgreSQL."""

import argparse
import sys
from datetime import date, timedelta

from app.database.connection import get_connection
from app.database.sync_series import load_series_config
from app.ingestion.fred_releases import (
    RELEASE_DATE_PAGE_SIZE,
    fetch_release_dates_page,
    fetch_series_release,
    parse_release_dates,
    parse_series_releases,
)
from app.ingestion.release_raw_storage import save_release_response


ACTIVE_CONFIGURED_SERIES_SQL = """
SELECT series_id FROM series
WHERE active = TRUE AND series_id = ANY(%s)
ORDER BY series_id;
"""

UPSERT_RELEASE_SQL = """
INSERT INTO economic_releases (release_id, name, source_link, press_release)
VALUES (%s, %s, %s, %s)
ON CONFLICT (release_id) DO UPDATE SET
    name = EXCLUDED.name,
    source_link = EXCLUDED.source_link,
    press_release = EXCLUDED.press_release,
    updated_at = CURRENT_TIMESTAMP
WHERE (economic_releases.name, economic_releases.source_link, economic_releases.press_release)
  IS DISTINCT FROM (EXCLUDED.name, EXCLUDED.source_link, EXCLUDED.press_release);
"""

REMOVE_STALE_MAP_SQL = """
DELETE FROM series_release_map
WHERE series_id = %s AND NOT (release_id = ANY(%s));
"""

UPSERT_MAP_SQL = """
INSERT INTO series_release_map (series_id, release_id)
VALUES (%s, %s)
ON CONFLICT (series_id, release_id) DO NOTHING;
"""

UPSERT_DATE_SQL = """
INSERT INTO release_dates (release_id, release_date, release_last_updated)
VALUES (%s, %s, %s)
ON CONFLICT (release_id, release_date) DO UPDATE SET
    release_last_updated = EXCLUDED.release_last_updated,
    updated_at = CURRENT_TIMESTAMP
WHERE release_dates.release_last_updated IS DISTINCT FROM EXCLUDED.release_last_updated;
"""

REMOVE_STALE_FUTURE_DATES_SQL = """
DELETE FROM release_dates
WHERE release_id = %s AND release_date BETWEEN %s AND %s
  AND NOT (release_date = ANY(%s::date[]));
"""


def active_configured_series_ids() -> list[str]:
    configured = load_series_config()
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(ACTIVE_CONFIGURED_SERIES_SQL, (list(configured),))
            return [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()


def collect_release_dates(release_id: int, start_date: date, end_date: date) -> list[dict]:
    """Page newest first and stop after reaching dates older than the requested window."""
    offset = 0
    selected = {}
    while True:
        payload = fetch_release_dates_page(release_id, offset)
        save_release_response("release_dates", str(release_id), payload)
        page = parse_release_dates(payload, release_id)
        for item in page:
            if start_date <= item["release_date"] <= end_date:
                selected[item["release_date"]] = item
        if not page or min(item["release_date"] for item in page) < start_date:
            break
        offset += len(page)
        if offset >= int(payload.get("count", offset + RELEASE_DATE_PAGE_SIZE)) or len(page) < RELEASE_DATE_PAGE_SIZE:
            break
    return [selected[key] for key in sorted(selected)]


def sync_release_calendar(start_date: date, end_date: date) -> dict:
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date.")

    today = date.today()
    series_ids = active_configured_series_ids()
    releases = {}
    mappings = {}
    for series_id in series_ids:
        payload = fetch_series_release(series_id)
        save_release_response("series_release", series_id, payload)
        linked = parse_series_releases(payload)
        mappings[series_id] = {release["release_id"] for release in linked}
        for release in linked:
            releases[release["release_id"]] = release

    dates = {}
    for release_id in sorted(releases):
        for item in collect_release_dates(release_id, start_date, end_date):
            dates[(release_id, item["release_date"])] = item

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            for release in releases.values():
                cursor.execute(UPSERT_RELEASE_SQL, (
                    release["release_id"], release["name"],
                    release["source_link"], release["press_release"],
                ))
            for series_id, release_ids in mappings.items():
                cursor.execute(REMOVE_STALE_MAP_SQL, (series_id, list(release_ids)))
                for release_id in sorted(release_ids):
                    cursor.execute(UPSERT_MAP_SQL, (series_id, release_id))
            for item in dates.values():
                cursor.execute(UPSERT_DATE_SQL, (
                    item["release_id"], item["release_date"], item["release_last_updated"],
                ))
            future_start = max(start_date, today)
            if future_start <= end_date:
                for release_id in releases:
                    current_future_dates = [
                        item["release_date"] for item in dates.values()
                        if item["release_id"] == release_id and item["release_date"] >= future_start
                    ]
                    cursor.execute(REMOVE_STALE_FUTURE_DATES_SQL, (
                        release_id, future_start, end_date, current_future_dates,
                    ))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return {
        "series_processed": len(series_ids),
        "releases": len(releases),
        "dates_upserted": len(dates),
        "future_dates": sum(1 for item in dates.values() if item["release_date"] > today),
    }


def main(argv=None) -> int:
    today = date.today()
    parser = argparse.ArgumentParser(description="Sync MacroLens FRED release calendar.")
    parser.add_argument("--start-date", type=date.fromisoformat, default=today - timedelta(days=365))
    parser.add_argument("--end-date", type=date.fromisoformat, default=today + timedelta(days=180))
    args = parser.parse_args(argv)
    try:
        result = sync_release_calendar(args.start_date, args.end_date)
    except Exception:
        print("Calendar sync failed. Check FRED key, network, and database configuration.", file=sys.stderr)
        return 1
    print(f"Configured active series processed: {result['series_processed']}")
    print(f"Relevant releases: {result['releases']}")
    print(f"Release dates upserted: {result['dates_upserted']}")
    print(f"Future release dates: {result['future_dates']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
