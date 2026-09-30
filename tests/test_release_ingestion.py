from datetime import date, timedelta
from pathlib import Path

import pytest

from app.ingestion import fred_releases, release_raw_storage, sync_release_calendar


def release_payload():
    return {"releases": [{
        "id": 10, "name": "Consumer Price Index", "link": "https://www.bls.gov/cpi/",
        "press_release": True,
    }]}


def dates_payload(today):
    return {"count": 2, "offset": 0, "limit": 1000, "release_dates": [
        {"release_id": 10, "date": (today + timedelta(days=7)).isoformat(), "release_last_updated": None},
        {"release_id": 10, "date": (today - timedelta(days=7)).isoformat(), "release_last_updated": "2026-09-20 09:00:00-05"},
    ]}


def test_fred_release_mapping_and_future_dates_parse_without_invented_times():
    assert fred_releases.parse_series_releases(release_payload()) == [{
        "release_id": 10, "name": "Consumer Price Index",
        "source_link": "https://www.bls.gov/cpi/", "press_release": True,
    }]
    parsed = fred_releases.parse_release_dates(dates_payload(date(2026, 9, 26)), 10)
    assert parsed[0] == {
        "release_id": 10, "release_date": date(2026, 10, 3),
        "release_last_updated": None,
    }
    assert parsed[1]["release_last_updated"] == "2026-09-20 09:00:00-05"
    assert "release_time" not in parsed[0]
    with pytest.raises(ValueError):
        fred_releases.parse_release_dates({"release_dates": [{"release_id": 11, "date": "2026-10-03"}]}, 10)


def test_fred_http_uses_only_relevant_release_endpoints_and_future_flag(monkeypatch):
    calls = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return release_payload()

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        return Response()

    monkeypatch.setenv("FRED_API_KEY", "test-key-not-for-logging")
    monkeypatch.setattr(fred_releases.httpx, "get", fake_get)
    fred_releases.fetch_series_release("CPIAUCSL")
    fred_releases.fetch_release_dates_page(10, 1000)
    assert calls[0][0].endswith("/fred/series/release")
    assert calls[0][1]["series_id"] == "CPIAUCSL"
    assert calls[1][0].endswith("/fred/release/dates")
    assert calls[1][1]["include_release_dates_with_no_data"] == "true"
    assert calls[1][1]["offset"] == 1000


def test_raw_release_responses_are_immutable(tmp_path, monkeypatch):
    monkeypatch.setattr(release_raw_storage, "RAW_RELEASE_ROOT", tmp_path)
    first = release_raw_storage.save_release_response("series_release", "CPIAUCSL", release_payload())
    second = release_raw_storage.save_release_response("series_release", "CPIAUCSL", release_payload())
    assert first != second
    assert first.exists() and second.exists()
    assert len(list(Path(tmp_path).rglob("*.json"))) == 2
    with pytest.raises(ValueError):
        release_raw_storage.save_release_response("series_release", "../escape", {})


class FakeCursor:
    def __init__(self, state):
        self.state = state
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params):
        self.statements.append((query, params))
        if query == sync_release_calendar.UPSERT_RELEASE_SQL:
            self.state["releases"].add(params[0])
        elif query == sync_release_calendar.UPSERT_MAP_SQL:
            self.state["mappings"].add(tuple(params))
        elif query == sync_release_calendar.UPSERT_DATE_SQL:
            self.state["dates"].add((params[0], params[1]))
        elif query == sync_release_calendar.REMOVE_STALE_FUTURE_DATES_SQL:
            release_id, start, end, keep = params
            self.state["dates"] = {
                item for item in self.state["dates"]
                if item[0] != release_id or not (start <= item[1] <= end) or item[1] in keep
            }


class FakeConnection:
    def __init__(self, state):
        self.cursor_instance = FakeCursor(state)
        self.committed = False
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        self.closed = True


def test_sync_deduplicates_shared_release_and_is_idempotent(monkeypatch):
    today = date.today()
    state = {"releases": set(), "mappings": set(), "dates": {(10, today + timedelta(days=14))}}
    connections = []

    def connection():
        item = FakeConnection(state)
        connections.append(item)
        return item

    fetched_ids = []
    monkeypatch.setattr(sync_release_calendar, "active_configured_series_ids", lambda: ["CPIAUCSL", "CPILFESL"])
    monkeypatch.setattr(sync_release_calendar, "fetch_series_release", lambda series_id: fetched_ids.append(series_id) or release_payload())
    monkeypatch.setattr(sync_release_calendar, "fetch_release_dates_page", lambda release_id, offset: dates_payload(today))
    monkeypatch.setattr(sync_release_calendar, "save_release_response", lambda *args: None)
    monkeypatch.setattr(sync_release_calendar, "get_connection", connection)

    first = sync_release_calendar.sync_release_calendar(today - timedelta(days=30), today + timedelta(days=30))
    second = sync_release_calendar.sync_release_calendar(today - timedelta(days=30), today + timedelta(days=30))

    assert first == second == {"series_processed": 2, "releases": 1, "dates_upserted": 2, "future_dates": 1}
    assert fetched_ids == ["CPIAUCSL", "CPILFESL"] * 2
    assert state == {
        "releases": {10},
        "mappings": {("CPIAUCSL", 10), ("CPILFESL", 10)},
        "dates": {(10, today - timedelta(days=7)), (10, today + timedelta(days=7))},
    }
    assert all(connection.committed and connection.closed for connection in connections)
    statements = [query for connection in connections for query, _ in connection.cursor_instance.statements]
    assert sync_release_calendar.UPSERT_RELEASE_SQL in statements
    assert "ON CONFLICT" in sync_release_calendar.UPSERT_RELEASE_SQL
    assert "ON CONFLICT" in sync_release_calendar.UPSERT_MAP_SQL
    assert "ON CONFLICT" in sync_release_calendar.UPSERT_DATE_SQL
    assert sync_release_calendar.REMOVE_STALE_FUTURE_DATES_SQL in statements


def test_only_active_configured_series_are_selected(monkeypatch):
    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query, params):
            assert "active = TRUE" in query
            assert "series_id = ANY(%s)" in query
            assert "CPIAUCSL" in params[0]

        def fetchall(self):
            return [("CPIAUCSL",)]

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            pass

    monkeypatch.setattr(sync_release_calendar, "get_connection", lambda: Connection())
    assert sync_release_calendar.active_configured_series_ids() == ["CPIAUCSL"]


def test_release_date_pagination_stops_at_requested_start(monkeypatch):
    today = date(2026, 9, 26)
    calls = []
    monkeypatch.setattr(sync_release_calendar, "fetch_release_dates_page", lambda release_id, offset: calls.append(offset) or dates_payload(today))
    monkeypatch.setattr(sync_release_calendar, "save_release_response", lambda *args: None)
    result = sync_release_calendar.collect_release_dates(10, today, today + timedelta(days=10))
    assert calls == [0]
    assert [item["release_date"] for item in result] == [today + timedelta(days=7)]


def test_calendar_schema_has_unique_keys_and_no_unverified_event_fields():
    schema = (Path(__file__).parents[1] / "app" / "database" / "schema.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS economic_releases" in schema
    assert "CREATE TABLE IF NOT EXISTS series_release_map" in schema
    assert "CREATE TABLE IF NOT EXISTS release_dates" in schema
    assert "PRIMARY KEY (series_id, release_id)" in schema
    assert "PRIMARY KEY (release_id, release_date)" in schema
    assert "release_time" not in schema
    assert "consensus" not in schema
    assert "surprise" not in schema
