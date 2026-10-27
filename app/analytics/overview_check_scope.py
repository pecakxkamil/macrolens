"""Read-only scope projection: Overview availability versus full FOMC schedule."""
import copy


def scope_overview_checks(brief):
    """Project saved provenance; do not fetch, update timestamps or mutate a cache."""
    checks = brief.get('source_checks')
    if not checks:
        return brief
    result = {**brief, 'source_checks': copy.deepcopy(checks)}
    checks = result['source_checks']
    checks['status_scope'] = 'overview'
    checks['full_scope_status'] = checks.get('full_scope_status', checks['status'])
    fed = next((row for row in checks.get('sources', []) if row['resource'] == 'fed:calendar'), None)
    if not fed:
        return result
    scope = fed.get('scope', {})
    start, end = brief['calendar_start_date'], brief['calendar_end_date']
    policy = brief.get('policy') or {}
    policy_data = policy.get('data') or {}
    next_event = policy_data.get('next_decision')
    calendar = brief.get('calendar') or {}
    events = (calendar.get('data') or {}).get('events', [])
    displayed = [event for event in events if event.get('event_type') == 'fomc_decision'
                 or event.get('release_name') == 'FOMC policy decision']
    if next_event:
        displayed.append(next_event)
    # Also include scheduled dates in the displayed window if a calendar loader
    # omitted them, so missing event data cannot silently improve coverage.
    required = {day for day in scope.get('dates', []) if start <= day <= end}
    required.update(event['release_date'] for event in displayed)
    missing = set(scope.get('missing_times', []))
    displayed_missing = missing & required
    displayed_missing.update(event['release_date'] for event in displayed if not event.get('release_datetime_utc'))
    time_checks = scope.get('time_checks', [])
    fetch_errors = {row['release_date'] for row in time_checks if row['fetch_status'] == 'error'}
    displayed_errors = sorted(fetch_errors & required)
    future_missing = sorted(day for day in missing - required if day > end)
    overview_status = fed['status']
    reason = None
    if overview_status not in ('error', 'running', 'not_recorded'):
        if (policy.get('status') != 'ready' or policy_data.get('schedule_status') != 'available'
                or not next_event or calendar.get('status') != 'ready'):
            overview_status, reason = 'partial', 'displayed_schedule_unavailable'
        elif required - {event['release_date'] for event in displayed}:
            overview_status, reason = 'partial', 'displayed_event_unavailable'
        elif displayed_errors:
            overview_status, reason = 'error', 'displayed_schedule_fetch_failed'
        elif displayed_missing:
            overview_status, reason = 'partial', 'displayed_decision_time_unavailable'
        elif (fed['status'] == 'partial' and fed.get('error_code') == 'decision_times_unavailable'
                and missing and not scope.get('legacy_dates_only')
                and required <= set(scope.get('dates', []))):
            overview_status = 'success'
    fed['overview_status'] = overview_status
    fed['overview_error_code'] = reason or (fed.get('error_code') if overview_status != 'success' else None)
    # Existing timestamps only: a partial run can successfully check this narrower
    # scope. Older caches may only have the conservative coverage timestamp.
    fed['overview_checked_at'] = (fed.get('last_finished_at') or fed.get('coverage_checked_at')) if overview_status == 'success' else fed.get('coverage_checked_at')
    checks['fomc_schedule'] = {
        'source_check_status': ('error' if fetch_errors else 'success') if time_checks else fed['status'],
        'completeness_status': 'partial' if missing else 'complete' if fed['status'] == 'success' else fed['status'],
        'overview_status': overview_status,
        'overview_dates': sorted(required), 'displayed_missing_times': sorted(displayed_missing),
        'future_missing_times': future_missing, 'fetch_error_dates': sorted(fetch_errors),
        'time_checks': time_checks,
    }
    for row in checks['sources']:
        row.setdefault('overview_status', row['status'])
        row.setdefault('overview_checked_at', row.get('coverage_checked_at'))
    checked = [row for row in checks['sources'] if row.get('overview_checked_at')]
    checks['checked_count'] = len(checked)
    checks['checked_at'] = min((row['overview_checked_at'] for row in checked), default=None)
    complete = len(checked) == checks['required_count'] and all(row['overview_status'] == 'success' for row in checks['sources'])
    checks['status'] = 'complete' if complete else 'partial' if checked else 'not_recorded'
    return result
