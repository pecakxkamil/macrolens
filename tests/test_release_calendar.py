from datetime import date

from fastapi.testclient import TestClient
import pytest

from app.analytics import release_calendar
from app.analytics.release_times import release_time_metadata
from app.api import main as api_main


SERIES_CPI = ("CPIAUCSL", "Consumer Price Index", "CPI", "inflation", "monthly", "index")
SERIES_CORE = ("CPILFESL", "Core Consumer Price Index", "Core CPI", "inflation", "monthly", "index")
SERIES_PAYROLL = ("PAYEMS", "Nonfarm Payrolls", "Nonfarm Payrolls", "labor", "monthly", "thousands of persons")


class FakeCursor:
    def __init__(self, responses):
        self.responses = list(responses)
        self.query = None
        self.params = None
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params):
        self.query = query
        self.params = params
        self.calls.append((query, params))

    def fetchall(self):
        return self.responses.pop(0)


class FakeConnection:
    def __init__(self, responses):
        self.cursor_instance = FakeCursor(responses)
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def close(self):
        self.closed = True


def event_rows():
    return [
        (date(2026, 9, 28), 10, "Consumer Price Index", "https://www.bls.gov/cpi/", *SERIES_CPI),
        (date(2026, 9, 28), 10, "Consumer Price Index", "https://www.bls.gov/cpi/", *SERIES_CORE),
        (date(2026, 9, 29), 20, "Employment Situation", None, *SERIES_PAYROLL),
    ]


@pytest.mark.parametrize(("name", "expected"), [
    ("Employment Situation", "high"),
    ("Consumer Price Index", "high"),
    ("Personal Income and Outlays", "high"),
    ("Gross Domestic Product", "high"),
    ("Unemployment Insurance Weekly Claims Report", "high"),
    ("Job Openings and Labor Turnover Survey", "medium"),
    ("Industrial Production and Capacity Utilization", "medium"),
    ("Advance Monthly Sales for Retail and Food Services", "medium"),
    ("New Residential Construction", "medium"),
    ("New Residential Sales", "medium"),
    ("Chicago Fed National Financial Conditions Index", "medium"),
    ("H.15 Selected Interest Rates", "low"),
    ("Unknown Release", "medium"),
])
def test_release_importance_mapping(name, expected):
    assert release_calendar.release_importance(name) == expected


@pytest.mark.parametrize(("name", "expected_time"), [
    ("Employment Situation", "08:30:00"),
    ("Consumer Price Index", "08:30:00"),
    ("Job Openings and Labor Turnover Survey", "10:00:00"),
    ("Gross Domestic Product", "08:30:00"),
    ("Personal Income and Outlays", "08:30:00"),
    ("New Residential Construction", "08:30:00"),
    ("New Residential Sales", "10:00:00"),
])
def test_official_release_time_mapping(name, expected_time):
    metadata = release_time_metadata(name, date(2026, 9, 30))
    assert metadata["release_time"] == expected_time
    assert metadata["source_timezone"] == "America/New_York"


def test_unknown_release_has_no_fabricated_time():
    assert release_time_metadata("Unknown Release", date(2026, 9, 30)) == {
        "release_time": None,
        "source_timezone": None,
        "release_datetime_utc": None,
    }


def test_release_utc_instant_uses_new_york_dst_rules():
    summer = release_time_metadata("Gross Domestic Product", date(2026, 9, 30))
    us_dst_before_poland = release_time_metadata("Personal Income and Outlays", date(2026, 3, 13))
    assert summer["release_datetime_utc"] == "2026-09-30T12:30:00Z"
    assert us_dst_before_poland["release_datetime_utc"] == "2026-03-13T12:30:00Z"
    assert release_time_metadata("Consumer Price Index", date(2026, 1, 15))["release_datetime_utc"] == "2026-01-15T13:30:00Z"


def test_calendar_groups_series_once_orders_dates_and_filters(monkeypatch):
    connection = FakeConnection([event_rows()])
    monkeypatch.setattr(release_calendar, "get_connection", lambda: connection)
    start, end = date(2026, 9, 28), date(2026, 10, 4)

    result = release_calendar.list_calendar_events(start, end)

    assert result["start_date"] == start
    assert result["end_date"] == end
    assert len(result["events"]) == 2
    assert [event["release_date"] for event in result["events"]] == [date(2026, 9, 28), date(2026, 9, 29)]
    assert result["events"][0]["date_precision"] == "date"
    assert result["events"][0]["release_time"] == "08:30:00"
    assert result["events"][0]["source_timezone"] == "America/New_York"
    assert [event["importance"] for event in result["events"]] == ["high", "high"]
    assert [series["series_id"] for series in result["events"][0]["series"]] == ["CPIAUCSL", "CPILFESL"]
    assert connection.cursor_instance.params[:2] == (start, end)
    assert "s.active = TRUE" in connection.cursor_instance.query
    assert "s.series_id = ANY(%s)" in connection.cursor_instance.query
    assert connection.closed

    monkeypatch.setattr(release_calendar, "get_connection", lambda: FakeConnection([event_rows()]))
    inflation = release_calendar.list_calendar_events(start, end, "inflation")
    assert len(inflation["events"]) == 1
    assert len(inflation["events"][0]["series"]) == 2


def test_calendar_sorts_importance_within_each_day(monkeypatch):
    day = date(2026, 9, 28)
    rows = [
        (day, 1, "H.15 Selected Interest Rates", None, *SERIES_CPI),
        (day, 2, "Unknown Release", None, *SERIES_CPI),
        (day, 3, "Consumer Price Index", None, *SERIES_CPI),
    ]
    monkeypatch.setattr(release_calendar, "get_connection", lambda: FakeConnection([rows]))
    result = release_calendar.list_calendar_events(day, day)
    assert [(event["release_name"], event["importance"]) for event in result["events"]] == [
        ("Consumer Price Index", "high"),
        ("Unknown Release", "medium"),
        ("H.15 Selected Interest Rates", "low"),
    ]


def test_category_filter_matches_any_linked_category_without_duplicate(monkeypatch):
    rows = [
        (date(2026, 9, 28), 10, "Combined Release", None, *SERIES_CPI),
        (date(2026, 9, 28), 10, "Combined Release", None, *SERIES_PAYROLL),
    ]
    monkeypatch.setattr(release_calendar, "get_connection", lambda: FakeConnection([rows]))
    result = release_calendar.list_calendar_events(date(2026, 9, 28), date(2026, 9, 28), "labor")
    assert len(result["events"]) == 1
    assert {item["category"] for item in result["events"][0]["series"]} == {"inflation", "labor"}


def test_invalid_date_range_and_category_do_not_access_database(monkeypatch):
    monkeypatch.setattr(release_calendar, "get_connection", lambda: pytest.fail("database should not be accessed"))
    with pytest.raises(release_calendar.InvalidCalendarRangeError):
        release_calendar.list_calendar_events(date(2026, 10, 1), date(2026, 9, 1))
    with pytest.raises(release_calendar.InvalidCalendarCategoryError):
        release_calendar.list_calendar_events(date(2026, 9, 1), date(2026, 10, 1), "unknown")


def test_release_detail_uses_active_configured_series_and_unknown_is_rejected(monkeypatch):
    rows = [
        (10, "Consumer Price Index", "https://www.bls.gov/cpi/", True, *SERIES_CPI),
        (10, "Consumer Price Index", "https://www.bls.gov/cpi/", True, *SERIES_CORE),
    ]
    connection = FakeConnection([rows, [(date(2026, 9, 28),)]])
    monkeypatch.setattr(release_calendar, "get_connection", lambda: connection)
    detail = release_calendar.get_release_detail(10)
    assert detail["release_name"] == "Consumer Price Index"
    assert len(detail["series"]) == 2
    assert detail["recent_dates"] == [date(2026, 9, 28)]
    assert "s.active = TRUE" in connection.cursor_instance.calls[0][0]
    assert "s.series_id = ANY(%s)" in connection.cursor_instance.calls[0][0]
    monkeypatch.setattr(release_calendar, "get_connection", lambda: FakeConnection([[]]))
    with pytest.raises(release_calendar.UnknownReleaseError):
        release_calendar.get_release_detail(999)


def test_calendar_api_serialization_validation_and_existing_health(monkeypatch):
    client = TestClient(api_main.app)
    def fake_list(start_date, end_date, category):
        assert start_date == date(2026, 9, 28)
        assert end_date == date(2026, 10, 4)
        assert category == "inflation"
        return {"start_date": start_date, "end_date": end_date, "category": category, "events": [{
            "release_id": 10, "release_name": "Consumer Price Index", "release_date": start_date,
            "date_precision": "date", "importance": "high", "source_link": None,
            "series": [dict(zip(("series_id", "name", "short_name", "category", "frequency", "unit"), SERIES_CPI))],
        }]}
    monkeypatch.setattr(api_main.release_calendar, "list_calendar_events", fake_list)
    response = client.get("/api/v1/calendar", params={
        "start_date": "2026-09-28", "end_date": "2026-10-04", "category": "inflation",
    })
    assert response.status_code == 200
    assert response.json()["events"][0]["release_date"] == "2026-09-28"
    assert response.json()["events"][0]["importance"] == "high"
    assert response.json()["start_date"] == "2026-09-28"
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/v1/calendar?start_date=invalid").status_code == 422


def test_calendar_api_response_includes_mapped_importance(monkeypatch):
    day = date(2026, 9, 28)
    rows = [
        (day, 1, "H.15 Selected Interest Rates", None, *SERIES_CPI),
        (day, 2, "Unlisted Release", None, *SERIES_CPI),
        (day, 3, "Consumer Price Index", None, *SERIES_CPI),
    ]
    monkeypatch.setattr(release_calendar, "get_connection", lambda: FakeConnection([rows]))
    response = TestClient(api_main.app).get("/api/v1/calendar", params={
        "start_date": "2026-09-28", "end_date": "2026-09-28",
    })
    assert response.status_code == 200
    assert [(event["release_name"], event["importance"]) for event in response.json()["events"]] == [
        ("Consumer Price Index", "high"),
        ("Unlisted Release", "medium"),
        ("H.15 Selected Interest Rates", "low"),
    ]
    known, unknown, unsupported = response.json()["events"]
    assert known["release_date"] == "2026-09-28"
    assert known["release_time"] == "08:30:00"
    assert known["source_timezone"] == "America/New_York"
    assert known["release_datetime_utc"] == "2026-09-28T12:30:00Z"
    for event in (unknown, unsupported):
        assert event["release_date"] == "2026-09-28"
        assert event["release_time"] is None
        assert event["source_timezone"] is None
        assert event["release_datetime_utc"] is None


def test_calendar_api_clean_errors_and_release_detail(monkeypatch):
    client = TestClient(api_main.app)
    def invalid(*args):
        raise release_calendar.InvalidCalendarRangeError("start_date must be on or before end_date.")
    monkeypatch.setattr(api_main.release_calendar, "list_calendar_events", invalid)
    assert client.get("/api/v1/calendar").status_code == 400

    def missing(*args):
        raise release_calendar.UnknownReleaseError("Unknown release: 999")
    monkeypatch.setattr(api_main.release_calendar, "get_release_detail", missing)
    assert client.get("/api/v1/releases/999").status_code == 404

    monkeypatch.setattr(api_main.release_calendar, "get_release_detail", lambda release_id: {
        "release_id": release_id, "release_name": "Employment Situation",
        "source_link": None, "series": [], "recent_dates": [date(2026, 9, 28)],
    })
    assert client.get("/api/v1/releases/10").json()["recent_dates"] == ["2026-09-28"]

    def fail(*args):
        raise RuntimeError("SELECT secret FROM release_dates password=secret")
    monkeypatch.setattr(api_main.release_calendar, "get_release_detail", fail)
    response = client.get("/api/v1/releases/10")
    assert response.status_code == 503
    assert "SELECT" not in response.text and "password" not in response.text
