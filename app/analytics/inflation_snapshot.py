"""Transparent Inflation Snapshot using configured computed features."""

import sys
from datetime import date
from decimal import Decimal
from typing import Optional

from app.analytics.feature_store import load_latest_component_features
from app.analytics.labor_state import _parse_as_of_date
from app.database.connection import get_connection


PRICE_INDEX_FEATURES = ("mom", "yoy", "annualized_3m")
ECI_FEATURES = ("qoq", "yoy")
EARNINGS_FEATURES = ("mom", "yoy", "annualized_3m")


def classify_inflation_momentum(annualized_3m, yoy) -> str:
    """Classify price-index momentum from 3M annualized inflation versus YoY."""
    annualized_3m = Decimal(str(annualized_3m))
    yoy = Decimal(str(yoy))

    if annualized_3m > yoy:
        return "accelerating"
    if annualized_3m < yoy:
        return "decelerating"
    return "stable"


def _with_dates(features: dict) -> dict:
    return {
        "observation_date": str(features["observation_date"]),
        "feature_as_of_date": str(features["feature_as_of_date"]),
    }


def _price_component(features: dict) -> dict:
    return {
        **_with_dates(features),
        "mom": features["mom"],
        "yoy": features["yoy"],
        "annualized_3m": features["annualized_3m"],
        "momentum": classify_inflation_momentum(
            features["annualized_3m"],
            features["yoy"],
        ),
    }


def build_inflation_snapshot(
    as_of_date,
    headline_cpi_features: dict,
    core_cpi_features: dict,
    headline_pce_features: dict,
    core_pce_features: dict,
    eci_features: dict,
    earnings_features: dict,
) -> dict:
    """Build a structured Inflation Snapshot from already-loaded feature values."""
    return {
        "as_of_date": str(as_of_date),
        "headline_cpi": _price_component(headline_cpi_features),
        "core_cpi": _price_component(core_cpi_features),
        "headline_pce": _price_component(headline_pce_features),
        "core_pce": _price_component(core_pce_features),
        "employment_cost_index": {
            **_with_dates(eci_features),
            "qoq": eci_features["qoq"],
            "yoy": eci_features["yoy"],
        },
        "average_hourly_earnings": {
            **_with_dates(earnings_features),
            "mom": earnings_features["mom"],
            "yoy": earnings_features["yoy"],
            "annualized_3m": earnings_features["annualized_3m"],
        },
    }


def load_inflation_snapshot_inputs(requested_as_of_date: Optional[date] = None) -> dict:
    """Load latest v1 feature values needed for the Inflation Snapshot."""
    connection = None

    try:
        connection = get_connection()
        return {
            "headline_cpi": load_latest_component_features(
                connection,
                "CPIAUCSL",
                PRICE_INDEX_FEATURES,
                requested_as_of_date,
            ),
            "core_cpi": load_latest_component_features(
                connection,
                "CPILFESL",
                PRICE_INDEX_FEATURES,
                requested_as_of_date,
            ),
            "headline_pce": load_latest_component_features(
                connection,
                "PCEPI",
                PRICE_INDEX_FEATURES,
                requested_as_of_date,
            ),
            "core_pce": load_latest_component_features(
                connection,
                "PCEPILFE",
                PRICE_INDEX_FEATURES,
                requested_as_of_date,
            ),
            "employment_cost_index": load_latest_component_features(
                connection,
                "ECIALLCIV",
                ECI_FEATURES,
                requested_as_of_date,
            ),
            "average_hourly_earnings": load_latest_component_features(
                connection,
                "CES0500000003",
                EARNINGS_FEATURES,
                requested_as_of_date,
            ),
        }
    finally:
        if connection is not None:
            connection.close()


def get_inflation_snapshot(requested_as_of_date: Optional[date] = None) -> dict:
    """Load and build the Inflation Snapshot."""
    inputs = load_inflation_snapshot_inputs(requested_as_of_date)
    resolved_as_of_date = requested_as_of_date or max(
        component["feature_as_of_date"] for component in inputs.values()
    )

    return build_inflation_snapshot(
        resolved_as_of_date,
        inputs["headline_cpi"],
        inputs["core_cpi"],
        inputs["headline_pce"],
        inputs["core_pce"],
        inputs["employment_cost_index"],
        inputs["average_hourly_earnings"],
    )


def print_inflation_snapshot(snapshot: dict) -> None:
    """Print a readable Inflation Snapshot console summary."""
    print("INFLATION SNAPSHOT")
    print(f"As of: {snapshot['as_of_date']}")
    print("")

    for label, key in (
        ("Headline CPI", "headline_cpi"),
        ("Core CPI", "core_cpi"),
        ("Headline PCE", "headline_pce"),
        ("Core PCE", "core_pce"),
    ):
        component = snapshot[key]
        print(
            f"{label}: {component['momentum']} "
            f"(obs={component['observation_date']}, "
            f"feature_as_of={component['feature_as_of_date']})"
        )
        print(f"MoM: {component['mom']}")
        print(f"YoY: {component['yoy']}")
        print(f"3M annualized: {component['annualized_3m']}")
        print("")

    eci = snapshot["employment_cost_index"]
    print("Employment Cost Index:")
    print(f"Observation date: {eci['observation_date']}")
    print(f"Feature as of: {eci['feature_as_of_date']}")
    print(f"QoQ: {eci['qoq']}")
    print(f"YoY: {eci['yoy']}")
    print("")

    earnings = snapshot["average_hourly_earnings"]
    print("Average Hourly Earnings:")
    print(f"Observation date: {earnings['observation_date']}")
    print(f"Feature as of: {earnings['feature_as_of_date']}")
    print(f"MoM: {earnings['mom']}")
    print(f"YoY: {earnings['yoy']}")
    print(f"3M annualized: {earnings['annualized_3m']}")


def main() -> int:
    if len(sys.argv) not in (1, 2):
        print(
            "Usage: python -m app.analytics.inflation_snapshot [AS_OF_DATE]",
            file=sys.stderr,
        )
        return 1

    try:
        requested_as_of_date = (
            _parse_as_of_date(sys.argv[1]) if len(sys.argv) == 2 else None
        )
        snapshot = get_inflation_snapshot(requested_as_of_date)
        print_inflation_snapshot(snapshot)
        return 0
    except Exception as error:
        print(f"Inflation Snapshot failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
