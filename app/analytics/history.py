"""Read-only current-vintage history access for charts."""

from datetime import date
from typing import Optional

from app.analytics.features import FEATURES_BY_SERIES, METHODOLOGY_VERSION
from app.database.connection import get_connection
from app.database.sync_series import load_series_config


HISTORY_TYPE = "current_vintage"

SERIES_HISTORY_SQL = """
SELECT observation_date, value
FROM (
    SELECT DISTINCT ON (observation_date)
        observation_date,
        value
    FROM observation_vintages
    WHERE series_id = %s
      AND (%s::date IS NULL OR observation_date >= %s)
      AND (%s::date IS NULL OR observation_date <= %s)
    ORDER BY observation_date, vintage_date DESC, ingested_at DESC, id DESC
) AS current_values
ORDER BY observation_date ASC;
"""

FEATURE_HISTORY_SQL = """
SELECT observation_date, as_of_date, feature_value
FROM (
    SELECT DISTINCT ON (observation_date)
        observation_date,
        as_of_date,
        feature_value
    FROM computed_features
    WHERE series_id = %s
      AND feature_name = %s
      AND methodology_version = %s
      AND (%s::date IS NULL OR observation_date >= %s)
      AND (%s::date IS NULL OR observation_date <= %s)
    ORDER BY observation_date, as_of_date DESC, computed_at DESC, id DESC
) AS current_features
ORDER BY observation_date ASC;
"""

YIELD_CURVE_HISTORY_SQL = """
WITH current_yields AS (
    SELECT DISTINCT ON (series_id, observation_date)
        series_id, observation_date, value
    FROM observation_vintages
    WHERE series_id IN ('DGS2', 'DGS10')
      AND (%s::date IS NULL OR observation_date >= %s)
      AND (%s::date IS NULL OR observation_date <= %s)
    ORDER BY series_id, observation_date, vintage_date DESC, ingested_at DESC, id DESC
)
SELECT ten.observation_date, ten.value - two.value AS value
FROM current_yields AS ten
JOIN current_yields AS two ON ten.observation_date = two.observation_date
WHERE ten.series_id = 'DGS10' AND two.series_id = 'DGS2'
  AND ten.value IS NOT NULL AND two.value IS NOT NULL
ORDER BY ten.observation_date ASC;
"""


class UnknownSeriesError(ValueError):
    """Raised when a series is not configured in MacroLens."""


class UnsupportedFeatureError(ValueError):
    """Raised when a feature is not configured for a series."""


class InvalidDateRangeError(ValueError):
    """Raised when a history date range is reversed."""


def _validate_date_range(
    start_date: Optional[date], end_date: Optional[date]
) -> None:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise InvalidDateRangeError("start_date must be on or before end_date.")


def _series_metadata(series_id: str) -> dict:
    config = load_series_config()
    if series_id not in config:
        raise UnknownSeriesError(f"Unknown series: {series_id}")

    metadata = config[series_id]
    return {
        "name": metadata["name"],
        "short_name": metadata["short_name"],
        "frequency": metadata["frequency"],
        "unit": metadata["unit"],
    }


def load_series_history(
    series_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """Load one latest-stored value per observation date for a series."""
    metadata = _series_metadata(series_id)
    _validate_date_range(start_date, end_date)

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                SERIES_HISTORY_SQL,
                (series_id, start_date, start_date, end_date, end_date),
            )
            rows = cursor.fetchall()
    finally:
        connection.close()

    return {
        "series_id": series_id,
        **metadata,
        "history_type": HISTORY_TYPE,
        "start_date": start_date,
        "end_date": end_date,
        "observations": [
            {"observation_date": observation_date, "value": value}
            for observation_date, value in rows
        ],
    }


def load_feature_history(
    series_id: str,
    feature_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    methodology_version: str = METHODOLOGY_VERSION,
) -> dict:
    """Load the latest stored feature value per observation date."""
    metadata = _series_metadata(series_id)
    configured_features = FEATURES_BY_SERIES.get(series_id, ())
    if feature_name not in configured_features:
        raise UnsupportedFeatureError(
            f"Unsupported feature for {series_id}: {feature_name}"
        )
    _validate_date_range(start_date, end_date)

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                FEATURE_HISTORY_SQL,
                (
                    series_id,
                    feature_name,
                    methodology_version,
                    start_date,
                    start_date,
                    end_date,
                    end_date,
                ),
            )
            rows = cursor.fetchall()
    finally:
        connection.close()

    return {
        "series_id": series_id,
        **metadata,
        "feature_name": feature_name,
        "methodology_version": methodology_version,
        "history_type": HISTORY_TYPE,
        "start_date": start_date,
        "end_date": end_date,
        "observations": [
            {
                "observation_date": observation_date,
                "feature_as_of_date": feature_as_of_date,
                "value": value,
            }
            for observation_date, feature_as_of_date, value in rows
        ],
    }


def load_yield_curve_2s10s_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """Subtract latest stored DGS2 from DGS10 on matching observation dates."""
    _validate_date_range(start_date, end_date)
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                YIELD_CURVE_HISTORY_SQL,
                (start_date, start_date, end_date, end_date),
            )
            rows = cursor.fetchall()
    finally:
        connection.close()

    return {
        "series_id": "2s10s",
        "name": "2s10s Treasury Yield Spread",
        "frequency": "daily",
        "unit": "percentage points",
        "history_type": HISTORY_TYPE,
        "start_date": start_date,
        "end_date": end_date,
        "observations": [
            {"observation_date": observation_date, "value": value}
            for observation_date, value in rows
        ],
    }
