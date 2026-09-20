from datetime import date
from decimal import Decimal

import pytest

from app.analytics import history


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


class FakeConnection:
    def __init__(self, rows):
        self.cursor_instance = FakeCursor(rows)
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def close(self):
        self.closed = True


def test_series_history_returns_ordered_current_vintage_rows(monkeypatch):
    connection = FakeConnection(
        [
            (date(2026, 1, 1), Decimal("4.1")),
            (date(2026, 2, 1), Decimal("4.0")),
        ]
    )
    monkeypatch.setattr(history, "get_connection", lambda: connection)

    result = history.load_series_history("UNRATE")

    assert result["history_type"] == "current_vintage"
    assert result["observations"] == [
        {"observation_date": date(2026, 1, 1), "value": Decimal("4.1")},
        {"observation_date": date(2026, 2, 1), "value": Decimal("4.0")},
    ]
    assert "DISTINCT ON (observation_date)" in connection.cursor_instance.query
    assert "vintage_date DESC" in connection.cursor_instance.query
    assert "ORDER BY observation_date ASC" in connection.cursor_instance.query
    assert connection.closed is True


def test_series_history_passes_date_filters(monkeypatch):
    connection = FakeConnection([])
    monkeypatch.setattr(history, "get_connection", lambda: connection)
    start = date(2025, 1, 1)
    end = date(2025, 12, 31)

    result = history.load_series_history("UNRATE", start, end)

    assert connection.cursor_instance.params == ("UNRATE", start, start, end, end)
    assert result["start_date"] == start
    assert result["end_date"] == end


def test_feature_history_selects_latest_as_of_per_observation(monkeypatch):
    connection = FakeConnection(
        [
            (date(2026, 1, 1), date(2026, 3, 1), Decimal("4.2")),
            (date(2026, 2, 1), date(2026, 3, 1), Decimal("4.0")),
        ]
    )
    monkeypatch.setattr(history, "get_connection", lambda: connection)

    result = history.load_feature_history("UNRATE", "level")

    assert result["feature_name"] == "level"
    assert result["methodology_version"] == "v1"
    assert result["history_type"] == "current_vintage"
    assert result["observations"][0] == {
        "observation_date": date(2026, 1, 1),
        "feature_as_of_date": date(2026, 3, 1),
        "value": Decimal("4.2"),
    }
    assert "DISTINCT ON (observation_date)" in connection.cursor_instance.query
    assert "as_of_date DESC" in connection.cursor_instance.query
    assert "ORDER BY observation_date ASC" in connection.cursor_instance.query


def test_unknown_series_is_rejected_before_database_access(monkeypatch):
    monkeypatch.setattr(
        history,
        "get_connection",
        lambda: pytest.fail("database should not be accessed"),
    )

    with pytest.raises(history.UnknownSeriesError, match="Unknown series"):
        history.load_series_history("NOT_A_SERIES")


def test_unsupported_feature_is_rejected_before_database_access(monkeypatch):
    monkeypatch.setattr(
        history,
        "get_connection",
        lambda: pytest.fail("database should not be accessed"),
    )

    with pytest.raises(history.UnsupportedFeatureError, match="Unsupported feature"):
        history.load_feature_history("UNRATE", "not_a_feature")


def test_reversed_date_range_is_rejected_before_database_access(monkeypatch):
    monkeypatch.setattr(
        history,
        "get_connection",
        lambda: pytest.fail("database should not be accessed"),
    )

    with pytest.raises(history.InvalidDateRangeError, match="start_date"):
        history.load_series_history(
            "UNRATE",
            date(2026, 2, 1),
            date(2026, 1, 1),
        )
