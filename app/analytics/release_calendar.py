"""Read-only calendar queries for tracked MacroLens releases."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

from app.database.connection import get_connection
from app.database.sync_series import load_series_config
from app.analytics.release_times import release_time_metadata
from app.analytics.fomc_calendar import read_schedule


CALENDAR_SQL = """
SELECT d.release_date, r.release_id, r.name, r.source_link,
       s.series_id, s.name, s.short_name, s.category, s.frequency, s.unit
FROM economic_releases AS r
JOIN series_release_map AS m ON m.release_id = r.release_id
JOIN series AS s ON s.series_id = m.series_id
LEFT JOIN release_dates AS d ON d.release_id = r.release_id
  AND d.release_date BETWEEN %s AND %s
WHERE s.active = TRUE AND s.series_id = ANY(%s)
ORDER BY d.release_date, r.name, r.release_id, s.series_id;
"""

RELEASE_DETAIL_SQL = """
SELECT r.release_id, r.name, r.source_link, r.press_release,
       s.series_id, s.name, s.short_name, s.category, s.frequency, s.unit
FROM economic_releases AS r
JOIN series_release_map AS m ON m.release_id = r.release_id
JOIN series AS s ON s.series_id = m.series_id
WHERE r.release_id = %s AND s.active = TRUE AND s.series_id = ANY(%s)
ORDER BY s.series_id;
"""

RECENT_DATES_SQL = """
SELECT release_date FROM release_dates
WHERE release_id = %s
ORDER BY release_date DESC
LIMIT 8;
"""

HIGH_IMPORTANCE_RELEASES = frozenset({
    "Employment Situation",
    "Consumer Price Index",
    "Personal Income and Outlays",
    "Gross Domestic Product",
    "Unemployment Insurance Weekly Claims Report",
})
MEDIUM_IMPORTANCE_RELEASES = frozenset({
    "Job Openings and Labor Turnover Survey",
    "Industrial Production and Capacity Utilization",
    "Advance Monthly Sales for Retail and Food Services",
    "New Residential Construction",
    "New Residential Sales",
    "Chicago Fed National Financial Conditions Index",
})
LOW_IMPORTANCE_RELEASES = frozenset({"H.15 Selected Interest Rates"})
IMPORTANCE_ORDER = {"high": 0, "medium": 1, "low": 2}


class InvalidCalendarRangeError(ValueError):
    pass


class InvalidCalendarCategoryError(ValueError):
    pass


class UnknownReleaseError(ValueError):
    pass


def _series(row: tuple) -> dict:
    return dict(zip(("series_id", "name", "short_name", "category", "frequency", "unit"), row))


def release_importance(name: str) -> str:
    if name in HIGH_IMPORTANCE_RELEASES:
        return "high"
    if name in LOW_IMPORTANCE_RELEASES:
        return "low"
    if name in MEDIUM_IMPORTANCE_RELEASES:
        return "medium"
    return "medium"


def list_calendar_events(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
) -> dict:
    today = datetime.now(ZoneInfo("Europe/Warsaw")).date()
    start = start_date or today - timedelta(days=today.weekday())
    end = end_date or start + timedelta(days=6)
    if start > end:
        raise InvalidCalendarRangeError("start_date must be on or before end_date.")
    if (end-start).days >= 366:
        raise InvalidCalendarRangeError("Calendar ranges are limited to 366 days.")
    configured = load_series_config()
    categories = {item["category"] for item in configured.values()}
    if category is not None and category not in categories:
        raise InvalidCalendarCategoryError(f"Unknown category: {category}")

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(CALENDAR_SQL, (start, end, list(configured)))
            rows = cursor.fetchall()
    finally:
        connection.close()

    events = {}
    from app.analytics.calendar_evidence import read_evidence
    evidence=read_evidence()
    templates={}
    for release_date, release_id, name, source_link, *series_columns in rows:
        # Target-bound series have technical FRED update dates on this release.
        # Official policy decisions are merged separately from the Fed schedule.
        if name.casefold() == "fomc press release":
            continue
        template=templates.setdefault(release_id,dict(release_id=release_id,release_name=name,source_link=source_link,
            importance=release_importance(name),date_precision='date',series=[]))
        series = _series(tuple(series_columns))
        if not any(s['series_id']==series['series_id'] for s in template['series']):template['series'].append(series)
        if release_date is None:continue
        key = (release_id, release_date)
        event = events.setdefault(key, {
            "release_id": release_id,
            "release_name": name,
            "release_date": release_date,
            **release_time_metadata(name, release_date, evidence),
            "importance": release_importance(name),
            "source_link": source_link,
            "date_precision": "date",
            "series": [],
        })
        series = _series(tuple(series_columns))
        if not any(item["series_id"] == series["series_id"] for item in event["series"]):
            event["series"].append(series)

    conflicts=apply_bls_schedule(events,templates,evidence,start,end)
    selected = [event for event in events.values() if category is None or any(
        item["category"] == category for item in event["series"]
    )]
    if category in (None, 'growth'):
        from app.analytics.ism_calendar import calendar_events
        selected.extend(calendar_events(start,end))
    policy = read_schedule()
    if category in (None, 'consumer'):
        from app.analytics.michigan_calendar import calendar_events as michigan_events
        selected.extend(michigan_events(start,end))
    if category in (None, 'labor'):
        from app.analytics.adp_calendar import calendar_events as adp_events
        selected.extend(adp_events(start,end))
    if category in (None, 'growth'):
        from app.analytics.empire_state import calendar_events as empire_events
        selected.extend(empire_events(start,end))
        from app.analytics.ft900_calendar import calendar_events as ft900_events
        selected.extend(ft900_events(start,end))
    if category in (None, "financial_conditions"):
        selected.extend({**event, "release_date": date.fromisoformat(event["release_date"])}
                        for event in policy["events"] if str(start) <= event["release_date"] <= str(end))
    selected.sort(key=lambda event: (
        event["release_date"], IMPORTANCE_ORDER[event["importance"]],
        event["release_name"], str(event.get("event_id") or event["release_id"]),
    ))
    from app.ingestion.sync_michigan_calendar import read_schedule as read_michigan_schedule
    michigan=read_michigan_schedule()
    michigan_years=sorted({int(e['reference_period'][:4]) for e in michigan['events']})
    from app.ingestion.sync_adp_calendar import read_schedule as read_adp_schedule
    adp=read_adp_schedule()
    from app.analytics.empire_state import read_schedule as read_empire_schedule
    empire=read_empire_schedule()
    empire_years=sorted({int(e['reference_period'][:4]) for e in empire['events']})
    from app.ingestion.sync_ft900 import read_schedule as ft900_schedule
    trade=ft900_schedule()
    return {
        "start_date": start,
        "end_date": end,
        "category": category,
        "events": selected,
        "ft900_calendar": {"published_years":sorted({int(e['release_date'][:4]) for e in trade['events']}),"tbd_periods":trade.get('tbd_periods',[])},
        "empire_state_calendar": {"published_years":empire_years,
            "requested_year_status":{str(y):'confirmed' if y in empire_years else 'not_published_in_checked_sources' for y in range(start.year,end.year+1)}},
        "michigan_calendar": {"published_years":michigan_years,"check":michigan['check'],
            "requested_year_status":{str(y):'confirmed' if y in michigan_years else 'not_published_in_checked_sources' for y in range(start.year,end.year+1)}},
        "adp_calendar": {"check":adp['check'],"coverage":"bounded_official_evidence",
            "confirmed_dates":sorted(row['release_date'] for row in adp['events']),
            "requested_year_status":{str(y):'bounded_evidence' if any(row['release_date'].startswith(str(y)) for row in adp['events']) else 'not_published_in_checked_sources' for y in range(start.year,end.year+1)}},
        "official_schedule_conflicts": conflicts,
        "policy_calendar": {key: policy[key] for key in ("status", "retrieved_at", "source_url")},
    }


def apply_bls_schedule(events, templates, evidence, start, end):
    """Overlay confirmed identities on the existing FRED calendar, without writes.

    Missing rows in a shorter source do not cancel events. Only an explicit move
    of the same reference period supersedes a previously known date.
    """
    from app.ingestion.bls_schedule import publisher_identity
    from app.analytics.calendar_evidence import schedule_records, claims_rule, period_evidence
    from app.analytics.employment_measures import EMPLOYMENT_LEVELS
    selected,conflicts=schedule_records(evidence)
    active={publisher_identity(r):r for r in selected}
    for old in evidence.get('periods',[])+evidence.get('bls_history',[])+evidence.get('publisher_history',[]):
        current=active.get(publisher_identity(old))
        if current and current['release_date']!=old['release_date']:
            events.pop((old['release_id'],date.fromisoformat(old['release_date'])),None)
    for row in selected:
        rid=row['release_id'];day=date.fromisoformat(row['release_date'])
        if rid not in templates or not start<=day<=end:continue
        template=templates[rid]
        related=[c for c in conflicts if any(publisher_identity(r)==publisher_identity(row) for r in c['candidates'])]
        events[(rid,day)]={**template,'release_date':day,
            'event_id':f"release:{rid}:{row['reference_period']}:{row.get('estimate_stage') or 'main'}",
            'series':[s for s in template['series'] if s['series_id'] in row['series_ids']
                      or (rid==50 and 'PAYEMS' in row['series_ids'] and s['series_id'] in EMPLOYMENT_LEVELS)],
            **release_time_metadata(template['release_name'],day,evidence),
            'source_link':row['source_url'],'schedule_provenance':row,
            'schedule_status':'confirmed', 'estimate_stage':row.get('estimate_stage'),
            'schedule_conflicts':related}
    for conflict in conflicts:
        if conflict['resolution']!='unresolved':continue
        for row in conflict['candidates']:
            key=(row['release_id'],date.fromisoformat(row['release_date']))
            if key in events:
                events[key].update(schedule_status='conflict',schedule_conflicts=[conflict],
                                   release_time=None,source_timezone=None,release_datetime_utc=None)
    # G.17 explicitly distinguishes an annual revision from monthly readings.
    # It has a confirmed date/clock, but no single monthly Actual/Previous pair.
    clocks={}
    for rule in evidence.get('rules',[]):
        if rule.get('release_id')==13 and rule.get('id','').startswith('g17_clock_'):
            if rule['id'] not in clocks or rule['retrieved_at']>clocks[rule['id']]['retrieved_at']:
                clocks[rule['id']]=rule
    if 13 in templates:
        for rule in clocks.values():
            for text in rule.get('annual_revision_dates',[]):
                day=date.fromisoformat(text)
                if not start<=day<=end:continue
                events[(13,day)]={**templates[13], 'event_id':f'release:13:annual_revision:{day.year}',
                    'release_date':day,'release_name':'G.17 annual revision',
                    **release_time_metadata(templates[13]['release_name'],day,evidence),
                    'source_link':rule['source_url'],'schedule_provenance':rule,'schedule_status':'confirmed',
                    'estimate_stage':'annual_revision','expects_numeric_result':False,'measures':[],
                    'description':'Annual revision of industrial production and capacity utilization history; no single monthly reading is assigned.'}
    # DOL publishes an explicit bounded weekly rule and holiday substitutions.
    # No dates are inferred from a FRED series frequency.
    if 180 in templates:
        for offset in range((end-start).days+1):
            day=start+timedelta(days=offset)
            rule=claims_rule(evidence,str(day))
            if not rule:continue
            template=templates[180]
            proof=period_evidence(evidence,180,str(day),'ICSA')
            events[(180,day)]={**template,'release_date':day,
                'event_id':f"release:180:{proof['reference_period']}:weekly",
                **release_time_metadata(template['release_name'],day,evidence),
                'source_link':rule['source_url'],'schedule_provenance':proof,'schedule_status':'confirmed'}
        for key in list(events):
            if key[0]==180 and any(str(key[1]) in r.get('cancelled_dates',[]) for r in evidence.get('rules',[])
                                  if r.get('id')=='dol_weekly_claims') and not claims_rule(evidence,str(key[1])):
                events.pop(key)
    return conflicts


def get_release_detail(release_id: int) -> dict:
    configured = load_series_config()
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(RELEASE_DETAIL_SQL, (release_id, list(configured)))
            rows = cursor.fetchall()
            if not rows:
                raise UnknownReleaseError(f"Unknown release: {release_id}")
            cursor.execute(RECENT_DATES_SQL, (release_id,))
            recent_dates = [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()

    first = rows[0]
    return {
        "release_id": first[0],
        "release_name": first[1],
        "source_link": first[2],
        "press_release": first[3],
        "date_precision": "date",
        "series": [_series(row[4:]) for row in rows],
        "recent_dates": recent_dates,
    }
