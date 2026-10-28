"""Offline levels and independent release availability for CPS/CES."""
import copy
from datetime import datetime,timezone
import pytest
from app.analytics.calendar_readings import bind_events,value_at,SPECS
from app.analytics.employment_measures import EMPLOYMENT_LEVELS,NAMES,validate_metadata,expand_employment_evidence
from app.database.sync_series import load_series_config
from tests.test_calendar_agenda import event

NOW=datetime(2026,10,28,tzinfo=timezone.utc)
IDS=('PAYEMS','UNRATE','CES0500000003',*EMPLOYMENT_LEVELS)

def data():
    vals={'PAYEMS':[100,110,120,140,150],'UNRATE':[4,4,4.1,4.1,4.2],
          'CES0500000003':[35,35.1,35.2,35.3,35.4],
          'CIVPART':[61.8,61.5,61.4,61.6,61.8],'U6RATE':[8.1,7.9,7.9,7.7,7.6],
          'AWHAETP':[34.3,34.3,34.3,34.4,34.4]}
    return {s:[dict(observation_date=f'2026-{month:02}-01',value=v,vintage_date='2026-10-28',source='fred_snapshot') for month,v in zip(range(5,10),vv)] for s,vv in vals.items()}

def proof(day='2026-10-02',period='2026-09-01'):
    return {'periods':[dict(release_id=50,series_ids=['PAYEMS','UNRATE','CES0500000003'],release_date=day,reference_period=period,source_url='https://www.bls.gov/schedule/news_release/empsit.htm',binding_method='reviewed_official_schedule',retrieved_at='2026-10-01T12:00:00Z')]}

def bind(current=None,updates=None,evidence=None,day='2026-10-02'):
    return bind_events([event(50,day,IDS)],{},data() if current is None else current,NOW,
        proof() if evidence is None else evidence,dict.fromkeys(IDS,'2026-10-02 08:26:00-05') if updates is None else updates)[0]

@pytest.mark.parametrize('sid',EMPLOYMENT_LEVELS)
def test_exact_reviewed_metadata_and_existing_participation_catalog(sid):
    config=load_series_config();assert config[sid]['name']==NAMES[sid]
    assert config[sid]['unit']==EMPLOYMENT_LEVELS[sid][1]
    if sid=='CIVPART':assert config[sid]['transformations']==['level','change_3m','change_6m','moving_average_3m']
    else:assert config[sid]['transformations']==['level']
    m=dict(id=sid,title=NAMES[sid],frequency='Monthly',seasonal_adjustment='Seasonally Adjusted',units='Hours' if sid=='AWHAETP' else 'Percent')
    validate_metadata(sid,m)
    for key,value in [('id','UNEMPLOY'),('title','Production and Nonsupervisory Employees'),('units','Index'),('frequency','Weekly'),('seasonal_adjustment','Not Seasonally Adjusted')]:
        with pytest.raises(ValueError):validate_metadata(sid,{**m,key:value})

def test_one_report_six_ordered_measures_and_cps_ces_definitions():
    e=bind();assert [m['series_id'] for m in e['measures']]==list(IDS)
    rows=e['measures'][3:]
    assert [(m['actual'],m['previous']) for m in rows]==[(61.8,61.6),(7.6,7.7),(34.4,34.4)]
    assert [m['survey'] for m in rows]==['CPS','CPS','CES']
    assert rows[1]['source_series_id']=='LNS13327709' and 'divided by the civilian labor force plus people marginally attached' in rows[1]['definition']
    assert rows[2]['source_series_id']=='CES0500000002' and 'all employees' in rows[2]['definition']
    for m in rows:
        assert m['feature_name']=='raw' and m['data_version']=='current_vintage'
        assert m['reference_period']=='2026-09-01' and m['previous_period']=='2026-08-01'
        assert m['forecast'] is None and m['consensus_status']=='not_integrated'
        assert m['seasonal_adjustment']=='Seasonally Adjusted'

@pytest.mark.parametrize('sid',EMPLOYMENT_LEVELS)
@pytest.mark.parametrize('fault',['missing','negative','nan','source'])
def test_invalid_or_missing_levels_do_not_borrow_another_series(sid,fault):
    d=data()
    if fault=='missing':d[sid].pop()
    elif fault=='source':d[sid][-1]['source']='alfred'
    else:d[sid][-1]['value']=-1 if fault=='negative' else float('nan')
    rows=bind(current=d)['measures'];m=next(m for m in rows if m['series_id']==sid)
    assert m['actual'] is None and m['previous'] is not None
    assert all(m['actual'] is not None for m in rows[3:] if m['series_id']!=sid)

@pytest.mark.parametrize('sid',EMPLOYMENT_LEVELS)
def test_missing_previous_month_and_zero_level_are_not_replaced(sid):
    d=data();d[sid]=[p for p in d[sid] if p['observation_date']!='2026-08-01'];d[sid][-1]['value']=0
    m=next(m for m in bind(current=d)['measures'] if m['series_id']==sid)
    assert m['actual']==0 and m['previous'] is None

@pytest.mark.parametrize('sid',EMPLOYMENT_LEVELS)
def test_each_series_requires_its_own_freshness_after_publication(sid):
    updates=dict.fromkeys(IDS,'2026-10-02 08:26:00-05');updates[sid]='2026-10-01 08:26:00-05'
    rows=bind(updates=updates)['measures'][3:]
    assert [m['series_id'] for m in rows if m['actual'] is None]==[sid]
    d=data();d[sid][-1]['vintage_date']='2026-10-01'
    assert next(m for m in bind(current=d)['measures'] if m['series_id']==sid)['actual'] is None

def test_time_or_timestamp_alone_without_period_or_new_observation_is_insufficient():
    assert all(m['actual'] is None for m in bind(evidence={})['measures'][3:])
    updates=dict.fromkeys(IDS,'2026-10-02 06:00:00-05')
    assert all(m['actual'] is None for m in bind(updates=updates)['measures'][3:])

def test_future_actual_forecast_and_previous_month():
    d=data()
    for sid in IDS:d[sid].append(dict(d[sid][-1],observation_date='2026-10-01'))
    rows=bind(d,evidence=proof('2026-11-06','2026-10-01'),day='2026-11-06')['measures'][3:]
    for m in rows:
        assert m['actual'] is None and m['forecast'] is None and m['previous'] is not None
        assert m['previous_period']=='2026-09-01' and m['missing_reason']['actual']=='not_yet_published'

def test_elapsed_release_without_new_report_month_stays_empty():
    rows=bind_events([event(50,'2026-11-06',IDS)],{},data(),datetime(2026,11,7,tzinfo=timezone.utc),
        proof('2026-11-06','2026-10-01'),dict.fromkeys(IDS,'2026-11-06 09:00:00-05'))[0]['measures'][3:]
    assert all(m['actual'] is None and m['previous'] is not None for m in rows)

def test_schedule_projection_keeps_original_publisher_receipt_and_all_six_series():
    from datetime import date
    from app.analytics.release_calendar import apply_bls_schedule
    p=proof();original=copy.deepcopy(p);template={**event(50,'2026-10-02',IDS),'importance':'high'}
    events={}
    apply_bls_schedule(events,{50:template},p,date(2026,10,1),date(2026,10,31))
    e=next(iter(events.values()))
    assert [s['series_id'] for s in e['series']]==list(IDS)
    assert e['schedule_provenance']==original['periods'][0] and p==original

def test_revision_remains_current_vintage_and_does_not_change_other_measures():
    d=data();before=bind(d)['measures'];d['AWHAETP'][-1]['value']=34.5;after=bind(d)['measures']
    assert after[:-1]==before[:-1] and after[-1]['actual']==34.5 and after[-1]['data_version']=='current_vintage'

def test_legacy_three_measures_and_evidence_are_unchanged():
    d=data();p=proof();original=copy.deepcopy(p)
    old=bind_events([event(50,'2026-10-02',IDS[:3])],{},d,NOW,p,dict.fromkeys(IDS,'2026-10-02'))[0]
    assert bind()['measures'][:3]==old['measures']
    expanded=expand_employment_evidence(p)
    assert p==original and expand_employment_evidence(expanded)==expanded and len(expanded['periods'])==1
    assert [m[0] for m in SPECS[50]]==list(IDS)

@pytest.mark.parametrize('sid',['U6RATE','AWHAETP'])
def test_existing_importer_is_idempotent(monkeypatch,tmp_path,sid):
    from tests.test_calendar_retail_measures import test_existing_ingester_reuses_retail_observation_keys_on_reimport
    test_existing_ingester_reuses_retail_observation_keys_on_reimport(monkeypatch,tmp_path,sid)
