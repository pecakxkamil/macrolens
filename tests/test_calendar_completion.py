"""Documented calendar conventions and publication transitions, entirely offline."""
import copy
from datetime import date,datetime,timezone,timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import httpx
import pytest
from app.analytics.calendar_evidence import period_evidence,read_evidence
from app.analytics.calendar_readings import bind_events
from app.analytics.release_times import release_time_metadata
from app.analytics.overview_refresh import publication_results_due
from app.ingestion.sync_calendar_periods import parse_bls_ics,parse_m3_result,parse_bea_result,parse_dol_schedule,import_bls_document
from tests.test_calendar_agenda import event,point

RULE={'id':'dol_weekly_claims','valid_from':'2026-01-02','valid_through':'2027-12-31',
      'source_url':'https://oui.doleta.gov/unemploy/archive.asp','methodology_url':'https://www.dol.gov/sites/dolgov/files/ETA/handbooks/2017/ETHand401_5th.pdf',
      'retrieved_at':'2026-10-27T10:30:00+00:00','exceptions':{'2026-11-25':'08:30:00','2027-11-10':'08:30:00','2027-11-24':'08:30:00'},
      'cancelled_dates':['2026-11-26','2027-11-11','2027-11-25']}
EVIDENCE={'rules':[RULE]}
M3="Manufacturer's Shipments, Inventories, and Orders (M3) Survey"

@pytest.mark.parametrize('name',['Chicago Fed National Activity Index','Chicago Fed National Financial Conditions Index','Unemployment Insurance Weekly Claims Report'])
def test_documented_clocks_have_source_zone_and_validity(name):
    m=release_time_metadata(name,date(2026,10,29),EVIDENCE)
    assert m['release_time']=='08:30:00' and m['source_timezone']=='America/New_York'
    assert m['time_source_url'].startswith('https://') and m['time_rule']['valid_through']>='2026-10-29'

@pytest.mark.parametrize('day,expected',[('2026-03-05','14:30'),('2026-03-12','13:30'),('2026-10-22','14:30'),('2026-10-29','13:30'),('2026-11-05','14:30')])
def test_claims_time_uses_both_iana_dst_transitions(day,expected):
    m=release_time_metadata('Unemployment Insurance Weekly Claims Report',date.fromisoformat(day),EVIDENCE)
    instant=datetime.fromisoformat(m['release_datetime_utc'].replace('Z','+00:00'))
    assert instant.astimezone(ZoneInfo('Europe/Warsaw')).strftime('%H:%M')==expected

def test_holiday_exception_and_cancelled_day_are_explicit():
    assert release_time_metadata('Unemployment Insurance Weekly Claims Report',date(2026,11,25),EVIDENCE)['release_time']=='08:30:00'
    assert release_time_metadata('Unemployment Insurance Weekly Claims Report',date(2026,11,26),EVIDENCE)['release_time'] is None
    assert period_evidence(EVIDENCE,180,'2026-11-25','ICSA')['reference_period']=='2026-11-21'
    assert period_evidence(EVIDENCE,180,'2026-11-25','CCSA')['reference_period']=='2026-11-14'
    assert period_evidence(EVIDENCE,180,'2026-11-26','ICSA') is None
    assert period_evidence(EVIDENCE,180,'2026-10-28','ICSA') is None
    assert period_evidence(EVIDENCE,180,'2028-01-06','ICSA') is None

def test_explicit_time_and_reference_overrides_are_used():
    evidence=copy.deepcopy(EVIDENCE)
    evidence['rules'][0]['exceptions']['2026-10-27']='09:00:00'
    assert period_evidence(evidence,180,'2026-10-27','ICSA') is None
    evidence['rules'][0]['period_overrides']={'2026-10-27':{'ICSA':'2026-10-17','CCSA':'2026-10-10'}}
    assert period_evidence(evidence,180,'2026-10-27','ICSA')['reference_period']=='2026-10-17'
    assert release_time_metadata('Unemployment Insurance Weekly Claims Report',date(2026,10,27),evidence)['release_time']=='09:00:00'
    evidence={'periods':[dict(release_id=180,release_date='2026-10-27',series_ids=['ICSA'],reference_period='2026-10-17',binding_method='official_release',release_time='09:15:00',source_url='https://www.dol.gov/report.pdf',retrieved_at=RULE['retrieved_at'])]}
    assert release_time_metadata('Unemployment Insurance Weekly Claims Report',date(2026,10,27),evidence)['release_time']=='09:15:00'


def test_new_schedule_cancellation_cannot_fall_back_to_old_rule():
    updated=copy.deepcopy(RULE)
    updated.update(schedule_retrieved_at='2026-10-28T10:00:00+00:00')
    updated['exceptions']['2026-10-28']='08:30:00'
    updated['cancelled_dates'].append('2026-10-29')
    evidence={'rules':[RULE,updated]}
    assert period_evidence(evidence,180,'2026-10-29','ICSA') is None
    assert release_time_metadata('Unemployment Insurance Weekly Claims Report',date(2026,10,29),evidence)['release_time'] is None
    assert period_evidence(evidence,180,'2026-10-28','ICSA')['reference_period']=='2026-10-24'

def test_future_claims_have_different_weeks_and_comparable_previous_values():
    e=event(180,'2026-10-29',('ICSA','CCSA'))
    current={'ICSA':[point('2026-10-10',200000),point('2026-10-17',194000)],'CCSA':[point('2026-10-03',1703000),point('2026-10-10',1728000)]}
    m=bind_events([e],{},current,datetime(2026,10,27,tzinfo=timezone.utc),EVIDENCE)[0]['measures']
    assert [x['reference_period'] for x in m]==['2026-10-24','2026-10-17']
    assert [x['previous'] for x in m]==[194000,1728000] and all(x['actual'] is None for x in m)
    assert all(x['previous_data_version']=='current_vintage' for x in m)
    assert all(x['period_provenance']['rule_id']=='dol_weekly_claims' for x in m)
    # Time and provider metadata alone cannot fill a missing observation.
    after=datetime(2026,10,29,18,tzinfo=timezone.utc)
    m=bind_events([e],{},current,after,EVIDENCE,{'ICSA':'2026-10-29','CCSA':'2026-10-29'})[0]['measures']
    assert all(x['actual'] is None for x in m)
    current['ICSA'].append(point('2026-10-24',195000,'2026-10-29'))
    current['CCSA'].append(point('2026-10-17',1730000,'2026-10-29'))
    m=bind_events([e],{},current,after,EVIDENCE,{'ICSA':'2026-10-29','CCSA':'2026-10-29'})[0]['measures']
    assert [x['actual'] for x in m]==[195000,1730000]
    assert [x['actual']-x['previous'] for x in m]==[1000,2000]

def m3_proof(day,stage):
    return dict(release_id=95,series_ids=['DGORDER'],release_date=day,reference_period='2026-09-01',estimate_stage=stage,source_url='https://www.census.gov/manufacturing/m3/release_schedule.html',retrieved_at='2026-10-27T10:00:00+00:00',binding_method='official_schedule')

def test_m3_stages_have_distinct_clocks_and_same_reference_month():
    evidence={'periods':[m3_proof('2026-10-27','advance'),m3_proof('2026-11-03','full')]}
    a=release_time_metadata(M3,date(2026,10,27),evidence);b=release_time_metadata(M3,date(2026,11,3),evidence)
    assert a['release_time']=='08:30:00' and b['release_time']=='10:00:00'
    assert a['release_datetime_utc']=='2026-10-27T12:30:00Z' and b['release_datetime_utc']=='2026-11-03T15:00:00Z'
    assert release_time_metadata(M3,date(2026,10,28),evidence)['release_time'] is None
    evidence['periods'][0]['release_time']='09:00:00'
    assert release_time_metadata(M3,date(2026,10,27),evidence)['release_time']=='09:00:00'

def test_full_m3_requires_its_own_report_and_fetched_values_not_advance_or_timestamp():
    e=event(95,'2026-11-03',('DGORDER',));proof=m3_proof('2026-11-03','full');evidence={'periods':[proof]}
    rows={'DGORDER':[point('2026-07-01',100,'2026-10-27'),point('2026-08-01',101,'2026-10-27'),point('2026-09-01',103,'2026-10-27')]}
    updates={'DGORDER':'2026-11-03'};now=datetime(2026,11,3,17,tzinfo=timezone.utc)
    def measure():return bind_events([e],rows,rows,now,evidence,updates)[0]['measures'][0]
    assert measure()['actual'] is None
    evidence['results']=[m3_proof('2026-10-27','advance')]
    assert measure()['actual'] is None
    evidence['results']=[dict(proof,announced_at='2026-11-03T15:00:00+00:00')]
    assert measure()['actual'] is None  # The old snapshot still predates the full report.
    rows['DGORDER']=[dict(p,vintage_date='2026-11-03') for p in rows['DGORDER']]
    result=measure()
    assert result['actual']==pytest.approx((103/101-1)*100) and result['previous']==pytest.approx(1)
    assert result['previous_period']=='2026-08-01' and result['previous_kind']=='previous_period'
    assert result['result_provenance']['estimate_stage']=='full' and not result['revision_confirmed']

def test_m3_pdf_header_proves_stage_period_and_actual_release_date(monkeypatch):
    import pypdf
    text='FOR RELEASE AT 10:00 AM EST, TUESDAY, NOVEMBER 3, 2026 MONTHLY FULL REPORT ON MANUFACTURERS\u2019 SHIPMENTS, INVENTORIES AND ORDERS SEPTEMBER 2026 New orders for durable goods.'
    monkeypatch.setattr(pypdf,'PdfReader',lambda f:SimpleNamespace(pages=[SimpleNamespace(extract_text=lambda:text)]))
    m=parse_m3_result(b'fixture','full','https://www.census.gov/report.pdf','2026-11-03T16:00:00+00:00')
    assert m['reference_period']=='2026-09-01' and m['announced_at']=='2026-11-03T15:00:00+00:00'
    with pytest.raises(ValueError):parse_m3_result(b'fixture','advance','https://www.census.gov/report.pdf','2026-11-03T16:00:00+00:00')

ICS='BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nDTSTART;TZID=America/New_York:20261106T083000\r\nSUMMARY:Employment Situation for Octo\r\n ber 2026\r\nEND:VEVENT\r\nEND:VCALENDAR'

def test_official_ics_unfolds_explicit_periods_and_does_not_invent_missing_ones():
    rows=parse_bls_ics(ICS,'https://www.bls.gov/schedule/news_release/bls.ics','2026-10-27T10:00:00+00:00')
    assert rows[0]['reference_period']=='2026-10-01' and rows[0]['release_date']=='2026-11-06'
    with pytest.raises(ValueError):parse_bls_ics(ICS.replace(' for Octo\r\n ber 2026',''),'https://www.bls.gov/schedule/news_release/bls.ics','2026-10-27T10:00:00+00:00')

def test_manual_import_keeps_original_retrieval_time_and_other_evidence(tmp_path):
    path=tmp_path/'bls.ics';path.write_bytes(ICS.encode('utf-8'));target=tmp_path/'evidence.json'
    stamp='2026-10-20T10:00:00+00:00'
    assert import_bls_document(path,'https://www.bls.gov/schedule/news_release/bls.ics',stamp,target)==1
    result=read_evidence(target)
    assert result['periods'][0]['retrieved_at']==stamp and result['checks']==[]
    with pytest.raises(ValueError):import_bls_document(path,'https://example.com/calendar',stamp,target)

def test_result_check_is_due_at_release_and_respects_existing_cadence():
    e=event(95,'2026-10-27',('DGORDER',));evidence={'periods':[m3_proof('2026-10-27','advance')]}
    now=datetime(2026,10,27,13,tzinfo=timezone.utc)
    assert publication_results_due([e],evidence,{}, {'attempted_at':'2026-10-27T12:00:00+00:00'},now)
    previous={'attempted_at':'2026-10-27T12:55:00+00:00'}
    versions={'fred:DGORDER':{'last_updated':'2026-10-27','observation_end':'2026-09-01'}}
    assert not publication_results_due([e],evidence,versions,previous,now)
    assert publication_results_due([e],evidence,versions,previous,now+timedelta(minutes=15))
    evidence['results']=[m3_proof('2026-10-27','advance')]
    assert not publication_results_due([e],evidence,versions,previous,now+timedelta(minutes=15))


def test_dol_schedule_refresh_preserves_method_date_and_updates_explicit_exceptions():
    html='<p>The report is published each week on Thursday morning at 8:30am EST.</p><table><tr><th>Release Date</th><th>Release Time</th></tr><tr><td>Wednesday, November 25, 2026</td><td>8:30 AM EST</td></tr></table>'
    result=parse_dol_schedule(html,RULE,'2026-10-28T10:00:00+00:00')
    assert result['retrieved_at']==RULE['retrieved_at'] and result['schedule_retrieved_at']=='2026-10-28T10:00:00+00:00'
    assert result['exceptions']=={'2026-11-25':'08:30:00'} and result['cancelled_dates']==['2026-11-26']
    with pytest.raises(ValueError):parse_dol_schedule('<h1>Unavailable</h1>',RULE,RULE['retrieved_at'])


def test_bea_report_requires_published_date_period_and_estimate_stage():
    proof={'release_date':'2026-09-30','reference_period':'2026-04-01','estimate_stage':'third'}
    html='<meta property="article:published_time" content="2026-09-30T08:30:00-04:00"><h1>Gross Domestic Product, 2nd Quarter 2026 (Third Estimate)</h1>'
    result=parse_bea_result(html,proof,'https://www.bea.gov/news/result','2026-10-27T10:00:00+00:00')
    assert result['reference_period']=='2026-04-01' and result['estimate_stage']=='third'
    with pytest.raises(ValueError):parse_bea_result(html.replace('Third','Second'),proof,'https://www.bea.gov/news/result',RULE['retrieved_at'])
    with pytest.raises(ValueError):parse_bea_result(html.replace('2026-09-30','2026-09-29'),proof,'https://www.bea.gov/news/result',RULE['retrieved_at'])


def test_documented_bls_feed_fallback_keeps_original_reviewed_evidence(tmp_path,monkeypatch):
    from contextlib import contextmanager
    import json
    from app.ingestion import sync_calendar_periods as sync
    from app.analytics import fomc_calendar
    target=tmp_path/'derived'/'evidence.json';target.parent.mkdir()
    old=dict(release_id=50,series_ids=['PAYEMS'],release_date='2026-10-02',reference_period='2026-09-01',source_url='https://www.bls.gov/schedule/2026/home.htm',retrieved_at='2026-10-20T10:00:00+00:00',binding_method='reviewed_official_schedule')
    target.write_text(json.dumps({'version':1,'periods':[old]}),encoding='utf-8')
    @contextmanager
    def check(resource,scope):yield {'scope':scope}
    monkeypatch.setattr(sync,'availability_check',check)
    monkeypatch.setattr(fomc_calendar,'read_schedule',lambda:{'events':[]})
    calls=[]
    def handle(request):
        calls.append(str(request.url))
        return httpx.Response(200,text=ICS,request=request) if request.url.path.endswith('bls.ics') else httpx.Response(403,request=request)
    now=datetime(2026,10,27,11,tzinfo=timezone.utc)
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result=sync.sync_periods(client,date(2026,10,26),date(2026,11,8),[],now,target)
    assert all('bls.gov' in u for u in calls[:2])
    assert old in result['periods']
    imported=next(r for r in result['periods'] if r['release_date']=='2026-11-06')
    assert imported['binding_method']=='official_calendar_feed' and imported['retrieved_at']==now.isoformat()
    assert all(c['status']=='error' for c in result['checks'] if c['source_url'].endswith('.htm'))
    assert next(c for c in result['checks'] if c['source_url'].endswith('bls.ics'))['status']=='success'
