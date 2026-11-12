"""Offline CPI contracts; the public batch fixture retains its original bytes."""
import copy,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
import pytest,httpx
from app.ingestion import bls_cpi as cpi

RAW=(Path(__file__).parent/'fixtures/bls_cpi_response.json').read_bytes()
AT=datetime(2026,11,11,18,tzinfo=timezone.utc)
EVENT=dict(release_id=10,release_date='2026-11-10',reference_period='2026-10-01',scheduled_at='2026-11-10T13:30:00+00:00')

def test_original_contracts_precision_and_terminal_proof():
 rows=cpi.parse(RAW,'2026-10-01')
 assert (rows['CPIAUCSL:mom']['actual'],rows['CPIAUCSL:mom']['previous'])==('0.4','0.6')
 core=rows['CPILFESL:mom'];assert (core['actual'],core['previous'])==('0.3','0.3')
 assert core['unrounded_actual']!=core['unrounded_previous']
 for key in ('CPIAUCSL:yoy','CPILFESL:yoy'):
  assert rows[key]['actual'] is None and rows[key]['terminal']
  assert rows[key]['seasonal_adjustment']=='NSA'
  assert rows[key]['missing_base_period']=='2025-10-01'
  assert rows[key]['missing_proof']['missing_confirmed']
 assert core['rate_kind']=='derived_index_rate'

@pytest.mark.parametrize('kind',['series','duplicate_series','adjustment','unit','month','year','duplicate_month','missing_month','value','infinite','no_proof','status','duplicate_json','container'])
def test_invalid_payloads_fail_closed(kind):
 p=json.loads(RAW);series=p['Results']['series'];row=series[0]['data'][0]
 if kind=='series':series.pop()
 if kind=='duplicate_series':series[-1]=copy.deepcopy(series[0])
 if kind=='adjustment':series[0]['seasonal_adjustment']='NSA'
 if kind=='unit':series[0]['unit']='percent'
 if kind=='month':row['period']='M14'
 if kind=='year':row['year']='2024'
 if kind=='duplicate_month':series[0]['data'].append(copy.deepcopy(row))
 if kind=='missing_month':series[0]['data']=[r for r in series[0]['data'] if (r['year'],r['period'])!=('2026','M09')]
 if kind=='value':row['value']='garbage'
 if kind=='infinite':row['value']='NaN'
 if kind=='no_proof':
  for r in series[-1]['data']:
   if r['value']=='-':r['footnotes']=[]
 if kind=='status':p['status']='REQUEST_FAILED'
 raw=json.dumps(p).encode()
 if kind=='duplicate_json':raw=b'{"status":1,"status":2}'
 if kind=='container':raw=b'[]'
 with pytest.raises(ValueError):cpi.parse(raw,'2026-10-01')

def test_projection_same_capture_no_sa_overwrite(monkeypatch):
 rows=cpi.parse(RAW,'2026-10-01');meta=dict(event=EVENT,readings=rows)
 monkeypatch.setattr(cpi,'documents',lambda c:[dict(id='test',raw_hash='a'*64,retrieved_at=AT,metadata=meta)])
 measures=[dict(series_id=k.split(':')[0],feature_name=k.split(':')[1],reference_period='2026-10-01',unit='percent',actual=5,previous=4) for k in rows]
 events=[dict(release_id=10,release_date='2026-11-10',measures=measures)]
 cpi.project(events,None,AT)
 assert measures[1]['actual']==measures[1]['previous']==0.3
 assert measures[0]['fred_alternative']['actual']==5
 assert measures[2]['result_status']=='publisher_unavailable' and measures[2]['actual'] is None
 assert measures[2]['cpi_contract_id'].endswith(':yoy:NSA')
 cpi.forecast_contract(events);assert measures[2]['forecast_status']=='not_comparable_adjustment'

@pytest.mark.parametrize('status,retry',[(403,None),(429,'1800'),(200,None)])
def test_single_batch_transport(status,retry):
 calls=[]
 def handler(request):
  calls.append(request);assert request.url==cpi.URL
  body=json.loads(request.content);assert len(body['seriesid'])==4 and body['startyear']=='2025'
  return httpx.Response(status,content=RAW if status==200 else b'blocked',headers={'Retry-After':retry} if retry else {})
 with httpx.Client(transport=httpx.MockTransport(handler)) as client:
  raw,request,code,delay=cpi.fetch(client,EVENT)
 assert code==status and delay==retry and len(calls)==1
 assert raw==(RAW if status==200 else None)

def test_future_capture_never_selected(monkeypatch):
 monkeypatch.setattr(cpi,'documents',lambda c:[dict(retrieved_at=AT+timedelta(seconds=1),metadata={'event':EVENT})])
 events=[dict(release_id=10,release_date='2026-11-10',measures=[])]
 assert cpi.project(events,None,AT)==events

def test_synthetic_published_report_is_separate_and_strict():
 # Deliberately synthetic table, never a production captured report fixture.
 raw=b'<html>CONSUMER PRICE INDEX - OCTOBER 2026 November 10, 2026 8:30 Seasonally adjusted changes from preceding month<table>'
 for label,prev,actual in [('All items','0.6','0.4'),('All items less food and energy','0.3','0.3')]:
  raw+=('<tr>'+''.join('<td>'+v+'</td>' for v in [label,'a','b','c','d','e',prev,actual,'z'])+'</tr>').encode()
 raw+=b'</table></html>'
 url='https://www.bls.gov/news.release/archives/cpi_11102026.htm'
 assert cpi.published_report(raw,EVENT,url)['CPILFESL:mom']==dict(actual='0.3',previous='0.3')
 with pytest.raises(ValueError):cpi.published_report(raw.replace(b'OCTOBER',b'SEPTEMBER'),EVENT,url)
 with pytest.raises(ValueError):cpi.published_report(raw,EVENT,'https://invalid.test/report')

@pytest.mark.parametrize('offset,expected',[(-1,0),(0,1),(86400,1),(172799,1),(172800,0)])
def test_own_catchup_window(monkeypatch,offset,expected):
 from app.analytics import release_calendar,calendar_evidence
 at=cpi.instant(EVENT['scheduled_at'])
 monkeypatch.setattr(release_calendar,'list_calendar_events',lambda *a:{'events':[dict(release_id=10,release_date=EVENT['release_date'],release_datetime_utc=EVENT['scheduled_at'])]})
 monkeypatch.setattr(calendar_evidence,'read_evidence',lambda:{})
 monkeypatch.setattr(calendar_evidence,'period_evidence',lambda *a:dict(source_url='https://www.bls.gov/schedule/news_release/cpi.htm',reference_period='2026-10-01'))
 assert len(cpi.events(at+timedelta(seconds=offset)))==expected
 from app.ingestion.bls_employment import POLICY
 assert POLICY['window_seconds']==7200

@pytest.mark.parametrize('complete,expected',[(False,1),(True,0)])
def test_cpi_release_probe_with_unchanged_metadata(monkeypatch,complete,expected):
 from contextlib import contextmanager
 from unittest.mock import Mock
 from app.analytics import overview_refresh as refresh,compute_features as features
 from app.ingestion import fred,ingest_series
 @contextmanager
 def check(*a,**k):yield {'scope':{}}
 monkeypatch.setattr(refresh,'availability_check',check)
 monkeypatch.setattr(cpi,'events',lambda now:[EVENT])
 monkeypatch.setattr(cpi,'complete',lambda c,e:complete)
 monkeypatch.setattr(features,'_load_series_config',lambda:{'CPIAUCSL':{'transformations':['mom','yoy']}})
 monkeypatch.setattr(fred,'fetch_series_metadata',lambda sid:dict(last_updated='unchanged'))
 fetch=Mock(return_value=dict(observations=[]));monkeypatch.setattr(fred,'fetch_series_observations',fetch)
 monkeypatch.setattr(ingest_series,'_ingest_series',lambda *a,**k:None)
 monkeypatch.setattr(features,'compute_features',lambda *a,**k:None)
 monkeypatch.setattr(refresh,'inventory',lambda *a:{'CPIAUCSL':dict(signature=[1])})
 connection=Mock();connection.execute.return_value.fetchone.return_value=('2026-09-01',)
 state,result=refresh.refresh_fred('CPIAUCSL',dict(last_updated='unchanged',local_signature=[1],transformations=['mom','yoy']),dict(signature=[1]),connection,AT)
 assert fetch.call_count==expected
 assert state['release_observation_probe']==bool(expected)

def test_invalid_hash_or_changed_readings_not_accepted_as_document():
 rows=cpi.parse(RAW,'2026-10-01');meta=dict(event=EVENT,readings=rows,raw_utf8=RAW.decode(),contract=json.loads(json.dumps(cpi.POLICY)))
 class Connection:
  def execute(self,*a):return [('test',cpi.URL,AT,'0'*64,meta)]
 assert cpi.documents(Connection())==[]

def test_listener_uses_existing_lifecycle_and_cancelled_tick_never_launches(monkeypatch,tmp_path):
 from app import cpi_runtime
 from app.analytics.overview_refresh import coordinator
 token=tmp_path/'activation.json';token.write_text('{"version":4}')
 calls=[];monkeypatch.setattr(coordinator,'launch',lambda fn:(calls.append(True),fn()))
 monkeypatch.setattr(cpi,'run',lambda *a,**k:dict(status='complete',added=0))
 cpi_runtime.tick(token,tmp_path,lambda:True);assert calls==[]
 cpi_runtime.tick(token,tmp_path,lambda:False);assert calls==[True]
 assert cpi_runtime.STATE['last_result']['status']=='complete'


def test_capture_revisions_select_by_asof_without_overwriting_first_capture(monkeypatch):
 first=dict(id='first',raw_hash='a'*64,retrieved_at=AT,metadata=dict(event=EVENT,readings=cpi.parse(RAW,'2026-10-01')))
 revised_raw=json.loads(RAW)
 for series in revised_raw['Results']['series']:
  if series['seriesID']=='CUSR0000SA0L1E':
   for row in series['data']:
    if row['year']=='2026' and row['period']=='M10':row['value']='340.900'
 second=dict(id='later',raw_hash='b'*64,retrieved_at=AT+timedelta(hours=1),metadata=dict(event=EVENT,readings=cpi.parse(json.dumps(revised_raw).encode(),'2026-10-01')))
 monkeypatch.setattr(cpi,'documents',lambda c:[first,second])
 def event():return [dict(release_id=10,release_date='2026-11-10',measures=[dict(series_id='CPILFESL',feature_name='mom',unit='percent',reference_period='2026-10-01',actual=None,previous=None)])]
 early=cpi.project(event(),None,AT)[0]['measures'][0];late=cpi.project(event(),None,AT+timedelta(hours=2))[0]['measures'][0]
 assert early['actual']==0.3 and late['actual']==0.6
 assert early['actual_provenance']['document_id']=='first' and late['actual_provenance']['document_id']=='later'
 assert first['metadata']['readings']['CPILFESL:mom']['actual']=='0.3'
