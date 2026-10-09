from copy import deepcopy
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.analytics import features
from app.analytics import macro_conditions_index as mci
from app.api import main as api_main


# Constant histories yield exactly 50 for every domain (inflation 4% is 2pp
# from its 2% reference). This gives a hand-checkable 50-point composite.
INPUTS = {
    ("PAYEMS", "monthly_change_ma_3m"): 200,
    ("PAYEMS", "monthly_change_ma_6m"): 150,
    ("UNRATE", "change_3m"): -0.2,
    ("ICSA", "moving_average_4w"): 200000,
    ("ICSA", "moving_average_13w"): 220000,
    ("CPIAUCSL", "yoy"): 4,
    ("CPILFESL", "yoy"): 4,
    ("PCEPILFE", "yoy"): 4,
    ("GDPC1", "qoq_annualized"): 2,
    ("CFNAI", "moving_average_3m"): 0.1,
    ("INDPRO", "annualized_3m"): 2,
    ("PCEC96", "annualized_3m"): 2,
    ("DSPIC96", "annualized_3m"): 2,
    ("HOUST", "yoy"): 2,
    ("PERMIT", "yoy"): 2,
    ("HSN1F", "yoy"): 2,
    ("NFCI", "level"): -0.2,
}


@pytest.fixture
def histories():
    result = {}
    for (series, feature), value in INPUTS.items():
        observations = [
            {"observation_date": str(date(year, month, 1)), "value": Decimal(str(value)),
             "feature_as_of_date": "2026-10-01"}
            for year in range(2000, 2007) for month in range(1, 13)
            if series != "GDPC1" or month in (1, 4, 7, 10)
        ]
        result[(series, feature)] = {"series_id": series, "feature_name": feature,
                                     "observations": observations}
    return result


def component(row, domain, key):
    return next(item for item in row["domains"][domain]["components"] if item["key"] == key)


def row_at(rows, observed):
    return next(row for row in rows if row["observation_date"] == observed)


def patch_loader(monkeypatch, histories):
    calls = []

    def load(series, feature, start_date=None, end_date=None):
        calls.append((series, feature, start_date, end_date))
        return histories[(series, feature)]

    monkeypatch.setattr(mci.history, "load_feature_history", load)
    return calls


@pytest.mark.parametrize("value,expected", [(2, 100), (1, 75), (3, 75), (0, 50), (4, 50), (-2, 0), (6, 0), (-20, 0), (40, 0)])
def test_symmetric_inflation_reference(value, expected):
    assert mci.inflation_score(value) == expected


def test_percentiles_have_neutral_ties_and_explicit_orientation():
    assert mci.percentile_score(5, [5] * 60, "higher") == 50
    assert mci.percentile_score(2, [1, 2, 3], "higher") == 50
    assert mci.percentile_score(3, [1, 2, 3], "higher") == pytest.approx(100 * 2.5 / 3)
    assert mci.percentile_score(3, [1, 2, 3], "lower") == pytest.approx(100 / 6)
    with pytest.raises(ValueError):
        mci.percentile_score(2, [], "higher")
    with pytest.raises(ValueError):
        mci.percentile_score(2, [1, 2, 3], "unspecified")


def test_domain_weights_contributions_and_neutral_composite(histories):
    last = mci.build_monthly_index(histories, date(2006, 12, 31))[-1]
    assert last["mci"] == pytest.approx(50)
    assert len(last["domains"]) == 6
    assert {len(domain["components"]) for domain in last["domains"].values()} == {1, 2, 3}
    for domain in last["domains"].values():
        assert domain["score"] == pytest.approx(50)
        assert domain["weight"] == pytest.approx(1 / 6)
        assert domain["contribution"] == pytest.approx(50 / 6)
        assert sum(item["weight"] for item in domain["components"]) == pytest.approx(1)
        assert sum(item["overall_weight"] for item in domain["components"]) == pytest.approx(1 / 6)
        assert sum(item["domain_contribution"] for item in domain["components"]) == pytest.approx(domain["score"])
    assert sum(item["mci_contribution"] for domain in last["domains"].values()
               for item in domain["components"]) == pytest.approx(last["mci"])


def test_target_is_not_lower_is_always_better_and_financial_is_nfci_only(histories):
    for series in ("CPIAUCSL", "CPILFESL", "PCEPILFE"):
        for observation in histories[(series, "yoy")]["observations"]:
            observation["value"] = 2
    last = mci.build_monthly_index(histories, date(2006, 12, 31))[-1]
    assert last["domains"]["inflation"]["score"] == pytest.approx(100)
    assert last["mci"] == pytest.approx((50 * 5 + 100) / 6)
    assert [item["series_id"] for item in last["domains"]["financial_conditions"]["components"]] == ["NFCI"]
    assert all(item["series_id"] != "RSAFS" for item in last["domains"]["consumer"]["components"])


@pytest.mark.parametrize("key", [("PERMIT", "yoy"), ("NFCI", "level"), ("PCEC96", "annualized_3m")])
def test_missing_component_does_not_reweight_or_impute(histories, key):
    histories[key]["observations"] = histories[key]["observations"][:-1]
    last = mci.build_monthly_index(histories, date(2006, 12, 31))[-1]
    assert last["mci"] is None
    domains = [domain for domain in last["domains"].values() if domain["score"] is None]
    assert len(domains) == 1
    assert domains[0]["weight"] == pytest.approx(1 / 6)
    assert any(item["raw_value"] is None and item["score"] is None and item["status"] == "missing"
               for item in domains[0]["components"])


def test_warmup_and_historical_month_order(histories):
    rows = mci.build_monthly_index(histories, date(2006, 12, 15))
    dates = [row["observation_date"] for row in rows]
    assert dates == sorted(set(dates))
    assert dates[-1] == "2006-11-30"  # No partial or future December row.
    early = row_at(rows, "2004-11-30")
    assert component(early, "labor", "payroll_momentum")["reference_sample_size"] == 59
    assert component(early, "labor", "payroll_momentum")["status"] == "insufficient_history"
    assert early["mci"] is None
    assert component(row_at(rows, "2004-12-31"), "labor", "payroll_momentum")["score"] == 50
    assert component(row_at(rows, "2005-01-31"), "growth", "real_gdp")["reference_sample_size"] == 20
    assert row_at(rows, "2005-01-31")["mci"] == pytest.approx(50)


def test_no_future_observations_used_and_deterministic(histories):
    original = deepcopy(histories)
    early = mci.build_monthly_index(histories, date(2005, 12, 31))
    for values in histories.values():
        for item in values["observations"]:
            if item["observation_date"] > "2005-12-31":
                item["value"] = 100000
        values["observations"].reverse()
    full = mci.build_monthly_index(histories, date(2006, 12, 31))
    assert [row for row in full if row["observation_date"] <= "2005-12-31"] == early
    assert mci.build_monthly_index(original, date(2005, 12, 31)) == early


def test_gdp_is_lagged_then_carried_for_only_three_months(histories):
    values = histories[("GDPC1", "qoq_annualized")]["observations"]
    for item in values:
        if item["observation_date"] == "2006-01-01":
            item["value"] = 123
    histories[("GDPC1", "qoq_annualized")]["observations"] = [
        item for item in values if item["observation_date"] != "2006-04-01"
    ]
    rows = mci.build_monthly_index(histories, date(2006, 12, 31))
    march = component(row_at(rows, "2006-03-31"), "growth", "real_gdp")
    assert march["source_observation_date"] == "2005-10-01"
    assert march["raw_value"] == 2
    april = component(row_at(rows, "2006-04-30"), "growth", "real_gdp")
    june = component(row_at(rows, "2006-06-30"), "growth", "real_gdp")
    assert april["raw_value"] == june["raw_value"] == 123
    assert april["score"] == june["score"]
    assert not april["carried_forward"] and june["carried_forward"]
    assert component(row_at(rows, "2006-07-31"), "growth", "real_gdp")["status"] == "missing"
    assert row_at(rows, "2006-07-31")["mci"] is None


def test_weekly_sampling_and_gaps_require_same_date_inputs(histories):
    for feature, value in (("moving_average_4w", 180000), ("moving_average_13w", 220000)):
        histories[("ICSA", feature)]["observations"].append({
            "observation_date": "2006-12-28", "feature_as_of_date": "2026-10-02", "value": value,
        })
    last = mci.build_monthly_index(histories, date(2006, 12, 31))[-1]
    claims = component(last, "labor", "claims_momentum")
    assert claims["raw_value"] == -40000
    assert claims["source_observation_date"] == "2006-12-28"
    assert claims["reference_sample_size"] == 84  # One sample per month, not one per week.
    assert claims["score"] > 50
    histories[("ICSA", "moving_average_13w")]["observations"] = [
        item for item in histories[("ICSA", "moving_average_13w")]["observations"]
        if not item["observation_date"].startswith("2006-12")
    ]
    assert component(mci.build_monthly_index(histories, date(2006, 12, 31))[-1],
                     "labor", "claims_momentum")["status"] == "missing"


@pytest.mark.parametrize("invalid", [None, float("nan"), float("inf"), float("-inf")])
def test_nonfinite_values_are_missing_not_fabricated(histories, invalid):
    histories[("NFCI", "level")]["observations"][-1]["value"] = invalid
    last = mci.build_monthly_index(histories, date(2006, 12, 31))[-1]
    assert last["mci"] is None
    assert last["domains"]["financial_conditions"]["score"] is None


def test_scores_always_bounded(histories):
    for (series, _), response in histories.items():
        for index, item in enumerate(response["observations"]):
            item["value"] = (-1 if index % 2 else 1) * index ** 2
    for row in mci.build_monthly_index(histories, date(2006, 12, 31)):
        scores = [row["mci"]] + [item["score"] for item in row["domains"].values()]
        scores += [item["score"] for domain in row["domains"].values() for item in domain["components"]]
        assert all(score is None or 0 <= score <= 100 for score in scores)


def test_history_range_filters_after_full_normalization(monkeypatch, histories):
    calls = patch_loader(monkeypatch, histories)
    result = mci.get_index_history(date(2006, 10, 1), date(2006, 12, 31))
    assert [row["observation_date"] for row in result["observations"]] == ["2006-10-31", "2006-11-30", "2006-12-31"]
    assert all(row["mci"] == pytest.approx(50) for row in result["observations"])
    assert result["history_type"] == "current_vintage"
    assert result["methodology_version"] == "v1"
    assert len(calls) == 17 and all(call[2] is None for call in calls)
    assert all(call[3] == date(2006, 12, 31) for call in calls)


def test_current_uses_latest_complete_month_and_preserves_freshness(monkeypatch, histories):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2006, 12, 31)
    monkeypatch.setattr(mci, "date", FixedDate)
    histories[("PERMIT", "yoy")]["observations"] = histories[("PERMIT", "yoy")]["observations"][:-1]
    patch_loader(monkeypatch, histories)

    def forbidden(*args, **kwargs):
        raise AssertionError("Do not recompute stored features")
    monkeypatch.setattr(features, "calculate_features", forbidden)
    current = mci.get_current_index()
    assert current["observation_date"] == "2006-11-30"
    assert current["latest_evaluated_month"] == "2006-12-31"
    assert current["mci"] == pytest.approx(50)
    assert current["component_as_of_dates"]["labor"] == "2026-10-01"
    assert current["history_type"] == "current_vintage"
    assert current["methodology_version"] == "v1"


def test_empty_histories_return_null_current_and_empty_history(monkeypatch, histories):
    for response in histories.values():
        response["observations"] = []
    patch_loader(monkeypatch, histories)
    current = mci.get_current_index()
    assert current["mci"] is None and current["observation_date"] is None
    assert len(current["domains"]) == 6
    assert all(domain["score"] is None for domain in current["domains"].values())
    assert mci.get_index_history()["observations"] == []


def test_api_history_shape_validation_and_sanitized_errors(monkeypatch, histories):
    patch_loader(monkeypatch, histories)
    client = TestClient(api_main.app)
    response = client.get("/api/v1/economy/us/mci/history?start_date=2006-10-01&end_date=2006-12-31")
    assert response.status_code == 200
    row = response.json()["observations"][-1]
    assert set(row) == {"observation_date", "mci", "labor", "inflation", "growth", "consumer", "housing", "financial_conditions"}
    assert row["mci"] == pytest.approx(50)
    assert client.get("/api/v1/economy/us/mci/history?start_date=2006-12-31&end_date=2006-01-01").status_code == 400
    assert client.get("/api/v1/economy/us/mci/history?start_date=invalid").status_code == 422

    def fail(*args, **kwargs):
        raise RuntimeError("secret credentials")
    monkeypatch.setattr(mci.history, "load_feature_history", fail)
    for endpoint in ("/api/v1/economy/us/mci", "/api/v1/economy/us/mci/history"):
        response = client.get(endpoint)
        assert response.status_code == 503
        assert response.json() == {"detail": api_main.MCI_UNAVAILABLE_DETAIL}
        assert "secret" not in response.text


def test_api_current_decomposition_and_metadata(monkeypatch, histories):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2006, 12, 31)
    monkeypatch.setattr(mci, "date", FixedDate)
    patch_loader(monkeypatch, histories)
    response = TestClient(api_main.app).get("/api/v1/economy/us/mci")
    assert response.status_code == 200
    result = response.json()
    assert result["mci"] == pytest.approx(50)
    assert result["methodology_version"] == "v1" and result["history_type"] == "current_vintage"
    assert result["domains"]["labor"]["components"][0]["raw_value"] == 50
    assert result["domains"]["labor"]["components"][0]["inputs"] == [
        {"feature_name": "monthly_change_ma_3m", "value": 200.0},
        {"feature_name": "monthly_change_ma_6m", "value": 150.0},
    ]
