"""Refresh explicit market assets using FRED snapshots, without ALFRED backfill."""
import argparse
import json
import sys
from datetime import date
from decimal import Decimal

from app.database.connection import get_connection
from app.database.sync_series import UPSERT_SERIES_SQL
from app.ingestion.fred import fetch_series_observations
from app.ingestion.ingest_series import INSERT_OBSERVATION_SQL, _parse_observation
from app.ingestion.raw_storage import save_raw_response
from app.market_assets import load_market_assets
from app.validation.fred_observations import validate_fred_observations


def ingest_market_asset(series_id: str) -> dict:
    assets = load_market_assets()
    if series_id not in assets:
        raise ValueError("Select an explicitly configured market asset.")
    metadata = assets[series_id]
    payload = fetch_series_observations(series_id)
    raw_path = save_raw_response(series_id, payload)
    validation = validate_fred_observations(payload)
    observations = payload["observations"]
    # Both v1 daily histories fit FRED's 100000-row response cap. Fail rather
    # than silently accept a truncated snapshot if that changes in the future.
    if (payload.get("offset") != 0 or payload.get("count") != len(observations)
            or payload.get("units") != "lin" or not 1 <= payload.get("limit", 0) <= 100000):
        raise ValueError("Market snapshot is incomplete or transformed; no rows were committed.")
    parsed = []
    for observation in observations:
        row = _parse_observation(series_id, observation)
        if row is None:
            row = {"series_id": series_id, "observation_date": date.fromisoformat(observation["date"]),
                   "vintage_date": date.fromisoformat(observation["realtime_start"]), "value": None}
        if row["value"] is not None and row["value"] <= Decimal(0):
            raise ValueError("Market prices must be positive or source-missing.")
        if row["observation_date"] > date.today():
            raise ValueError("Market observations cannot be future dated.")
        parsed.append(row)
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(UPSERT_SERIES_SQL, {"series_id": series_id, "name": metadata["name"],
                "short_name": metadata["name"], "category": "market", "frequency": "daily",
                "unit": metadata["unit"], "revision_tracking": False})
            # Market rows are accessible by their explicit loader, not macro
            # workflows that join active configured economic series.
            cursor.execute("UPDATE series SET active = FALSE WHERE series_id = %s", (series_id,))
            cursor.executemany(INSERT_OBSERVATION_SQL, parsed)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {"series_id": series_id, "rows_processed": len(parsed), "missing_values": validation["missing_observations"],
            "raw_path": str(raw_path), "provider": metadata["source"], "source_organization": metadata["source_organization"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", choices=tuple(load_market_assets()), action="append")
    args = parser.parse_args()
    try:
        for series in dict.fromkeys(args.asset or load_market_assets()):
            print(json.dumps(ingest_market_asset(series)), flush=True)
        return 0
    except Exception:
        # Existing HTTP exceptions can contain request URLs with keys.
        print("Market refresh failed; check configuration, source availability, and local raw responses.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
