"""Transparent Financial Conditions Snapshot using computed features."""

import sys
from datetime import date
from decimal import Decimal
from typing import Optional

from app.analytics.feature_store import load_latest_component_features
from app.analytics.features import METHODOLOGY_VERSION
from app.analytics.labor_state import _parse_as_of_date
from app.database.connection import get_connection


RATE_FEATURES = ("level",)
NFCI_FEATURES = ("level", "change_4w", "moving_average_4w")

SYNCHRONIZED_2S10S_SQL = """
WITH dgs2_levels AS (
    SELECT
        observation_date,
        as_of_date,
        feature_value,
        ROW_NUMBER() OVER (
            PARTITION BY observation_date
            ORDER BY as_of_date DESC
        ) AS feature_rank
    FROM computed_features
    WHERE series_id = 'DGS2'
      AND methodology_version = %s
      AND feature_name = 'level'
      AND (%s::date IS NULL OR as_of_date <= %s)
),
dgs10_levels AS (
    SELECT
        observation_date,
        as_of_date,
        feature_value,
        ROW_NUMBER() OVER (
            PARTITION BY observation_date
            ORDER BY as_of_date DESC
        ) AS feature_rank
    FROM computed_features
    WHERE series_id = 'DGS10'
      AND methodology_version = %s
      AND feature_name = 'level'
      AND (%s::date IS NULL OR as_of_date <= %s)
)
SELECT
    dgs2_levels.observation_date,
    dgs2_levels.as_of_date AS dgs2_feature_as_of_date,
    dgs2_levels.feature_value AS dgs2,
    dgs10_levels.as_of_date AS dgs10_feature_as_of_date,
    dgs10_levels.feature_value AS dgs10
FROM dgs2_levels
JOIN dgs10_levels
  ON dgs2_levels.observation_date = dgs10_levels.observation_date
WHERE dgs2_levels.feature_rank = 1
  AND dgs10_levels.feature_rank = 1
ORDER BY dgs2_levels.observation_date DESC
LIMIT 1;
"""


def classify_nfci_position(level) -> str:
    """Classify NFCI relative to its zero historical-average reference."""
    level = Decimal(str(level))

    if level > 0:
        return "tighter_than_average"
    if level < 0:
        return "looser_than_average"
    return "average"


def classify_nfci_direction(change_4w) -> str:
    """Classify NFCI direction from a 4-week index-point change."""
    change_4w = Decimal(str(change_4w))

    if change_4w > 0:
        return "tightening"
    if change_4w < 0:
        return "easing"
    return "stable"


def classify_yield_curve_shape(spread) -> str:
    """Classify 2s10s curve shape mathematically, without economic signals."""
    spread = Decimal(str(spread))

    if spread > 0:
        return "positive"
    if spread < 0:
        return "inverted"
    return "flat"


def _with_dates(features: dict) -> dict:
    return {
        "observation_date": str(features["observation_date"]),
        "feature_as_of_date": str(features["feature_as_of_date"]),
    }


def _rate_component(features: dict) -> dict:
    return {
        **_with_dates(features),
        "level": features["level"],
    }


def build_yield_curve_spread(
    observation_date,
    dgs2,
    dgs10,
    dgs2_feature_as_of_date,
    dgs10_feature_as_of_date,
) -> dict:
    """Build a synchronized 2s10s spread from same-date DGS2/DGS10 values."""
    dgs2 = Decimal(str(dgs2))
    dgs10 = Decimal(str(dgs10))
    spread = dgs10 - dgs2
    feature_as_of_date = max(str(dgs2_feature_as_of_date), str(dgs10_feature_as_of_date))

    return {
        "observation_date": str(observation_date),
        "feature_as_of_date": feature_as_of_date,
        "dgs2": dgs2,
        "dgs10": dgs10,
        "spread": spread,
        "shape": classify_yield_curve_shape(spread),
    }


def build_latest_synchronized_2s10s_spread(
    dgs2_levels: list[dict],
    dgs10_levels: list[dict],
) -> dict:
    """Select the latest same-date DGS2/DGS10 pair and build 2s10s."""
    dgs2_by_date = {
        str(row["observation_date"]): row
        for row in dgs2_levels
    }
    dgs10_by_date = {
        str(row["observation_date"]): row
        for row in dgs10_levels
    }
    common_dates = sorted(set(dgs2_by_date.keys()) & set(dgs10_by_date.keys()))

    if not common_dates:
        raise RuntimeError("No synchronized DGS2/DGS10 observations found.")

    observation_date = common_dates[-1]
    dgs2 = dgs2_by_date[observation_date]
    dgs10 = dgs10_by_date[observation_date]

    return build_yield_curve_spread(
        observation_date,
        dgs2["level"],
        dgs10["level"],
        dgs2["feature_as_of_date"],
        dgs10["feature_as_of_date"],
    )


def build_financial_conditions_snapshot(
    as_of_date,
    fed_funds_features: dict,
    treasury_2y_features: dict,
    treasury_10y_features: dict,
    real_yield_10y_features: dict,
    nfci_features: dict,
    yield_curve_2s10s: dict,
) -> dict:
    """Build a structured Financial Conditions Snapshot from feature values."""
    return {
        "as_of_date": str(as_of_date),
        "fed_funds_rate": _rate_component(fed_funds_features),
        "treasury_2y": _rate_component(treasury_2y_features),
        "treasury_10y": _rate_component(treasury_10y_features),
        "real_yield_10y": _rate_component(real_yield_10y_features),
        "yield_curve_2s10s": yield_curve_2s10s,
        "nfci": {
            **_with_dates(nfci_features),
            "level": nfci_features["level"],
            "change_4w": nfci_features["change_4w"],
            "moving_average_4w": nfci_features["moving_average_4w"],
            "position": classify_nfci_position(nfci_features["level"]),
            "direction": classify_nfci_direction(nfci_features["change_4w"]),
        },
    }


def load_synchronized_2s10s_spread(
    connection,
    requested_as_of_date: Optional[date] = None,
) -> dict:
    """Load latest same-observation-date DGS2/DGS10 values for 2s10s."""
    with connection.cursor() as cursor:
        cursor.execute(
            SYNCHRONIZED_2S10S_SQL,
            (
                METHODOLOGY_VERSION,
                requested_as_of_date,
                requested_as_of_date,
                METHODOLOGY_VERSION,
                requested_as_of_date,
                requested_as_of_date,
            ),
        )
        row = cursor.fetchone()

    if row is None:
        raise RuntimeError("No synchronized DGS2/DGS10 level features found.")

    (
        observation_date,
        dgs2_feature_as_of_date,
        dgs2,
        dgs10_feature_as_of_date,
        dgs10,
    ) = row
    return build_latest_synchronized_2s10s_spread(
        [
            {
                "observation_date": observation_date,
                "feature_as_of_date": dgs2_feature_as_of_date,
                "level": dgs2,
            }
        ],
        [
            {
                "observation_date": observation_date,
                "feature_as_of_date": dgs10_feature_as_of_date,
                "level": dgs10,
            }
        ],
    )


def load_financial_conditions_snapshot_inputs(
    requested_as_of_date: Optional[date] = None,
) -> dict:
    """Load latest v1 feature values needed for the Financial Conditions Snapshot."""
    connection = None

    try:
        connection = get_connection()
        return {
            "fed_funds_rate": load_latest_component_features(
                connection,
                "DFF",
                RATE_FEATURES,
                requested_as_of_date,
            ),
            "treasury_2y": load_latest_component_features(
                connection,
                "DGS2",
                RATE_FEATURES,
                requested_as_of_date,
            ),
            "treasury_10y": load_latest_component_features(
                connection,
                "DGS10",
                RATE_FEATURES,
                requested_as_of_date,
            ),
            "real_yield_10y": load_latest_component_features(
                connection,
                "DFII10",
                RATE_FEATURES,
                requested_as_of_date,
            ),
            "nfci": load_latest_component_features(
                connection,
                "NFCI",
                NFCI_FEATURES,
                requested_as_of_date,
            ),
            "yield_curve_2s10s": load_synchronized_2s10s_spread(
                connection,
                requested_as_of_date,
            ),
        }
    finally:
        if connection is not None:
            connection.close()


def get_financial_conditions_snapshot(
    requested_as_of_date: Optional[date] = None,
) -> dict:
    """Load and build the Financial Conditions Snapshot."""
    inputs = load_financial_conditions_snapshot_inputs(requested_as_of_date)
    resolved_as_of_date = requested_as_of_date or max(
        str(component["feature_as_of_date"]) for component in inputs.values()
    )

    return build_financial_conditions_snapshot(
        resolved_as_of_date,
        inputs["fed_funds_rate"],
        inputs["treasury_2y"],
        inputs["treasury_10y"],
        inputs["real_yield_10y"],
        inputs["nfci"],
        inputs["yield_curve_2s10s"],
    )


def _print_rate_component(label: str, component: dict) -> None:
    print(f"{label}:")
    print(f"Observation date: {component['observation_date']}")
    print(f"Feature as of: {component['feature_as_of_date']}")
    print(f"Level: {component['level']}")


def print_financial_conditions_snapshot(snapshot: dict) -> None:
    """Print a readable Financial Conditions Snapshot console summary."""
    print("FINANCIAL CONDITIONS SNAPSHOT")
    print(f"As of: {snapshot['as_of_date']}")
    print("")

    _print_rate_component("Effective Fed Funds Rate", snapshot["fed_funds_rate"])
    print("")
    _print_rate_component("2Y Treasury Yield", snapshot["treasury_2y"])
    print("")
    _print_rate_component("10Y Treasury Yield", snapshot["treasury_10y"])
    print("")
    _print_rate_component("10Y Real Yield", snapshot["real_yield_10y"])
    print("")

    curve = snapshot["yield_curve_2s10s"]
    print("2s10s Treasury Spread:")
    print(f"Shape: {curve['shape']}")
    print(f"Observation date: {curve['observation_date']}")
    print(f"Feature as of: {curve['feature_as_of_date']}")
    print(f"DGS2: {curve['dgs2']}")
    print(f"DGS10: {curve['dgs10']}")
    print(f"Spread: {curve['spread']}")
    print("")

    nfci = snapshot["nfci"]
    print(f"NFCI: {nfci['position']}, {nfci['direction']}")
    print(f"Observation date: {nfci['observation_date']}")
    print(f"Feature as of: {nfci['feature_as_of_date']}")
    print(f"Level: {nfci['level']}")
    print(f"Change 4W: {nfci['change_4w']}")
    print(f"4W average: {nfci['moving_average_4w']}")
    print("Note: NFCI labels are mechanical descriptions, not trading signals")


def main() -> int:
    if len(sys.argv) not in (1, 2):
        print(
            "Usage: python -m app.analytics.financial_conditions_snapshot "
            "[AS_OF_DATE]",
            file=sys.stderr,
        )
        return 1

    try:
        requested_as_of_date = (
            _parse_as_of_date(sys.argv[1]) if len(sys.argv) == 2 else None
        )
        snapshot = get_financial_conditions_snapshot(requested_as_of_date)
        print_financial_conditions_snapshot(snapshot)
        return 0
    except Exception as error:
        print(f"Financial Conditions Snapshot failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
