from app.analytics.labor_snapshot import (
    build_labor_snapshot,
    classify_continuing_claims_momentum,
    classify_direction_from_change,
)


def component_features(**values):
    return {
        "observation_date": "2026-08-01",
        "feature_as_of_date": "2026-09-04",
        **values,
    }


def test_ccsa_momentum_classification():
    assert classify_continuing_claims_momentum(210000, 225000) == "improving"
    assert classify_continuing_claims_momentum(240000, 225000) == "weakening"
    assert classify_continuing_claims_momentum(225000, 225000) == "stable"


def test_jtsjol_direction():
    assert classify_direction_from_change(1) == "rising"
    assert classify_direction_from_change(-1) == "falling"
    assert classify_direction_from_change(0) == "stable"


def test_civpart_direction():
    assert classify_direction_from_change(0.2) == "rising"
    assert classify_direction_from_change(-0.2) == "falling"
    assert classify_direction_from_change(0) == "stable"


def test_snapshot_structure_contains_all_components_and_freshness_dates():
    snapshot = build_labor_snapshot(
        "2026-09-04",
        component_features(
            monthly_change=180,
            monthly_change_ma_3m=220,
            monthly_change_ma_6m=200,
        ),
        component_features(level=4.1, change_3m=0.1),
        component_features(moving_average_4w=220000, moving_average_13w=220000),
        component_features(moving_average_4w=2100000, moving_average_13w=2200000),
        component_features(level=7400, change_3m=100, yoy=4.0),
        component_features(level=62.5, change_3m=-0.1, moving_average_3m=62.6),
        component_features(mom=0.3, yoy=4.1, annualized_3m=3.8),
    )

    assert set(snapshot.keys()) == {
        "as_of_date",
        "payrolls",
        "unemployment",
        "initial_claims",
        "continuing_claims",
        "job_openings",
        "labor_force_participation",
        "average_hourly_earnings",
        "overall_momentum",
    }
    for component_name in (
        "payrolls",
        "unemployment",
        "initial_claims",
        "continuing_claims",
        "job_openings",
        "labor_force_participation",
        "average_hourly_earnings",
    ):
        assert snapshot[component_name]["observation_date"] == "2026-08-01"
        assert snapshot[component_name]["feature_as_of_date"] == "2026-09-04"


def test_snapshot_preserves_existing_overall_labor_momentum_v1_behavior():
    snapshot = build_labor_snapshot(
        "2026-09-04",
        component_features(
            monthly_change=180,
            monthly_change_ma_3m=220,
            monthly_change_ma_6m=200,
        ),
        component_features(level=4.1, change_3m=-0.1),
        component_features(moving_average_4w=240000, moving_average_13w=220000),
        component_features(moving_average_4w=2500000, moving_average_13w=2200000),
        component_features(level=7400, change_3m=-100, yoy=-2.0),
        component_features(level=62.5, change_3m=-0.1, moving_average_3m=62.6),
        component_features(mom=0.5, yoy=5.0, annualized_3m=6.0),
    )

    assert snapshot["payrolls"]["momentum"] == "improving"
    assert snapshot["unemployment"]["momentum"] == "improving"
    assert snapshot["initial_claims"]["momentum"] == "weakening"
    assert snapshot["continuing_claims"]["momentum"] == "weakening"
    assert snapshot["job_openings"]["direction"] == "falling"
    assert snapshot["labor_force_participation"]["direction"] == "falling"
    assert snapshot["overall_momentum"] == "improving"
