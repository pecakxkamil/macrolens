"""Calendar-only retail definitions; levels come from the existing FRED pipeline.

The market control aggregate is not BEA's adjusted PCE retail-control estimate.
RSFSXMV already excludes NAICS 441; subtract 447, 444 and 722 once each.
Only a common stored current-vintage snapshot is used, never synthetic first prints.
"""
import copy
import math

RETAIL_SERIES = ('RSAFS', 'RSFSXMV', 'RSGASS', 'RSBMGESD', 'RSFSDP')
CONTROL_COMPONENTS = {'RSFSXMV': 1, 'RSGASS': -1, 'RSBMGESD': -1, 'RSFSDP': -1}
EX_AUTOS_DEFINITION = 'Monthly percentage change in seasonally adjusted nominal retail and food services sales excluding motor vehicle and parts dealers (NAICS 441). Both vehicles and automotive parts are excluded; food services are retained. Levels are millions of dollars; prices are not deflated.'
CONTROL_DEFINITION = 'Control Group = RSFSXMV - RSGASS - RSBMGESD - RSFSDP: seasonally adjusted nominal sales excluding NAICS 441, 447, 444 and 722. MoM = 100 × (current level / previous level - 1). This market aggregate is not BEA PCE or a real spending measure.'


def validate_metadata(sid, metadata):
    if sid not in CONTROL_COMPONENTS:
        return
    from app.database.sync_series import load_series_config
    spec = load_series_config()[sid]
    if (metadata.get('id') != sid or metadata.get('title') != spec['name']
            or metadata.get('frequency') != 'Monthly'
            or metadata.get('seasonal_adjustment') != 'Seasonally Adjusted'
            or metadata.get('units') != 'Millions of Dollars'):
        raise ValueError('Retail component metadata does not match the reviewed SA monthly level definition.')


def expand_retail_evidence(evidence):
    """The confirmed advance report month applies to its covered retail categories.

    Preserve source records on disk. Do not extend full MRTS or other stages.
    """
    result = copy.deepcopy(evidence)
    for kind in ('periods', 'results'):
        for row in result.get(kind, []):
            if row.get('release_id') == 9 and row.get('estimate_stage') == 'advance' and 'RSAFS' in row.get('series_ids', []):
                row['series_ids'] = list(dict.fromkeys([*row['series_ids'], *RETAIL_SERIES]))
    return result


def control_level(current, period):
    """Require the same observation period AND stored FRED vintage for all inputs."""
    points = {}
    for sid in CONTROL_COMPONENTS:
        candidates = [p for p in current.get(sid, []) if str(p['observation_date']) == period]
        if len(candidates) != 1:
            return None, 'retail_component_missing', None
        point = candidates[0]
        try:
            valid = math.isfinite(float(point['value'])) and float(point['value']) >= 0
        except (TypeError, ValueError):
            valid = False
        if not valid:
            return None, 'retail_component_invalid', None
        points[sid] = point
    vintages = {str(p.get('vintage_date') or '') for p in points.values()}
    # ALFRED and FRED must never be mixed into a fictitious common snapshot.
    if len(vintages) != 1 or '' in vintages or any(p.get('source') != 'fred_snapshot' for p in points.values()):
        return None, 'retail_component_vintage_mismatch', None
    components = {sid: float(p['value']) for sid, p in points.items()}
    level = sum(CONTROL_COMPONENTS[sid] * value for sid, value in components.items())
    proof = dict(observation_period=period, vintage_date=next(iter(vintages)),
                 components=components, level=level, unit='millions of dollars',
                 source_urls={sid: f'https://fred.stlouisfed.org/series/{sid}' for sid in components})
    return (level, None, proof) if math.isfinite(level) and level > 0 else (None, 'retail_denominator_invalid', proof)


def control_change(current, period):
    from app.analytics.calendar_readings import period_before, value_at
    if not period:
        return None, 'reference_period_unconfirmed', None
    previous = period_before(period, 'monthly')
    level, reason, proof = control_level(current, period)
    prior, prior_reason, prior_proof = control_level(current, previous)
    provenance = dict(current=proof, previous=prior_proof, formula='100 * ((RSFSXMV - RSGASS - RSBMGESD - RSFSDP)[t] / (RSFSXMV - RSGASS - RSBMGESD - RSFSDP)[t-1] - 1)')
    if reason or prior_reason:
        return None, reason or prior_reason, provenance
    if proof['vintage_date'] != prior_proof['vintage_date']:
        return None, 'retail_component_vintage_mismatch', provenance
    # Reuse the shared percentage-change implementation on explicit monthly levels.
    value = value_at('RSFSXMV', 'mom', [dict(observation_date=previous, value=prior),
                     dict(observation_date=period, value=level)], period, 'monthly')
    return value, None, provenance


def append_control(event, current, updates):
    base = next((m for m in event['measures'] if m['series_id'] == 'RSFSXMV'), None)
    if base is None:
        return
    measure = copy.deepcopy(base)
    measure.update(series_id='RETAIL_CONTROL', label='Retail Sales Control Group MoM', definition=CONTROL_DEFINITION,
                   source_url='https://www.census.gov/retail/sales.html', revision_confirmed=False,
                   vintage_date=None, realtime_end=None, actual_provenance=None, previous_provenance=None)
    actual, actual_reason, actual_proof = control_change(current, base['reference_period'])
    previous, previous_reason, previous_proof = control_change(current, base['previous_period'])
    # Report evidence, fresh observations and provider availability must all hold.
    # A shared retrieval day is not evidence of a newly published month.
    day = str(event['release_date'])
    fresh = actual_proof and actual_proof.get('current') and actual_proof['current']['vintage_date'] >= day
    posted = updates and all((updates.get(sid) or '')[:10] >= day for sid in CONTROL_COMPONENTS)
    if base['actual'] is None or not base.get('result_provenance') or not fresh or not posted:
        actual = None
        actual_reason = base['missing_reason']['actual'] if base['actual'] is None else actual_reason or 'publisher_result_not_confirmed'
    measure.update(actual=actual, previous=previous, data_version='current_vintage' if actual is not None else None,
                   previous_data_version='current_vintage' if previous is not None else None,
                   result_provenance=base.get('result_provenance') if actual is not None else None,
                   result_status='available' if actual is not None else base['result_status'] if base['actual'] is None else 'awaiting_data',
                   missing_reason=dict(actual=actual_reason, previous=previous_reason),
                   calculation_provenance=dict(actual=actual_proof, previous=previous_proof))
    for kind, value, proof in [('actual', actual, actual_proof), ('previous', previous, previous_proof)]:
        if value is not None:
            measure[kind+'_provenance'] = dict(source_url=measure['source_url'],version='current_vintage',
                vintage_date=proof['current']['vintage_date'], observation_period=proof['current']['observation_period'])
    event['measures'].append(measure)
