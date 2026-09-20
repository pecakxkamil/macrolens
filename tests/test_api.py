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


def test_development_cors_allows_vite_origin():
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_development_cors_does_not_use_wildcard_origin():
    response = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers["access-control-allow-origin"] != "*"


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


def test_observation_history_serializes_dates_and_decimals(monkeypatch):
    monkeypatch.setattr(
        api_main.history,
        "load_series_history",
        lambda series_id, start_date, end_date: {
            "series_id": series_id,
            "name": "Unemployment Rate",
            "short_name": "Unemployment Rate",
            "frequency": "monthly",
            "unit": "percent",
            "history_type": "current_vintage",
            "start_date": start_date,
            "end_date": end_date,
            "observations": [
                {
                    "observation_date": date(2026, 1, 1),
                    "value": Decimal("4.125"),
                }
            ],
        },
    )

    response = client.get(
        "/api/v1/series/UNRATE/history",
        params={"start_date": "2026-01-01", "end_date": "2026-12-31"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["history_type"] == "current_vintage"
    assert payload["start_date"] == "2026-01-01"
    assert payload["end_date"] == "2026-12-31"
    assert payload["observations"] == [
        {"observation_date": "2026-01-01", "value": 4.125}
    ]
    assert not isinstance(payload["observations"][0]["value"], str)


def test_feature_history_preserves_feature_as_of_date(monkeypatch):
    monkeypatch.setattr(
        api_main.history,
        "load_feature_history",
        lambda series_id, feature_name, start_date, end_date: {
            "series_id": series_id,
            "feature_name": feature_name,
            "methodology_version": "v1",
            "history_type": "current_vintage",
            "observations": [
                {
                    "observation_date": date(2026, 1, 1),
                    "feature_as_of_date": date(2026, 3, 1),
                    "value": Decimal("4.2"),
                }
            ],
        },
    )

    response = client.get("/api/v1/series/UNRATE/features/level/history")

    assert response.status_code == 200
    assert response.json()["observations"] == [
        {
            "observation_date": "2026-01-01",
            "feature_as_of_date": "2026-03-01",
            "value": 4.2,
        }
    ]


def test_history_unknown_series_returns_404(monkeypatch):
    def unknown_series(*args):
        raise api_main.history.UnknownSeriesError("Unknown series: UNKNOWN")

    monkeypatch.setattr(api_main.history, "load_series_history", unknown_series)

    response = client.get("/api/v1/series/UNKNOWN/history")

    assert response.status_code == 404


def test_history_unknown_feature_returns_404(monkeypatch):
    def unsupported_feature(*args):
        raise api_main.history.UnsupportedFeatureError(
            "Unsupported feature for UNRATE: unknown"
        )

    monkeypatch.setattr(api_main.history, "load_feature_history", unsupported_feature)

    response = client.get("/api/v1/series/UNRATE/features/unknown/history")

    assert response.status_code == 404


def test_history_reversed_date_range_returns_clean_400(monkeypatch):
    def invalid_range(*args):
        raise api_main.history.InvalidDateRangeError(
            "start_date must be on or before end_date."
        )

    monkeypatch.setattr(api_main.history, "load_series_history", invalid_range)

    response = client.get(
        "/api/v1/series/UNRATE/history",
        params={"start_date": "2026-02-01", "end_date": "2026-01-01"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "start_date must be on or before end_date."
    }


def test_history_invalid_date_returns_422():
    response = client.get(
        "/api/v1/series/UNRATE/history",
        params={"start_date": "not-a-date"},
    )

    assert response.status_code == 422


def test_history_database_failure_does_not_leak_internal_details(monkeypatch):
    def fail_history(*args):
        raise RuntimeError("SELECT secret FROM observation_vintages password=secret")

    monkeypatch.setattr(api_main.history, "load_series_history", fail_history)

    response = client.get("/api/v1/series/UNRATE/history")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Historical chart data is temporarily unavailable."
    }
    assert "SELECT" not in response.text
    assert "password" not in response.text


def test_existing_health_endpoint_remains_unchanged():
    assert client.get("/health").json() == {"status": "ok"}
