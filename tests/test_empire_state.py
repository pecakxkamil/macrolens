"""Offline direct-publisher fixtures; no production network or database."""
import calendar
import copy
import hashlib
import json
from contextlib import contextmanager
from datetime import date,datetime,timedelta,timezone
from io import BytesIO
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
from app.ingestion import sync_empire_state as sync
from app.analytics import empire_state as agenda
from app.analytics.calendar_readings import bind_events
from app.analytics.calendar_agenda import event_resources

NOW=datetime(2026,10,29,12,tzinfo=timezone.utc)
DATES=[15,17,16,15,15,15,15,17,15,15,16,15]


def html(year=2026,dates=None,published_through=10):
    dates=dates or DATES
    chunks=[]
    for group in range(3):
        months=range(group*4+1,group*4+5)
        chunks.append('<tr>'+''.join('<td>'+calendar.month_abbr[m].upper()+'</td>' for m in months)+'</tr>')
        chunks.append('<tr>'+''.join(f'<td>{dates[m-1]}'+(f'<a href="/medialibrary/media/survey/empire/review/{year}-{m:02}.pdf">report</a>' if m<=published_through else '')+'</td>' for m in months)+'</tr>')
    return '<h1>Empire State Manufacturing Survey</h1><p>Released at or shortly after 8:30 a.m.</p><div><strong>'+str(year)+'</strong></div><table>'+''.join(chunks)+'</table>'


def csv_data(values=('20.6','7.6','25.5'),extra=''):
    return ('surveyDate,GAFDISA,GACDISA\n'+''.join(f'2026-{m:02}-{calendar.monthrange(2026,m)[1]},99,{v}\n' for m,v in zip([8,9,10],values))+extra).encode()


def pages(period,current,previous):
    day=date.fromisoformat(period);prior=date.fromisoformat(sync.previous_month(period))
    return [f'Empire State Manufacturing Survey Seasonally Adjusted November 2020 {calendar.month_name[day.month]} {day.year}',
        f'General Business Conditions Percent Reporting Higher Lower Index {calendar.month_abbr[prior.month]} 45 12 {previous} {calendar.month_abbr[day.month]} 40 13 {current} Change 0 Current Indicators Change from Preceding Month',
        'Future General Business Conditions Index 99']


def pdf(period,current,previous):
    writer=PdfWriter()
    for text in pages(period,current,previous):
        page=writer.add_blank_page(width=612,height=792)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        stream=DecodedStreamObject();stream.set_data(('BT /F1 10 Tf 20 760 Td ('+text+') Tj ET').encode())
        page[NameObject('/Contents')]=writer._add_object(stream)
    output=BytesIO();writer.write(output);return output.getvalue()


class Connection:
    def __init__(self):self.docs=[];self.obs={};self.result=[];self.fail=False
    @contextmanager
    def transaction(self):
        before=copy.deepcopy((self.docs,self.obs))
        try:yield
        except BaseException:self.docs,self.obs=before;raise
    def cursor(self):return self
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def execute(self,sql,args=()):
        if sql.startswith('SELECT id,kind'):
            self.result=[tuple(d[k] for k in ('id','kind','source_url','retrieved_at','http_status','raw_hash','raw_path','metadata')) for d in self.docs]
        elif 'INSERT INTO publisher_documents' in sql:
            ident,source,kind,url,stamp,status,digest,path,meta=args
            existing=next((d for d in self.docs if d['kind']==kind and d['raw_hash']==digest),None)
            if existing:self.result=[]
            else:
                self.docs.append(dict(id=ident,kind=kind,source_url=url,retrieved_at=datetime.fromisoformat(stamp),http_status=status,raw_hash=digest,raw_path=path,metadata=json.loads(meta)))
                self.result=[(ident,)]
        elif sql.startswith('SELECT id FROM publisher_documents'):
            self.result=[(d['id'],) for d in self.docs if d['kind']==args[1] and d['raw_hash']==args[2]]
        elif 'SELECT DISTINCT ON(observation_date)' in sql:
            self.result=[(date.fromisoformat(p),r['value'],date.fromisoformat(r['vintage_date']),r['document_id'],r['publication_document_id']) for p,r in sorted(self.obs.items())]
        elif 'INSERT INTO observation_vintages' in sql:
            if self.fail:
                import psycopg
                raise psycopg.DatabaseError('Synthetic write failure')
            _,period,vintage,value,source,doc,pub,_=args
            self.obs[period]=dict(value=value,vintage_date=str(vintage),document_id=doc,publication_document_id=pub)
        elif 'INSERT INTO series' not in sql:raise AssertionError(sql)
    def fetchall(self):return self.result
    def fetchone(self):return self.result[0] if self.result else None


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    @contextmanager
    def check(*args,**kw):yield {'scope':{},'status':'running'}
    monkeypatch.setattr(sync,'availability_check',check)


def run(tmp_path,connection=None,content=None,status=200,home=None,now=NOW,historical=True):
    connection=connection or Connection();calls=[]
    def handle(req):
        calls.append(str(req.url))
        if req.url==sync.HOME:body=(home or html()).encode()
        elif req.url==sync.CSV:body=content if content is not None else csv_data()
        elif '/2026-09.pdf' in str(req.url):body=pdf('2026-09-01',7.6,20.6)
        elif '/2026-11.pdf' in str(req.url):body=pdf('2026-11-01',42,25.5)
        else:body=pdf('2026-10-01',25.5,7.6)
        return httpx.Response(status,content=body,request=req)
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result=sync.sync_source(client,connection,now,tmp_path,('2026-09-01',) if historical else (),clock=lambda:now)
    return connection,result,calls


@pytest.mark.parametrize('value,expected',[('12.5',12.5),('0',0),('-17.2',-17.2),('ND',None),('',None),('NaN',None),('inf',None)])
def test_current_sa_named_column_and_valid_missing_values(value,expected):
    result=sync.parse_csv(csv_data((value,'1','2')))
    assert result['2026-08-01']==expected and result['2026-10-01']==2


@pytest.mark.parametrize('content',[
    b'surveyDate,GAFDISA\n2026-10-31,12',b'surveyDate,GACDINA\n2026-10-31,12',
    b'surveyDate,GACDISA,GACDISA\n2026-10-31,1,2',b'surveyDate,GACDISA\n',
    b'surveyDate,GACDISA\n2026-10-31',b'surveyDate,GACDISA\n2026-10-31,garbage',
    b'surveyDate,GACDISA\n2026-10-31,101',b'surveyDate,GACDISA\n2026-02-30,1',
    b'surveyDate,GACDISA\n10/31/2026,1',b'surveyDate,GACDISA\n2026-10-31,1\n2026-10-01,2',
    b'surveyDate,GACDISA\n2026-10-31,1\n2026-10-31,1',b'<html>error</html>',
])
def test_invalid_or_conflicting_csv_rejected(content):
    with pytest.raises((ValueError,UnicodeError)):sync.parse_csv(content)


def test_column_reordering_and_year_transition():
    assert sync.parse_csv(b'GACDISA,surveyDate,GAFDISA\n-5,2026-12-31,99\n0,2027-01-31,88')=={'2026-12-01':-5,'2027-01-01':0}
    assert sync.previous_month('2027-01-01')=='2026-12-01'


def test_explicit_calendar_does_not_generate_next_year():
    rows=sync.parse_schedule(html(),{'source_url':sync.HOME})
    assert len(rows)==12
    assert [(r['release_date'],r['reference_period']) for r in rows[-4:]]==[('2026-09-15','2026-09-01'),('2026-10-15','2026-10-01'),('2026-11-16','2026-11-01'),('2026-12-15','2026-12-01')]
    assert not any(r['release_date'].startswith('2027') for r in rows)
    with pytest.raises(ValueError):sync.parse_schedule(html().replace('<td>DEC</td>',''),{})


def test_schedule_change_preserves_identity_history_and_idempotence():
    rows=sync.parse_schedule(html(),{});old={'events':rows,'history':[]}
    changed=sync.parse_schedule(html(dates=DATES[:-2]+[17,15]),{})
    first=sync.merge_schedule(old,changed,NOW.isoformat());again=sync.merge_schedule(first,changed,NOW.isoformat())
    assert len(first['events'])==12 and first['events'][10]['event_id']=='empire-state:2026-11:monthly'
    assert len(first['history'])==1 and first['history']==again['history']
    assert first['history'][0]['previous']['release_date']=='2026-11-16'


def test_pdf_uses_current_table_not_future_or_template_date():
    result=sync.parse_report(pdf('2026-10-01',25.5,7.6),'2026-10-01')
    assert result['current']==25.5 and result['previous']==7.6
    with pytest.raises(ValueError):sync.parse_report(pdf('2026-09-01',7.6,20.6),'2026-10-01')
    wrong=pages('2026-10-01',25.5,7.6);wrong[1]=wrong[1].replace('General Business Conditions','Future General Business Conditions')
    # Future heading must not be accepted as the Current chart.
    with pytest.raises(ValueError):sync.parse_report_text(wrong,'2026-10-01')
    wrong=pages('2026-10-01',25.5,7.6)
    wrong[1]=wrong[1].replace('Current Indicators Change from Preceding Month','Forward-Looking Indicators Expectations Six Months Ahead')
    with pytest.raises(ValueError):sync.parse_report_text(wrong,'2026-10-01')


def events(monkeypatch,connection,start=date(2026,9,1),end=date(2026,12,31)):
    monkeypatch.setattr(agenda,'read_schedule',lambda:sync.read_schedule(connection))
    return agenda.calendar_events(start,end)


def test_real_pipeline_contract_history_previous_and_future(tmp_path,monkeypatch):
    c,result,calls=run(tmp_path)
    assert result['status']=='success' and len(calls)==4 and len(c.obs)==3
    es=events(monkeypatch,c);state=agenda.load_state(c)
    bound=bind_events(es,{'PAYEMS':[{'value':99}]},{},NOW,empire_state=state)
    readings={e['reference_period']:e['measures'][0] for e in bound}
    for p,a,b in [('2026-09-01',7.6,20.6),('2026-10-01',25.5,7.6),('2026-11-01',None,25.5),('2026-12-01',None,None)]:
        m=readings[p];assert (m['actual'],m['previous'],m['forecast'])==(a,b,None)
        assert m['feature_name']=='raw' and m['unit']=='index points'
    assert readings['2026-10-01']['actual_provenance']['source']==sync.SOURCE
    assert readings['2026-09-01']['data_version']=='current_vintage'
    assert event_resources(es)=={'nyfed:empire-state'}
    assert 'fred_snapshot' not in json.dumps(bound,default=str)


def test_repeated_import_is_idempotent_and_revision_keeps_raw(tmp_path):
    c,_,_=run(tmp_path);before=copy.deepcopy((c.docs,c.obs))
    run(tmp_path,c)
    assert (c.docs,c.obs)==before
    original=next(d for d in c.docs if d['kind']=='csv')
    old_bytes=(tmp_path/(original['raw_hash']+'.raw')).read_bytes()
    _,result,_=run(tmp_path,c,content=csv_data(('20.6','7.8','25.5')),now=NOW+timedelta(hours=1))
    assert c.obs['2026-09-01']['value']==7.8
    assert result['historical_revisions'][0]['before']==7.6
    assert (tmp_path/(original['raw_hash']+'.raw')).read_bytes()==old_bytes
    _,result,_=run(tmp_path,c,now=NOW+timedelta(hours=2))
    assert c.obs['2026-09-01']['value']==7.8 and not result['csv_validated']


@pytest.mark.parametrize('status',[403,404,503])
def test_http_failure_preserves_last_good_schedule_and_observations(tmp_path,status):
    c,_,_=run(tmp_path);before=copy.deepcopy((c.docs,c.obs))
    _,result,_=run(tmp_path,c,status=status)
    assert result['status']=='error' and before==(c.docs,c.obs)


def test_malformed_csv_and_partial_provider_file_preserve_last_good(tmp_path):
    c,_,_=run(tmp_path);old=copy.deepcopy(c.obs)
    for bad in [b'broken',b'surveyDate,GACDISA\n2026-10-31,25.5']:
        _,r,_=run(tmp_path,c,content=bad)
        assert not r['csv_validated'] and c.obs==old


def test_november_row_without_publication_receipt_never_actual(tmp_path,monkeypatch):
    c,_,_=run(tmp_path)
    later=datetime(2026,11,16,16,tzinfo=timezone.utc)
    _,result,_=run(tmp_path,c,content=csv_data(extra='2026-11-30,77,42\n'),now=later)
    e=events(monkeypatch,c,date(2026,11,16),date(2026,11,16))[0]
    m=agenda.bind_measure(e,agenda.load_state(c),later)
    assert m['actual'] is None and m['previous']==25.5
    assert result['missing_results']['2026-11-01']=='empire_report_not_confirmed'


def test_pdf_exists_csv_old_and_first_result_conflict():
    event={'release_date':'2026-11-16','release_time':'08:30:00'}
    later=datetime(2026,11,16,16,tzinfo=timezone.utc)
    report={'reference_period':'2026-11-01','current':7}
    assert sync.admitted('2026-11-01',None,event,report,None,later)=='observation_missing'
    assert sync.admitted('2026-11-01',9,event,report,None,later)=='empire_source_conflict'
    assert sync.admitted('2026-11-01',7,event,report,None,later) is None
    assert sync.admitted('2026-11-01',7,event,report,None,later-timedelta(hours=4))=='not_yet_published'


def test_sql_failure_rolls_back_all_published_state(tmp_path):
    c=Connection();c.fail=True
    import psycopg
    with pytest.raises(psycopg.DatabaseError):run(tmp_path,c)
    assert c.docs==[] and c.obs=={}
    assert not list(tmp_path.glob('*.tmp'))


def test_pdf_available_csv_lags_then_verified_new_report_import(tmp_path,monkeypatch):
    c,_,_=run(tmp_path)
    later=datetime(2026,11,16,16,tzinfo=timezone.utc);home=html(published_through=11)
    _,result,_=run(tmp_path,c,home=home,now=later,historical=False)
    e=events(monkeypatch,c,date(2026,11,16),date(2026,11,16))[0]
    m=agenda.bind_measure(e,agenda.load_state(c),later)
    assert e['document_status']=='available' and m['actual'] is None and m['previous']==25.5
    assert result['status']=='partial' and result['result_pending']
    _,result,calls=run(tmp_path,c,home=home,now=later+timedelta(minutes=10),historical=False,content=csv_data(extra='2026-11-30,99,42\n'))
    e=events(monkeypatch,c,date(2026,11,16),date(2026,11,16))[0]
    m=agenda.bind_measure(e,agenda.load_state(c),later+timedelta(minutes=10))
    assert (m['actual'],m['previous'],m['forecast'])==(42,25.5,None)
    assert result['status']=='success' and len(calls)==3 and len(c.obs)==4
    assert m['actual_provenance']['column']=='GACDISA'


def test_existing_previous_context_cannot_be_mistaken_for_published_actual(tmp_path,monkeypatch):
    c,_,_=run(tmp_path)
    e=events(monkeypatch,c,date(2026,8,1),date(2026,8,31))[0]
    m=agenda.bind_measure(e,agenda.load_state(c),NOW)
    assert m['actual'] is None and c.obs['2026-08-01']['publication_document_id'] is None


def test_coordinator_uses_existing_slow_interval_and_lock_runner(monkeypatch):
    from app.analytics import overview_refresh as refresh
    from app.ingestion import sync_ism_calendar,import_ism
    monkeypatch.setattr(refresh,'FRED_SERIES',set());monkeypatch.setattr(refresh,'inventory',lambda *a:{})
    monkeypatch.setattr(sync_ism_calendar,'read_schedule',lambda:{'adapter_version':sync_ism_calendar.SCHEDULE_ADAPTER_VERSION})
    resources=['fred:calendar','fed:calendar','ism:calendar','adp:calendar','michigan:calendar','nyfed:empire-state',*['ism:'+sid for sid in import_ism.KINDS.values()]]
    prior={k:{'attempted_at':NOW.isoformat()} for k in resources}
    calls=[];monkeypatch.setattr(sync,'sync_source',lambda *a:(calls.append(a[2]) or {'status':'success'}))
    c=Connection();versions,result=refresh.refresh_sources(c,prior,NOW+timedelta(minutes=15))
    assert calls==[] and next(r for r in result if r['resource']=='nyfed:empire-state')['status']=='cached'
    later=NOW+timedelta(hours=6)
    for k in versions:
        if k!='nyfed:empire-state':versions[k]={'attempted_at':later.isoformat()}
    _,result=refresh.refresh_sources(c,versions,later)
    assert calls==[later] and next(r for r in result if r['resource']=='nyfed:empire-state')['status']=='success'


@pytest.mark.parametrize('day,utc,pl',[('2026-03-16','12:30','13:30'),('2026-10-26','12:30','13:30'),('2026-11-16','13:30','14:30'),('2027-03-09','13:30','14:30'),('2027-03-16','12:30','13:30')])
def test_iana_dst_synthetic_clocks(day,utc,pl):
    d=agenda.instant({'release_date':day,'release_time':'08:30:00'})
    assert d.strftime('%H:%M')==utc and d.astimezone(ZoneInfo('Europe/Warsaw')).strftime('%H:%M')==pl


def test_api_carries_rights_and_single_measure(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.main import app
    from app.analytics import calendar_agenda
    c,_,_=run(tmp_path);es=events(monkeypatch,c)
    bound=bind_events(es,{}, {},NOW,empire_state=agenda.load_state(c))
    monkeypatch.setattr(calendar_agenda,'calendar_agenda',lambda *a,**k:{'events':bound})
    data=TestClient(app).get('/api/v1/calendar?start_date=2026-09-01&end_date=2026-12-31&include_readings=true').json()
    assert all(len(e['measures'])==1 for e in data['events'])
    rights=data['events'][0]['usage_rights']
    assert 'Federal Reserve Bank of New York' in rights['copyright'] and rights['terms_url']==sync.TERMS
    assert rights['original_url']==sync.CSV and 'does not endorse' in rights['modifications']


def test_source_check_final_success_joins_the_observation_transaction(monkeypatch):
    from app import source_checks
    recorded=[];final=[];connection=object()
    monkeypatch.setattr(source_checks,'_record',lambda run:recorded.append(copy.deepcopy(run)))
    monkeypatch.setattr(source_checks,'write_run',lambda run,conn=None:final.append((copy.deepcopy(run),conn)))
    with source_checks.availability_check('nyfed:empire-state',connection=connection) as run:
        run['scope']['csv_validated']=True
    assert len(recorded)==1 and recorded[0]['status']=='running'
    assert final[0][0]['status']=='success' and final[0][1] is connection
    assert final[0][0]['scope']['csv_validated']


def test_nonfinite_numeric_overflow_is_missing_not_a_result():
    assert sync.parse_csv(csv_data(('1e999','1','2')))['2026-08-01'] is None
