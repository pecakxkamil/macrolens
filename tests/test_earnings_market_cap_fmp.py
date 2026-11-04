"""Explicit synthetic examples, never live FMP responses or credentials."""
import copy,json
from datetime import date
from decimal import Decimal
import httpx
import pytest
from app import earnings_market_cap_fmp as f,earnings_market_cap as store

TOKEN='synthetic-unit-test-token-not-a-credential'
WHEN='2026-11-04T15:00:00+00:00'


def access():
    return {'access':{'api_access':True,'local_storage':True,'private_display':True,'usage':'private_local',
                      'reference':'Synthetic test permission, no provider agreement','verified_on':'2026-11-04','valid_until':'2026-12-01'}}


def examples(count=3):
    entries=f.mapping()[:count]
    profiles=[dict(symbol=r['symbol'],cik=r['cik'],currency='USD',companyName='SYNTHETIC TEST ISSUER',isAdr=False,isEtf=False,isFund=False) for r in entries]
    values=[dict(symbol=r['symbol'],date='2026-11-03',marketCap=Decimal('123456789012.345678901')) for r in entries]
    return entries,profiles,values


def bundle(count=3):
    entries,profiles,values=examples(count)
    return f.parse_candidates(entries,profiles,values,retrieved_at=WHEN,receipts=[{'endpoint':'synthetic test, no network','retrieved_at':WHEN}],fixture=True)


def prepare_example(b,review):return f.prepare(b,review,allow_examples=True)


def review_for(b):
    review=access();review.update(candidate_sha256=f.digest(b),verified_on='2026-11-04',issuers={})
    for c in b['candidates']:
        review['issuers'][c['cik']]={'symbol':c['symbol'],'whole_issuer_all_classes':True,'basis_evidence':'Synthetic scope evidence, not production approval',
            'independent_check':{'source_url':'https://independent.example.invalid/synthetic','as_of':c['as_of'],'currency':c['currency'],
                                 'market_cap_value':c['market_cap_value']}}
    return review


@pytest.fixture(autouse=True)
def audit_day(monkeypatch):monkeypatch.setattr(store,'utc_today',lambda:date(2026,11,4))


def test_mappings_one_symbol_per_53_issuer_and_pilot():
    all_rows=f.mapping('all');assert len(all_rows)==53 and len({r['cik'] for r in all_rows})==53
    assert len(f.mapping())==10
    assert len([r for r in all_rows if r['symbol'] in ('GOOG','GOOGL')])==1
    assert len([r for r in all_rows if r['symbol'].startswith('BRK')])==1


@pytest.mark.parametrize('key',['',None,'demo','YOUR_API_KEY'])
def test_missing_keys_never_open_transport(key):
    with pytest.raises(f.FmpError,match='missing_fmp_api_key'):f.Client(key,access())


@pytest.mark.parametrize('field',['api_access','local_storage','private_display'])
def test_access_review_is_required(field):
    review=access();review['access'][field]=False
    with pytest.raises(f.FmpError,match='review_required'):f.Client(TOKEN,review)


def test_authorization_header_precision_and_sanitized_receipts():
    seen=[]
    def handler(request):
        seen.append(request)
        assert request.headers['apikey']==TOKEN and TOKEN not in str(request.url)
        return httpx.Response(200,text='[{"symbol":"AAPL","marketCap":123456789012.345678901,"date":"2026-11-03"}]',headers={'x-request-id':'owned-test-request'})
    client=f.Client(TOKEN,access(),transport=httpx.MockTransport(handler))
    try:
        response=client.get('market-capitalization',{'symbol':'AAPL'})
        assert response[0]['marketCap']==Decimal('123456789012.345678901')
        assert client.receipts[0]['request_id']=='owned-test-request'
        assert TOKEN not in json.dumps(client.receipts)
    finally:client.close()


@pytest.mark.parametrize('status,code',[(401,'unauthorized'),(403,'forbidden_plan_or_access'),(429,'rate_limited'),(500,'provider_unavailable'),(503,'provider_unavailable'),(302,'unexpected_http_status')])
def test_errors_stop_without_retry_redirect_or_secret(status,code):
    attempts=[]
    def handler(request):attempts.append(True);return httpx.Response(status,text='Do not log '+TOKEN,headers={'location':'https://other.invalid/?apikey='+TOKEN})
    client=f.Client(TOKEN,access(),transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(f.FmpError) as error:client.get('profile',{'symbol':'AAPL'})
        assert str(error.value)==code and error.value.__cause__ is None
        assert len(attempts)==1 and TOKEN not in json.dumps(client.receipts)
    finally:client.close()


@pytest.mark.parametrize('body',['not-json','{"Error Message":"'+TOKEN+'"}','[{"symbol":"AAPL","name":"'+TOKEN+'"}]'])
def test_bad_or_credential_echo_payloads_are_not_exposed(body):
    client=f.Client(TOKEN,access(),transport=httpx.MockTransport(lambda r:httpx.Response(200,text=body)))
    try:
        with pytest.raises(f.FmpError) as error:client.get('profile',{'symbol':'AAPL'})
        assert TOKEN not in str(error.value)
    finally:client.close()


def test_network_failure_cannot_leak_exception_text():
    def handler(request):raise httpx.ConnectError('private '+TOKEN,request=request)
    client=f.Client(TOKEN,access(),transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(f.FmpError,match='transport_or_invalid_json') as error:client.get('profile',{'symbol':'AAPL'})
        assert TOKEN not in str(error.value)
    finally:client.close()


def test_bounded_calls_and_no_provider_fallback():
    calls=[];sleeps=[]
    client=f.Client(TOKEN,access(),max_requests=2,sleeper=sleeps.append,transport=httpx.MockTransport(lambda r:(calls.append(str(r.url)) or httpx.Response(200,json=[]))))
    try:
        client.get('profile',{'symbol':'AAPL'});client.get('profile',{'symbol':'MSFT'})
        with pytest.raises(f.FmpError,match='budget'):client.get('profile',{'symbol':'NVDA'})
        assert len(calls)==2 and sleeps==[1.0]
        with pytest.raises(f.FmpError):client.get('../other',{'symbol':'NVDA'})
    finally:client.close()


def test_parser_preserves_currency_measurement_and_retrieval_separately():
    entries,profiles,values=examples(1);profiles[0]['currency']='TWD';profiles[0]['isAdr']=True
    result=f.parse_candidates(entries,profiles,values,retrieved_at=WHEN,receipts=[])
    c=result['candidates'][0]
    assert c['market_cap_value']=='123456789012.345678901' and c['currency']=='TWD'
    assert c['as_of']=='2026-11-03' and c['retrieved_at']==WHEN and c['measured_at'] is None
    assert c['verification_status']=='unsupported_currency' and c['profile']['isAdr'] is True


@pytest.mark.parametrize('mutation',[
    lambda p,v:p[0].update(cik='0000000000'),lambda p,v:v.append(copy.deepcopy(v[0])),
    lambda p,v:v[0].update(symbol='GOOG'),lambda p,v:v[0].pop('date'),
    lambda p,v:v[0].update(marketCap='NaN'),lambda p,v:v[0].update(marketCap=0),
    lambda p,v:v[0].update(marketCap=1.2),lambda p,v:v[0].update(date='2099-01-01'),
    lambda p,v:p[0].update(isFund=True),
])
def test_wrong_identity_duplicate_missing_date_and_values_fail(mutation):
    entries,profiles,values=examples(1);mutation(profiles,values)
    with pytest.raises(f.FmpError):f.parse_candidates(entries,profiles,values,retrieved_at=WHEN,receipts=[])


def test_undated_profile_cap_is_never_a_fallback():
    entries,profiles,values=examples(1);profiles[0]['marketCap']='999'
    result=f.parse_candidates(entries,profiles,[],retrieved_at=WHEN,receipts=[])
    assert not result['candidates'] and result['gaps'][0]['reason']=='missing_profile_or_dated_market_cap'


def test_prepare_requires_review_scope_and_independent_measurements():
    b=bundle();review=review_for(b);prepared=prepare_example(b,review)
    assert len(prepared['records'])==3
    assert 'retrieved_at' in json.loads(prepared['records'][0]['basis_evidence'])
    assert prepared['records'][0]['measured_at'] is None
    bad=copy.deepcopy(review);bad['candidate_sha256']='0'*64
    with pytest.raises(f.FmpError,match='hash'):prepare_example(b,bad)
    bad=copy.deepcopy(review)
    for r in bad['issuers'].values():r['independent_check']=None
    with pytest.raises(f.FmpError,match='independent_checks'):prepare_example(b,bad)
    for r in bad['issuers'].values():r['whole_issuer_all_classes']=False
    assert not prepare_example(b,bad)['records']


def test_no_arbitrary_correction_when_independent_source_differs():
    b=bundle(1);review=review_for(b);ind=next(iter(review['issuers'].values()))['independent_check']
    ind['market_cap_value']='999'
    with pytest.raises(f.FmpError,match='reference'):prepare_example(b,review)
    ind['difference_explanation']='Synthetic difference: distinct measurement time, accepted manually'
    assert prepare_example(b,review)['records'][0]['market_cap_usd']==b['candidates'][0]['market_cap_value']


def test_same_measurement_refresh_keeps_version_and_old_snapshot_expires():
    b=bundle(1);first=prepare_example(b,review_for(b))
    b['retrieved_at']='2026-11-04T16:00:00+00:00';b['candidates'][0]['retrieved_at']=b['retrieved_at'];b['receipts']=[]
    second=prepare_example(b,review_for(b))
    assert first['records'][0]['source_version']==second['records'][0]['source_version']
    assert store.measurement_basis(first['records'][0]['basis_evidence'])==store.measurement_basis(second['records'][0]['basis_evidence'])
    b['candidates'][0]['as_of']='2026-10-01'
    assert not prepare_example(b,review_for(b))['records']


def test_examples_cannot_be_promoted_as_live():
    b=bundle(1)
    with pytest.raises(f.FmpError,match='test_fixture'):f.prepare(b,review_for(b))


def test_explicit_non_usd_response_is_not_overwritten_by_usd_profile():
    entries,profiles,values=examples(1);values[0]['currency']='TWD'
    result=f.parse_candidates(entries,profiles,values,retrieved_at=WHEN,receipts=[],fixture=True)
    assert result['candidates'][0]['currency']=='TWD' and result['candidates'][0]['verification_status']=='currency_conflict'
    assert not prepare_example(result,review_for(result))['records']


def test_access_expiry_does_not_leave_a_value_displayable():
    assert store.access_is_current(json.dumps({'provider':'FMP','access_valid_until':'2026-11-03'})) is False
    assert store.access_is_current(json.dumps({'provider':'FMP','access_valid_until':'2026-11-04'})) is True
    assert store.access_is_current(json.dumps({'provider':'FMP'})) is False


@pytest.mark.parametrize('offset,fresh',[(0,True),(7,True),(8,False),(-1,False)])
def test_seven_calendar_day_freshness(offset,fresh):
    from datetime import timedelta
    assert store.is_fresh(date(2026,11,4)-timedelta(days=offset)) is fresh
