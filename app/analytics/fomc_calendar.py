"""Stored official FOMC schedules. Rendering never contacts the Federal Reserve."""
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FEDWATCH_URL = "https://www.cmegroup.com/fedwatch"
SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "data/derived/fomc_calendar_v1.json"
logger = logging.getLogger(__name__)


def read_schedule(path=None):
    try:
        data = json.loads(Path(path or SNAPSHOT_PATH).read_text(encoding="utf-8"))
        if data["version"] != 1 or not data["events"]:
            raise ValueError("Empty or unsupported FOMC schedule")
        datetime.fromisoformat(data["retrieved_at"])
        for event in data["events"]:
            date.fromisoformat(event["release_date"])
            if event["source_link"] != SOURCE_URL or event["release_id"] is not None:
                raise ValueError("Invalid FOMC provenance")
        return {"status": "available", **data}
    except FileNotFoundError:
        return {"status": "not_synced", "events": [], "retrieved_at": None, "source_url": SOURCE_URL}
    except (OSError, ValueError, KeyError, TypeError):
        logger.warning("Stored FOMC schedule is unreadable; refresh the official calendar.")
        return {"status": "unavailable", "events": [], "retrieved_at": None, "source_url": SOURCE_URL}


def policy_outlook(now):
    schedule = read_schedule()
    eastern_day = now.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    future = [event for event in schedule["events"] if event.get('event_type') == 'fomc_decision' and event["release_date"] >= eastern_day
              and (not event["release_datetime_utc"] or datetime.fromisoformat(event["release_datetime_utc"]) > now)]
    next_event = min(future, key=lambda event: event["release_date"], default=None)
    return {"schedule_status": schedule["status"] if next_event or not schedule["events"] else "exhausted",
            "retrieved_at": schedule["retrieved_at"], "source_url": SOURCE_URL,
            "next_decision": next_event,
            "market_probabilities": {"status": "not_integrated", "source_url": FEDWATCH_URL}}
