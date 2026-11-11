"""Offline production adapter tests; the fixture is an actual captured BLS batch."""
import copy
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
import httpx
import pytest
from app.ingestion import bls_employment as s

FIXTURE=Path(__file__).parent/'fixtures/bls_employment_response.json'

def payload():return json.loads(FIXTURE.read_text(encoding='utf-8'))

def test_real_bls_batch_derivations_and_source_specific_history():
    rows=s.parse(FIXTURE.read_bytes(),'2026-10-01')
    assert {k:v['actual'] for k,v in rows.items()}==dict(PAYEMS='165',UNRATE='4.1',CES0500000003='0.4',CIVPART='61.9',U6RATE='7.9',AWHAETP='34.4')
    assert rows['PAYEMS']['previous']=='60'
    assert rows['CES0500000003']['previous']=='0.3'
    assert rows['PAYEMS']['trend']['2026-09-01']=='60'
    assert rows['CES0500000003']['unrounded_actual'].startswith('0.369783')
    assert rows['AWHAETP']['unit']=='hours'
    assert all(v['seasonal_adjustment']=='SA' for v in rows.values())

@pytest.mark.parametrize('fault',['missing','duplicate','nsa','unit','nonfinite','month','duplicate_month','missing_dependency','wrong_period','failed','zero_denominator'])
def test_bad_batch_rejected(fault):
    p=payload();rows=p['Results']['series'];period='2026-10-01'
    if fault=='missing':rows.pop()
    elif fault=='duplicate':rows[-1]=copy.deepcopy(rows[0])
    elif fault=='nsa':rows[0]['seriesID']='CEU0000000001'
    elif fault=='unit':rows[0]['unit']='millions of persons'
    elif fault=='nonfinite':rows[0]['data'][0]['value']='NaN'
    elif fault=='month':rows[0]['data'][0]['period']='Q04'
    elif fault=='duplicate_month':rows[0]['data'].append(rows[0]['data'][0])
    elif fault=='missing_dependency':rows[0]['data']=[r for r in rows[0]['data'] if r['period']!='M09']
    elif fault=='wrong_period':period='2026-11-01'
    elif fault=='failed':p['status']='REQUEST_NOT_PROCESSED'
    elif fault=='zero_denominator':next(r for r in rows if r['seriesID']=='CES0500000003')['data'][1]['value']='0'
    with pytest.raises(ValueError):s.parse(json.dumps(p).encode(),period)

@pytest.mark.parametrize('code',[301,403,429,503])
def test_transport_refuses_redirect_or_error_without_retry(code):
    calls=[]
    def respond(request):calls.append(request);return httpx.Response(code,headers={'Retry-After':'900'})
    with httpx.Client(transport=httpx.MockTransport(respond),follow_redirects=False) as client:
        raw,request,status,retry=s.fetch(client,dict(reference_period='2026-10-01'))
    assert len(calls)==1 and status==code and raw is None
    assert len(request['seriesid'])==6 and 'registrationkey' not in request
    assert calls[0].url==s.URL

def test_transport_one_batch_and_maximum_bytes():
    with httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(200,content=FIXTURE.read_bytes()))) as client:
        raw,request,status,_=s.fetch(client,dict(reference_period='2026-10-01'))
    assert status==200 and raw==FIXTURE.read_bytes()
    with httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(200,content=b'x'*(s.MAX_BYTES+1)))) as client:
        with pytest.raises(ValueError,match='large'):s.fetch(client,dict(reference_period='2026-10-01'))

@pytest.mark.parametrize('header,days',[('259200',3),('Mon, 09 Nov 2026 14:00:00 GMT',3)])
def test_long_retry_after_never_capped(header,days):
    now=datetime(2026,11,6,14,tzinfo=timezone.utc)
    assert s.retry_after(header,now)>=now+timedelta(days=days)

def test_series_contract_is_frozen_and_not_inferred_from_payload():
    assert len(s.CONTRACT)==6
    assert s.CONTRACT['AWHAETP'][0]=='CES0500000002'
    assert s.CONTRACT['CES0500000003'][3]=='dollars per hour'

def test_projection_uses_same_capture_previous_and_retains_first_print_alternative(monkeypatch):
    stamp=datetime.now(timezone.utc);raw=FIXTURE.read_bytes();rows=s.parse(raw,'2026-10-01')
    doc=dict(id='test-document',retrieved_at=stamp,raw_hash='a'*64,metadata=dict(event=dict(release_date='2026-11-06',scheduled_at='2026-11-06T13:30:00+00:00'),readings=rows))
    monkeypatch.setattr(s,'documents',lambda c:[doc])
    measures=[dict(series_id=sid,feature_name=v[1],unit=v[2],reference_period='2026-10-01',actual=None,previous=29 if sid=='PAYEMS' else None) for sid,v in s.CONTRACT.items()]
    result=s.project([dict(release_id=50,release_date='2026-11-06',measures=measures)],None,stamp)[0]['measures']
    nfp=next(m for m in result if m['series_id']=='PAYEMS')
    assert nfp['actual']==165 and nfp['previous']==60 and nfp['actual']-nfp['previous']==105
    assert nfp['fred_alternative']['previous']==29 and nfp['actual_provenance']['first_print'] is False
    assert nfp['bls_history']['2026-09-01']=='60' and nfp['bls_history']['2026-10-01']=='165'
    assert all(m['comparison_status']=='same_bls_capture' for m in result)

def test_new_schedule_check_does_not_reactivate_complete_report(monkeypatch):
    event=dict(release_id=50,release_date='2026-11-06',reference_period='2026-10-01',scheduled_at='2026-11-06T13:30:00+00:00',schedule_proofs=['new'])
    monkeypatch.setattr(s,'documents',lambda c:[dict(metadata=dict(event={**event,'schedule_proofs':['old']},readings={'PAYEMS':{}}))])
    assert s.complete(None,event)

def test_runtime_uses_existing_launcher_without_browser_or_timer(monkeypatch,tmp_path):
    from app import bls_employment_runtime as runtime
    from app.analytics.overview_refresh import coordinator
    calls=[];token=tmp_path/'token.json';token.write_text('{"version":3}')
    monkeypatch.setattr(coordinator,'launch',lambda fn:fn())
    monkeypatch.setattr(s,'run',lambda *args,**kwargs:calls.append(True) or dict(status='cooldown',added=0))
    runtime.tick(token,tmp_path)
    assert calls==[True] and runtime.STATE['status']=='cooldown'
    runtime.tick(token,tmp_path,cancelled=lambda:True)
    assert calls==[True]

def test_real_refresh_function_fetches_missing_period_despite_unchanged_metadata(monkeypatch):
    from contextlib import contextmanager
    from unittest.mock import Mock
    from app.analytics import overview_refresh as refresh,compute_features as features
    from app.ingestion import fred,ingest_series
    @contextmanager
    def check(*args,**kwargs):yield {'scope':{}}
    monkeypatch.setattr(refresh,'availability_check',check)
    monkeypatch.setattr(s,'events',lambda now:[dict(reference_period='2026-10-01')])
    monkeypatch.setattr(s,'complete',lambda c,event:False)
    monkeypatch.setattr(features,'_load_series_config',lambda:{'PAYEMS':{'transformations':['monthly_change']}})
    monkeypatch.setattr(fred,'fetch_series_metadata',lambda sid:dict(last_updated='unchanged',observation_end='2026-09-01'))
    fetch=Mock(return_value=dict(observations=[dict(date='2026-10-01',value='159293')]))
    monkeypatch.setattr(fred,'fetch_series_observations',fetch)
    stored=[];monkeypatch.setattr(ingest_series,'_ingest_series',lambda sid,response_data:stored.append(response_data))
    monkeypatch.setattr(features,'compute_features',lambda *args,**kwargs:None)
    monkeypatch.setattr(refresh,'inventory',lambda *args:{'PAYEMS':dict(signature=[2])})
    connection=Mock();connection.execute.return_value.fetchone.return_value=('2026-09-01',)
    prior=dict(last_updated='unchanged',local_signature=[1],transformations=['monthly_change'])
    state,result=refresh.refresh_fred('PAYEMS',prior,dict(signature=[1]),connection,datetime.now(timezone.utc))
    assert result['release_observation_probe'] and result['observation_fetch_status']=='fetched'
    assert fetch.call_count==1 and stored[0]['observations'][0]['date']=='2026-10-01'
    connection.execute.return_value.fetchone.return_value=('2026-10-01',)
    _,result=refresh.refresh_fred('PAYEMS',state,dict(signature=[2]),connection,datetime.now(timezone.utc))
    assert not result['release_observation_probe'] and fetch.call_count==1
