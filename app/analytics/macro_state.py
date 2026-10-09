"""Descriptive current macro state from existing USA Economy Now snapshots."""

from typing import Optional

from app.analytics import usa_economy_now

# component, feature, label, unit, existing classification
READINGS = {
    "labor": [
        ("payrolls", "monthly_change", "Payroll change", "thousands", "momentum"),
        ("unemployment", "level", "Unemployment rate", "percent", "momentum"),
        ("initial_claims", "moving_average_4w", "Initial claims, 4W average", "persons", "momentum"),
        ("continuing_claims", "moving_average_4w", "Continuing claims, 4W average", "persons", "momentum"),
        ("job_openings", "level", "Job openings", "thousands", "direction"),
        ("labor_force_participation", "level", "Participation rate", "percent", "direction"),
        ("average_hourly_earnings", "yoy", "Wage growth YoY", "percent", None),
    ],
    "inflation": [
        ("headline_cpi", "yoy", "Headline CPI YoY", "percent", "momentum"),
        ("core_cpi", "yoy", "Core CPI YoY", "percent", "momentum"),
        ("headline_pce", "yoy", "Headline PCE YoY", "percent", "momentum"),
        ("core_pce", "yoy", "Core PCE YoY", "percent", "momentum"),
        ("employment_cost_index", "yoy", "ECI YoY", "percent", None),
        ("average_hourly_earnings", "yoy", "Wage growth YoY", "percent", None),
    ],
    "growth": [
        ("real_gdp", "qoq_annualized", "Real GDP QoQ annualized", "percent", "momentum"),
        ("cfnai", "moving_average_3m", "CFNAI 3M average", "index", "position"),
        ("industrial_production", "yoy", "Industrial production YoY", "percent", "momentum"),
        ("capacity_utilization", "level", "Capacity utilization", "percent", "direction"),
        ("durable_goods_orders", "yoy", "Durable goods orders YoY", "percent", "latest_direction"),
    ],
    "consumer": [
        ("retail_sales", "yoy", "Retail sales YoY (nominal)", "percent", "momentum"),
        ("real_consumption", "yoy", "Real consumption YoY", "percent", "momentum"),
        ("real_disposable_income", "yoy", "Real disposable income YoY", "percent", "momentum"),
        ("saving_rate", "level", "Saving rate", "percent", "direction"),
    ],
    "housing": [
        ("housing_starts", "level", "Housing starts", "thousands SAAR", "direction"),
        ("building_permits", "level", "Building permits", "thousands SAAR", "direction"),
        ("new_home_sales", "level", "New home sales", "thousands SAAR", "direction"),
        ("mortgage_rate", "level", "30Y mortgage rate", "percent", "direction"),
    ],
    "financial_conditions": [
        ("fed_funds_rate", "level", "Effective Fed Funds Rate", "percent", None),
        ("treasury_2y", "level", "2Y Treasury yield", "percent", None),
        ("treasury_10y", "level", "10Y Treasury yield", "percent", None),
        ("real_yield_10y", "level", "10Y real yield", "percent", None),
        ("yield_curve_2s10s", "spread", "2s10s spread", "percentage points", "shape"),
        ("nfci", "level", "NFCI", "index", "position"),
    ],
}

EVIDENCE_FIELDS = {
    "labor": [("overall_momentum", "Labor overall momentum"),
              ("payrolls.momentum", "Payroll momentum"),
              ("initial_claims.momentum", "Initial claims momentum"),
              ("continuing_claims.momentum", "Continuing claims momentum")],
    "inflation": [("headline_cpi.momentum", "Headline CPI momentum"),
                  ("core_cpi.momentum", "Core CPI momentum"),
                  ("headline_pce.momentum", "Headline PCE momentum"),
                  ("core_pce.momentum", "Core PCE momentum")],
    "growth": [("real_gdp.momentum", "Real GDP momentum"),
               ("cfnai.position", "CFNAI"),
               ("industrial_production.momentum", "Industrial production momentum"),
               ("capacity_utilization.direction", "Capacity utilization")],
    "consumer": [("retail_sales.momentum", "Nominal retail sales momentum"),
                 ("real_consumption.momentum", "Real consumption momentum"),
                 ("real_disposable_income.momentum", "Real disposable income momentum"),
                 ("saving_rate.direction", "Saving rate")],
    "housing": [("housing_starts.direction", "Housing starts"),
                ("building_permits.direction", "Building permits"),
                ("new_home_sales.direction", "New home sales"),
                ("mortgage_rate.direction", "30Y mortgage rate")],
    "financial_conditions": [("yield_curve_2s10s.shape", "2s10s curve shape"),
                             ("nfci.position", "NFCI position"),
                             ("nfci.direction", "NFCI direction")],
}

# Only explicitly opposite existing classifications trigger a cross-current.
CROSS_CURRENT_RULES = [
    ("labor", "Labor indicators are sending mixed directional signals.",
     (("overall_momentum", "improving", "Labor overall momentum"),
      ("payrolls.momentum", "weakening", "Payroll momentum"))),
    ("growth", "Growth indicators are sending mixed directional signals.",
     (("real_gdp.momentum", "decelerating", "Real GDP momentum"),
      ("industrial_production.momentum", "accelerating", "Industrial production momentum"))),
    ("housing", "Housing indicators are sending mixed directional signals.",
     (("housing_starts.direction", "falling", "Housing starts"),
      ("building_permits.direction", "rising", "Building permits"))),
]


def _field(snapshot: dict, path: str):
    value = snapshot
    for part in path.split("."):
        value = value[part]
    return value


def build_macro_state(snapshot: Optional[dict] = None) -> dict:
    """Project current snapshots without recomputing features or classifications."""
    if snapshot is None:
        snapshot = usa_economy_now.build_usa_economy_now()
    domains = {}
    for domain, specs in READINGS.items():
        source = snapshot[domain]
        readings = []
        classifications = {"overall_momentum": source["overall_momentum"]} if domain == "labor" else {}
        for component, field, label, unit, classification_field in specs:
            item = source[component]
            reading = {"key": component, "label": label, "value": item[field],
                       "unit": unit, "observation_date": item["observation_date"],
                       "feature_as_of_date": item["feature_as_of_date"]}
            if classification_field:
                classification = item[classification_field]
                reading["classification"] = classification
                classifications[f"{component}.{classification_field}"] = classification
            readings.append(reading)
        if domain == "financial_conditions":
            classifications["nfci.direction"] = source["nfci"]["direction"]
        evidence = []
        for path, label in EVIDENCE_FIELDS[domain]:
            verb = "are" if path in {
                "housing_starts.direction", "building_permits.direction", "new_home_sales.direction",
            } else "is"
            classification = _field(source, path)
            description = {
                "looser_than_average": "looser than its historical average",
                "tighter_than_average": "tighter than its historical average",
            }.get(classification, classification.replace("_", " "))
            evidence.append(f"{label} {verb} {description}.")
        domains[domain] = {"name": usa_economy_now.DOMAIN_LABELS[domain],
                           "as_of_date": source["as_of_date"], "readings": readings,
                           "classifications": classifications, "evidence": evidence}
    cross_currents = []
    for domain, summary, pair in CROSS_CURRENT_RULES:
        if all(_field(snapshot[domain], path) == expected for path, expected, _ in pair):
            cross_currents.append({
                "domain": domain, "summary": summary,
                "evidence": [{"label": label, "classification": expected}
                             for _, expected, label in pair],
            })
    return {"as_of_date": snapshot["as_of_date"],
            "component_as_of_dates": snapshot["component_as_of_dates"].copy(),
            "domains": domains, "cross_currents": cross_currents}
