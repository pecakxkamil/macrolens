"""USA Economy Now aggregation layer for existing domain snapshots."""

import sys
from datetime import date
from typing import Optional

from app.analytics import consumer_snapshot
from app.analytics import financial_conditions_snapshot
from app.analytics import growth_snapshot
from app.analytics import housing_snapshot
from app.analytics import inflation_snapshot
from app.analytics import labor_snapshot
from app.analytics.labor_state import _parse_as_of_date


DOMAIN_LABELS = {
    "labor": "Labor",
    "inflation": "Inflation",
    "growth": "Growth",
    "consumer": "Consumer",
    "housing": "Housing",
    "financial_conditions": "Financial Conditions",
}


def build_usa_economy_now(as_of_date: Optional[date] = None) -> dict:
    """Build a current-state view from the six existing domain snapshots."""
    snapshots = {
        "labor": labor_snapshot.get_labor_snapshot(as_of_date),
        "inflation": inflation_snapshot.get_inflation_snapshot(as_of_date),
        "growth": growth_snapshot.get_growth_snapshot(as_of_date),
        "consumer": consumer_snapshot.get_consumer_snapshot(as_of_date),
        "housing": housing_snapshot.get_housing_snapshot(as_of_date),
        "financial_conditions": (
            financial_conditions_snapshot.get_financial_conditions_snapshot(as_of_date)
        ),
    }
    component_as_of_dates = {
        domain: str(snapshot["as_of_date"])
        for domain, snapshot in snapshots.items()
    }
    top_level_as_of_date = (
        str(as_of_date) if as_of_date is not None else max(component_as_of_dates.values())
    )

    return {
        "as_of_date": top_level_as_of_date,
        "component_as_of_dates": component_as_of_dates,
        **snapshots,
    }


def print_usa_economy_now(snapshot: dict) -> None:
    """Print a compact USA Economy Now console summary."""
    print("USA ECONOMY NOW")
    print(f"As of: {snapshot['as_of_date']}")
    print("")

    print("Component freshness:")
    for domain, label in DOMAIN_LABELS.items():
        print(f"{label}: {snapshot['component_as_of_dates'][domain]}")

    print("")
    _print_labor_section(snapshot["labor"])
    print("")
    _print_inflation_section(snapshot["inflation"])
    print("")
    _print_growth_section(snapshot["growth"])
    print("")
    _print_consumer_section(snapshot["consumer"])
    print("")
    _print_housing_section(snapshot["housing"])
    print("")
    _print_financial_conditions_section(snapshot["financial_conditions"])


def _print_labor_section(snapshot: dict) -> None:
    print("LABOR")
    print(f"Overall momentum: {snapshot['overall_momentum']}")
    print(f"Payrolls: {snapshot['payrolls']['momentum']}")
    print(f"Unemployment: {snapshot['unemployment']['momentum']}")
    print(f"Initial claims: {snapshot['initial_claims']['momentum']}")


def _print_inflation_section(snapshot: dict) -> None:
    print("INFLATION")
    print(f"Headline CPI: {snapshot['headline_cpi']['momentum']}")
    print(f"Core CPI: {snapshot['core_cpi']['momentum']}")
    print(f"Headline PCE: {snapshot['headline_pce']['momentum']}")
    print(f"Core PCE: {snapshot['core_pce']['momentum']}")
    print(f"ECI YoY: {snapshot['employment_cost_index']['yoy']}")
    print(f"Average hourly earnings YoY: {snapshot['average_hourly_earnings']['yoy']}")


def _print_growth_section(snapshot: dict) -> None:
    print("GROWTH")
    print(f"Real GDP: {snapshot['real_gdp']['momentum']}")
    print(f"CFNAI: {snapshot['cfnai']['position']}")
    print(f"Industrial production: {snapshot['industrial_production']['momentum']}")
    print(f"Capacity utilization: {snapshot['capacity_utilization']['direction']}")
    print(f"Durable goods orders: {snapshot['durable_goods_orders']['latest_direction']}")


def _print_consumer_section(snapshot: dict) -> None:
    print("CONSUMER")
    print(f"Retail sales: {snapshot['retail_sales']['momentum']}")
    print(f"Real consumption: {snapshot['real_consumption']['momentum']}")
    print(f"Real disposable income: {snapshot['real_disposable_income']['momentum']}")
    print(f"Saving rate: {snapshot['saving_rate']['direction']}")


def _print_housing_section(snapshot: dict) -> None:
    print("HOUSING")
    print(f"Housing starts: {snapshot['housing_starts']['direction']}")
    print(f"Building permits: {snapshot['building_permits']['direction']}")
    print(f"New home sales: {snapshot['new_home_sales']['direction']}")
    print(f"30Y mortgage rate: {snapshot['mortgage_rate']['direction']}")


def _print_financial_conditions_section(snapshot: dict) -> None:
    print("FINANCIAL CONDITIONS")
    print(f"Effective Fed Funds Rate: {snapshot['fed_funds_rate']['level']}")
    print(
        "2s10s Treasury Spread: "
        f"{snapshot['yield_curve_2s10s']['spread']} "
        f"({snapshot['yield_curve_2s10s']['shape']})"
    )
    print(
        "NFCI: "
        f"{snapshot['nfci']['position']}, "
        f"{snapshot['nfci']['direction']}"
    )


def main() -> int:
    if len(sys.argv) not in (1, 2):
        print(
            "Usage: python -m app.analytics.usa_economy_now [AS_OF_DATE]",
            file=sys.stderr,
        )
        return 1

    requested_as_of_date = None
    try:
        requested_as_of_date = (
            _parse_as_of_date(sys.argv[1]) if len(sys.argv) == 2 else None
        )
    except Exception as error:
        print(f"USA Economy Now failed: {error}", file=sys.stderr)
        return 1

    try:
        snapshot = build_usa_economy_now(requested_as_of_date)
        print_usa_economy_now(snapshot)
        return 0
    except Exception as error:
        if requested_as_of_date is not None:
            print(
                f"USA Economy Now unavailable for {requested_as_of_date}:",
                file=sys.stderr,
            )
            print(
                "historical point-in-time features are not available for all "
                "required domains.",
                file=sys.stderr,
            )
            return 1

        print(f"USA Economy Now failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
