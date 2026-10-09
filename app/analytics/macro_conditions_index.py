"""Transparent monthly Macro Conditions Index v1 over stored feature histories."""

import calendar
import math
from bisect import bisect_left, bisect_right, insort
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.analytics import history

METHODOLOGY_VERSION = "v1"
HISTORY_TYPE = "current_vintage"
DOMAIN_NAMES = {
    "labor": "Labor Conditions Index",
    "inflation": "Inflation Stability Index",
    "growth": "Growth Conditions Index",
    "consumer": "Consumer Conditions Index",
    "housing": "Housing Conditions Index",
    "financial_conditions": "Financial Conditions Index",
}
DOMAIN_WEIGHT = 1 / 6
MIN_MONTHLY_SAMPLES = 60
MIN_QUARTERLY_SAMPLES = 20
INFLATION_REFERENCE = 2.0
INFLATION_ZERO_DISTANCE = 4.0


@dataclass(frozen=True)
class Component:
    key: str
    domain: str
    label: str
    series_id: str
    features: tuple
    unit: str
    orientation: str
    rationale: str
    quarterly: bool = False


COMPONENTS = (
    Component("payroll_momentum", "labor", "Payroll momentum gap", "PAYEMS",
              ("monthly_change_ma_3m", "monthly_change_ma_6m"), "thousands of persons",
              "higher", "A larger 3M minus 6M payroll-change average denotes improving payroll momentum."),
    Component("unemployment_change", "labor", "Unemployment 3M change", "UNRATE",
              ("change_3m",), "percentage points", "lower",
              "A lower 3M unemployment-rate change denotes improving labor momentum."),
    Component("claims_momentum", "labor", "Initial claims momentum gap", "ICSA",
              ("moving_average_4w", "moving_average_13w"), "persons", "lower",
              "A lower 4W minus 13W claims average denotes improving claims momentum."),
    Component("headline_cpi", "inflation", "Headline CPI YoY", "CPIAUCSL", ("yoy",),
              "percent", "target_distance", "Symmetric distance from the analytical 2% inflation reference."),
    Component("core_cpi", "inflation", "Core CPI YoY", "CPILFESL", ("yoy",),
              "percent", "target_distance", "Symmetric distance from the analytical 2% inflation reference."),
    Component("core_pce", "inflation", "Core PCE YoY", "PCEPILFE", ("yoy",),
              "percent", "target_distance", "Symmetric distance from the analytical 2% inflation reference."),
    Component("real_gdp", "growth", "Real GDP QoQ annualized", "GDPC1", ("qoq_annualized",),
              "percent", "higher", "Higher real GDP growth describes greater aggregate output growth.", True),
    Component("cfnai", "growth", "CFNAI 3M average", "CFNAI", ("moving_average_3m",),
              "index points", "higher", "Higher CFNAI describes activity further above its trend reference."),
    Component("industrial_production", "growth", "Industrial production 3M annualized", "INDPRO",
              ("annualized_3m",), "percent", "higher", "Higher real industrial growth describes greater output growth."),
    Component("real_consumption", "consumer", "Real consumption 3M annualized", "PCEC96",
              ("annualized_3m",), "percent", "higher", "Higher inflation-adjusted consumption growth describes greater real spending growth."),
    Component("real_income", "consumer", "Real disposable income 3M annualized", "DSPIC96",
              ("annualized_3m",), "percent", "higher", "Higher real disposable income growth describes greater real income growth."),
    Component("housing_starts", "housing", "Housing starts YoY", "HOUST", ("yoy",),
              "percent", "higher", "Higher starts growth describes expanding construction activity, not affordability."),
    Component("building_permits", "housing", "Building permits YoY", "PERMIT", ("yoy",),
              "percent", "higher", "Higher permits growth describes expanding permitted activity, not affordability."),
    Component("new_home_sales", "housing", "New home sales YoY", "HSN1F", ("yoy",),
              "percent", "higher", "Higher sales growth describes expanding new-home sales activity, not affordability."),
    Component("nfci", "financial_conditions", "NFCI level", "NFCI", ("level",),
              "index points", "lower", "Lower NFCI describes looser financial conditions relative to history, not economic welfare."),
)


def inflation_score(value: float) -> float:
    """100 at 2%; 50 at a 2pp deviation; zero at deviations of at least 4pp."""
    return max(0.0, min(100.0, 100 * (1 - abs(value - INFLATION_REFERENCE) / INFLATION_ZERO_DISTANCE)))


def percentile_score(value: float, sorted_sample: list, orientation: str) -> float:
    """Expanding midrank percentile, including the current observation."""
    if not sorted_sample or orientation not in ("higher", "lower"):
        raise ValueError("A nonempty reference sample and explicit orientation are required.")
    less = bisect_left(sorted_sample, value)
    equal = bisect_right(sorted_sample, value) - less
    score = 100 * (less + equal / 2) / len(sorted_sample)
    return score if orientation == "higher" else 100 - score


def _date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _month(value: date) -> date:
    return value.replace(day=1)


def _shift_month(value: date, months: int) -> date:
    number = value.year * 12 + value.month - 1 + months
    return date(number // 12, number % 12 + 1, 1)


def _month_end(value: date) -> date:
    return value.replace(day=calendar.monthrange(value.year, value.month)[1])


def _finite(value):
    if value is None:
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def methodology_metadata() -> dict:
    return {
        "methodology_version": METHODOLOGY_VERSION,
        "history_type": HISTORY_TYPE,
        "frequency": "monthly",
        "domain_weights": {key: DOMAIN_WEIGHT for key in DOMAIN_NAMES},
        "normalization": {
            "method": "expanding_midrank_percentile",
            "formula": "100 * (count(x < current) + 0.5 * count(x = current)) / N",
            "lower_orientation": "100 - percentile",
            "reference": "Distinct monthly component observations through the scored month, including current; GDP uses distinct quarterly observations.",
            "minimum_monthly_samples": MIN_MONTHLY_SAMPLES,
            "minimum_quarterly_samples": MIN_QUARTERLY_SAMPLES,
            "inflation_formula": "max(0, 100 * (1 - abs(inflation_yoy - 2) / 4))",
            "inflation_reference_percent": INFLATION_REFERENCE,
            "inflation_zero_distance_pp": INFLATION_ZERO_DISTANCE,
        },
        "alignment": {
            "monthly_weekly": "Latest same-date finite component inputs within each completed calendar month; no carry-forward.",
            "gdp": "Quarter-start observation becomes eligible in the month after that quarter ends; carry its raw value and score for at most two additional months.",
            "calendar": "Month-end rows, completed months only. Source observation periods are used, not reconstructed publication dates.",
        },
        "missing_data": "Require every configured component per domain and all six domains for MCI. Null scores retain fixed weights; no neutral imputation or reweighting.",
        "current_selection": "Latest complete MCI month, or latest evaluated month with null MCI if no complete month exists.",
        "limitation": "Current-vintage values include revisions and may differ from real-time calculations. Publication availability is not reconstructed; this is not an investable or backtest signal.",
    }


def _events(component: Component, histories: dict, cutoff: date) -> dict:
    inputs = []
    for feature in component.features:
        response = histories[(component.series_id, feature)]
        # Existing loaders guarantee unique dates. Prefer latest feature vintage if
        # supplied test/history rows contain duplicates.
        dated = {}
        for row in sorted(response["observations"], key=lambda item: (
            str(item["observation_date"]), str(item.get("feature_as_of_date", "")),
        )):
            observed = _date(row["observation_date"])
            if observed <= cutoff:
                dated[observed] = row
        inputs.append(dated)
    matched_dates = set(inputs[0])
    for values in inputs[1:]:
        matched_dates &= set(values)

    events = {}
    for observed in sorted(matched_dates):
        rows = [values[observed] for values in inputs]
        values = [_finite(row["value"]) for row in rows]
        if any(value is None for value in values):
            continue
        raw_value = values[0] if len(values) == 1 else values[0] - values[1]
        if not math.isfinite(raw_value):
            continue
        effective_month = _month(observed)
        if component.quarterly:
            effective_month = _shift_month(date(observed.year, ((observed.month - 1) // 3) * 3 + 1, 1), 3)
        if _month_end(effective_month) > cutoff:
            continue
        events[effective_month] = {
            "raw_value": raw_value,
            "source_observation_date": str(observed),
            "effective_month": str(effective_month),
            "feature_as_of_date": max(str(row.get("feature_as_of_date", observed)) for row in rows),
            "inputs": [{"feature_name": feature, "value": value}
                       for feature, value in zip(component.features, values)],
        }
    return events


def _score_events(component: Component, events: dict) -> dict:
    sample = []
    scored = {}
    first_date = None
    minimum = MIN_QUARTERLY_SAMPLES if component.quarterly else MIN_MONTHLY_SAMPLES
    for month, event in sorted(events.items()):
        value = event["raw_value"]
        insort(sample, value)
        first_date = first_date or month
        target = component.orientation == "target_distance"
        score = inflation_score(value) if target else (
            percentile_score(value, sample, component.orientation) if len(sample) >= minimum else None
        )
        scored[month] = {
            **event, "score": score, "status": "available" if score is not None else "insufficient_history",
            "reference_sample_size": 0 if target else len(sample),
            "reference_start_date": None if target else str(first_date),
            "reference_end_date": None if target else str(month),
        }
    return scored


def _component_reading(component: Component, scored: dict, month: date, weight: float) -> dict:
    event = scored.get(month)
    carried = False
    if event is None and component.quarterly:
        for age in (1, 2):
            event = scored.get(_shift_month(month, -age))
            if event is not None:
                carried = True
                break
    score = event["score"] if event else None
    return {
        "key": component.key, "label": component.label, "series_id": component.series_id,
        "features": list(component.features), "unit": component.unit,
        "orientation": component.orientation, "rationale": component.rationale,
        "weight": weight, "overall_weight": weight * DOMAIN_WEIGHT,
        "score": score, "raw_value": event["raw_value"] if event else None,
        "domain_contribution": score * weight if score is not None else None,
        "mci_contribution": score * weight * DOMAIN_WEIGHT if score is not None else None,
        "status": event["status"] if event else "missing",
        "source_observation_date": event["source_observation_date"] if event else None,
        "effective_month": event["effective_month"] if event else None,
        "feature_as_of_date": event["feature_as_of_date"] if event else None,
        "inputs": event["inputs"] if event else [],
        "carried_forward": carried,
        "reference_sample_size": event["reference_sample_size"] if event else 0,
        "reference_start_date": event["reference_start_date"] if event else None,
        "reference_end_date": event["reference_end_date"] if event else None,
    }


def build_monthly_index(histories: dict, as_of_date: date) -> list:
    """Pure calculation over stored features; no feature recomputation or writes."""
    scored = {component.key: _score_events(component, _events(component, histories, as_of_date))
              for component in COMPONENTS}
    starts = [month for events in scored.values() for month in events]
    if not starts:
        return []
    month = min(starts)
    rows = []
    while _month_end(month) <= as_of_date:
        domains = {}
        for domain, name in DOMAIN_NAMES.items():
            definitions = [component for component in COMPONENTS if component.domain == domain]
            readings = [_component_reading(component, scored[component.key], month, 1 / len(definitions))
                        for component in definitions]
            score = sum(item["domain_contribution"] for item in readings) if all(
                item["score"] is not None for item in readings
            ) else None
            dates = [item["feature_as_of_date"] for item in readings if item["feature_as_of_date"]]
            domains[domain] = {
                "name": name, "score": score, "weight": DOMAIN_WEIGHT,
                "contribution": score * DOMAIN_WEIGHT if score is not None else None,
                "as_of_date": max(dates) if dates else None, "components": readings,
            }
        mci = sum(item["contribution"] for item in domains.values()) if all(
            item["score"] is not None for item in domains.values()
        ) else None
        rows.append({"observation_date": str(_month_end(month)), "mci": mci, "domains": domains})
        month = _shift_month(month, 1)
    return rows


def _load_histories(cutoff: date) -> dict:
    # Always load the full reference history before filtering the response range.
    requests = dict.fromkeys((component.series_id, feature)
                             for component in COMPONENTS for feature in component.features)
    return {key: history.load_feature_history(*key, end_date=cutoff) for key in requests}


def get_current_index() -> dict:
    cutoff = date.today()
    rows = build_monthly_index(_load_histories(cutoff), cutoff)
    complete = [row for row in rows if row["mci"] is not None]
    if rows:
        current = complete[-1] if complete else rows[-1]
    else:
        empty = {component.key: {} for component in COMPONENTS}
        domains = {}
        for domain, name in DOMAIN_NAMES.items():
            definitions = [component for component in COMPONENTS if component.domain == domain]
            domains[domain] = {
                "name": name, "score": None, "weight": DOMAIN_WEIGHT, "contribution": None,
                "as_of_date": None, "components": [
                    _component_reading(component, empty[component.key], _month(cutoff), 1 / len(definitions))
                    for component in definitions
                ],
            }
        current = {"observation_date": None, "mci": None, "domains": domains}
    return {
        **methodology_metadata(), **current, "as_of_date": str(cutoff),
        "latest_evaluated_month": rows[-1]["observation_date"] if rows else None,
        "component_as_of_dates": {key: item["as_of_date"] for key, item in current["domains"].items()},
    }


def get_index_history(start_date: Optional[date] = None, end_date: Optional[date] = None) -> dict:
    history._validate_date_range(start_date, end_date)
    cutoff = min(date.today(), end_date) if end_date else date.today()
    rows = build_monthly_index(_load_histories(cutoff), cutoff)
    observations = [
        {"observation_date": row["observation_date"], "mci": row["mci"],
         **{key: item["score"] for key, item in row["domains"].items()}}
        for row in rows
        if (start_date is None or _date(row["observation_date"]) >= start_date)
        and (end_date is None or _date(row["observation_date"]) <= end_date)
    ]
    return {
        **methodology_metadata(), "as_of_date": str(cutoff),
        "start_date": str(start_date) if start_date else None,
        "end_date": str(end_date) if end_date else None,
        "observations": observations,
    }
