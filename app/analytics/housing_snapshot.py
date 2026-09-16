"""Transparent Housing Snapshot using configured computed features."""

import sys
from datetime import date
from decimal import Decimal
from typing import Optional

from app.analytics.feature_store import load_latest_component_features
from app.analytics.labor_state import _parse_as_of_date
from app.database.connection import get_connection


MONTHLY_HOUSING_FEATURES = ("level", "mom", "yoy", "moving_average_3m")
MORTGAGE_RATE_FEATURES = ("level", "change_4w", "change_13w", "moving_average_4w")


def classify_direction_from_change(change_value) -> str:
    """Classify direction from a signed change without assigning good/bad meaning."""
    change_value = Decimal(str(change_value))

    if change_value > 0:
        return "rising"
    if change_value < 0:
        return "falling"
    return "stable"


def _with_dates(features: dict) -> dict:
    return {
        "observation_date": str(features["observation_date"]),
        "feature_as_of_date": str(features["feature_as_of_date"]),
    }


def _monthly_housing_component(features: dict) -> dict:
    return {
        **_with_dates(features),
        "level": features["level"],
        "mom": features["mom"],
        "yoy": features["yoy"],
        "moving_average_3m": features["moving_average_3m"],
        "direction": classify_direction_from_change(features["mom"]),
    }


def build_housing_snapshot(
    as_of_date,
    housing_starts_features: dict,
    building_permits_features: dict,
    new_home_sales_features: dict,
    mortgage_rate_features: dict,
) -> dict:
    """Build a structured Housing Snapshot from already-loaded feature values."""
    return {
        "as_of_date": str(as_of_date),
        "housing_starts": _monthly_housing_component(housing_starts_features),
        "building_permits": _monthly_housing_component(building_permits_features),
        "new_home_sales": _monthly_housing_component(new_home_sales_features),
        "mortgage_rate": {
            **_with_dates(mortgage_rate_features),
            "level": mortgage_rate_features["level"],
            "change_4w": mortgage_rate_features["change_4w"],
            "change_13w": mortgage_rate_features["change_13w"],
            "moving_average_4w": mortgage_rate_features["moving_average_4w"],
            "direction": classify_direction_from_change(
                mortgage_rate_features["change_4w"]
            ),
        },
    }


def load_housing_snapshot_inputs(requested_as_of_date: Optional[date] = None) -> dict:
    """Load latest v1 feature values needed for the Housing Snapshot."""
    connection = None

    try:
        connection = get_connection()
        return {
            "housing_starts": load_latest_component_features(
                connection,
                "HOUST",
                MONTHLY_HOUSING_FEATURES,
                requested_as_of_date,
            ),
            "building_permits": load_latest_component_features(
                connection,
                "PERMIT",
                MONTHLY_HOUSING_FEATURES,
                requested_as_of_date,
            ),
            "new_home_sales": load_latest_component_features(
                connection,
                "HSN1F",
                MONTHLY_HOUSING_FEATURES,
                requested_as_of_date,
            ),
            "mortgage_rate": load_latest_component_features(
                connection,
                "MORTGAGE30US",
                MORTGAGE_RATE_FEATURES,
                requested_as_of_date,
            ),
        }
    finally:
        if connection is not None:
            connection.close()


def get_housing_snapshot(requested_as_of_date: Optional[date] = None) -> dict:
    """Load and build the Housing Snapshot."""
    inputs = load_housing_snapshot_inputs(requested_as_of_date)
    resolved_as_of_date = requested_as_of_date or max(
        component["feature_as_of_date"] for component in inputs.values()
    )

    return build_housing_snapshot(
        resolved_as_of_date,
        inputs["housing_starts"],
        inputs["building_permits"],
        inputs["new_home_sales"],
        inputs["mortgage_rate"],
    )


def _print_monthly_component(label: str, component: dict) -> None:
    print(
        f"{label}: {component['direction']} "
        f"(obs={component['observation_date']}, "
        f"feature_as_of={component['feature_as_of_date']})"
    )
    print(f"Level: {component['level']}")
    print(f"MoM: {component['mom']}")
    print(f"YoY: {component['yoy']}")
    print(f"3M average: {component['moving_average_3m']}")


def print_housing_snapshot(snapshot: dict) -> None:
    """Print a readable Housing Snapshot console summary."""
    print("HOUSING SNAPSHOT")
    print(f"As of: {snapshot['as_of_date']}")
    print("")

    _print_monthly_component("Housing Starts", snapshot["housing_starts"])
    print("")
    _print_monthly_component("Building Permits", snapshot["building_permits"])
    print("")
    _print_monthly_component("New Home Sales", snapshot["new_home_sales"])
    print("")

    mortgage_rate = snapshot["mortgage_rate"]
    print(
        "30Y Mortgage Rate: "
        f"{mortgage_rate['direction']} "
        f"(obs={mortgage_rate['observation_date']}, "
        f"feature_as_of={mortgage_rate['feature_as_of_date']})"
    )
    print(f"Level: {mortgage_rate['level']}")
    print(f"Change 4W: {mortgage_rate['change_4w']}")
    print(f"Change 13W: {mortgage_rate['change_13w']}")
    print(f"4W average: {mortgage_rate['moving_average_4w']}")
    print("Note: mortgage-rate changes are percentage-point differences")


def main() -> int:
    if len(sys.argv) not in (1, 2):
        print(
            "Usage: python -m app.analytics.housing_snapshot [AS_OF_DATE]",
            file=sys.stderr,
        )
        return 1

    try:
        requested_as_of_date = (
            _parse_as_of_date(sys.argv[1]) if len(sys.argv) == 2 else None
        )
        snapshot = get_housing_snapshot(requested_as_of_date)
        print_housing_snapshot(snapshot)
        return 0
    except Exception as error:
        print(f"Housing Snapshot failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
