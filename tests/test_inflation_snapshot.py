from app.analytics.inflation_snapshot import (
    build_inflation_snapshot,
    classify_inflation_momentum,
    print_inflation_snapshot,
)
from app.analytics.labor_state import build_labor_momentum_state


def component_features(**values):
    return {
        "observation_date": "2026-08-01",
        "feature_as_of_date": "2026-09-04",
        **values,
    }


def price_features(annualized_3m, yoy):
    return component_features(mom=0.2, yoy=yoy, annualized_3m=annualized_3m)


def test_inflation_momentum_accelerating():
    assert classify_inflation_momentum(4.0, 3.0) == "accelerating"


def test_inflation_momentum_decelerating():
    assert classify_inflation_momentum(2.0, 3.0) == "decelerating"


def test_inflation_momentum_stable():
    assert classify_inflation_momentum(3.0, 3.0) == "stable"


def test_snapshot_contains_all_six_components():
    snapshot = build_inflation_snapshot(
        "2026-09-04",
        price_features(2.5, 3.0),
        price_features(3.5, 3.0),
        price_features(3.0, 3.0),
        price_features(2.0, 3.0),
        component_features(qoq=0.8, yoy=3.7),
        component_features(mom=0.3, yoy=4.1, annualized_3m=3.8),
    )

    assert set(snapshot.keys()) == {
        "as_of_date",
        "headline_cpi",
        "core_cpi",
        "headline_pce",
        "core_pce",
        "employment_cost_index",
        "average_hourly_earnings",
    }


def test_snapshot_preserves_observation_and_feature_as_of_dates():
    snapshot = build_inflation_snapshot(
        "2026-09-04",
        price_features(2.5, 3.0),
        price_features(3.5, 3.0),
        price_features(3.0, 3.0),
        price_features(2.0, 3.0),
        component_features(qoq=0.8, yoy=3.7),
        component_features(mom=0.3, yoy=4.1, annualized_3m=3.8),
    )

    for component_name in (
        "headline_cpi",
        "core_cpi",
        "headline_pce",
        "core_pce",
        "employment_cost_index",
        "average_hourly_earnings",
    ):
        assert snapshot[component_name]["observation_date"] == "2026-08-01"
        assert snapshot[component_name]["feature_as_of_date"] == "2026-09-04"


def test_eci_and_wages_are_exposed_without_good_bad_classification():
    snapshot = build_inflation_snapshot(
        "2026-09-04",
        price_features(2.5, 3.0),
        price_features(3.5, 3.0),
        price_features(3.0, 3.0),
        price_features(2.0, 3.0),
        component_features(qoq=0.8, yoy=3.7),
        component_features(mom=0.3, yoy=4.1, annualized_3m=3.8),
    )

    assert snapshot["employment_cost_index"] == {
        "observation_date": "2026-08-01",
        "feature_as_of_date": "2026-09-04",
        "qoq": 0.8,
        "yoy": 3.7,
    }
    assert snapshot["average_hourly_earnings"] == {
        "observation_date": "2026-08-01",
        "feature_as_of_date": "2026-09-04",
        "mom": 0.3,
        "yoy": 4.1,
        "annualized_3m": 3.8,
    }


def test_average_hourly_earnings_console_output_includes_required_fields(capsys):
    snapshot = build_inflation_snapshot(
        "2026-09-04",
        price_features(2.5, 3.0),
        price_features(3.5, 3.0),
        price_features(3.0, 3.0),
        price_features(2.0, 3.0),
        component_features(qoq=0.8, yoy=3.7),
        component_features(mom=0.3, yoy=4.1, annualized_3m=3.8),
    )

    print_inflation_snapshot(snapshot)
    output = capsys.readouterr().out

    assert "Average Hourly Earnings:" in output
    assert "Observation date: 2026-08-01" in output
    assert "Feature as of: 2026-09-04" in output
    assert "MoM: 0.3" in output
    assert "YoY: 4.1" in output
    assert "3M annualized: 3.8" in output


def test_existing_labor_behavior_remains_unchanged():
    labor_state = build_labor_momentum_state(
        "2026-09-04",
        {
            "monthly_change": 180,
            "monthly_change_ma_3m": 220,
            "monthly_change_ma_6m": 200,
        },
        {"level": 4.1, "change_3m": -0.1},
        {"moving_average_4w": 240000, "moving_average_13w": 220000},
    )

    assert labor_state["payrolls"]["momentum"] == "improving"
    assert labor_state["unemployment"]["momentum"] == "improving"
    assert labor_state["claims"]["momentum"] == "weakening"
    assert labor_state["overall_momentum"] == "improving"
