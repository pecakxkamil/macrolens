"""Explicit release/measure bindings and read-only, date-level result evidence.

Release dates alone never identify a reference period. Publisher schedules,
explicit reports and stored ALFRED links supply independently recorded evidence.
Rendering never contacts providers or creates observation vintages.
"""
import copy
import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pandas as pd
from app.analytics.features import calculate_features
from app.analytics.employment_measures import EMPLOYMENT_LEVELS, level_reason as employment_level_reason, expand_employment_evidence, availability_reason as employment_availability_reason, decorate as decorate_employment
from app.analytics.ppi_measures import NEW_PPI_SERIES, PPI_LABELS, inputs as ppi_inputs, expand_ppi_evidence, availability_reason as ppi_availability_reason, decorate_and_fold
from app.analytics.point_in_time import select_as_of
from app.analytics.calendar_evidence import read_evidence, period_evidence

# FRED release IDs + exact configured series IDs, never fuzzy release-name joins.
# Shared monthly reports: BLS Employment Situation/CPI, BEA Income and Outlays,
# Census New Residential Construction. Weekly claims have DIFFERENT periods.
SPECS = {
 50:[('PAYEMS','monthly_change','Nonfarm payrolls (NFP)','thousand jobs'),('UNRATE','raw','Unemployment rate','percent'),('CES0500000003','mom','Hourly earnings MoM','percent')]+[(sid,'raw',spec[0],spec[1]) for sid,spec in EMPLOYMENT_LEVELS.items()],
 10:[('CPIAUCSL','mom','CPI MoM','percent'),('CPIAUCSL','yoy','Headline CPI YoY','percent'),('CPILFESL','mom','Core CPI MoM','percent'),('CPILFESL','yoy','Core CPI YoY','percent')],
 54:[('PCEPI','mom','Headline PCE MoM','percent'),('PCEPILFE','mom','Core PCE MoM','percent'),('PCEPILFE','yoy','Core PCE YoY','percent'),('DSPIC96','mom','Real disposable income MoM','percent'),('PCEC96','mom','Real consumption MoM','percent'),('PSAVERT','raw','Saving rate','percent')],
 27:[('HOUST','raw','Housing starts','thousand homes/year (SAAR)'),('PERMIT','raw','Building permits','thousand homes/year (SAAR)')],
 53:[('GDPC1','qoq_annualized','Real GDP QoQ, annualized','percent')],
 180:[('ICSA','raw','Initial jobless claims','claims'),('CCSA','raw','Continuing jobless claims','claims')],
 9:[('RSAFS','mom','Nominal retail sales MoM','percent'),('RSFSXMV','mom','Retail Sales ex Autos MoM','percent')],46:[('PPIFIS','mom','Producer inflation PPI MoM','percent')]+[(sid,'mom' if sid in ('PPIFES','WPSFD49116') else 'yoy',PPI_LABELS[sid],'percent') for sid in ('PPIFES','WPSFD49116','PPIFID','PPICOR','WPUFD49116')],
 13:[('INDPRO','mom','Industrial production MoM','percent'),('TCU','raw','Capacity utilization','percent')],
 192:[('JTSJOL','raw','JOLTS job openings','thousand openings')],97:[('HSN1F','raw','New home sales','thousand homes/year (SAAR)')],
 190:[('MORTGAGE30US','raw','30Y mortgage rate','percent')],219:[('CFNAI','raw','CFNAI','index points')],221:[('NFCI','raw','NFCI','index points')],
 11:[('ECIALLCIV','qoq','Employment cost index QoQ','percent')],95:[('DGORDER','mom','Durable goods orders MoM','percent')],
 18:[('DFF','raw','Effective Fed Funds Rate','percent'),('DGS2','raw','2Y Treasury yield','percent'),('DGS10','raw','10Y Treasury yield','percent'),('DFII10','raw','10Y real yield','percent')],
}
SHARED_MONTH = {50,10,54,27}
DESCRIPTIONS = {50:'Monthly payroll employment, unemployment and hourly earnings.',10:'Monthly consumer prices, including headline and core measures.',54:'Personal income, consumption and PCE prices.',27:'Residential housing starts and building permits, at seasonally adjusted annualized rates.',53:'Quarterly real GDP estimates; a later estimate can concern the same quarter.',180:'Weekly initial and continued unemployment insurance claims, with separate reference weeks.'}
DEFINITIONS = {'monthly_change':'Change from the preceding calendar month, in the original unit.','mom':'Percentage change from the preceding calendar month.','yoy':'Percentage change from the same month one year earlier.','qoq':'Percentage change from the preceding quarter.','qoq_annualized':'Quarterly real growth expressed at an annualized rate.','raw':'Stored level for the reference observation period.'}


def finite(value):
    try:return float(value) if math.isfinite(float(value)) else None
    except (TypeError,ValueError):return None


def period_before(day,frequency):
    day=date.fromisoformat(str(day))
    if frequency=='weekly':return str(day-timedelta(days=7))
    if frequency in ('monthly','quarterly'):
        months=day.year*12+day.month-1-(3 if frequency=='quarterly' else 1)
        return str(date(months//12,months%12+1,1))
    return None


def value_at(sid,feature,points,period,frequency):
    if not period:return None
    if sid in EMPLOYMENT_LEVELS and employment_level_reason(sid,points,period):return None
    if sid in NEW_PPI_SERIES and ppi_inputs(points,period,feature)[1]:return None
    values={str(p['observation_date']):finite(p['value']) for p in points}
    if feature=='raw':return values.get(period)
    if not values:return None
    # Reuse pure v1 formulas on an explicit calendar grid; never compress holes.
    grid=pd.date_range(min(values),max(values),freq='QS' if frequency=='quarterly' else 'MS')
    frame=pd.DataFrame([{'observation_date':d.date(),'value':values.get(str(d.date()))} for d in grid])
    calculated=calculate_features(sid,frame,[feature])
    row=calculated[(calculated.feature_name==feature)&(calculated.observation_date.astype(str)==period)]
    return finite(row.iloc[0].feature_value) if len(row) else None


def linked_period(rows,event_day,sid):
    known=select_as_of(rows,date.fromisoformat(event_day))
    valid=[p for p in known if finite(p['value']) is not None]
    if not valid:return None
    latest=max(str(p['observation_date']) for p in valid)
    if not any(str(p['observation_date'])==latest and str(p['vintage_date'])==event_day and finite(p['value']) is not None for p in rows):return None
    first=min(str(p['vintage_date']) for p in rows if str(p['observation_date'])==latest and finite(p['value']) is not None)
    # GDP may publish another estimate of the SAME quarter; other releases need
    # evidence of a newly introduced period rather than a historical revision.
    return latest if first==event_day or sid=='GDPC1' else None


def bind_events(events,panel,current,now,evidence=None,provider_updates=None,ism_documents=None):
    from app.analytics.retail_measures import expand_retail_evidence, append_control, EX_AUTOS_DEFINITION
    evidence=expand_employment_evidence(expand_ppi_evidence(expand_retail_evidence(evidence or {})))
    from app.ingestion.bls_schedule import select_records
    _,bls_conflicts=select_records(evidence.get('periods',[]))
    events=copy.deepcopy(events)
    for event in events:
        if event.get('expects_numeric_result') is False and event.get('estimate_stage')=='annual_revision':
            event['measures']=[]
            continue
        if event.get('event_type') in ('fomc_press_conference','fomc_minutes','fomc_sep'):
            event.update(expects_numeric_result=False, measures=[])
            continue
        if event.get('event_type')=='ism_report':
            from app.analytics.ism_calendar import bind_measure
            event.update(description='Monthly ISM survey of US business activity.',expects_numeric_result=True,
                measures=[bind_measure(event,ism_documents or [],now)])
            continue
        day=str(event['release_date']);rid=event['release_id'];metadata={s['series_id']:s for s in event['series']}
        specs=[s for s in SPECS.get(rid,[]) if s[0] in metadata]
        if not specs:specs=[(s['series_id'],'raw',s['short_name'] or s['name'],s['unit']) for s in event['series']]
        official=[r for r in evidence.get('periods',[]) if r['release_id']==rid and r['release_date']==day]
        if rid==9 and (event.get('estimate_stage') not in (None,'advance') or (official and all(r.get('estimate_stage') not in (None,'advance') for r in official))):
            specs=[s for s in specs if s[0]=='RSAFS']
        if rid==27 and official:
            # Census's later revised-permits release is not another starts report.
            permitted={sid for r in official for sid in r['series_ids']}
            specs=[s for s in specs if s[0] in permitted]
        instant=event.get('release_datetime_utc')
        future=(datetime.fromisoformat(instant.replace('Z','+00:00'))>now) if instant else day>now.astimezone(ZoneInfo('America/New_York')).date().isoformat()
        links={sid:linked_period(panel.get(sid,[]),day,sid) for sid,_,_,_ in specs} if not future and rid in SPECS else {}
        shared=set(p for p in links.values() if p) if rid in SHARED_MONTH else set()
        event['description']=DESCRIPTIONS.get(rid,'Stored publication affecting the listed indicators.')
        event['expects_numeric_result']=bool(specs)
        event['measures']=[]
        for sid,feature,label,unit in specs:
            frequency=metadata[sid]['frequency'];period=links.get(sid)
            binding='alfred_release_date' if period else None
            if not period and len(shared)==1 and frequency=='monthly':period=next(iter(shared));binding='shared_report_month'
            proof=period_evidence(evidence,rid,day,sid)
            if proof:
                period=proof['reference_period'];binding=proof['binding_method']
            elif len({r['reference_period'] for r in official if sid in r['series_ids']})>1 or any(
                c['resolution']=='unresolved' and any(r['release_id']==rid and r['release_date']==day and sid in r['series_ids'] for r in c['candidates']) for c in bls_conflicts):
                period=None;binding=None
            known=select_as_of(panel.get(sid,[]),date.fromisoformat(day)) if not future else []
            current_points=current.get(sid,[])
            actual=value_at(sid,feature,known,period,frequency) if not future else None
            vintage=next((p for p in known if str(p['observation_date'])==period),None)
            version='stored_date_vintage' if actual is not None else None
            if actual is None and period and not future:
                actual=value_at(sid,feature,current_points,period,frequency)
                if actual is not None:version='current_vintage';vintage=None
            unconfirmed_result=False
            revised_reason=None
            if version=='current_vintage' and actual is not None and provider_updates is not None:
                # Re-reading an old snapshot after the scheduled hour does not
                # confirm that a later estimate/revision has actually appeared.
                updated=provider_updates.get(sid) or ''
                if not updated or updated[:10]<day:
                    actual=None;version=None;unconfirmed_result=True
            stage=proof.get('estimate_stage') if proof else None
            requires_report=(rid in (9,13,95) or (rid==53 and stage in ('second','third','updated')) or (rid==27 and stage=='revised_permits'))
            receipt=next((r for r in evidence.get('results',[]) if r['release_id']==rid and sid in r['series_ids']
                and r['release_date']==day and r['reference_period']==period and r.get('estimate_stage')==stage
                and (not r.get('announced_at') or datetime.fromisoformat(r['announced_at'])<=now)),None)
            new_alfred=vintage and str(vintage.get('vintage_date',''))==day
            if not future and period and rid==192 and not new_alfred:
                # JOLTS has no report-result parser: a newly fetched value for
                # its confirmed month can establish availability, an old point
                # plus a changed provider timestamp cannot.
                fresh=any(str(p['observation_date'])==period and p.get('vintage_date') and str(p['vintage_date'])>=day for p in current_points)
                if fresh and ((provider_updates or {}).get(sid) or '')[:10]>=day:
                    actual=value_at(sid,feature,current_points,period,frequency)
                    version='current_vintage' if actual is not None else None;vintage=None
                else:actual=None;version=None;unconfirmed_result=True
            if not future and period and requires_report and not new_alfred:
                # A provider timestamp, or an old same-period ALFRED value, is
                # not evidence that this stage of the publication occurred.
                updated=(provider_updates or {}).get(sid) or ''
                fresh=next((p for p in current_points if str(p['observation_date'])==period and p.get('vintage_date') and str(p['vintage_date'])>=day),None)
                if receipt and fresh and updated[:10]>=day:
                    actual=value_at(sid,feature,current_points,period,frequency)
                    version='current_vintage' if actual is not None else None;vintage=None
                else:
                    actual=None;version=None;unconfirmed_result=True
                if stage=='revised_permits' and actual is None:
                    revised_reason='revised_permits_provider_pending' if receipt else 'publication_stage_unconfirmed'
            if stage=='revised_permits' and receipt and receipt.get('reported_value') is not None and actual is not None and actual!=finite(receipt['reported_value']):
                actual=None;version=None;vintage=None;unconfirmed_result=True;revised_reason='revised_permits_provider_pending'
            ppi_reason=None
            if rid==46 and sid in NEW_PPI_SERIES and not future:
                ppi_reason=ppi_availability_reason(sid,current_points,period,event,proof,provider_updates)
                if ppi_reason:actual=None;version=None;vintage=None
            employment_reason=None
            if rid==50 and sid in EMPLOYMENT_LEVELS and not future:
                employment_reason=employment_availability_reason(sid,current_points,period,event,proof,provider_updates)
                if employment_reason:actual=None;version=None;vintage=None
            previous_period=period_before(period,frequency) if period else None
            previous_kind='previous_period'
            prior_snapshot=select_as_of(panel.get(sid,[]),date.fromisoformat(day)-timedelta(days=1))
            later_estimate=proof and proof.get('estimate_stage') in ('second','third','updated')
            if sid=='GDPC1' and period and (later_estimate or (not proof and any(str(p['observation_date'])==period and finite(p['value']) is not None for p in prior_snapshot))):
                previous_period=period;previous_kind='previous_estimate'
                previous=value_at(sid,feature,prior_snapshot,period,frequency)
            else:previous=value_at(sid,feature,known if version=='stored_date_vintage' else current_points,previous_period,frequency)
            previous_version=('stored_date_vintage' if previous_kind=='previous_estimate' or version=='stored_date_vintage' else 'current_vintage') if previous is not None else None
            before_value=value_at(sid,feature,prior_snapshot,period,frequency) if previous_kind=='previous_estimate' else None
            revised=previous_kind=='previous_estimate' and actual is not None and before_value is not None and actual!=before_value
            reason=lambda value,ref,points: None if value is not None else 'reference_period_unconfirmed' if not ref else 'observation_missing' if not any(str(p['observation_date'])==ref and finite(p['value']) is not None for p in points) else 'transformation_dependency_missing'
            event['measures'].append({'series_id':sid,'label':label,'feature_name':feature,'frequency':frequency,'unit':unit,
                'definition':EX_AUTOS_DEFINITION if sid=='RSFSXMV' else DEFINITIONS[feature],'reference_period':period,'previous_period':previous_period,'previous_kind':previous_kind,
                'actual':actual,'previous':previous,'forecast':None,'consensus_status':'not_integrated',
                'data_version':version,'previous_data_version':previous_version,'revision_confirmed':revised,'binding_method':binding,
                'vintage_date':str(vintage['vintage_date']) if vintage else None,'realtime_end':str(vintage['realtime_end']) if vintage and vintage.get('realtime_end') else None,
                'result_status':'available' if actual is not None else 'scheduled' if future else 'awaiting_data',
                'mapping_status':'confirmed' if period else 'reference_period_unconfirmed',
                'period_status_reason':None if period else 'claims_weeks_not_confirmed' if rid==180 else 'release_mapping_not_supported' if rid not in SPECS else 'publisher_schedule_no_matching_period',
                'period_provenance':{**proof,'source_check':next((r for r in evidence.get('checks',[]) if r['source_url'] in (proof['source_url'],proof.get('schedule_source_url'))),None)} if proof else ({'binding_method':binding,'reference_period':period,'source_url':f'https://alfred.stlouisfed.org/series?seid={sid}'} if period else None),
                'result_provenance':receipt if actual is not None else None,
                'publication_provenance':receipt if stage=='revised_permits' else None,
                'actual_provenance':provenance(sid,period,version,next((p for p in current_points if str(p['observation_date'])==period),None) if version=='current_vintage' else vintage,str(now.date()) if version=='current_vintage' else day) if actual is not None else None,
                'previous_provenance':provenance(sid,previous_period,previous_version,next((p for p in (prior_snapshot if previous_kind=='previous_estimate' else known if previous_version=='stored_date_vintage' else current_points) if str(p['observation_date'])==previous_period),None),str(now.date()) if previous_version=='current_vintage' else day) if previous is not None else None,
                'missing_reason':{'actual':employment_reason or ppi_reason or revised_reason or ('publisher_result_not_confirmed' if unconfirmed_result else 'not_yet_published' if future and period else reason(actual,period,current_points)),'previous':reason(previous,previous_period,current_points)},
                'source_url':f'https://fred.stlouisfed.org/series/{sid}'})
        if rid==50:
            decorate_employment(event,current)
        if rid==46:
            decorate_and_fold(event,current)
        if rid==9:
            append_control(event,current,provider_updates)
        if event.get('event_type')=='fomc_decision':
            event['expects_numeric_result']=True
            event['measures']=[policy_measure(event,evidence.get('decisions',[]),now)]
    return events


def provenance(sid,period,version,point,as_of):
    return dict(source_url=f'https://fred.stlouisfed.org/series/{sid}',observation_period=period,
                version=version,vintage_date=str(point['vintage_date']) if point and point.get('vintage_date') else None,as_of=as_of,
                source=point.get('source') if point else None)


def policy_measure(event,decisions,now):
    day=str(event['release_date'])
    today=str(now.astimezone(ZoneInfo('America/New_York')).date())
    eligible=[r for r in decisions if r['release_date']<=today and
        (datetime.fromisoformat(r['announced_at'])<=now if r.get('announced_at') else
         datetime.fromisoformat(r['retrieved_at'])<=now if r.get('retrieved_at') else r['release_date']<today)]
    actual=next((r for r in eligible if r['release_date']==day),None)
    previous=max((r for r in eligible if r['release_date']<day),key=lambda r:r['release_date'],default=None)
    bounds=lambda r:[r['lower'],r['upper']] if r else None
    return dict(series_id='DFEDTARL/DFEDTARU',label='Fed target range',feature_name='target_range',frequency='decision',unit='percent',
        definition='Officially announced target range; the scalar comparison uses the lower bound only when both bounds move equally.',
        reference_period=day,previous_period=previous['release_date'] if previous else None,previous_kind='previous_decision',
        actual=actual['lower'] if actual else None,previous=previous['lower'] if previous else None,actual_range=bounds(actual),previous_range=bounds(previous),
        forecast=None,consensus_status='not_integrated',data_version='official_release' if actual else None,previous_data_version='official_release' if previous else None,
        binding_method='official_decision',mapping_status='confirmed',revision_confirmed=False,vintage_date=None,realtime_end=None,
        effective_date=actual['effective_date'] if actual else None,previous_effective_date=previous['effective_date'] if previous else None,
        actual_provenance=actual,previous_provenance=previous,period_provenance={'source_url':event.get('source_link','https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'),'reference_period':day,'binding_method':'official_meeting_schedule'},
        missing_reason={'actual':None if actual else 'official_decision_not_available','previous':None if previous else 'official_prior_decision_not_available'},
        result_status='available' if actual else 'scheduled' if day>=str(now.date()) else 'awaiting_data',source_url=actual['source_url'] if actual else event.get('source_link','https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'))


def load_results(events,start,end,now,connection):
    from app.analytics.ism_calendar import load_documents
    ism_documents=load_documents(connection) if any(e.get('event_type')=='ism_report' for e in events) else []
    series=sorted({s['series_id'] for event in events if event.get('event_type')!='ism_report' for s in event['series']})
    panel=defaultdict(list);current=defaultdict(list);updates={}
    if series:
        with connection.cursor() as cursor:
            cursor.execute('''SELECT series_id,observation_date,vintage_date,value,realtime_end FROM observation_vintages
                WHERE source='alfred' AND series_id=ANY(%s) AND observation_date BETWEEN %s AND %s AND vintage_date<=%s
                ORDER BY series_id,vintage_date,observation_date''',(series,start-timedelta(days=465),end,min(end,now.date())))
            for sid,observed,vintage,value,expires in cursor.fetchall():
                panel[sid].append(dict(observation_date=str(observed),vintage_date=str(vintage),value=value,realtime_end=str(expires) if expires else None,source='alfred'))
            cursor.execute('''SELECT DISTINCT ON(series_id,observation_date) series_id,observation_date,CASE WHEN source='alfred' AND realtime_end<%s THEN NULL ELSE value END AS value,source,vintage_date FROM observation_vintages
                WHERE series_id=ANY(%s) AND observation_date BETWEEN %s AND %s AND vintage_date<=%s
                ORDER BY series_id,observation_date,vintage_date DESC,ingested_at DESC,id DESC''',(now.date(),series,start-timedelta(days=465),end,now.date()))
            for sid,observed,value,source,vintage in cursor.fetchall():current[sid].append(dict(observation_date=str(observed),value=value,source=source,vintage_date=str(vintage)))
            cursor.execute('''SELECT DISTINCT ON(resource) resource,scope->>'last_updated' FROM source_check_runs
                WHERE resource=ANY(%s) AND status='success' AND scope ? 'last_updated'
                ORDER BY resource,finished_at DESC''',(['fred:'+sid for sid in series],))
            updates={resource.split(':',1)[1]:updated for resource,updated in cursor.fetchall()}
    return bind_events(events,panel,current,now,read_evidence(),updates,ism_documents)
