"""Compatibility wrapper for UNRATE ingestion."""

import sys

from app.ingestion.ingest_series import ingest_series


SERIES_ID = "UNRATE"


def main() -> int:
    try:
        ingest_series(SERIES_ID)
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())
