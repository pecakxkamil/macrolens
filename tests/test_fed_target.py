from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from app.analytics.fed_target import summarize_target, load_fed_target, TARGET_SQL
from app.database import sync_series

STAMP = datetime(2026, 10, 19, 11, tzinfo=timezone.utc)

def row(day, lower=3.75, upper=4, lower_latest="2026-10-18", upper_latest="2026-10-18"):
    return (day, lower, upper, STAMP, STAMP, lower_latest, upper_latest)


def test_latest_unchanged_daily_range_is_not_a_new_decision():
    result = summarize_target([row("2026-10-18"), row("2026-10-17"), row("2026-10-16"), row("2026-10-15", 3.5, 3.75)])
    assert result["observation_date"] == "2026-10-18" and result["effective_date"] == "2026-10-16"
    assert result["last_rate_change"]["change_bps"] == 25
    assert "decision_date" not in result and "last_decision" not in result
    assert result["retrieved_at"] == STAMP.isoformat()


def test_range_sources_share_the_selected_observation_date_without_implying_freshness():
    result = summarize_target([row("2026-10-17", lower_latest="2026-10-18", upper_latest="2026-10-17")])
    assert result["lower"] == 3.75 and result["upper"] == 4
    assert result["observation_date"] == "2026-10-17"
    assert result["sources"][0]["observation_date"] == "2026-10-18"
    assert result["sources"][1]["observation_date"] == "2026-10-17"
    assert result["effective_date"] is None and result["last_rate_change"] is None
    assert "l.observation_date = u.observation_date" in TARGET_SQL


@pytest.mark.parametrize("bounds", [(4,3.75),(None,4),(3.75,None),(float("nan"),4),(3.75,float("inf"))])
def test_invalid_latest_range_is_unavailable_without_dff_or_older_fallback(bounds):
    result = summarize_target([row("2026-10-18",*bounds),row("2026-10-17")])
    assert result["availability"] == "unavailable" and result["lower"] is result["upper"] is None
    assert result["last_rate_change"] is None
    assert "DFF" not in TARGET_SQL


def test_empty_history_has_no_fabricated_target_or_effective_date():
    result = summarize_target([])
    assert result["lower"] is result["upper"] is result["effective_date"] is None
    assert [source["series_id"] for source in result["sources"]] == ["DFEDTARL", "DFEDTARU"]


@pytest.mark.parametrize("earlier", [row("2026-10-16",3.5,3.75),row("2026-10-17",None,4),row("2026-10-17",4.5,4)])
def test_gaps_or_invalid_history_cannot_prove_last_rate_change(earlier):
    result=summarize_target([row("2026-10-18"),earlier])
    assert result["availability"] == "available" and result["last_rate_change"] is None and result["effective_date"] is None


def test_width_changes_keep_both_basis_point_differences():
    result=summarize_target([row("2026-10-18",Decimal("3.75"),Decimal("4.25")),row("2026-10-17",Decimal("3.5"),Decimal("3.75"))])
    assert result["last_rate_change"]["change_bps"] is None
    assert result["last_rate_change"]["lower_change_bps"] == 25
    assert result["last_rate_change"]["upper_change_bps"] == 50


def test_loader_streams_history_and_stops_after_first_confirmed_change(monkeypatch):
    calls=[]
    class Cursor:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def execute(self,sql,params): calls.append((sql,params))
        def __iter__(self):
            yield row("2026-10-18")
            yield row("2026-10-17",3.5,3.75)
            raise AssertionError("Unnecessary older history consumed")
    class Connection:
        def cursor(self,*,name): calls.append(name);return Cursor()
        def close(self): calls.append("closed")
    monkeypatch.setattr("app.analytics.fed_target.get_connection",Connection)
    assert load_fed_target(date(2026,10,19))["last_rate_change"]["change_bps"] == 25
    assert len(calls)==3 and calls[-1]=="closed" and calls[1][1] == (date(2026,10,19),)


def test_series_registration_can_target_only_the_two_bounds(monkeypatch):
    written=[]
    class Connection:
        def cursor(self): return self
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def execute(self,sql,params): written.append(params["series_id"])
        def commit(self): pass
        def rollback(self): pass
        def close(self): pass
    monkeypatch.setattr(sync_series,"get_connection",Connection)
    assert sync_series.main(["DFEDTARL","DFEDTARU"])==0
    assert written==["DFEDTARL","DFEDTARU"]


def test_target_series_are_supported_without_entering_mci():
    from app.analytics.features import FEATURES_BY_SERIES
    from app.analytics import point_in_time_mci
    from app.database.sync_series import load_series_config
    config=load_series_config()
    for series in ["DFEDTARL","DFEDTARU"]:
        assert config[series]["transformations"]==["level"]
        assert FEATURES_BY_SERIES[series]==("level",)
    # The established MCI component definitions remain the source of its universe.
    assert "DFEDTAR" not in str(point_in_time_mci.MCI_SERIES)
