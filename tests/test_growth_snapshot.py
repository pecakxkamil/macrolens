from app.analytics.growth_snapshot import (
    build_growth_snapshot,
    classify_cfnai_position,
    classify_direction_from_change,
    classify_growth_momentum,
    print_growth_snapshot,
)
from app.analytics.inflation_snapshot import build_inflation_snapshot
from app.analytics.labor_snapshot import build_labor_snapshot


def component_features(**values):
    return {
        "observation_date": "2026-08-01",
        "feature_as_of_date": "2026-09-04",
        **values,
    }


def growth_snapshot(
    gdp_qoq=3.0,
    gdp_yoy=2.0,
    cfnai_average=0.1,
    industrial_annualized=4.0,
    industrial_yoy=3.0,
    capacity_change=0.2,
    durable_mom=1.0,
):
    return build_growth_snapshot(
        "2026-09-04",
        component_features(qoq_annualized=gdp_qoq, yoy=gdp_yoy),
        component_features(level=0.2, moving_average_3m=cfnai_average),
        component_features(
            mom=0.3,
            yoy=industrial_yoy,
            annualized_3m=industrial_annualized,
        ),
        component_features(
            level=78.0,
            change_3m=capacity_change,
            moving_average_3m=77.5,
        ),
        component_features(mom=durable_mom, yoy=4.0, moving_average_3m=250000.0),
    )


def test_gdp_accelerating():
    assert classify_growth_momentum(3.0, 2.0) == "accelerating"


def test_gdp_decelerating():
    assert classify_growth_momentum(1.0, 2.0) == "decelerating"


def test_gdp_stable():
    assert classify_growth_momentum(2.0, 2.0) == "stable"


def test_cfnai_above_trend():
    assert classify_cfnai_position(0.1) == "above_trend"


def test_cfnai_below_trend():
    assert classify_cfnai_position(-0.1) == "below_trend"


def test_cfnai_at_trend():
    assert classify_cfnai_position(0) == "at_trend"


def test_industrial_production_accelerating_and_decelerating():
    accelerating = growth_snapshot(industrial_annualized=4.0, industrial_yoy=3.0)
    decelerating = growth_snapshot(industrial_annualized=2.0, industrial_yoy=3.0)

    assert accelerating["industrial_production"]["momentum"] == "accelerating"
    assert decelerating["industrial_production"]["momentum"] == "decelerating"


def test_capacity_utilization_direction():
    assert classify_direction_from_change(0.1) == "rising"
    assert classify_direction_from_change(-0.1) == "falling"
    assert classify_direction_from_change(0) == "stable"


def test_durable_goods_latest_direction():
    rising = growth_snapshot(durable_mom=1.0)
    falling = growth_snapshot(durable_mom=-1.0)
    stable = growth_snapshot(durable_mom=0)

    assert rising["durable_goods_orders"]["latest_direction"] == "rising"
    assert falling["durable_goods_orders"]["latest_direction"] == "falling"
    assert stable["durable_goods_orders"]["latest_direction"] == "stable"


def test_snapshot_contains_all_five_components():
    snapshot = growth_snapshot()

    assert set(snapshot.keys()) == {
        "as_of_date",
        "real_gdp",
        "cfnai",
        "industrial_production",
        "capacity_utilization",
        "durable_goods_orders",
    }


def test_snapshot_preserves_observation_and_feature_as_of_dates():
    snapshot = growth_snapshot()

    for component_name in (
        "real_gdp",
        "cfnai",
        "industrial_production",
        "capacity_utilization",
        "durable_goods_orders",
    ):
        assert snapshot[component_name]["observation_date"] == "2026-08-01"
        assert snapshot[component_name]["feature_as_of_date"] == "2026-09-04"


def test_cfnai_console_output_includes_required_fields(capsys):
    print_growth_snapshot(growth_snapshot(cfnai_average=0.1))

    output = capsys.readouterr().out

    assert "CFNAI:" in output
    assert "Observation date: 2026-08-01" in output
    assert "Feature as of: 2026-09-04" in output
    assert "Level: 0.2" in output
    assert "3M average: 0.1" in output
    assert "Position: above_trend" in output


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
