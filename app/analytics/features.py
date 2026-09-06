"""Mechanical v1 feature calculations for economic series."""

from collections.abc import Sequence

import pandas as pd


METHODOLOGY_VERSION = "v1"

FEATURES_BY_SERIES = {
    "PAYEMS": ("monthly_change", "monthly_change_ma_3m", "monthly_change_ma_6m"),
    "UNRATE": ("level", "change_3m", "change_6m", "moving_average_3m"),
    "ICSA": ("moving_average_4w", "moving_average_13w", "yoy"),
}


def calculate_features(
    series_id: str,
    observations: pd.DataFrame,
    feature_names: Sequence[str],
) -> pd.DataFrame:
    """Calculate configured v1 features from chronological observations."""
    if series_id not in FEATURES_BY_SERIES:
        raise ValueError(f"Unsupported series_id for feature calculation: {series_id}")

    unsupported_features = set(feature_names) - set(FEATURES_BY_SERIES[series_id])
    if unsupported_features:
        features = ", ".join(sorted(unsupported_features))
        raise ValueError(f"Unsupported features for {series_id}: {features}")

    if observations.empty:
        return pd.DataFrame(
            columns=["observation_date", "feature_name", "feature_value"]
        )

    frame = observations[["observation_date", "value"]].copy()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"])
    frame["value"] = pd.to_numeric(frame["value"])
    frame = frame.sort_values("observation_date").reset_index(drop=True)

    calculated = {}
    values = frame["value"]

    if series_id == "PAYEMS":
        monthly_change = values.diff(1)
        calculated["monthly_change"] = monthly_change
        calculated["monthly_change_ma_3m"] = monthly_change.rolling(window=3).mean()
        calculated["monthly_change_ma_6m"] = monthly_change.rolling(window=6).mean()
    elif series_id == "UNRATE":
        calculated["level"] = values
        calculated["change_3m"] = values.diff(3)
        calculated["change_6m"] = values.diff(6)
        calculated["moving_average_3m"] = values.rolling(window=3).mean()
    elif series_id == "ICSA":
        calculated["moving_average_4w"] = values.rolling(window=4).mean()
        calculated["moving_average_13w"] = values.rolling(window=13).mean()
        calculated["yoy"] = ((values / values.shift(52)) - 1) * 100

    feature_rows = []
    for feature_name in feature_names:
        for index, feature_value in calculated[feature_name].items():
            if pd.isna(feature_value):
                continue

            feature_value = float(feature_value)
            if feature_value in (float("inf"), float("-inf")):
                continue

            feature_rows.append(
                {
                    "observation_date": frame.at[index, "observation_date"].date(),
                    "feature_name": feature_name,
                    "feature_value": feature_value,
                }
            )

    return pd.DataFrame(
        feature_rows,
        columns=["observation_date", "feature_name", "feature_value"],
    )
