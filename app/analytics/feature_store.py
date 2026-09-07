"""Shared computed-feature loading helpers for analytics modules."""

from datetime import date
from typing import Optional

from app.analytics.features import METHODOLOGY_VERSION


LATEST_FEATURE_AS_OF_SQL = """
SELECT as_of_date
FROM computed_features
WHERE series_id = %s
  AND methodology_version = %s
  AND feature_name = ANY(%s)
  AND (%s::date IS NULL OR as_of_date <= %s)
GROUP BY as_of_date
HAVING COUNT(DISTINCT feature_name) = %s
ORDER BY as_of_date DESC
LIMIT 1;
"""

LATEST_COMMON_OBSERVATION_DATE_SQL = """
SELECT observation_date
FROM computed_features
WHERE series_id = %s
  AND methodology_version = %s
  AND as_of_date = %s
  AND feature_name = ANY(%s)
GROUP BY observation_date
HAVING COUNT(DISTINCT feature_name) = %s
ORDER BY observation_date DESC
LIMIT 1;
"""

FEATURE_VALUES_SQL = """
SELECT feature_name, feature_value
FROM computed_features
WHERE series_id = %s
  AND methodology_version = %s
  AND as_of_date = %s
  AND observation_date = %s
  AND feature_name = ANY(%s);
"""


def load_latest_component_features(
    connection,
    series_id: str,
    feature_names: tuple,
    requested_as_of_date: Optional[date],
) -> dict:
    """Load the latest complete v1 feature set for a series."""
    with connection.cursor() as cursor:
        cursor.execute(
            LATEST_FEATURE_AS_OF_SQL,
            (
                series_id,
                METHODOLOGY_VERSION,
                list(feature_names),
                requested_as_of_date,
                requested_as_of_date,
                len(feature_names),
            ),
        )
        as_of_result = cursor.fetchone()

        if as_of_result is None or as_of_result[0] is None:
            raise RuntimeError(f"No v1 features found for {series_id}.")

        feature_as_of_date = as_of_result[0]
        cursor.execute(
            LATEST_COMMON_OBSERVATION_DATE_SQL,
            (
                series_id,
                METHODOLOGY_VERSION,
                feature_as_of_date,
                list(feature_names),
                len(feature_names),
            ),
        )
        observation_result = cursor.fetchone()

        if observation_result is None:
            raise RuntimeError(
                f"No complete feature set found for {series_id} as of "
                f"{feature_as_of_date}."
            )

        observation_date = observation_result[0]
        cursor.execute(
            FEATURE_VALUES_SQL,
            (
                series_id,
                METHODOLOGY_VERSION,
                feature_as_of_date,
                observation_date,
                list(feature_names),
            ),
        )
        rows = cursor.fetchall()

    values = {feature_name: feature_value for feature_name, feature_value in rows}
    missing_features = set(feature_names) - set(values.keys())
    if missing_features:
        missing = ", ".join(sorted(missing_features))
        raise RuntimeError(f"Missing features for {series_id}: {missing}")

    values["feature_as_of_date"] = feature_as_of_date
    values["observation_date"] = observation_date
    return values
