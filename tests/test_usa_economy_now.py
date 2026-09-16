from datetime import date

from app.analytics import usa_economy_now


def fake_domain_snapshots():
    return {
        "labor": {
            "as_of_date": "2026-09-01",
            "overall_momentum": "mixed",
            "payrolls": {"momentum": "improving"},
            "unemployment": {"momentum": "stable"},
            "initial_claims": {"momentum": "weakening"},
        },
        "inflation": {
            "as_of_date": "2026-09-03",
            "headline_cpi": {"momentum": "decelerating"},
            "core_cpi": {"momentum": "accelerating"},
            "headline_pce": {"momentum": "stable"},
            "core_pce": {"momentum": "decelerating"},
            "employment_cost_index": {"yoy": 3.7},
            "average_hourly_earnings": {"yoy": 4.1},
        },
        "growth": {
            "as_of_date": "2026-08-30",
            "real_gdp": {"momentum": "accelerating"},
            "cfnai": {"position": "above_trend"},
            "industrial_production": {"momentum": "decelerating"},
            "capacity_utilization": {"direction": "falling"},
            "durable_goods_orders": {"latest_direction": "stable"},
        },
        "consumer": {
            "as_of_date": "2026-09-02",
            "retail_sales": {"momentum": "accelerating"},
            "real_consumption": {"momentum": "stable"},
            "real_disposable_income": {"momentum": "decelerating"},
            "saving_rate": {"direction": "rising"},
        },
        "housing": {
            "as_of_date": "2026-08-28",
            "housing_starts": {"direction": "rising"},
            "building_permits": {"direction": "falling"},
            "new_home_sales": {"direction": "stable"},
            "mortgage_rate": {"direction": "rising"},
        },
        "financial_conditions": {
            "as_of_date": "2026-09-04",
            "fed_funds_rate": {"level": 5.33},
            "yield_curve_2s10s": {"spread": -0.25, "shape": "inverted"},
            "nfci": {"position": "tighter_than_average", "direction": "tightening"},
        },
    }


def patch_domain_builders(monkeypatch, snapshots=None):
    snapshots = snapshots or fake_domain_snapshots()
    calls = {}

    def patch_builder(module, function_name, domain):
        def fake_builder(as_of_date=None):
            calls[domain] = as_of_date
            return snapshots[domain]

        monkeypatch.setattr(module, function_name, fake_builder)

    patch_builder(
        usa_economy_now.labor_snapshot,
        "get_labor_snapshot",
        "labor",
    )
    patch_builder(
        usa_economy_now.inflation_snapshot,
        "get_inflation_snapshot",
        "inflation",
    )
    patch_builder(
        usa_economy_now.growth_snapshot,
        "get_growth_snapshot",
        "growth",
    )
    patch_builder(
        usa_economy_now.consumer_snapshot,
        "get_consumer_snapshot",
        "consumer",
    )
    patch_builder(
        usa_economy_now.housing_snapshot,
        "get_housing_snapshot",
        "housing",
    )
    patch_builder(
        usa_economy_now.financial_conditions_snapshot,
        "get_financial_conditions_snapshot",
        "financial_conditions",
    )

    return snapshots, calls


def test_all_six_domain_snapshots_are_present(monkeypatch):
    patch_domain_builders(monkeypatch)

    snapshot = usa_economy_now.build_usa_economy_now()

    assert set(snapshot.keys()) == {
        "as_of_date",
        "component_as_of_dates",
        "labor",
        "inflation",
        "growth",
        "consumer",
        "housing",
        "financial_conditions",
    }


def test_each_existing_snapshot_builder_is_called(monkeypatch):
    _, calls = patch_domain_builders(monkeypatch)

    usa_economy_now.build_usa_economy_now()

    assert set(calls.keys()) == {
        "labor",
        "inflation",
        "growth",
        "consumer",
        "housing",
        "financial_conditions",
    }


def test_requested_as_of_date_is_passed_to_all_builders(monkeypatch):
    _, calls = patch_domain_builders(monkeypatch)
    requested_as_of_date = date(2026, 9, 4)

    usa_economy_now.build_usa_economy_now(requested_as_of_date)

    assert calls == {
        "labor": requested_as_of_date,
        "inflation": requested_as_of_date,
        "growth": requested_as_of_date,
        "consumer": requested_as_of_date,
        "housing": requested_as_of_date,
        "financial_conditions": requested_as_of_date,
    }


def test_explicit_requested_as_of_date_is_preserved_at_top_level(monkeypatch):
    patch_domain_builders(monkeypatch)

    snapshot = usa_economy_now.build_usa_economy_now(date(2026, 9, 4))

    assert snapshot["as_of_date"] == "2026-09-04"


def test_latest_component_as_of_date_becomes_top_level_without_requested_date(
    monkeypatch,
):
    patch_domain_builders(monkeypatch)

    snapshot = usa_economy_now.build_usa_economy_now()

    assert snapshot["as_of_date"] == "2026-09-04"


def test_component_as_of_dates_contains_all_six_domains(monkeypatch):
    snapshots, _ = patch_domain_builders(monkeypatch)

    snapshot = usa_economy_now.build_usa_economy_now()

    assert snapshot["component_as_of_dates"] == {
        domain: domain_snapshot["as_of_date"]
        for domain, domain_snapshot in snapshots.items()
    }


def test_nested_domain_snapshots_remain_unchanged(monkeypatch):
    snapshots, _ = patch_domain_builders(monkeypatch)

    snapshot = usa_economy_now.build_usa_economy_now()

    for domain, domain_snapshot in snapshots.items():
        assert snapshot[domain] is domain_snapshot


def test_no_overall_score_or_state_exists(monkeypatch):
    patch_domain_builders(monkeypatch)

    snapshot = usa_economy_now.build_usa_economy_now()

    assert "overall_score" not in snapshot
    assert "macro_score" not in snapshot
    assert "overall_state" not in snapshot
    assert "economic_state" not in snapshot
    assert "macro_state" not in snapshot
    assert "usa_economy_state" not in snapshot
    assert "classification" not in snapshot


def test_cli_output_contains_all_six_section_headings_and_freshness(monkeypatch, capsys):
    patch_domain_builders(monkeypatch)
    snapshot = usa_economy_now.build_usa_economy_now()

    usa_economy_now.print_usa_economy_now(snapshot)

    output = capsys.readouterr().out
    output_lines = output.splitlines()
    section_headings = [
        "LABOR",
        "INFLATION",
        "GROWTH",
        "CONSUMER",
        "HOUSING",
        "FINANCIAL CONDITIONS",
    ]

    assert "USA ECONOMY NOW" in output
    assert "Component freshness:" in output
    assert "Labor: 2026-09-01" in output
    assert "Inflation: 2026-09-03" in output
    assert "Growth: 2026-08-30" in output
    assert "Consumer: 2026-09-02" in output
    assert "Housing: 2026-08-28" in output
    assert "Financial Conditions: 2026-09-04" in output
    assert [line for line in output_lines if line in section_headings] == section_headings


def test_historical_as_of_failure_is_graceful(monkeypatch, capsys):
    def fail_build(as_of_date=None):
        raise RuntimeError("No v1 features found for PAYEMS.")

    monkeypatch.setattr(usa_economy_now, "build_usa_economy_now", fail_build)
    monkeypatch.setattr(
        usa_economy_now.sys,
        "argv",
        ["usa_economy_now", "2026-07-31"],
    )

    exit_code = usa_economy_now.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "USA Economy Now unavailable for 2026-07-31:" in captured.err
    assert (
        "historical point-in-time features are not available for all required domains."
        in captured.err
    )


def test_historical_as_of_failure_does_not_leak_raw_series_detail(
    monkeypatch,
    capsys,
):
    def fail_build(as_of_date=None):
        raise RuntimeError("No v1 features found for PAYEMS.")

    monkeypatch.setattr(usa_economy_now, "build_usa_economy_now", fail_build)
    monkeypatch.setattr(
        usa_economy_now.sys,
        "argv",
        ["usa_economy_now", "2026-07-31"],
    )

    usa_economy_now.main()

    captured = capsys.readouterr()
    assert "PAYEMS" not in captured.err
    assert "No v1 features found" not in captured.err


def test_current_cli_aggregation_still_works(monkeypatch, capsys):
    patch_domain_builders(monkeypatch)
    monkeypatch.setattr(usa_economy_now.sys, "argv", ["usa_economy_now"])

    exit_code = usa_economy_now.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "USA ECONOMY NOW" in captured.out
    assert "As of: 2026-09-04" in captured.out
