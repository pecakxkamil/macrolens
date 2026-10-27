"""ISM calendar projection over existing validated document versions; no ingestion."""
import math
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.local_ism import SERIES, ATTRIBUTION
from app.ingestion.import_ism import KINDS
from app.ingestion.sync_ism_calendar import read_schedule


def calendar_events(start, end):
    events=[]
    for row in read_schedule()['events']:
        if not str(start)<=row['release_date']<=str(end): continue
        sid=KINDS[row['kind']]
        local=datetime.fromisoformat(row['release_date']+'T'+row['release_time']).replace(tzinfo=ZoneInfo(row['source_timezone']))
        events.append(dict(release_id=None,event_id=f"ism:{row['kind']}:{row['reference_period']}",event_type='ism_report',
            release_name=SERIES[sid]['name'],release_date=date.fromisoformat(row['release_date']),
            release_time=row['release_time'],source_timezone=row['source_timezone'],release_datetime_utc=local.astimezone(timezone.utc).isoformat().replace('+00:00','Z'),
            time_source_url=row.get('clock_source_url') or row['source_url'],source_link=row['source_url'],date_precision='date',
            importance='high',importance_origin='macrolens_editorial',series=[dict(series_id=sid,**SERIES[sid])],
            period_evidence=row,attribution=ATTRIBUTION))
    return events


def load_documents(connection):
    with connection.cursor() as cursor:
        cursor.execute('''SELECT d.id,d.series_id,d.report_month,d.published_at,d.retrieved_at,d.source_url,d.raw_hash,
            o.observation_date,o.value FROM ism_documents d JOIN ism_observations o ON o.document_id=d.id
            ORDER BY d.series_id,d.report_month,d.published_at,d.retrieved_at,d.id,o.observation_date''')
        rows=cursor.fetchall()
    documents={}
    for identity,sid,period,published,retrieved,url,digest,observed,value in rows:
        doc=documents.setdefault(identity,dict(id=identity,series_id=sid,report_month=str(period),published_at=published,
            retrieved_at=retrieved,source_url=url,raw_hash=digest,readings={}))
        if value is not None and math.isfinite(float(value)):doc['readings'][str(observed)]=float(value)
    return list(documents.values())


def previous_month(period):
    day=date.fromisoformat(period);ordinal=day.year*12+day.month-2
    return str(date(ordinal//12,ordinal%12+1,1))


def document_provenance(doc, period, version):
    if not doc:return None
    return dict(source_url=doc['source_url'],document_id=doc['id'],report_month=doc['report_month'],
        document_published_at=doc['published_at'].isoformat(),retrieved_at=doc['retrieved_at'].isoformat(),raw_hash=doc['raw_hash'],
        observation_period=period,version=version,source='ism_document')


def bind_measure(event, documents, now):
    proof=event['period_evidence'];period=proof['reference_period'];prior=previous_month(period)
    sid=KINDS[proof['kind']]
    instant=datetime.fromisoformat(event['release_datetime_utc'].replace('Z','+00:00'))
    future=instant>now
    eligible=[d for d in documents if d['series_id']==sid and d['published_at']<=now]
    order=lambda d:(d['published_at'],d['retrieved_at'],d['id'])
    # Only the document whose MAIN report month matches this event can provide
    # Actual. Older rows in a new 12-month table never become historical prints.
    doc=max((d for d in eligible if d['report_month']==period and d['published_at']>=instant),key=order,default=None) if not future else None
    actual=doc['readings'].get(period) if doc else None
    if actual is None:doc=None
    previous_doc=doc
    previous=doc['readings'].get(prior) if doc else None
    previous_version='official_release' if previous is not None else None
    if doc is None:
        # Prefer an actual document for the immediately preceding report. Fall
        # back to a clearly labelled current-vintage context only for that month.
        candidates=[d for d in eligible if d['report_month']==prior and prior in d['readings']]
        previous_doc=max(candidates,key=order,default=None)
        if previous_doc:previous=previous_doc['readings'][prior];previous_version='official_release'
        else:
            previous_doc=max((d for d in eligible if prior in d['readings']),key=order,default=None)
            if previous_doc:previous=previous_doc['readings'][prior];previous_version='current_vintage'
    before=max((d for d in eligible if d['report_month']==prior and prior in d['readings'] and doc and d['published_at']<doc['published_at']),key=order,default=None)
    if before is None and doc:
        # An older version of this same report can also document an earlier
        # previous value. Keep its report identity; it is not a first print.
        before=max((d for d in eligible if prior in d['readings'] and order(d)<order(doc)),key=order,default=None)
    old_previous=before['readings'][prior] if before else None
    previous_revised=old_previous is not None and previous is not None and previous!=old_previous
    return dict(series_id=sid,label=SERIES[sid]['name'],feature_name='raw',frequency='monthly',unit='index points',
        definition='ISM diffusion index level; changes are index-point differences, not percentages or percentage growth.',
        reference_period=period,previous_period=prior,previous_kind='previous_period',actual=actual,previous=previous,
        forecast=None,consensus_status='not_integrated',mapping_status='confirmed',binding_method=proof['binding_method'],
        data_version='official_release' if doc else None,previous_data_version=previous_version,
        revision_confirmed=False,vintage_date=None,realtime_end=None,
        result_status='available' if doc else 'scheduled' if future else 'awaiting_data',
        missing_reason={'actual':None if doc else 'not_yet_published' if future else 'ism_report_not_confirmed',
                        'previous':None if previous is not None else 'observation_missing'},
        source_url=doc['source_url'] if doc else SERIES[sid]['source_url'],period_provenance=proof,
        actual_provenance=document_provenance(doc,period,'official_release'),
        previous_provenance=document_provenance(previous_doc,prior,previous_version),
        result_provenance={**document_provenance(doc,period,'official_release'),'release_date':str(event['release_date']),'reference_period':period} if doc else None,
        previous_before_report={'value':old_previous,'provenance':document_provenance(before,prior,'official_release')} if before else None,
        previous_revision_confirmed=previous_revised,attribution=ATTRIBUTION)
