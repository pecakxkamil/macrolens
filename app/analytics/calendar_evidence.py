"""Persisted publisher evidence, separate from observation vintages and schedules."""
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / 'data/derived/calendar_periods_v1.json'
REVIEWED = ROOT / 'config/calendar_period_evidence.json'

# Existing numeric release families only. FOMC and ISM retain their adapters.
PUBLISHER_GROUPS = {9,13,27,53,54,95,97,219,221}
PUBLISHER_PRIORITY = {'official_release':4, 'official_schedule':3,
                      'reviewed_official_schedule':2, 'official_g17_monthly_rule':2}


def schedule_records(evidence):
    from app.ingestion.bls_schedule import select_records, publisher_identity, PRIORITY
    rows = evidence.get('periods', [])
    bls, conflicts = select_records([r for r in rows if r.get('binding_method') in
        set(PRIORITY) | {'official_schedule','reviewed_official_schedule','official_release'}])
    publisher, additional = select_records(
        [r for r in rows if r.get('binding_method') in PUBLISHER_PRIORITY],
        PUBLISHER_GROUPS, PUBLISHER_PRIORITY, publisher_identity)
    return bls + publisher, conflicts + additional


def read_evidence(path=None):
    result = {'periods': [], 'decisions': [], 'checks': [], 'rules': [], 'results': [],
              'bls_sources': [], 'bls_history': [], 'bls_conflicts': [], 'publisher_history': []}
    for source in ([Path(path)] if path else [REVIEWED, SNAPSHOT]):
        try:
            payload = json.loads(source.read_text(encoding='utf-8'))
            if payload['version'] != 1:
                continue
            for key in result:
                result[key].extend(payload.get(key, []))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    from app.analytics.retail_measures import expand_retail_evidence
    return expand_retail_evidence(result)


def period_evidence(evidence, release_id, day, sid):
    candidates=evidence.get('periods', [])
    from app.ingestion.bls_schedule import GROUPS
    if release_id in {g[0] for g in GROUPS.values()}:
        candidates,_=schedule_records(evidence)
    elif release_id in PUBLISHER_GROUPS:
        candidates,_=schedule_records(evidence)
    rows = [r for r in candidates if r['release_id'] == release_id
            and r['release_date'] == day and sid in r['series_ids']]
    # Conflicting schedules are not resolved by choosing the latest period.
    periods = {r['reference_period'] for r in rows}
    if rows:
        return max(rows, key=lambda r: r['retrieved_at']) if len(periods) == 1 else None
    if release_id == 180 and sid in ('ICSA','CCSA'):
        rule = claims_rule(evidence, day)
        if rule:
            released = date.fromisoformat(day)
            initial = released-timedelta(days=(released.weekday()-5)%7)
            period = initial-timedelta(days=7 if sid=='CCSA' else 0)
            override=rule.get('period_overrides',{}).get(day,{}).get(sid)
            if override:period=date.fromisoformat(override)
            return dict(release_id=180,release_date=day,series_ids=[sid],reference_period=str(period),
                binding_method='official_claims_week_rule',source_url=rule['methodology_url'],
                schedule_source_url=rule['source_url'],retrieved_at=rule['retrieved_at'],rule_id=rule['id'])
    return None


def claims_rule(evidence, day):
    released=date.fromisoformat(str(day))
    for rule in sorted(evidence.get('rules',[]),key=lambda r:r.get('schedule_retrieved_at') or r.get('retrieved_at',''),reverse=True):
        if rule.get('id')!='dol_weekly_claims' or not rule['valid_from']<=str(day)<=rule['valid_through']:
            continue
        # Explicit holiday substitutions also cancel their regular Thursday.
        exceptions=rule.get('exceptions',{})
        if str(day) in exceptions and (released.weekday() in (2,3) or str(day) in rule.get('period_overrides',{})):
            return rule
        if str(day) in rule.get('cancelled_dates',[]):
            return None
        if released.weekday()==3:
            return rule
        # The newest applicable schedule supersedes older overlapping copies,
        # including their exceptions and cancellations.
        return None
    return None
