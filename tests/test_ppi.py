from datetime import date
import pandas as pd
import pytest
from app.database.sync_series import load_series_config
from app.analytics.features import calculate_features, FEATURES_BY_SERIES
from app.analytics import overview_readings, series_catalog, relationship_sources
from app.analytics.macro_conditions_index import COMPONENTS
from app.ingestion.backfill_vintages import MCI_SERIES
from tests.test_relationship_lab import install_snapshot
from tests.test_series_catalog import FakeConnection


def test_ppi_configuration_is_final_demand_sa_monthly_index_not_a_percent():
    ppi = load_series_config()["PPIFIS"]
    assert ppi["name"] == "Producer Price Index by Commodity: Final Demand"
    assert ppi["category"] == "inflation" and ppi["frequency"] == "monthly"
    assert ppi["unit"] == "index" and ppi["revision_tracking"] is True
    assert ppi["transformations"] == ["mom"] and FEATURES_BY_SERIES["PPIFIS"] == ("mom",)
    assert "Nov 2009=100" in ppi["description"] and "Seasonally adjusted" in ppi["description"]
    assert "PPIFIS" not in MCI_SERIES and all(spec.series_id != "PPIFIS" for spec in COMPONENTS)


def test_ppi_mom_reuses_the_shared_formula_without_interpreting_index_as_percent():
    data = pd.DataFrame({"observation_date": ["2025-01-01", "2025-02-01", "2025-03-01"], "value": [100, 102, 101]})
    result = calculate_features("PPIFIS", data, ["mom"])
    assert result["feature_name"].tolist() == ["mom", "mom"]
    assert result["feature_value"].tolist() == pytest.approx([2, (101/102-1)*100])


def test_ppi_gap_does_not_compress_months_and_legacy_features_are_unchanged():
    data = pd.DataFrame({"observation_date": ["2025-01-01", "2025-03-01", "2025-04-01"], "value": [100, 102, 103]})
    result = calculate_features("PPIFIS", data, ["mom"])
    assert result["observation_date"].tolist() == [date(2025,4,1)]
    assert result.iloc[0].feature_value == pytest.approx((103/102-1)*100)
    assert len(calculate_features("CPIAUCSL", data, ["mom"])) == 2


def test_ppi_overview_reports_rate_changes_and_no_yoy_context():
    rows = [("PPIFIS", "mom", date(2025,m,1), date(2025,5,1), v) for m,v in [(1,.3),(2,.1),(4,.2)]]
    result = next(r for r in overview_readings.compare_overview_readings(rows) if r["series_id"] == "PPIFIS")
    assert result["unit"] == "percent" and result["change_unit"] == "percentage points"
    assert result["current"]["observation_date"] == "2025-04-01"
    assert result["previous"] is None and result["change"] is None and result["context_yoy"] is None
    result = next(r for r in overview_readings.compare_overview_readings(rows+[("PPIFIS", "mom", date(2025,3,1),date(2025,5,1),.4)]) if r["series_id"] == "PPIFIS")
    assert result["change"] == pytest.approx(-.2)


def test_ppi_catalog_exposes_definition_and_existing_dynamic_relationship_catalog(monkeypatch):
    row = ("PPIFIS", "Producer Price Index by Commodity: Final Demand", "PPI Final Demand", "inflation", "monthly", "index")
    monkeypatch.setattr(series_catalog, "get_connection", lambda: FakeConnection([row]))
    metadata = series_catalog.list_active_series()["series"][0]
    assert metadata["unit"] == "index" and "Nov 2009=100" in metadata["description"]
    monkeypatch.setattr(relationship_sources.series_catalog, "list_active_series", lambda: {"series": [metadata]})
    monkeypatch.setattr(relationship_sources, "get_connection", lambda: FakeConnection([("PPIFIS", "mom")]))
    result = relationship_sources.list_sources()["sources"]
    ppi = next(r for r in result if r["series_id"] == "PPIFIS")
    assert ppi["features"] == ["mom"] and ppi["source_kind"] == "macro"
    relationship_sources.validate_source("PPIFIS", "mom")


@pytest.mark.parametrize("days,excluded", [(["2025-01-01", "2025-02-01"],0), (["2024-12-01", "2025-02-01"],1)])
def test_ppi_is_registered_for_existing_lab_continuity_checks(monkeypatch,days,excluded):
    install_snapshot(monkeypatch, days)
    kept, count = relationship_sources.calendar_safe_points("PPIFIS", "mom", "monthly", [{"observation_date":"2025-02-01", "feature_as_of_date":"2025-03-01", "value":1}])
    assert count == excluded and len(kept) == 1-excluded
