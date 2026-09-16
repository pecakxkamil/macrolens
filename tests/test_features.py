import pandas as pd
import pytest

from app.analytics.features import calculate_features


def observations(values, start="2024-01-01", frequency="MS"):
    return pd.DataFrame(
        {
            "observation_date": pd.date_range(
                start=start,
                periods=len(values),
                freq=frequency,
            ),
            "value": values,
        }
    )


def feature_values(features, name):
    return features[features["feature_name"] == name]["feature_value"].tolist()


def test_payems_monthly_change():
    features = calculate_features(
        "PAYEMS",
        observations([100, 125, 150]),
        ["monthly_change"],
    )

    assert feature_values(features, "monthly_change") == [25.0, 25.0]


def test_payems_3m_moving_average():
    features = calculate_features(
        "PAYEMS",
        observations([100, 110, 130, 160]),
        ["monthly_change_ma_3m"],
    )

    assert feature_values(features, "monthly_change_ma_3m") == [20.0]


def test_payems_6m_moving_average():
    features = calculate_features(
        "PAYEMS",
        observations([100, 110, 125, 145, 170, 200, 235]),
        ["monthly_change_ma_6m"],
    )

    assert feature_values(features, "monthly_change_ma_6m") == [22.5]


def test_unrate_3m_change():
    features = calculate_features(
        "UNRATE",
        observations([4.0, 4.1, 4.2, 4.5]),
        ["change_3m"],
    )

    assert feature_values(features, "change_3m") == pytest.approx([0.5])


def test_unrate_level():
    features = calculate_features(
        "UNRATE",
        observations([3.8, 3.9]),
        ["level"],
    )

    assert feature_values(features, "level") == [3.8, 3.9]


def test_icsa_4w_moving_average():
    features = calculate_features(
        "ICSA",
        observations([200, 220, 240, 260], frequency="W-FRI"),
        ["moving_average_4w"],
    )

    assert feature_values(features, "moving_average_4w") == [230.0]


def test_icsa_yoy_uses_52_prior_observations():
    values = [100] * 52 + [110]
    features = calculate_features(
        "ICSA",
        observations(values, frequency="W-FRI"),
        ["yoy"],
    )

    assert feature_values(features, "yoy") == pytest.approx([10.0])


def test_ccsa_uses_weekly_yoy_with_52_prior_observations():
    values = [200] * 52 + [220]
    features = calculate_features(
        "CCSA",
        observations(values, frequency="W-FRI"),
        ["yoy"],
    )

    assert feature_values(features, "yoy") == pytest.approx([10.0])


def test_jtsjol_monthly_yoy_uses_12_prior_observations():
    values = [1000] * 12 + [1100]
    features = calculate_features(
        "JTSJOL",
        observations(values),
        ["yoy"],
    )

    assert feature_values(features, "yoy") == pytest.approx([10.0])


def test_civpart_uses_generic_level_change_and_moving_average():
    features = calculate_features(
        "CIVPART",
        observations([60.0, 60.1, 60.2, 60.5]),
        ["level", "change_3m", "moving_average_3m"],
    )

    assert feature_values(features, "level") == [60.0, 60.1, 60.2, 60.5]
    assert feature_values(features, "change_3m") == pytest.approx([0.5])
    assert feature_values(features, "moving_average_3m") == pytest.approx(
        [60.1, 60.2666666667]
    )


def test_ces_average_hourly_earnings_mom():
    features = calculate_features(
        "CES0500000003",
        observations([25.00, 25.50]),
        ["mom"],
    )

    assert feature_values(features, "mom") == pytest.approx([2.0])


def test_ces_average_hourly_earnings_annualized_3m():
    features = calculate_features(
        "CES0500000003",
        observations([25.00, 25.25, 25.50, 26.00]),
        ["annualized_3m"],
    )

    expected = ((26.00 / 25.00) ** 4 - 1) * 100
    assert feature_values(features, "annualized_3m") == pytest.approx([expected])


def test_monthly_yoy_inflation_calculation():
    features = calculate_features(
        "CPIAUCSL",
        observations([300.0] * 12 + [312.0]),
        ["yoy"],
    )

    assert feature_values(features, "yoy") == pytest.approx([4.0])


def test_monthly_mom_inflation_calculation():
    features = calculate_features(
        "CPILFESL",
        observations([300.0, 303.0]),
        ["mom"],
    )

    assert feature_values(features, "mom") == pytest.approx([1.0])


def test_inflation_annualized_3m_calculation():
    features = calculate_features(
        "PCEPI",
        observations([120.0, 121.0, 122.0, 123.0]),
        ["annualized_3m"],
    )

    expected = ((123.0 / 120.0) ** 4 - 1) * 100
    assert feature_values(features, "annualized_3m") == pytest.approx([expected])


def test_quarterly_qoq_calculation():
    features = calculate_features(
        "ECIALLCIV",
        observations([160.0, 162.0], frequency="QS"),
        ["qoq"],
    )

    assert feature_values(features, "qoq") == pytest.approx([1.25])


def test_quarterly_yoy_calculation():
    features = calculate_features(
        "ECIALLCIV",
        observations([160.0, 161.0, 162.0, 163.0, 168.0], frequency="QS"),
        ["yoy"],
    )

    assert feature_values(features, "yoy") == pytest.approx([5.0])


def test_gdpc1_qoq_annualized_calculation():
    features = calculate_features(
        "GDPC1",
        observations([100.0, 101.0], frequency="QS"),
        ["qoq_annualized"],
    )

    expected = ((101.0 / 100.0) ** 4 - 1) * 100
    assert feature_values(features, "qoq_annualized") == pytest.approx([expected])


def test_gdpc1_quarterly_yoy_uses_lag_4():
    features = calculate_features(
        "GDPC1",
        observations([100.0, 101.0, 102.0, 103.0, 104.0], frequency="QS"),
        ["yoy"],
    )

    assert feature_values(features, "yoy") == pytest.approx([4.0])


def test_cfnai_level():
    features = calculate_features(
        "CFNAI",
        observations([0.1, -0.2]),
        ["level"],
    )

    assert feature_values(features, "level") == [0.1, -0.2]


def test_cfnai_3m_moving_average():
    features = calculate_features(
        "CFNAI",
        observations([0.1, -0.2, 0.4]),
        ["moving_average_3m"],
    )

    assert feature_values(features, "moving_average_3m") == pytest.approx([0.1])


def test_indpro_mom():
    features = calculate_features(
        "INDPRO",
        observations([100.0, 102.0]),
        ["mom"],
    )

    assert feature_values(features, "mom") == pytest.approx([2.0])


def test_indpro_monthly_yoy_uses_lag_12():
    features = calculate_features(
        "INDPRO",
        observations([100.0] * 12 + [105.0]),
        ["yoy"],
    )

    assert feature_values(features, "yoy") == pytest.approx([5.0])


def test_indpro_annualized_3m():
    features = calculate_features(
        "INDPRO",
        observations([100.0, 101.0, 102.0, 103.0]),
        ["annualized_3m"],
    )

    expected = ((103.0 / 100.0) ** 4 - 1) * 100
    assert feature_values(features, "annualized_3m") == pytest.approx([expected])


def test_tcu_level():
    features = calculate_features(
        "TCU",
        observations([75.0, 76.0]),
        ["level"],
    )

    assert feature_values(features, "level") == [75.0, 76.0]


def test_tcu_change_3m():
    features = calculate_features(
        "TCU",
        observations([75.0, 75.5, 76.0, 77.0]),
        ["change_3m"],
    )

    assert feature_values(features, "change_3m") == pytest.approx([2.0])


def test_dgorder_mom():
    features = calculate_features(
        "DGORDER",
        observations([200.0, 220.0]),
        ["mom"],
    )

    assert feature_values(features, "mom") == pytest.approx([10.0])


def test_dgorder_monthly_yoy_uses_lag_12():
    features = calculate_features(
        "DGORDER",
        observations([200.0] * 12 + [220.0]),
        ["yoy"],
    )

    assert feature_values(features, "yoy") == pytest.approx([10.0])


def test_rsafs_mom():
    features = calculate_features(
        "RSAFS",
        observations([500.0, 510.0]),
        ["mom"],
    )

    assert feature_values(features, "mom") == pytest.approx([2.0])


def test_rsafs_monthly_yoy_uses_lag_12():
    features = calculate_features(
        "RSAFS",
        observations([500.0] * 12 + [550.0]),
        ["yoy"],
    )

    assert feature_values(features, "yoy") == pytest.approx([10.0])


def test_rsafs_annualized_3m():
    features = calculate_features(
        "RSAFS",
        observations([500.0, 505.0, 510.0, 515.0]),
        ["annualized_3m"],
    )

    expected = ((515.0 / 500.0) ** 4 - 1) * 100
    assert feature_values(features, "annualized_3m") == pytest.approx([expected])


def test_pcec96_mom():
    features = calculate_features(
        "PCEC96",
        observations([100.0, 101.0]),
        ["mom"],
    )

    assert feature_values(features, "mom") == pytest.approx([1.0])


def test_pcec96_yoy():
    features = calculate_features(
        "PCEC96",
        observations([100.0] * 12 + [103.0]),
        ["yoy"],
    )

    assert feature_values(features, "yoy") == pytest.approx([3.0])


def test_pcec96_annualized_3m():
    features = calculate_features(
        "PCEC96",
        observations([100.0, 101.0, 102.0, 104.0]),
        ["annualized_3m"],
    )

    expected = ((104.0 / 100.0) ** 4 - 1) * 100
    assert feature_values(features, "annualized_3m") == pytest.approx([expected])


def test_dspic96_mom():
    features = calculate_features(
        "DSPIC96",
        observations([200.0, 204.0]),
        ["mom"],
    )

    assert feature_values(features, "mom") == pytest.approx([2.0])


def test_dspic96_yoy():
    features = calculate_features(
        "DSPIC96",
        observations([200.0] * 12 + [210.0]),
        ["yoy"],
    )

    assert feature_values(features, "yoy") == pytest.approx([5.0])


def test_dspic96_annualized_3m():
    features = calculate_features(
        "DSPIC96",
        observations([200.0, 202.0, 204.0, 206.0]),
        ["annualized_3m"],
    )

    expected = ((206.0 / 200.0) ** 4 - 1) * 100
    assert feature_values(features, "annualized_3m") == pytest.approx([expected])


def test_psavert_level():
    features = calculate_features(
        "PSAVERT",
        observations([4.0, 4.2]),
        ["level"],
    )

    assert feature_values(features, "level") == [4.0, 4.2]


def test_psavert_change_3m():
    features = calculate_features(
        "PSAVERT",
        observations([4.0, 4.1, 4.2, 4.5]),
        ["change_3m"],
    )

    assert feature_values(features, "change_3m") == pytest.approx([0.5])


def test_psavert_3m_moving_average():
    features = calculate_features(
        "PSAVERT",
        observations([4.0, 4.1, 4.2, 4.5]),
        ["moving_average_3m"],
    )

    assert feature_values(features, "moving_average_3m") == pytest.approx(
        [4.1, 4.2666666667]
    )


def test_existing_labor_feature_behavior_is_preserved():
    payems_features = calculate_features(
        "PAYEMS",
        observations([100, 110, 130, 160]),
        ["monthly_change_ma_3m"],
    )
    unrate_features = calculate_features(
        "UNRATE",
        observations([4.0, 4.1, 4.2, 4.5]),
        ["change_3m"],
    )
    icsa_features = calculate_features(
        "ICSA",
        observations([100] * 52 + [110], frequency="W-FRI"),
        ["yoy"],
    )

    assert feature_values(payems_features, "monthly_change_ma_3m") == [20.0]
    assert feature_values(unrate_features, "change_3m") == pytest.approx([0.5])
    assert feature_values(icsa_features, "yoy") == pytest.approx([10.0])


def test_existing_inflation_feature_behavior_is_preserved():
    cpi_features = calculate_features(
        "CPIAUCSL",
        observations([300.0] * 12 + [312.0]),
        ["yoy"],
    )
    eci_features = calculate_features(
        "ECIALLCIV",
        observations([160.0, 162.0], frequency="QS"),
        ["qoq"],
    )

    assert feature_values(cpi_features, "yoy") == pytest.approx([4.0])
    assert feature_values(eci_features, "qoq") == pytest.approx([1.25])


def test_existing_growth_feature_behavior_is_preserved():
    gdp_features = calculate_features(
        "GDPC1",
        observations([100.0, 101.0], frequency="QS"),
        ["qoq_annualized"],
    )
    indpro_features = calculate_features(
        "INDPRO",
        observations([100.0] * 12 + [105.0]),
        ["yoy"],
    )

    expected = ((101.0 / 100.0) ** 4 - 1) * 100
    assert feature_values(gdp_features, "qoq_annualized") == pytest.approx([expected])
    assert feature_values(indpro_features, "yoy") == pytest.approx([5.0])


def test_insufficient_rolling_history_produces_no_premature_values():
    payems_features = calculate_features(
        "PAYEMS",
        observations([100, 110]),
        ["monthly_change_ma_3m"],
    )
    payems_6m_features = calculate_features(
        "PAYEMS",
        observations([100, 110, 125, 145, 170, 200]),
        ["monthly_change_ma_6m"],
    )
    icsa_features = calculate_features(
        "ICSA",
        observations([100] * 52, frequency="W-FRI"),
        ["yoy"],
    )

    assert payems_features.empty
    assert payems_6m_features.empty
    assert icsa_features.empty


def test_insufficient_growth_history_produces_no_premature_values():
    monthly_yoy_features = calculate_features(
        "JTSJOL",
        observations([100] * 12),
        ["yoy"],
    )
    mom_features = calculate_features(
        "CES0500000003",
        observations([25.00]),
        ["mom"],
    )
    annualized_features = calculate_features(
        "CES0500000003",
        observations([25.00, 25.25, 25.50]),
        ["annualized_3m"],
    )

    assert monthly_yoy_features.empty
    assert mom_features.empty
    assert annualized_features.empty


def test_insufficient_new_growth_history_produces_no_premature_values():
    gdp_qoq_features = calculate_features(
        "GDPC1",
        observations([100.0], frequency="QS"),
        ["qoq_annualized"],
    )
    gdp_yoy_features = calculate_features(
        "GDPC1",
        observations([100.0, 101.0, 102.0, 103.0], frequency="QS"),
        ["yoy"],
    )
    cfnai_average_features = calculate_features(
        "CFNAI",
        observations([0.1, -0.2]),
        ["moving_average_3m"],
    )
    dgorder_yoy_features = calculate_features(
        "DGORDER",
        observations([200.0] * 12),
        ["yoy"],
    )

    assert gdp_qoq_features.empty
    assert gdp_yoy_features.empty
    assert cfnai_average_features.empty
    assert dgorder_yoy_features.empty


def test_insufficient_consumer_history_produces_no_premature_values():
    rsafs_yoy_features = calculate_features(
        "RSAFS",
        observations([500.0] * 12),
        ["yoy"],
    )
    pcec96_mom_features = calculate_features(
        "PCEC96",
        observations([100.0]),
        ["mom"],
    )
    dspic96_annualized_features = calculate_features(
        "DSPIC96",
        observations([200.0, 202.0, 204.0]),
        ["annualized_3m"],
    )
    psavert_average_features = calculate_features(
        "PSAVERT",
        observations([4.0, 4.1]),
        ["moving_average_3m"],
    )

    assert rsafs_yoy_features.empty
    assert pcec96_mom_features.empty
    assert dspic96_annualized_features.empty
    assert psavert_average_features.empty


def test_insufficient_quarterly_growth_history_produces_no_premature_values():
    quarterly_yoy_features = calculate_features(
        "ECIALLCIV",
        observations([160.0, 161.0, 162.0, 163.0], frequency="QS"),
        ["yoy"],
    )
    qoq_features = calculate_features(
        "ECIALLCIV",
        observations([160.0], frequency="QS"),
        ["qoq"],
    )

    assert quarterly_yoy_features.empty
    assert qoq_features.empty
