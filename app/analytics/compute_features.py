"""Compute and store configured v1 analytical features."""

import sys
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

from app.analytics.features import METHODOLOGY_VERSION, calculate_features
from app.database.connection import get_connection


CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "series.yaml"

LATEST_AS_OF_DATE_SQL = """
SELECT MAX(vintage_date)
FROM observation_vintages
WHERE series_id = %s;
"""

SNAPSHOT_SQL = """
WITH ranked_vintages AS (
    SELECT
        observation_date,
        vintage_date,
        value,
        ROW_NUMBER() OVER (
            PARTITION BY observation_date
            ORDER BY vintage_date DESC
        ) AS vintage_rank
    FROM observation_vintages
    WHERE series_id = %s
      AND vintage_date <= %s
      AND value IS NOT NULL
)
SELECT observation_date, vintage_date, value
FROM ranked_vintages
WHERE vintage_rank = 1
ORDER BY observation_date;
"""

UPSERT_FEATURE_SQL = """
INSERT INTO computed_features (
    series_id,
    observation_date,
    as_of_date,
    feature_name,
    feature_value,
    methodology_version
) VALUES (
    %(series_id)s,
    %(observation_date)s,
    %(as_of_date)s,
    %(feature_name)s,
    %(feature_value)s,
    %(methodology_version)s
)
ON CONFLICT (
    series_id,
    observation_date,
    as_of_date,
    feature_name,
    methodology_version
) DO UPDATE SET
    feature_value = EXCLUDED.feature_value,
    computed_at = CURRENT_TIMESTAMP;
"""


def _load_series_config() -> dict:
    if not CONFIG_PATH.exists():
        raise RuntimeError(f"Series config not found: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    if not isinstance(config, dict) or not config:
        raise RuntimeError("Series config must contain at least one series entry.")

    return config


def _parse_as_of_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise RuntimeError(f"Invalid as_of_date, expected YYYY-MM-DD: {value}") from error


def _get_latest_as_of_date(connection, series_id: str) -> date:
    with connection.cursor() as cursor:
        cursor.execute(LATEST_AS_OF_DATE_SQL, (series_id,))
        result = cursor.fetchone()

    if result is None or result[0] is None:
        raise RuntimeError(f"No observation vintages found for {series_id}.")

    return result[0]


def load_point_in_time_snapshot(
    connection,
    series_id: str,
    as_of_date: date,
) -> pd.DataFrame:
    """Load one latest-available value per observation date as of a vintage date."""
    with connection.cursor() as cursor:
        cursor.execute(SNAPSHOT_SQL, (series_id, as_of_date))
        rows = cursor.fetchall()

    return pd.DataFrame(
        rows,
        columns=["observation_date", "vintage_date", "value"],
    )


def compute_features(series_id: str, as_of_date: Optional[date] = None) -> dict:
    """Compute and store configured v1 features for one series."""
    connection = None

    try:
        config = _load_series_config()
        if series_id not in config:
            known_series = ", ".join(sorted(config.keys()))
            raise RuntimeError(
                f"Unknown series_id: {series_id}. Configured series: {known_series}"
            )

        feature_names = config[series_id].get("transformations")
        if not isinstance(feature_names, list) or not feature_names:
            raise RuntimeError(f"No transformations configured for {series_id}.")

        connection = get_connection()
        resolved_as_of_date = as_of_date or _get_latest_as_of_date(
            connection,
            series_id,
        )
        snapshot = load_point_in_time_snapshot(
            connection,
            series_id,
            resolved_as_of_date,
        )
        features = calculate_features(series_id, snapshot, feature_names)

        with connection.cursor() as cursor:
            for feature in features.to_dict("records"):
                cursor.execute(
                    UPSERT_FEATURE_SQL,
                    {
                        "series_id": series_id,
                        "observation_date": feature["observation_date"],
                        "as_of_date": resolved_as_of_date,
                        "feature_name": feature["feature_name"],
                        "feature_value": feature["feature_value"],
                        "methodology_version": METHODOLOGY_VERSION,
                    },
                )

        connection.commit()

        summary = {
            "series_id": series_id,
            "as_of_date": resolved_as_of_date,
            "source_observations": len(snapshot),
            "feature_rows_written": len(features),
            "feature_names": feature_names,
        }

        print(f"Series ID: {series_id}")
        print(f"As-of date: {resolved_as_of_date}")
        print(f"Source observations: {summary['source_observations']}")
        print(f"Feature rows written: {summary['feature_rows_written']}")
        print(f"Feature names calculated: {', '.join(feature_names)}")

        return summary
    except Exception as error:
        if connection is not None:
            connection.rollback()
        print(f"Feature computation failed for {series_id}: {error}", file=sys.stderr)
        raise
    finally:
        if connection is not None:
            connection.close()


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(
            "Usage: python -m app.analytics.compute_features <SERIES_ID> "
            "[AS_OF_DATE]",
            file=sys.stderr,
        )
        return 1

    series_id = sys.argv[1]
    try:
        as_of_date = _parse_as_of_date(sys.argv[2]) if len(sys.argv) == 3 else None
    except Exception as error:
        print(f"Feature computation failed for {series_id}: {error}", file=sys.stderr)
        return 1

    try:
        compute_features(series_id, as_of_date)
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())
