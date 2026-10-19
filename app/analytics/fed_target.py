"""Official Fed target bounds from synchronized stored FRED observations."""
from datetime import date, timedelta
from decimal import Decimal
from app.analytics.relationships import _finite_value
from app.database.connection import get_connection

SOURCE_IDS = ("DFEDTARL", "DFEDTARU")
TARGET_SQL = """
WITH current_values AS MATERIALIZED (
    SELECT DISTINCT ON (series_id, observation_date)
           series_id, observation_date, value, ingested_at
    FROM observation_vintages
    WHERE series_id IN ('DFEDTARL', 'DFEDTARU') AND observation_date <= %s
    ORDER BY series_id, observation_date, vintage_date DESC, ingested_at DESC, id DESC
), lower_latest AS (
    SELECT * FROM current_values WHERE series_id = 'DFEDTARL' ORDER BY observation_date DESC LIMIT 1
), upper_latest AS (
    SELECT * FROM current_values WHERE series_id = 'DFEDTARU' ORDER BY observation_date DESC LIMIT 1
)
SELECT l.observation_date, l.value, u.value,
       ll.ingested_at AT TIME ZONE 'UTC', ul.ingested_at AT TIME ZONE 'UTC',
       ll.observation_date, ul.observation_date
FROM current_values l JOIN current_values u ON l.observation_date = u.observation_date
CROSS JOIN lower_latest ll CROSS JOIN upper_latest ul
WHERE l.series_id = 'DFEDTARL' AND u.series_id = 'DFEDTARU'
ORDER BY l.observation_date DESC;
"""


def summarize_target(rows):
    """Find the current continuous regime; a gap cannot prove its effective date."""
    result = {"availability": "unavailable", "lower": None, "upper": None, "observation_date": None,
              "effective_date": None, "last_rate_change": None, "retrieved_at": None,
              "sources": [{"series_id": sid, "url": f"https://fred.stlouisfed.org/series/{sid}",
                           "observation_date": None, "retrieved_at": None} for sid in SOURCE_IDS]}
    iterator = iter(rows)
    first = next(iterator, None)
    if first is None:
        return result
    day, lower, upper, lower_retrieved, upper_retrieved, lower_latest, upper_latest = first
    lower, upper = _finite_value(lower), _finite_value(upper)
    result["observation_date"] = str(day)
    result["retrieved_at"] = min(lower_retrieved, upper_retrieved).isoformat()
    for source, observed, retrieved in zip(result["sources"], (lower_latest, upper_latest), (lower_retrieved, upper_retrieved)):
        source.update(observation_date=str(observed), retrieved_at=retrieved.isoformat())
    if lower is None or upper is None or lower > upper:
        return result
    result.update(availability="available", lower=lower, upper=upper)
    start = date.fromisoformat(str(day))
    for earlier in iterator:
        previous_day = date.fromisoformat(str(earlier[0]))
        previous_lower, previous_upper = _finite_value(earlier[1]), _finite_value(earlier[2])
        if previous_day != start - timedelta(days=1) or previous_lower is None or previous_upper is None or previous_lower > previous_upper:
            break
        if (previous_lower, previous_upper) != (lower, upper):
            lower_bps = float((Decimal(str(lower)) - Decimal(str(previous_lower))) * 100)
            upper_bps = float((Decimal(str(upper)) - Decimal(str(previous_upper))) * 100)
            result["effective_date"] = str(start)
            result["last_rate_change"] = {"effective_date": str(start), "lower_change_bps": lower_bps,
                                          "upper_change_bps": upper_bps,
                                          "change_bps": lower_bps if lower_bps == upper_bps else None,
                                          "previous_lower": previous_lower, "previous_upper": previous_upper}
            break
        start = previous_day
    return result


def load_fed_target(today):
    connection = get_connection()
    try:
        # A server-side cursor stops sending history as soon as the latest rate
        # change or a gap is reached. Rendering never contacts FRED.
        with connection.cursor(name="macrolens_fed_target") as cursor:
            cursor.execute(TARGET_SQL, (today,))
            return summarize_target(cursor)
    finally:
        connection.close()
