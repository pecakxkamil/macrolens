from decimal import Decimal

import pytest

from app.analytics.consumer_snapshot import build_consumer_snapshot
from app.analytics.financial_conditions_snapshot import (
    build_financial_conditions_snapshot,
    build_latest_synchronized_2s10s_spread,
    build_yield_curve_spread,
    classify_nfci_direction,
    classify_nfci_position,
    classify_yield_curve_shape,
    print_financial_conditions_snapshot,
)
from app.analytics.growth_snapshot import build_growth_snapshot
from app.analytics.housing_snapshot import build_housing_snapshot
from app.analytics.inflation_snapshot import build_inflation_snapshot
from app.analytics.labor_snapshot import build_labor_snapshot


def component_features(**values):
    return {
        "observation_date": "2026-08-01",
        "feature_as_of_date": "2026-09-04",
        **values,
    }


def rate_features(level):
    return component_features(level=level)


def nfci_features(level=0.2, change_4w=0.1):
    return component_features(
        level=level,
        change_4w=change_4w,
        moving_average_4w=0.05,
    )


def spread_features(dgs2=4.0, dgs10=4.5):
    return build_yield_curve_spread(
        "2026-08-01",
        dgs2,
        dgs10,
        "2026-09-03",
        "2026-09-04",
    )


def financial_conditions_snapshot():
    return build_financial_conditions_snapshot(
        "2026-09-04",
        rate_features(5.33),
        rate_features(4.0),
        rate_features(4.5),
        rate_features(2.1),
        nfci_features(),
        spread_features(),
    )


def test_snapshot_contains_all_components():
    snapshot = financial_conditions_snapshot()

    assert set(snapshot.keys()) == {
        "as_of_date",
        "fed_funds_rate",
        "treasury_2y",
        "treasury_10y",
        "real_yield_10y",
        "yield_curve_2s10s",
        "nfci",
    }


def test_observation_date_and_feature_as_of_date_are_preserved():
    snapshot = financial_conditions_snapshot()

    for component_name in (
        "fed_funds_rate",
        "treasury_2y",
        "treasury_10y",
        "real_yield_10y",
        "nfci",
    ):
        assert snapshot[component_name]["observation_date"] == "2026-08-01"
        assert snapshot[component_name]["feature_as_of_date"] == "2026-09-04"

    assert snapshot["yield_curve_2s10s"]["observation_date"] == "2026-08-01"
    assert snapshot["yield_curve_2s10s"]["feature_as_of_date"] == "2026-09-04"


def test_synchronized_2s10s_calculation():
    spread = build_yield_curve_spread(
        "2026-08-01",
        4.0,
        4.5,
        "2026-09-03",
        "2026-09-04",
    )

    assert spread["dgs2"] == Decimal("4.0")
    assert spread["dgs10"] == Decimal("4.5")
    assert spread["spread"] == Decimal("0.5")
    assert spread["feature_as_of_date"] == "2026-09-04"


def test_structured_2s10s_contains_required_freshness_fields():
    curve = financial_conditions_snapshot()["yield_curve_2s10s"]

    assert set(curve.keys()) == {
        "observation_date",
        "feature_as_of_date",
        "dgs2",
        "dgs10",
        "spread",
        "shape",
    }
    assert curve["observation_date"] == "2026-08-01"
    assert curve["feature_as_of_date"] == "2026-09-04"


def test_latest_common_date_is_selected():
    spread = build_latest_synchronized_2s10s_spread(
        [
            {
                "observation_date": "2026-08-01",
                "feature_as_of_date": "2026-09-03",
                "level": 4.0,
            },
            {
                "observation_date": "2026-08-03",
                "feature_as_of_date": "2026-09-04",
                "level": 4.2,
            },
        ],
        [
            {
                "observation_date": "2026-08-01",
                "feature_as_of_date": "2026-09-04",
                "level": 4.5,
            },
            {
                "observation_date": "2026-08-02",
                "feature_as_of_date": "2026-09-04",
                "level": 4.6,
            },
        ],
    )

    assert spread["observation_date"] == "2026-08-01"
    assert spread["spread"] == Decimal("0.5")


def test_mismatched_latest_dates_are_not_directly_subtracted():
    spread = build_latest_synchronized_2s10s_spread(
        [
            {
                "observation_date": "2026-08-01",
                "feature_as_of_date": "2026-09-03",
                "level": 4.0,
            },
            {
                "observation_date": "2026-08-03",
                "feature_as_of_date": "2026-09-04",
                "level": 4.2,
            },
        ],
        [
            {
                "observation_date": "2026-08-01",
                "feature_as_of_date": "2026-09-04",
                "level": 4.5,
            },
            {
                "observation_date": "2026-08-02",
                "feature_as_of_date": "2026-09-04",
                "level": 4.9,
            },
        ],
    )

    assert spread["observation_date"] == "2026-08-01"
    assert spread["spread"] != Decimal("0.7")


def test_no_forward_fill_for_2s10s():
    with pytest.raises(RuntimeError):
        build_latest_synchronized_2s10s_spread(
            [
                {
                    "observation_date": "2026-08-03",
                    "feature_as_of_date": "2026-09-04",
                    "level": 4.2,
                }
            ],
            [
                {
                    "observation_date": "2026-08-02",
                    "feature_as_of_date": "2026-09-04",
                    "level": 4.9,
                }
            ],
        )


def test_positive_inverted_and_flat_spread_shapes():
    assert classify_yield_curve_shape(0.5) == "positive"
    assert classify_yield_curve_shape(-0.5) == "inverted"
    assert classify_yield_curve_shape(0) == "flat"


def test_nfci_position_labels():
    assert classify_nfci_position(0.1) == "tighter_than_average"
    assert classify_nfci_position(-0.1) == "looser_than_average"
    assert classify_nfci_position(0) == "average"


def test_nfci_direction_labels():
    assert classify_nfci_direction(0.1) == "tightening"
    assert classify_nfci_direction(-0.1) == "easing"
    assert classify_nfci_direction(0) == "stable"


def test_no_overall_financial_conditions_score_or_state():
    snapshot = financial_conditions_snapshot()

    assert "overall_score" not in snapshot
    assert "financial_conditions_score" not in snapshot
    assert "overall_state" not in snapshot
    assert "financial_conditions_state" not in snapshot


def test_real_yield_10y_console_output_includes_required_fields(capsys):
    print_financial_conditions_snapshot(financial_conditions_snapshot())

    output = capsys.readouterr().out
    real_yield_section = output.split("10Y Real Yield:", 1)[1].split(
        "2s10s Treasury Spread:",
        1,
    )[0]

    assert "Observation date: 2026-08-01" in real_yield_section
    assert "Feature as of: 2026-09-04" in real_yield_section
    assert "Level: 2.1" in real_yield_section


def test_2s10s_console_output_includes_heading_and_required_fields(capsys):
    print_financial_conditions_snapshot(financial_conditions_snapshot())

    output = capsys.readouterr().out
    spread_section = output.split("2s10s Treasury Spread:", 1)[1].split(
        "NFCI:",
        1,
    )[0]

    assert "Observation date: 2026-08-01" in spread_section
    assert "Feature as of: 2026-09-04" in spread_section
    assert "DGS2: 4.0" in spread_section
    assert "DGS10: 4.5" in spread_section
    assert "Spread: 0.5" in spread_section


def test_nfci_console_output_includes_required_fields(capsys):
    print_financial_conditions_snapshot(financial_conditions_snapshot())

    output = capsys.readouterr().out
    nfci_section = output.split("NFCI:", 1)[1]

    assert "Observation date: 2026-08-01" in nfci_section
    assert "Feature as of: 2026-09-04" in nfci_section
    assert "Level: 0.2" in nfci_section
    assert "Change 4W: 0.1" in nfci_section
    assert "4W average: 0.05" in nfci_section
    assert "Note: NFCI labels are mechanical descriptions, not trading signals" in nfci_section


def test_existing_snapshot_behavior_remains_unchanged():
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
    inflation_snapshot = build_inflation_snapshot(
        "2026-09-04",
        component_features(mom=0.2, yoy=3.0, annualized_3m=2.5),
        component_features(mom=0.3, yoy=3.0, annualized_3m=3.5),
        component_features(mom=0.2, yoy=3.0, annualized_3m=3.0),
        component_features(mom=0.1, yoy=3.0, annualized_3m=2.0),
        component_features(qoq=0.8, yoy=3.7),
        component_features(mom=0.3, yoy=4.1, annualized_3m=3.8),
    )
    growth_snapshot = build_growth_snapshot(
        "2026-09-04",
        component_features(qoq_annualized=3.0, yoy=2.0),
        component_features(level=0.2, moving_average_3m=0.1),
        component_features(mom=0.3, yoy=3.0, annualized_3m=4.0),
        component_features(level=78.0, change_3m=-0.2, moving_average_3m=77.5),
        component_features(mom=0.0, yoy=4.0, moving_average_3m=250000.0),
    )
    consumer_snapshot = build_consumer_snapshot(
        "2026-09-04",
        component_features(mom=0.3, yoy=3.0, annualized_3m=4.0),
        component_features(mom=0.2, yoy=3.0, annualized_3m=3.0),
        component_features(mom=0.1, yoy=3.0, annualized_3m=2.0),
        component_features(level=4.5, change_3m=0.2, moving_average_3m=4.3),
    )
    housing_snapshot = build_housing_snapshot(
        "2026-09-04",
        component_features(level=1400.0, mom=1.0, yoy=5.0, moving_average_3m=1380.0),
        component_features(level=1400.0, mom=1.0, yoy=5.0, moving_average_3m=1380.0),
        component_features(level=1400.0, mom=-1.0, yoy=5.0, moving_average_3m=1380.0),
        component_features(level=6.5, change_4w=0.25, change_13w=0.5, moving_average_4w=6.35),
    )

    assert labor_snapshot["overall_momentum"] == "improving"
    assert inflation_snapshot["core_cpi"]["momentum"] == "accelerating"
    assert growth_snapshot["real_gdp"]["momentum"] == "accelerating"
    assert consumer_snapshot["retail_sales"]["series_type"] == "nominal"
    assert housing_snapshot["mortgage_rate"]["direction"] == "rising"
