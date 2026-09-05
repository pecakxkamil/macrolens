"""Sync configured economic series into PostgreSQL."""

import sys
from pathlib import Path

import yaml

from app.database.connection import get_connection


CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "series.yaml"
REQUIRED_FIELDS = (
    "name",
    "short_name",
    "category",
    "frequency",
    "unit",
    "revision_tracking",
)

UPSERT_SERIES_SQL = """
INSERT INTO series (
    series_id,
    name,
    short_name,
    category,
    frequency,
    unit,
    revision_tracking,
    active
) VALUES (
    %(series_id)s,
    %(name)s,
    %(short_name)s,
    %(category)s,
    %(frequency)s,
    %(unit)s,
    %(revision_tracking)s,
    TRUE
)
ON CONFLICT (series_id) DO UPDATE SET
    name = EXCLUDED.name,
    short_name = EXCLUDED.short_name,
    category = EXCLUDED.category,
    frequency = EXCLUDED.frequency,
    unit = EXCLUDED.unit,
    revision_tracking = EXCLUDED.revision_tracking,
    active = TRUE;
"""


def load_series_config() -> dict:
    if not CONFIG_PATH.exists():
        raise RuntimeError(f"Series config not found: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    if not isinstance(config, dict) or not config:
        raise RuntimeError("Series config must contain at least one series entry.")

    for series_id, metadata in config.items():
        if not isinstance(series_id, str) or not series_id.strip():
            raise RuntimeError("Series config contains an invalid series id.")
        if not isinstance(metadata, dict):
            raise RuntimeError(f"Series {series_id} must be a mapping.")

        missing = [
            field
            for field in REQUIRED_FIELDS
            if field not in metadata or metadata[field] is None
        ]
        if missing:
            fields = ", ".join(missing)
            raise RuntimeError(f"Series {series_id} is missing required fields: {fields}")

    return config


def main() -> int:
    connection = None

    try:
        series_config = load_series_config()
        connection = get_connection()

        with connection.cursor() as cursor:
            for series_id, metadata in series_config.items():
                cursor.execute(
                    UPSERT_SERIES_SQL,
                    {
                        "series_id": series_id,
                        "name": metadata["name"],
                        "short_name": metadata["short_name"],
                        "category": metadata["category"],
                        "frequency": metadata["frequency"],
                        "unit": metadata["unit"],
                        "revision_tracking": metadata["revision_tracking"],
                    },
                )

        connection.commit()
        print(f"Synced {len(series_config)} series successfully.")
        return 0
    except Exception as error:
        if connection is not None:
            connection.rollback()
        print(f"Series sync failed: {error}", file=sys.stderr)
        return 1
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    sys.exit(main())
