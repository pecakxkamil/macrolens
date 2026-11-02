"""Current MacroLens editorial policy, applied on read to every publication date.

Ratings describe whole reports, not individual measures or realized price moves.
Overview selection is deliberately outside this policy. No storage or I/O here.
"""

POLICY_VERSION = "2026-11-k2-v1"

# Canonical FRED release IDs; names and translated labels are not identifiers.
RELEASE_STARS = {
    9: 3, 10: 3, 11: 2, 13: 2, 18: 1, 27: 2, 46: 3, 50: 3,
    53: 3, 54: 3, 95: 2, 97: 3, 180: 3, 190: 2, 192: 3, 219: 2, 221: 2,
}
EVENT_STARS = {
    "fomc_decision": 3, "fomc_press_conference": 3, "fomc_sep": 3,
    "fomc_minutes": 3, "michigan_preliminary": 3, "michigan_final": 2,
    "adp_monthly": 3, "empire_state": 2, "ft900": 2,
}
ISM_RULES = {
    "ISM_MANUFACTURING_PMI": "ism_manufacturing",
    "ISM_SERVICES_PMI": "ism_services",
}


def classify_event(event):
    """Return additive metadata and a compatible importance for known IDs.

    An unrecognized dedicated type cannot borrow a FRED rule. Unknown keeps
    its legacy importance, but explicitly has no market-impact star rating.
    """
    kind = event.get("event_type")
    rule = None
    stars = None
    if kind == "ism_report":
        series = {item.get("series_id") for item in event.get("series", [])}
        matches = series.intersection(ISM_RULES)
        if len(matches) == 1:
            rule = ISM_RULES[next(iter(matches))]
            stars = 3
    elif kind:
        stars = EVENT_STARS.get(kind)
        if stars is not None:
            rule = kind
    else:
        release = event.get("release_id")
        stars = RELEASE_STARS.get(release)
        if stars is not None:
            rule = "release:{}".format(release)
            if release == 13 and event.get("estimate_stage") == "annual_revision":
                rule += ":annual_revision"
    metadata = {
        "market_impact_stars": stars,
        "market_impact_policy_version": POLICY_VERSION,
        "market_impact_rule_id": rule,
        "market_impact_scope": "event",
    }
    if stars is not None:
        metadata["importance"] = {3: "high", 2: "medium", 1: "low"}[stars]
    return {**event, **metadata}


def classify_calendar(payload):
    return {**payload, "events": [classify_event(event) for event in payload["events"]]}


def classify_brief(payload):
    """Project current policy over cached brief responses without changing cache.

    Only event metadata changes: generations, timestamps, data and refresh
    deadlines remain those of the original response.
    """
    result = {**payload}
    for section_name in ("calendar", "policy"):
        section = payload.get(section_name)
        if not section or not section.get("data"):
            continue
        data = section["data"]
        if section_name == "calendar":
            data = classify_calendar(data)
        elif data.get("next_decision"):
            data = {**data, "next_decision": classify_event(data["next_decision"])}
        result[section_name] = {**section, "data": data}
    return result
