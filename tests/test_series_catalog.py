from fastapi.testclient import TestClient
import pytest

from app.analytics import series_catalog
from app.api import main as api_main


SERIES_ROW = (
    "UNRATE", "Unemployment Rate", "Unemployment Rate", "labor", "monthly", "percent"
)


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.query = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params):
        self.query = query
        self.params = params

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConnection:
    def __init__(self, rows):
        self.cursor_instance = FakeCursor(rows)
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def close(self):
        self.closed = True


def test_catalog_lists_only_active_configured_series(monkeypatch):
    connection = FakeConnection([SERIES_ROW])
    monkeypatch.setattr(series_catalog, "get_connection", lambda: connection)

    result = series_catalog.list_active_series()

    assert result == {"series": [{
        "series_id": "UNRATE", "name": "Unemployment Rate",
        "short_name": "Unemployment Rate", "category": "labor",
        "frequency": "monthly", "unit": "percent",
    }]}
    assert "active = TRUE" in connection.cursor_instance.query
    assert "series_id = ANY(%s)" in connection.cursor_instance.query
    assert "UNRATE" in connection.cursor_instance.params[0]
    assert connection.closed


def test_known_series_detail_and_unknown_or_inactive_series(monkeypatch):
    connection = FakeConnection([SERIES_ROW])
    monkeypatch.setattr(series_catalog, "get_connection", lambda: connection)
    assert series_catalog.get_active_series("UNRATE")["unit"] == "percent"
    assert "active = TRUE" in connection.cursor_instance.query

    monkeypatch.setattr(series_catalog, "get_connection", lambda: FakeConnection([]))
    with pytest.raises(series_catalog.UnknownCatalogSeriesError):
        series_catalog.get_active_series("UNRATE")
    with pytest.raises(series_catalog.UnknownCatalogSeriesError):
        series_catalog.get_active_series("NOT_CONFIGURED")


def test_available_features_are_configured_supported_and_stored(monkeypatch):
    connections = iter([FakeConnection([SERIES_ROW]), FakeConnection([
        ("yoy",), ("level",), ("unsupported",),
    ])])
    monkeypatch.setattr(series_catalog, "get_connection", lambda: next(connections))

    result = series_catalog.list_available_features("UNRATE")

    assert result == {
        "series_id": "UNRATE", "methodology_version": "v1",
        "features": ["level"],
    }


def test_catalog_api_routes_and_history_regression(monkeypatch):
    client = TestClient(api_main.app)
    metadata = dict(zip(series_catalog.SERIES_FIELDS, SERIES_ROW))
    monkeypatch.setattr(api_main.series_catalog, "list_active_series", lambda: {"series": [metadata]})
    monkeypatch.setattr(api_main.series_catalog, "get_active_series", lambda series_id: metadata if series_id == "UNRATE" else (_ for _ in ()).throw(series_catalog.UnknownCatalogSeriesError("Unknown series")))
    def features(series_id):
        if series_id != "UNRATE":
            raise series_catalog.UnknownCatalogSeriesError("Unknown series")
        return {"series_id": series_id, "methodology_version": "v1", "features": ["level"]}
    monkeypatch.setattr(api_main.series_catalog, "list_available_features", features)
    monkeypatch.setattr(api_main.history, "load_series_history", lambda series_id, start_date, end_date: {"series_id": series_id, "history_type": "current_vintage", "observations": []})

    assert client.get("/api/v1/series").json() == {"series": [metadata]}
    assert client.get("/api/v1/series/UNRATE").json() == metadata
    assert client.get("/api/v1/series/UNRATE/features").json()["features"] == ["level"]
    assert client.get("/api/v1/series/UNKNOWN").status_code == 404
    assert client.get("/api/v1/series/UNKNOWN/features").status_code == 404
    assert client.get("/api/v1/series/UNRATE/history").json()["history_type"] == "current_vintage"


def test_catalog_api_hides_internal_errors(monkeypatch):
    client = TestClient(api_main.app)
    def fail():
        raise RuntimeError("SELECT secret FROM series password=secret")
    monkeypatch.setattr(api_main.series_catalog, "list_active_series", fail)
    response = client.get("/api/v1/series")
    assert response.status_code == 503
    assert "SELECT" not in response.text
    assert "password" not in response.text
