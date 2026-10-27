from datetime import date
from decimal import Decimal
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from app.analytics import relationships as lab, relationship_sources as sources, history
from app.api.main import app
from tests.test_relationships import make_history, stub_histories


def test_configured_market_sources_use_existing_raw_loader_without_provider_requests(monkeypatch):
    calls = []
    def asset(sid, start, end):
        calls.append(sid)
        result = make_history(sid, "daily", [("2026-01-30", 100), ("2026-02-27", 120), ("2026-03-30", 90)])
        return {**result, "name": "Bitcoin" if sid == "CBBTCUSD" else "Nasdaq Composite", "source_kind": "asset", "unit": "USD" if sid == "CBBTCUSD" else "index points"}
    monkeypatch.setattr(sources, "load_asset", asset)
    monkeypatch.setattr(history, "load_series_history", lambda sid, a, b: make_history(sid,"monthly", [("2026-01-01", 2),("2026-02-01", 4),("2026-03-01", 3)]))
    result = lab.compare_histories("UNRATE", "NASDAQCOM", third_series="CBBTCUSD")
    assert calls == ["NASDAQCOM", "CBBTCUSD"]
    assert result["comparison_frequency"] == "monthly"
    assert result["observations"][0]["right"]["observation_date"] == date(2026,1,30)
    assert result["comparisons"][0]["first_pair_period"] == "2026-01"
    assert result["comparisons"][0]["last_pair_period"] == "2026-03"
    assert result["indicators"][1]["name"] == "Nasdaq Composite"
    assert len(result["comparisons"]) == 3


@pytest.mark.parametrize("sid,feature,status", [("SP500",None,404),("BTCUSD",None,404),("NASDAQCOM","yoy",404),("CBBTCUSD","level",404),("UNRATE","qoq",404),("UNRATE","level; DROP TABLE series",404)])
def test_api_validates_every_source_before_database_access(monkeypatch,sid,feature,status):
    monkeypatch.setattr(history,"get_connection",lambda:pytest.fail("No database expected"))
    monkeypatch.setattr(sources,"get_connection",lambda:pytest.fail("No database expected"))
    params={"left_series":"UNRATE","right_series":sid}
    if feature:params["right_feature"]=feature
    assert TestClient(app).get("/api/v1/relationships/compare",params=params).status_code == status


def test_raw_and_level_aliases_cannot_duplicate_the_same_measure():
    with pytest.raises(lab.InvalidRelationshipSelectionError):
        lab.compare_histories("UNRATE","UNRATE",right_feature="level")


def test_sources_catalog_uses_active_macro_configured_stored_features_and_explicit_assets(monkeypatch):
    monkeypatch.setattr(sources.series_catalog,"list_active_series",lambda:{"series":[{"series_id":"UNRATE","name":"Unemployment","short_name":"Unemployment","category":"labor","frequency":"monthly","unit":"percent"}]})
    class Cursor:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def execute(self,*a):pass
        def fetchall(self):return [("UNRATE","level"),("UNRATE","change_3m"),("UNRATE","invented")]
    class Connection:
        def cursor(self):return Cursor()
        def close(self):pass
    monkeypatch.setattr(sources,"get_connection",Connection)
    result=TestClient(app).get("/api/v1/relationships/sources").json()
    assert {row["series_id"] for row in result["sources"]} == {"UNRATE","NASDAQCOM","CBBTCUSD"}
    assert result["sources"][0]["features"] == ["level","change_3m"]
    assert all(row["features"] == [] for row in result["sources"] if row["source_kind"] == "asset")


def install_snapshot(monkeypatch, days):
    calls=[]
    class Connection:
        def close(self):calls.append("closed")
    monkeypatch.setattr(sources,"get_connection",Connection)
    def snapshot(connection,series,as_of):
        calls.append((series,as_of))
        return pd.DataFrame({"observation_date":[date.fromisoformat(day) for day in days],"value":[Decimal("100")] * len(days)})
    monkeypatch.setattr(sources,"load_point_in_time_snapshot",snapshot)
    return calls


@pytest.mark.parametrize("feature,days,day,safe", [
    ("mom",["2026-01-01","2026-03-01"],"2026-03-01",False),
    ("mom",["2026-01-01","2026-02-01","2026-03-01"],"2026-03-01",True),
    ("mom",["2026-02-01","2026-02-15","2026-03-01"],"2026-03-01",False),
    ("moving_average_3m",["2026-01-01","2026-03-01","2026-04-01"],"2026-04-01",False),
    ("annualized_3m",["2026-01-01","2026-02-01","2026-03-01","2026-04-01"],"2026-04-01",True),
    ("monthly_change_ma_3m",["2026-01-01","2026-02-01","2026-04-01","2026-05-01"],"2026-05-01",False),
])
def test_calendar_guard_excludes_row_compressed_features_without_recomputing(monkeypatch,feature,days,day,safe):
    calls=install_snapshot(monkeypatch,days)
    points=[{"observation_date":day,"feature_as_of_date":"2026-10-14","value":123.45}]
    kept,excluded=sources.calendar_safe_points("PAYEMS" if feature.startswith("monthly_change") else "INDPRO",feature,"monthly",points)
    assert bool(kept) == safe and excluded == (0 if safe else 1)
    if safe:assert kept == points
    assert calls[-1] == "closed"


@pytest.mark.parametrize("series,feature,frequency,days,day", [
    ("GDPC1","qoq_annualized","quarterly",["2026-01-01","2026-07-01"],"2026-07-01"),
    ("ICSA","moving_average_4w","weekly",["2026-01-03","2026-01-10","2026-01-24","2026-01-31"],"2026-01-31"),
    ("CPIAUCSL","yoy","monthly",["2025-01-01","2026-01-01"],"2026-01-01"),
])
def test_guard_checks_all_intervening_periods_and_provenance(monkeypatch,series,feature,frequency,days,day):
    calls=install_snapshot(monkeypatch,days)
    points=[{"observation_date":day,"feature_as_of_date":"2026-10-14","value":1},{"observation_date":day,"value":2}]
    assert sources.calendar_safe_points(series,feature,frequency,points) == ([],2)
    assert calls.count((series,date(2026,10,14))) == 1


def test_guard_uses_each_features_actual_computation_snapshot_and_batches_identical_dates(monkeypatch):
    calls=install_snapshot(monkeypatch,["2026-01-01","2026-02-01","2026-03-01"])
    points=[{"observation_date":d,"feature_as_of_date":"2026-10-14","value":1} for d in ["2026-02-01","2026-03-01"]]
    kept,excluded=sources.calendar_safe_points("INDPRO","mom","monthly",points)
    assert kept == points and excluded == 0
    assert calls == [("INDPRO",date(2026,10,14)),"closed"]


@pytest.mark.parametrize("unit,feature,values,allowed", [("number",None,[1,2,3],True),("number",None,[0,2,3],False),("number",None,[-1,2,3],False),("percent",None,[1,2,3],False),("number","yoy",[1,2,3],False),("number","change_3m",[1,2,3],False)])
def test_indexing_is_display_only_and_rejects_inappropriate_zero_negative_measures(monkeypatch,unit,feature,values,allowed):
    left=make_history("LEFT","monthly",list(zip(["2026-01-01","2026-02-01","2026-03-01"],values)),feature)
    left["unit"]=unit
    stub_histories(monkeypatch,{("LEFT",feature):left,("RIGHT",None):make_history("RIGHT","monthly",[("2026-01-01",2),("2026-02-01",4),("2026-03-01",6)])})
    result=lab.compare_histories("LEFT","RIGHT",left_feature=feature)
    assert result["indexing"]["available"] == allowed
    assert result["correlation"] == lab._pearson(list(zip(values,[2,4,6])))
    if not allowed:assert all(row["left"]["normalized_value"] is None for row in result["observations"])


def test_pair_range_counts_only_actual_overlap_and_never_carries_a_missing_month(monkeypatch):
    stub_histories(monkeypatch,{("LEFT",None):make_history("LEFT","monthly",[("2026-01-01",1),("2026-02-01",2),("2026-03-01",3)]),("RIGHT",None):make_history("RIGHT","daily",[("2025-12-31",5),("2026-02-28",6),("2026-03-31",8)])})
    result=lab.compare_histories("LEFT","RIGHT")
    assert result["observations"][1]["right"] is None  # January, despite a December price.
    pair=result["comparisons"][0]
    assert pair["first_pair_period"] == "2026-02" and pair["last_pair_period"] == "2026-03"
    assert pair["overlapping_observation_count"] == 2 and pair["correlation"] is None


@pytest.mark.parametrize("series", ["CFNAI","NFCI"])
def test_centered_indices_are_not_ratio_indexed_even_in_positive_only_ranges(monkeypatch,series):
    stub_histories(monkeypatch,{(series,None):make_history(series,"monthly",[("2026-01-01",1),("2026-02-01",2),("2026-03-01",3)]),("RIGHT",None):make_history("RIGHT","monthly",[("2026-01-01",2),("2026-02-01",4),("2026-03-01",6)])})
    result=lab.compare_histories(series,"RIGHT")
    assert result["indexing"]["available"] is False and result["correlation"] == pytest.approx(1)


def test_feature_uses_its_own_as_of_snapshot_not_the_latest_repaired_calendar(monkeypatch):
    install_snapshot(monkeypatch,[])
    calls=[]
    def load(connection,sid,as_of):
        calls.append(as_of)
        days=["2026-01-01","2026-03-01"] if as_of == date(2026,4,1) else ["2026-01-01","2026-02-01","2026-03-01"]
        return pd.DataFrame({"observation_date":[date.fromisoformat(d) for d in days],"value":[100]*len(days)})
    monkeypatch.setattr(sources,"load_point_in_time_snapshot",load)
    points=[{"observation_date":"2026-03-01","feature_as_of_date":d,"value":.2} for d in ["2026-04-01","2026-05-01"]]
    kept,excluded=sources.calendar_safe_points("INDPRO","mom","monthly",points)
    assert kept == [points[1]] and excluded == 1
    assert calls == [date(2026,4,1),date(2026,5,1)]


def test_api_masks_unsafe_feature_points_and_reports_the_restriction(monkeypatch):
    install_snapshot(monkeypatch,["2026-01-01","2026-03-01"])
    monkeypatch.setattr(history,"load_series_history",lambda sid,a,b:make_history(sid,"monthly",[("2026-03-01",4)]))
    feature=make_history("INDPRO","monthly",[("2026-03-01",.5)],"mom")
    feature["observations"][0]["feature_as_of_date"] = "2026-04-01"
    monkeypatch.setattr(history,"load_feature_history",lambda *a:feature)
    response=TestClient(app).get("/api/v1/relationships/compare?left_series=UNRATE&right_series=INDPRO&right_feature=mom")
    assert response.status_code == 200
    result=response.json()
    assert result["indicators"][1]["excluded_observation_count"] == 1
    assert result["observations"][0]["right"] is None
    assert result["correlation"] is None and result["overlapping_observation_count"] == 0


def test_validation_rejects_bad_third_source_before_loading_valid_market_prices(monkeypatch):
    monkeypatch.setattr(sources,"load_asset",lambda *a:pytest.fail("Validation must precede any loading"))
    monkeypatch.setattr(history,"load_series_history",lambda *a:pytest.fail("Validation must precede any loading"))
    response=TestClient(app).get("/api/v1/relationships/compare?left_series=UNRATE&right_series=NASDAQCOM&third_series=UNCONFIGURED")
    assert response.status_code == 404


def test_absolute_index_changes_have_index_point_units_without_changing_other_modules(monkeypatch):
    stub_histories(monkeypatch,{("LEFT","change_4w"):make_history("LEFT","weekly",[("2026-01-03",.1)],"change_4w"),("RIGHT",None):make_history("RIGHT","weekly",[("2026-01-03",4)])})
    original_loader=history.load_feature_history
    def load(*args):return {**original_loader(*args),"unit":"index"}
    monkeypatch.setattr(history,"load_feature_history",load)
    assert lab.compare_histories("LEFT","RIGHT",left_feature="change_4w")["indicators"][0]["unit"] == "index points"
