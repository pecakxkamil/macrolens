"""Read-only Overview availability-check coverage; no freshness threshold or polling."""
from datetime import datetime, timedelta, timezone

from app.database.connection import get_connection
from app.analytics.overview_readings import READINGS
from app.analytics.fomc_calendar import read_schedule

# Include the existing domain snapshot/details, not just visible headline rows.
SNAPSHOT_SERIES = {
    'PAYEMS', 'UNRATE', 'CIVPART', 'ICSA', 'CCSA', 'JTSJOL',
    'CPIAUCSL', 'CPILFESL', 'PCEPI', 'PCEPILFE', 'ECIALLCIV', 'CES0500000003',
    'GDPC1', 'CFNAI', 'INDPRO', 'TCU', 'DGORDER',
    'RSAFS', 'PCEC96', 'DSPIC96', 'PSAVERT', 'HOUST', 'PERMIT', 'HSN1F',
    'MORTGAGE30US', 'DFF', 'DGS2', 'DGS10', 'DFII10', 'NFCI',
    'DFEDTARL', 'DFEDTARU',
}
FRED_SERIES = SNAPSHOT_SERIES | {sid.strip() for spec in READINGS
    for sid in spec[2].split('/') if not sid.strip().startswith('ISM_')}
REQUIRED = {**{f'fred:{sid}': ('FRED', sid) for sid in sorted(FRED_SERIES)},
    'nyfed:empire-state': ('Federal Reserve Bank of New York', 'Empire State Manufacturing Survey'),
    'fred:calendar': ('FRED', 'Release calendar'),
    'fed:calendar': ('Federal Reserve', 'FOMC schedule'),
    'ism:calendar': ('ISM', 'ISM publication schedule'),
    'michigan:calendar': ('University of Michigan', 'Michigan publication schedule'),
    'adp:calendar': ('ADP', 'ADP monthly publication schedule'),
    'ism:ISM_MANUFACTURING_PMI': ('ISM via PR Newswire', 'ISM Manufacturing PMI'),
    'ism:ISM_SERVICES_PMI': ('ISM via PR Newswire', 'ISM Services PMI')}


def instant(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    if not isinstance(value, datetime) or value.tzinfo is None:
        return None
    return value.astimezone(timezone.utc)


def eligible(row, today, end_date=None):
    scope = row['scope']
    if row['resource']=='nyfed:empire-state':
        return scope.get('schedule_checked') is True and scope.get('csv_validated') is True and set(range(today.year,(end_date or today).year+1))<=set(scope.get('confirmed_years',[]))
    if row['resource']=='michigan:calendar':
        return set(range(today.year,(end_date or today).year+1)) <= set(scope.get('confirmed_years',[]))
    if row['resource']=='adp:calendar':
        return scope.get('confirmed_from','9999')<=str(today) and scope.get('confirmed_through','')>=str(end_date or today)
    if row['resource']=='ism:calendar':
        return bool(scope.get('confirmed_from') and scope.get('confirmed_through') and scope['confirmed_from']<=str(today) and scope['confirmed_through']>=str(end_date or today))
    if row['resource'].startswith('ism:'):
        # Importing a named document cannot discover a more recent publication.
        return scope.get('latest_publication_discovered') is True
    if row['resource'] == 'calendar:periods':
        return scope.get('start_date','9999')<=str(today) and scope.get('end_date','')>=str(end_date or today)
    if row['resource'] == 'fred:calendar':
        return (scope.get('start_date', '9999') <= str(today)
            and scope.get('end_date', '') >= str(end_date or today + timedelta(days=6))
            and FRED_SERIES <= set(scope.get('series_ids', [])))
    if row['resource'] == 'fed:calendar':
        return any(day >= str(today) for day in scope.get('dates', []))
    return True


def summarize_checks(rows, today, required=None, end_date=None):
    sources = []
    for resource, (provider, label) in (required or REQUIRED).items():
        attempts = [row for row in rows if row['resource'] == resource and instant(row['attempted_at'])]
        recorded_attempts = [row for row in attempts if not row['scope'].get('legacy_dates_only')]
        latest = max(recorded_attempts or attempts, key=lambda row: instant(row['attempted_at']), default=None)
        successes = [row for row in attempts if row['status'] == 'success'
            and instant(row['finished_at'])
            and (not resource.startswith('ism:') or resource=='ism:calendar' or row['scope'].get('latest_publication_discovered') is True)]
        success = max(successes, key=lambda row: instant(row['finished_at']), default=None)
        covered = max((row for row in successes if eligible(row, today, end_date)),
            key=lambda row: instant(row['finished_at']), default=None)
        sources.append({'resource': resource, 'provider': provider, 'label': label,
            'status': ('partial' if latest['scope'].get('legacy_dates_only') else latest['status']) if latest else 'not_recorded',
            'last_attempt_at': instant(latest['attempted_at']).isoformat() if latest else None,
            'last_finished_at': instant(latest['finished_at']).isoformat() if latest and instant(latest.get('finished_at')) else None,
            'last_success_at': instant(success['finished_at']).isoformat() if success else None,
            'coverage_checked_at': instant(covered['finished_at']).isoformat() if covered else None,
            'error_code': latest.get('error_code') if latest else None,
            'scope': latest['scope'] if latest else {},
            'successful_scope': success['scope'] if success else None,
            'coverage_scope': covered['scope'] if covered else None})
    checked = [row for row in sources if row['coverage_checked_at']]
    # Conservative coverage watermark: never use one series' newest timestamp
    # as the time the entire Overview was checked. No implicit stale threshold.
    checked_at = min((row['coverage_checked_at'] for row in checked), default=None)
    complete = len(checked) == len(sources) and all(row['status'] == 'success' for row in sources)
    return {'status': 'complete' if complete else 'partial' if checked else 'not_recorded',
        'checked_at': checked_at, 'checked_count': len(checked), 'required_count': len(sources),
        'sources': sources}


def load_source_checks(today, resources=None, end_date=None):
    required = {**REQUIRED, **{resource:("FRED",resource.split(":",1)[1]) for resource in (resources or []) if resource.startswith("fred:") and resource not in REQUIRED}}
    if 'calendar:periods' in (resources or []):required['calendar:periods']=('Publishers','Publisher schedules')
    rows = []
    connection = None
    metadata_status = "available"
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            # Keep latest attempt and latest success whose window/scope covers
            # this Overview. Both survive failed or narrower subsequent checks.
            cursor.execute("""WITH candidates AS (
                SELECT *, row_number() OVER (PARTITION BY resource ORDER BY attempted_at DESC) AS attempt_rank,
                    row_number() OVER (PARTITION BY resource, status,
                        CASE WHEN resource = 'fred:calendar' THEN scope ELSE '{}'::jsonb END
                        ORDER BY finished_at DESC NULLS LAST) AS result_rank
                FROM source_check_runs WHERE resource = ANY(%s)
            ) SELECT resource, attempted_at, finished_at, status, scope, error_code
              FROM candidates WHERE attempt_rank = 1 OR (status = 'success' AND result_rank = 1)""",
                (list(required),))
            rows = [dict(zip(('resource', 'attempted_at', 'finished_at', 'status', 'scope', 'error_code'), row))
                    for row in cursor.fetchall()]
    except Exception:
        # Missing additive migration or unavailable DB: never substitute row
        # ingestion, feature, report assembly or page-load timestamps.
        metadata_status = "unavailable"
    finally:
        if connection is not None:
            connection.close()
    # Existing durable Fed snapshot explicitly proves a successful meeting-date
    # fetch. Its retrieval timestamp proves nothing about other providers or
    # unrecorded monthly-page attempts. Preserve that limited legacy provenance.
    schedule = read_schedule()
    retrieved = instant(schedule.get('retrieved_at'))
    if retrieved and not any(row['resource'] == 'fed:calendar' and row['status'] == 'success' for row in rows):
        dates = [event['release_date'] for event in schedule.get('events', [])]
        rows.append(dict(resource='fed:calendar', attempted_at=retrieved, finished_at=retrieved,
            status='success', scope={'dates': dates, 'legacy_dates_only': True}, error_code=None))
    return {**summarize_checks(rows, today, required, end_date), "metadata_status": metadata_status}
