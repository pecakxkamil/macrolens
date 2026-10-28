"""Three raw Employment Situation levels; CPS and CES are distinct surveys."""
import copy
import math
import re
from datetime import datetime

EMPLOYMENT_LEVELS = {
    'CIVPART': ('Labor Force Participation Rate', 'percent', 'CPS', 'LNS11300000'),
    'U6RATE': ('U-6 Labor Underutilization Rate', 'percent', 'CPS', 'LNS13327709'),
    'AWHAETP': ('Average Weekly Hours — Total Private', 'hours', 'CES', 'CES0500000002'),
}
NAMES = {
    'CIVPART': 'Labor Force Participation Rate',
    'U6RATE': 'Total Unemployed, Plus All Persons Marginally Attached to the Labor Force, Plus Total Employed Part Time for Economic Reasons, as a Percent of the Civilian Labor Force Plus All Persons Marginally Attached to the Labor Force (U-6)',
    'AWHAETP': 'Average Weekly Hours of All Employees, Total Private',
}
DEFINITIONS = {
    'CIVPART': 'CPS household survey: civilian labor force as a percentage of the civilian noninstitutional population aged 16 and over. Seasonally adjusted rate, not a monthly percentage change.',
    'U6RATE': 'CPS household survey: unemployed people plus people marginally attached to the labor force plus people working part time for economic reasons, divided by the civilian labor force plus people marginally attached. Marginally attached people want and are available for work, searched within the past 12 months, but did not search in the past four weeks. Seasonally adjusted U-6, distinct from U-3 and the number unemployed.',
    'AWHAETP': 'CES establishment survey: average weekly paid hours of all employees on total private nonfarm payrolls, seasonally adjusted. Includes all employees, not only production and nonsupervisory workers; not manufacturing hours or overtime hours.',
}


def validate_metadata(sid, metadata):
    if sid not in EMPLOYMENT_LEVELS:
        return
    if (metadata.get('id') != sid or metadata.get('title') != NAMES[sid]
            or metadata.get('frequency') != 'Monthly'
            or metadata.get('seasonal_adjustment') != 'Seasonally Adjusted'
            or metadata.get('units') != ('Hours' if sid == 'AWHAETP' else 'Percent')):
        raise ValueError('Employment metadata differs from the reviewed CPS/CES series.')


def expand_employment_evidence(evidence):
    result = copy.deepcopy(evidence)
    for kind in ('periods', 'results'):
        for row in result.get(kind, []):
            if row.get('release_id') == 50 and 'PAYEMS' in row.get('series_ids', []):
                row['series_ids'] = list(dict.fromkeys([*row['series_ids'], *EMPLOYMENT_LEVELS]))
    return result


def level_reason(sid, points, period):
    rows = [p for p in points if str(p['observation_date']) == str(period)]
    if not period:
        return 'reference_period_unconfirmed'
    if len(rows) != 1:
        return 'observation_missing'
    p = rows[0]
    try:
        value = float(p['value'])
        if not math.isfinite(value) or value < 0 or (sid != 'AWHAETP' and value > 100):
            return 'employment_level_invalid'
    except (ValueError, TypeError):
        return 'employment_level_invalid'
    return None if p.get('source') == 'fred_snapshot' and p.get('vintage_date') else 'employment_snapshot_unconfirmed'


def availability_reason(sid, points, period, event, proof, updates):
    reason = level_reason(sid, points, period)
    if reason:
        return reason
    p = next(p for p in points if str(p['observation_date']) == period)
    updated = (updates or {}).get(sid) or ''
    if not proof or str(p['vintage_date']) < str(event['release_date']) or updated[:10] < str(event['release_date']):
        return 'employment_publication_not_confirmed'
    if event.get('release_datetime_utc'):
        try:
            stamp = re.sub(r'([+-]\d{2})$', r'\1:00', updated)
            if datetime.fromisoformat(stamp) < datetime.fromisoformat(event['release_datetime_utc'].replace('Z', '+00:00')):
                return 'employment_publication_not_confirmed'
        except (ValueError, TypeError):
            return 'employment_publication_not_confirmed'
    return None


def decorate(event, current):
    for m in event['measures']:
        sid = m['series_id']
        if sid not in EMPLOYMENT_LEVELS:
            continue
        _, _, survey, code = EMPLOYMENT_LEVELS[sid]
        m.update(definition=DEFINITIONS[sid], survey=survey, source_series_id=code,
                 seasonal_adjustment='Seasonally Adjusted')
        for kind, period in [('actual', m['reference_period']), ('previous', m['previous_period'])]:
            if m[kind] is None and m['missing_reason'][kind] not in ('not_yet_published', 'reference_period_unconfirmed'):
                reason = level_reason(sid, current.get(sid, []), period)
                if reason:
                    m['missing_reason'][kind] = reason
