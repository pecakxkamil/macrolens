"""Synthetic ISM schedules and document versions; no provider calls."""
import copy
import json
from contextlib import contextmanager, nullcontext
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest
from app.analytics import ism_calendar as agenda, calendar_readings, calendar_agenda
from app.ingestion import sync_ism_calendar as sync, import_ism, discover_ism
from tests.test_ism import document

NOW=datetime(2026,10,27,15,tzinfo=timezone.utc)


def rules():
    return {k:dict(following_month_rule_confirmed=True,release_clock_confirmed=True,source_url='https://www.prnewswire.com/news-releases/test.html',raw_hash='a'*64) for k in import_ism.KINDS}


def calendar():
    return '''<h1>Release Dates for the ISM Manufacturing and Services PMI Reports</h1>
    <p>10:00 a.m. (EST)</p><table><tr><th>Month</th><th>Manufacturing PMI</th><th>Services PMI</th></tr>
    <tr><td>January 2026</td><td>5*</td><td>7</td></tr>
    <tr><td>July 2026</td><td>1</td><td>6**</td></tr>
    <tr><td>November 2026</td><td>2</td><td>4</td></tr>
    <tr><td>January 2027</td><td>5</td><td>7</td></tr></table>'''


def event(kind='manufacturing',day='2026-10-01',period='2026-09-01'):
    return dict(release_id=None,event_type='ism_report',release_date=day,
        release_datetime_utc=day+'T14:00:00Z',series=[{'series_id':import_ism.KINDS[kind]}],
        period_evidence=dict(kind=kind,reference_period=period,release_date=day,source_url=sync.SOURCE_URL,binding_method='official_ism_calendar_and_month_rule'))


def doc(kind='manufacturing',period='2026-09-01',published='2026-10-01T14:00:00Z',identity=1,readings=None):
    return dict(id=identity,series_id=import_ism.KINDS[kind],report_month=period,
        published_at=datetime.fromisoformat(published.replace('Z','+00:00')),
        retrieved_at=NOW,source_url='https://www.prnewswire.com/news-releases/report.html',raw_hash=str(identity)*64,
        readings=readings if readings is not None else {'2026-09-01':51.2,'2026-08-01':50.3})


def test_calendar_uses_explicit_exceptions_and_bounded_reference_month_rule(monkeypatch):
    rows=sync.parse_calendar(calendar(),rules(),NOW.isoformat())
    assert len(rows)==8
    assert [(r['release_date'],r['reference_period']) for r in rows[:2]]==[('2026-01-05','2025-12-01'),('2026-01-07','2025-12-01')]
    assert rows[3]['release_date']=='2026-07-06'
    assert rows[-1]['reference_period']=='2026-12-01'
    monkeypatch.setattr(agenda,'read_schedule',lambda:{'events':rows})
    events=agenda.calendar_events(date(2026,11,1),date(2026,11,30))
    assert [e['series'][0]['series_id'] for e in events]==list(import_ism.KINDS.values())
    assert all(e['importance']=='high' and e['importance_origin']=='macrolens_editorial' for e in events)
    assert not agenda.calendar_events(date(2027,2,1),date(2027,12,31))


@pytest.mark.parametrize('change',[
    lambda s:'<html>captcha_form</html>',lambda s:s.replace('10:00 a.m. (EST)',''),
    lambda s:s.replace('<td>5*</td><td>7</td>','<td>5*</td>'),
    lambda s:s.replace('Manufacturing PMI','S&P Global PMI'),
])
def test_calendar_rejects_challenges_incomplete_dates_and_other_pmi(change):
    with pytest.raises(ValueError):sync.parse_calendar(change(calendar()),rules(),NOW.isoformat())


def test_period_and_et_clock_need_documented_methodology():
    for key in ('following_month_rule_confirmed','release_clock_confirmed'):
        proof=rules();proof['services'][key]=False
        with pytest.raises(ValueError):sync.parse_calendar(calendar(),proof,NOW.isoformat())


@pytest.mark.parametrize('day,poland', [('2026-03-04','16:00'),('2026-03-11','15:00'),('2026-10-27','15:00'),('2026-11-02','16:00')])
def test_iana_clock_accounts_for_different_dst_weeks(monkeypatch,day,poland):
    row=sync.parse_calendar(calendar(),rules(),NOW.isoformat())[0]
    row.update(release_date=day,reference_period=day[:7]+'-01')
    monkeypatch.setattr(agenda,'read_schedule',lambda:{'events':[row]})
    e=agenda.calendar_events(date.fromisoformat(day),date.fromisoformat(day))[0]
    assert datetime.fromisoformat(e['release_datetime_utc'].replace('Z','+00:00')).astimezone(ZoneInfo('Europe/Warsaw')).strftime('%H:%M')==poland


@pytest.mark.parametrize('kind',['manufacturing','services'])
def test_explicit_next_announcement_is_not_the_pr_document_timestamp(kind):
    label=kind.capitalize()
    text=document(kind).replace('</section>',f'<p>ISM then compiles the report for release on the {"first" if kind=="manufacturing" else "third"} business day of the following month.</p><p>The next ISM {label} PMI Report featuring January 2025 data will be released at 10:00 a.m. ET on Monday, February 3, 2025.</p></section>')
    result=import_ism.parse_report(text,kind)
    assert result['next_release']['release_date']=='2025-02-03'
    assert result['next_release']['reference_period']=='2025-01-01'
    assert result['next_release']['release_time']=='10:00:00'
    assert result['published_at'].date()==date(2025,1,3)
    with pytest.raises(ValueError):import_ism.parse_report(text.replace('10:00 a.m.','25:00 a.m.'),kind)


@pytest.mark.parametrize('kind',['manufacturing','services'])
def test_future_missing_report_and_matching_report_keep_separate_states(kind):
    old=doc(kind,period='2026-08-01',published='2026-09-01T14:00:00Z',readings={'2026-08-01':50.0})
    e=event(kind)
    before=agenda.bind_measure(e,[old],datetime(2026,10,1,13,tzinfo=timezone.utc))
    assert before['actual'] is None and before['previous']==50 and before['forecast'] is None
    assert before['missing_reason']['actual']=='not_yet_published'
    pending=agenda.bind_measure(e,[old],NOW)
    assert pending['actual'] is None and pending['missing_reason']['actual']=='ism_report_not_confirmed'
    result=agenda.bind_measure(e,[old,doc(kind,identity=2)],NOW)
    assert result['actual']==51.2 and result['previous']==50.3 and result['unit']=='index points'
    assert result['previous_before_report']['value']==50
    assert result['previous_revision_confirmed'] and not result['revision_confirmed']
    assert result['actual_provenance']['raw_hash']=='2'*64
    assert result['previous_provenance']['document_id']==result['actual_provenance']['document_id']


def test_wrong_kind_period_future_document_and_later_history_rows_cannot_supply_actual():
    e=event()
    for source in [doc('services'),doc(period='2026-10-01'),doc(published='2026-11-01T14:00:00Z')]:
        m=agenda.bind_measure(e,[source],NOW)
        assert m['actual'] is None
    # Latest table may supply explicitly labelled previous context, not an
    # invented historical first publication for September.
    later=doc(period='2026-10-01',readings={'2026-08-01':49,'2026-09-01':52})
    m=agenda.bind_measure(e,[later],NOW)
    assert m['actual'] is None and m['previous']==49 and m['previous_data_version']=='current_vintage'


def test_document_order_uses_published_version_not_import_order_and_missing_previous_stays_missing():
    older=doc(identity=9);newer=doc(identity=2,published='2026-10-02T14:00:00Z',readings={'2026-09-01':52})
    older['retrieved_at']=NOW+timedelta(days=1)
    m=agenda.bind_measure(event(),[newer,older],NOW)
    assert m['actual']==52 and m['previous'] is None
    assert m['actual_provenance']['document_id']==2


def test_previous_revision_in_an_older_version_of_same_report_retains_its_document_identity():
    older=doc(identity=1,readings={'2026-08-01':49,'2026-09-01':51})
    newer=doc(identity=2,published='2026-10-02T14:00:00Z',readings={'2026-08-01':50,'2026-09-01':51.2})
    m=agenda.bind_measure(event(),[older,newer],NOW)
    assert m['previous']==50 and m['previous_before_report']['value']==49 and m['previous_revision_confirmed']
    assert m['previous_before_report']['provenance']['report_month']=='2026-09-01'


def test_rich_calendar_dispatch_never_uses_fred_observations_for_ism():
    e=event()
    fake_fred={'ISM_MANUFACTURING_PMI':[{'observation_date':'2026-09-01','value':99}]}
    result=calendar_readings.bind_events([e],fake_fred,fake_fred,NOW,ism_documents=[doc()])[0]
    assert result['measures'][0]['actual']==51.2 and result['expects_numeric_result']
    required=calendar_agenda.event_resources([e])
    assert required=={'ism:ISM_MANUFACTURING_PMI','ism:calendar'}


def test_schedule_failure_retains_last_good_dates_and_imports_only_explicit_next_announcement(tmp_path,monkeypatch):
    path=tmp_path/'schedule.json';saved=sync.parse_calendar(calendar(),rules(),NOW.isoformat())
    path.write_text(json.dumps({'version':1,'events':saved}),encoding='utf-8')
    proof=rules();proof['manufacturing'].update(published_at=NOW,next_release=dict(reference_period='2027-01-01',release_date='2027-02-01',release_time='10:00:00',source_timezone='America/New_York'))
    recorded={}
    @contextmanager
    def check(resource,scope):
        recorded.update(scope=scope);yield recorded
    monkeypatch.setattr(sync,'availability_check',check)
    monkeypatch.setattr(sync,'ROOT',tmp_path)
    transport=httpx.MockTransport(lambda r:httpx.Response(200,headers={'content-type':'text/html'},text='<form>captcha_form</form>',request=r))
    with httpx.Client(transport=transport) as client:payload=sync.sync_schedule(client,None,NOW,path,proof)
    assert payload['check']['annual_schedule_status']=='error' and recorded['status']=='partial'
    assert len(payload['events'])==len(saved)+1
    assert any(r['release_date']=='2027-02-01' and r['binding_method']=='explicit_next_ism_report' for r in payload['events'])
    assert sync.read_schedule(path)['events']==payload['events']


def test_successful_schedule_refresh_is_idempotent_and_caches_new_status(tmp_path,monkeypatch):
    @contextmanager
    def check(resource,scope):yield {'scope':scope}
    monkeypatch.setattr(sync,'availability_check',check);monkeypatch.setattr(sync,'ROOT',tmp_path)
    path=tmp_path/'schedule.json'
    transport=httpx.MockTransport(lambda r:httpx.Response(200,headers={'content-type':'text/html'},text=calendar(),request=r))
    with httpx.Client(transport=transport) as client:
        first=sync.sync_schedule(client,None,NOW,path,rules())
        second=sync.sync_schedule(client,None,NOW+timedelta(hours=6),path,rules())
    assert len(second['events'])==len(first['events'])==8 and second['check']['status']=='success'
    assert {r['release_date'] for r in first['events']}=={r['release_date'] for r in second['events']}


@pytest.mark.parametrize('wrong', ['kind','month'])
def test_discovered_document_of_wrong_kind_or_month_is_rejected_before_store(monkeypatch,wrong):
    parsed=import_ism.parse_report(document('services' if wrong=='kind' else 'manufacturing'),'services' if wrong=='kind' else 'manufacturing')
    monkeypatch.setattr(import_ism,'fetch_report',lambda *a:(parsed,b'fixture'))
    monkeypatch.setattr(import_ism,'store_report',lambda *a:pytest.fail('Wrong identity cannot be stored'))
    with pytest.raises(ValueError):discover_ism.import_discovered('manufacturing',(date(2025,1,1),'https://www.prnewswire.com/news-releases/test.html'))


def test_schedule_runs_inside_coordinator_and_honors_existing_ism_interval(monkeypatch):
    from app.analytics import overview_refresh as refresh
    class Connection:
        def transaction(self):return nullcontext()
    monkeypatch.setattr(refresh,'FRED_SERIES',set());monkeypatch.setattr(refresh,'inventory',lambda *a:{})
    monkeypatch.setattr(sync,'read_schedule',lambda:{'adapter_version':sync.SCHEDULE_ADAPTER_VERSION})
    prior={key:{'attempted_at':NOW.isoformat()} for key in ['fred:calendar','fed:calendar','ism:calendar',*['ism:'+sid for sid in import_ism.KINDS.values()]]}
    calls=[]
    monkeypatch.setattr(sync,'sync_schedule',lambda *a:(calls.append(a[2]) or {'check':{'status':'success'}}))
    versions,result=refresh.refresh_sources(Connection(),prior,NOW+timedelta(minutes=15))
    assert not calls and next(r for r in result if r['resource']=='ism:calendar')['status']=='cached'
    # Only schedule metadata is due in the next normal job; other provider
    # intervals are independently preserved.
    later=NOW+timedelta(hours=6)
    for key in versions:
        if key!='ism:calendar':versions[key]={'attempted_at':later.isoformat()}
    refresh.refresh_sources(Connection(),versions,later)
    assert calls==[later]


def test_stored_document_paths_follow_existing_importer_data_root_and_hash(tmp_path,monkeypatch):
    import hashlib
    raw=tmp_path/'data/raw/ism/report.html';raw.parent.mkdir(parents=True)
    raw.write_text(document().replace('</section>','<p>ISM then compiles the report for release on the first business day of the following month.</p></section>'),encoding='utf-8')
    digest=hashlib.sha256(raw.read_bytes()).hexdigest()
    class Connection:
        def cursor(self):return self
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def execute(self,*a):pass
        def fetchall(self):return [('ISM_MANUFACTURING_PMI','https://www.prnewswire.com/news-releases/test.html',str(raw.relative_to(tmp_path/'data')),digest,NOW)]
    monkeypatch.setattr(sync,'ROOT',tmp_path)
    result=sync.stored_report_rules(Connection())
    assert result['manufacturing']['following_month_rule_confirmed']
    assert result['manufacturing']['retrieved_at']==NOW and result['manufacturing']['raw_hash']==digest
    raw.write_text('changed content',encoding='utf-8')
    assert sync.stored_report_rules(Connection())=={}


def test_derived_cache_rebuild_preserves_failed_check_original_retrieval_and_provider_cadence(tmp_path,monkeypatch):
    path=tmp_path/'cached.json'
    check={'status':'partial','attempted_at':NOW.isoformat(),'annual_schedule_status':'error'}
    path.write_text(json.dumps({'version':1,'events':[],'check':check}),encoding='utf-8')
    proof=rules();retrieved=NOW-timedelta(days=1)
    proof['manufacturing'].update(published_at=NOW-timedelta(days=20),retrieved_at=retrieved,next_release=dict(reference_period='2026-10-01',release_date='2026-11-02',release_time='10:00:00',source_timezone='America/New_York'))
    monkeypatch.setattr(sync,'stored_report_rules',lambda connection:proof)
    monkeypatch.setattr(sync,'before_request',lambda *a:pytest.fail('Cache rebuilding makes no provider request'))
    payload=sync.rebuild_cached_announcements(None,NOW+timedelta(minutes=5),path)
    assert payload['check']==check and payload['events'][0]['retrieved_at']==retrieved.isoformat()
    assert payload['adapter_version']==sync.SCHEDULE_ADAPTER_VERSION


def test_newer_published_announcement_compares_timezone_aware_instants():
    e={('manufacturing','2026-10-01'):{'priority':3,'retrieved_at':'2026-10-27T14:30:00+00:00','release_date':'2026-11-01'}}
    proof=rules();proof['manufacturing'].update(published_at=datetime.fromisoformat('2026-10-27T11:00:00-04:00'),
        next_release=dict(reference_period='2026-10-01',release_date='2026-11-02',release_time='10:00:00',source_timezone='America/New_York'))
    sync.apply_announcements(e,proof,NOW.isoformat())
    assert e[('manufacturing','2026-10-01')]['release_date']=='2026-11-02'


def test_new_document_invalidates_derived_announcements_without_early_calendar_fetch(monkeypatch):
    from app.analytics import overview_refresh as refresh
    class Connection:
        def transaction(self):return nullcontext()
    @contextmanager
    def check(resource,scope):yield {'scope':scope}
    monkeypatch.setattr(refresh,'availability_check',check)
    monkeypatch.setattr(refresh,'FRED_SERIES',set());monkeypatch.setattr(refresh,'inventory',lambda *a:{})
    prior={key:{'attempted_at':NOW.isoformat()} for key in ['fred:calendar','fed:calendar','ism:calendar','ism:ISM_SERVICES_PMI']}
    monkeypatch.setattr(discover_ism,'fetch_listing',lambda:{'manufacturing':(date(2026,9,1),'https://www.prnewswire.com/news-releases/test.html')})
    monkeypatch.setattr(discover_ism,'import_discovered',lambda *a:{'new_document':True,'report_month':'2026-09-01'})
    monkeypatch.setattr(sync,'read_schedule',lambda:{'adapter_version':sync.SCHEDULE_ADAPTER_VERSION})
    monkeypatch.setattr(sync,'sync_schedule',lambda *a:pytest.fail('Annual-calendar minimum interval must be preserved'))
    calls=[];monkeypatch.setattr(sync,'rebuild_cached_announcements',lambda *a:calls.append(a[1]))
    versions,result=refresh.refresh_sources(Connection(),prior,NOW+timedelta(minutes=15))
    assert calls==[NOW+timedelta(minutes=15)]
    assert versions['ism:calendar']['attempted_at']==NOW.isoformat()
    assert next(r for r in result if r['resource']=='ism:calendar')['outcome']=='rebuilt_from_stored_documents'
