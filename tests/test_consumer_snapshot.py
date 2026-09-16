from app.analytics.consumer_snapshot import (
    build_consumer_snapshot,
    classify_consumer_growth_momentum,
    classify_saving_rate_direction,
    print_consumer_snapshot,
)
from app.analytics.growth_snapshot import build_growth_snapshot
from app.analytics.inflation_snapshot import build_inflation_snapshot
from app.analytics.labor_snapshot import build_labor_snapshot


def component_features(**values):
    return {
        "observation_date": "2026-08-01",
        "feature_as_of_date": "2026-09-04",
        **values,
    }


def growth_features(annualized_3m=4.0, yoy=3.0):
    return component_features(mom=0.3, yoy=yoy, annualized_3m=annualized_3m)


def consumer_snapshot(
    retail_annualized=4.0,
    retail_yoy=3.0,
    consumption_annualized=3.0,
    consumption_yoy=3.0,
    income_annualized=2.0,
    income_yoy=3.0,
    saving_change=0.2,
):
    return build_consumer_snapshot(
        "2026-09-04",
        growth_features(retail_annualized, retail_yoy),
        growth_features(consumption_annualized, consumption_yoy),
        growth_features(income_annualized, income_yoy),
        component_features(
            level=4.5,
            change_3m=saving_change,
            moving_average_3m=4.3,
        ),
    )


def test_consumer_growth_momentum_accelerating():
    assert classify_consumer_growth_momentum(4.0, 3.0) == "accelerating"


def test_consumer_growth_momentum_decelerating():
    assert classify_consumer_growth_momentum(2.0, 3.0) == "decelerating"


def test_consumer_growth_momentum_stable():
    assert classify_consumer_growth_momentum(3.0, 3.0) == "stable"


def test_saving_rate_rising():
    assert classify_saving_rate_direction(0.1) == "rising"


def test_saving_rate_falling():
    assert classify_saving_rate_direction(-0.1) == "falling"


def test_saving_rate_stable():
    assert classify_saving_rate_direction(0) == "stable"


def test_snapshot_contains_all_four_components():
    snapshot = consumer_snapshot()

    assert set(snapshot.keys()) == {
        "as_of_date",
        "retail_sales",
        "real_consumption",
        "real_disposable_income",
        "saving_rate",
    }


def test_snapshot_preserves_observation_and_feature_as_of_dates():
    snapshot = consumer_snapshot()

    for component_name in (
        "retail_sales",
        "real_consumption",
        "real_disposable_income",
        "saving_rate",
    ):
        assert snapshot[component_name]["observation_date"] == "2026-08-01"
        assert snapshot[component_name]["feature_as_of_date"] == "2026-09-04"


def test_retail_sales_remains_identified_as_nominal():
    snapshot = consumer_snapshot()

    assert snapshot["retail_sales"] == {
        "observation_date": "2026-08-01",
        "feature_as_of_date": "2026-09-04",
        "mom": 0.3,
        "yoy": 3.0,
        "annualized_3m": 4.0,
        "momentum": "accelerating",
        "series_type": "nominal",
    }
    assert snapshot["retail_sales"]["series_type"] == "nominal"
    assert snapshot["retail_sales"]["momentum"] == "accelerating"


def test_retail_sales_console_output_includes_nominal_fields(capsys):
    print_consumer_snapshot(consumer_snapshot())

    output = capsys.readouterr().out

    assert "Retail Sales: accelerating" in output
    assert "MoM: 0.3" in output
    assert "YoY: 3.0" in output
    assert "3M annualized: 4.0" in output
    assert "Note: nominal series" in output


def test_no_overall_consumer_score_or_state_is_created():
    snapshot = consumer_snapshot()

    assert "overall_score" not in snapshot
    assert "consumer_score" not in snapshot
    assert "overall_state" not in snapshot
    assert "consumer_state" not in snapshot


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
