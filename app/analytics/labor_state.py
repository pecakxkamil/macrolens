"""Deterministic v1 Labor Market Momentum classification."""

import sys
from datetime import date
from decimal import Decimal
from typing import Optional

from app.analytics.features import METHODOLOGY_VERSION
from app.database.connection import get_connection


PAYROLL_FEATURES = (
    "monthly_change",
    "monthly_change_ma_3m",
    "monthly_change_ma_6m",
)
UNEMPLOYMENT_FEATURES = ("level", "change_3m")
CLAIMS_FEATURES = ("moving_average_4w", "moving_average_13w")

LATEST_FEATURE_AS_OF_SQL = """
SELECT as_of_date
FROM computed_features
WHERE series_id = %s
  AND methodology_version = %s
  AND feature_name = ANY(%s)
  AND (%s::date IS NULL OR as_of_date <= %s)
GROUP BY as_of_date
HAVING COUNT(DISTINCT feature_name) = %s
ORDER BY as_of_date DESC
LIMIT 1;
"""

LATEST_COMMON_OBSERVATION_DATE_SQL = """
SELECT observation_date
FROM computed_features
WHERE series_id = %s
  AND methodology_version = %s
  AND as_of_date = %s
  AND feature_name = ANY(%s)
GROUP BY observation_date
HAVING COUNT(DISTINCT feature_name) = %s
ORDER BY observation_date DESC
LIMIT 1;
"""

FEATURE_VALUES_SQL = """
SELECT feature_name, feature_value
FROM computed_features
WHERE series_id = %s
  AND methodology_version = %s
  AND as_of_date = %s
  AND observation_date = %s
  AND feature_name = ANY(%s);
"""


def _compare(lower_is_better: bool, first_value, second_value) -> str:
    first_value = Decimal(str(first_value))
    second_value = Decimal(str(second_value))

    if first_value == second_value:
        return "stable"

    if lower_is_better:
        return "improving" if first_value < second_value else "weakening"

    return "improving" if first_value > second_value else "weakening"


def classify_payroll_momentum(monthly_change_ma_3m, monthly_change_ma_6m) -> str:
    """Classify payroll momentum by comparing 3M and 6M job-gain averages."""
    return _compare(False, monthly_change_ma_3m, monthly_change_ma_6m)


def classify_unemployment_momentum(change_3m) -> str:
    """Classify unemployment momentum using the 3-month change."""
    change_3m = Decimal(str(change_3m))
    if change_3m < 0:
        return "improving"
    if change_3m > 0:
        return "weakening"
    return "stable"


def classify_claims_momentum(moving_average_4w, moving_average_13w) -> str:
    """Classify claims momentum by comparing 4W and 13W averages."""
    return _compare(True, moving_average_4w, moving_average_13w)


def classify_overall_labor_momentum(component_momentums) -> str:
    """Classify overall labor momentum from three component classifications."""
    improving_count = component_momentums.count("improving")
    weakening_count = component_momentums.count("weakening")

    if improving_count >= 2:
        return "improving"
    if weakening_count >= 2:
        return "weakening"
    return "mixed"


def build_labor_momentum_state(
    as_of_date,
    payroll_features: dict,
    unemployment_features: dict,
    claims_features: dict,
) -> dict:
    """Build a structured Labor Market Momentum result from feature values."""
    payroll_momentum = classify_payroll_momentum(
        payroll_features["monthly_change_ma_3m"],
        payroll_features["monthly_change_ma_6m"],
    )
    unemployment_momentum = classify_unemployment_momentum(
        unemployment_features["change_3m"]
    )
    claims_momentum = classify_claims_momentum(
        claims_features["moving_average_4w"],
        claims_features["moving_average_13w"],
    )
    overall_momentum = classify_overall_labor_momentum(
        [payroll_momentum, unemployment_momentum, claims_momentum]
    )

    return {
        "as_of_date": str(as_of_date),
        "payrolls": {
            "monthly_change": payroll_features["monthly_change"],
            "monthly_change_ma_3m": payroll_features["monthly_change_ma_3m"],
            "monthly_change_ma_6m": payroll_features["monthly_change_ma_6m"],
            "momentum": payroll_momentum,
        },
        "unemployment": {
            "level": unemployment_features["level"],
            "change_3m": unemployment_features["change_3m"],
            "momentum": unemployment_momentum,
        },
        "claims": {
            "moving_average_4w": claims_features["moving_average_4w"],
            "moving_average_13w": claims_features["moving_average_13w"],
            "momentum": claims_momentum,
        },
        "overall_momentum": overall_momentum,
    }


def _parse_as_of_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise RuntimeError(f"Invalid as_of_date, expected YYYY-MM-DD: {value}") from error


def _load_latest_component_features(
    connection,
    series_id: str,
    feature_names: tuple,
    requested_as_of_date: Optional[date],
) -> dict:
    with connection.cursor() as cursor:
        cursor.execute(
            LATEST_FEATURE_AS_OF_SQL,
            (
                series_id,
                METHODOLOGY_VERSION,
                list(feature_names),
                requested_as_of_date,
                requested_as_of_date,
                len(feature_names),
            ),
        )
        as_of_result = cursor.fetchone()

        if as_of_result is None or as_of_result[0] is None:
            raise RuntimeError(f"No v1 features found for {series_id}.")

        feature_as_of_date = as_of_result[0]
        cursor.execute(
            LATEST_COMMON_OBSERVATION_DATE_SQL,
            (
                series_id,
                METHODOLOGY_VERSION,
                feature_as_of_date,
                list(feature_names),
                len(feature_names),
            ),
        )
        observation_result = cursor.fetchone()

        if observation_result is None:
            raise RuntimeError(
                f"No complete feature set found for {series_id} as of "
                f"{feature_as_of_date}."
            )

        observation_date = observation_result[0]
        cursor.execute(
            FEATURE_VALUES_SQL,
            (
                series_id,
                METHODOLOGY_VERSION,
                feature_as_of_date,
                observation_date,
                list(feature_names),
            ),
        )
        rows = cursor.fetchall()

    values = {feature_name: feature_value for feature_name, feature_value in rows}
    missing_features = set(feature_names) - set(values.keys())
    if missing_features:
        missing = ", ".join(sorted(missing_features))
        raise RuntimeError(f"Missing features for {series_id}: {missing}")

    values["feature_as_of_date"] = feature_as_of_date
    values["observation_date"] = observation_date
    return values


def load_labor_momentum_inputs(requested_as_of_date: Optional[date] = None) -> dict:
    """Load latest v1 feature values needed for Labor Market Momentum."""
    connection = None

    try:
        connection = get_connection()
        return {
            "payrolls": _load_latest_component_features(
                connection,
                "PAYEMS",
                PAYROLL_FEATURES,
                requested_as_of_date,
            ),
            "unemployment": _load_latest_component_features(
                connection,
                "UNRATE",
                UNEMPLOYMENT_FEATURES,
                requested_as_of_date,
            ),
            "claims": _load_latest_component_features(
                connection,
                "ICSA",
                CLAIMS_FEATURES,
                requested_as_of_date,
            ),
        }
    finally:
        if connection is not None:
            connection.close()


def get_labor_momentum_state(requested_as_of_date: Optional[date] = None) -> dict:
    """Load feature inputs and return the current Labor Market Momentum state."""
    inputs = load_labor_momentum_inputs(requested_as_of_date)
    resolved_as_of_date = requested_as_of_date or max(
        component["feature_as_of_date"] for component in inputs.values()
    )

    return build_labor_momentum_state(
        resolved_as_of_date,
        inputs["payrolls"],
        inputs["unemployment"],
        inputs["claims"],
    )


def print_labor_momentum_summary(state: dict) -> None:
    """Print a readable Labor Market Momentum console summary."""
    payrolls = state["payrolls"]
    unemployment = state["unemployment"]
    claims = state["claims"]

    print("LABOR MARKET MOMENTUM")
    print(f"As of: {state['as_of_date']}")
    print("")
    print(
        "Payrolls: "
        f"{payrolls['momentum']} "
        f"(monthly_change={payrolls['monthly_change']}, "
        f"monthly_change_ma_3m={payrolls['monthly_change_ma_3m']}, "
        f"monthly_change_ma_6m={payrolls['monthly_change_ma_6m']})"
    )
    print(
        "Unemployment: "
        f"{unemployment['momentum']} "
        f"(level={unemployment['level']}, change_3m={unemployment['change_3m']})"
    )
    print(
        "Claims: "
        f"{claims['momentum']} "
        f"(moving_average_4w={claims['moving_average_4w']}, "
        f"moving_average_13w={claims['moving_average_13w']})"
    )
    print("")
    print(f"Overall momentum: {state['overall_momentum']}")


def main() -> int:
    if len(sys.argv) not in (1, 2):
        print(
            "Usage: python -m app.analytics.labor_state [AS_OF_DATE]",
            file=sys.stderr,
        )
        return 1

    try:
        requested_as_of_date = (
            _parse_as_of_date(sys.argv[1]) if len(sys.argv) == 2 else None
        )
        state = get_labor_momentum_state(requested_as_of_date)
        print_labor_momentum_summary(state)
        return 0
    except Exception as error:
        print(f"Labor Market Momentum failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
