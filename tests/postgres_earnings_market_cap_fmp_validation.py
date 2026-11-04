"""Offline FMP wire examples -> existing SQL store -> real API. NOT a live pilot."""
import copy,json,os,sys,tempfile
from pathlib import Path
from datetime import date
from uuid import uuid4
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx,psycopg
from psycopg import sql
from app import earnings as e,earnings_market_cap as cap,earnings_market_cap_fmp as f
from app.database.activate_earnings_financials import table_snapshots
from tests.postgres_earnings_market_cap_validation import seed_all
from tests.postgres_http_guard import no_publisher_http
from tests.test_earnings_market_cap_fmp import access,review_for,TOKEN


def example_transport(request):
    symbol=request.url.params.get('symbol')
    if request.url.path.endswith('/profile'):
        entry=next(r for r in f.mapping('all') if r['symbol']==symbol)
        rows=[dict(symbol=symbol,cik=entry['cik'],currency='USD',isAdr=symbol in ('TSM','ASML'),isEtf=False,isFund=False,companyName='EXPLICIT SYNTHETIC TEST, NOT LIVE')]
    else:
        requested=request.url.params.get('symbols',symbol).split(',')
        rows=[dict(symbol=s,date='2026-11-03',marketCap=str(100000000000+int(next(r['cik'] for r in f.mapping('all') if r['symbol']==s)))) for s in requested]
    return httpx.Response(200,json=rows,headers={'x-request-id':'offline-owned-test'})


def collected(scope):
    client=f.Client(TOKEN,access(),transport=httpx.MockTransport(example_transport),max_requests=54,sleeper=lambda s:None)
    try:bundle=f.collect(client,scope)
    finally:client.close()
    assert bundle['fixture'] is True
    assert len(bundle['receipts'])==(11 if scope=='pilot' else 54)
    return bundle


def verify(factory):
    with factory() as c:seed_all(c)
    with factory() as c,tempfile.TemporaryDirectory(prefix='macrolens-fmp-test-') as tmp,patch.object(cap,'utc_today',return_value=date(2026,11,4)):
        before=table_snapshots(c);prior=e.load_events(c);c.rollback()
        bundle=collected('pilot');review=review_for(bundle)
        try:f.prepare(bundle,review)
        except f.FmpError:pass
        else:raise AssertionError('Synthetic examples accepted as live pilot')
        prepared=f.prepare(bundle,review,allow_examples=True)
        ledger=Path(tmp)/'synthetic-reviewed.json';ledger.write_text(json.dumps(prepared['records']))
        try:
            with c.transaction():
                cap.initialize_isolated(c);f.import_reviewed(c,prepared,ledger,allow_examples=True);c.execute('SELECT 1/0')
        except psycopg.errors.DivisionByZero:pass
        else:raise AssertionError('DDL and import rollback not exercised')
        assert table_snapshots(c)==before;c.rollback()
        cap.initialize_isolated(c)
        f.import_reviewed(c,prepared,ledger,allow_examples=True)
        first=table_snapshots(c);c.rollback();assert first['earnings_market_cap_snapshots']['rows']==10
        # An independent retrieval has different receipt times, not a new valuation.
        second_bundle=collected('pilot');second=f.prepare(second_bundle,review_for(second_bundle),allow_examples=True)
        second['records'][0]['verified_on']='2026-11-04'
        ledger.write_text(json.dumps(second['records']));f.import_reviewed(c,second,ledger,allow_examples=True)
        assert table_snapshots(c)==first;c.rollback()
        all_bundle=collected('all');all_prepared=f.prepare(all_bundle,review_for(all_bundle),allow_examples=True)
        ledger.write_text(json.dumps(all_prepared['records']));f.import_reviewed(c,all_prepared,ledger,allow_examples=True)
        after=table_snapshots(c);c.rollback()
        assert after['earnings_market_cap_snapshots']['rows']==53
        assert all(after[t]==s for t,s in before.items())
        f.import_reviewed(c,all_prepared,ledger,allow_examples=True);assert table_snapshots(c)==after;c.rollback()
        now=e.load_events(c)
        assert [{k:v for k,v in x.items() if not k.startswith('market_cap_')} for x in now]==[{k:v for k,v in x.items() if not k.startswith('market_cap_')} for x in prior]
        assert all(x['market_cap_status']=='verified_snapshot' for x in now);c.rollback()
        from fastapi.testclient import TestClient
        from app.api.main import app
        with patch.object(e,'get_independent_connection',factory),TestClient(app) as client:
            response=client.get('/api/v1/calendar/events?domains=earnings&start_date=2026-05-01&end_date=2026-12-31')
            assert response.status_code==200 and len(response.json()['events'])==34
            with patch.object(cap,'utc_today',return_value=date(2026,11,11)):
                stale=client.get('/api/v1/calendar/events?domains=earnings&start_date=2026-05-01&end_date=2026-12-31')
                assert stale.status_code==200 and all(x['market_cap_status']=='stale' and x['market_cap_usd'] is None and x['market_cap_snapshot'] for x in stale.json()['events'])
        with c.transaction(force_rollback=True):
            limited_review=review_for(bundle);limited_review['access']['valid_until']='2026-11-04'
            limited=f.prepare(bundle,limited_review,allow_examples=True)
            ledger.write_text(json.dumps(limited['records']));f.import_reviewed(c,limited,ledger,allow_examples=True)
            ids={e.identity(r['cik']) for r in limited['records']}
            with patch.object(cap,'utc_today',return_value=date(2026,11,5)):
                expired=[x for x in e.load_events(c) if x['company_id'] in ids]
                assert expired and all(x['market_cap_status']=='unavailable' and x['market_cap_usd'] is None for x in expired)
        assert table_snapshots(c)==after;c.rollback()
        # Whole batch validation: no first-row insertion before a later invalid USD/basis.
        bad=copy.deepcopy(all_prepared);bad['records'][0]['source_version']='new-test-version';bad['records'][-1]['currency']='EUR'
        ledger.write_text(json.dumps(bad['records']))
        try:f.import_reviewed(c,bad,ledger,allow_examples=True)
        except ValueError:pass
        else:raise AssertionError('Invalid batch accepted')
        assert table_snapshots(c)==after;c.rollback()
    print('OFFLINE FMP examples PASSED: 11/54 bounded mock requests; 10/53 synthetic SQL records, idempotent repeated retrieval, stale/expired access, batch rollback, real API and preserved E2A-E2E. Live FMP imported: 0.')


def main():
    if os.environ.get('DB_NAME')!='macrolens_fmp_control':raise ValueError('Owned FMP control required')
    params={k:os.environ[v] for k,v in [('host','DB_HOST'),('port','DB_PORT'),('user','DB_USER'),('password','DB_PASSWORD')]}
    if params['host']!='127.0.0.1':raise ValueError('Loopback required')
    with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
        name=cap.PREFIX+'fmp_'+uuid4().hex[:10]
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:verify(lambda:psycopg.connect(**params,dbname=name))
        finally:admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))


if __name__=='__main__':
    with no_publisher_http():main()
