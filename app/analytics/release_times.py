"""Official publication-time conventions for a small set of tracked releases.

FRED supplies release dates, not these times. Confirm a provider's schedule before
adding another name. These conventions may change for an individual release.
"""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo


SOURCE_TIMEZONE = "America/New_York"
EASTERN = ZoneInfo(SOURCE_TIMEZONE)

# BLS: https://www.bls.gov/schedule/2026/home.htm
# BEA: https://www.bea.gov/news/schedule/full
# Census: https://www.census.gov/construction/soc/schedule.html
OFFICIAL_RELEASE_TIMES = {
    "Employment Situation": time(8, 30),
    "Consumer Price Index": time(8, 30),
    "Job Openings and Labor Turnover Survey": time(10, 0),
    "Gross Domestic Product": time(8, 30),
    "Personal Income and Outlays": time(8, 30),
    "New Residential Construction": time(8, 30),
    "New Residential Sales": time(10, 0),
}


def release_time_metadata(name: str, release_date: date) -> dict:
    source_time = OFFICIAL_RELEASE_TIMES.get(name)
    if source_time is None:
        return {
            "release_time": None,
            "source_timezone": None,
            "release_datetime_utc": None,
        }
    source_datetime = datetime.combine(release_date, source_time, tzinfo=EASTERN)
    utc_datetime = source_datetime.astimezone(timezone.utc)
    return {
        "release_time": source_time.isoformat(timespec="seconds"),
        "source_timezone": SOURCE_TIMEZONE,
        "release_datetime_utc": utc_datetime.isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
