"""Manual FMP candidate collection and reviewed import into owned isolation.

Never imported by Calendar/startup. No automatic retry, provider fallback,
FX, ADR calculation or assumption that an API key grants display rights.
"""
import argparse
import hashlib
import json
import os
import re
import time
from datetime import date,datetime,timezone
from decimal import Decimal,InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit
import httpx
from app import earnings_market_cap as store,earnings_coverage as coverage
from app.earnings import identity

BASE='https://financialmodelingprep.com/stable/'
MAPPING=store.ROOT/'config/earnings_market_cap_fmp_symbols.json'
PILOT=('NVDA','AAPL','MSFT','AMZN','GOOGL','META','AMD','INTC','TSM','ASML')
ENDPOINTS={'profile','market-capitalization','market-capitalization-batch'}


class FmpError(ValueError):
    """Only controlled codes are printable; never provider bodies/credentials."""


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()


def safe_reference(value):
    if not isinstance(value,str) or not value.strip() or len(value)>2000 or re.search(r'(?i)(apikey|api_key|token|secret)\s*[=:]',value):
        raise FmpError('invalid_review_reference')
    return value


def access_review(review,today=None):
    today=today or store.utc_today()
    access=review.get('access',{})
    if any(access.get(k) is not True for k in ('api_access','local_storage','private_display')):
        raise FmpError('access_storage_display_review_required')
    safe_reference(access.get('reference'))
    if access.get('usage')!='private_local' or not date.fromisoformat(access['verified_on'])<=today<=date.fromisoformat(access['valid_until']):
        raise FmpError('access_review_expired_or_wrong_scope')
    return access


def mapping(scope='pilot'):
    entries=json.loads(MAPPING.read_text(encoding='utf-8'));registry=coverage.registry()
    if len({r['cik'] for r in entries})!=len(entries) or len({r['symbol'] for r in entries})!=len(entries):raise FmpError('duplicate_issuer_or_symbol')
    for r in entries:
        if r['cik'] not in registry or not re.fullmatch(r'[A-Z0-9.-]{1,15}',r['symbol']):raise FmpError('invalid_symbol_mapping')
    if scope=='pilot':entries=[r for ticker in PILOT for r in entries if registry[r['cik']]['ticker']==ticker]
    elif scope!='all':raise FmpError('invalid_scope')
    return entries


class Client:
    def __init__(self,key,review,*,transport=None,max_requests=12,interval=1.0,sleeper=time.sleep):
        if not key or key.strip().lower() in ('demo','your_api_key','changeme'):raise FmpError('missing_fmp_api_key')
        access_review(review)
        if not 1<=max_requests<=108 or interval<1:raise FmpError('invalid_request_budget')
        self.key=key;self.limit=max_requests;self.interval=interval;self.sleep=sleeper;self.receipts=[]
        self.fixture=isinstance(transport,httpx.MockTransport)
        self.client=httpx.Client(headers={'apikey':key},timeout=20,follow_redirects=False,trust_env=False,transport=transport)

    def close(self):self.client.close()

    def get(self,endpoint,params):
        if endpoint not in ENDPOINTS or len(self.receipts)>=self.limit:raise FmpError('endpoint_or_request_budget_rejected')
        if set(params) not in ({'symbol'},{'symbols'}):raise FmpError('invalid_query')
        symbols=next(iter(params.values())).split(',')
        if any(not re.fullmatch(r'[A-Z0-9.-]{1,15}',s) for s in symbols):raise FmpError('invalid_query')
        if self.receipts:self.sleep(self.interval)
        receipt={'endpoint':endpoint,'symbols':symbols,'retrieved_at':datetime.now(timezone.utc).isoformat()}
        self.receipts.append(receipt)
        code=None;payload=None
        try:
            with self.client.stream('GET',BASE+endpoint,params=params) as response:
                receipt['http_status']=response.status_code
                if response.status_code!=200:
                    code={401:'unauthorized',403:'forbidden_plan_or_access',429:'rate_limited'}.get(response.status_code,'provider_unavailable' if response.status_code>=500 else 'unexpected_http_status')
                else:
                    body=bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body)>2000000:raise FmpError('response_too_large')
                    payload=json.loads(body.decode('utf-8'),parse_float=Decimal,parse_int=Decimal)
                    receipt['response_sha256']=hashlib.sha256(body).hexdigest()
                    request_id=response.headers.get('x-request-id')
                    if request_id and request_id!=self.key and re.fullmatch(r'[a-zA-Z0-9._:-]{1,120}',request_id):receipt['request_id']=request_id
        except FmpError:raise
        except (httpx.HTTPError,ValueError,UnicodeError):code='transport_or_invalid_json'
        # Raise outside the exception handler: no chained URL, body or headers.
        if code:raise FmpError(code) from None
        if not isinstance(payload,list):raise FmpError('provider_error_or_invalid_shape')
        if self.key in json.dumps(payload,default=str):raise FmpError('credential_echo_rejected')
        return payload


def indexed(rows,expected):
    result={}
    for r in rows:
        if not isinstance(r,dict) or r.get('symbol') not in expected or r['symbol'] in result:raise FmpError('unexpected_or_duplicate_provider_symbol')
        result[r['symbol']]=r
    return result


def parse_candidates(entries,profiles,valuations,*,retrieved_at,receipts,fixture=False):
    symbols={r['symbol'] for r in entries}
    profiles=indexed(profiles,symbols);valuations=indexed(valuations,symbols)
    observed=datetime.fromisoformat(retrieved_at)
    if observed.tzinfo is None:raise FmpError('retrieval_timezone_required')
    candidates=[];gaps=[]
    for item in entries:
        symbol=item['symbol'];profile=profiles.get(symbol);value=valuations.get(symbol)
        reason=None
        if profile is None or value is None:reason='missing_profile_or_dated_market_cap'
        else:
            cik=str(profile.get('cik',''))
            if not cik.isdigit():reason='missing_provider_cik'
            elif cik.zfill(10)!=item['cik']:raise FmpError('provider_cik_mismatch')
            elif profile.get('isEtf') is True or profile.get('isFund') is True:raise FmpError('non_equity_instrument')
        if reason:
            gaps.append({**item,'reason':reason});continue
        currency=value.get('currency',profile.get('currency'))
        if not isinstance(currency,str) or not re.fullmatch('[A-Z]{3}',currency):
            gaps.append({**item,'reason':'missing_trading_currency'});continue
        try:
            amount=value['marketCap']
            if isinstance(amount,(float,bool)) or not isinstance(amount,(Decimal,int,str)):raise ValueError()
            amount=Decimal(amount);as_of=date.fromisoformat(value['date'])
            if not amount.is_finite() or amount<=0 or as_of>observed.astimezone(timezone.utc).date():raise ValueError()
        except (KeyError,TypeError,ValueError,InvalidOperation):raise FmpError('invalid_capitalization_or_measurement_date') from None
        metadata={k:profile.get(k) for k in ('companyName','exchange','exchangeFullName','country','isAdr','isin','currency','cik')}
        metadata['cik']=item['cik']
        if metadata['isAdr'] is not None and not isinstance(metadata['isAdr'],bool):raise FmpError('invalid_adr_metadata')
        if any(v is not None and not isinstance(v,str) for k,v in metadata.items() if k!='isAdr'):raise FmpError('invalid_profile_metadata')
        stale=not store.is_fresh(as_of,observed.astimezone(timezone.utc).date())
        candidate={**item,'company_id':identity(item['cik']),'provider':'FMP','market_cap_value':format(amount,'f'),
                   'currency':currency,'as_of':as_of.isoformat(),'measured_at':None,'retrieved_at':retrieved_at,
                   'source_url':BASE+'market-capitalization?symbol='+symbol,'method':'provider_reported_issuer_equity',
                   'profile':metadata,'verification_status':'currency_conflict' if currency!=profile.get('currency') else 'stale' if stale else 'unsupported_currency' if currency!='USD' else 'needs_whole_issuer_review'}
        candidates.append(candidate)
    return {'provider':'FMP','fixture':fixture,'retrieved_at':retrieved_at,'candidates':candidates,'gaps':gaps,'receipts':receipts}


def collect(client,scope='pilot',mode='batch'):
    entries=mapping(scope);profiles=[];values=[]
    required=len(entries)+(1 if mode=='batch' else len(entries))
    if mode not in ('batch','single') or required>client.limit:raise FmpError('insufficient_request_budget')
    for item in entries:profiles.extend(client.get('profile',{'symbol':item['symbol']}))
    if mode=='batch':values=client.get('market-capitalization-batch',{'symbols':','.join(r['symbol'] for r in entries)})
    else:
        for item in entries:values.extend(client.get('market-capitalization',{'symbol':item['symbol']}))
    return parse_candidates(entries,profiles,values,retrieved_at=datetime.now(timezone.utc).isoformat(),receipts=client.receipts,fixture=client.fixture)


def prepare(bundle,review,*,allow_examples=False):
    """Convert explicitly reviewed candidates; unknown currency/scope stays out."""
    access=access_review(review)
    if review.get('candidate_sha256')!=digest(bundle):raise FmpError('candidate_review_hash_mismatch')
    if bundle.get('fixture') is not False and not allow_examples:raise FmpError('test_fixture_is_not_live_data')
    verified=date.fromisoformat(review['verified_on'])
    if verified>store.utc_today():raise FmpError('future_review')
    approvals=review.get('issuers',{})
    records=[];gaps=list(bundle['gaps']);checks=0
    known={r['cik']:r['symbol'] for r in mapping('all')}
    for c in bundle['candidates']:
        if known.get(c['cik'])!=c['symbol'] or c['company_id']!=identity(c['cik']):raise FmpError('candidate_identity_changed')
        approval=approvals.get(c['cik'],{})
        if c['currency']!='USD' or not store.is_fresh(c['as_of']) or c['verification_status']!='needs_whole_issuer_review':
            gaps.append({'cik':c['cik'],'symbol':c['symbol'],'reason':'non_usd_stale_or_unverified'});continue
        if approval.get('whole_issuer_all_classes') is not True or approval.get('symbol')!=c['symbol']:
            gaps.append({'cik':c['cik'],'symbol':c['symbol'],'reason':'whole_issuer_basis_not_reviewed'});continue
        evidence=safe_reference(approval.get('basis_evidence'))
        independent=approval.get('independent_check')
        if independent:
            url=urlsplit(independent['source_url'])
            if url.scheme!='https' or not url.hostname or 'financialmodelingprep' in url.hostname or url.username or url.password:raise FmpError('independent_source_required')
            date.fromisoformat(independent['as_of'])
            other=Decimal(independent['market_cap_value'])
            if not other.is_finite() or other<=0:raise FmpError('invalid_independent_measurement')
            if other!=Decimal(c['market_cap_value']) or independent['as_of']!=c['as_of'] or independent['currency']!='USD':safe_reference(independent.get('difference_explanation'))
            checks+=1
        basis={'provider':'FMP','symbol':c['symbol'],'profile':c['profile'],'review':evidence,'independent_check':independent,'access_valid_until':access['valid_until'],
               'candidate_sha256':digest({k:v for k,v in c.items() if k!='retrieved_at'})}
        source_version=digest({'measurement':{k:c[k] for k in ('cik','symbol','market_cap_value','currency','as_of')},'basis':basis,'access':access['reference']})
        basis.update(retrieved_at=c['retrieved_at'],receipts=bundle['receipts'])
        r=dict(cik=c['cik'],market_cap_usd=c['market_cap_value'],currency='USD',as_of=c['as_of'],measured_at=c['measured_at'],
               source_url=c['source_url'],source_id='FMP:'+c['symbol'],source_version=source_version,
               method=c['method'],issuer_scope='whole_issuer_all_classes',basis_evidence=json.dumps(basis,sort_keys=True,separators=(',',':')),
               access_evidence=access['reference'],verified_on=verified.isoformat())
        records.append(r)
    if records and checks<min(3,len(records)):raise FmpError('independent_checks_required_for_several_issuers')
    return {'records':records,'gaps':gaps,'fixture':bundle['fixture'],'candidate_sha256':digest(bundle),'access_valid_until':access['valid_until'],
            'reviewed_on':verified.isoformat(),'retrieved_at':bundle['retrieved_at'],'receipts':bundle['receipts']}


def import_reviewed(connection,prepared,reviewed_path,*,allow_examples=False):
    if not connection.info.dbname.startswith(store.PREFIX):raise FmpError('normal_database_import_forbidden')
    if prepared.get('fixture') is not False and not allow_examples:raise FmpError('test_fixture_is_not_live_data')
    if store.utc_today()>date.fromisoformat(prepared['access_valid_until']):raise FmpError('access_review_expired')
    if any(not store.is_fresh(r['as_of']) for r in prepared['records']):raise FmpError('stale_reviewed_batch')
    store.import_records(connection,prepared['records'],reviewed_path=reviewed_path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('check','collect','prepare','import-isolated'))
    parser.add_argument('--scope',choices=('pilot','all'),default='pilot')
    parser.add_argument('--mode',choices=('batch','single'),default='batch')
    parser.add_argument('--review',type=Path)
    parser.add_argument('--input',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--request-budget',type=int,default=12)
    args=parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(store.ROOT/'.env')
    key=os.getenv('FMP_API_KEY')
    if args.command=='check':
        print(json.dumps({'key_configured':bool(key),'review_supplied':bool(args.review),'live_requests_performed':0}));return
    try:
        if args.command=='collect':
            if not key:raise FmpError('missing_fmp_api_key')
            if not args.review:raise FmpError('access_review_required')
            review=json.loads(args.review.read_text(encoding='utf-8'))
            client=Client(key,review,max_requests=args.request_budget)
            try:result=collect(client,args.scope,args.mode)
            finally:client.close()
        elif args.command=='prepare':
            result=prepare(json.loads(args.input.read_text(encoding='utf-8')),json.loads(args.review.read_text(encoding='utf-8')))
        else:
            result=json.loads(args.input.read_text(encoding='utf-8'))
            from app.database.connection import get_independent_connection
            with get_independent_connection() as c:
                # Import never creates schema. Owned initialization is separate.
                import tempfile
                with tempfile.TemporaryDirectory(prefix='macrolens-fmp-reviewed-') as tmp:
                    ledger=Path(tmp)/'reviewed.json';ledger.write_text(json.dumps(result['records']),encoding='utf-8')
                    import_reviewed(c,result,ledger)
            print(json.dumps({'imported_or_already_present':len(result['records'])}));return
        if not args.output:raise FmpError('output_path_required')
        args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps({'command':args.command,'records':len(result.get('records',result.get('candidates',[]))),'gaps':len(result['gaps'])}))
    except (FmpError,ValueError,TypeError,KeyError,OSError,AttributeError):
        # No tracebacks from provider requests, credential-bearing environment,
        # bodies or arbitrary reviewed inputs. Codes remain actionable.
        import sys
        error=sys.exc_info()[1]
        code=str(error) if isinstance(error,FmpError) else 'invalid_local_input_or_operation'
        print(json.dumps({'status':'blocked_or_failed','code':code}));raise SystemExit(2) from None


if __name__=='__main__':main()
