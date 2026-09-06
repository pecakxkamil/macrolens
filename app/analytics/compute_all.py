"""Run feature computation for every configured series."""

import sys
from datetime import date
from typing import Optional

from app.analytics.compute_features import (
    _load_series_config,
    _parse_as_of_date,
    compute_features,
)


def compute_all(as_of_date: Optional[date] = None) -> dict:
    """Compute configured features for all configured series."""
    successful_series = []
    failed_series = []

    config = _load_series_config()

    for series_id in config.keys():
        print(f"Processing series: {series_id}")
        try:
            compute_features(series_id, as_of_date)
        except Exception as error:
            failed_series.append((series_id, str(error)))
        else:
            successful_series.append(series_id)

    print("Batch feature computation completed.")
    print(f"Successful: {len(successful_series)}")
    print(f"Failed: {len(failed_series)}")

    print("Successful series:")
    for series_id in successful_series:
        print(f"- {series_id}")

    if failed_series:
        print("Failed series:")
        for series_id, error_message in failed_series:
            print(f"- {series_id}: {error_message}")

    return {
        "successful_series": successful_series,
        "failed_series": failed_series,
    }


def main() -> int:
    if len(sys.argv) not in (1, 2):
        print(
            "Usage: python -m app.analytics.compute_all [AS_OF_DATE]",
            file=sys.stderr,
        )
        return 1

    try:
        as_of_date = _parse_as_of_date(sys.argv[1]) if len(sys.argv) == 2 else None
    except Exception as error:
        print(f"Batch feature computation failed: {error}", file=sys.stderr)
        return 1

    try:
        summary = compute_all(as_of_date)
    except Exception as error:
        print(f"Batch feature computation failed: {error}", file=sys.stderr)
        return 1

    return 1 if summary["failed_series"] else 0


if __name__ == "__main__":
    sys.exit(main())
