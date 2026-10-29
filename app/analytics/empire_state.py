"""Read-only calendar binding for direct NY Fed snapshots, not FRED vintages."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from app.database.connection import get_connection
from app.ingestion.sync_empire_state import (SOURCE,SID,NAME,LABEL,HOME,CSV,TERMS,DEFINITIONS,
    ATTRIBUTION,USAGE,read_schedule,receipts,load_observations,previous_month)

DEFINITION = 'Seasonally adjusted diffusion index: percentage reporting improvement minus percentage reporting deterioration. Neutral threshold zero, not 50. Level and index-point differences; no MoM or YoY growth.'


def rights(year):
    return dict(source='Federal Reserve Bank of New York',copyright=ATTRIBUTION.format(year=year),
        original_title=NAME,terms_url=TERMS,original_url=CSV,modifications=USAGE,redistribution_conditions=TERMS)


def instant(event):
    return datetime.fromisoformat(str(event['release_date'])+'T'+event['release_time']).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)


def calendar_events(start,end):
    schedule=read_schedule();events=[]
    for row in schedule['events']:
        if not str(start)<=row['release_date']<=str(end):continue
        events.append(dict(release_id=None,event_id=row['event_id'],event_type='empire_state',release_name=NAME,
            release_date=date.fromisoformat(row['release_date']),release_time=row['release_time'],
            release_datetime_utc=instant(row).isoformat().replace('+00:00','Z'),
            source_timezone='America/New_York',date_precision='date',source_link=HOME,time_source_url=row['time_source_url'],
            category='growth',importance='medium',importance_origin='macrolens_editorial',
            series=[dict(series_id=SID,name=NAME,short_name=LABEL,category='growth',frequency='monthly',unit='index points',source=SOURCE)],
            expects_numeric_result=True,reference_period=row['reference_period'],date_status='confirmed',time_status='confirmed',
            description='Monthly survey of New York State manufacturers. Current General Business Conditions SA is distinct from future expectations and ISM.',
            schedule_status=row.get('schedule_status','confirmed'),schedule_provenance=row['schedule_provenance'],
            document_url=row.get('document_url'),document_status='unconfirmed',
            publisher='Federal Reserve Bank of New York',usage_rights=rights(row['reference_period'][:4]),
            history=[h for h in schedule.get('history',[]) if h['event_id']==row['event_id']]))
    return events


def load_state(connection):
    docs=receipts(connection)
    return dict(observations=load_observations(connection),documents=docs)


def provenance(observation,documents,period):
    if not observation:return None
    doc=next((d for d in documents if str(d['id'])==observation['document_id']),None)
    if not doc:return None
    return dict(source=SOURCE,source_url=doc['source_url'],retrieved_at=doc['retrieved_at'].isoformat(),
        http_status=doc['http_status'],raw_hash=doc['raw_hash'],document_id=str(doc['id']),
        observation_period=period,column='GACDISA',version='current_vintage',vintage_date=observation['vintage_date'])


def bind_measure(event,state,now):
    period=event['reference_period'];prior=previous_month(period);docs=state['documents']
    eligible=[d for d in docs if d['retrieved_at']<=now]
    reports=[d for d in eligible if d['kind']=='report' and d['metadata']['reference_period']==period and d['source_url']==event.get('document_url')]
    report=reports[-1] if reports else None
    event['document_status']='available' if report else 'unconfirmed'
    event['document_provenance']={k:str(v) if k in ('id','retrieved_at') else v for k,v in report.items() if k!='metadata'} if report else None
    observations=state['observations'];point=observations.get(period);previous_point=observations.get(prior)
    proof=provenance(point,eligible,period);previous_proof=provenance(previous_point,eligible,prior)
    future=now<instant(event)
    bound_report=next((d for d in reports if point and str(d['id'])==point.get('publication_document_id')),None)
    reason='not_yet_published' if future else 'empire_report_not_confirmed' if not bound_report else 'observation_missing' if not point or not proof else None
    csvs=[d for d in eligible if d['kind']=='csv'];latest=csvs[-1] if csvs else None
    if reason and not future and latest and latest['metadata'].get('missing_results',{}).get(period)=='empire_source_conflict':reason='empire_source_conflict'
    # A CSV row can never act as a publication receipt. PDF identity is required.
    actual=point['value'] if reason is None else None
    previous=previous_point['value'] if previous_proof else None
    changed=report is not None and actual is not None and report['metadata']['current']!=actual
    event['result_state']=dict(schedule='confirmed',document=event['document_status'],
        numeric='available' if actual is not None else reason,data_version='current_vintage',
        report_csv_difference=changed,publication_time_observed=None,csv_update_time_observed=None,
        freshness='validated_current_csv' if latest and period in latest['metadata'].get('accepted_periods',[]) else 'last_valid_snapshot' if actual is not None else 'no_matching_csv',
        latest_csv_period=latest['metadata']['latest_csv_period'] if latest else None)
    return dict(series_id=SID,label=LABEL,feature_name='raw',frequency='monthly',unit='index points',definition=DEFINITION,
        reference_period=period,previous_period=prior,previous_kind='previous_period',actual=actual,previous=previous,
        forecast=None,consensus_status='not_integrated',mapping_status='confirmed',binding_method='official_nyfed_report_and_csv',
        data_version='current_vintage' if actual is not None else None,previous_data_version='current_vintage' if previous is not None else None,
        revision_confirmed=changed,vintage_date=point['vintage_date'] if point and actual is not None else None,realtime_end=None,
        result_status='available' if actual is not None else 'scheduled' if future else 'awaiting_data',
        missing_reason=dict(actual=reason,previous=None if previous is not None else 'observation_missing'),
        source_url=CSV,period_provenance=dict(source_url=HOME,reference_period=period,binding_method='official_schedule'),
        actual_provenance=proof if actual is not None else None,previous_provenance=previous_proof,
        result_provenance=dict(source_url=report['source_url'],release_date=str(event['release_date']),reference_period=period) if report and actual is not None else None,
        attribution=ATTRIBUTION.format(year=period[:4]),usage_rights=rights(period[:4]),
        report_current=report['metadata']['current'] if report else None,
        document_versions=[dict(id=str(d['id']),raw_hash=d['raw_hash'],retrieved_at=d['retrieved_at'].isoformat(),source_url=d['source_url'],revisions=d['metadata'].get('revisions',[])) for d in eligible if d['kind']=='csv' and period in d['metadata'].get('accepted_periods',[])])
