"""Reusable date-level ALFRED loaders isolated from current FRED snapshots."""

from datetime import date

from app.database.connection import get_connection
from app.ingestion.backfill_vintages import MCI_SERIES

AS_OF_SQL = """
SELECT observation_date, vintage_date, value, realtime_end FROM (
    SELECT DISTINCT ON (observation_date)
        observation_date, vintage_date, value, realtime_end
    FROM observation_vintages
    WHERE series_id = %s AND source = 'alfred'
      AND vintage_date <= %s AND observation_date <= %s
    ORDER BY observation_date, vintage_date DESC
) known ORDER BY observation_date;
"""
BULK_SQL = """
SELECT series_id, observation_date, vintage_date, value, realtime_end
FROM observation_vintages
WHERE source = 'alfred' AND series_id = ANY(%s)
  AND vintage_date <= %s AND observation_date <= %s
ORDER BY vintage_date, series_id, observation_date;
"""


def select_as_of(rows: list, as_of_date: date) -> list:
    """Pure fixture/in-memory equivalent of latest-known vintage selection."""
    selected = {}
    for row in sorted(rows, key=lambda item: (str(item["vintage_date"]), str(item["observation_date"]))):
        if str(row["vintage_date"]) <= str(as_of_date) and str(row["observation_date"]) <= str(as_of_date):
            selected[str(row["observation_date"])] = row
    result = []
    for observed in sorted(selected):
        row = selected[observed].copy()
        if row.get("realtime_end") and str(row["realtime_end"]) < str(as_of_date):
            row["value"] = None  # Expiration is not permission to revive an earlier vintage.
        result.append(row)
    return result


def load_series_as_of(series_id: str, as_of_date: date) -> dict:
    if series_id not in MCI_SERIES:
        raise ValueError("PIT v1 supports MCI component series only.")
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(AS_OF_SQL, (series_id, as_of_date, as_of_date))
            rows = [{"observation_date": str(observed), "vintage_date": str(vintage),
                     "value": value if end is None or end >= as_of_date else None,
                     "realtime_end": str(end) if end else None}
                    for observed, vintage, value, end in cursor.fetchall()]
    finally:
        connection.close()
    return {"series_id": series_id, "as_of_date": str(as_of_date),
            "history_type": "point_in_time", "observations": rows}


def load_vintage_panel(cutoff: date) -> tuple:
    """Two bulk reads, independent of the number of historical month-end rows."""
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(BULK_SQL, (list(MCI_SERIES), cutoff, cutoff))
            rows = [{"series_id": series, "observation_date": str(observed),
                     "vintage_date": str(vintage), "value": value,
                     "realtime_end": str(end) if end else None}
                    for series, observed, vintage, value, end in cursor.fetchall()]
            cursor.execute("SELECT series_id, realtime_end FROM alfred_backfills WHERE series_id = ANY(%s)", (list(MCI_SERIES),))
            coverage = {series: str(end) for series, end in cursor.fetchall()}
    finally:
        connection.close()
    return rows, coverage


def load_backfill_signature() -> dict:
    # A completed backfill is the supported writer of trusted vintages.
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT series_id, realtime_end, rows_downloaded, completed_at "
                "FROM alfred_backfills WHERE series_id = ANY(%s) ORDER BY series_id",
                (list(MCI_SERIES),),
            )
            return {series: [str(end), count, str(completed)]
                    for series, end, count, completed in cursor.fetchall()}
    finally:
        connection.close()
