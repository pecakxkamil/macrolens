"""Offline BLS formats, conditional cache and reconciliation. No providers/DB."""
import copy
import gzip
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.ingestion.bls_schedule import parse_html, sync_sources, select_records, merge_source, GROUPS
from app.analytics.release_calendar import apply_bls_schedule
from app.analytics.calendar_evidence import period_evidence
from app.analytics.release_times import release_time_metadata
from app.analytics.calendar_readings import bind_events
from tests.test_calendar_agenda import event, point

NOW=datetime(2026,10,27,11,30,tzinfo=timezone.utc)
URL='https://www.bls.gov/schedule/news_release/empsit.htm'


def table(period='December 2026', day='Jan. 08, 2027', clock='08:30 AM'):
    return f'<table><thead><tr><th>Reference Month</th><th>Release Date</th><th>Release Time</th></tr></thead><tbody><tr><td>{period}</td><td>{day}</td><td>{clock}</td></tr></tbody></table>'


def proof(day='Jan. 08, 2027'):
    return parse_html(table(day=day),URL,NOW.isoformat(),'Employment Situation')[0]


def data():return dict(periods=[],bls_history=[],bls_sources=[])


@pytest.mark.parametrize('name',list(GROUPS))
def test_per_release_tables_keep_explicit_reference_and_clock(name):
    period='Fourth Quarter 2026' if name=='Employment Cost Index' else 'December 2026'
    row=parse_html(table(period),URL,NOW.isoformat(),name)[0]
    assert row['release_id']==GROUPS[name][0] and row['series_ids']==GROUPS[name][1]
    assert row['reference_period']==('2026-10-01' if name=='Employment Cost Index' else '2026-12-01')
    assert row['release_date']=='2027-01-08' and row['release_time']=='08:30:00'


def test_monthly_list_parses_quarter_and_december_in_january():
    html='<table><tr><th>Date</th><th>Time</th><th>Release</th></tr><tr><td>Friday, January 8, 2027</td><td>08:30 AM</td><td>Employment Situation for December 2026</td></tr><tr><td>Friday, January 29, 2027</td><td>08:30 AM</td><td>Employment Cost Index for Fourth Quarter 2026</td></tr></table>'
    rows=parse_html(html,'https://www.bls.gov/schedule/2027/01_sched_list.htm',NOW.isoformat())
    assert [(r['reference_period'],r['release_date']) for r in rows]==[('2026-12-01','2027-01-08'),('2026-10-01','2027-01-29')]
    with pytest.raises(ValueError):parse_html(html.replace('December 2026',''),URL,NOW.isoformat())


@pytest.mark.parametrize('html',[table()+table('January 2027',clock=''),table()+'<table><tr><th>Reference Month Release Date Release Time</th></tr><tr><td>January 2027</td><td>Feb. 05, 2027</td></tr></table>',table('October and November 2026')])
def test_incomplete_or_ambiguous_content_is_rejected(html):
    with pytest.raises(ValueError):parse_html(html,URL,NOW.isoformat(),'Employment Situation')


def test_move_is_idempotent_retains_history_and_does_not_remove_absent_rows():
    d=data();row=proof();merge_source(d,URL,[row])
    merge_source(d,URL,[{**row,'retrieved_at':(NOW+timedelta(days=1)).isoformat()}])
    assert d['periods']==[row] and not d['bls_history']
    moved=proof('Jan. 15, 2027');merge_source(d,URL,[moved]);merge_source(d,URL,[])
    assert d['periods']==[moved] and d['bls_history']==[row]
    events={(50,date(2027,1,8)):dict(release_date=date(2027,1,8))}
    template={50:dict(release_id=50,release_name='Employment Situation',series=[])}
    apply_bls_schedule(events,template,d,date(2027,1,1),date(2027,1,31))
    assert list(events)==[(50,date(2027,1,15))]
    assert events[(50,date(2027,1,15))]['release_datetime_utc']=='2027-01-15T13:30:00Z'


def test_conflict_resolution_is_explicit_and_independent_of_response_order():
    primary=proof();monthly={**proof('Jan. 15, 2027'),'binding_method':'bls_monthly_list','source_url':'https://www.bls.gov/schedule/2027/01_sched_list.htm'}
    for rows in ([primary,monthly],[monthly,primary]):
        selected,conflicts=select_records(rows)
        assert selected==[primary] and conflicts[0]['resolution']=='documented_source_priority'
    peer={**monthly,'binding_method':'bls_release_table'}
    selected,conflicts=select_records([primary,peer])
    assert not selected and conflicts[0]['resolution']=='unresolved'
    assert period_evidence({'periods':[primary,peer]},50,'2027-01-08','PAYEMS') is None
    current={'PAYEMS':[point('2026-11-01',100),point('2026-12-01',101)]}
    row=bind_events([event(50,'2027-01-08',('PAYEMS',))],current,current,NOW+timedelta(days=100),{'periods':[primary,peer]})[0]['measures'][0]
    assert row['reference_period'] is None and row['actual'] is None


def test_ics_with_shorter_coverage_cannot_cancel_or_override_html():
    primary=proof();older={**primary,'reference_period':'2026-10-01','release_date':'2026-11-06','binding_method':'official_calendar_feed'}
    selected,_=select_records([primary,older])
    assert len(selected)==2 and primary in selected
    d=data();merge_source(d,URL,[primary]);merge_source(d,'https://www.bls.gov/schedule/news_release/bls.ics',[older])
    assert primary in d['periods']


def response_handler(request):
    return httpx.Response(200,headers={'Content-Type':'text/html','ETag':'"v1"','Last-Modified':'Tue, 27 Oct 2026 10:00:00 GMT'},text=table('Fourth Quarter 2026' if request.url.path.endswith('eci.htm') else 'December 2026'),request=request)


def sync(d,tmp_path,handler,now=NOW):
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return sync_sources(client,d,date(2026,12,1),date(2027,1,31),now,tmp_path)


def test_daily_minimum_conditional_304_and_acquisition_date_are_separate(tmp_path):
    d=data();checks=sync(d,tmp_path,response_handler)
    assert len(d['periods'])==5 and all(c['status']=='success' for c in checks)
    original=copy.deepcopy(d['periods']);states=copy.deepcopy(d['bls_sources'])
    sync(d,tmp_path,lambda r:pytest.fail('BLS polled inside its minimum interval'),NOW+timedelta(hours=23))
    def unchanged(request):
        assert request.headers['If-None-Match']=='"v1"'
        assert request.headers['If-Modified-Since']=='Tue, 27 Oct 2026 10:00:00 GMT'
        return httpx.Response(304,request=request)
    checks=sync(d,tmp_path,unchanged,NOW+timedelta(days=1))
    assert d['periods']==original and all(c['http_status']==304 for c in checks)
    assert d['bls_sources'][0]['content_retrieved_at']==states[0]['content_retrieved_at']
    assert d['bls_sources'][0]['last_successful_check']!=(states[0]['last_successful_check'])
    assert d['bls_sources'][0]['coverage']['reference_through']=='2026-12-01'


@pytest.mark.parametrize('failure',['403','timeout','error_html','bad_type','incomplete'])
def test_errors_preserve_last_good_schedule(tmp_path,monkeypatch,failure):
    monkeypatch.setattr('app.ingestion.bls_schedule.time.sleep',lambda delay:None)
    d=data();sync(d,tmp_path,response_handler);original=copy.deepcopy(d['periods']);old_check=d['bls_sources'][0]['last_successful_check'];calls=[]
    def fail(request):
        calls.append(str(request.url))
        if failure=='timeout':raise httpx.ReadTimeout('offline',request=request)
        if failure=='403':return httpx.Response(403,request=request)
        return httpx.Response(200,headers={'Content-Type':'application/json' if failure=='bad_type' else 'text/html'},text=table(clock='') if failure=='incomplete' else '<h2>Access Denied</h2>',request=request)
    checks=sync(d,tmp_path,fail,NOW+timedelta(days=1))
    assert d['periods']==original and all(c['status']=='error' for c in checks)
    assert d['bls_sources'][0]['last_successful_check']==old_check
    assert calls.count(URL)==(2 if failure=='timeout' else 1)


def test_gzip_and_bounded_transient_retry(tmp_path,monkeypatch):
    delays=[];monkeypatch.setattr('app.ingestion.bls_schedule.time.sleep',delays.append)
    calls={}
    def handle(request):
        url=str(request.url);calls[url]=calls.get(url,0)+1
        if calls[url]==1:return httpx.Response(503,request=request)
        body=table('Fourth Quarter 2026' if url.endswith('eci.htm') else 'December 2026').encode()
        return httpx.Response(200,headers={'Content-Type':'text/html','Content-Encoding':'gzip'},content=gzip.compress(body),request=request)
    d=data();sync(d,tmp_path,handle)
    assert len(d['periods'])==5 and all(n==2 for n in calls.values()) and delays==[1]*5


@pytest.mark.parametrize('day,expected',[('2026-03-12','13:30'),('2026-10-29','13:30'),('2026-11-05','14:30')])
def test_explicit_bls_time_uses_iana_dst(day,expected):
    row={**proof(),'release_date':day,'release_time':'08:30:00'}
    result=release_time_metadata('Employment Situation',date.fromisoformat(day),{'periods':[row]})
    assert datetime.fromisoformat(result['release_datetime_utc'].replace('Z','+00:00')).astimezone(ZoneInfo('Europe/Warsaw')).strftime('%H:%M')==expected


def test_fred_date_without_period_cannot_prove_bls_time():
    assert release_time_metadata('Employment Situation',date(2027,1,8),{})['release_time'] is None


def test_calendar_uses_publisher_dates_even_without_fred_window_dates(monkeypatch):
    from app.analytics import release_calendar, calendar_evidence
    from app.analytics import michigan_calendar
    monkeypatch.setattr(michigan_calendar,'calendar_events',lambda *args:[])
    from app.analytics import adp_calendar
    monkeypatch.setattr(adp_calendar,'calendar_events',lambda *args:[])
    from tests.test_release_calendar import FakeConnection, SERIES_PAYROLL
    metadata=(None,50,'Employment Situation','https://www.bls.gov/ces/',*SERIES_PAYROLL)
    monkeypatch.setattr(release_calendar,'get_connection',lambda:FakeConnection([[metadata]]))
    monkeypatch.setattr(release_calendar,'read_schedule',lambda:dict(events=[],status='not_synced',retrieved_at=None,source_url=''))
    monkeypatch.setattr(calendar_evidence,'read_evidence',lambda:{'periods':[proof()]})
    result=release_calendar.list_calendar_events(date(2027,1,1),date(2027,1,31))
    assert len(result['events'])==1
    assert result['events'][0]['release_date']==date(2027,1,8)
    assert result['events'][0]['series'][0]['series_id']=='PAYEMS'
    assert result['events'][0]['release_time']=='08:30:00'


def test_minimum_is_configurable_and_independent_of_fred(monkeypatch):
    from app.ingestion.bls_schedule import sources_due
    states=[dict(source_url=f'https://www.bls.gov/schedule/news_release/{g[2]}.htm',attempted_at=NOW.isoformat()) for g in GROUPS.values()]
    assert not sources_due({'bls_sources':states},NOW+timedelta(hours=23))
    assert sources_due({'bls_sources':states},NOW+timedelta(hours=24))
    monkeypatch.setenv('BLS_SCHEDULE_MIN_INTERVAL_SECONDS','172800')
    assert not sources_due({'bls_sources':states},NOW+timedelta(hours=24))


def test_schedule_import_does_not_make_future_reading_available():
    row=proof();current={'PAYEMS':[point('2026-10-01',90),point('2026-11-01',100),point('2026-12-01',105)]}
    e=event(50,'2027-01-08',('PAYEMS',))
    e.update(release_time_metadata('Employment Situation',date(2027,1,8),{'periods':[row]}))
    result=bind_events([e],{},current,datetime(2027,1,8,13,tzinfo=timezone.utc),{'periods':[row]}, {'PAYEMS':'2027-01-08'})[0]['measures'][0]
    assert result['actual'] is None and result['previous']==10


def test_fred_success_cannot_claim_publisher_schedule_success():
    from app.analytics.calendar_agenda import scoped_check
    shown=event(50,'2027-01-08',())
    check={'sources':[dict(resource='fred:calendar',status='success',coverage_checked_at=NOW.isoformat(),scope=dict(start_date='2027-01-01',end_date='2027-01-31')),
                      dict(resource='fed:calendar',status='success',coverage_checked_at=NOW.isoformat(),scope=dict(dates=['2026-01-01','2027-12-31'])),
                      dict(resource='calendar:periods',status='partial',scope=dict(start_date='2027-01-01',end_date='2027-01-31',sources=[dict(source_url=URL,status='error',http_status=403)]))]}
    result=scoped_check(check,date(2027,1,1),date(2027,1,31),[shown],{'status':'available'})
    assert result['status']=='partial' and 'calendar:periods' in result['required_resources']
    assert result['sources'][-1]['scope']['sources'][0]['http_status']==403


def test_monthly_fallback_imports_explicit_period_when_primary_fails(tmp_path):
    html='<table><tr><td>Friday, January 8, 2027</td><td>08:30 AM</td><td>Employment Situation for December 2026</td></tr></table>'
    def handle(request):
        if request.url.path.endswith('_sched_list.htm'):
            return httpx.Response(200,headers={'Content-Type':'text/html'},text=html,request=request)
        return httpx.Response(403,request=request)
    d=data();checks=sync(d,tmp_path,handle)
    assert len(d['periods'])==2  # Both fallback documents identify the same period.
    assert len(select_records(d['periods'])[0])==1
    assert d['periods'][0]['reference_period']=='2026-12-01'
    assert any(c['status']=='success' for c in checks) and any(c['http_status']==403 for c in checks)
