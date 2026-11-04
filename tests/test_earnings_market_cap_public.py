"""Synthetic public-provider examples; never used by the normal cache."""
import copy
import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
import httpx
import pytest
from app import earnings_market_cap_cache as cache, earnings_market_cap_public as public


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(public, 'now', lambda: '2026-11-04T16:00:00+00:00')


def example():
    item = next(r for r in public.reviewed() if r['ticker'] == 'AAPL')
    payload = dict(symbol='AAPL', name=item['tgm_name'], currency='USD',
                   classification={'type': 'operating', 'flags': {'adr': False, 'fund': False}},
                   price={'lastClose': Decimal('1.23'), 'latestPrice': Decimal('1.23'),
                          'lastCloseDate': '2026-11-03', 'marketCap': Decimal('1234567890123.123456789')})
    body = json.dumps(payload, default=str).encode()
    receipt = dict(url=public.TGM+'AAPL', sha256=hashlib.sha256(body).hexdigest(), retrieved_at=public.now())
    return item, payload, receipt


def bundle():
    item, payload, receipt = example()
    r = public.tgm_record(item, payload, receipt)
    return dict(version=1, synthetic=False, generated_at=public.now(), records=[r], gaps=[])


def test_identity_map_all_53_and_canonical_classes():
    items = public.reviewed()
    assert len(items) == 53 and len({r['cik'] for r in items}) == 53
    assert next(r for r in items if r['ticker']=='GOOGL')['delta_symbol']=='GOOGL'
    assert next(r for r in items if r['ticker']=='BRK-B')['delta_symbol']=='BRK.B'
    assert {r['ticker'] for r in items if not r['scope_reviewed']} == {'TSM','ASML','ARM','SHOP'}


def test_tgm_exact_decimal_date_and_delayed_quote_ambiguity():
    item, payload, receipt = example()
    r = public.tgm_record(item, payload, receipt)
    assert r['market_cap_usd']=='1234567890123.123456789' and r['as_of']=='2026-11-03'
    payload['price']['latestPrice'] = Decimal('1.24')
    with pytest.raises(public.DataGap, match='date_ambiguous'):
        public.tgm_record(item,payload,receipt)


@pytest.mark.parametrize('key,value', [('currency','TWD'),('symbol','GOOG'),('name','Wrong issuer')])
def test_tgm_wrong_identity_or_currency(key,value):
    item,payload,receipt=example();payload[key]=value
    with pytest.raises(public.DataGap):public.tgm_record(item,payload,receipt)


@pytest.mark.parametrize('value',[None,0,-1,True,1.5,'NaN','Infinity','-1'])
def test_bad_amounts(value):
    with pytest.raises((ValueError,ArithmeticError)):public.amount(value)


def test_csv_dated_snapshot_not_fetch_date_and_no_float():
    item,_,receipt=example();receipt['url']='https://deltascreener.com/data/us-stock-universe-2026-11-03.csv'
    body=('ticker,name,exchange,mktCap\nAAPL,"'+item['delta_name']+'",'+item['delta_exchange']+',1234567890123.123456789\n').encode()
    r=public.delta_record(item,public.delta_rows(body),receipt)
    assert r['as_of']=='2026-11-03' and r['market_cap_usd']=='1234567890123.123456789'
    receipt['url']='https://deltascreener.com/data/us-stock-universe-latest.csv'
    with pytest.raises(public.DataGap,match='dated_csv'):public.delta_record(item,public.delta_rows(body),receipt)
    with pytest.raises(public.DataGap,match='duplicate'):public.delta_rows(body+body.splitlines()[1]+b'\n')


@pytest.mark.parametrize('ticker',['TSM','ASML','ARM','SHOP'])
def test_ambiguous_adr_and_class_stay_missing(ticker):
    item=next(r for r in public.reviewed() if r['ticker']==ticker)
    with pytest.raises(public.DataGap):public.record(item,'123','2026-11-03','DeltaScreener',item['delta_name'],item['delta_exchange'],example()[2],'synthetic')


def test_cache_stale_future_missing_invalid_and_atomic_write(tmp_path,monkeypatch):
    b=bundle();monkeypatch.setattr(cache,'CACHE',tmp_path/'cache.json')
    assert cache.read(date(2026,11,4))=={}
    public.publish(b,cache.CACHE)
    assert len(cache.read(date(2026,11,4)))==1
    assert len(cache.read(date(2026,11,10)))==1
    assert cache.read(date(2026,11,11))=={}
    original=cache.CACHE.read_bytes()
    b['records']*=2
    with pytest.raises(ValueError):public.publish(b,cache.CACHE)
    with pytest.raises(ValueError):cache.validate(b,date(2026,11,11))
    assert cache.CACHE.read_bytes()==original
    cache.CACHE.write_text('{partial')
    assert cache.read(date(2026,11,4))=={}


def test_fresh_sql_wins_and_cache_fills_unavailable_without_other_changes(monkeypatch):
    r=bundle()['records'][0];monkeypatch.setattr(cache,'read',lambda today:{r['cik']:r})
    base=dict(cik=r['cik'],company_id=r['company_id'],market_cap_status='not_activated',current_eps_actual={'actual':'2.10'})
    event=copy.deepcopy(base)
    cache.attach([event],date(2026,11,4))
    assert event['market_cap_usd']==r['market_cap_usd'] and event['current_eps_actual']==base['current_eps_actual']
    sql={**base,'market_cap_status':'verified_snapshot','market_cap_usd':'999'};before=copy.deepcopy(sql)
    cache.attach([sql],date(2026,11,4));assert sql==before


@pytest.mark.parametrize('status',[401,403,404,302])
def test_public_no_retry_for_access_or_uncovered(tmp_path,status):
    calls=[]
    def reply(request):calls.append(request);return httpx.Response(status)
    client=public.PublicClient(tmp_path,transport=httpx.MockTransport(reply),sleeper=lambda n:None)
    with pytest.raises(public.DataGap):client.get(public.TGM+'AAPL')
    assert len(calls)==1 and 'authorization' not in calls[0].headers and 'apikey' not in calls[0].headers
    client.close()


@pytest.mark.parametrize('status',[429,500,503])
def test_backoff_bounded_and_hourly_response_cache(tmp_path,status):
    calls=[];sleeps=[]
    def reply(request):calls.append(request);return httpx.Response(status if len(calls)<3 else 200,json={'ok':True})
    client=public.PublicClient(tmp_path,transport=httpx.MockTransport(reply),sleeper=sleeps.append)
    first=client.get(public.TGM+'AAPL');assert client.get(public.TGM+'AAPL')==first
    assert len(calls)==3 and 2 in sleeps and 4 in sleeps
    client.close()


def test_retry_after_budget_and_unknown_host(tmp_path):
    client=public.PublicClient(tmp_path,transport=httpx.MockTransport(lambda r:httpx.Response(429,headers={'Retry-After':'3600'})),sleeper=lambda n:None)
    with pytest.raises(public.DataGap):client.get(public.TGM+'AAPL')
    assert client.count==1
    with pytest.raises(public.DataGap):client.get('https://unapproved.invalid/')
    client.budget=1
    with pytest.raises(public.DataGap,match='budget'):client.get(public.TGM+'NVDA')
    client.close()


def test_monthly_45_days_daily_7_and_no_rewrite(tmp_path):
    b=bundle();r=b['records'][0];item=example()[0]
    r.update(provider='DeltaScreener',source_url=cache.SOURCES['DeltaScreener'],source_symbol=item['delta_symbol'],source_name=item['delta_name'])
    from datetime import timedelta
    assert len(cache.validate(b,date(2026,11,3)+timedelta(days=45)))==1
    assert cache.validate(b,date(2026,11,3)+timedelta(days=46))=={}
    destination=tmp_path/'monthly.json'
    assert public.publish(b,destination)=='updated'
    first=destination.read_bytes();b['records'][0]['retrieved_at']='2026-11-04T17:00:00+00:00';b['generated_at']='2026-11-04T17:00:00+00:00'
    assert public.publish(b,destination)=='unchanged' and destination.read_bytes()==first


def test_due_command_no_network_off_event_day_and_once_daily(tmp_path,monkeypatch,capsys):
    import sys
    monkeypatch.setattr(cache,'CACHE',tmp_path/'current.json')
    monkeypatch.setattr(sys,'argv',['public','refresh','--if-due','--event-date','2026-11-05'])
    public.main();assert 'not_an_earnings_day' in capsys.readouterr().out
    (tmp_path/'attempts').mkdir();(tmp_path/'attempts/2026-11-04.json').write_text('{}')
    monkeypatch.setattr(sys,'argv',['public','refresh','--if-due','--event-date','2026-11-04'])
    public.main();assert 'already_attempted_today' in capsys.readouterr().out
