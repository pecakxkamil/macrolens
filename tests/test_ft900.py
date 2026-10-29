"""FT900 synthetic ZIP/XML, PDF and HTTP fixtures; no real provider or DB."""
import copy
import hashlib
import io
import json
import zipfile
from contextlib import contextmanager
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
from xml.sax.saxutils import escape

import httpx
import pytest
from app.ingestion import sync_ft900 as s
from app.analytics import ft900_calendar as a
from app.analytics.calendar_readings import bind_events
from app.analytics.calendar_agenda import event_resources
from tests.test_empire_state import Connection
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject

NOW=datetime(2026,10,29,12,tzinfo=timezone.utc)
BASE={'2026-05-01':('-75752','319979','395731'), '2026-06-01':('-71182','317335','388517'),
      '2026-07-01':('-92826','310723','403550'), '2026-08-01':('-105572','315182','420754')}


def workbook(values=None,layout=('balance','exports','imports'),sheet_name='Exhibit',wrong_first=False,unit='millions of dollars',sa='Seasonally Adjusted',bop='balance of payments (BOP) basis',formula=None,duplicate=False):
    import calendar
    values=values or BASE
    def cell(column,row,value):
        ref=chr(64+column)+str(row)
        f='<f>1+1</f>' if ref==formula else ''
        return f'<c r="{ref}" t="inlineStr">{f}<is><t>{escape(str(value))}</t></is></c>'
    rows={1:{1:'Part A: '+sa},2:{1:'Exhibit 1. U.S. International Trade in Goods and Services'},3:{1:'In '+unit},4:{1:'Data are presented on a '+bop},5:{1:'Period'},6:{}}
    for i,group in enumerate(layout):
        first=2+3*i;rows[5][first]=group.title()
        rows[6].update({first:'Total',first+1:'Goods (1)',first+2:'Services'})
    last_year=None;n=7
    for period,triplet in sorted(values.items()):
        year=int(period[:4]);month=int(period[5:7])
        if year!=last_year:rows[n]={1:str(year)};n+=1;last_year=year
        rows[n]={1:calendar.month_name[month]+(' (R)' if month==7 else '')}
        for i,group in enumerate(layout):rows[n].update({2+3*i:triplet[('balance','exports','imports').index(group)],3+3*i:'999',4+3*i:'888'})
        n+=1
    if duplicate:rows[n]=dict(rows[n-1]);n+=1
    latest_month=int(max(values)[5:7])
    if latest_month==12:rows[n]={1:str(int(max(values)[:4])+1)};n+=1
    rows[n]={1:calendar.month_name[latest_month%12+1]}  # empty printed future month
    xml='<worksheet xmlns="'+s.NS['s']+'"><sheetData>'+''.join('<row r="'+str(r)+'">'+''.join(cell(c,r,v) for c,v in sorted(row.items()))+'</row>' for r,row in rows.items())+'</sheetData><mergeCells>'+''.join(f'<mergeCell ref="{chr(66+i*3)}5:{chr(68+i*3)}5"/>' for i in range(3))+'</mergeCells></worksheet>'
    names=['Wrong',sheet_name] if wrong_first else [sheet_name]
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        write=z.writestr
        z.writestr=lambda name,data:write(zipfile.ZipInfo(name,(2026,1,1,0,0,0)),data)
        z.writestr('xl/workbook.xml','<workbook xmlns="'+s.NS['s']+'" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'+''.join(f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>' for i,name in enumerate(names,1))+'</sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships>'+''.join(f'<Relationship Id="rId{i}" Type="x/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(names)+1))+'</Relationships>')
        for i,name in enumerate(names,1):z.writestr(f'xl/worksheets/sheet{i}.xml',xml if name==sheet_name else '<worksheet xmlns="'+s.NS['s']+'"><sheetData/></worksheet>')
    return output.getvalue()


def schedule(day='November 4, 2026'):
    return f'<h2>FT900 U.S. International Trade in Goods and Services</h2><table><tr><th>Statistical Month</th><th>Data Release</th><th>Day</th></tr><tr><td>September 2026</td><td>{day}</td><td>WED</td></tr><tr><td>October 2026</td><td>December 8, 2026</td><td>TUE</td></tr><tr><td>November 2026</td><td>January 7, 2027</td><td>THU</td></tr><tr><td>December 2026</td><td>February 4, 2027</td><td>THU</td></tr><tr><td>January 2027</td><td>March 9, 2027</td><td>TUE</td></tr><tr><td>February 2027</td><td>April 6, 2027</td><td>TUE</td></tr><tr><td>November 2027</td><td>TBD</td><td>TBD</td></tr><tr><td>All releases occur at 8:30am (Eastern)</td><td>TBD</td><td></td></tr></table><h2>Advance Economic Indicators</h2><table><tr><td>September 2026</td><td>October 28, 2026</td><td>WED</td></tr></table>'


def bea():
    rows=[('August 4','June'),('September 3','July'),('October 6','August'),('November 4','September'),('December 8','October')]
    return '<table><tr><th>Year 2026</th></tr>'+''.join(f'<tr><td>{day} 8:30 AM</td><td>News</td><td>{s.OFFICIAL_TITLE}, {period} 2026</td></tr>' for day,period in rows)+'</table>'


def archive(latest=8):
    return '<h1>FT900 Historical Releases</h1>'+''.join(f'<a href="/foreign-trade/Press-Release/ft900/ft900_26{m:02}.pdf">PDF</a>' for m in range(6,latest+1))


def pdf(period='2026-08-01',balance='105.6',day='OCTOBER 6',direction='deficit'):
    import calendar
    month=calendar.month_name[int(period[5:7])]
    release=datetime.strptime(day.title()+', 2026','%B %d, %Y').replace(hour=8,minute=30,tzinfo=s.ZoneInfo('America/New_York'))
    text=f'FOR RELEASE AT 8:30 AM {release.tzname()}, {release.strftime("%A").upper()}, {day}, 2026 U.S. INTERNATIONAL TRADE IN GOODS AND SERVICES, {month.upper()} 2026 The goods and services {direction} was ${balance} billion in {month}.'
    writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(('BT /F1 10 Tf 20 760 Td ('+text+') Tj ET').encode());page[NameObject('/Contents')]=writer._add_object(stream)
    output=io.BytesIO();writer.write(output);return output.getvalue()


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    @contextmanager
    def check(*args,**kwargs):yield {'scope':{},'status':'running'}
    monkeypatch.setattr(s,'availability_check',check)


def run(path,connection=None,book=None,now=NOW,bad=None,home=None,bea_body=None,latest=8):
    connection=connection or Connection();calls=[]
    bodies={s.SCHEDULE:home or schedule(),s.BEA_SCHEDULE:bea_body or bea(),s.ARCHIVE:archive(latest),s.XLSX:book if book is not None else workbook()}
    for period,value,day in [('2026-06-01','73.3','AUGUST 4'),('2026-07-01','88.6','SEPTEMBER 3'),('2026-08-01','105.6','OCTOBER 6'),('2026-09-01','105.0','NOVEMBER 4')]:
        bodies[f'https://www.census.gov/foreign-trade/Press-Release/ft900/ft900_26{period[5:7]}.pdf']=pdf(period,value,day)
    def handle(req):
        url=str(req.url);calls.append(url);body=bodies[url]
        return httpx.Response(503 if bad and bad in url else 200,content=body.encode() if isinstance(body,str) else body,request=req)
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result=s.sync_source(client,connection,now,path,history_periods=('2026-06-01','2026-07-01'),clock=lambda:now)
    return connection,result,calls


def test_schedule_separates_advance_tbd_and_years():
    parsed=s.parse_schedule(schedule().encode(),{'source_url':s.SCHEDULE})
    assert len(parsed['events'])==6 and parsed['tbd_periods']==['2027-11-01']
    assert parsed['events'][0]['release_date']=='2026-11-04'
    assert parsed['events'][2]['reference_period']=='2026-11-01'
    assert parsed['events'][4]['release_date']=='2027-03-09'
    assert not any(r['release_date']=='2026-10-28' for r in parsed['events'])


@pytest.mark.parametrize('layout',[('balance','exports','imports'),('imports','balance','exports'),('exports','imports','balance')])
def test_xlsx_named_total_columns_sheet_and_current_values(layout):
    book=s.parse_xlsx(workbook(layout=layout,wrong_first=True))
    assert book['sheet']=='Exhibit' and book['latest_period']=='2026-08-01'
    assert book['values']['2026-08-01']['balance']=='-105572'
    assert book['values']['2026-07-01']['revised']
    assert book['values']['2026-08-01']['exports']=='315182'


@pytest.mark.parametrize('balance,exports,imports',[('12','22','10'),('0','10','10'),('-12','10','22'),('-1,234 (R)','1,000','2,234')])
def test_signed_surplus_zero_deficit_and_separators(balance,exports,imports):
    book=s.parse_xlsx(workbook({'2026-08-01':(balance,exports,imports)}))
    assert Decimal(book['values']['2026-08-01']['balance'])==Decimal(balance.replace(',','').replace(' (R)',''))


from decimal import Decimal


@pytest.mark.parametrize('kwargs',[{'unit':'billions of dollars'},{'sa':'Not Seasonally Adjusted'},{'bop':'Census basis'},{'formula':'B9'},{'duplicate':True}])
def test_invalid_metadata_formula_duplicate_rejected(kwargs):
    with pytest.raises(ValueError):s.parse_xlsx(workbook(**kwargs))


@pytest.mark.parametrize('triplet',[('12','20','10'),('','1','1'),('0','','1'),('NaN','1','1'),('0','-1','-1')])
def test_bad_arithmetic_empty_nonfinite_rejected(triplet):
    with pytest.raises(ValueError):s.parse_xlsx(workbook({'2026-08-01':triplet}))


@pytest.mark.parametrize('content',[b'not zip',b'PK\x03\x04broken',b'<html>error</html>'])
def test_broken_zip_rejected(content):
    with pytest.raises((ValueError,zipfile.BadZipFile)):s.parse_xlsx(content)


def test_month_year_transition_explicit_and_revised():
    book=s.parse_xlsx(workbook({'2025-12-01':('0','10','10'),'2026-01-01':('-2','8','10')}))
    assert set(book['values'])=={'2025-12-01','2026-01-01'}


def test_report_requires_own_full_month_and_clock():
    assert s.parse_report(pdf(),'2026-08-01')['release_date']=='2026-10-06'
    with pytest.raises(ValueError):s.parse_report(pdf(),'2026-09-01')


def test_live_binding_historical_future_provenance_no_fred(tmp_path,monkeypatch):
    c,result,calls=run(tmp_path)
    original=s.read_schedule
    monkeypatch.setattr(s,'read_schedule',lambda *args:original(c))
    events=bind_events(a.calendar_events(date(2026,1,1),date(2027,12,31)),{},{},NOW,ft900=a.load_state(c))
    readings={e['reference_period']:e['measures'][0] for e in events}
    assert (readings['2026-08-01']['actual'],readings['2026-08-01']['previous'])==(-105.572,-92.826)
    assert (readings['2026-07-01']['actual'],readings['2026-07-01']['previous'])==(-92.826,-71.182)
    assert readings['2026-09-01']['actual'] is None and readings['2026-09-01']['previous']==-105.572
    assert readings['2026-10-01']['actual'] is None and readings['2026-10-01']['previous'] is None
    assert all(m['forecast'] is None for m in readings.values())
    assert readings['2026-07-01']['revision_confirmed']
    assert event_resources(events)=={'census:ft900'}
    assert all('fred' not in url for url in calls)
    assert readings['2026-08-01']['source_value_millions']=='-105572'
    assert result['status']=='success' and len(c.obs)==4
    for doc in c.docs:assert hashlib.sha256(Path(doc['raw_path']).read_bytes()).hexdigest()==doc['raw_hash']


def test_idempotence_and_revisions_preserve_raw(tmp_path):
    c,_,_=run(tmp_path);before=copy.deepcopy((c.docs,c.obs));run(tmp_path,c)
    assert before==(c.docs,c.obs)
    values=copy.deepcopy(BASE);values['2026-07-01']=('-93000','310550','403550')
    _,r,_=run(tmp_path,c,book=workbook(values),now=NOW+timedelta(minutes=1))
    assert Decimal(c.obs['2026-07-01']['value'])==-93000
    assert r['historical_revisions'][0]['before']=='-92826'
    _,r,_=run(tmp_path,c,now=NOW+timedelta(minutes=2))
    assert not r['exhibit1_validated'] and Decimal(c.obs['2026-07-01']['value'])==-93000


@pytest.mark.parametrize('bad',['exh1.xlsx','ft900_2608.pdf','schedule.html'])
def test_partial_http_failure_preserves_observations(tmp_path,bad):
    c,_,_=run(tmp_path);before=copy.deepcopy(c.obs)
    _,r,_=run(tmp_path,c,bad=bad)
    assert c.obs==before and r['status']=='partial'


def test_unknown_future_csv_month_without_report_is_rejected(tmp_path):
    c,_,_=run(tmp_path);old=copy.deepcopy(c.obs);values=copy.deepcopy(BASE);values['2026-09-01']=('-100','10','110')
    _,r,_=run(tmp_path,c,book=workbook(values),now=datetime(2026,11,4,16,tzinfo=timezone.utc))
    assert c.obs==old and not r['exhibit1_validated'] and r['result_pending']


def test_first_latest_xlsx_pdf_conflict_is_visible(tmp_path):
    values=copy.deepcopy(BASE);values['2026-08-01']=('-100000','320754','420754')
    c,r,_=run(tmp_path,book=workbook(values))
    assert not c.obs and not r['exhibit1_validated']
    assert 'conflicts' in r['errors'][0]['reason']


def test_database_failure_rolls_back_documents_and_observations(tmp_path):
    import psycopg
    c=Connection();c.fail=True
    with pytest.raises(psycopg.DatabaseError):run(tmp_path,c)
    assert not c.docs and not c.obs


def test_stable_id_and_schedule_history(tmp_path):
    c,_,_=run(tmp_path)
    # Publisher and BEA agree on rescheduling; identity follows the month.
    _,r,_=run(tmp_path,c,home=schedule('November 5, 2026'),bea_body=bea().replace('November 4','November 5'),now=NOW+timedelta(minutes=1))
    saved=s.read_schedule(c);e=next(e for e in saved['events'] if e['reference_period']=='2026-09-01')
    assert e['event_id']=='ft900:2026-09:monthly' and e['release_date']=='2026-11-05'
    assert len(saved['history'])==1


@pytest.mark.parametrize('day,utc,pl',[('2026-10-06','12:30','14:30'),('2026-11-04','13:30','14:30'),('2027-03-09','13:30','14:30'),('2027-03-16','12:30','13:30'),('2027-04-06','12:30','14:30')])
def test_iana_dst(day,utc,pl):
    instant=a.instant({'release_date':day,'release_time':'08:30:00'})
    assert instant.strftime('%H:%M')==utc and instant.astimezone(s.ZoneInfo('Europe/Warsaw')).strftime('%H:%M')==pl


def test_bea_conflict_does_not_overwrite_schedule(tmp_path):
    c,_,_=run(tmp_path);old=s.read_schedule(c)
    _,r,_=run(tmp_path,c,bea_body=bea().replace('November 4','November 5'))
    assert not r['schedule_checked'] and s.read_schedule(c)==old


def test_document_available_exhibit_lags_then_new_actual(tmp_path,monkeypatch):
    c,_,_=run(tmp_path);now=datetime(2026,11,4,14,tzinfo=timezone.utc)
    _,result,_=run(tmp_path,c,latest=9,now=now)
    assert result['result_pending'] and '2026-09-01' not in c.obs
    values=copy.deepcopy(BASE);values['2026-09-01']=('-105000','315000','420000')
    _,result,_=run(tmp_path,c,latest=9,now=now+timedelta(minutes=1),book=workbook(values))
    original=s.read_schedule;monkeypatch.setattr(s,'read_schedule',lambda *args:original(c))
    event=next(e for e in a.calendar_events(date(2026,11,4),date(2026,11,4)) if e['event_type']=='ft900')
    measure=a.bind_measure(event,a.load_state(c),now+timedelta(minutes=1))
    assert result['status']=='success' and measure['actual']==-105 and measure['previous']==-105.572
    assert measure['forecast'] is None


def test_clock_alone_never_publishes_actual(tmp_path):
    c,_,_=run(tmp_path)
    _,result,_=run(tmp_path,c,now=datetime(2026,11,4,16,tzinfo=timezone.utc))
    assert result['result_pending'] and '2026-09-01' not in c.obs


def rewrite(content,replace):
    output=io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(content)) as before,zipfile.ZipFile(output,'w') as after:
        for name in before.namelist():after.writestr(name,replace(before.read(name)) if name.startswith('xl/worksheets/') else before.read(name))
    return output.getvalue()


@pytest.mark.parametrize('old,new',[(b'>Total<',b'>Goods<'),(b'Exhibit 1.',b'Exhibit 1s.'),(b'>August<',b'>Augusst<')])
def test_wrong_scope_or_ambiguous_period_is_rejected(old,new):
    with pytest.raises(ValueError):s.parse_xlsx(rewrite(workbook(),lambda data:data.replace(old,new)))


def test_new_raw_hash_unchanged_observations(tmp_path):
    c,_,_=run(tmp_path);before=copy.deepcopy(c.obs);book=workbook()
    _,result,_=run(tmp_path,c,book=rewrite(book,lambda data:data+b'\n'),now=NOW+timedelta(minutes=1))
    assert result['changed_observations']==0 and c.obs==before
    assert len([d for d in c.docs if d['kind']=='xlsx'])==2


def test_multiple_intraday_revisions_recoverable_from_raw(tmp_path):
    c,_,_=run(tmp_path)
    for minute,value in [(1,'-93000'),(2,'-94000')]:
        values=copy.deepcopy(BASE);values['2026-07-01']=(value,str(403550+int(value)),'403550')
        run(tmp_path,c,book=workbook(values),now=NOW+timedelta(minutes=minute))
    versions=[s.parse_xlsx(Path(d['raw_path']).read_bytes())['values']['2026-07-01']['balance'] for d in c.docs if d['kind']=='xlsx']
    assert versions==['-92826','-93000','-94000'] and len(c.obs)==4


def test_api_keeps_census_bea_attribution_and_full_source_precision(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.main import app
    from app.analytics import calendar_agenda
    c,_,_=run(tmp_path);original=s.read_schedule
    monkeypatch.setattr(s,'read_schedule',lambda *args:original(c))
    events=bind_events(a.calendar_events(date(2026,10,6),date(2026,10,6)),{},{},NOW,ft900=a.load_state(c))
    monkeypatch.setattr(calendar_agenda,'calendar_agenda',lambda *a,**kw:{'events':events})
    data=TestClient(app).get('/api/v1/calendar?start_date=2026-10-06&end_date=2026-10-06&include_readings=true').json()
    event=data['events'][0];m=event['measures'][0]
    assert event['usage_rights']['original_url']==s.XLSX and 'Census Bureau' in event['usage_rights']['source']
    assert m['source_value_millions']=='-105572' and m['actual']==-105.572 and len(event['measures'])==1


def test_current_total_rounding_tolerance_is_explicit():
    # Three independently rounded million-dollar values may differ by at most 1.5.
    assert s.parse_xlsx(workbook({'2026-08-01':('-10','20','31')}))['values']['2026-08-01']['balance']=='-10'
    with pytest.raises(ValueError):s.parse_xlsx(workbook({'2026-08-01':('-10','20','32')}))


def test_coordinator_ft900_respects_existing_six_hour_cooldown(monkeypatch):
    from app.analytics import overview_refresh as refresh
    from app.ingestion import sync_ism_calendar,import_ism
    monkeypatch.setattr(refresh,'FRED_SERIES',set());monkeypatch.setattr(refresh,'inventory',lambda *a:{})
    monkeypatch.setattr(sync_ism_calendar,'read_schedule',lambda:{'adapter_version':sync_ism_calendar.SCHEDULE_ADAPTER_VERSION})
    resources=['fred:calendar','fed:calendar','ism:calendar','adp:calendar','michigan:calendar','nyfed:empire-state','census:ft900',*['ism:'+sid for sid in import_ism.KINDS.values()]]
    prior={k:{'attempted_at':NOW.isoformat()} for k in resources};calls=[]
    monkeypatch.setattr(s,'sync_source',lambda *args:(calls.append(args[2]) or {'status':'success'}))
    versions,result=refresh.refresh_sources(Connection(),prior,NOW+timedelta(minutes=15))
    assert not calls and next(r for r in result if r['resource']=='census:ft900')['status']=='cached'
    later=NOW+timedelta(hours=6)
    for key in versions:
        if key!='census:ft900':versions[key]={'attempted_at':later.isoformat()}
    refresh.refresh_sources(Connection(),versions,later)
    assert calls==[later]


def test_nonfinite_numeric_overflow_never_reaches_api():
    with pytest.raises(ValueError):s.parse_xlsx(workbook({'2026-08-01':('0','9'*400,'9'*400)}))


def test_empty_future_month_is_not_an_observation():
    assert '2026-09-01' not in s.parse_xlsx(workbook())['values']


def test_xml_entities_not_expanded():
    with pytest.raises(ValueError):s.parse_xlsx(rewrite(workbook(),lambda data:b'<!DOCTYPE x [<!ENTITY x "bad">]>'+data))


def test_empty_historical_row_is_not_a_printed_future_month():
    values=copy.deepcopy(BASE);values['2026-06-01']=('','','')
    with pytest.raises(ValueError):s.parse_xlsx(workbook(values))


def test_report_comparison_tolerance_comes_from_published_precision():
    assert Decimal(s.parse_report(pdf(balance='105.57'),'2026-08-01')['reported_precision_millions'])==5
    assert Decimal(s.parse_report(pdf(balance='105.6'),'2026-08-01')['reported_precision_millions'])==50


def test_merged_numeric_cells_cannot_fill_missing_total_inputs():
    content=workbook({'2026-08-01':('0','10','')})
    merged=rewrite(content,lambda data:data.replace(b'</mergeCells>',b'<mergeCell ref="E8:H8"/></mergeCells>'))
    with pytest.raises(ValueError,match='Empty or invalid'):s.parse_xlsx(merged)


def test_formula_without_cached_value_is_rejected_even_in_empty_future_row():
    content=workbook()
    def formula(data):
        return data.replace(b'<row r="12">',b'<row r="12"><c r="B12"><f>1+1</f></c>')
    with pytest.raises(ValueError,match='Formula'):s.parse_xlsx(rewrite(content,formula))
