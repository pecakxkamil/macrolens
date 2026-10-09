"""Separate idempotent ALFRED backfill for the 15 explicit MCI series."""

import argparse
import json
import sys
from datetime import date

from app.analytics.macro_conditions_index import COMPONENTS
from app.database.connection import get_connection
from app.database.sync_series import load_series_config
from app.ingestion import alfred

MCI_SERIES = tuple(dict.fromkeys(item.series_id for item in COMPONENTS))
STAGE_SQL = """
CREATE TEMP TABLE alfred_stage (
    series_id VARCHAR, observation_date DATE, vintage_date DATE,
    value NUMERIC, realtime_end DATE,
    PRIMARY KEY (series_id, observation_date, vintage_date)
) ON COMMIT DROP;
"""
CONFLICT_SQL = """
SELECT COUNT(*) FROM alfred_stage s JOIN observation_vintages o
USING (series_id, observation_date, vintage_date)
WHERE o.source = 'alfred' AND o.value IS DISTINCT FROM s.value;
"""
MERGE_SQL = """
INSERT INTO observation_vintages (series_id, observation_date, vintage_date, value, realtime_end, source)
SELECT series_id, observation_date, vintage_date, value, realtime_end, 'alfred' FROM alfred_stage
ON CONFLICT (series_id, observation_date, vintage_date) DO UPDATE SET
    value = EXCLUDED.value, source = 'alfred',
    realtime_end = GREATEST(observation_vintages.realtime_end, EXCLUDED.realtime_end),
    ingested_at = CURRENT_TIMESTAMP
WHERE observation_vintages.source != 'alfred'
   OR observation_vintages.realtime_end < EXCLUDED.realtime_end;
"""
COVERAGE_SQL = """
INSERT INTO alfred_backfills (series_id, realtime_start, realtime_end, rows_downloaded)
VALUES (%s, %s, %s, %s)
ON CONFLICT (series_id) DO UPDATE SET
    realtime_end = GREATEST(alfred_backfills.realtime_end, EXCLUDED.realtime_end),
    rows_downloaded = EXCLUDED.rows_downloaded, completed_at = CURRENT_TIMESTAMP;
"""


def backfill_series(series_id: str, cutoff: date) -> dict:
    if series_id not in MCI_SERIES or series_id not in load_series_config():
        raise ValueError("Backfill supports configured MCI component series only.")
    if not alfred.EARLIEST_REALTIME <= cutoff <= date.today():
        raise ValueError("Backfill end_date must be between 1776-07-04 and today.")
    connection = get_connection()
    received = changed = offset = 0
    expected_count = None
    try:
        with connection.cursor() as cursor:
            cursor.execute(STAGE_SQL)
            for payload in alfred.iter_vintage_pages(series_id, cutoff):
                rows = alfred.parse_vintage_page(series_id, payload, cutoff, offset)
                count = payload["count"]
                if expected_count is not None and count != expected_count:
                    raise RuntimeError("ALFRED pagination changed; retry the backfill.")
                expected_count = count
                if not rows and offset < count:
                    raise RuntimeError("ALFRED pagination ended before all rows were received.")
                cursor.execute("TRUNCATE alfred_stage")
                with cursor.copy("COPY alfred_stage (series_id, observation_date, vintage_date, value, realtime_end) FROM STDIN") as copy:
                    for row in rows:
                        copy.write_row(row)
                cursor.execute(CONFLICT_SQL)
                if cursor.fetchone()[0]:
                    raise RuntimeError("An existing ALFRED vintage changed value; immutable history was preserved. Inspect raw files.")
                cursor.execute(MERGE_SQL)
                changed += cursor.rowcount
                received += len(rows)
                offset += len(rows)
                print(json.dumps({"series_id": series_id, "downloaded": offset, "expected": count}), flush=True)
            if offset != expected_count:
                raise RuntimeError("ALFRED pagination did not receive the complete series.")
            cursor.execute(COVERAGE_SQL, (series_id, alfred.EARLIEST_REALTIME, cutoff, received))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {"series_id": series_id, "rows_downloaded": received, "rows_inserted_or_promoted": changed,
            "backfilled_through": str(cutoff)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--series", choices=MCI_SERIES, action="append", help="Repeat to select MCI series; default is all 15.")
    parser.add_argument("--end-date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    summaries = []
    try:
        for series_id in dict.fromkeys(args.series or MCI_SERIES):
            summary = backfill_series(series_id, args.end_date)
            summaries.append(summary)
            print(json.dumps(summary), flush=True)
        print(json.dumps({"total_rows_downloaded": sum(item["rows_downloaded"] for item in summaries)}))
        return 0
    except Exception as error:
        print(f"ALFRED backfill failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

