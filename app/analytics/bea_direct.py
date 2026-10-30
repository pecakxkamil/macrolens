"""Read-only preference for validated BEA published rates, retaining FRED evidence."""
import copy
from datetime import datetime, timezone
from decimal import Decimal
from app.ingestion import sync_bea_reports as source
from app.analytics.calendar_readings import period_before


def load_state(connection):
    docs=source.receipts(connection)
    with connection.cursor() as c:
        c.execute('''SELECT DISTINCT ON(series_id,observation_date) series_id,observation_date,value,source_document_id,publication_document_id,vintage_date
            FROM observation_vintages WHERE source=%s ORDER BY series_id,observation_date,vintage_date DESC,ingested_at DESC,id DESC''',(source.SOURCE,))
        points={(sid,str(period)):dict(value=str(value),document_id=str(doc),publication_document_id=str(publication),vintage_date=str(vintage)) for sid,period,value,doc,publication,vintage in c.fetchall()}
    return dict(documents=docs,observations=points)


def rights(title,url):
    return dict(source=source.ATTRIBUTION,copyright=source.ATTRIBUTION,original_title=title,original_url=url,terms_url=source.TERMS,
                modifications=source.MODIFICATIONS,redistribution_conditions='BEA public-domain policy, unless otherwise stated; retain source attribution and distinguish MacroLens changes. Other sources have separate terms.')


def select(measure,event,state,now):
    """One Actual. A bad/missing BEA proof leaves the original binding intact."""
    result=copy.deepcopy(measure)
    if event.get('release_id') not in (53,54):return result
    result['selected_source']='fred_fallback' if result.get('actual') is not None else 'not_available'
    period=measure.get('reference_period');stage=event.get('estimate_stage') or (measure.get('period_provenance') or {}).get('estimate_stage')
    if event.get('reference_period'):
        if period is not None and event['reference_period']!=period:return result
        period=event['reference_period']
    for doc in reversed(state['documents']):
        meta=doc['metadata'];stamp=doc['retrieved_at']
        if isinstance(stamp,str):stamp=datetime.fromisoformat(stamp)
        if stamp>now or datetime.fromisoformat(meta['announced_at'])>now:continue
        if (meta['release_id'],meta['release_date'])!=(event['release_id'],str(event['release_date'])):continue
        if period is not None and period!=meta['reference_period']:continue
        if stage is not None and stage!=meta['estimate_stage']:continue
        # The stored report was itself validated against the official schedule.
        # Cold/missing FRED period metadata must not prevent an independent BEA proof.
        period=meta['reference_period'];stage=meta['estimate_stage']
        row=next((r for r in meta['readings'] if (r['series_id'],r['feature_name'])==(measure['series_id'],measure['feature_name'])),None)
        if not row:continue
        storage=source.storage_id(row['series_id'],row['feature_name'],stage)
        point=state['observations'].get((storage,period))
        if not point or point['document_id']!=str(doc['id']) or point.get('publication_document_id')!=str(doc['id']) or Decimal(point['value'])!=Decimal(row['value']):continue
        original={k:copy.deepcopy(measure.get(k)) for k in ('actual','previous','actual_provenance','previous_provenance','data_version','source_url','previous_period','previous_kind')}
        alternative=original['actual'];conflict=alternative is not None and abs(Decimal(str(alternative))-Decimal(row['value']))>Decimal('0.05')
        prior=period_before(period,measure['frequency']);previous=row['previous']
        mixed=previous is None and measure.get('previous') is not None and measure.get('previous_period')==prior and measure.get('previous_kind')=='previous_period'
        proof=dict(source=source.SOURCE,source_url=doc['source_url'],document_id=str(doc['id']),raw_hash=doc['raw_hash'],retrieved_at=stamp.isoformat(),
                   document_published_at=meta['announced_at'],vintage_date=point['vintage_date'],version='captured_snapshot',observation_period=period,
                   original_title=meta['title'],method=row['method'],precision=row['precision'],raw_published_value=row['value'],field=row['field'],unit=row['unit'],estimate_stage=stage)
        result.update(actual=float(Decimal(row['value'])),previous=float(Decimal(previous)) if previous is not None else measure['previous'] if mixed else None,
            reference_period=period,period_provenance=dict(source_url=doc['source_url'],report_url=doc['source_url'],reference_period=period,estimate_stage=stage,binding_method='official_bea_document',retrieved_at=stamp.isoformat()),
            previous_period=prior,previous_kind='previous_period',data_version='official_release',previous_data_version='official_release' if previous is not None else measure.get('previous_data_version') if mixed else None,
            actual_provenance=proof,previous_provenance={**proof,'observation_period':prior,'raw_published_value':previous} if previous is not None else measure.get('previous_provenance') if mixed else None,
            source_url=doc['source_url'],selected_source=source.SOURCE,published_precision=row['precision'],previous_precision=row['precision'] if previous is not None else None,
            result_status='available',mapping_status='confirmed',binding_method='official_bea_published_value',vintage_date=point['vintage_date'],forecast=None,consensus_status='not_integrated',
            missing_reason={'actual':None,'previous':None if previous is not None or mixed else 'bea_previous_not_in_document'},
            result_provenance=dict(source_url=doc['source_url'],reference_period=period,release_date=meta['release_date'],estimate_stage=stage),
            attribution=source.ATTRIBUTION,usage_rights=rights(meta['title'],doc['source_url']),fred_alternative=original,
            source_comparison='conflict' if conflict else 'consistent_with_rounding' if alternative is not None else 'bea_only',
            comparison_status='mixed_sources' if mixed else 'same_bea_document' if previous is not None else 'previous_unavailable',
            revision_confirmed=bool(meta.get('revisions')),
            document_versions=[dict(id=str(d['id']),source_url=d['source_url'],raw_hash=d['raw_hash'],retrieved_at=str(d['retrieved_at']),revisions=d['metadata'].get('revisions',[])) for d in state['documents'] if d['kind']==doc['kind']])
        for field in ('index_inputs','calculation_provenance','input_unit','transform_formula'):result.pop(field,None)
        return result
    return result


def apply(events,state,now):
    for event in events:
        if event.get('release_id') in (53,54):event['measures']=[select(m,event,state,now) for m in event.get('measures',[])]
    return events


def overview(rows,connection,today,state=None):
    """Overlay only curated numerical readings; classification and MCI stay intact."""
    state=load_state(connection) if state is None else state;now=datetime.now(timezone.utc)
    for item in rows:
        sid,feature=item['series_id'],item['feature_name']
        if (sid,feature) not in source.MEASURES:continue
        candidates=[d for d in state['documents'] if d['metadata']['reference_period']<=str(today) and any((r['series_id'],r['feature_name'])==(sid,feature) for r in d['metadata']['readings'])]
        if not candidates:continue
        doc=max(candidates,key=lambda d:(d['metadata']['reference_period'],d['metadata']['release_date'],str(d['retrieved_at'])))
        meta=doc['metadata'];period=meta['reference_period']
        if item['current'] and item['current']['observation_date']>period:continue
        fake=dict(series_id=sid,feature_name=feature,reference_period=period,frequency=item['frequency'],actual=item['current']['value'] if item['current'] and item['current']['observation_date']==period else None,
                  previous=item['previous']['value'] if item['previous'] else None,previous_period=item['expected_previous_observation_date'],previous_kind='previous_period',source_url=item.get('source_url'),data_version='current_vintage')
        selected=select(fake,dict(release_id=meta['release_id'],release_date=meta['release_date'],estimate_stage=meta['estimate_stage']),state,now)
        if selected['selected_source']!=source.SOURCE:continue
        def point(kind):
            if selected[kind] is None:return None
            proof=selected.get(kind+'_provenance') or {}
            return dict(value=selected[kind],observation_date=period if kind=='actual' else selected['previous_period'],feature_as_of_date=None,
                        **{k:proof[k] for k in ('source_url','document_published_at','retrieved_at','raw_hash') if k in proof},published_precision=selected['published_precision'] if kind=='actual' else selected['previous_precision'])
        item.update(current=point('actual'),previous=point('previous'),source_url=selected['source_url'],attribution=source.ATTRIBUTION,bea_direct=selected,
                    three_periods_ago=None,
                    latest_stored_observation_date=period,expected_previous_observation_date=selected['previous_period'],
                    change=round(selected['actual']-selected['previous'],1) if selected['comparison_status']=='same_bea_document' else None)
        if item.get('context_yoy'):
            annual=select({**fake,'feature_name':'yoy'},dict(release_id=meta['release_id'],release_date=meta['release_date'],estimate_stage=None),state,now)
            if annual.get('selected_source')==source.SOURCE:
                item['context_yoy']=dict(current=dict(value=annual['actual'],observation_date=period,feature_as_of_date=None,published_precision=1),previous=None,three_periods_ago=None)
            else:
                selected['annual_context_source']='fred'
    return rows
