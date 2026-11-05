"""E2A pure metadata/time/API regressions; global network and DB guards remain active."""
import copy
import json
from datetime import date,datetime
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient
from app import earnings as e
from app.api import earnings as api
from app.api.main import app


def records(): return json.loads(e.DATA.read_text(encoding='utf-8'))
def nvda(): return records()[0]


@pytest.mark.parametrize('index,cik,ticker',[(0,'0001045810','NVDA'),(2,'0001018724','AMZN'),(4,'0000050863','INTC')])
def test_pilots(index,cik,ticker):
    row=e.validate(records()[index]);assert row['cik']==cik and row['ticker']==ticker
    assert e.identity(cik)==e.identity(cik) and len(cik)==10


def test_nvda_release_not_call():
    row=e.validate(nvda());assert row['period_end']=='2026-10-25' and row['period_label']=='Q3 FY2027'
    release,call=row['release'],row['call']
    assert release['precision']=='approximate' and release['scheduled_at_utc'] is None
    assert datetime.fromisoformat(release['expected_time_utc']).astimezone(ZoneInfo('Europe/Warsaw')).strftime('%H:%M')=='22:20'
    assert datetime.fromisoformat(call['scheduled_at_utc']).astimezone(ZoneInfo('Europe/Warsaw')).strftime('%H:%M')=='23:00'


@pytest.mark.parametrize('index',[1,3,5])
def test_unknown_no_invented_next_date(index):
    r=e.validate(records()[index]);assert r['period_end'] is None
    for c in ('call','release'): assert r[c]['precision']=='unknown' and r[c]['scheduled_at_utc'] is None and r[c]['expected_time_utc'] is None


def test_call_only_and_intel_conflict():
    amazon=e.validate(records()[2]);assert amazon['release']['date_status']=='unknown'
    assert amazon['call']['scheduled_at_utc'].startswith('2026-10-29T21:00')
    intel=e.validate(records()[4]);assert intel['release']['precision']=='after_close' and intel['release']['scheduled_at_utc'] is None
    assert 'PST' in intel['call']['evidence']['facts'] and intel['call']['timezone_label_raw']=='PDT'


@pytest.mark.parametrize('day,expected',[('2026-11-17','21:00'),('2026-10-22','20:00'),('2026-10-29','20:00'),('2026-03-16','20:00'),('2026-11-27','18:00'),('2026-12-24','18:00')])
def test_session_boundaries(day,expected):
    c={'precision':'after_close','source_local_date':day,'scheduled_at_utc':None,'expected_time_utc':None}
    out=e.temporal(c);assert out['session_boundary_utc'][11:16]==expected and out['poland_date'] is None
    local=datetime.fromisoformat(out['session_boundary_utc']).astimezone(ZoneInfo('Europe/Warsaw'))
    assert local.strftime('%H:%M')==('21:00' if day in ('2026-03-16','2026-10-29') else '19:00' if day in ('2026-11-27','2026-12-24') else '22:00')


@pytest.mark.parametrize('day',['2026-11-26','2026-11-28','2027-11-17'])
def test_unreviewed_session_no_boundary(day):
    assert e.temporal({'precision':'after_close','source_local_date':day})['session_boundary_utc'] is None


def test_date_only_and_next_polish_day():
    r=nvda();r['release'].update(precision='date_only',source_local_time=None)
    c=e.validate(r)['release'];assert c['scheduled_at_utc'] is None and c['expected_time_utc'] is None
    assert e.temporal(c)['poland_date'] is None
    r=nvda();r['release'].update(precision='exact',source_local_time='19:30',source_timezone='America/New_York',timezone_label_raw='EST')
    c=e.validate(r)['release'];assert e.temporal(c)['poland_date']=='2026-11-18'


def test_before_open_boundary():
    c=e.temporal({'precision':'before_open','source_local_date':'2026-10-29'})
    assert datetime.fromisoformat(c['session_boundary_utc']).astimezone(ZoneInfo('Europe/Warsaw')).strftime('%H:%M')=='14:30'


@pytest.mark.parametrize('mutation',[
 lambda r:r.update(cik='0000000000'),lambda r:r.update(ticker='INTC'),lambda r:r.update(revenue=1),
 lambda r:r['release']['evidence'].update(source_url='https://investing.com/test'),
 lambda r:r['release']['evidence'].update(cik='0000050863'),lambda r:r['release']['evidence'].update(fiscal_quarter=2),
 lambda r:r['release'].update(precision='made_up'),lambda r:r['release'].update(source_timezone='UTC'),
 lambda r:r['release'].update(timezone_label_raw='PDT'),lambda r:r['release'].update(precision='after_close'),
 lambda r:r['release'].update(date_status='unknown'),lambda r:r['release']['evidence'].update(verification_method='http_200')])
def test_invalid_manual_metadata(mutation):
    r=nvda();mutation(r)
    with pytest.raises(ValueError):e.validate(r)


def test_api_read_only_union(monkeypatch):
    from app import forecast_f1
    monkeypatch.setattr(forecast_f1,'project_earnings',lambda events,**kwargs:events)
    seen=[]
    monkeypatch.setattr(e,'companies',lambda:[{'ticker':v[1]} for v in e.PILOTS.values()])
    monkeypatch.setattr(e,'calendar_events',lambda start,end,symbols:(seen.append(symbols) or {'events':[{'domain':'earnings','event_id':'earnings:one'}],'undated':[],'earnings_data_revision':'e1'}))
    monkeypatch.setattr(api,'calendar_agenda',lambda *a:{'events':[{'event_id':'macro:one'}],'data_revision':'m1'})
    with TestClient(app) as client:
        response=client.get('/api/v1/calendar/events?start_date=2026-11-01&end_date=2026-11-20&domains=macro,earnings&tickers=NVDA')
        assert response.status_code==200
        data=response.json();assert [x['domain'] for x in data['events']]==['macro','earnings']
        assert data['macro_data_revision']=='m1' and data['earnings_data_revision']=='e1'
        assert data['forecast_snapshot_scope']=='independent_read_only_forecast_snapshot'
        assert seen==[{'NVDA'}] and 'revenue' not in response.text and 'EPS' not in response.text
        assert len(client.get('/api/v1/earnings/companies').json())==3


@pytest.mark.parametrize('query',['domains=other','domains=earnings&tickers=BAD%27','start_date=2026-11-20&end_date=2026-11-01','start_date=2026-01-01&end_date=2028-01-01'])
def test_api_validation_no_db(query):
    with TestClient(app) as client:assert client.get('/api/v1/calendar/events?'+query).status_code==422
