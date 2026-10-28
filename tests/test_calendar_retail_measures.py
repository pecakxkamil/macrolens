"""Retail definitions, coherent component snapshots and calendar binding, offline."""
import copy
from datetime import datetime, timezone, date

import pandas as pd
import pytest

from app.analytics.retail_measures import (CONTROL_COMPONENTS, RETAIL_SERIES,
    control_change, expand_retail_evidence, validate_metadata)
from app.analytics.calendar_readings import bind_events
from app.analytics.features import calculate_features
from app.database.sync_series import load_series_config
from app.ingestion.sync_calendar_periods import parse_retail_schedule, parse_retail_report
from tests.test_calendar_agenda import event
from tests.test_calendar_key_publications import RETAIL, RETAIL_REPORT, STAMP


def points():
    return {sid:[dict(observation_date=f'2026-{m:02d}-01', value=value,
                     source='fred_snapshot', vintage_date='2026-10-28')
                 for m, value in zip([6,7,8,9],values)]
            for sid,values in {'RSAFS':[980,990,1000,1100],
              'RSFSXMV':[500,510,520,530], 'RSGASS':[50,50,50,50],
              'RSBMGESD':[40,40,40,40], 'RSFSDP':[30,30,30,30]}.items()}


def bound(day='2026-10-15', current=None, updates=None, evidence=None):
    proof=parse_retail_schedule(RETAIL,'retail',STAMP)[0 if day=='2026-10-15' else 1]
    return bind_events([event(9,day,RETAIL_SERIES)],{},current or points(),
        datetime(2026,10,28,tzinfo=timezone.utc), evidence or {'periods':[proof],
        'results':[parse_retail_report(RETAIL_REPORT,'report',STAMP)]},
        updates if updates is not None else dict.fromkeys(RETAIL_SERIES,'2026-10-15'))[0]


def test_reviewed_ex_autos_is_a_monthly_sa_level_not_a_percent_or_nsa_series():
    spec=load_series_config()['RSFSXMV']
    assert spec['seasonal_adjustment']=='Seasonally Adjusted'
    assert spec['unit']=='millions of dollars' and spec['frequency']=='monthly'
    assert spec['transformations']==['mom']
    metadata=dict(id='RSFSXMV',title=spec['name'],seasonal_adjustment='Seasonally Adjusted',
                  frequency='Monthly',units='Millions of Dollars')
    validate_metadata('RSFSXMV',metadata)
    for field,value in [('seasonal_adjustment','Not Seasonally Adjusted'),('units','Percent'),
                        ('frequency','Quarterly'),('id','RSAFS'),('title','Wrong category')]:
        with pytest.raises(ValueError):validate_metadata('RSFSXMV',{**metadata,field:value})


@pytest.mark.parametrize('prior,current,expected',[(100,101,1),(100,100,0),(100,0,-100),(0,10,None),(-1,10,None)])
def test_ex_autos_shared_mom_formula_and_invalid_denominators(prior,current,expected):
    frame=pd.DataFrame(dict(observation_date=[date(2026,8,1),date(2026,9,1)],value=[prior,current]))
    result=calculate_features('RSFSXMV',frame,['mom'])
    if expected is None:assert result.empty
    else:assert result.iloc[-1].feature_value==pytest.approx(expected)


def test_monthly_transform_never_compresses_missing_months():
    frame=pd.DataFrame(dict(observation_date=[date(2026,7,1),date(2026,9,1)],value=[100,110]))
    assert calculate_features('RSFSXMV',frame,['mom']).empty


def test_control_definition_subtracts_each_disjoint_exclusion_once_from_ex_autos():
    assert CONTROL_COMPONENTS==dict(RSFSXMV=1,RSGASS=-1,RSBMGESD=-1,RSFSDP=-1)
    value,reason,proof=control_change(points(),'2026-09-01')
    assert reason is None and value==pytest.approx((410/400-1)*100)
    assert proof['current']['level']==410 and proof['previous']['level']==400
    assert proof['current']['components']['RSFSXMV']==530


@pytest.mark.parametrize('fault,reason',[
    ('missing','retail_component_missing'),('previous_month','retail_component_missing'),
    ('period','retail_component_missing'),('vintage','retail_component_vintage_mismatch'),
    ('source','retail_component_vintage_mismatch'),('cross_month_vintage','retail_component_vintage_mismatch'),
    ('invalid','retail_component_invalid'),('denominator','retail_denominator_invalid')])
def test_incomplete_or_mixed_component_data_is_never_approximated(fault,reason):
    current=points()
    if fault=='missing':del current['RSGASS']
    if fault=='previous_month':current['RSGASS'].pop(2)
    if fault=='period':current['RSGASS'][-1]['observation_date']='2026-10-01'
    if fault=='vintage':current['RSGASS'][-1]['vintage_date']='2026-10-27'
    if fault=='source':current['RSGASS'][-1]['source']='alfred'
    if fault=='cross_month_vintage':
        for sid in CONTROL_COMPONENTS:current[sid][2]['vintage_date']='2026-10-27'
    if fault=='invalid':current['RSGASS'][-1]['value']=float('nan')
    if fault=='denominator':current['RSFSXMV'][2]['value']=120
    value,actual_reason,_=control_change(current,'2026-09-01')
    assert value is None and actual_reason==reason


def test_one_report_three_measures_with_correct_months_previous_and_no_consensus():
    result=bound();measures=result['measures']
    assert [m['series_id'] for m in measures]==['RSAFS','RSFSXMV','RETAIL_CONTROL']
    assert all(m['reference_period']=='2026-09-01' and m['previous_period']=='2026-08-01' for m in measures)
    assert all(m['forecast'] is None and m['consensus_status']=='not_integrated' and m['unit']=='percent' for m in measures)
    assert measures[1]['actual']==pytest.approx((530/520-1)*100)
    assert measures[2]['actual']==pytest.approx((410/400-1)*100)
    assert measures[2]['previous']==pytest.approx((400/390-1)*100)
    assert measures[2]['data_version']=='current_vintage'


def test_future_actual_stays_empty_even_if_a_future_point_is_stored():
    data=points()
    for sid in data:data[sid].append(dict(data[sid][-1],observation_date='2026-10-01'))
    measures=bound('2026-11-17',data)['measures']
    assert all(m['actual'] is None and m['previous'] is not None for m in measures)
    assert all(m['forecast'] is None for m in measures)


def test_time_or_provider_timestamp_cannot_turn_an_old_snapshot_into_new_actual():
    data=points()
    for sid in data:
        for p in data[sid]:p['vintage_date']='2026-10-14'
    assert all(m['actual'] is None for m in bound(current=data)['measures'])
    evidence={'periods':parse_retail_schedule(RETAIL,'retail',STAMP)}
    assert all(m['actual'] is None for m in bound(evidence=evidence)['measures'])


def test_one_stale_component_hides_control_without_hiding_ex_autos():
    updates=dict.fromkeys(RETAIL_SERIES,'2026-10-15');updates['RSGASS']='2026-10-14'
    measures=bound(updates=updates)['measures']
    assert measures[1]['actual'] is not None and measures[2]['actual'] is None


def test_revision_recalculates_control_without_inventing_historical_first_prints():
    data=points();before=bound(current=data)['measures'][-1]
    data['RSGASS'][-1]['value']=55
    after=bound(current=data)['measures'][-1]
    assert after['actual']!=before['actual'] and after['data_version']=='current_vintage'
    assert not after['revision_confirmed']


def test_legacy_evidence_is_extended_only_for_advance_and_without_mutation():
    proof=parse_retail_schedule(RETAIL,'retail',STAMP)[0]
    proof['series_ids']=['RSAFS'];full={**proof,'estimate_stage':'full'}
    original={'periods':[proof,full]};expanded=expand_retail_evidence(original)
    assert expanded['periods'][0]['series_ids']==list(RETAIL_SERIES)
    assert expanded['periods'][1]['series_ids']==['RSAFS']
    assert original['periods'][0]['series_ids']==['RSAFS']
    assert expand_retail_evidence(expanded)==expanded


def test_adding_retail_measures_preserves_existing_headline_result():
    result=bound()['measures'][0]
    e=event(9,'2026-10-15',('RSAFS',))
    evidence={'periods':parse_retail_schedule(RETAIL,'retail',STAMP),
              'results':[parse_retail_report(RETAIL_REPORT,'report',STAMP)]}
    old=bind_events([e],{},points(),datetime(2026,10,28,tzinfo=timezone.utc),evidence,
                    dict.fromkeys(RETAIL_SERIES,'2026-10-15'))[0]['measures'][0]
    assert old==result


def test_full_mrts_stage_does_not_receive_advance_measures():
    proof=parse_retail_schedule(RETAIL,'retail',STAMP)[0]
    proof.update(estimate_stage='full',series_ids=['RSAFS'])
    assert [m['series_id'] for m in bound(evidence={'periods':[proof]})['measures']]==['RSAFS']


def test_historical_report_header_confirms_its_own_month_and_clock():
    from app.ingestion.sync_calendar_periods import parse_retail_pdf_text
    text='FOR RELEASE AT 8:30 AM EDT, WEDNESDAY, SEPTEMBER 16, 2026 ADVANCE MONTHLY SALES FOR RETAIL AND FOOD SERVICES, AUGUST 2026 Advance estimates of U.S. retail and food services sales for August 2026'
    proof=parse_retail_pdf_text(text,'official.pdf',STAMP)
    assert proof['release_date']=='2026-09-16' and proof['reference_period']=='2026-08-01'
    assert proof['release_time']=='08:30:00' and proof['estimate_stage']=='advance'
    for invalid in [text.replace('AUGUST 2026','JULY 2026'),text.replace('EDT','EST'),text.replace('ADVANCE MONTHLY','MONTHLY')]:
        with pytest.raises(ValueError):parse_retail_pdf_text(invalid,'official.pdf',STAMP)


@pytest.mark.parametrize('changed,mixed,expected',[(False,False,0),(True,False,3),(False,True,4)])
def test_coordinator_aligns_only_changed_or_mixed_retail_snapshots(monkeypatch,changed,mixed,expected):
    from contextlib import nullcontext
    from app.analytics import overview_refresh as refresh
    class Connection:
        def transaction(self):return nullcontext()
    versions={f'fred:{sid}':dict(last_updated='2026-10-15',local_signature=[6,'stored','2026-10-28']) for sid in CONTROL_COMPONENTS}
    results=[dict(resource=key,status='success',outcome='unchanged') for key in versions]
    if changed:results[0]['outcome']='updated'
    if mixed:next(iter(versions.values()))['local_signature'][-1]='2026-10-27'
    calls=[]
    def fake(sid,prior,local,connection,now):
        assert prior['last_updated'] is None
        calls.append(sid)
        return versions['fred:'+sid],dict(resource='fred:'+sid,status='success',outcome='updated')
    monkeypatch.setattr(refresh,'refresh_fred',fake)
    refresh.align_retail_snapshots(Connection(),versions,results,{},datetime(2026,10,28,tzinfo=timezone.utc))
    assert len(calls)==expected and len(results)==4


@pytest.mark.parametrize('month,ex_autos,control',[
    (5,.9781136647,.8616792786),(6,-.2645266405,.2286452201),
    (7,-.1023747219,-.2261025975),(8,1.4306562924,1.1897919447),
    (9,.8988040954,.1356213811)])
def test_reviewed_current_census_levels_reproduce_both_measures(month,ex_autos,control):
    # Bounded April–September 2026 SA levels, independently matched to the four
    # Census adv44Y72/adv44700/adv44400/adv72200 tables on 28 October.
    levels={'RSFSXMV':[587764,593513,591943,591337,599797,605188],
            'RSGASS':[63594,65205,61634,61509,63950,68021],
            'RSBMGESD':[43909,43841,44366,44233,44323,44077],
            'RSFSDP':[88700,89532,90105,90652,91882,92906]}
    current={sid:[dict(observation_date=f'2026-{m:02d}-01',value=value,
                      source='fred_snapshot',vintage_date='2026-10-28')
                  for m,value in enumerate(values,4)] for sid,values in levels.items()}
    from app.analytics.calendar_readings import value_at
    period=f'2026-{month:02d}-01'
    assert value_at('RSFSXMV','mom',current['RSFSXMV'],period,'monthly')==pytest.approx(ex_autos)
    assert control_change(current,period)[0]==pytest.approx(control)


@pytest.mark.parametrize('sid',list(CONTROL_COMPONENTS))
def test_existing_ingester_reuses_retail_observation_keys_on_reimport(monkeypatch,tmp_path,sid):
    from app.ingestion import ingest_series as ingestion
    stored={};captures=[]
    class Cursor:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,sql,params):
            assert 'ON CONFLICT (series_id, observation_date, vintage_date) DO UPDATE' in sql
            stored[(params['series_id'],params['observation_date'],params['vintage_date'])]=params['value']
    class Connection:
        def cursor(self):return Cursor()
        def commit(self):pass
        def rollback(self):pass
        def close(self):pass
    def capture(series,payload):
        assert series==sid
        captures.append(copy.deepcopy(payload))
        return tmp_path/'snapshot.json'
    monkeypatch.setattr(ingestion,'get_connection',Connection)
    monkeypatch.setattr(ingestion,'save_raw_response',capture)
    payload={'observations':[dict(date='2026-08-01',realtime_start='2026-10-28',value='100'),
                             dict(date='2026-09-01',realtime_start='2026-10-28',value='101')]}
    ingestion._ingest_series(sid,response_data=payload)
    ingestion._ingest_series(sid,response_data=payload)
    assert len(stored)==2 and len(captures)==2
    payload['observations'][-1]['value']='102'
    ingestion._ingest_series(sid,response_data=payload)
    assert len(stored)==2 and stored[(sid,date(2026,9,1),date(2026,10,28))]==102
    assert captures[0]['observations'][-1]['value']=='101'
