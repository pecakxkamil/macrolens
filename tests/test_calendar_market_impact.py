"""The reviewed 29-kind K1 inventory is shared with frontend contract tests."""
import copy
import json
from collections import Counter
from pathlib import Path

import pytest
from fastapi.encoders import jsonable_encoder

from app.analytics.calendar_market_impact import (
    POLICY_VERSION, classify_event, classify_calendar, classify_brief,
)

CASES = json.loads((Path(__file__).resolve().parents[1] /
    "frontend/src/brief/__fixtures__/marketImpact.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["event"]["release_name"])
def test_all_reviewed_kinds(case):
    original = copy.deepcopy(case["event"])
    # Recompute from canonical identity, not fixture metadata/name/old importance.
    event = {k: v for k, v in original.items() if not k.startswith("market_impact_")}
    event.update(release_name="Renamed publisher label", importance="low")
    result = classify_event(event)
    assert result["market_impact_stars"] == case["expected"]
    assert result["importance"] == {1: "low", 2: "medium", 3: "high"}[case["expected"]]
    assert result["market_impact_policy_version"] == POLICY_VERSION
    assert result["market_impact_scope"] == "event"
    assert result["market_impact_rule_id"] == original["market_impact_rule_id"]
    assert case["event"] == original
    for day, actual, previous, source in (
        ("2026-09-01", None, None, None),
        ("2026-10-29", 3.4, 2.2, "bea_official"),
        ("2026-12-23", -9, 8, "fred"),
    ):
        variant = {**event, "release_date": day, "measures": [
            {"actual": actual, "previous": previous, "source": source, "forecast": None}]}
        assessed = classify_event(variant)
        assert assessed["market_impact_stars"] == case["expected"]
        assert assessed["measures"] == variant["measures"]


def test_exact_six_changes_and_inventory_counts():
    # Independently reviewed acceptance contract, not generated from the policy
    # or JSON. A coordinated mistake in fixture + implementation must fail too.
    assert POLICY_VERSION == "2026-11-k2-v1"
    approved = {
        "release:9": 3, "release:10": 3, "release:11": 2,
        "release:13": 2, "release:18": 1, "release:27": 2,
        "release:46": 3, "release:50": 3, "release:53": 3,
        "release:54": 3, "release:95": 2, "release:97": 3,
        "release:180": 3, "release:190": 2, "release:192": 3,
        "release:219": 2, "release:221": 2,
        "fomc_decision": 3, "fomc_press_conference": 3, "fomc_sep": 3,
        "fomc_minutes": 3, "ism_manufacturing": 3, "ism_services": 3,
        "michigan_preliminary": 3, "michigan_final": 2, "adp_monthly": 3,
        "empire_state": 2, "ft900": 2, "release:13:annual_revision": 2,
    }
    assessed = [classify_event(c["event"]) for c in CASES]
    assert {e["market_impact_rule_id"]: e["market_impact_stars"] for e in assessed} == approved
    assert len({e["market_impact_rule_id"] for e in assessed}) == 29
    assert len(CASES) == 29
    assert Counter(c["before"] for c in CASES) == {3: 11, 2: 17, 1: 1}
    assert Counter(c["expected"] for c in CASES) == {3: 17, 2: 11, 1: 1}
    changed = [c for c in CASES if c["before"] != c["expected"]]
    assert {c["event"]["release_id"] for c in changed} == {9, 192, 180, 46, 97, None}
    assert [c["event"].get("event_type") for c in changed if c["event"]["release_id"] is None] == ["fomc_minutes"]


@pytest.mark.parametrize("event", [
    {"release_id": 999, "release_name": "Consumer Price Index", "importance": "high"},
    {"release_id": 10, "event_type": "unsupported", "importance": "medium"},
    {"release_id": None, "event_type": "ism_report", "series": []},
    {"release_id": None, "event_type": "ism_report", "series": [
        {"series_id": "ISM_MANUFACTURING_PMI"}, {"series_id": "ISM_SERVICES_PMI"}]},
])
def test_unknown_is_explicit_and_never_borrows_name_or_other_identity(event):
    result = classify_event(event)
    assert result["market_impact_stars"] is None
    assert result["market_impact_rule_id"] is None
    assert result.get("importance") == event.get("importance")


@pytest.mark.parametrize("stage", ["advance", "second", "third", "updated"])
def test_gdp_stages_dates_and_values_do_not_change_policy(stage):
    for day in ("2026-09-30", "2026-10-29", "2026-11-25", "2026-12-23"):
        for actual, previous, source in ((None, 2.2, None), (3.4, 2.2, "bea_official"), (-9, 8, "fred")):
            event = {"release_id": 53, "estimate_stage": stage, "release_date": day,
                     "event_id": "preserved", "measures": [{"actual": actual, "previous": previous,
                     "forecast": None, "source": source}]}
            result = classify_event(event)
            assert result["market_impact_stars"] == 3
            assert result["measures"] == event["measures"]
            assert result["event_id"] == "preserved"
            assert result["release_date"] == day


def test_current_policy_projects_cached_brief_without_mutation_or_new_generation():
    events = [{"release_id": 9, "importance": "medium", "event_id": "retail:old"},
              {"event_type": "fomc_minutes", "importance": "medium"}]
    original = {"calendar": {"status": "ready", "data": {"events": events}},
                "policy": {"status": "ready", "data": {"next_decision": {"event_type": "fomc_decision"}}},
                "data_revision": "old-generation", "assembled_at": "old-time", "refresh": {"next_check_at": "unchanged"}}
    before = copy.deepcopy(original)
    result = classify_brief(original)
    assert original == before
    assert result["data_revision"] == original["data_revision"]
    assert result["assembled_at"] == original["assembled_at"]
    assert result["refresh"] == original["refresh"]
    assert all(e["market_impact_stars"] == 3 for e in result["calendar"]["data"]["events"])
    assert result["policy"]["data"]["next_decision"]["market_impact_stars"] == 3
    wire = json.loads(json.dumps(jsonable_encoder(classify_calendar({"events": events}))))
    assert wire["events"][0]["market_impact_policy_version"] == POLICY_VERSION
    assert wire["events"][1]["importance"] == "high"


def test_real_calendar_endpoint_classifies_all_six_without_readings_or_writes(monkeypatch):
    from datetime import date
    from fastapi.testclient import TestClient
    from app.api.main import app
    from app.analytics import release_calendar, ism_calendar, michigan_calendar, adp_calendar
    from tests.test_release_calendar import FakeConnection

    day = date(2026, 10, 20)
    rows = [(day, rid, "Renamed release {}".format(rid), None,
             "SERIES{}".format(rid), "Series", "Series", "labor", "monthly", "index")
            for rid in (9, 46, 97, 180, 192)]
    connection = FakeConnection([rows])
    monkeypatch.setattr(release_calendar, "get_connection", lambda: connection)
    monkeypatch.setattr(release_calendar, "load_series_config", lambda: {
        "SERIES{}".format(rid): {"category": "labor"} for rid in (9, 46, 97, 180, 192)})
    monkeypatch.setattr(release_calendar, "read_schedule", lambda: {
        "events": [{"release_id": None, "event_type": "fomc_minutes", "event_id": "minutes:test",
                    "release_name": "FOMC Meeting Minutes", "release_date": str(day),
                    "importance": "medium", "series": []}],
        "status": "available", "retrieved_at": None, "source_url": "test"})
    for module in (ism_calendar, michigan_calendar, adp_calendar):
        monkeypatch.setattr(module, "read_schedule", lambda: {"events": [], "check": {}})
    response = TestClient(app).get("/api/v1/calendar?start_date=2026-10-20&end_date=2026-10-20")
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == 6
    assert all(e["market_impact_stars"] == 3 and e["importance"] == "high" for e in events)
    assert all(e["market_impact_policy_version"] == POLICY_VERSION for e in events)
    assert len(connection.cursor_instance.calls) == 1
