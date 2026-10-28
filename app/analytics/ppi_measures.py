"""Reviewed BLS final-demand definitions and calendar snapshot safeguards.

Each percentage uses one series, one index base and one stored daily snapshot.
SA and NSA levels are never divided by one another. No first prints are inferred.
"""
import copy
import math
import re
from datetime import date, datetime

PPI_PAIRS = {'PPIFIS': 'PPIFID', 'PPIFES': 'PPICOR', 'WPSFD49116': 'WPUFD49116'}
PPI_SERIES = tuple(PPI_PAIRS) + tuple(PPI_PAIRS.values())
NEW_PPI_SERIES = set(PPI_SERIES) - {'PPIFIS'}
PPI_BASES = {'PPIFIS': 'Nov 2009', 'PPIFID': 'Nov 2009',
             'PPIFES': 'Apr 2010', 'PPICOR': 'Apr 2010',
             'WPSFD49116': 'Aug 2013', 'WPUFD49116': 'Aug 2013'}
PPI_NAMES = {'PPIFIS': 'Producer Price Index by Commodity: Final Demand',
             'PPIFID': 'Producer Price Index by Commodity: Final Demand',
             'PPIFES': 'Producer Price Index by Commodity: Final Demand: Final Demand Less Foods and Energy',
             'PPICOR': 'Producer Price Index by Commodity: Final Demand: Final Demand Less Foods and Energy',
             'WPSFD49116': 'Producer Price Index by Commodity: Final Demand: Final Demand Less Foods, Energy, and Trade Services',
             'WPUFD49116': 'Producer Price Index by Commodity: Final Demand: Final Demand Less Foods, Energy, and Trade Services'}
PPI_LABELS = {'PPIFIS': 'PPI Final Demand MoM', 'PPIFID': 'PPI Final Demand YoY',
              'PPIFES': 'Core PPI excluding foods and energy MoM', 'PPICOR': 'Core PPI excluding foods and energy YoY',
              'WPSFD49116': 'PPI excluding foods, energy and trade services MoM',
              'WPUFD49116': 'PPI excluding foods, energy and trade services YoY'}
DEFINITIONS = {
    'PPIFIS': 'Prices received by domestic producers for final demand, including foods, energy and trade services.',
    'PPIFES': 'Final-demand prices excluding foods and energy; trade services remain included.',
    'WPSFD49116': 'Final-demand prices excluding foods, energy and trade services. Trade services indexes measure wholesale and retail margins.',
}


def validate_metadata(sid, metadata):
    if sid not in PPI_SERIES:
        return
    adjustment = 'Seasonally Adjusted' if sid in PPI_PAIRS else 'Not Seasonally Adjusted'
    if (metadata.get('id') != sid or metadata.get('title') != PPI_NAMES[sid]
            or metadata.get('frequency') != 'Monthly'
            or metadata.get('seasonal_adjustment') != adjustment
            or metadata.get('units') != f'Index {PPI_BASES[sid]}=100'):
        raise ValueError('PPI metadata differs from the reviewed BLS series, base, frequency or seasonal adjustment.')


def expand_ppi_evidence(evidence):
    result = copy.deepcopy(evidence)
    for kind in ('periods', 'results'):
        for row in result.get(kind, []):
            if row.get('release_id') == 46 and 'PPIFIS' in row.get('series_ids', []):
                row['series_ids'] = list(dict.fromkeys([*row['series_ids'], *PPI_SERIES]))
    return result


def inputs(points, period, feature):
    if not period:
        return None, 'reference_period_unconfirmed'
    day = date.fromisoformat(period)
    months = day.year * 12 + day.month - 1 - (12 if feature == 'yoy' else 1)
    prior = str(date(months // 12, months % 12 + 1, 1))
    found = []
    for key in (period, prior):
        rows = [p for p in points if str(p['observation_date']) == key]
        if len(rows) != 1:
            return None, 'transformation_dependency_missing'
        point = rows[0]
        try:
            if not math.isfinite(float(point['value'])) or float(point['value']) <= 0:
                return None, 'ppi_index_invalid'
        except (ValueError, TypeError):
            return None, 'ppi_index_invalid'
        found.append(point)
    if (any(p.get('source') != 'fred_snapshot' for p in found)
            or not found[0].get('vintage_date')
            or str(found[0]['vintage_date']) != str(found[1].get('vintage_date'))):
        return None, 'ppi_snapshot_mismatch'
    return dict(period=period, level=float(found[0]['value']), comparison_period=prior,
                comparison_level=float(found[1]['value']), vintage_date=str(found[0]['vintage_date'])), None


def availability_reason(sid, points, period, event, proof, updates):
    feature = 'mom' if sid in PPI_PAIRS else 'yoy'
    detail, reason = inputs(points, period, feature)
    if reason:
        return reason
    day = str(event['release_date'])
    updated = (updates or {}).get(sid) or ''
    # A newly fetched observation for the exact confirmed report month, not
    # another PPI series or a metadata timestamp alone, is required.
    if not proof or detail['vintage_date'] < day or updated[:10] < day:
        return 'ppi_publication_not_confirmed'
    if event.get('release_datetime_utc'):
        try:
            stamp = re.sub(r'([+-]\d{2})$', r'\1:00', updated)
            if datetime.fromisoformat(stamp) < datetime.fromisoformat(event['release_datetime_utc'].replace('Z', '+00:00')):
                return 'ppi_publication_not_confirmed'
        except (ValueError, TypeError):
            return 'ppi_publication_not_confirmed'
    return None


def decorate_and_fold(event, current):
    for measure in event['measures']:
        sid = measure['series_id']
        if sid not in PPI_SERIES:
            continue
        sa = sid in PPI_PAIRS
        primary = sid if sa else next(k for k,v in PPI_PAIRS.items() if v == sid)
        measure.update(input_unit=f'Index {PPI_BASES[sid]}=100',
                       seasonal_adjustment='Seasonally Adjusted' if sa else 'Not Seasonally Adjusted',
                       transform_formula='100 * (I[t] / I[t-1] - 1)' if sa else '100 * (I[t] / I[t-12] - 1)',
                       definition=DEFINITIONS[primary] + ' PPI measures selling prices received, not production costs; it is not a market or Fed signal.')
        if sid in NEW_PPI_SERIES:
            measure['index_inputs'] = {}
            for kind, period in [('actual',measure['reference_period']),('previous',measure['previous_period'])]:
                detail, reason = inputs(current.get(sid, []), period, measure['feature_name'])
                measure['index_inputs'][kind] = detail
                if measure[kind] is None and reason and measure['missing_reason'][kind] not in ('not_yet_published','reference_period_unconfirmed'):
                    measure['missing_reason'][kind] = reason
    measures = {m['series_id']: m for m in event['measures']}
    for sid, yearly in PPI_PAIRS.items():
        if sid in measures and yearly in measures:
            measures[sid]['year_over_year'] = measures[yearly]
    event['measures'] = [m for m in event['measures'] if m['series_id'] not in PPI_PAIRS.values()]
