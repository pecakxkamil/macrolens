from datetime import date
from decimal import Decimal
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from app.analytics import market_comparison as market
from app.analytics.macro_conditions_index import COMPONENTS
from app.database.sync_series import load_series_config
from app.market_assets import load_market_assets
from app.ingestion import ingest_market_assets as ingestion, raw_storage
from app.api.main import app


def prices(*items):
    return [{"observation_date": day, "value": value} for day, value in items]


def macro(*items):
    return [{"as_of_date": day, "mci": value} for day, value in items]


def build(months, assets, **kwargs):
    return market.build_comparison(months, assets, load_market_assets(), **kwargs)


def test_explicit_universe_stays_out_of_macro_config_and_mci():
    config = load_market_assets()
    assert list(config) == ["NASDAQCOM", "CBBTCUSD"]
    assert config["NASDAQCOM"]["source_organization"] == "Nasdaq, Inc."
    assert config["CBBTCUSD"]["source_organization"] == "Coinbase"
    assert config["CBBTCUSD"]["unit"] == "USD"
    assert not set(config) & set(load_series_config())
    assert not set(config) & {component.series_id for component in COMPONENTS}
    for key in config:
        assert config[key]["provider"] == "fred" and config[key]["frequency"] == "daily"


@pytest.mark.parametrize("invalid", ["", "GOLD", "SP500", "NASDAQCOM,NASDAQCOM", "CBBTCUSD,DFF", "NASDAQCOM, arbitrary"])
def test_asset_whitelist(invalid):
    with pytest.raises(market.InvalidMarketComparisonError):
        market.select_assets(invalid, load_market_assets())


@pytest.mark.parametrize("month_end,observations,expected_date,expected_value", [
    ("2020-05-31", [("2020-05-29", 9500), ("2020-06-01", 9600)], "2020-05-29", 9500),
    ("2020-12-31", [("2020-12-30", 100), ("2021-01-04", 120)], "2020-12-30", 100),
    ("2020-05-31", [("2020-05-29", 9500), ("2020-05-31", 9700)], "2020-05-31", 9700),
    ("2020-05-31", [("2020-05-29", 9500), ("2020-05-31", None)], "2020-05-29", 9500),
    ("2020-05-31", [("2020-06-01", 9600)], None, None),
])
def test_backward_only_weekend_holiday_exact_missing_and_beginning(month_end, observations, expected_date, expected_value):
    response = build(macro((month_end, 50)), {"NASDAQCOM": prices(*observations)})
    row = response["rows"][0]
    assert row["NASDAQCOM"] == expected_value
    assert row["NASDAQCOM_observation_date"] == expected_date
    assert row["mci"] == 50
    assert row["NASDAQCOM_return_1m"] is None


def test_common_base_indexing_ordering_and_no_macro_rebase():
    months = macro(("2020-06-30", 60), ("2020-04-30", 40), ("2020-05-31", 50), ("2020-05-31", 50))
    data = {"NASDAQCOM": prices(("2020-04-30", 100), ("2020-05-29", 200), ("2020-06-30", 300)),
            "CBBTCUSD": prices(("2020-05-31", 1000), ("2020-06-30", 2000))}
    result = build(months, data, start_date=date(2020, 4, 1))
    assert result["base_date"] == "2020-05-31"
    assert result["base_values"] == {"NASDAQCOM": 200, "CBBTCUSD": 1000}
    assert [row["as_of_date"] for row in result["rows"]] == ["2020-04-30", "2020-05-31", "2020-06-30"]
    assert result["rows"][0]["NASDAQCOM_indexed"] is None
    assert result["rows"][1]["NASDAQCOM_indexed"] == result["rows"][1]["CBBTCUSD_indexed"] == 100
    assert result["rows"][2]["NASDAQCOM_indexed"] == 150
    assert result["rows"][2]["CBBTCUSD_indexed"] == 200
    assert result["rows"][2]["mci"] == 60
    assert "mci_indexed" not in result["rows"][2]
    maximum = build(months, data)
    assert maximum["rows"][0]["as_of_date"] == maximum["available_overlap_start"] == "2020-05-31"
    assert result["rows"][1]["CBBTCUSD_observation_date"] == "2020-05-31"
    filtered = build(months, data, start_date=date(2020, 6, 1))
    assert filtered["base_date"] == "2020-06-30" and filtered["rows"][0]["NASDAQCOM_indexed"] == 100


def test_returns_correlation_pairing_and_mode_independence():
    months = macro(("2020-01-31", 10), ("2020-02-29", 20), ("2020-03-31", None), ("2020-04-30", 40), ("2020-05-31", 60))
    data = {"NASDAQCOM": prices(("2020-01-31", 100), ("2020-02-28", 110), ("2020-03-31", 121), ("2020-04-30", 145.2), ("2020-05-29", 174.24))}
    result = build(months, data)
    assert result["rows"][1]["NASDAQCOM_return_1m"] == pytest.approx(10)
    assert result["rows"][3]["NASDAQCOM_return_1m"] == pytest.approx(20)
    assert result["rows"][3]["mci_change"] is None
    stats = result["statistics"][0]
    assert stats["mci"]["overlapping_observations"] == 3
    assert stats["mci_change"]["overlapping_observations"] == 2
    assert stats["mci_change"]["correlation"] is None
    assert stats["mci"]["correlation"] == pytest.approx(market._pearson([(20, 10), (40, 20), (60, 20)]))
    actual = build(months, data, mode="actual")
    assert actual["rows"] == result["rows"] and actual["statistics"] == result["statistics"]
    ranged = build(months, data, start_date=date(2020, 2, 1))
    assert ranged["rows"][0]["NASDAQCOM_return_1m"] == pytest.approx(10)  # prior month outside display range


def test_nonconsecutive_months_do_not_become_monthly_returns():
    result = build(macro(("2020-01-31", 10), ("2020-03-31", 30)),
                   {"NASDAQCOM": prices(("2020-01-31", 100), ("2020-03-31", 121))})
    assert result["rows"][1]["NASDAQCOM_return_1m"] is None
    assert result["rows"][1]["mci_change"] is None


def test_insufficient_overlap_zero_variance_and_missing_macro_base():
    result = build(macro(("2020-05-31", None)), {"NASDAQCOM": prices(("2020-05-29", 100))})
    assert result["status"] == "insufficient_overlap" and result["base_date"] is None
    assert result["base_values"] == {} and result["rows"][0]["NASDAQCOM_indexed"] is None
    assert market._pearson([(10, 1), (10, 2), (10, 3)]) is None


def test_api_defaults_current_vintage_validation_and_sanitized_failure(monkeypatch):
    calls = []
    monkeypatch.setattr(market.pit, "get_history", lambda **kwargs: calls.append("pit") or {"observations": macro(("2020-05-31", 50))})
    monkeypatch.setattr(market.mci, "get_index_history", lambda **kwargs: calls.append("current") or {"observations": macro(("2020-05-31", 60))})
    monkeypatch.setattr(market, "load_market_history", lambda key, cutoff: prices(("2020-05-29", 9500)))
    client = TestClient(app)
    body = client.get("/api/v1/market-comparison").json()
    assert body["macro_history_type"] == "point_in_time" and body["mode"] == "indexed" and calls == ["pit"]
    assert body["rows"][0]["NASDAQCOM"] == 9500 and body["rows"][0]["mci"] == 50
    assert body["series"][1]["source"] == "FRED" and body["series"][1]["first_observation"] == "2020-05-29"
    assert client.get("/api/v1/market-comparison?macro_history_type=current_vintage").json()["rows"][0]["mci"] == 60
    for query in ("assets=GOLD", "assets=", "mode=normalized", "macro_history_type=other", "start_date=2020-06-01&end_date=2020-05-31"):
        assert client.get("/api/v1/market-comparison?" + query).status_code == 400
    assert client.get("/api/v1/market-comparison?start_date=bad").status_code == 422
    def fail(*args, **kwargs): raise RuntimeError("secret")
    monkeypatch.setattr(market, "load_market_history", fail)
    failed = client.get("/api/v1/market-comparison")
    assert failed.status_code == 503 and "secret" not in failed.text


def test_ingestion_reuses_snapshot_storage_and_preserves_missing_values(monkeypatch):
    payload = {"count": 2, "offset": 0, "limit": 100000, "units": "lin", "observations": [
        {"date": "2020-05-29", "realtime_start": "2020-06-01", "value": "9500"},
        {"date": "2020-05-30", "realtime_start": "2020-06-01", "value": "."}]}
    monkeypatch.setattr(ingestion, "fetch_series_observations", lambda key: payload)
    raw_calls, queries, inserted = [], [], []
    monkeypatch.setattr(ingestion, "save_raw_response", lambda key, data: raw_calls.append(deepcopy(data)) or "raw.json")
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql, params): queries.append((sql, params))
        def executemany(self, sql, rows): inserted.extend(rows)
    class Connection:
        committed = False
        def cursor(self): return Cursor()
        def commit(self): self.committed = True
        def rollback(self): pytest.fail("Valid ingestion should not roll back")
        def close(self): pass
    connection = Connection()
    monkeypatch.setattr(ingestion, "get_connection", lambda: connection)
    result = ingestion.ingest_market_asset("NASDAQCOM")
    assert result["missing_values"] == 1 and connection.committed
    assert inserted[0]["value"] == Decimal(9500) and inserted[1]["value"] is None
    assert "active = FALSE" in queries[1][0] and queries[0][1]["category"] == "market"
    assert "ON CONFLICT (series_id, observation_date, vintage_date)" in ingestion.INSERT_OBSERVATION_SQL
    payload["count"] = 3
    with pytest.raises(ValueError, match="incomplete"):
        ingestion.ingest_market_asset("NASDAQCOM")
    assert len(raw_calls) == 2  # invalid payload also preserved for inspection


def test_raw_snapshots_are_exclusive_and_never_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(raw_storage, "RAW_ROOT", tmp_path)
    first = raw_storage.save_raw_response("NASDAQCOM", {"value": 1})
    second = raw_storage.save_raw_response("NASDAQCOM", {"value": 2})
    assert first != second and first.read_text().strip() == '{\n  "value": 1\n}'
