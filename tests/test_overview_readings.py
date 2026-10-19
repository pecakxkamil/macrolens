from datetime import date, datetime, timezone
from decimal import Decimal
import copy
import pytest
from fastapi.testclient import TestClient
from app.analytics import overview_readings as readings, economy_brief
from app.api.main import app
from tests.test_economy_brief import stub_sections


def row(series, feature, day, value):
    return series, feature, day, "2026-10-08", value


def get(rows, component):
    return next(item for item in readings.compare_overview_readings(rows) if item["component"] == component)


@pytest.mark.parametrize("series,feature,component,current,previous,earlier", [
    ("UNRATE", "level", "unemployment", "2026-01-01", "2025-12-01", "2025-10-01"),
    ("GDPC1", "qoq_annualized", "real_gdp", "2026-01-01", "2025-10-01", "2025-04-01"),
    ("ICSA", "moving_average_4w", "initial_claims", "2026-01-03", "2025-12-27", "2025-12-13"),
])
def test_calendar_comparisons_anchor_to_latest_available_period(series, feature, component, current, previous, earlier):
    result = get([row(series, feature, current, 4), row(series, feature, previous, 3), row(series, feature, earlier, 2)], component)
    assert result["current"]["observation_date"] == current
    assert result["previous"]["observation_date"] == previous
    assert result["three_periods_ago"]["observation_date"] == earlier
    assert result["change"] == 1


@pytest.mark.parametrize("series,feature,component,current,second,older,expected", [
    ("UNRATE", "level", "unemployment", "2026-01-01", "2025-11-01", "2025-09-01", "2025-10-01"),
    ("GDPC1", "qoq_annualized", "real_gdp", "2026-01-01", "2025-07-01", "2025-01-01", "2025-04-01"),
    ("ICSA", "moving_average_4w", "initial_claims", "2026-01-03", "2025-12-20", "2025-12-06", "2025-12-13"),
])
def test_missing_calendar_periods_are_not_compressed(series, feature, component, current, second, older, expected):
    result = get([row(series, feature, current, 4), row(series, feature, second, 3), row(series, feature, older, 2)], component)
    assert result["previous"] is result["three_periods_ago"] is result["change"] is None
    assert result["expected_three_periods_ago_date"] == expected


def test_daily_offsets_count_available_observations_across_weekends_and_holidays():
    result = get([row("DGS2 / DGS10", "spread", day, value) for day, value in [("2026-10-07", 4), ("2026-10-06", None), ("2026-10-05", 3), ("2026-10-02", 2), ("2026-09-30", 1)]], "yield_curve_2s10s")
    assert result["previous"]["observation_date"] == "2026-10-05"
    assert result["three_periods_ago"]["observation_date"] == "2026-09-30"
    assert result["change_type"] == "Difference from previous available observation"


@pytest.mark.parametrize("bad", [None, ".", float("nan"), float("inf")])
def test_missing_values_never_become_zero_or_bridge_required_periods(bad):
    result = get([row("CPIAUCSL", "mom", "2026-09-01", bad), row("CPIAUCSL", "mom", "2026-08-01", 3.7), row("CPIAUCSL", "mom", "2026-07-01", bad), row("CPIAUCSL", "mom", "2026-06-01", 2.5), row("CPIAUCSL", "mom", "2026-05-01", 0)], "headline_cpi")
    assert result["current"]["observation_date"] == "2026-08-01"
    assert result["latest_stored_observation_date"] == "2026-09-01"
    assert result["previous"] is result["change"] is None
    assert result["three_periods_ago"]["value"] == 0


@pytest.mark.parametrize("series,feature,component,unit", [
    ("CPIAUCSL", "mom", "headline_cpi", "percentage points"),
    ("GDPC1", "qoq_annualized", "real_gdp", "percentage points"),
    ("PAYEMS", "monthly_change", "payrolls", "thousands"),
    ("ICSA", "moving_average_4w", "initial_claims", "persons"),
    ("CFNAI", "moving_average_3m", "cfnai", "index points"),
    ("HOUST", "level", "housing_starts", "thousands SAAR"),
])
def test_same_transform_and_difference_units(series, feature, component, unit):
    spec = next(item for item in readings.READINGS if item[1] == component)
    latest = date(2026, 7, 1) if spec[5] != "weekly" else date(2026, 7, 4)
    prev = readings.offset_period(latest, spec[5], 1)
    data = [row(series, feature, str(latest), Decimal("10")), row(series, feature, str(prev), Decimal("7")), row(series, "unrelated", str(latest), 99999)]
    original = copy.deepcopy(data)
    result = get(data, component)
    assert result["feature_name"] == feature and result["current"]["value"] == 10
    assert result["change"] == 3 and result["change_unit"] == unit
    assert data == original


def test_daily_spread_uses_previous_synchronized_spread_observations():
    result = get([row("DGS2 / DGS10", "spread", day, value) for day, value in [("2026-10-07", .5), ("2026-10-05", .4), ("2026-10-02", .3), ("2026-09-30", .2)]], "yield_curve_2s10s")
    assert result["previous"]["value"] == .4 and result["three_periods_ago"]["value"] == .2
    assert result["change"] == pytest.approx(.1)
    assert result["change_unit"] == "percentage points"


def test_one_bounded_query_reuses_current_vintage_order_and_synchronized_yields(monkeypatch):
    calls = []
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql, params): calls.append((sql, params))
        def fetchall(self): return []
    class Connection:
        def cursor(self): return Cursor()
        def close(self): calls.append("closed")
    monkeypatch.setattr(readings, "get_connection", Connection)
    result = readings.load_reading_comparisons(date(2026, 10, 19))
    assert len(calls) == 2 and len(result) == 17
    sql, params = calls[0]
    assert "as_of_date DESC, computed_at DESC, id DESC" in sql
    assert "a.observation_date = b.observation_date" in sql and "b.feature_value - a.feature_value" in sql
    assert "available_rank <= 4" in sql and "INTERVAL '9 months'" in sql
    assert params[-2:] == ["v1", date(2026, 10, 19)]


def test_api_aggregates_readings_once_and_keeps_existing_snapshots_and_changes(monkeypatch):
    from pathlib import Path
    import json
    snapshot = json.loads((Path(__file__).parent / "fixtures/macro_state_snapshot.json").read_text(encoding="utf-8"))
    original = copy.deepcopy(snapshot)
    stub_sections(monkeypatch, snapshot)
    calls = []
    prepared = readings.compare_overview_readings([row("UNRATE", "level", "2026-09-01", 4.2), row("UNRATE", "level", "2026-08-01", 4.1), row("UNRATE", "level", "2026-06-01", 4.0)])
    monkeypatch.setattr(economy_brief, "load_reading_comparisons", lambda today: calls.append(today) or prepared)
    response = TestClient(app).get("/api/v1/economy/us/brief")
    assert response.status_code == 200 and len(calls) == 1
    body = response.json()
    assert len(body["reading_comparisons"]["data"]) == 17 and len(body["changes"]["data"]) == 6
    item = body["reading_comparisons"]["data"][1]
    assert item["three_periods_ago"]["observation_date"] == "2026-06-01"
    assert item["change"] == pytest.approx(.1)
    assert body["snapshot"]["data"] == snapshot and snapshot == original
    assert body["classification_basis"] and body["history_type"] == "current_vintage"


@pytest.mark.parametrize("component,series", [("headline_cpi", "CPIAUCSL"), ("core_cpi", "CPILFESL"), ("core_pce", "PCEPILFE"), ("industrial_production", "INDPRO"), ("real_consumption", "PCEC96"), ("real_disposable_income", "DSPIC96"), ("retail_sales", "RSAFS")])
def test_monthly_main_measure_is_stored_mom_with_exact_month_yoy_context(component, series):
    result = get([row(series, "mom", "2026-08-01", .3), row(series, "mom", "2026-07-01", .1), row(series, "mom", "2026-05-01", .2), row(series, "yoy", "2026-08-01", 3.7), row(series, "yoy", "2026-07-01", 3.5), row(series, "yoy", "2026-05-01", 3.1), row(series, "level", "2026-08-01", 999)], component)
    assert result["feature_name"] == "mom" and result["current"]["value"] == .3
    assert result["previous"]["value"] == .1 and result["three_periods_ago"]["value"] == .2
    assert result["change"] == pytest.approx(.2) and result["change_unit"] == "percentage points"
    for key in ["current", "previous", "three_periods_ago"]:
        assert result["context_yoy"][key]["observation_date"] == result[key]["observation_date"]


def test_missing_yoy_context_never_uses_another_month_or_series():
    result = get([row("CPIAUCSL", "mom", "2026-08-01", .3), row("CPIAUCSL", "yoy", "2026-07-01", 3.5), row("CPILFESL", "yoy", "2026-08-01", 3.1)], "headline_cpi")
    assert result["context_yoy"]["current"] is None
    assert result["previous"] is None and result["change"] is None


def test_sql_joined_context_rows_preserve_the_primary_date_even_with_newer_yoy():
    result = get([("PCEC96", "mom", "2026-08-01", "2026-09-30", .5, "2026-10-02", 2.5), row("PCEC96", "yoy", "2026-09-01", 3.1)], "real_consumption")
    assert result["current"]["observation_date"] == "2026-08-01"
    assert result["context_yoy"]["current"] == {"value": 2.5, "observation_date": "2026-08-01", "feature_as_of_date": "2026-10-02"}


def test_latest_observation_is_selected_by_period_not_retrieval_or_feature_as_of():
    result = get([
        ("CPIAUCSL", "mom", "2026-09-01", "2026-10-14", .25),
        ("CPIAUCSL", "mom", "2026-08-01", "2026-10-19", .40),
        ("CPIAUCSL", "mom", "2026-06-01", "2026-10-19", .20),
        row("CPIAUCSL", "yoy", "2026-09-01", 3.6),
    ], "headline_cpi")
    assert result["current"]["observation_date"] == "2026-09-01"
    assert result["current"]["feature_as_of_date"] == "2026-10-14"
    assert result["previous"]["observation_date"] == "2026-08-01"
    assert result["change"] == pytest.approx(-.15)
    assert result["context_yoy"]["current"]["observation_date"] == "2026-09-01"
