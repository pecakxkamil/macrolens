"""Read-only brief aggregation; existing snapshots and classifications are unchanged."""
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from app.analytics import macro_state, usa_economy_now, release_calendar
from app.analytics.fomc_calendar import policy_outlook
from app.analytics.features import METHODOLOGY_VERSION
from app.analytics.relationships import _finite_value
from app.analytics.overview_readings import load_reading_comparisons
from app.analytics.fed_target import load_fed_target
from app.analytics.source_checks import load_source_checks

logger = logging.getLogger(__name__)
# Explicit editorial selection, not a significance ranking.
COMPARISONS = (
    ("UNRATE", "level", "Unemployment rate", "monthly", "percent", "percentage points"),
    ("CPIAUCSL", "yoy", "Headline CPI YoY", "monthly", "percent", "percentage points"),
    ("GDPC1", "qoq_annualized", "Real GDP QoQ annualized", "quarterly", "percent", "percentage points"),
    ("PCEC96", "yoy", "Real consumption YoY", "monthly", "percent", "percentage points"),
    ("HOUST", "level", "Housing starts", "monthly", "thousands SAAR", "thousands SAAR"),
    ("NFCI", "level", "NFCI", "weekly", "index", "index points"),
)


def previous_period(observed: date, frequency: str) -> date:
    if frequency == "weekly":
        return observed - timedelta(days=7)
    months = 3 if frequency == "quarterly" else 1
    ordinal = observed.year * 12 + observed.month - 1 - months
    return date(ordinal // 12, ordinal % 12 + 1, 1)


def compare_readings(rows: list) -> list:
    """Compare the latest finite stored feature with the exact preceding period."""
    result = []
    for series, feature, label, frequency, unit, change_unit in COMPARISONS:
        available = {str(day): {"value": _finite_value(value), "feature_as_of_date": str(as_of)}
                     for sid, fname, day, as_of, value in rows if sid == series and fname == feature}
        latest = max((day for day, row in available.items() if row["value"] is not None), default=None)
        expected = str(previous_period(date.fromisoformat(latest), frequency)) if latest else None
        current = {"observation_date": latest, **available[latest]} if latest else None
        previous = ({"observation_date": expected, **available[expected]}
                    if expected in available and available[expected]["value"] is not None else None)
        result.append({"series_id": series, "feature_name": feature, "label": label,
            "frequency": frequency, "unit": unit, "change_unit": change_unit,
            "change_type": "Difference from previous calendar quarter" if frequency == "quarterly" else
                           "Difference from previous calendar week" if frequency == "weekly" else "Difference from previous calendar month",
            "current": current, "previous": previous, "expected_previous_observation_date": expected,
            "latest_stored_observation_date": max(available, default=None),
            "change": current["value"] - previous["value"] if current and previous else None})
    return result


def legacy_comparisons(readings):
    by_measure = {(row["series_id"], row["feature_name"]): row for row in readings}
    for row in readings:
        context = row.get("context_yoy")
        if context is not None:
            current, previous = context["current"], context["previous"]
            by_measure[(row["series_id"], "yoy")] = {**row, **context, "feature_name": "yoy", "context_yoy": None,
                "change": current["value"] - previous["value"] if current and previous else None}
    return [{**by_measure[(series, feature)], "label": label}
            for series, feature, label, *_ in COMPARISONS if (series, feature) in by_measure]


def load_comparisons(today: date) -> list:
    """Retain the existing six-comparison helper using the bounded shared query."""
    return legacy_comparisons(load_reading_comparisons(today))


def classification_basis(snapshot: dict) -> dict:
    """Explain existing classifications using their actual snapshot inputs.

    This projects values and rule descriptions; it never computes a new label.
    Covers every classification in brief readings, evidence and cross-currents.
    """
    result = {key: [] for key in macro_state.EVIDENCE_FIELDS}

    def add(domain, component, field, label, inputs, rule, short):
        item = snapshot[domain][component] if component else snapshot[domain]
        result[domain].append({"component": component or "overall", "field": field,
            "label": label, "classification": item[field], "rule": rule, "short": short,
            "observation_date": item.get("observation_date"),
            "feature_as_of_date": item.get("feature_as_of_date"),
            "inputs": [{"feature_name": key, "label": title, "value": item[key], "unit": unit}
                       for key, title, unit in inputs]})

    add("labor", None, "overall_momentum", "Overall labor momentum", [],
        "At least two of payroll, unemployment and initial-claims momentum improving means improving; at least two weakening means weakening; otherwise mixed.",
        "Existing balance of payrolls, unemployment and initial claims")
    result["labor"][-1]["component_classifications"] = {
        key: snapshot["labor"][key]["momentum"] for key in ("payrolls", "unemployment", "initial_claims")}
    add("labor", "payrolls", "momentum", "Payroll momentum",
        [("monthly_change_ma_3m", "3-month average payroll gain", "thousands"), ("monthly_change_ma_6m", "6-month average payroll gain", "thousands")],
        "3-month average monthly job gains above the 6-month average means improving, below means weakening, equal means stable. Not a comparison of two monthly payroll changes.",
        "Payroll momentum: 3-month versus 6-month average job gains")
    add("labor", "unemployment", "momentum", "Unemployment momentum", [("change_3m", "3-month change in unemployment rate", "percentage points")],
        "A negative 3-month change means improving, positive means weakening, zero means stable; not the latest month-to-month change.",
        "Unemployment momentum uses the 3-month rate change")
    for key, label in [("initial_claims", "Initial claims momentum"), ("continuing_claims", "Continuing claims momentum")]:
        add("labor", key, "momentum", label, [("moving_average_4w", "4-week average claims", "persons"), ("moving_average_13w", "13-week average claims", "persons")],
            "4-week average below the 13-week average means improving, above means weakening, equal means stable.", "Claims momentum: 4-week versus 13-week average")
    for domain, keys in [("inflation", ["headline_cpi", "core_cpi", "headline_pce", "core_pce"]), ("consumer", ["retail_sales", "real_consumption", "real_disposable_income"]), ("growth", ["industrial_production"])]:
        for key in keys:
            label = next(spec[2] for spec in macro_state.READINGS[domain] if spec[0] == key)
            add(domain, key, "momentum", label.replace(" YoY", "") + " momentum", [("annualized_3m", "3-month annualized pace", "percent"), ("yoy", "Year-over-year pace", "percent")],
                "At the same observation period, 3-month annualized pace above YoY means accelerating, below means decelerating, equal means stable. This does not compare successive YoY readings. Uses unrounded feature values.",
                "Momentum compares the recent 3-month pace with the annual pace")
    add("growth", "real_gdp", "momentum", "Real GDP momentum", [("qoq_annualized", "Quarterly growth, annualized", "percent"), ("yoy", "Year-over-year growth", "percent")],
        "For the same quarter, QoQ annualized above YoY means accelerating, below means decelerating, equal means stable. This does not compare successive quarterly annualized rates. Uses unrounded feature values.",
        "GDP momentum compares this quarter's annualized growth with its year-over-year growth")
    add("growth", "cfnai", "position", "CFNAI position", [("moving_average_3m", "3-month average CFNAI", "index")],
        "3-month average above zero means above trend, below zero means below trend, zero means at trend.", "Position uses the 3-month average relative to zero")
    for domain, key, field, feature, label, unit, short in [
        ("growth", "capacity_utilization", "direction", "change_3m", "Capacity utilization", "percentage points", "3-month change"),
        ("consumer", "saving_rate", "direction", "change_3m", "Saving rate", "percentage points", "3-month change"),
        ("housing", "housing_starts", "direction", "mom", "Housing starts", "percent", "month-to-month change"),
        ("housing", "building_permits", "direction", "mom", "Building permits", "percent", "month-to-month change"),
        ("housing", "new_home_sales", "direction", "mom", "New home sales", "percent", "month-to-month change"),
        ("housing", "mortgage_rate", "direction", "change_4w", "30Y mortgage rate", "percentage points", "4-week change")]:
        add(domain, key, field, label + " direction", [(feature, short.capitalize(), unit)],
            f"Positive {short} means rising, negative means falling, zero means stable. Direction does not assign good/bad meaning.", f"Direction uses the {short}")
    add("financial_conditions", "yield_curve_2s10s", "shape", "2s10s curve shape", [("spread", "10Y minus 2Y yield", "percentage points")],
        "Positive spread means positive, negative means inverted, zero means flat. No recession inference.", "Curve shape describes the sign of the yield spread")
    add("financial_conditions", "nfci", "position", "NFCI position", [("level", "NFCI level", "index")],
        "Below zero means looser than historical average, above zero means tighter than average, zero means average.", "Position describes the level relative to its historical average")
    add("financial_conditions", "nfci", "direction", "NFCI direction", [("change_4w", "4-week NFCI change", "index points")],
        "Positive 4-week change means tightening, negative means easing, zero means stable. Position and direction describe different measures.", "Direction uses the 4-week index change")
    return result

def _section(loader, name):
    try:
        return {"status": "ready", "data": loader(), "error": None}
    except Exception:
        logger.exception("Economy Brief section unavailable: %s", name)
        return {"status": "unavailable", "data": None, "error": f"{name} is unavailable."}


def build_brief(now=None):
    now = now or datetime.now(ZoneInfo("Europe/Warsaw"))
    today = now.astimezone(ZoneInfo("Europe/Warsaw")).date()
    snapshot = _section(usa_economy_now.build_usa_economy_now, "USA Economy Now")
    # Reuse the SAME snapshot. No second snapshot load and no new interpretation rules.
    state = (_section(lambda: macro_state.build_macro_state(snapshot["data"]), "Macro State")
             if snapshot["status"] == "ready" else
             {"status": "unavailable", "data": None, "error": "Macro State requires the unavailable current snapshot."})
    readings = _section(lambda: load_reading_comparisons(today), "Reading comparisons")
    changes = {**readings, "data": legacy_comparisons(readings["data"]) if readings["data"] is not None else None}
    calendar = _section(lambda: release_calendar.list_calendar_events(today, today + timedelta(days=6)), "Release calendar")
    return {"assembled_at": now.isoformat(), "timezone": "Europe/Warsaw", "history_type": "current_vintage",
        "snapshot": snapshot, "state": state, "changes": changes, "calendar": calendar,
        "reading_comparisons": readings,
        "source_checks": load_source_checks(today),
        "fed_target": _section(lambda: load_fed_target(today), "Fed target range"),
        "policy": _section(lambda: policy_outlook(now), "FOMC schedule"),
        "classification_basis": classification_basis(snapshot["data"]) if snapshot["data"] else {},
        "calendar_start_date": str(today), "calendar_end_date": str(today + timedelta(days=6))}
