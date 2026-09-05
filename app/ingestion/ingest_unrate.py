"""Fetch UNRATE from FRED and load observation vintages into PostgreSQL."""

import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.database.connection import get_connection
from app.ingestion.fred import fetch_series_observations
from app.ingestion.raw_storage import save_raw_response


SERIES_ID = "UNRATE"

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


def _parse_observation(observation: dict) -> Optional[dict]:
    value = observation.get("value")
    if value in (None, "."):
        return None

    try:
        numeric_value = Decimal(value)
        observation_date = date.fromisoformat(observation["date"])
        vintage_date = date.fromisoformat(observation["realtime_start"])
    except (InvalidOperation, KeyError, ValueError):
        return None

    return {
        "series_id": SERIES_ID,
        "observation_date": observation_date,
        "vintage_date": vintage_date,
        "value": numeric_value,
    }


def main() -> int:
    connection = None

    try:
        response_data = fetch_series_observations(SERIES_ID)
        raw_file_path = save_raw_response(SERIES_ID, response_data)

        observations = response_data["observations"]
        parsed_observations = [
            parsed
            for observation in observations
            if (parsed := _parse_observation(observation)) is not None
        ]

        connection = get_connection()
        with connection.cursor() as cursor:
            for observation in parsed_observations:
                cursor.execute(INSERT_OBSERVATION_SQL, observation)

        connection.commit()

        print(f"RAW file: {raw_file_path}")
        print(f"Observations received: {len(observations)}")
        print(f"Valid observations processed: {len(parsed_observations)}")
        print("UNRATE ingestion completed successfully.")
        return 0
    except Exception as error:
        if connection is not None:
            connection.rollback()
        print(f"UNRATE ingestion failed: {error}", file=sys.stderr)
        return 1
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    sys.exit(main())
