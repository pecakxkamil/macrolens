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


def test_yield_curve_history_uses_same_date_current_values_and_date_filters(monkeypatch):
    connection = FakeConnection([
        (date(2026, 1, 2), Decimal("0.32")),
        (date(2026, 1, 5), Decimal("-0.10")),
    ])
    monkeypatch.setattr(history, "get_connection", lambda: connection)
    start, end = date(2026, 1, 1), date(2026, 1, 31)

    result = history.load_yield_curve_2s10s_history(start, end)

    assert result["history_type"] == "current_vintage"
    assert result["start_date"] == start
    assert result["end_date"] == end
    assert result["observations"] == [
        {"observation_date": date(2026, 1, 2), "value": Decimal("0.32")},
        {"observation_date": date(2026, 1, 5), "value": Decimal("-0.10")},
    ]
    query = connection.cursor_instance.query
    assert "DISTINCT ON (series_id, observation_date)" in query
    assert "vintage_date DESC" in query
    assert "ten.observation_date = two.observation_date" in query
    assert "ten.value - two.value" in query
    assert "ten.value IS NOT NULL AND two.value IS NOT NULL" in query
    assert "ORDER BY ten.observation_date ASC" in query
    assert "JOIN current_yields" in query and "LEFT JOIN" not in query
    assert connection.cursor_instance.params == (start, start, end, end)
    assert connection.closed


def test_yield_curve_reversed_date_range_does_not_access_database(monkeypatch):
    monkeypatch.setattr(history, "get_connection", lambda: pytest.fail("database should not be accessed"))
    with pytest.raises(history.InvalidDateRangeError):
        history.load_yield_curve_2s10s_history(date(2026, 2, 1), date(2026, 1, 1))
