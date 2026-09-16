from app.analytics.consumer_snapshot import build_consumer_snapshot
from app.analytics.growth_snapshot import build_growth_snapshot
from app.analytics.housing_snapshot import (
    build_housing_snapshot,
    classify_direction_from_change,
    print_housing_snapshot,
)
from app.analytics.inflation_snapshot import build_inflation_snapshot
from app.analytics.labor_snapshot import build_labor_snapshot


def component_features(**values):
    return {
        "observation_date": "2026-08-01",
        "feature_as_of_date": "2026-09-04",
        **values,
    }


def monthly_housing_features(mom=2.0):
    return component_features(
        level=1400.0,
        mom=mom,
        yoy=5.0,
        moving_average_3m=1380.0,
    )


def mortgage_features(change_4w=0.25):
    return component_features(
        level=6.5,
        change_4w=change_4w,
        change_13w=0.5,
        moving_average_4w=6.35,
    )


def housing_snapshot(
    starts_mom=2.0,
    permits_mom=1.0,
    sales_mom=-1.0,
    mortgage_change_4w=0.25,
):
    return build_housing_snapshot(
        "2026-09-04",
        monthly_housing_features(starts_mom),
        monthly_housing_features(permits_mom),
        monthly_housing_features(sales_mom),
        mortgage_features(mortgage_change_4w),
    )


def test_housing_starts_rising_falling_stable():
    assert housing_snapshot(starts_mom=1.0)["housing_starts"]["direction"] == "rising"
    assert (
        housing_snapshot(starts_mom=-1.0)["housing_starts"]["direction"] == "falling"
    )
    assert housing_snapshot(starts_mom=0)["housing_starts"]["direction"] == "stable"


def test_permits_rising_falling_stable():
    assert housing_snapshot(permits_mom=1.0)["building_permits"][
        "direction"
    ] == "rising"
    assert housing_snapshot(permits_mom=-1.0)["building_permits"][
        "direction"
    ] == "falling"
    assert housing_snapshot(permits_mom=0)["building_permits"][
        "direction"
    ] == "stable"


def test_new_home_sales_rising_falling_stable():
    assert housing_snapshot(sales_mom=1.0)["new_home_sales"]["direction"] == "rising"
    assert housing_snapshot(sales_mom=-1.0)["new_home_sales"][
        "direction"
    ] == "falling"
    assert housing_snapshot(sales_mom=0)["new_home_sales"]["direction"] == "stable"


def test_mortgage_rate_rising_falling_stable():
    assert classify_direction_from_change(0.25) == "rising"
    assert classify_direction_from_change(-0.25) == "falling"
    assert classify_direction_from_change(0) == "stable"


def test_snapshot_contains_all_four_components():
    snapshot = housing_snapshot()

    assert set(snapshot.keys()) == {
        "as_of_date",
        "housing_starts",
        "building_permits",
        "new_home_sales",
        "mortgage_rate",
    }


def test_building_permits_console_output_includes_required_fields(capsys):
    print_housing_snapshot(housing_snapshot(permits_mom=1.0))

    output = capsys.readouterr().out

    assert "Building Permits: rising (obs=2026-08-01, feature_as_of=2026-09-04)" in output
    assert "Level: 1400.0" in output
    assert "MoM: 1.0" in output
    assert "YoY: 5.0" in output
    assert "3M average: 1380.0" in output


def test_snapshot_preserves_observation_and_feature_as_of_dates():
    snapshot = housing_snapshot()

    for component_name in (
        "housing_starts",
        "building_permits",
        "new_home_sales",
        "mortgage_rate",
    ):
        assert snapshot[component_name]["observation_date"] == "2026-08-01"
        assert snapshot[component_name]["feature_as_of_date"] == "2026-09-04"


def test_all_required_numeric_features_are_exposed():
    snapshot = housing_snapshot()

    for component_name in ("housing_starts", "building_permits", "new_home_sales"):
        assert snapshot[component_name]["level"] == 1400.0
        assert "mom" in snapshot[component_name]
        assert snapshot[component_name]["yoy"] == 5.0
        assert snapshot[component_name]["moving_average_3m"] == 1380.0

    assert snapshot["mortgage_rate"]["level"] == 6.5
    assert snapshot["mortgage_rate"]["change_4w"] == 0.25
    assert snapshot["mortgage_rate"]["change_13w"] == 0.5
    assert snapshot["mortgage_rate"]["moving_average_4w"] == 6.35


def test_mortgage_changes_remain_percentage_point_differences():
    snapshot = housing_snapshot(mortgage_change_4w=-0.25)

    assert snapshot["mortgage_rate"]["change_4w"] == -0.25
    assert snapshot["mortgage_rate"]["direction"] == "falling"


def test_no_overall_housing_score_or_state_exists():
    snapshot = housing_snapshot()

    assert "overall_score" not in snapshot
    assert "housing_score" not in snapshot
    assert "overall_state" not in snapshot
    assert "housing_state" not in snapshot


def test_existing_labor_behavior_remains_unchanged():
    labor_snapshot = build_labor_snapshot(
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

    assert labor_snapshot["overall_momentum"] == "improving"
    assert labor_snapshot["job_openings"]["direction"] == "falling"


def test_existing_inflation_behavior_remains_unchanged():
    inflation_snapshot = build_inflation_snapshot(
        "2026-09-04",
        component_features(mom=0.2, yoy=3.0, annualized_3m=2.5),
        component_features(mom=0.3, yoy=3.0, annualized_3m=3.5),
        component_features(mom=0.2, yoy=3.0, annualized_3m=3.0),
        component_features(mom=0.1, yoy=3.0, annualized_3m=2.0),
        component_features(qoq=0.8, yoy=3.7),
        component_features(mom=0.3, yoy=4.1, annualized_3m=3.8),
    )

    assert inflation_snapshot["headline_cpi"]["momentum"] == "decelerating"
    assert inflation_snapshot["core_cpi"]["momentum"] == "accelerating"
    assert inflation_snapshot["headline_pce"]["momentum"] == "stable"


def test_existing_growth_behavior_remains_unchanged():
    growth_snapshot = build_growth_snapshot(
        "2026-09-04",
        component_features(qoq_annualized=3.0, yoy=2.0),
        component_features(level=0.2, moving_average_3m=0.1),
        component_features(mom=0.3, yoy=3.0, annualized_3m=4.0),
        component_features(level=78.0, change_3m=-0.2, moving_average_3m=77.5),
        component_features(mom=0.0, yoy=4.0, moving_average_3m=250000.0),
    )

    assert growth_snapshot["real_gdp"]["momentum"] == "accelerating"
    assert growth_snapshot["cfnai"]["position"] == "above_trend"
    assert growth_snapshot["capacity_utilization"]["direction"] == "falling"
    assert growth_snapshot["durable_goods_orders"]["latest_direction"] == "stable"


def test_existing_consumer_behavior_remains_unchanged():
    consumer_snapshot = build_consumer_snapshot(
        "2026-09-04",
        component_features(mom=0.3, yoy=3.0, annualized_3m=4.0),
        component_features(mom=0.2, yoy=3.0, annualized_3m=3.0),
        component_features(mom=0.1, yoy=3.0, annualized_3m=2.0),
        component_features(level=4.5, change_3m=0.2, moving_average_3m=4.3),
    )

    assert consumer_snapshot["retail_sales"]["momentum"] == "accelerating"
    assert consumer_snapshot["retail_sales"]["series_type"] == "nominal"
    assert consumer_snapshot["saving_rate"]["direction"] == "rising"
