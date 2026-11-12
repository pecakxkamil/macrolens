"""Publisher-scoped financial date bindings; all fixtures are offline."""
import copy
from datetime import datetime,timezone
import pytest
from app.analytics.calendar_evidence import read_evidence
from app.analytics.calendar_readings import bind_events
from app.analytics.release_times import release_time_metadata
from tests.test_calendar_agenda import event,point

NOW=datetime(2026,11,12,12,tzinfo=timezone.utc)
CASES=[('DFF',18,3.88,3.88),('DGS2',18,4.56,4.51),('DGS10',18,4.88,4.86),('DFII10',18,2.66,2.63),('MORTGAGE30US',190,7.18,7.24)]

def setup(sid,rid,actual,previous):
    weekly=rid==190;day='2026-11-05' if weekly else '2026-11-10'
    period='2026-11-05' if weekly else '2026-11-09';prior='2026-10-29' if weekly else '2026-11-06'
    e=event(rid,day,(sid,));e['series'][0]['frequency']='weekly' if weekly else 'daily'
    points=[point(prior,previous,'2026-11-11'),point(period,actual,'2026-11-11'),point('2026-11-12',99,'2026-11-12')]
    return e,{sid:points},read_evidence(),period,prior

def measure(e,points,proof,now=NOW,panel=None):
    return bind_events([e],panel or {},points,now,proof)[0]['measures'][0]

@pytest.mark.parametrize('sid,rid,a,p',CASES)
def test_exact_period_pair_and_no_latest_substitution(sid,rid,a,p):
    e,points,proof,period,prior=setup(sid,rid,a,p);m=measure(e,points,proof)
    assert (m['reference_period'],m['previous_period'],m['actual'],m['previous'])==(period,prior,a,p)
    assert m['data_version']==m['previous_data_version']=='current_vintage'
    assert m['comparison_status']=='publisher_confirmed_pair' and not m['revision_confirmed']

@pytest.mark.parametrize('sid,rid,a,p',CASES)
def test_missing_publication_proof_never_falls_back_to_alfred_latest(sid,rid,a,p):
    e,points,proof,_,_=setup(sid,rid,a,p);m=measure(e,points,{},panel=points)
    assert m['actual'] is m['previous'] is None and m['mapping_status']=='reference_period_unconfirmed'

@pytest.mark.parametrize('sid,rid,a,p',CASES)
def test_missing_previous_keeps_actual_without_zero_or_another_period(sid,rid,a,p):
    e,points,proof,period,prior=setup(sid,rid,a,p);points[sid]=[x for x in points[sid] if x['observation_date']!=prior]
    m=measure(e,points,proof);assert m['actual']==a and m['previous'] is None

@pytest.mark.parametrize('day',['2026-11-07','2026-11-08','2026-11-11','2026-11-12'])
def test_weekends_holiday_and_unproved_next_publication_stay_null(day):
    e,points,proof,_,_=setup(*CASES[1]);e['release_date']=day;e['release_datetime_utc']=None
    assert measure(e,points,proof)['actual'] is None

def test_dff_weekend_carry_values_are_not_previous_business_observation():
    e,points,proof,_,_=setup(*CASES[0]);points['DFF'] += [point('2026-11-07',99),point('2026-11-08',98)]
    m=measure(e,points,proof);assert m['previous_period']=='2026-11-06' and m['previous']==3.88

def test_clock_boundary_and_no_invented_pmms_intraday_clock():
    e,points,proof,_,_=setup(*CASES[1]);assert measure(e,points,proof,datetime(2026,11,10,21,14,tzinfo=timezone.utc))['actual'] is None
    assert measure(e,points,proof,datetime(2026,11,10,21,15,tzinfo=timezone.utc))['actual']==4.56
    clock=release_time_metadata('H.15 Selected Interest Rates',datetime(2026,11,10).date(),proof);assert clock['release_datetime_utc']=='2026-11-10T21:15:00Z'
    assert release_time_metadata('Primary Mortgage Market Survey',datetime(2026,11,5).date(),proof)['release_datetime_utc'] is None
    e,points,proof,_,_=setup(*CASES[4]);assert measure(e,points,proof,datetime(2026,11,5,23,tzinfo=timezone.utc))['actual'] is None

def test_historical_alfred_pair_is_not_mixed_with_current_revision():
    e,current,proof,period,prior=setup(*CASES[1]);panel={'DGS2':[point(prior,4.51,'2026-11-10'),point(period,4.56,'2026-11-10')]}
    current['DGS2'][1]['value']=9
    m=measure(e,current,proof,panel=panel);assert (m['actual'],m['previous'])==(4.56,4.51) and m['data_version']=='stored_date_vintage'
    panel['DGS2']=panel['DGS2'][1:];m=measure(e,current,proof,panel=panel);assert m['actual']==4.56 and m['previous'] is None

def test_publisher_version_mismatch_is_explicit_not_overwritten():
    e,points,proof,_,_=setup(*CASES[1]);points['DGS2'][1]['value']=9
    m=measure(e,points,proof);assert m['actual'] is None and m['missing_reason']['actual']=='publisher_version_mismatch'

@pytest.mark.parametrize('field,value',[('source_url','https://example.com/'),('publication_confirmed',False),('frequency','monthly'),('reference_period','2026-11-14'),('previous_period','2026-11-09')])
def test_invalid_or_conflicting_contract_cannot_bind(field,value):
    e,points,proof,_,_=setup(*CASES[1]);row=next(x for x in proof['periods'] if x['release_id']==18 and x['series_ids']==['DGS2']);row[field]=value
    assert measure(e,points,proof)['actual'] is None

def test_weekly_holiday_shift_requires_explicit_asof_not_seven_day_offset():
    e,points,proof,_,_=setup(*CASES[4]);row=next(x for x in proof['periods'] if x['release_id']==190)
    row.update(release_date='2026-11-25',reference_period='2026-11-25',previous_period='2026-11-19');e['release_date']='2026-11-25';e['release_datetime_utc']=None
    points={'MORTGAGE30US':[point('2026-11-19',7.24,'2026-11-26'),point('2026-11-25',7.18,'2026-11-26')]}
    m=measure(e,points,proof,datetime(2026,11,26,12,tzinfo=timezone.utc));assert m['actual']==7.18 and m['previous_period']=='2026-11-19'

def test_conflicting_period_proof_is_not_chosen_by_latest_retrieval():
    e,points,proof,_,_=setup(*CASES[1]);row=copy.deepcopy(next(x for x in proof['periods'] if x['release_id']==18 and x['series_ids']==['DGS2']));row['reference_period']='2026-11-06';proof['periods'].append(row)
    assert measure(e,points,proof)['actual'] is None


def test_reviewed_extract_hash_and_publisher_pairs_match_the_bounded_proofs():
    import hashlib,json
    from pathlib import Path
    raw=(Path(__file__).parent/'fixtures/financial_publication_columns.json').read_bytes()
    digest=hashlib.sha256(raw).hexdigest();extract=json.loads(raw)
    rows=[p for p in read_evidence()['periods'] if p.get('binding_method')=='reviewed_financial_table']
    assert len(rows)==5 and all(p['evidence_sha256']==digest for p in rows)
    assert extract['capture_kind']=='reviewed official web text; not full original HTML'
    for row in rows:
        sid=row['series_ids'][0]
        expected=extract['pmms']['values'] if sid=='MORTGAGE30US' else extract['h15']['values'][sid]
        assert [row['previous_reported_value'],row['reported_value']]==expected
