"""Read-only FT900 calendar and signed total BOP balance, directly from Census."""
from datetime import date
from decimal import Decimal
from app.database.connection import get_connection
from app.ingestion import sync_ft900 as source
from app.analytics.empire_state import instant

DEFINITION = 'Total Goods and Services Balance, Seasonally Adjusted, Balance of Payments Basis. Exports minus imports; negative means deficit. Millions divided by 1000 for USD billions. Nominal level, not MoM, annualized growth or real GDP contribution.'


def rights():
    return dict(source=source.ATTRIBUTION,copyright=source.ATTRIBUTION,original_title=source.OFFICIAL_TITLE,
        original_url=source.XLSX,terms_url=source.TERMS,modifications=source.MODIFICATIONS,
        redistribution_conditions='BEA public-domain policy with stated exceptions; retain Census/BEA attribution and distinguish MacroLens conversions. Separate FRED terms remain unresolved.')


def calendar_events(start,end):
    schedule=source.read_schedule();result=[]
    for row in schedule['events']:
        if not str(start)<=row['release_date']<=str(end):continue
        result.append(dict(release_id=None,event_id=row['event_id'],event_type='ft900',release_name=source.NAME,
            release_date=date.fromisoformat(row['release_date']),release_time=row['release_time'],release_datetime_utc=instant(row).isoformat().replace('+00:00','Z'),
            source_timezone='America/New_York',date_precision='date',date_status='confirmed',time_status='confirmed',
            source_link=row['source_url'],time_source_url=row['time_source_url'],category='growth',importance='medium',importance_origin='macrolens_editorial',
            reference_period=row['reference_period'],expects_numeric_result=True,description=DEFINITION,
            series=[dict(series_id=source.SID,name=source.NAME,short_name=source.LABEL,category='growth',frequency='monthly',unit='Millions of Dollars',source=source.SOURCE)],
            publisher='U.S. Census Bureau / U.S. Bureau of Economic Analysis',usage_rights=rights(),
            document_url=row.get('document_url'),document_status='unconfirmed',schedule_status=row.get('schedule_status','confirmed'),schedule_provenance=row['schedule_provenance'],
            history=[h for h in schedule.get('history',[]) if h['event_id']==row['event_id']]))
    return result


def load_state(connection):
    return dict(documents=source.receipts(connection),observations=source.load_observations(connection))


def bind_measure(event,state,now):
    period=event['reference_period'];prior=source.previous_month(period)
    documents=[d for d in state['documents'] if d['retrieved_at']<=now];points=state['observations']
    reports=[d for d in documents if d['kind']=='report' and d['metadata']['reference_period']==period]
    point=points.get(period);previous_point=points.get(prior);future=now<instant(event)
    report=next((d for d in reversed(reports) if point and str(d['id'])==point['publication_document_id']),None)
    def proof(row,month):
        if not row:return None
        doc=next((d for d in documents if str(d['id'])==row['document_id']),None)
        if not doc:return None
        inputs=doc['metadata'].get('values',{}).get(month)
        return dict(source=source.SOURCE,source_url=doc['source_url'],retrieved_at=doc['retrieved_at'].isoformat(),http_status=doc['http_status'],
            raw_hash=doc['raw_hash'],document_id=str(doc['id']),vintage_date=row['vintage_date'],version='current_vintage',observation_period=month,
            exhibit='Exhibit 1',sheet=doc['metadata']['sheet'],source_unit='Millions of Dollars',basis='Balance of Payments',seasonal_adjustment='Seasonally Adjusted',inputs=inputs,
            conversion='USD bn = source Millions of Dollars / 1000')
    actual_proof=proof(point,period);previous_proof=proof(previous_point,prior)
    reason='not_yet_published' if future else 'ft900_publication_unconfirmed' if not reports else 'ft900_exhibit1_unconfirmed' if not report or not actual_proof else None
    actual=float(Decimal(point['value'])/1000) if reason is None else None
    previous=float(Decimal(previous_point['value'])/1000) if previous_proof else None
    books=[d for d in documents if d['kind']=='xlsx'];latest=books[-1] if books else None
    event['document_status']='available' if reports else 'unconfirmed'
    if reports:
        event['document_url']=reports[-1]['source_url']
        event['document_provenance']={k:str(v) if k in ('id','retrieved_at') else v for k,v in reports[-1].items() if k!='metadata'}
    difference=bool(report and actual is not None and abs(Decimal(point['value'])-Decimal(report['metadata']['reported_balance_millions']))>Decimal(report['metadata']['reported_precision_millions']))
    event['result_state']=dict(schedule='confirmed',document=event['document_status'],numeric='available' if actual is not None else reason,
        data_version='current_vintage',report_exhibit_difference=difference,publication_time_observed=None,csv_update_time_observed=None,
        exhibit_latest_period=latest['metadata']['latest_period'] if latest else None)
    return dict(series_id=source.SID,label=source.LABEL,feature_name='raw',frequency='monthly',unit='USD bn',definition=DEFINITION,
        reference_period=period,previous_period=prior,previous_kind='previous_period',actual=actual,previous=previous,forecast=None,consensus_status='not_integrated',
        mapping_status='confirmed',binding_method='official_ft900_report_and_exhibit1',data_version='current_vintage' if actual is not None else None,
        previous_data_version='current_vintage' if previous is not None else None,revision_confirmed=difference,
        vintage_date=point['vintage_date'] if actual is not None else None,realtime_end=None,
        result_status='available' if actual is not None else 'scheduled' if future else 'awaiting_data',
        missing_reason=dict(actual=reason,previous=None if previous is not None else 'observation_missing'),
        source_url=source.XLSX,period_provenance=dict(source_url=event['source_link'],reference_period=period,binding_method='official_schedule'),
        actual_provenance=actual_proof if actual is not None else None,previous_provenance=previous_proof,
        result_provenance=dict(source_url=report['source_url'],reference_period=period,release_date=report['metadata']['release_date']) if report and actual is not None else None,
        source_value_millions=point['value'] if actual is not None else None,previous_source_value_millions=previous_point['value'] if previous is not None else None,
        attribution=source.ATTRIBUTION,usage_rights=rights(),
        document_versions=[dict(id=str(d['id']),source_url=d['source_url'],raw_hash=d['raw_hash'],retrieved_at=d['retrieved_at'].isoformat(),revisions=d['metadata'].get('revisions',[])) for d in books if period in d['metadata'].get('values',{})])
