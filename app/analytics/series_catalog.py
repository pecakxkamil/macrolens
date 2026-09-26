"""Public metadata for active configured series and stored v1 features."""

from app.analytics.features import FEATURES_BY_SERIES, METHODOLOGY_VERSION
from app.database.connection import get_connection
from app.database.sync_series import load_series_config


SERIES_FIELDS = ("series_id", "name", "short_name", "category", "frequency", "unit")

LIST_SERIES_SQL = """
SELECT series_id, name, short_name, category, frequency, unit
FROM series
WHERE active = TRUE AND series_id = ANY(%s)
ORDER BY category, short_name, series_id;
"""

GET_SERIES_SQL = """
SELECT series_id, name, short_name, category, frequency, unit
FROM series
WHERE active = TRUE AND series_id = %s;
"""

AVAILABLE_FEATURES_SQL = """
SELECT DISTINCT feature_name
FROM computed_features
WHERE series_id = %s AND methodology_version = %s
  AND feature_value IS NOT NULL;
"""


class UnknownCatalogSeriesError(ValueError):
    """Raised for an unknown or inactive configured series."""


def _metadata(row: tuple) -> dict:
    return dict(zip(SERIES_FIELDS, row))


def list_active_series() -> dict:
    configured = load_series_config()
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(LIST_SERIES_SQL, (list(configured),))
            rows = cursor.fetchall()
    finally:
        connection.close()

    return {"series": [_metadata(row) for row in rows]}


def get_active_series(series_id: str) -> dict:
    if series_id not in load_series_config():
        raise UnknownCatalogSeriesError(f"Unknown series: {series_id}")

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(GET_SERIES_SQL, (series_id,))
            row = cursor.fetchone()
    finally:
        connection.close()

    if row is None:
        raise UnknownCatalogSeriesError(f"Unknown series: {series_id}")
    return _metadata(row)


def list_available_features(series_id: str) -> dict:
    # Validate active status before reporting transformations.
    get_active_series(series_id)
    configured = load_series_config()[series_id].get("transformations", ())
    supported = FEATURES_BY_SERIES.get(series_id, ())
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(AVAILABLE_FEATURES_SQL, (series_id, METHODOLOGY_VERSION))
            stored = {row[0] for row in cursor.fetchall()}
    finally:
        connection.close()

    return {
        "series_id": series_id,
        "methodology_version": METHODOLOGY_VERSION,
        "features": [
            feature for feature in configured
            if feature in supported and feature in stored
        ],
    }
