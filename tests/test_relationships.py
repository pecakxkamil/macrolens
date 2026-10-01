from datetime import date

from fastapi.testclient import TestClient
import pytest

from app.analytics import history, relationships
from app.api import main as api_main


def make_history(series_id, frequency, observations, feature_name=None):
    return {
        "series_id": series_id,
        "name": series_id,
        "short_name": series_id,
        "frequency": frequency,
        "unit": "percent",
        "history_type": "current_vintage",
        "feature_name": feature_name,
        "observations": [
            {"observation_date": date.fromisoformat(day), "value": value}
            for day, value in observations
        ],
    }


def stub_histories(monkeypatch, payloads):
    calls = []

    def load(series_id, start_date, end_date):
        calls.append((series_id, None, start_date, end_date))
        return payloads[(series_id, None)]

    def load_feature(series_id, feature_name, start_date, end_date):
        calls.append((series_id, feature_name, start_date, end_date))
        return payloads[(series_id, feature_name)]

    monkeypatch.setattr(history, "load_series_history", load)
    monkeypatch.setattr(history, "load_feature_history", load_feature)
    return calls


def test_same_frequency_alignment_uses_latest_observation_per_period(monkeypatch):
    stub_histories(monkeypatch, {
        ("LEFT", None): make_history("LEFT", "monthly", [
            ("2026-01-01", 0), ("2026-01-31", 1), ("2026-02-01", 2), ("2026-03-01", 3),
        ]),
        ("RIGHT", "yoy"): make_history("RIGHT", "monthly", [
            ("2026-01-01", 2), ("2026-02-01", 4), ("2026-03-01", 6),
        ], "yoy"),
    })
    result = relationships.compare_histories("LEFT", "RIGHT", right_feature="yoy")
    assert [row["period"] for row in result["observations"]] == ["2026-01", "2026-02", "2026-03"]
    assert result["observations"][0]["left"]["observation_date"] == date(2026, 1, 31)
    assert result["observations"][0]["left"]["normalized_value"] == 100
    assert result["observations"][1]["right"]["normalized_value"] == 200
    assert result["overlapping_observation_count"] == 3
    assert result["correlation"] == pytest.approx(1.0)
    assert result["history_type"] == "current_vintage"
    assert result["indicators"][1]["feature_name"] == "yoy"


def test_mixed_daily_monthly_uses_latest_daily_value_within_month(monkeypatch):
    stub_histories(monkeypatch, {
        ("MONTHLY", None): make_history("MONTHLY", "monthly", [
            ("2026-01-01", 10), ("2026-02-01", 20), ("2026-03-01", 30),
        ]),
        ("DAILY", None): make_history("DAILY", "daily", [
            ("2026-01-03", 2), ("2026-01-29", 3),
            ("2026-02-02", 4), ("2026-02-27", 6),
            ("2026-03-02", 8), ("2026-03-30", 9),
        ]),
    })
    result = relationships.compare_histories("MONTHLY", "DAILY")
    assert result["comparison_frequency"] == "monthly"
    assert [row["right"]["value"] for row in result["observations"]] == [3, 6, 9]
    assert result["correlation"] == pytest.approx(1.0)
    assert "latest dated non-null observation" in result["alignment_methodology"]


def test_quarterly_comparison_uses_latest_monthly_value_in_each_quarter(monkeypatch):
    stub_histories(monkeypatch, {
        ("QUARTERLY", None): make_history("QUARTERLY", "quarterly", [
            ("2026-01-01", 1), ("2026-04-01", 2), ("2026-07-01", 3),
        ]),
        ("MONTHLY", None): make_history("MONTHLY", "monthly", [
            ("2026-01-01", 1), ("2026-03-01", 3),
            ("2026-04-01", 4), ("2026-06-01", 6),
            ("2026-07-01", 7), ("2026-09-01", 9),
        ]),
    })
    result = relationships.compare_histories("QUARTERLY", "MONTHLY")
    assert result["comparison_frequency"] == "quarterly"
    assert [row["period"] for row in result["observations"]] == ["2026-Q1", "2026-Q2", "2026-Q3"]
    assert [row["right"]["value"] for row in result["observations"]] == [3, 6, 9]
    assert result["correlation"] == pytest.approx(1.0)


def test_sparse_overlap_and_constant_values_return_null_correlation(monkeypatch):
    stub_histories(monkeypatch, {
        ("LEFT", None): make_history("LEFT", "monthly", [
            ("2026-01-01", 2), ("2026-02-01", 2), ("2026-03-01", 2),
        ]),
        ("RIGHT", None): make_history("RIGHT", "monthly", [
            ("2026-01-01", 4), ("2026-02-01", None), ("2026-03-01", 6),
        ]),
    })
    result = relationships.compare_histories("LEFT", "RIGHT")
    assert result["overlapping_observation_count"] == 2
    assert result["correlation"] is None
    assert result["observations"][1]["right"] is None

    stub_histories(monkeypatch, {
        ("LEFT", None): make_history("LEFT", "monthly", [
            ("2026-01-01", 2), ("2026-02-01", 2), ("2026-03-01", 2),
        ]),
        ("RIGHT", None): make_history("RIGHT", "monthly", [
            ("2026-01-01", 4), ("2026-02-01", 5), ("2026-03-01", 6),
        ]),
    })
    assert relationships.compare_histories("LEFT", "RIGHT")["correlation"] is None


def test_optional_third_series_and_pairwise_overlap(monkeypatch):
    stub_histories(monkeypatch, {
        ("LEFT", None): make_history("LEFT", "monthly", [
            ("2026-01-01", 1), ("2026-02-01", 2), ("2026-03-01", 3),
        ]),
        ("RIGHT", None): make_history("RIGHT", "monthly", [
            ("2026-01-01", 2), ("2026-02-01", 4), ("2026-03-01", 6),
        ]),
        ("THIRD", None): make_history("THIRD", "monthly", [
            ("2026-02-01", 7), ("2026-03-01", 8),
        ]),
    })
    result = relationships.compare_histories("LEFT", "RIGHT", third_series="THIRD")
    assert result["overlapping_observation_count"] == 3
    assert [(item["left_key"], item["right_key"], item["overlapping_observation_count"])
            for item in result["comparisons"]] == [
        ("left", "right", 3), ("left", "third", 2), ("right", "third", 2),
    ]
    assert result["normalization_base_period"] == "2026-02"
    assert result["observations"][0]["third"] is None


def test_date_filters_and_invalid_selection_are_checked_before_loading(monkeypatch):
    calls = stub_histories(monkeypatch, {
        ("LEFT", None): make_history("LEFT", "monthly", []),
        ("RIGHT", None): make_history("RIGHT", "monthly", []),
    })
    start, end = date(2025, 1, 1), date(2025, 12, 31)
    result = relationships.compare_histories("LEFT", "RIGHT", start_date=start, end_date=end)
    assert calls == [("LEFT", None, start, end), ("RIGHT", None, start, end)]
    assert result["start_date"] == start and result["end_date"] == end
    with pytest.raises(history.InvalidDateRangeError):
        relationships.compare_histories("LEFT", "RIGHT", start_date=end, end_date=start)
    with pytest.raises(relationships.InvalidRelationshipSelectionError):
        relationships.compare_histories("LEFT", "LEFT")
    with pytest.raises(relationships.InvalidRelationshipSelectionError):
        relationships.compare_histories("LEFT", "RIGHT", third_feature="yoy")
    assert len(calls) == 2


def test_existing_history_validation_rejects_unknown_series_and_feature(monkeypatch):
    monkeypatch.setattr(history, "get_connection", lambda: pytest.fail("database should not be accessed"))
    with pytest.raises(history.UnknownSeriesError):
        relationships.compare_histories("BAD_SERIES", "UNRATE")
    with pytest.raises(history.UnsupportedFeatureError):
        relationships.compare_histories("UNRATE", "CPIAUCSL", left_feature="not_a_feature")


def test_compare_api_serializes_current_vintage_and_hides_errors(monkeypatch):
    stub_histories(monkeypatch, {
        ("UNRATE", None): make_history("UNRATE", "monthly", [("2026-01-01", 3), ("2026-02-01", 4)]),
        ("DFF", None): make_history("DFF", "daily", [("2026-01-30", 2), ("2026-02-27", 3)]),
    })
    client = TestClient(api_main.app)
    response = client.get("/api/v1/relationships/compare", params={
        "left_series": "UNRATE", "right_series": "DFF",
        "start_date": "2026-01-01", "end_date": "2026-02-28",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["history_type"] == "current_vintage"
    assert data["comparison_frequency"] == "monthly"
    assert data["observations"][0]["left"]["observation_date"] == "2026-01-01"
    assert data["observations"][0]["right"]["observation_date"] == "2026-01-30"
    assert data["overlapping_observation_count"] == 2
    assert data["correlation"] is None
    assert client.get("/api/v1/relationships/compare?left_series=UNRATE").status_code == 422
    assert client.get("/api/v1/relationships/compare?left_series=UNRATE&right_series=UNRATE").status_code == 400
    assert client.get("/api/v1/relationships/compare?left_series=UNRATE&right_series=DFF&start_date=bad").status_code == 422

    def fail(*args, **kwargs):
        raise RuntimeError("SELECT secret FROM observations password=secret")
    monkeypatch.setattr(api_main.relationships, "compare_histories", fail)
    failed = client.get("/api/v1/relationships/compare?left_series=UNRATE&right_series=DFF")
    assert failed.status_code == 503
    assert "SELECT" not in failed.text and "password" not in failed.text


def test_compare_api_rejects_unconfigured_sources_and_features(monkeypatch):
    monkeypatch.setattr(history, "get_connection", lambda: pytest.fail("database should not be accessed"))
    client = TestClient(api_main.app)
    assert client.get("/api/v1/relationships/compare", params={
        "left_series": "BAD_SERIES", "right_series": "UNRATE",
    }).status_code == 404
    assert client.get("/api/v1/relationships/compare", params={
        "left_series": "UNRATE", "left_feature": "bad_feature", "right_series": "CPIAUCSL",
    }).status_code == 404
