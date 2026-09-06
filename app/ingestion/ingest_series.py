"""Fetch a configured FRED series and load observation vintages."""

import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

import yaml

from app.database.connection import get_connection
from app.ingestion.fred import fetch_series_observations
from app.ingestion.raw_storage import save_raw_response
from app.validation.fred_observations import validate_fred_observations


CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "series.yaml"

INSERT_OBSERVATION_SQL = """
INSERT INTO observation_vintages (
    series_id,
    observation_date,
    vintage_date,
    value
) VALUES (
    %(series_id)s,
    %(observation_date)s,
    %(vintage_date)s,
    %(value)s
)
ON CONFLICT (series_id, observation_date, vintage_date) DO UPDATE SET
    value = EXCLUDED.value,
    ingested_at = CURRENT_TIMESTAMP;
"""


def _load_configured_series_ids() -> set:
    if not CONFIG_PATH.exists():
        raise RuntimeError(f"Series config not found: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    if not isinstance(config, dict) or not config:
        raise RuntimeError("Series config must contain at least one series entry.")

    return set(config.keys())


def _parse_observation(series_id: str, observation: dict) -> Optional[dict]:
    value = observation.get("value")
    if value in (None, "."):
        return None

    try:
        return {
            "series_id": series_id,
            "observation_date": date.fromisoformat(observation["date"]),
            "vintage_date": date.fromisoformat(observation["realtime_start"]),
            "value": Decimal(value),
        }
    except (InvalidOperation, KeyError, ValueError) as error:
        raise RuntimeError(f"Invalid observation for {series_id}: {observation}") from error


def ingest_series(series_id: str) -> dict:
    """Ingest one configured FRED series into observation_vintages."""
    connection = None

    try:
        configured_series_ids = _load_configured_series_ids()
        if series_id not in configured_series_ids:
            known_series = ", ".join(sorted(configured_series_ids))
            raise RuntimeError(
                f"Unknown series_id: {series_id}. Configured series: {known_series}"
            )

        response_data = fetch_series_observations(series_id)
        raw_file_path = save_raw_response(series_id, response_data)
        validation_summary = validate_fred_observations(response_data)

        observations = response_data["observations"]
        parsed_observations = []
        for observation in observations:
            parsed = _parse_observation(series_id, observation)
            if parsed is not None:
                parsed_observations.append(parsed)

        connection = get_connection()
        with connection.cursor() as cursor:
            for observation in parsed_observations:
                cursor.execute(INSERT_OBSERVATION_SQL, observation)

        connection.commit()

        summary = {
            "series_id": series_id,
            "raw_file_path": raw_file_path,
            "observations_received": len(observations),
            "valid_observations_processed": len(parsed_observations),
            "validation": validation_summary,
        }

        print(f"Series ID: {series_id}")
        print(f"RAW file: {raw_file_path}")
        print(
            "Validation summary: "
            f"total={validation_summary['total_observations']}, "
            f"numeric={validation_summary['numeric_observations']}, "
            f"missing={validation_summary['missing_observations']}"
        )
        print(f"Observations received: {summary['observations_received']}")
        print(
            "Valid observations processed: "
            f"{summary['valid_observations_processed']}"
        )
        print(f"{series_id} ingestion completed successfully.")

        return summary
    except Exception as error:
        if connection is not None:
            connection.rollback()
        print(f"{series_id} ingestion failed: {error}", file=sys.stderr)
        raise
    finally:
        if connection is not None:
            connection.close()


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: python -m app.ingestion.ingest_series <SERIES_ID>",
            file=sys.stderr,
        )
        return 1

    try:
        ingest_series(sys.argv[1])
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())
