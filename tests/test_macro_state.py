import copy
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.analytics import features, macro_state
from app.api import main as api_main


@pytest.fixture
def snapshot():
    return json.loads((Path(__file__).parent / "fixtures" / "macro_state_snapshot.json").read_text())


def test_reuses_aggregated_snapshot_without_recalculation(monkeypatch, snapshot):
    calls = []
    original = copy.deepcopy(snapshot)

    def existing_builder():
        calls.append("usa_economy_now")
        return snapshot

    def forbidden(*args, **kwargs):
        raise AssertionError("Macro State must not recalculate features")

    monkeypatch.setattr(macro_state.usa_economy_now, "build_usa_economy_now", existing_builder)
    monkeypatch.setattr(features, "calculate_features", forbidden)
    result = macro_state.build_macro_state()
    assert calls == ["usa_economy_now"]
    assert snapshot == original
    assert result == macro_state.build_macro_state(snapshot)


def test_six_domains_readings_and_freshness_preserved(snapshot):
    result = macro_state.build_macro_state(snapshot)
    assert set(result["domains"]) == {
        "labor", "inflation", "growth", "consumer", "housing", "financial_conditions",
    }
    assert result["as_of_date"] == snapshot["as_of_date"]
    assert result["component_as_of_dates"] == snapshot["component_as_of_dates"]
    for key, domain in result["domains"].items():
        assert domain["as_of_date"] == snapshot[key]["as_of_date"]
        for reading in domain["readings"]:
            component = snapshot[key][reading["key"]]
            assert reading["observation_date"] == component["observation_date"]
            assert reading["feature_as_of_date"] == component["feature_as_of_date"]
    labor = result["domains"]["labor"]
    assert labor["readings"][0]["value"] == 180
    assert labor["classifications"]["overall_momentum"] == "mixed"
    consumer = result["domains"]["consumer"]
    assert consumer["readings"][0]["label"] == "Retail sales YoY (nominal)"
    assert consumer["readings"][0]["value"] == snapshot["consumer"]["retail_sales"]["yoy"]


def test_existing_classifications_are_authoritative_even_if_readings_disagree(snapshot):
    snapshot["labor"]["overall_momentum"] = "improving"
    snapshot["labor"]["payrolls"]["momentum"] = "weakening"
    snapshot["inflation"]["headline_cpi"]["momentum"] = "stable"
    result = macro_state.build_macro_state(snapshot)
    assert result["domains"]["labor"]["classifications"]["overall_momentum"] == "improving"
    assert result["domains"]["labor"]["classifications"]["payrolls.momentum"] == "weakening"
    assert result["domains"]["inflation"]["classifications"]["headline_cpi.momentum"] == "stable"


def test_deterministic_evidence_is_based_on_existing_states(snapshot):
    first = macro_state.build_macro_state(snapshot)
    assert first == macro_state.build_macro_state(copy.deepcopy(snapshot))
    assert first["domains"]["labor"]["evidence"] == [
        "Labor overall momentum is mixed.",
        "Payroll momentum is improving.",
        "Initial claims momentum is weakening.",
        "Continuing claims momentum is weakening.",
    ]
    assert "Headline CPI momentum is decelerating." in first["domains"]["inflation"]["evidence"]
    for domain in first["domains"].values():
        assert 2 <= len(domain["evidence"]) <= 4


@pytest.mark.parametrize("domain,left_path,left,right_path,right", [
    ("labor", "overall_momentum", "improving", "payrolls.momentum", "weakening"),
    ("growth", "real_gdp.momentum", "decelerating", "industrial_production.momentum", "accelerating"),
    ("housing", "housing_starts.direction", "falling", "building_permits.direction", "rising"),
])
def test_curated_cross_currents_require_both_explicit_states(snapshot, domain, left_path, left, right_path, right):
    def set_field(path, value):
        component = snapshot[domain]
        parts = path.split(".")
        for part in parts[:-1]:
            component = component[part]
        component[parts[-1]] = value

    set_field(left_path, left)
    set_field(right_path, right)
    result = macro_state.build_macro_state(snapshot)
    current = next(item for item in result["cross_currents"] if item["domain"] == domain)
    assert [item["classification"] for item in current["evidence"]] == [left, right]
    assert "mixed directional signals" in current["summary"]
    set_field(right_path, "stable")
    assert not any(item["domain"] == domain for item in macro_state.build_macro_state(snapshot)["cross_currents"])
    set_field(right_path, right)
    set_field(left_path, "stable")
    assert not any(item["domain"] == domain for item in macro_state.build_macro_state(snapshot)["cross_currents"])


def test_no_cross_current_for_stable_states(snapshot):
    snapshot["labor"]["overall_momentum"] = "mixed"
    snapshot["growth"]["real_gdp"]["momentum"] = "stable"
    snapshot["housing"]["housing_starts"]["direction"] = "stable"
    assert macro_state.build_macro_state(snapshot)["cross_currents"] == []


def test_no_global_score_probability_regime_or_signals(snapshot):
    result = macro_state.build_macro_state(snapshot)
    assert set(result) == {"as_of_date", "component_as_of_dates", "domains", "cross_currents"}
    text = json.dumps(result).lower()
    for forbidden in ("macro_score", "recession", "probability", "regime", "bullish", "bearish", "risk_on", "risk_off", "trading_signal"):
        assert forbidden not in text
    assert "overall_momentum" not in result["domains"]["inflation"]["classifications"]


def test_api_serializes_existing_numbers_dates_and_six_domains(monkeypatch, snapshot):
    snapshot["labor"]["payrolls"]["monthly_change"] = Decimal("180.25")
    snapshot["labor"]["payrolls"]["observation_date"] = date(2026, 8, 1)
    monkeypatch.setattr(macro_state.usa_economy_now, "build_usa_economy_now", lambda: snapshot)
    response = TestClient(api_main.app).get("/api/v1/economy/us/state")
    assert response.status_code == 200
    body = response.json()
    assert len(body["domains"]) == 6
    assert body["component_as_of_dates"] == snapshot["component_as_of_dates"]
    payroll = body["domains"]["labor"]["readings"][0]
    assert payroll["value"] == 180.25
    assert payroll["observation_date"] == "2026-08-01"


def test_api_failure_is_sanitized(monkeypatch):
    def fail():
        raise RuntimeError("secret database connection details")
    monkeypatch.setattr(macro_state.usa_economy_now, "build_usa_economy_now", fail)
    response = TestClient(api_main.app).get("/api/v1/economy/us/state")
    assert response.status_code == 503
    assert response.json() == {"detail": api_main.SNAPSHOT_UNAVAILABLE_DETAIL}
    assert "secret" not in response.text
