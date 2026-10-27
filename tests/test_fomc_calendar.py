"""Official schedule parsing and optional stored calendar integration."""
import json
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi.testclient import TestClient

from app.analytics import fomc_calendar as fomc, release_calendar, economy_brief
from app.api.main import app
from app.ingestion.sync_fomc_calendar import make_event, parse_meetings, parse_decision_time, sync_schedule


def schedule_html(month="October", days="27-28", year=2026):
    return f'<div class="panel panel-default"><h4>{year} FOMC Meetings</h4><div class="row fomc-meeting" "><div class="fomc-meeting__month"><strong>{month}</strong></div><div class="fomc-meeting__date">{days}</div><p>Press Conference</p></div></div>'


def monthly_html(clock="2:00 p.m.", description="FOMC Meeting", day=28):
    return f'<h4>October 2026</h4><div class="row"><div><p>{clock}</p></div><div><p>{description}</p><p>Two-day meeting, October&nbsp;27 - 28</p></div><div>{day}</div></div>'


@pytest.mark.parametrize("month,days,start,end", [
    ("October", "27-28*", "2026-10-27", "2026-10-28"),
    ("Apr/May", "30-1", "2026-04-30", "2026-05-01"),
    ("December", "9", "2026-12-09", "2026-12-09"),
])
def test_final_meeting_day_is_decision_day(month, days, start, end):
    assert parse_meetings(schedule_html(month, days), 2026) == [(date.fromisoformat(start), date.fromisoformat(end))]


def test_schedule_ignores_older_years_and_fails_closed_on_changed_markup():
    html = schedule_html(year=2025) + schedule_html()
    assert len(parse_meetings(html, 2026)) == 1
    with pytest.raises(ValueError):
        parse_meetings(schedule_html(days="TBD"), 2026)
    with pytest.raises(ValueError):
        parse_meetings("<h4>No schedule</h4>", 2026)


@pytest.mark.parametrize("html,expected", [
    (monthly_html(), "14:00:00"),
    (monthly_html(description="FOMC Minutes"), None),
    (monthly_html(description="FOMC Meeting Press Conference"), None),
    (monthly_html(day=27), None), (monthly_html(clock="TBA"), None),
    (monthly_html().replace("October 2026", "November 2026"), None),
    (monthly_html() + monthly_html(), None),
])
def test_only_explicit_unambiguous_decision_time_is_used(html, expected):
    assert parse_decision_time(html, date(2026, 10, 28)) == expected


@pytest.mark.parametrize("day,warsaw", [("2026-10-28", "19:00"), ("2026-12-09", "20:00"), ("2026-03-18", "19:00")])
def test_source_timezone_handles_transatlantic_dst_difference(day, warsaw):
    end = date.fromisoformat(day)
    event = make_event(end, end, "14:00:00", "2026-10-19T12:00:00+00:00", "https://www.federalreserve.gov/")
    assert event["source_timezone"] == "America/New_York"
    assert datetime.fromisoformat(event["release_datetime_utc"]).astimezone(ZoneInfo("Europe/Warsaw")).strftime("%H:%M") == warsaw
    unknown = make_event(end, end, None, "2026-10-19T12:00:00+00:00")
    assert unknown["release_time"] is unknown["source_timezone"] is unknown["release_datetime_utc"] is None


def test_refresh_is_durable_repeatable_and_failed_refresh_keeps_last_schedule(tmp_path):
    path = tmp_path / "derived/fomc.json"
    now = datetime(2026, 10, 19, tzinfo=timezone.utc)
    def respond(request):
        return httpx.Response(200, text=schedule_html() if str(request.url) == fomc.SOURCE_URL else monthly_html())
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        first = sync_schedule(client, path, tmp_path / "raw", now)
        assert sync_schedule(client, path, tmp_path / "raw", now) == first
    assert len(first["events"]) == 1
    assert len(list((tmp_path / "raw").glob("*/*.htm.json"))) == 4
    assert fomc.read_schedule(path)["status"] == "available"
    original = path.read_bytes()
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text="No calendar"))) as client:
        with pytest.raises(ValueError):
            sync_schedule(client, path, tmp_path / "raw", now)
    assert path.read_bytes() == original


def test_missing_monthly_page_does_not_invent_time(tmp_path):
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=schedule_html()) if str(request.url) == fomc.SOURCE_URL else httpx.Response(404))) as client:
        payload = sync_schedule(client, tmp_path / "derived/fomc.json", tmp_path / "raw", datetime(2026, 10, 19, tzinfo=timezone.utc))
    event = payload["events"][0]
    assert event["release_time"] is event["time_source_url"] is None
    assert event["release_id"] is None and event["event_id"] == "fomc:2026-10-28"


def test_missing_or_corrupt_snapshot_is_optional(tmp_path):
    path = tmp_path / "fomc.json"
    assert fomc.read_schedule(path)["status"] == "not_synced"
    path.write_text("broken", encoding="utf-8")
    assert fomc.read_schedule(path)["status"] == "unavailable"


def test_next_decision_outside_seven_days_and_after_decision_rollover(monkeypatch):
    oct_event = make_event(date(2026, 10, 27), date(2026, 10, 28), "14:00:00", "2026-10-19T12:00:00+00:00")
    dec_event = make_event(date(2026, 12, 8), date(2026, 12, 9), None, "2026-10-19T12:00:00+00:00")
    monkeypatch.setattr(fomc, "read_schedule", lambda: {"status": "available", "events": [oct_event, dec_event], "retrieved_at": oct_event["retrieved_at"]})
    assert fomc.policy_outlook(datetime(2026, 10, 19, tzinfo=timezone.utc))["next_decision"] == oct_event
    assert fomc.policy_outlook(datetime(2026, 10, 28, 18, tzinfo=timezone.utc))["next_decision"] == dec_event
    result = fomc.policy_outlook(datetime(2026, 12, 10, 12, tzinfo=timezone.utc))
    assert result["next_decision"] is None and result["schedule_status"] == "exhausted"
    assert result["market_probabilities"] == {"status": "not_integrated", "source_url": fomc.FEDWATCH_URL}


def test_calendar_api_merges_policy_without_fake_fred_identifier(monkeypatch):
    from tests.test_release_calendar import FakeConnection, SERIES_CPI
    event = make_event(date(2026, 10, 27), date(2026, 10, 28), "14:00:00", "2026-10-19T12:00:00+00:00")
    policy = {"status": "available", "events": [event], "retrieved_at": event["retrieved_at"], "source_url": fomc.SOURCE_URL}
    monkeypatch.setattr(release_calendar, "read_schedule", lambda: policy)
    monkeypatch.setattr(release_calendar, "get_connection", lambda: FakeConnection([[(date(2026, 10, 28), 10, "Consumer Price Index", None, *SERIES_CPI)]]))
    client = TestClient(app)
    response = client.get("/api/v1/calendar?start_date=2026-10-26&end_date=2026-11-01")
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == 2 and events[0]["release_id"] == 10
    assert events[1]["event_id"] == "fomc:2026-10-28" and events[1]["release_id"] is None
    assert events[1]["series"] == [] and events[1]["retrieved_at"] == event["retrieved_at"]
    assert len(client.get("/api/v1/calendar?start_date=2026-10-26&end_date=2026-11-01&category=inflation").json()["events"]) == 1
    assert len(client.get("/api/v1/calendar?start_date=2026-10-26&end_date=2026-11-01&category=financial_conditions").json()["events"]) == 1


def test_optional_policy_failure_does_not_block_existing_brief(monkeypatch):
    from tests.test_economy_brief import stub_sections
    from pathlib import Path
    snapshot = json.loads((Path(__file__).parent / "fixtures/macro_state_snapshot.json").read_text(encoding="utf-8"))
    stub_sections(monkeypatch, snapshot)
    monkeypatch.setattr(economy_brief, "policy_outlook", lambda now: (_ for _ in ()).throw(OSError("unavailable")))
    result = economy_brief.build_brief(datetime(2026, 10, 19, tzinfo=timezone.utc))
    assert result["policy"]["status"] == "unavailable"
    assert all(result[key]["status"] == "ready" for key in ("snapshot", "state", "calendar", "changes"))


@pytest.fixture(autouse=True)
def isolate_availability_provenance(monkeypatch):
    # These ingestion tests must never write to a configured local database.
    from app import source_checks
    monkeypatch.setattr(source_checks, "write_run", lambda run: None)
