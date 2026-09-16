"""Transparent Consumer Snapshot using configured computed features."""

import sys
from datetime import date
from decimal import Decimal
from typing import Optional

from app.analytics.feature_store import load_latest_component_features
from app.analytics.labor_state import _parse_as_of_date
from app.database.connection import get_connection


CONSUMER_GROWTH_FEATURES = ("mom", "yoy", "annualized_3m")
SAVING_RATE_FEATURES = ("level", "change_3m", "moving_average_3m")


def classify_consumer_growth_momentum(annualized_3m, yoy) -> str:
    """Classify mechanical consumer growth momentum from 3M annualized versus YoY."""
    annualized_3m = Decimal(str(annualized_3m))
    yoy = Decimal(str(yoy))

    if annualized_3m > yoy:
        return "accelerating"
    if annualized_3m < yoy:
        return "decelerating"
    return "stable"


def classify_saving_rate_direction(change_3m) -> str:
    """Classify saving-rate direction without assigning good/bad meaning."""
    change_3m = Decimal(str(change_3m))

    if change_3m > 0:
        return "rising"
    if change_3m < 0:
        return "falling"
    return "stable"


def _with_dates(features: dict) -> dict:
    return {
        "observation_date": str(features["observation_date"]),
        "feature_as_of_date": str(features["feature_as_of_date"]),
    }


def _growth_component(features: dict, *, nominal: bool = False) -> dict:
    component = {
        **_with_dates(features),
        "mom": features["mom"],
        "yoy": features["yoy"],
        "annualized_3m": features["annualized_3m"],
        "momentum": classify_consumer_growth_momentum(
            features["annualized_3m"],
            features["yoy"],
        ),
    }

    if nominal:
        component["series_type"] = "nominal"

    return component


def build_consumer_snapshot(
    as_of_date,
    retail_sales_features: dict,
    real_consumption_features: dict,
    real_disposable_income_features: dict,
    saving_rate_features: dict,
) -> dict:
    """Build a structured Consumer Snapshot from already-loaded feature values."""
    return {
        "as_of_date": str(as_of_date),
        "retail_sales": _growth_component(retail_sales_features, nominal=True),
        "real_consumption": _growth_component(real_consumption_features),
        "real_disposable_income": _growth_component(real_disposable_income_features),
        "saving_rate": {
            **_with_dates(saving_rate_features),
            "level": saving_rate_features["level"],
            "change_3m": saving_rate_features["change_3m"],
            "moving_average_3m": saving_rate_features["moving_average_3m"],
            "direction": classify_saving_rate_direction(
                saving_rate_features["change_3m"]
            ),
        },
    }


def load_consumer_snapshot_inputs(requested_as_of_date: Optional[date] = None) -> dict:
    """Load latest v1 feature values needed for the Consumer Snapshot."""
    connection = None

    try:
        connection = get_connection()
        return {
            "retail_sales": load_latest_component_features(
                connection,
                "RSAFS",
                CONSUMER_GROWTH_FEATURES,
                requested_as_of_date,
            ),
            "real_consumption": load_latest_component_features(
                connection,
                "PCEC96",
                CONSUMER_GROWTH_FEATURES,
                requested_as_of_date,
            ),
            "real_disposable_income": load_latest_component_features(
                connection,
                "DSPIC96",
                CONSUMER_GROWTH_FEATURES,
                requested_as_of_date,
            ),
            "saving_rate": load_latest_component_features(
                connection,
                "PSAVERT",
                SAVING_RATE_FEATURES,
                requested_as_of_date,
            ),
        }
    finally:
        if connection is not None:
            connection.close()


def get_consumer_snapshot(requested_as_of_date: Optional[date] = None) -> dict:
    """Load and build the Consumer Snapshot."""
    inputs = load_consumer_snapshot_inputs(requested_as_of_date)
    resolved_as_of_date = requested_as_of_date or max(
        component["feature_as_of_date"] for component in inputs.values()
    )

    return build_consumer_snapshot(
        resolved_as_of_date,
        inputs["retail_sales"],
        inputs["real_consumption"],
        inputs["real_disposable_income"],
        inputs["saving_rate"],
    )


def print_consumer_snapshot(snapshot: dict) -> None:
    """Print a readable Consumer Snapshot console summary."""
    print("CONSUMER SNAPSHOT")
    print(f"As of: {snapshot['as_of_date']}")
    print("")

    retail_sales = snapshot["retail_sales"]
    print(
        "Retail Sales: "
        f"{retail_sales['momentum']} "
        f"(obs={retail_sales['observation_date']}, "
        f"feature_as_of={retail_sales['feature_as_of_date']})"
    )
    print(f"MoM: {retail_sales['mom']}")
    print(f"YoY: {retail_sales['yoy']}")
    print(f"3M annualized: {retail_sales['annualized_3m']}")
    print("Note: nominal series")
    print("")

    real_consumption = snapshot["real_consumption"]
    print(
        "Real Consumption: "
        f"{real_consumption['momentum']} "
        f"(obs={real_consumption['observation_date']}, "
        f"feature_as_of={real_consumption['feature_as_of_date']})"
    )
    print(f"MoM: {real_consumption['mom']}")
    print(f"YoY: {real_consumption['yoy']}")
    print(f"3M annualized: {real_consumption['annualized_3m']}")
    print("")

    real_income = snapshot["real_disposable_income"]
    print(
        "Real Disposable Income: "
        f"{real_income['momentum']} "
        f"(obs={real_income['observation_date']}, "
        f"feature_as_of={real_income['feature_as_of_date']})"
    )
    print(f"MoM: {real_income['mom']}")
    print(f"YoY: {real_income['yoy']}")
    print(f"3M annualized: {real_income['annualized_3m']}")
    print("")

    saving_rate = snapshot["saving_rate"]
    print(
        "Saving Rate: "
        f"{saving_rate['direction']} "
        f"(obs={saving_rate['observation_date']}, "
        f"feature_as_of={saving_rate['feature_as_of_date']})"
    )
    print(f"Level: {saving_rate['level']}")
    print(f"Change 3M: {saving_rate['change_3m']}")
    print(f"3M average: {saving_rate['moving_average_3m']}")


def main() -> int:
    if len(sys.argv) not in (1, 2):
        print(
            "Usage: python -m app.analytics.consumer_snapshot [AS_OF_DATE]",
            file=sys.stderr,
        )
        return 1

    try:
        requested_as_of_date = (
            _parse_as_of_date(sys.argv[1]) if len(sys.argv) == 2 else None
        )
        snapshot = get_consumer_snapshot(requested_as_of_date)
        print_consumer_snapshot(snapshot)
        return 0
    except Exception as error:
        print(f"Consumer Snapshot failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
