from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.analytics import point_in_time as loader, point_in_time_mci as pit
from app.analytics import macro_conditions_index as mci
from app.api import main as api_main
from app.ingestion import alfred, backfill_vintages

SERIES = backfill_vintages.MCI_SERIES


def vintage(observed, known, value, series="CPIAUCSL", end="9999-12-31"):
    return {"series_id": series, "observation_date": observed, "vintage_date": known,
            "value": Decimal(str(value)) if value is not None else None, "realtime_end": end}


def test_latest_known_vintage_and_not_yet_published():
    rows = [vintage("2020-01-01", "2020-02-01", 100),
            vintage("2020-01-01", "2020-03-01", 105),
            vintage("2020-02-01", "2020-03-01", 110)]
    assert loader.select_as_of(rows, date(2020, 1, 31)) == []
    feb = loader.select_as_of(rows, date(2020, 2, 15))
    assert len(feb) == 1 and feb[0]["value"] == 100
    march = loader.select_as_of(rows, date(2020, 3, 15))
    assert [row["value"] for row in march] == [105, 110]
    assert all(row["vintage_date"] <= "2020-03-15" for row in march)


def test_expired_or_null_vintage_never_revives_older_value():
    rows = [vintage("2020-01-01", "2020-02-01", 100, end="2020-02-29"),
            vintage("2020-01-01", "2020-03-01", None)]
    assert loader.select_as_of(rows, date(2020, 3, 15))[0]["value"] is None
    assert loader.select_as_of(rows[:1], date(2020, 3, 15))[0]["value"] is None


def test_pit_yoy_reconstructs_revisions_and_excludes_future_observation():
    rows = [vintage(str(date(2019, month, 1)), str(date(2019, month, 15)), 100) for month in range(1, 13)]
    rows += [vintage("2020-01-01", "2020-02-01", 110),
             vintage("2019-01-01", "2020-03-01", 105),
             vintage("2020-01-01", "2020-03-01", 115),
             vintage("2021-01-01", "2020-01-01", 999)]
    feb, grid = pit.reconstruct_features("CPIAUCSL", rows, date(2020, 2, 15))
    march, _ = pit.reconstruct_features("CPIAUCSL", rows, date(2020, 3, 15))
    value = lambda frame: frame[(frame.feature_name == "yoy") & (frame.observation_date.astype(str) == "2020-01-01")].feature_value.iloc[0]
    assert value(feb) == pytest.approx(10)
    assert value(march) == pytest.approx((115 / 105 - 1) * 100)
    assert grid[-1]["observation_date"] == "2020-01-01"


def test_missing_period_does_not_compress_three_month_change():
    rows = [vintage("2020-01-01", "2020-02-01", 4, "UNRATE"),
            vintage("2020-03-01", "2020-04-01", 5, "UNRATE"),
            vintage("2020-04-01", "2020-05-01", 6, "UNRATE")]
    frame, grid = pit.reconstruct_features("UNRATE", rows, date(2020, 5, 31))
    assert grid[1]["value"] is None
    assert frame[frame.observation_date.astype(str) == "2020-04-01"].feature_value.iloc[0] == 2


@pytest.fixture
def panel():
    rows = []
    for series in SERIES:
        if series in ("ICSA", "NFCI"):
            for index in range(415):
                observed = date(2000, 1, 1) + timedelta(weeks=index)
                rows.append(vintage(str(observed), str(observed + timedelta(days=7)),
                                    200000 + index * 10 if series == "ICSA" else index / 1000, series))
        else:
            index = 0
            for year in range(2000, 2008):
                for month in range(1, 13):
                    if series == "GDPC1" and month not in (1, 4, 7, 10):
                        continue
                    observed = date(year, month, 1)
                    available_month = mci._shift_month(observed, 3 if series == "GDPC1" else 1)
                    available = available_month.replace(day=28 if series == "GDPC1" else 10)
                    value = 4 + index / 100 if series == "UNRATE" else 1000 + index * 4
                    rows.append(vintage(str(observed), str(available), value, series))
                    index += 1
    return rows, {series: "2008-01-31" for series in SERIES}


def test_pit_month_end_history_order_coverage_and_revision_invariance(panel):
    rows, verified = panel
    result = pit.build_history(rows, verified, date(2007, 12, 31))
    dates = [row["as_of_date"] for row in result["observations"]]
    assert dates == sorted(set(dates))
    assert all(mci._month_end(date.fromisoformat(value)) == date.fromisoformat(value) for value in dates)
    assert result["history_type"] == "point_in_time" and result["methodology_version"] == "v1"
    assert result["coverage"]["first_valid_as_of_date"] == "2006-01-31"
    revised = rows + [vintage("2005-01-01", "2007-06-01", 5000, "GDPC1"),
                      vintage("2006-01-01", "2007-06-01", 9000, "PAYEMS")]
    changed = pit.build_history(revised, verified, date(2007, 12, 31))
    assert [row for row in changed["observations"] if row["as_of_date"] < "2007-06-01"] == [
        row for row in result["observations"] if row["as_of_date"] < "2007-06-01"]
    assert any(row["mci"] is not None for row in result["observations"])


def test_audit_exposes_exact_dependencies_and_reference_without_future_vintages(panel):
    rows, verified = panel
    cutoff = date(2006, 2, 28)
    known = {series: [row for row in rows if row["series_id"] == series] for series in SERIES}
    audited = pit.build_as_of(known, cutoff, verified, audit=True)
    assert audited["mci"] is not None
    assert set(audited["series_inputs"]) == set(SERIES)
    for domain in audited["domains"].values():
        for item in domain["components"]:
            assert item["raw_observations_used"]
            assert all(value <= str(cutoff) for value in item["vintage_dates_used"])
            assert all(row["observation_date"] <= str(cutoff) for row in item["raw_observations_used"])
            assert "normalization_reference" in item
    gdp = next(item for item in audited["domains"]["growth"]["components"] if item["key"] == "real_gdp")
    assert gdp["source_observation_date"] == "2005-10-01"  # Q1 has not been published yet.
    assert "2006-04-28" not in gdp["vintage_dates_used"]


def test_missing_series_coverage_and_stale_data_are_not_filled(panel):
    rows, verified = panel
    missing = verified.copy()
    del missing["NFCI"]
    result = pit.build_history(rows, missing, date(2007, 12, 31))
    assert result["observations"] == [] and result["coverage"]["missing_series"] == ["NFCI"]
    known = {series: [row for row in rows if row["series_id"] == series] for series in SERIES}
    audited = pit.build_as_of(known, date(2009, 1, 31), {series: "2009-12-31" for series in SERIES})
    assert audited["mci"] is None
    assert all(domain["score"] is None for domain in audited["domains"].values())


def test_pit_api_history_audit_and_existing_current_vintage_route(monkeypatch, panel):
    monkeypatch.setattr(loader, "load_vintage_panel", lambda cutoff: panel)
    monkeypatch.setattr(loader, "load_backfill_signature", lambda: {"fixture": ["known"]})
    client = TestClient(api_main.app)
    response = client.get("/api/v1/economy/us/mci/point-in-time/history?start_date=2006-01-01&end_date=2006-03-31")
    assert response.status_code == 200
    assert response.json()["history_type"] == "point_in_time"
    assert len(response.json()["observations"]) == 3
    audit = client.get("/api/v1/economy/us/mci/point-in-time/2006-02-28")
    assert audit.status_code == 200
    assert audit.json()["domains"]["labor"]["components"][0]["vintage_dates_used"]
    assert "series_inputs" not in audit.json()
    assert all("normalization_reference" not in item and "normalization_summary" in item
               for domain in audit.json()["domains"].values() for item in domain["components"])
    assert client.get("/api/v1/economy/us/mci/point-in-time/history?start_date=2020-02-01&end_date=2020-01-01").status_code == 400
    assert client.get("/api/v1/economy/us/mci/point-in-time/not-a-date").status_code == 422
    monkeypatch.setattr(mci, "get_current_index", lambda: {"history_type": "current_vintage", "mci": 42})
    assert client.get("/api/v1/economy/us/mci").json() == {"history_type": "current_vintage", "mci": 42}


def test_pit_api_sanitizes_failure(monkeypatch):
    def fail(*args):
        raise RuntimeError("secret connection details")
    monkeypatch.setattr(loader, "load_vintage_panel", fail)
    monkeypatch.setattr(loader, "load_backfill_signature", lambda: {})
    monkeypatch.setattr(pit, "CACHE_PATH", Path("nonexistent-pit-cache.json"))
    response = TestClient(api_main.app).get("/api/v1/economy/us/mci/point-in-time/history")
    assert response.status_code == 503 and "secret" not in response.text


def test_loader_bulk_sql_and_provenance_exclude_snapshots(monkeypatch):
    calls = []
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql, params):
            calls.append((sql, params))
        def fetchall(self): return []
    class Connection:
        def cursor(self): return Cursor()
        def close(self): pass
    monkeypatch.setattr(loader, "get_connection", lambda: Connection())
    rows, verified = loader.load_vintage_panel(date(2020, 2, 15))
    assert rows == [] and verified == {} and len(calls) == 2
    assert "source = 'alfred'" in calls[0][0] and "vintage_date <= %s" in calls[0][0]
    loader.load_series_as_of("PAYEMS", date(2020, 2, 15))
    assert "DISTINCT ON (observation_date)" in calls[-1][0]


def page(observations, count=None, offset=0):
    return {"observations": observations, "output_type": 1, "units": "lin", "offset": offset,
            "count": len(observations) if count is None else count, "limit": alfred.PAGE_SIZE,
            "realtime_start": "1776-07-04", "realtime_end": "2020-03-31"}


def test_alfred_parser_preserves_revisions_missing_and_interval_dates():
    rows = [{"date": "2020-01-01", "realtime_start": "2020-02-01", "realtime_end": "2020-02-29", "value": "100"},
            {"date": "2020-01-01", "realtime_start": "2020-03-01", "realtime_end": "2020-03-31", "value": "105"},
            {"date": "2020-02-01", "realtime_start": "2020-03-01", "realtime_end": "2020-03-31", "value": "."}]
    parsed = alfred.parse_vintage_page("PAYEMS", page(rows), date(2020, 3, 31), 0)
    assert [row[3] for row in parsed] == [Decimal("100"), Decimal("105"), None]
    for value in ("NaN", "Infinity", "invalid"):
        bad = deepcopy(rows)
        bad[0]["value"] = value
        with pytest.raises(ValueError):
            alfred.parse_vintage_page("PAYEMS", page(bad), date(2020, 3, 31), 0)
    with pytest.raises(ValueError):
        alfred.parse_vintage_page("PAYEMS", page(rows + rows), date(2020, 3, 31), 0)


def test_raw_storage_is_separate_and_immutable(tmp_path, monkeypatch):
    monkeypatch.setattr(alfred, "RAW_ROOT", tmp_path / "alfred")
    first = alfred.save_raw_response("PAYEMS", {"original": 1})
    second = alfred.save_raw_response("PAYEMS", {"original": 2})
    assert first != second and '"original": 1' in first.read_text()
    assert first.parent == tmp_path / "alfred" / "PAYEMS"


def test_backfill_uses_real_periods_and_sanitizes_key(monkeypatch):
    params = []
    class Response:
        def raise_for_status(self): pass
        def json(self): return {}
    monkeypatch.setenv("FRED_API_KEY", "private")
    monkeypatch.setattr(alfred, "load_dotenv", lambda: None)
    monkeypatch.setattr(alfred.httpx, "get", lambda url, **kwargs: params.append(kwargs["params"]) or Response())
    alfred.fetch_vintage_page("PAYEMS", date(2020, 3, 31), 10)
    assert params[0]["realtime_start"] == "1776-07-04"
    assert params[0]["output_type"] == 1 and params[0]["offset"] == 10
    assert params[0]["units"] == "lin"


def test_backfill_conflict_and_snapshot_ingestion_guards():
    from app.ingestion.ingest_series import INSERT_OBSERVATION_SQL
    assert "o.source = 'alfred'" in backfill_vintages.CONFLICT_SQL
    assert "IS DISTINCT FROM" in backfill_vintages.CONFLICT_SQL
    assert "observation_vintages.source != 'alfred'" in INSERT_OBSERVATION_SQL
    assert len(SERIES) == 15 and "DGS10" not in SERIES and "RSAFS" not in SERIES



def test_history_cache_reuse_range_and_invalidation(tmp_path, monkeypatch):
    import json
    cache = tmp_path / "history.json"
    signature = {"PAYEMS": ["2020-03-31", 2, "finished"]}
    candidate = {"history_type": "point_in_time", "methodology_version": "v1",
                 "source_signature": signature, "cache_complete_history": True,
                 "as_of_date": "2020-03-31", "observations": [
                     {"as_of_date": "2020-01-31", "mci": 10},
                     {"as_of_date": "2020-02-29", "mci": 20},
                     {"as_of_date": "2020-03-31", "mci": 30}]}
    cache.write_text(json.dumps(candidate))
    monkeypatch.setattr(pit, "CACHE_PATH", cache)
    monkeypatch.setattr(loader, "load_backfill_signature", lambda: signature.copy())
    calls = []
    monkeypatch.setattr(loader, "load_vintage_panel", lambda cutoff: calls.append(cutoff) or ([], {}))
    result = pit.get_history(date(2020, 2, 1), date(2020, 2, 29))
    assert result["observations"] == [{"as_of_date": "2020-02-29", "mci": 20}]
    assert not calls
    signature["PAYEMS"][2] = "new-backfill"
    assert pit.get_history(end_date=date(2020, 2, 29))["observations"] == []
    assert calls == [date(2020, 2, 29)]


def test_alfred_pagination_replays_saved_pages_and_fetches_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(alfred, "RAW_ROOT", tmp_path)
    monkeypatch.setattr(alfred, "PAGE_SIZE", 1)
    def payload(offset):
        result = page([{"date": "2020-01-01", "realtime_start": f"2020-03-0{offset + 1}",
                        "realtime_end": "2020-03-31", "value": str(100 + offset)}], 3, offset)
        result["limit"] = 1
        return result
    first = alfred.save_raw_response("PAYEMS", payload(0))
    original = first.read_bytes()
    fetched = []
    monkeypatch.setattr(alfred, "fetch_vintage_page", lambda series, cutoff, offset:
                        fetched.append(offset) or payload(offset))
    pages = list(alfred.iter_vintage_pages("PAYEMS", date(2020, 3, 31)))
    assert [item["offset"] for item in pages] == [0, 1, 2]
    assert sorted(fetched) == [1, 2] and first.read_bytes() == original
    fetched.clear()
    assert len(list(alfred.iter_vintage_pages("PAYEMS", date(2020, 3, 31)))) == 3
    assert fetched == []


def test_exact_date_audit_includes_weekly_reading_already_known_this_month(panel):
    rows, verified = panel
    cutoff = date(2006, 3, 15)
    known = {series: [row for row in rows if row["series_id"] == series] for series in SERIES}
    result = pit.build_as_of(known, cutoff, verified, audit=True)
    nfci = result["domains"]["financial_conditions"]["components"][0]
    expected = max(row["observation_date"] for row in rows if row["series_id"] == "NFCI"
                   and row["vintage_date"] <= str(cutoff) and row["observation_date"] <= str(cutoff))
    assert expected.startswith("2006-03")
    assert nfci["source_observation_date"] == expected
    assert all(day <= str(cutoff) for day in nfci["vintage_dates_used"])


def test_pagination_crosses_100000_and_receives_final_partial_page(tmp_path, monkeypatch):
    # Eleven full pages plus a tail: specifically prevent a 100000-row ceiling.
    count = 110003
    fetched = []
    monkeypatch.setattr(alfred, "RAW_ROOT", tmp_path)
    monkeypatch.setattr(alfred, "save_raw_response", lambda *args: None)
    def fetch(series, cutoff, offset):
        fetched.append(offset)
        observations = [{"date": str(date(1900, 1, 1) + timedelta(days=i // 10000)),
                         "realtime_start": str(date(1950, 1, 1) + timedelta(days=i % 10000)),
                         "realtime_end": "2020-03-31", "value": str(i)}
                        for i in range(offset, min(offset + alfred.PAGE_SIZE, count))]
        return page(observations, count, offset)
    monkeypatch.setattr(alfred, "fetch_vintage_page", fetch)
    pages = list(alfred.iter_vintage_pages("NFCI", date(2020, 3, 31)))
    offset = 0
    for payload in pages:
        offset += len(alfred.parse_vintage_page("NFCI", payload, date(2020, 3, 31), offset))
    assert offset == count
    assert sorted(fetched) == list(range(0, count, 10000))
    assert pages[-1]["offset"] == 110000 and len(pages[-1]["observations"]) == 3


@pytest.mark.parametrize("corruption", ["wrong_limit", "short_page", "oversized_page", "wrong_offset", "invalid_count"])
def test_pagination_metadata_is_validated(corruption):
    item = {"date": "2020-01-01", "realtime_start": "2020-02-01",
            "realtime_end": "2020-03-31", "value": "100"}
    payload = page([item])
    if corruption == "wrong_limit": payload["limit"] = 100000
    if corruption == "short_page": payload["count"] = 2
    if corruption == "oversized_page": payload["observations"] *= 2
    if corruption == "wrong_offset": payload["offset"] = 1
    if corruption == "invalid_count": payload["count"] = True
    with pytest.raises(ValueError, match="metadata"):
        alfred.parse_vintage_page("PAYEMS", payload, date(2020, 3, 31), 0)


def test_no_look_ahead_percentile_reference_distribution(panel, monkeypatch):
    rows, verified = panel
    cutoff = date(2006, 2, 28)
    def forbidden(*args, **kwargs):
        raise AssertionError("PIT must never load current-vintage computed features")
    monkeypatch.setattr(mci.history, "load_feature_history", forbidden)
    def evaluate(values):
        return pit.build_as_of({series: [row for row in values if row["series_id"] == series]
                                for series in SERIES}, cutoff, verified, audit=True)
    baseline = evaluate(rows)
    poisoned = rows + [
        vintage("2006-01-07", "2006-03-01", -999999, "NFCI"),
        vintage("2000-01-01", "2006-03-01", 999999, "NFCI"),
        vintage("2007-01-06", "2006-01-01", -999999, "NFCI"),
        vintage("2006-03-04", "2006-03-11", 999999, "NFCI")]
    result = evaluate(poisoned)
    assert result == baseline
    component = result["domains"]["financial_conditions"]["components"][0]
    # One latest-known weekly level per month, Jan 2000 through Feb 2006.
    assert component["reference_sample_size"] == 74
    assert len(component["normalization_reference"]) == 74
    assert component["score"] == pytest.approx(100 / (2 * 74))
    assert max(item["observation_date"] for item in component["normalization_reference"]) <= str(cutoff)
    assert component["reference_end_date"] == "2006-02-01"


@pytest.mark.parametrize("series,feature,observed,initial,revised,expected_initial,expected_revised", [
    ("INDPRO", "annualized_3m", ["2020-01-01", "2020-02-01", "2020-03-01", "2020-04-01"],
     [100, 100, 100, 110], [100, 100, 100, 120], (1.1 ** 4 - 1) * 100, (1.2 ** 4 - 1) * 100),
    ("CFNAI", "moving_average_3m", ["2020-02-01", "2020-03-01", "2020-04-01"],
     [1, 2, 3], [1, 2, 6], 2, 3),
    ("ICSA", "moving_average_4w", ["2020-03-28", "2020-04-04", "2020-04-11", "2020-04-18"],
     [100, 100, 100, 140], [100, 100, 100, 180], 110, 120),
    ("GDPC1", "qoq_annualized", ["2019-10-01", "2020-01-01"],
     [100, 110], [100, 120], (1.1 ** 4 - 1) * 100, (1.2 ** 4 - 1) * 100),
])
def test_shared_features_use_pit_inputs_only(series, feature, observed, initial, revised, expected_initial, expected_revised):
    rows = [vintage(day, "2020-04-25", value, series) for day, value in zip(observed, initial)]
    rows += [vintage(day, "2020-05-01", value, series) for day, value in zip(observed, revised)]
    before, _ = pit.reconstruct_features(series, rows, date(2020, 4, 30))
    after, _ = pit.reconstruct_features(series, rows, date(2020, 5, 31))
    assert before[before.feature_name == feature].feature_value.iloc[-1] == pytest.approx(expected_initial)
    assert after[after.feature_name == feature].feature_value.iloc[-1] == pytest.approx(expected_revised)


def test_gdp_waits_for_publication_not_quarter_end():
    rows = [vintage("2019-10-01", "2020-01-30", 100, "GDPC1"),
            vintage("2020-01-01", "2020-04-30", 110, "GDPC1")]
    known = {"GDPC1": rows}
    verified = {series: "2020-12-31" for series in SERIES}
    for cutoff in (date(2020, 3, 31), date(2020, 4, 29)):
        result = pit.build_as_of(known, cutoff, verified, audit=True)
        gdp = result["domains"]["growth"]["components"][0]
        assert gdp["raw_value"] is None
        assert all(item["observation_date"] != "2020-01-01" for item in result["series_inputs"]["GDPC1"])
    result = pit.build_as_of(known, date(2020, 4, 30), verified, audit=True)
    gdp = result["domains"]["growth"]["components"][0]
    assert gdp["source_observation_date"] == "2020-01-01"
    assert gdp["raw_value"] == pytest.approx((1.1 ** 4 - 1) * 100)
    assert "2020-04-30" in gdp["vintage_dates_used"]


def test_interval_end_is_inclusive_and_disappearance_does_not_revive_value():
    rows = [vintage("2020-01-01", "2020-02-01", 100, end="2020-02-29"),
            vintage("2020-01-01", "2020-04-01", 105)]
    assert loader.select_as_of(rows, date(2020, 2, 29))[0]["value"] == 100
    assert loader.select_as_of(rows, date(2020, 3, 1))[0]["value"] is None
    assert loader.select_as_of(rows, date(2020, 3, 31))[0]["value"] is None
    assert loader.select_as_of(rows, date(2020, 4, 1))[0]["value"] == 105


@pytest.mark.parametrize("case", ["complete", "truncated", "count_changed", "offset_gap"])
def test_backfill_pagination_commits_only_complete_consistent_series(monkeypatch, case):
    monkeypatch.setattr(alfred, "PAGE_SIZE", 1)
    item = {"date": "2020-01-01", "realtime_start": "2020-02-01",
            "realtime_end": "2020-03-31", "value": "100"}
    pages = [page([item], 2, 0), page([{**item, "realtime_start": "2020-03-01", "value": "105"}], 2, 1)]
    if case == "truncated": pages.pop()
    if case == "count_changed": pages[1]["count"] = 3
    if case == "offset_gap": pages[1]["offset"] = 2
    monkeypatch.setattr(alfred, "iter_vintage_pages", lambda *args: iter(pages))
    monkeypatch.setattr(backfill_vintages, "load_series_config", lambda: {"UNRATE": {}})
    class Copy:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def write_row(self, row): pass
    class Cursor:
        rowcount = 1
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql, params=None): statements.append(sql)
        def fetchone(self): return (0,)
        def copy(self, sql): return Copy()
    class Connection:
        committed = rolled_back = False
        def cursor(self): return Cursor()
        def commit(self): self.committed = True
        def rollback(self): self.rolled_back = True
        def close(self): pass
    statements = []
    connection = Connection()
    monkeypatch.setattr(backfill_vintages, "get_connection", lambda: connection)
    if case == "complete":
        result = backfill_vintages.backfill_series("UNRATE", date(2020, 3, 31))
        assert result["rows_downloaded"] == 2 and connection.committed and not connection.rolled_back
        assert backfill_vintages.COVERAGE_SQL in statements
    else:
        with pytest.raises((RuntimeError, ValueError)):
            backfill_vintages.backfill_series("UNRATE", date(2020, 3, 31))
        assert connection.rolled_back and not connection.committed
        assert backfill_vintages.COVERAGE_SQL not in statements


def test_database_loader_expires_selected_interval_without_reviving_old_vintage(monkeypatch):
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql, params):
            assert sql == loader.AS_OF_SQL
            assert params == ("UNRATE", date(2020, 3, 15), date(2020, 3, 15))
        def fetchall(self):
            return [(date(2020, 1, 1), date(2020, 2, 1), Decimal("100"), date(2020, 2, 29))]
    class Connection:
        def cursor(self): return Cursor()
        def close(self): pass
    monkeypatch.setattr(loader, "get_connection", lambda: Connection())
    result = loader.load_series_as_of("UNRATE", date(2020, 3, 15))
    assert result["observations"][0]["value"] is None
    assert result["observations"][0]["vintage_date"] == "2020-02-01"


@pytest.mark.parametrize("rows,expected", [
    ([{"as_of_date": "2006-03-31", "mci": 25}, {"as_of_date": "2006-01-31", "mci": 0},
      {"as_of_date": "2005-12-31", "mci": None}], "2006-01-31"),
    ([{"as_of_date": "2005-12-31", "mci": None}], None),
])
def test_coverage_start_derived_from_cached_rows_not_stale_metadata(tmp_path, monkeypatch, rows, expected):
    import json
    cache = tmp_path / "history.json"
    cache.write_text(json.dumps({"history_type": "point_in_time", "methodology_version": "v1",
                                "source_signature": {}, "cache_complete_history": True,
                                "as_of_date": "2007-01-31", "coverage": {"first_valid_as_of_date": None},
                                "observations": rows}))
    monkeypatch.setattr(pit, "CACHE_PATH", cache)
    monkeypatch.setattr(loader, "load_backfill_signature", lambda: {})
    monkeypatch.setattr(loader, "load_vintage_panel", lambda *args: pytest.fail("Valid cache must supply coverage"))
    # A later display start does not erase the full history's first valid date.
    assert pit.get_history(date(2006, 2, 1), date(2006, 12, 31))["coverage"]["first_valid_as_of_date"] == expected
    assert pit.get_history(end_date=date(2005, 12, 31))["coverage"]["first_valid_as_of_date"] is None


def test_current_and_audit_coverage_use_actual_history_without_cache(monkeypatch):
    rows = [vintage("2006-01-01", "2006-02-01", 100, series) for series in SERIES]
    monkeypatch.setattr(loader, "load_vintage_panel", lambda *args: (rows, {series: "2006-03-31" for series in SERIES}))
    monkeypatch.setattr(loader, "load_backfill_signature", lambda: {})
    monkeypatch.setattr(pit, "CACHE_PATH", Path("nonexistent-pit-cache.json"))
    calls = []
    def built_history(rows, verified, cutoff):
        calls.append(cutoff)
        return {"coverage": {"first_valid_as_of_date": None}, "observations": [
            {"as_of_date": "2006-01-31", "mci": None},
            {"as_of_date": "2006-02-28", "mci": 40},
            {"as_of_date": "2006-03-31", "mci": 50}]}
    monkeypatch.setattr(pit, "build_history", built_history)
    assert pit.get_current()["coverage"]["first_valid_as_of_date"] == "2006-02-28"
    assert pit.get_audit(date(2006, 3, 31))["coverage"]["first_valid_as_of_date"] == "2006-02-28"
    assert calls == [date(2006, 3, 31), date(2006, 3, 31)]


def test_concise_audit_preserves_scores_vintages_and_reproducible_rank_counts(panel):
    rows, verified = panel
    known = {series: [row for row in rows if row["series_id"] == series] for series in SERIES}
    full = pit.build_as_of(known, date(2006, 2, 28), verified, audit=True)
    concise = pit._concise_audit(deepcopy(full))
    assert "series_inputs" not in concise and concise["mci"] == full["mci"]
    for key, domain in concise["domains"].items():
        assert domain["score"] == full["domains"][key]["score"]
        for component, original in zip(domain["components"], full["domains"][key]["components"]):
            assert "normalization_reference" not in component
            for field in ("raw_value", "score", "inputs", "raw_observations_used", "vintage_dates_used", "source_observation_date"):
                assert component[field] == original[field]
            assert all(row["vintage_date"] and row["realtime_end"] for row in component["raw_observations_used"])
            summary = component["normalization_summary"]
            if summary["method"] == "expanding_midrank_percentile":
                n = summary["reference_observation_count"]
                assert n == component["reference_sample_size"]
                assert summary["below_value_count"] + summary["equal_value_count"] + summary["above_value_count"] == n
                percentile = 100 * (summary["below_value_count"] + summary["equal_value_count"] / 2) / n
                expected = 100 - percentile if component["orientation"] == "lower" else percentile
                assert component["score"] == pytest.approx(expected)
            else:
                assert summary["reference_observation_count"] == 0
                assert summary["distance_pp"] == abs(component["raw_value"] - 2)
