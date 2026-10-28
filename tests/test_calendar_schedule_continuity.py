"""Publisher-only dates, stage identities and source history; entirely offline."""
import copy
import json
from datetime import date,datetime,timezone

import httpx
import pytest

from app.analytics import release_calendar as calendar
from app.analytics.calendar_evidence import period_evidence,schedule_records
from app.analytics.calendar_readings import bind_events
from app.ingestion.bls_schedule import merge_source,publisher_identity
from app.ingestion.sync_calendar_periods import parse_schedule,sync_periods
from tests.test_calendar_agenda import event,point
from tests.test_release_calendar import FakeConnection

STAMP='2026-10-27T20:00:00+00:00'
M3="Manufacturer's Shipments, Inventories, and Orders (M3) Survey"
NAMES={95:M3,27:'New Residential Construction',50:'Employment Situation',10:'Consumer Price Index',46:'Producer Price Index',11:'Employment Cost Index',180:'Unemployment Insurance Weekly Claims Report',13:'G.17 Industrial Production and Capacity Utilization'}


def proof(rid,day,period='2026-12-01',stage=None,sids=None,clock='08:30:00',method='official_schedule',url='https://www.census.gov/schedule'):
    return dict(release_id=rid,release_date=day,reference_period=period,estimate_stage=stage,
                series_ids=sids or {95:['DGORDER'],27:['HOUST','PERMIT'],50:['PAYEMS','UNRATE','CES0500000003'],10:['CPIAUCSL','CPILFESL'],46:['PPIFIS'],11:['ECIALLCIV']}[rid],
                release_time=clock,source_timezone='America/New_York',source_url=url,retrieved_at=STAMP,binding_method=method)


def template(rid,sids):
    item=event(rid,'2027-01-01',tuple(sids))
    item.update(release_name=NAMES[rid],date_precision='date',importance='medium',source_link='https://fred.stlouisfed.org/')
    return item


@pytest.fixture(autouse=True)
def offline_sources(monkeypatch):
    from app import source_checks
    monkeypatch.setattr(source_checks,'write_run',lambda run:None)
    monkeypatch.setattr(calendar,'read_schedule',lambda:{'status':'available','events':[],'retrieved_at':STAMP,'source_url':'https://www.federalreserve.gov/'})
    from app.analytics import ism_calendar
    monkeypatch.setattr(ism_calendar,'calendar_events',lambda *args:[])
    from app.analytics import michigan_calendar
    monkeypatch.setattr(michigan_calendar,'calendar_events',lambda *args:[])


@pytest.mark.parametrize('rid,day,period,stage,clock',[
    (95,'2027-01-07','2026-11-01','full','10:00:00'),
    (50,'2027-01-08','2026-12-01',None,'08:30:00'),
    (10,'2027-01-13','2026-12-01',None,'08:30:00'),
    (46,'2027-01-14','2026-12-01',None,'08:30:00'),
    (27,'2027-01-20','2026-12-01','initial','08:30:00'),
    (11,'2027-01-29','2026-10-01',None,'08:30:00'),
])
def test_sql_template_without_fred_date_creates_publisher_event(monkeypatch,rid,day,period,stage,clock):
    row=proof(rid,day,period,stage,clock=clock)
    from app.analytics import calendar_evidence
    monkeypatch.setattr(calendar_evidence,'read_evidence',lambda:{'periods':[row]})
    sids=row['series_ids']
    metadata=[(None,rid,NAMES[rid],'https://fred.stlouisfed.org/',sid,sid,sid,'housing' if rid==27 else 'growth','quarterly' if rid==11 else 'monthly','percent') for sid in sids]
    fake=FakeConnection([metadata]);monkeypatch.setattr(calendar,'get_connection',lambda:fake)
    result=calendar.list_calendar_events(date(2027,1,1),date(2027,1,31))['events']
    assert len(result)==1
    item=result[0]
    assert item['release_date']==date.fromisoformat(day) and item['release_time']==clock
    assert item['schedule_provenance']==row and item['source_link']==row['source_url']
    assert 'd.release_date IS NOT NULL' not in fake.cursor_instance.query
    assert item['event_id']==f'release:{rid}:{period}:{stage or "main"}'


def test_fred_duplicate_and_publisher_move_have_one_stable_identity():
    first=proof(95,'2027-01-07','2026-11-01','full',clock='10:00:00')
    t=template(95,['DGORDER']);events={(95,date(2027,1,7)):t.copy()}
    calendar.apply_bls_schedule(events,{95:t},{'periods':[first]},date(2027,1,1),date(2027,1,31))
    identity=next(iter(events.values()))['event_id']
    assert len(events)==1
    moved=dict(first,release_date='2027-01-08')
    evidence={'periods':[moved],'publisher_history':[first]}
    calendar.apply_bls_schedule(events,{95:t},evidence,date(2027,1,1),date(2027,1,31))
    assert list(events)==[(95,date(2027,1,8))]
    assert next(iter(events.values()))['event_id']==identity


def test_m3_and_housing_stage_identities_do_not_overwrite_each_other():
    rows=[proof(95,'2026-12-23','2026-11-01','advance'),proof(95,'2027-01-07','2026-11-01','full',clock='10:00:00'),
          proof(27,'2027-01-20',stage='initial'),proof(27,'2027-01-27',stage='revised_permits',sids=['PERMIT'],clock='08:00:00')]
    data={'periods':[]}
    merge_source(data,rows[0]['source_url'],rows,publisher_identity)
    merge_source(data,rows[0]['source_url'],rows,publisher_identity)
    assert len(data['periods'])==4 and not data['bls_history']
    selected,conflicts=schedule_records(data)
    assert len(selected)==4 and not conflicts
    t={95:template(95,['DGORDER']),27:template(27,['HOUST','PERMIT'])};events={}
    calendar.apply_bls_schedule(events,t,data,date(2026,12,1),date(2027,1,31))
    assert len({e['event_id'] for e in events.values()})==4
    revised=events[(27,date(2027,1,27))]
    assert [s['series_id'] for s in revised['series']]==['PERMIT']
    assert revised['release_time']=='08:00:00'
    assert events[(95,date(2027,1,7))]['release_time']=='10:00:00'


def test_unresolved_peer_conflict_is_not_arbitrarily_projected_or_bound():
    a=proof(95,'2027-01-07','2026-11-01','full',clock='10:00:00')
    b=dict(a,release_date='2027-01-08',source_url='https://www.census.gov/other')
    selected,conflicts=schedule_records({'periods':[a,b]})
    assert not selected and conflicts[0]['resolution']=='unresolved'
    assert period_evidence({'periods':[a,b]},95,'2027-01-07','DGORDER') is None
    t=template(95,['DGORDER']);events={(95,date(2027,1,7)):t.copy()}
    calendar.apply_bls_schedule(events,{95:t},{'periods':[a,b]},date(2027,1,1),date(2027,1,31))
    assert len(events)==1 and events[(95,date(2027,1,7))]['schedule_status']=='conflict'
    assert events[(95,date(2027,1,7))]['release_datetime_utc'] is None


def test_report_priority_resolves_conflict_with_explicit_provenance():
    schedule=proof(95,'2027-01-07','2026-11-01','full')
    receipt=dict(schedule,binding_method='official_release',release_date='2027-01-08',source_url='https://www.census.gov/report')
    selected,conflicts=schedule_records({'periods':[schedule,receipt]})
    assert selected==[receipt] and conflicts[0]['resolution']=='documented_source_priority'
    events={};calendar.apply_bls_schedule(events,{95:template(95,['DGORDER'])},{'periods':[schedule,receipt]},date(2027,1,1),date(2027,1,31))
    item=next(iter(events.values()))
    assert item['schedule_provenance']==receipt and item['schedule_conflicts']==conflicts


def test_month_stages_have_correct_previous_and_empty_future_actual():
    rows=[proof(95,'2027-01-07','2026-11-01','full',clock='10:00:00'),proof(27,'2027-01-27','2026-12-01','revised_permits',sids=['PERMIT'],clock='08:00:00')]
    evidence={'periods':rows};events={}
    calendar.apply_bls_schedule(events,{95:template(95,['DGORDER']),27:template(27,['HOUST','PERMIT'])},evidence,date(2027,1,1),date(2027,1,31))
    points={'DGORDER':[point('2026-09-01',100),point('2026-10-01',101)],'PERMIT':[point('2026-11-01',1400)]}
    result=bind_events(list(events.values()),{},points,datetime(2026,10,27,tzinfo=timezone.utc),evidence)
    full=next(e for e in result if e['release_id']==95)['measures'][0]
    permits=next(e for e in result if e['release_id']==27)['measures']
    assert full['previous']==pytest.approx(1) and full['previous_period']=='2026-10-01'
    assert len(permits)==1 and permits[0]['series_id']=='PERMIT'
    assert permits[0]['previous']==1400 and permits[0]['previous_period']=='2026-11-01'
    assert all(m['actual'] is None and m['forecast'] is None for e in result for m in e['measures'])


def test_claims_uses_only_documented_bounded_rule_with_separate_weeks():
    from tests.test_calendar_completion import RULE
    t=template(180,['ICSA','CCSA']);events={}
    calendar.apply_bls_schedule(events,{180:t},{'rules':[RULE]},date(2027,1,1),date(2027,1,31))
    assert [day for _,day in events]==[date(2027,1,d) for d in (7,14,21,28)]
    assert period_evidence({'rules':[RULE]},180,'2027-01-07','ICSA')['reference_period']=='2027-01-02'
    assert period_evidence({'rules':[RULE]},180,'2027-01-07','CCSA')['reference_period']=='2026-12-26'
    events={};calendar.apply_bls_schedule(events,{180:t},{},date(2027,1,1),date(2027,1,31));assert not events
    calendar.apply_bls_schedule(events,{180:t},{'rules':[RULE]},date(2028,1,1),date(2028,1,31));assert not events


def test_schedule_only_sync_retains_narrowed_failed_and_moved_source(tmp_path):
    url='https://www.census.gov/manufacturing/m3/release_schedule.html'
    target=tmp_path/'derived/periods.json'
    old=[proof(95,'2027-01-07','2026-11-01','full',url=url),proof(95,'2027-01-27','2026-12-01','advance',url=url)]
    target.parent.mkdir();target.write_text(json.dumps({'version':1,'periods':old}))
    html='<table><tr><th>Month</th><th>Advance (8:30 a.m.)</th><th>Full (10:00 a.m.)</th></tr><tr><td>November 2026</td><td>12/23/2026</td><td>1/8/2027</td></tr></table>'
    def run(status=200):
        with httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(status,text=html))) as c:
            return sync_periods(c,date(2026,12,1),date(2027,1,31),[],datetime.fromisoformat(STAMP),target,{'m3'},False)
    first=run();second=run()
    assert first['periods']==second['periods'] and first['publisher_history']==second['publisher_history']
    assert any(r['release_date']=='2027-01-27' for r in second['periods'])
    assert any(r['release_date']=='2027-01-07' for r in second['publisher_history'])
    assert any(r.get('raw_hash') for r in second['periods'])
    failed=run(503)
    assert failed['periods']==second['periods'] and failed['checks'][0]['status']=='error'
    assert failed['results']==[] and failed['decisions']==[]


def test_bls_403_keeps_one_time_official_proof_without_manufactured_hash(tmp_path):
    from app.ingestion.bls_schedule import sync_sources
    row=proof(50,'2027-01-08',method='reviewed_official_schedule',url='https://www.bls.gov/schedule/news_release/empsit.htm')
    row.update(confirmation_type='one_time_official_review',retrieval_method='official_page_read_via_web_tool')
    data={'periods':[row],'bls_sources':[],'bls_history':[]};raw=tmp_path/'raw';raw.mkdir()
    with httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(403))) as c:
        checks=sync_sources(c,data,date(2027,1,1),date(2027,1,31),datetime.fromisoformat(STAMP),raw)
    assert data['periods']==[row] and all(c['status']=='error' for c in checks)
    assert 'raw_hash' not in row
    events={};calendar.apply_bls_schedule(events,{50:template(50,row['series_ids'])},data,date(2027,1,1),date(2027,1,31))
    assert len(events)==1 and next(iter(events.values()))['schedule_provenance']['confirmation_type']=='one_time_official_review'


def test_no_new_family_or_unconfirmed_cycle_is_projected():
    unsupported=proof(999,'2027-01-08',sids=['UNKNOWN'])
    events={};calendar.apply_bls_schedule(events,{}, {'periods':[unsupported]},date(2027,1,1),date(2027,1,31));assert not events
    p=proof(95,'2027-01-07','2026-11-01','full',method='estimated')
    assert schedule_records({'periods':[p]})[0]==[]
    p=proof(50,'2027-01-08',method='estimated')
    assert schedule_records({'periods':[p]})[0]==[]
    assert period_evidence({'periods':[p]},50,'2027-01-08','PAYEMS') is None


def test_explicit_g17_annual_revision_does_not_disappear_or_become_monthly_reading():
    from app.ingestion.sync_calendar_periods import parse_g17_schedule
    from tests.test_calendar_key_publications import G17,METHOD
    _,rules=parse_g17_schedule(G17,'https://www.federalreserve.gov/releases/g17/default.htm',STAMP,METHOD)
    assert rules[0]['annual_revision_dates']==['2026-11-24']
    t=template(13,['INDPRO','TCU']);t['release_name']='G.17 Industrial Production and Capacity Utilization'
    events={};calendar.apply_bls_schedule(events,{13:t},{'rules':rules},date(2026,11,24),date(2026,11,24))
    item=next(iter(events.values()))
    assert item['release_time']=='12:00:00' and item['expects_numeric_result'] is False
    assert bind_events([item],{}, {'INDPRO':[point('2026-10-01',105)]},datetime(2026,11,25,tzinfo=timezone.utc),{'rules':rules})[0]['measures']==[]
