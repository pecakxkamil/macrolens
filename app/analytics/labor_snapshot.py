"""Transparent Labor Market Snapshot using configured computed features."""

import sys
from datetime import date
from decimal import Decimal
from typing import Optional

from app.analytics.feature_store import load_latest_component_features
from app.analytics.labor_state import (
    CLAIMS_FEATURES,
    PAYROLL_FEATURES,
    UNEMPLOYMENT_FEATURES,
    _parse_as_of_date,
    build_labor_momentum_state,
    classify_claims_momentum,
)
from app.database.connection import get_connection


CONTINUING_CLAIMS_FEATURES = ("moving_average_4w", "moving_average_13w")
JOB_OPENINGS_FEATURES = ("level", "change_3m", "yoy")
PARTICIPATION_FEATURES = ("level", "change_3m", "moving_average_3m")
EARNINGS_FEATURES = ("mom", "yoy", "annualized_3m")


def classify_direction_from_change(change_value) -> str:
    """Classify direction from a signed change without assigning good/bad meaning."""
    change_value = Decimal(str(change_value))
    if change_value > 0:
        return "rising"
    if change_value < 0:
        return "falling"
    return "stable"


def classify_continuing_claims_momentum(moving_average_4w, moving_average_13w) -> str:
    """Classify continuing claims with the same directional logic as initial claims."""
    return classify_claims_momentum(moving_average_4w, moving_average_13w)


def _with_dates(features: dict) -> dict:
    return {
        "observation_date": str(features["observation_date"]),
        "feature_as_of_date": str(features["feature_as_of_date"]),
    }


def build_labor_snapshot(
    as_of_date,
    payroll_features: dict,
    unemployment_features: dict,
    initial_claims_features: dict,
    continuing_claims_features: dict,
    job_openings_features: dict,
    participation_features: dict,
    earnings_features: dict,
) -> dict:
    """Build a structured snapshot from already-loaded feature values."""
    labor_momentum = build_labor_momentum_state(
        as_of_date,
        payroll_features,
        unemployment_features,
        initial_claims_features,
    )

    continuing_claims_momentum = classify_continuing_claims_momentum(
        continuing_claims_features["moving_average_4w"],
        continuing_claims_features["moving_average_13w"],
    )
    job_openings_direction = classify_direction_from_change(
        job_openings_features["change_3m"]
    )
    participation_direction = classify_direction_from_change(
        participation_features["change_3m"]
    )

    return {
        "as_of_date": str(as_of_date),
        "payrolls": {
            **_with_dates(payroll_features),
            "monthly_change": payroll_features["monthly_change"],
            "monthly_change_ma_3m": payroll_features["monthly_change_ma_3m"],
            "monthly_change_ma_6m": payroll_features["monthly_change_ma_6m"],
            "momentum": labor_momentum["payrolls"]["momentum"],
        },
        "unemployment": {
            **_with_dates(unemployment_features),
            "level": unemployment_features["level"],
            "change_3m": unemployment_features["change_3m"],
            "momentum": labor_momentum["unemployment"]["momentum"],
        },
        "initial_claims": {
            **_with_dates(initial_claims_features),
            "moving_average_4w": initial_claims_features["moving_average_4w"],
            "moving_average_13w": initial_claims_features["moving_average_13w"],
            "momentum": labor_momentum["claims"]["momentum"],
        },
        "continuing_claims": {
            **_with_dates(continuing_claims_features),
            "moving_average_4w": continuing_claims_features["moving_average_4w"],
            "moving_average_13w": continuing_claims_features["moving_average_13w"],
            "momentum": continuing_claims_momentum,
        },
        "job_openings": {
            **_with_dates(job_openings_features),
            "level": job_openings_features["level"],
            "change_3m": job_openings_features["change_3m"],
            "yoy": job_openings_features["yoy"],
            "direction": job_openings_direction,
        },
        "labor_force_participation": {
            **_with_dates(participation_features),
            "level": participation_features["level"],
            "change_3m": participation_features["change_3m"],
            "moving_average_3m": participation_features["moving_average_3m"],
            "direction": participation_direction,
        },
        "average_hourly_earnings": {
            **_with_dates(earnings_features),
            "mom": earnings_features["mom"],
            "yoy": earnings_features["yoy"],
            "annualized_3m": earnings_features["annualized_3m"],
        },
        "overall_momentum": labor_momentum["overall_momentum"],
    }


def load_labor_snapshot_inputs(requested_as_of_date: Optional[date] = None) -> dict:
    """Load latest v1 feature values needed for the full labor snapshot."""
    connection = None

    try:
        connection = get_connection()
        return {
            "payrolls": load_latest_component_features(
                connection,
                "PAYEMS",
                PAYROLL_FEATURES,
                requested_as_of_date,
            ),
            "unemployment": load_latest_component_features(
                connection,
                "UNRATE",
                UNEMPLOYMENT_FEATURES,
                requested_as_of_date,
            ),
            "initial_claims": load_latest_component_features(
                connection,
                "ICSA",
                CLAIMS_FEATURES,
                requested_as_of_date,
            ),
            "continuing_claims": load_latest_component_features(
                connection,
                "CCSA",
                CONTINUING_CLAIMS_FEATURES,
                requested_as_of_date,
            ),
            "job_openings": load_latest_component_features(
                connection,
                "JTSJOL",
                JOB_OPENINGS_FEATURES,
                requested_as_of_date,
            ),
            "labor_force_participation": load_latest_component_features(
                connection,
                "CIVPART",
                PARTICIPATION_FEATURES,
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


def get_labor_snapshot(requested_as_of_date: Optional[date] = None) -> dict:
    """Load and build the Labor Market Snapshot."""
    inputs = load_labor_snapshot_inputs(requested_as_of_date)
    resolved_as_of_date = requested_as_of_date or max(
        component["feature_as_of_date"] for component in inputs.values()
    )

    return build_labor_snapshot(
        resolved_as_of_date,
        inputs["payrolls"],
        inputs["unemployment"],
        inputs["initial_claims"],
        inputs["continuing_claims"],
        inputs["job_openings"],
        inputs["labor_force_participation"],
        inputs["average_hourly_earnings"],
    )


def print_labor_snapshot(snapshot: dict) -> None:
    """Print a readable Labor Market Snapshot console summary."""
    print("LABOR MARKET SNAPSHOT")
    print(f"As of: {snapshot['as_of_date']}")
    print("")

    payrolls = snapshot["payrolls"]
    print(
        "Payrolls: "
        f"{payrolls['momentum']} "
        f"(obs={payrolls['observation_date']}, "
        f"feature_as_of={payrolls['feature_as_of_date']}, "
        f"monthly_change={payrolls['monthly_change']}, "
        f"monthly_change_ma_3m={payrolls['monthly_change_ma_3m']}, "
        f"monthly_change_ma_6m={payrolls['monthly_change_ma_6m']})"
    )

    unemployment = snapshot["unemployment"]
    print(
        "Unemployment: "
        f"{unemployment['momentum']} "
        f"(obs={unemployment['observation_date']}, "
        f"feature_as_of={unemployment['feature_as_of_date']}, "
        f"level={unemployment['level']}, change_3m={unemployment['change_3m']})"
    )

    initial_claims = snapshot["initial_claims"]
    print(
        "Initial claims: "
        f"{initial_claims['momentum']} "
        f"(obs={initial_claims['observation_date']}, "
        f"feature_as_of={initial_claims['feature_as_of_date']}, "
        f"moving_average_4w={initial_claims['moving_average_4w']}, "
        f"moving_average_13w={initial_claims['moving_average_13w']})"
    )

    continuing_claims = snapshot["continuing_claims"]
    print(
        "Continuing claims: "
        f"{continuing_claims['momentum']} "
        f"(obs={continuing_claims['observation_date']}, "
        f"feature_as_of={continuing_claims['feature_as_of_date']}, "
        f"moving_average_4w={continuing_claims['moving_average_4w']}, "
        f"moving_average_13w={continuing_claims['moving_average_13w']})"
    )

    job_openings = snapshot["job_openings"]
    print(
        "JOLTS job openings: "
        f"{job_openings['direction']} "
        f"(obs={job_openings['observation_date']}, "
        f"feature_as_of={job_openings['feature_as_of_date']}, "
        f"level={job_openings['level']}, change_3m={job_openings['change_3m']}, "
        f"yoy={job_openings['yoy']})"
    )

    participation = snapshot["labor_force_participation"]
    print(
        "Labor force participation: "
        f"{participation['direction']} "
        f"(obs={participation['observation_date']}, "
        f"feature_as_of={participation['feature_as_of_date']}, "
        f"level={participation['level']}, "
        f"change_3m={participation['change_3m']}, "
        f"moving_average_3m={participation['moving_average_3m']})"
    )

    earnings = snapshot["average_hourly_earnings"]
    print(
        "Average hourly earnings: "
        f"(obs={earnings['observation_date']}, "
        f"feature_as_of={earnings['feature_as_of_date']}, "
        f"mom={earnings['mom']}, yoy={earnings['yoy']}, "
        f"annualized_3m={earnings['annualized_3m']})"
    )

    print("")
    print(f"Overall momentum: {snapshot['overall_momentum']}")


def main() -> int:
    if len(sys.argv) not in (1, 2):
        print(
            "Usage: python -m app.analytics.labor_snapshot [AS_OF_DATE]",
            file=sys.stderr,
        )
        return 1

    try:
        requested_as_of_date = (
            _parse_as_of_date(sys.argv[1]) if len(sys.argv) == 2 else None
        )
        snapshot = get_labor_snapshot(requested_as_of_date)
        print_labor_snapshot(snapshot)
        return 0
    except Exception as error:
        print(f"Labor Market Snapshot failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
