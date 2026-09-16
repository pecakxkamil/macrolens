from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api import main as api_main


client = TestClient(api_main.app)


def sample_snapshot(name="snapshot"):
    return {
        "name": name,
        "as_of_date": date(2026, 9, 4),
        "updated_at": datetime(2026, 9, 4, 12, 30, 0),
        "value": Decimal("1.25"),
        "nested": {
            "observation_date": date(2026, 8, 1),
            "feature_value": Decimal("2.50"),
        },
    }


def patch_domain_builders(monkeypatch):
    calls = {}

    def patch_builder(module, function_name, domain):
        def fake_builder():
            calls[domain] = calls.get(domain, 0) + 1
            return sample_snapshot(domain)

        monkeypatch.setattr(module, function_name, fake_builder)

    patch_builder(api_main.labor_snapshot, "get_labor_snapshot", "labor")
    patch_builder(api_main.inflation_snapshot, "get_inflation_snapshot", "inflation")
    patch_builder(api_main.growth_snapshot, "get_growth_snapshot", "growth")
    patch_builder(api_main.consumer_snapshot, "get_consumer_snapshot", "consumer")
    patch_builder(api_main.housing_snapshot, "get_housing_snapshot", "housing")
    patch_builder(
        api_main.financial_conditions_snapshot,
        "get_financial_conditions_snapshot",
        "financial_conditions",
    )

    return calls


def test_health_returns_200():
    response = client.get("/health")

    assert response.status_code == 200


def test_health_payload():
    response = client.get("/health")

    assert response.json() == {"status": "ok"}


def test_us_economy_endpoint_returns_aggregator_result(monkeypatch):
    expected = {
        "as_of_date": "2026-09-04",
        "component_as_of_dates": {"labor": "2026-09-04"},
        "labor": {"overall_momentum": "mixed"},
    }

    monkeypatch.setattr(
        api_main.usa_economy_now,
        "build_usa_economy_now",
        lambda: expected,
    )

    response = client.get("/api/v1/economy/us")

    assert response.status_code == 200
    assert response.json() == expected


def test_us_economy_endpoint_preserves_2s10s_freshness_fields(monkeypatch):
    expected = {
        "as_of_date": "2026-09-04",
        "component_as_of_dates": {
            "financial_conditions": "2026-09-04",
        },
        "financial_conditions": {
            "yield_curve_2s10s": {
                "observation_date": "2026-08-01",
                "feature_as_of_date": "2026-09-04",
                "dgs2": Decimal("4.0"),
                "dgs10": Decimal("4.5"),
                "spread": Decimal("0.5"),
                "shape": "positive",
            },
        },
    }

    monkeypatch.setattr(
        api_main.usa_economy_now,
        "build_usa_economy_now",
        lambda: expected,
    )

    response = client.get("/api/v1/economy/us")

    assert response.status_code == 200
    curve = response.json()["financial_conditions"]["yield_curve_2s10s"]
    assert curve == {
        "observation_date": "2026-08-01",
        "feature_as_of_date": "2026-09-04",
        "dgs2": 4.0,
        "dgs10": 4.5,
        "spread": 0.5,
        "shape": "positive",
    }


def test_all_six_domain_routes_exist(monkeypatch):
    patch_domain_builders(monkeypatch)

    for route in (
        "/api/v1/economy/us/labor",
        "/api/v1/economy/us/inflation",
        "/api/v1/economy/us/growth",
        "/api/v1/economy/us/consumer",
        "/api/v1/economy/us/housing",
        "/api/v1/economy/us/financial-conditions",
    ):
        response = client.get(route)
        assert response.status_code == 200


def test_every_domain_route_calls_its_existing_builder(monkeypatch):
    calls = patch_domain_builders(monkeypatch)

    client.get("/api/v1/economy/us/labor")
    client.get("/api/v1/economy/us/inflation")
    client.get("/api/v1/economy/us/growth")
    client.get("/api/v1/economy/us/consumer")
    client.get("/api/v1/economy/us/housing")
    client.get("/api/v1/economy/us/financial-conditions")

    assert calls == {
        "labor": 1,
        "inflation": 1,
        "growth": 1,
        "consumer": 1,
        "housing": 1,
        "financial_conditions": 1,
    }


def test_returned_nested_structures_are_preserved(monkeypatch):
    monkeypatch.setattr(
        api_main.labor_snapshot,
        "get_labor_snapshot",
        lambda: sample_snapshot("labor"),
    )

    response = client.get("/api/v1/economy/us/labor")

    assert response.json()["nested"] == {
        "observation_date": "2026-08-01",
        "feature_value": 2.5,
    }


def test_decimal_values_serialize_as_json_numbers(monkeypatch):
    monkeypatch.setattr(
        api_main.growth_snapshot,
        "get_growth_snapshot",
        lambda: sample_snapshot("growth"),
    )

    payload = client.get("/api/v1/economy/us/growth").json()

    assert payload["value"] == 1.25
    assert not isinstance(payload["value"], str)
    assert payload["nested"]["feature_value"] == 2.5
    assert not isinstance(payload["nested"]["feature_value"], str)


def test_dates_serialize_as_iso_strings(monkeypatch):
    monkeypatch.setattr(
        api_main.consumer_snapshot,
        "get_consumer_snapshot",
        lambda: sample_snapshot("consumer"),
    )

    payload = client.get("/api/v1/economy/us/consumer").json()

    assert payload["as_of_date"] == "2026-09-04"
    assert payload["updated_at"] == "2026-09-04T12:30:00"
    assert payload["nested"]["observation_date"] == "2026-08-01"


def test_snapshot_failure_returns_http_503(monkeypatch):
    def fail_snapshot():
        raise RuntimeError("No v1 features found for PAYEMS.")

    monkeypatch.setattr(api_main.labor_snapshot, "get_labor_snapshot", fail_snapshot)

    response = client.get("/api/v1/economy/us/labor")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Current macro snapshot is temporarily unavailable."
    }


def test_raw_internal_exception_text_is_not_exposed(monkeypatch):
    def fail_snapshot():
        raise RuntimeError(
            "No v1 features found for PAYEMS using SQL SELECT with password=secret."
        )

    monkeypatch.setattr(
        api_main.usa_economy_now,
        "build_usa_economy_now",
        fail_snapshot,
    )

    response = client.get("/api/v1/economy/us")
    response_text = response.text

    assert response.status_code == 503
    assert "PAYEMS" not in response_text
    assert "SELECT" not in response_text
    assert "password" not in response_text
    assert "Current macro snapshot is temporarily unavailable." in response_text


def test_no_historical_as_of_parameter_is_advertised_in_v1():
    openapi = client.get("/openapi.json").json()

    for path in (
        "/api/v1/economy/us",
        "/api/v1/economy/us/labor",
        "/api/v1/economy/us/inflation",
        "/api/v1/economy/us/growth",
        "/api/v1/economy/us/consumer",
        "/api/v1/economy/us/housing",
        "/api/v1/economy/us/financial-conditions",
    ):
        operation = openapi["paths"][path]["get"]
        assert "parameters" not in operation
