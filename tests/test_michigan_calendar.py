"""Offline schedule/document metadata only; no licensed numerical result fixtures."""
import calendar
import copy
from contextlib import contextmanager
from datetime import date, datetime, timezone
from io import BytesIO
import json
from pathlib import Path

import httpx
import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from app.ingestion import sync_michigan_calendar as sync
from app.analytics import michigan_calendar as agenda
from app.analytics.calendar_readings import bind_events
from app.analytics.calendar_agenda import event_resources

NOW=datetime(2026,10,28,16,tzinfo=timezone.utc)
DATES=json.loads((Path(__file__).parent/'fixtures/michigan_release_dates.json').read_text())

def pdf(year,dates=None):
    lines=[f'RELEASE DATES FOR {year}:']
    for i,day in enumerate(dates or DATES[str(year)]):
        d=date.fromisoformat(day)
        lines.append(f'{calendar.month_name[d.month]} {d.day} {calendar.month_name[i//2+1]} {"Prelim" if i%2==0 else "Final"}')
    lines.append('SURVEYS OF CONSUMERS UNIVERSITY OF MICHIGAN')
    writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(('BT /F1 10 Tf 20 760 Td 14 TL '+' '.join('('+s+') Tj T*' for s in lines)+' ET').encode())
    page[NameObject('/Contents')]=writer._add_object(stream)
    output=BytesIO();writer.write(output);return output.getvalue()

def home(day=6,stage='Preliminary',period='November'):
    return f'<h1>Final Results for October 2026</h1><p>Next data release: Friday, November {day}, 2026 for {stage} {period} data at 10am ET</p>'

def listing(include_final=True):
    final='<a href="fetchdoc.php?docid=82114">September Final Results</a>' if include_final else ''
    return '<h1>2026 Reports</h1><div><span class="date">September 2026</span><a href="fetchdoc.php?docid=81974">September Preliminary Results</a>'+final+'</div>'

@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    @contextmanager
    def check(*a,**k):yield {'scope':{},'status':'running'}
    monkeypatch.setattr(sync,'availability_check',check)

def run(tmp_path,content=None,years=(2026,2027),failure=False,archive=None,dates=None):
    requests=[]
    info=''.join(f'<a href="fetchdoc.php?docid={y}">{y} Release Dates</a>' for y in years)
    def handle(req):
        requests.append(str(req.url))
        if failure:return httpx.Response(503,request=req)
        if str(req.url)==sync.INFO:text=info
        elif req.url.path=='/fetchdoc.php':return httpx.Response(200,content=pdf(int(req.url.params['docid']),dates),request=req)
        elif req.url.path=='/reports.php':text=listing() if archive is None else archive
        else:text=content or home()
        return httpx.Response(200,text=text,request=req)
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result=sync.sync_schedule(client,NOW,tmp_path/'schedule.json',tmp_path/'raw')
    return result,requests

def test_full_official_dates_stages_and_exception_without_inference(tmp_path):
    result,requests=run(tmp_path)
    assert len(result['events'])==48
    rows={e['event_id']:e for e in result['events']}
    for year in (2026,2027):
        for i,day in enumerate(DATES[str(year)]):
            period=f'{year}-{i//2+1:02}-01';stage='preliminary' if i%2==0 else 'final'
            assert rows[sync.identity(period,stage)]['release_date']==day
    assert rows['michigan:2027-03:final']['release_date']=='2027-03-25'
    assert date(2027,3,25).weekday()==3
    assert not any('81974' in u or '82114' in u for u in requests) # links, not reports

def test_metadata_only_numeric_report_and_independent_document_stage(tmp_path,monkeypatch):
    result,_=run(tmp_path)
    monkeypatch.setattr(agenda,'read_schedule',lambda:result)
    events=agenda.calendar_events(date(2026,9,1),date(2026,12,31))
    assert len(events)==8 and all(e['expects_numeric_result'] and e['series']==[] and e['measures']==[] for e in events)
    assert all(e['actual'] is None and e['previous'] is None and e['forecast'] is None for e in events)
    assert all(e['result_status']=='restricted' and e['result_integration_status']=='publisher_permission_required' for e in events)
    assert events[0]['document_url'].endswith('81974') and events[1]['document_url'].endswith('82114')
    assert events[0]['reference_period']==events[1]['reference_period']=='2026-09-01'
    assert events[2]['document_status']=='unconfirmed' and events[3]['document_kind']=='current_summary_link'
    assert events[4]['release_datetime_utc']=='2026-11-06T15:00:00Z'
    assert all(e['release_datetime_utc'] is None for i,e in enumerate(events) if i!=4)
    # Even injected delayed FRED readings cannot cross the licensing gate.
    bound=bind_events(events,{'UMCSENT':[{'value':1}]},{'MICH':[{'value':2}]},NOW)
    assert bound==events and 'michigan:calendar' in event_resources(events)

def test_missing_2027_is_not_generated_and_missing_clock_is_not_midnight(tmp_path):
    result,_=run(tmp_path,years=(2026,),content='<h1>Final Results for October 2026</h1>')
    assert len(result['events'])==24
    assert all(e['release_time'] is None for e in result['events'])
    assert not any(e['reference_period'].startswith('2027') for e in result['events'])

def test_date_change_keeps_identity_and_history_and_idempotence(tmp_path):
    first,_=run(tmp_path)
    moved,_=run(tmp_path,content=home(day=5))
    key='michigan:2026-11:preliminary'
    row=next(e for e in moved['events'] if e['event_id']==key)
    assert row['release_date']=='2026-11-05' and row['schedule_status']=='changed'
    assert any(e['event_id']==key for e in moved['history'])
    again,_=run(tmp_path,content=home(day=5))
    assert len(again['events'])==48 and len(again['history'])==len(moved['history'])
    assert len(first['events'])==len(moved['events'])

def test_failed_or_shorter_source_retains_last_good_dates_clocks_and_links(tmp_path):
    first,_=run(tmp_path)
    failed,_=run(tmp_path,failure=True)
    assert failed['events']==first['events'] and failed['check']['status']=='partial'
    shorter,_=run(tmp_path,years=(2026,),archive='<h1>2026 Reports</h1>')
    assert len(shorter['events'])==48
    assert next(e for e in shorter['events'] if e['event_id']=='michigan:2026-09:final')['document_url'].endswith('82114')

def test_no_final_copy_into_preliminary_and_publication_not_inferred_from_clock(tmp_path):
    result,_=run(tmp_path,archive=listing(False))
    rows={e['event_id']:e for e in result['events']}
    assert rows['michigan:2026-09:final']['document_status']=='unconfirmed'
    assert rows['michigan:2026-09:preliminary']['document_url'].endswith('81974')
    assert rows['michigan:2026-11:preliminary']['document_status']=='unconfirmed'
    assert rows['michigan:2026-11:preliminary']['time_status']=='confirmed'

@pytest.mark.parametrize('year',[2026,2027])
def test_parser_rejects_incomplete_wrong_year_or_duplicate_pdf(year):
    with pytest.raises(ValueError):sync.parse_schedule(pdf(year),year+1,{})
    with pytest.raises(ValueError):sync.parse_schedule(pdf(year,DATES[str(year)][:-1]),year,{})
    with pytest.raises(ValueError):sync.parse_schedule(b'<html>403</html>',year,{})

def test_home_body_is_not_retained_but_actual_pdf_hashes_are(tmp_path):
    result,_=run(tmp_path,content=home()+'<p>PRIVATE-RESULT-BODY</p>')
    assert 'PRIVATE-RESULT-BODY' not in json.dumps(result)
    assert not any('PRIVATE-RESULT-BODY' in p.read_text(errors='ignore') for p in (tmp_path/'raw').iterdir())
    import hashlib
    for capture in result['check']['captures']:
        if capture['response_body_retained']:
            assert hashlib.sha256(Path(capture['capture_path']).read_bytes()).hexdigest()==capture['raw_hash']

@pytest.mark.parametrize('day,expected',[('2026-03-13','2026-03-13T14:00:00Z'),('2026-10-23','2026-10-23T14:00:00Z'),('2026-11-06','2026-11-06T15:00:00Z')])
def test_iana_clock_is_only_applied_with_evidence(monkeypatch,day,expected):
    row=dict(event_id='michigan:'+day[:7]+':preliminary',stage='preliminary',reference_period=day[:7]+'-01',release_date=day,
        release_time='10:00:00',time_status='confirmed',schedule_provenance={'source_url':sync.INFO,'retrieved_at':NOW.isoformat()})
    monkeypatch.setattr(agenda,'read_schedule',lambda:{'events':[row]})
    assert agenda.calendar_events(date.fromisoformat(day),date.fromisoformat(day))[0]['release_datetime_utc']==expected

def test_real_fastapi_contract_preserves_numeric_restriction(monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    from app.api.main import app
    from app.analytics import calendar_agenda
    result,_=run(tmp_path);monkeypatch.setattr(agenda,'read_schedule',lambda:result)
    events=agenda.calendar_events(date(2026,11,6),date(2026,11,6))
    monkeypatch.setattr(calendar_agenda,'calendar_agenda',lambda *a,**k:{'events':events})
    r=TestClient(app).get('/api/v1/calendar?start_date=2026-11-06&end_date=2026-11-06&include_readings=true')
    assert r.status_code==200
    e=r.json()['events'][0]
    assert e['expects_numeric_result'] and e['actual'] is None and e['result_status']=='restricted'


def test_coordinator_uses_existing_cooldown_and_records_failed_attempt(monkeypatch):
    from datetime import timedelta
    from contextlib import nullcontext
    from app.analytics import overview_refresh as refresh
    from app.ingestion import sync_ism_calendar, import_ism
    class Connection:
        def transaction(self):return nullcontext()
    monkeypatch.setattr(refresh,'FRED_SERIES',set())
    monkeypatch.setattr(refresh,'inventory',lambda *a:{})
    monkeypatch.setattr(sync_ism_calendar,'read_schedule',lambda:{'adapter_version':sync_ism_calendar.SCHEDULE_ADAPTER_VERSION})
    prior={key:{'attempted_at':NOW.isoformat()} for key in ['fred:calendar','fed:calendar','ism:calendar','michigan:calendar',*['ism:'+sid for sid in import_ism.KINDS.values()]]}
    calls=[]
    monkeypatch.setattr(sync,'sync_schedule',lambda *a:(calls.append(a[1]) or {'check':{'status':'partial'}}))
    versions,results=refresh.refresh_sources(Connection(),prior,NOW+timedelta(minutes=15))
    assert calls==[] and next(r for r in results if r['resource']=='michigan:calendar')['status']=='cached'
    later=NOW+timedelta(hours=6)
    for key in versions:
        if key!='michigan:calendar':versions[key]={'attempted_at':later.isoformat()}
    versions,results=refresh.refresh_sources(Connection(),versions,later)
    assert calls==[later] and versions['michigan:calendar']['attempted_at']==later.isoformat()
    assert next(r for r in results if r['resource']=='michigan:calendar')['status']=='partial'


def test_corrupt_snapshot_is_rejected_as_a_whole(tmp_path):
    result,_=run(tmp_path)
    result['events'].append({'stage':'wrong'})
    path=tmp_path/'corrupt.json';path.write_text(json.dumps(result))
    assert sync.read_schedule(path)['events']==[]


def test_source_check_does_not_claim_an_unpublished_year():
    from app.analytics.source_checks import eligible
    row={'resource':'michigan:calendar','scope':{'confirmed_years':[2026]}}
    assert eligible(row,date(2026,11,1))
    assert not eligible(row,date(2026,12,31),date(2027,1,1))


def test_unchanged_annual_table_cannot_rollback_newer_home_date_on_error(tmp_path):
    run(tmp_path,content=home(day=5))
    # The annual table is unchanged; only the next announcement is unavailable.
    moved,_=run(tmp_path,content='<h1>Temporarily unavailable</h1>')
    row=next(e for e in moved['events'] if e['event_id']=='michigan:2026-11:preliminary')
    assert row['release_date']=='2026-11-05' and row['time_status']=='confirmed'
    assert row['date_provenance']['source_url']==sync.HOME
    assert moved['check']['status']=='partial'


def test_first_clock_confirmation_is_not_a_claim_of_rescheduling(tmp_path):
    run(tmp_path,content='<h1>Final Results for October 2026</h1>')
    confirmed,_=run(tmp_path)
    row=next(e for e in confirmed['events'] if e['event_id']=='michigan:2026-11:preliminary')
    assert row['time_status']=='confirmed' and row['schedule_status']=='confirmed'
