"""E2B offline contracts. Existing global SQL/HTTP guards remain enabled."""
import copy
import json
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from app import earnings_financials as f, earnings as e
from app.api.main import app

def records(): return json.loads(f.DATA.read_text(encoding='utf-8'))

@pytest.mark.parametrize('index,rev,eps',[(0,'81615','2.39'),(1,'96221','2.46'),(2,'200606','5.75'),(3,'201944','1.89'),(4,'16128','-2.16'),(5,'16513','0.60')])
def test_reviewed_quarterly_facts(index,rev,eps):
    r=f.validate(records()[index]);a,b=r['observations']
    assert a['source_value']==rev and b['source_value']==eps
    assert a['methodology']=='consolidated_revenue' and b['methodology'].startswith('gaap_diluted')
    assert Decimal(a['source_value'])*f.SCALES[a['source_unit']]==Decimal(rev)*1000000
    assert r['document']['document_type']=='earnings_release'
    assert f.fingerprint(r)==f.fingerprint(copy.deepcopy(r))

@pytest.mark.parametrize('mutate',[
 lambda r:r.update(cik='0000000000'),lambda r:r.update(ticker='AMZN'),
 lambda r:r.update(fiscal_quarter=0),lambda r:r.update(fiscal_year=True),
 lambda r:r.update(period_end='2027-04-26'),lambda r:r.update(period_label='Q1 2027'),
 lambda r:r['document'].update(source_url='https://investing.com/x'),
 lambda r:r['document'].update(source_url='https://investor.nvidia.com@evil.example/x'),
 lambda r:r['document'].update(document_type='announcement'),lambda r:r['document'].update(evidence_method='http_200'),
 lambda r:r['document'].update(raw_hash='fake'),lambda r:r['document'].update(sec_accession='0001018724-26-000024'),
 lambda r:r['observations'][0].update(metric='aws_revenue'),lambda r:r['observations'][0].update(currency='EUR'),
 lambda r:r['observations'][0].update(source_unit='shares'),lambda r:r['observations'][0].update(source_value='NaN'),
 lambda r:r['observations'][0].update(source_value='-1'),lambda r:r['observations'][1].update(methodology='non_gaap'),
 lambda r:r['observations'][1].update(methodology='basic'),lambda r:r['observations'][1].update(source_value='1.234'),
 lambda r:r.update(consensus=1),lambda r:r['observations'][0].update(surprise=1),
 lambda r:r['observations'].append(copy.deepcopy(r['observations'][0])),
])
def test_invalid_financial_input(mutate):
    r=records()[0];mutate(r)
    with pytest.raises(ValueError):f.validate(r)

def test_partial_zero_negative_and_units():
    r=records()[4];r['observations']=r['observations'][1:]
    assert f.validate(r)['observations'][0]['source_value']=='-2.16'
    r['observations'][0]['source_value']='0.00';assert f.validate(r)
    r=records()[0];r['observations'][0].update(source_unit='USD_billions',source_value='81.615',decimal_places=3)
    assert Decimal(f.validate(r)['observations'][0]['source_value'])*f.SCALES['USD_billions']==81615000000

def test_no_future_nvda_actual_and_no_date_mutation():
    dates=json.loads(e.DATA.read_text(encoding='utf-8'))
    assert {(r['fiscal_year'],r['fiscal_quarter']) for r in records() if r['ticker']=='NVDA'}=={(2027,1),(2027,2)}
    assert e.validate(dates[0])['release']['expected_time_utc'].startswith('2026-11-17T21:20')
    assert e.validate(dates[0])['call']['scheduled_at_utc'].startswith('2026-11-17T22:00')

def test_dynamic_company_filter_not_import_allowlist(monkeypatch):
    seen=[]
    monkeypatch.setattr(e,'calendar_events',lambda start,end,tickers:(seen.append(tickers) or {'events':[],'undated':[],'earnings_data_revision':'x'}))
    monkeypatch.setattr(e,'companies',lambda:[{'ticker':'FOUR','name':'Synthetic fourth company'}])
    with TestClient(app) as client:
        assert client.get('/api/v1/calendar/events?domains=earnings&tickers=FOUR').status_code==200
        assert client.get('/api/v1/earnings/companies').json()[0]['ticker']=='FOUR'
    assert seen==[{'FOUR'}]
