"""Read-only calendar queries for tracked MacroLens releases."""

from datetime import date, timedelta
from typing import Optional

from app.database.connection import get_connection
from app.database.sync_series import load_series_config
from app.analytics.release_times import release_time_metadata


CALENDAR_SQL = """
SELECT d.release_date, r.release_id, r.name, r.source_link,
       s.series_id, s.name, s.short_name, s.category, s.frequency, s.unit
FROM release_dates AS d
JOIN economic_releases AS r ON r.release_id = d.release_id
JOIN series_release_map AS m ON m.release_id = r.release_id
JOIN series AS s ON s.series_id = m.series_id
WHERE d.release_date BETWEEN %s AND %s
  AND s.active = TRUE AND s.series_id = ANY(%s)
ORDER BY d.release_date, r.name, r.release_id, s.series_id;
"""

RELEASE_DETAIL_SQL = """
SELECT r.release_id, r.name, r.source_link, r.press_release,
       s.series_id, s.name, s.short_name, s.category, s.frequency, s.unit
FROM economic_releases AS r
JOIN series_release_map AS m ON m.release_id = r.release_id
JOIN series AS s ON s.series_id = m.series_id
WHERE r.release_id = %s AND s.active = TRUE AND s.series_id = ANY(%s)
ORDER BY s.series_id;
"""

RECENT_DATES_SQL = """
SELECT release_date FROM release_dates
WHERE release_id = %s
ORDER BY release_date DESC
LIMIT 8;
"""

HIGH_IMPORTANCE_RELEASES = frozenset({
    "Employment Situation",
    "Consumer Price Index",
    "Personal Income and Outlays",
    "Gross Domestic Product",
    "Unemployment Insurance Weekly Claims Report",
})
MEDIUM_IMPORTANCE_RELEASES = frozenset({
    "Job Openings and Labor Turnover Survey",
    "Industrial Production and Capacity Utilization",
    "Advance Monthly Sales for Retail and Food Services",
    "New Residential Construction",
    "New Residential Sales",
    "Chicago Fed National Financial Conditions Index",
})
LOW_IMPORTANCE_RELEASES = frozenset({"H.15 Selected Interest Rates"})
IMPORTANCE_ORDER = {"high": 0, "medium": 1, "low": 2}


class InvalidCalendarRangeError(ValueError):
    pass


class InvalidCalendarCategoryError(ValueError):
    pass


class UnknownReleaseError(ValueError):
    pass


def _series(row: tuple) -> dict:
    return dict(zip(("series_id", "name", "short_name", "category", "frequency", "unit"), row))


def release_importance(name: str) -> str:
    if name in HIGH_IMPORTANCE_RELEASES:
        return "high"
    if name in LOW_IMPORTANCE_RELEASES:
        return "low"
    if name in MEDIUM_IMPORTANCE_RELEASES:
        return "medium"
    return "medium"


def list_calendar_events(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
) -> dict:
    today = date.today()
    start = start_date or today - timedelta(days=today.weekday())
    end = end_date or start + timedelta(days=6)
    if start > end:
        raise InvalidCalendarRangeError("start_date must be on or before end_date.")
    configured = load_series_config()
    categories = {item["category"] for item in configured.values()}
    if category is not None and category not in categories:
        raise InvalidCalendarCategoryError(f"Unknown category: {category}")

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(CALENDAR_SQL, (start, end, list(configured)))
            rows = cursor.fetchall()
    finally:
        connection.close()

    events = {}
    for release_date, release_id, name, source_link, *series_columns in rows:
        key = (release_id, release_date)
        event = events.setdefault(key, {
            "release_id": release_id,
            "release_name": name,
            "release_date": release_date,
            **release_time_metadata(name, release_date),
            "importance": release_importance(name),
            "source_link": source_link,
            "date_precision": "date",
            "series": [],
        })
        series = _series(tuple(series_columns))
        if not any(item["series_id"] == series["series_id"] for item in event["series"]):
            event["series"].append(series)

    selected = [event for event in events.values() if category is None or any(
        item["category"] == category for item in event["series"]
    )]
    selected.sort(key=lambda event: (
        event["release_date"], IMPORTANCE_ORDER[event["importance"]],
        event["release_name"], event["release_id"],
    ))
    return {
        "start_date": start,
        "end_date": end,
        "category": category,
        "events": selected,
    }


def get_release_detail(release_id: int) -> dict:
    configured = load_series_config()
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(RELEASE_DETAIL_SQL, (release_id, list(configured)))
            rows = cursor.fetchall()
            if not rows:
                raise UnknownReleaseError(f"Unknown release: {release_id}")
            cursor.execute(RECENT_DATES_SQL, (release_id,))
            recent_dates = [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()

    first = rows[0]
    return {
        "release_id": first[0],
        "release_name": first[1],
        "source_link": first[2],
        "press_release": first[3],
        "date_precision": "date",
        "series": [_series(row[4:]) for row in rows],
        "recent_dates": recent_dates,
    }
