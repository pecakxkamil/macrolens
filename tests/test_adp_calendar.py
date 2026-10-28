"""Synthetic monthly ADP metadata only. No copyrighted payroll result fixtures."""
import copy
import hashlib
import json
from contextlib import contextmanager, nullcontext
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest
from app.ingestion import sync_adp_calendar as sync
from app.analytics import adp_calendar as agenda
from app.analytics.calendar_readings import bind_events
from app.analytics.calendar_agenda import event_resources

NOW=datetime(2026,10,28,20,tzinfo=timezone.utc)
URL='https://mediacenter.adp.com/2026-09-30-ADP-National-Employment-Report-Monthly'
PROOF={'source_url':URL,'retrieved_at':NOW.isoformat(),'raw_hash':'a'*64,'document_date':'2026-09-30','response_body_retained':False}


def release(period='September',day='Sep 30, 2026',next_date='November 4, 2026',clock=' at 8:15 a.m. ET'):
    return f'<title>ADP National Employment Report: Monthly private employment</title><p>{day}</p><h2>{period} 2026 Report Highlights</h2><p>The October 2026 ADP National Employment Report will be released on {next_date}{clock}.</p>'


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    @contextmanager
    def check(*a,**k):yield {'scope':{},'status':'running'}
    monkeypatch.setattr(sync,'availability_check',check)


def test_september_same_month_and_november_exact_period_not_month_lag():
    rows=sync.parse_release(release(),URL,PROOF,NOW)
    assert [(r['release_date'],r['reference_period']) for r in rows]==[('2026-09-30','2026-09-01'),('2026-11-04','2026-10-01')]
    assert rows[0]['document_status']=='available' and rows[1]['document_status']=='unconfirmed'
    assert rows[1]['release_time']=='08:15:00'


@pytest.mark.parametrize('clock',['',' at 8:15 a.m. ET'])
def test_missing_clock_is_not_guessed(clock):
    row=sync.parse_release(release(clock=clock),URL,PROOF,NOW)[1]
    assert row['time_status']==('confirmed' if clock else 'unconfirmed')
    assert row['release_time']==('08:15:00' if clock else None)


@pytest.mark.parametrize('bad',[
    '<title>ADP National Employment Report Preliminary Estimate for September</title>',
    '<title>NER Pulse</title>',
    release().replace('September 2026 Report Highlights','September Report Highlights'),
    release().replace('Sep 30, 2026','Sep 29, 2026'),
    release()+release(period='August'),
])
def test_wrong_product_period_date_or_conflict_is_rejected(bad):
    with pytest.raises(ValueError):sync.parse_release(bad,URL,PROOF,NOW)


def test_pulse_url_and_future_documents_never_become_monthly():
    for url in [URL.replace('Monthly','Preliminary-Estimate'),URL.replace('Monthly','NER-Pulse'),URL.replace('2026-09-30','2026-12-02')]:
        with pytest.raises(ValueError):sync.parse_release(release(),url,PROOF,NOW)
    html=f'<a href="{URL}">ADP National Employment Report: Monthly</a><a href="{URL.replace("Monthly","Preliminary-Estimate")}">ADP National Employment Report Preliminary Estimate</a>'
    assert sync.discover_monthly(html,NOW)==[URL]


def test_discovery_requires_official_https_and_explicit_monthly_title():
    html=''.join(f'<a href="{url}">ADP National Employment Report: Monthly</a>' for url in [URL,URL.replace('mediacenter.adp.com','example.com'),URL.replace('https:','http:'),URL.replace('2026-09-30','2027-01-06')])
    assert sync.discover_monthly(html,NOW)==[URL]


def test_stable_identity_move_history_and_idempotence():
    old=sync.row('2026-10-01','2026-11-04',PROOF,'08:15:00');rows={old['event_id']:old};history=[]
    moved={**old,'release_date':'2026-11-05'}
    sync.merge_rows(rows,[moved],NOW.isoformat(),history)
    assert list(rows)==['adp:2026-10:monthly'] and len(history)==1
    assert rows[old['event_id']]['schedule_status']=='changed'
    sync.merge_rows(rows,[moved],NOW.isoformat(),history)
    assert len(history)==1


def test_older_document_cannot_replace_newer_evidence():
    newer=sync.row('2026-09-01','2026-09-30',PROOF,document=URL);rows={newer['event_id']:copy.deepcopy(newer)}
    older=sync.row('2026-09-01','2026-10-07',{**PROOF,'document_date':'2026-09-02'})
    sync.merge_rows(rows,[older],NOW.isoformat(),[])
    assert rows[newer['event_id']]==newer


def test_moved_date_does_not_keep_an_old_clock_or_document():
    old=sync.row('2026-09-01','2026-09-30',PROOF,'08:15:00',URL)
    rows={old['event_id']:old};new=sync.row('2026-09-01','2026-10-01',PROOF)
    sync.merge_rows(rows,[new],NOW.isoformat(),[])
    assert rows[old['event_id']]['release_time'] is None and rows[old['event_id']]['document_url'] is None


def test_date_only_calendar_identity_survives_later_period_confirmation():
    old=sync.row('2026-11-01','2026-12-02',PROOF)
    old.update(event_id='adp:calendar:2026-12:monthly',reference_period=None,reference_period_status='unconfirmed')
    rows={old['event_id']:old};history=[]
    sync.merge_rows(rows,[sync.row('2026-11-01','2026-12-02',PROOF,'08:15:00')],NOW.isoformat(),history)
    assert len(rows)==1 and rows[old['event_id']]['reference_period']=='2026-11-01' and len(history)==1
    sync.merge_rows(rows,[sync.row('2026-11-01','2026-12-02',PROOF,'08:15:00')],NOW.isoformat(),history)
    assert len(rows)==1 and len(history)==1


def test_reviewed_and_runtime_snapshots_do_not_duplicate_history(tmp_path,monkeypatch):
    row=sync.row('2026-10-01','2026-11-04',PROOF)
    entry={'event_id':row['event_id'],'replaced_at':NOW.isoformat(),'previous':row}
    payload={'version':1,'events':[row],'history':[entry]}
    a=tmp_path/'reviewed.json';b=tmp_path/'snapshot.json'
    for p in [a,b]:p.write_text(json.dumps(payload))
    monkeypatch.setattr(sync,'REVIEWED',a);monkeypatch.setattr(sync,'SNAPSHOT',b)
    assert sync.read_schedule()['history']==[entry]


@pytest.mark.parametrize('day,utc,poland',[
    ('2026-03-11','12:15','13:15'),('2026-09-02','12:15','14:15'),
    ('2026-09-30','12:15','14:15'),('2026-10-28','12:15','13:15'),
    ('2026-11-04','13:15','14:15'),('2026-12-02','13:15','14:15')])
def test_iana_clock_and_separate_numeric_gate(monkeypatch,day,utc,poland):
    row=sync.row(day[:7]+'-01',day,PROOF,'08:15:00')
    monkeypatch.setattr(agenda,'read_schedule',lambda:{'events':[row]})
    e=agenda.calendar_events(date.fromisoformat(day),date.fromisoformat(day))[0]
    assert e['release_datetime_utc']==day+'T'+utc+':00Z'
    assert datetime.fromisoformat(e['release_datetime_utc'].replace('Z','+00:00')).astimezone(ZoneInfo('Europe/Warsaw')).strftime('%H:%M')==poland
    assert e['expects_numeric_result'] and e['result_integration_status']=='publisher_permission_required'
    assert e['series']==[] and e['measures']==[] and all(e[k] is None for k in ['actual','previous','forecast'])
    assert bind_events([e],{'PAYEMS':[{'value':7}]},{'ADPMNUSNERSA':[{'value':9}]},NOW)==[e]
    assert 'adp:calendar' in event_resources([e])


def run(tmp_path,failed=False,content=None):
    calls=[]
    def handle(req):
        calls.append(str(req.url))
        if failed:return httpx.Response(503,request=req)
        body=('<div id="root"></div>' if str(req.url)==sync.HOME else f'<a href="{URL}">ADP National Employment Report: Monthly</a>' if str(req.url)==sync.LISTING else content or release())
        return httpx.Response(200,text=body,request=req)
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:result=sync.sync_schedule(client,NOW,tmp_path/'schedule.json')
    return result,calls


def test_coordinated_metadata_only_does_not_claim_js_schedule_success(tmp_path):
    result,calls=run(tmp_path,content=release()+'<div>RESULT-DO-NOT-RETAIN</div>')
    assert len(calls)==3 and len(result['events'])==2
    assert result['check']['status']=='partial' and result['check']['calendar_automation']=='bounded_announcements_only'
    assert all(c['response_body_retained'] is False and 'capture_path' not in c for c in result['check']['captures'])
    assert 'RESULT-DO-NOT-RETAIN' not in json.dumps(result)
    assert result['check']['captures'][-1]['raw_hash']==hashlib.sha256((release()+'<div>RESULT-DO-NOT-RETAIN</div>').encode()).hexdigest()
    again,_=run(tmp_path,content=release()+'<div>RESULT-DO-NOT-RETAIN</div>')
    assert result['events']==again['events'] and result['history']==again['history']
    assert not any(r['release_date'].startswith('2027') for r in result['events'])


def test_fetch_or_parser_failure_keeps_all_last_good_rows(tmp_path):
    first,_=run(tmp_path)
    for failure,content in [(True,None),(False,'<h1>Temporarily unavailable</h1>')]:
        result,_=run(tmp_path,failed=failure,content=content)
        assert result['events']==first['events'] and result['check']['status']=='partial'
        assert result['check']['errors'][-1]['source_url']==(sync.LISTING if failure else URL)


def test_coordinator_reuses_existing_slow_interval(monkeypatch):
    from app.analytics import overview_refresh as refresh
    from app.ingestion import sync_michigan_calendar,sync_ism_calendar,import_ism
    class Connection:
        def transaction(self):return nullcontext()
    monkeypatch.setattr(refresh,'FRED_SERIES',set());monkeypatch.setattr(refresh,'inventory',lambda *a:{})
    monkeypatch.setattr(sync_ism_calendar,'read_schedule',lambda:{'adapter_version':sync_ism_calendar.SCHEDULE_ADAPTER_VERSION})
    calls=[];monkeypatch.setattr(sync,'sync_schedule',lambda *a:(calls.append(a[1]) or {'check':{'status':'partial'}}))
    prior={k:{'attempted_at':NOW.isoformat()} for k in ['fred:calendar','fed:calendar','ism:calendar','michigan:calendar','adp:calendar',*['ism:'+sid for sid in import_ism.KINDS.values()]]}
    versions,results=refresh.refresh_sources(Connection(),prior,NOW+timedelta(minutes=15))
    assert calls==[] and next(r for r in results if r['resource']=='adp:calendar')['status']=='cached'
    later=NOW+timedelta(hours=6)
    for k in versions:
        if k!='adp:calendar':versions[k]={'attempted_at':later.isoformat()}
    _,results=refresh.refresh_sources(Connection(),versions,later)
    assert calls==[later] and next(r for r in results if r['resource']=='adp:calendar')['status']=='partial'


def test_fastapi_keeps_adp_separate_from_employment(monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.main import app
    from app.analytics import calendar_agenda
    monkeypatch.setattr(agenda,'read_schedule',lambda:{'events':[sync.row('2026-10-01','2026-11-04',PROOF,'08:15:00')]})
    events=agenda.calendar_events(date(2026,11,4),date(2026,11,4))
    monkeypatch.setattr(calendar_agenda,'calendar_agenda',lambda *a,**k:{'events':events})
    response=TestClient(app).get('/api/v1/calendar?start_date=2026-11-04&end_date=2026-11-04&include_readings=true')
    assert response.status_code==200
    e=response.json()['events'][0]
    assert e['event_type']=='adp_monthly' and e['category']=='labor' and e['forecast'] is None


def test_catalog_has_no_adp_numeric_ingestion():
    from app.database.sync_series import load_series_config
    assert 'ADPMNUSNERSA' not in load_series_config()


def test_reviewed_official_metadata_has_bounded_dates_and_no_inferred_december_fields():
    data=json.loads(sync.REVIEWED.read_text(encoding='utf-8'))
    rows={r['release_date']:r for r in data['events']}
    assert sorted(rows)==['2026-07-01','2026-08-05','2026-09-02','2026-09-30','2026-11-04','2026-12-02']
    assert rows['2026-09-02']['reference_period']=='2026-08-01'
    assert rows['2026-09-30']['reference_period']=='2026-09-01'
    assert rows['2026-11-04']['reference_period']=='2026-10-01'
    assert rows['2026-12-02']['reference_period'] is None and rows['2026-12-02']['release_time'] is None
    assert all('actual' not in r and 'previous' not in r for r in rows.values())


def test_explicit_document_period_and_release_year_are_independent():
    url='https://mediacenter.adp.com/2027-01-06-ADP-National-Employment-Report-Monthly'
    html=release(period='December',day='Jan 6, 2027',next_date='February 3, 2027').replace('The October 2026','The January 2027')
    rows=sync.parse_release(html,url,{'source_url':url},datetime(2027,1,8,tzinfo=timezone.utc))
    assert [(r['reference_period'],r['release_date']) for r in rows]==[('2026-12-01','2027-01-06'),('2027-01-01','2027-02-03')]
