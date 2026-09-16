"""Transparent Growth Snapshot using configured computed features."""

import sys
from datetime import date
from decimal import Decimal
from typing import Optional

from app.analytics.feature_store import load_latest_component_features
from app.analytics.labor_state import _parse_as_of_date
from app.database.connection import get_connection


GDP_FEATURES = ("qoq_annualized", "yoy")
CFNAI_FEATURES = ("level", "moving_average_3m")
INDUSTRIAL_PRODUCTION_FEATURES = ("mom", "yoy", "annualized_3m")
CAPACITY_UTILIZATION_FEATURES = ("level", "change_3m", "moving_average_3m")
DURABLE_GOODS_FEATURES = ("mom", "yoy", "moving_average_3m")


def classify_growth_momentum(short_term_growth, year_over_year_growth) -> str:
    """Classify mechanical growth momentum from short-term growth versus YoY."""
    short_term_growth = Decimal(str(short_term_growth))
    year_over_year_growth = Decimal(str(year_over_year_growth))

    if short_term_growth > year_over_year_growth:
        return "accelerating"
    if short_term_growth < year_over_year_growth:
        return "decelerating"
    return "stable"


def classify_cfnai_position(moving_average_3m) -> str:
    """Classify CFNAI position relative to its zero trend reference."""
    moving_average_3m = Decimal(str(moving_average_3m))

    if moving_average_3m > 0:
        return "above_trend"
    if moving_average_3m < 0:
        return "below_trend"
    return "at_trend"


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


def build_growth_snapshot(
    as_of_date,
    real_gdp_features: dict,
    cfnai_features: dict,
    industrial_production_features: dict,
    capacity_utilization_features: dict,
    durable_goods_features: dict,
) -> dict:
    """Build a structured Growth Snapshot from already-loaded feature values."""
    return {
        "as_of_date": str(as_of_date),
        "real_gdp": {
            **_with_dates(real_gdp_features),
            "qoq_annualized": real_gdp_features["qoq_annualized"],
            "yoy": real_gdp_features["yoy"],
            "momentum": classify_growth_momentum(
                real_gdp_features["qoq_annualized"],
                real_gdp_features["yoy"],
            ),
        },
        "cfnai": {
            **_with_dates(cfnai_features),
            "level": cfnai_features["level"],
            "moving_average_3m": cfnai_features["moving_average_3m"],
            "position": classify_cfnai_position(
                cfnai_features["moving_average_3m"]
            ),
        },
        "industrial_production": {
            **_with_dates(industrial_production_features),
            "mom": industrial_production_features["mom"],
            "yoy": industrial_production_features["yoy"],
            "annualized_3m": industrial_production_features["annualized_3m"],
            "momentum": classify_growth_momentum(
                industrial_production_features["annualized_3m"],
                industrial_production_features["yoy"],
            ),
        },
        "capacity_utilization": {
            **_with_dates(capacity_utilization_features),
            "level": capacity_utilization_features["level"],
            "change_3m": capacity_utilization_features["change_3m"],
            "moving_average_3m": capacity_utilization_features["moving_average_3m"],
            "direction": classify_direction_from_change(
                capacity_utilization_features["change_3m"]
            ),
        },
        "durable_goods_orders": {
            **_with_dates(durable_goods_features),
            "mom": durable_goods_features["mom"],
            "yoy": durable_goods_features["yoy"],
            "moving_average_3m": durable_goods_features["moving_average_3m"],
            "latest_direction": classify_direction_from_change(
                durable_goods_features["mom"]
            ),
        },
    }


def load_growth_snapshot_inputs(requested_as_of_date: Optional[date] = None) -> dict:
    """Load latest v1 feature values needed for the Growth Snapshot."""
    connection = None

    try:
        connection = get_connection()
        return {
            "real_gdp": load_latest_component_features(
                connection,
                "GDPC1",
                GDP_FEATURES,
                requested_as_of_date,
            ),
            "cfnai": load_latest_component_features(
                connection,
                "CFNAI",
                CFNAI_FEATURES,
                requested_as_of_date,
            ),
            "industrial_production": load_latest_component_features(
                connection,
                "INDPRO",
                INDUSTRIAL_PRODUCTION_FEATURES,
                requested_as_of_date,
            ),
            "capacity_utilization": load_latest_component_features(
                connection,
                "TCU",
                CAPACITY_UTILIZATION_FEATURES,
                requested_as_of_date,
            ),
            "durable_goods_orders": load_latest_component_features(
                connection,
                "DGORDER",
                DURABLE_GOODS_FEATURES,
                requested_as_of_date,
            ),
        }
    finally:
        if connection is not None:
            connection.close()


def get_growth_snapshot(requested_as_of_date: Optional[date] = None) -> dict:
    """Load and build the Growth Snapshot."""
    inputs = load_growth_snapshot_inputs(requested_as_of_date)
    resolved_as_of_date = requested_as_of_date or max(
        component["feature_as_of_date"] for component in inputs.values()
    )

    return build_growth_snapshot(
        resolved_as_of_date,
        inputs["real_gdp"],
        inputs["cfnai"],
        inputs["industrial_production"],
        inputs["capacity_utilization"],
        inputs["durable_goods_orders"],
    )


def print_growth_snapshot(snapshot: dict) -> None:
    """Print a readable Growth Snapshot console summary."""
    print("GROWTH SNAPSHOT")
    print(f"As of: {snapshot['as_of_date']}")
    print("")

    real_gdp = snapshot["real_gdp"]
    print(
        "Real GDP: "
        f"{real_gdp['momentum']} "
        f"(obs={real_gdp['observation_date']}, "
        f"feature_as_of={real_gdp['feature_as_of_date']})"
    )
    print(f"QoQ annualized: {real_gdp['qoq_annualized']}")
    print(f"YoY: {real_gdp['yoy']}")
    print("")

    cfnai = snapshot["cfnai"]
    print("CFNAI:")
    print(f"Observation date: {cfnai['observation_date']}")
    print(f"Feature as of: {cfnai['feature_as_of_date']}")
    print(f"Level: {cfnai['level']}")
    print(f"3M average: {cfnai['moving_average_3m']}")
    print(f"Position: {cfnai['position']}")
    print("")

    industrial_production = snapshot["industrial_production"]
    print(
        "Industrial Production: "
        f"{industrial_production['momentum']} "
        f"(obs={industrial_production['observation_date']}, "
        f"feature_as_of={industrial_production['feature_as_of_date']})"
    )
    print(f"MoM: {industrial_production['mom']}")
    print(f"YoY: {industrial_production['yoy']}")
    print(f"3M annualized: {industrial_production['annualized_3m']}")
    print("")

    capacity_utilization = snapshot["capacity_utilization"]
    print(
        "Capacity Utilization: "
        f"{capacity_utilization['direction']} "
        f"(obs={capacity_utilization['observation_date']}, "
        f"feature_as_of={capacity_utilization['feature_as_of_date']})"
    )
    print(f"Level: {capacity_utilization['level']}")
    print(f"Change 3M: {capacity_utilization['change_3m']}")
    print(f"3M average: {capacity_utilization['moving_average_3m']}")
    print("")

    durable_goods = snapshot["durable_goods_orders"]
    print(
        "Durable Goods Orders: "
        f"{durable_goods['latest_direction']} "
        f"(obs={durable_goods['observation_date']}, "
        f"feature_as_of={durable_goods['feature_as_of_date']})"
    )
    print(f"MoM: {durable_goods['mom']}")
    print(f"YoY: {durable_goods['yoy']}")
    print(f"3M average: {durable_goods['moving_average_3m']}")


def main() -> int:
    if len(sys.argv) not in (1, 2):
        print(
            "Usage: python -m app.analytics.growth_snapshot [AS_OF_DATE]",
            file=sys.stderr,
        )
        return 1

    try:
        requested_as_of_date = (
            _parse_as_of_date(sys.argv[1]) if len(sys.argv) == 2 else None
        )
        snapshot = get_growth_snapshot(requested_as_of_date)
        print_growth_snapshot(snapshot)
        return 0
    except Exception as error:
        print(f"Growth Snapshot failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
