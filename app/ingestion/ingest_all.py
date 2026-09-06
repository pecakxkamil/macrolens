"""Run FRED ingestion for every configured series."""

import sys
from pathlib import Path

import yaml

from app.ingestion.ingest_series import ingest_series


CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "series.yaml"


def _load_series_ids() -> list:
    if not CONFIG_PATH.exists():
        raise RuntimeError(f"Series config not found: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    if not isinstance(config, dict) or not config:
        raise RuntimeError("Series config must contain at least one series entry.")

    return list(config.keys())


def main() -> int:
    successful_series = []
    failed_series = []

    try:
        series_ids = _load_series_ids()
    except Exception as error:
        print(f"Batch ingestion failed: {error}", file=sys.stderr)
        return 1

    for series_id in series_ids:
        print(f"Processing series: {series_id}")
        try:
            ingest_series(series_id)
            successful_series.append(series_id)
        except Exception as error:
            failed_series.append((series_id, str(error)))

    print("Batch ingestion completed.")
    print(f"Successful: {len(successful_series)}")
    print(f"Failed: {len(failed_series)}")

    print("Successful series:")
    for series_id in successful_series:
        print(f"- {series_id}")

    print("Failed series:")
    for series_id, error_message in failed_series:
        print(f"- {series_id}: {error_message}")

    return 1 if failed_series else 0


if __name__ == "__main__":
    sys.exit(main())
