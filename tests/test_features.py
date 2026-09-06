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
