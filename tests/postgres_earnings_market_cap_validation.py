"""Owned synthetic market cap fixtures; no real provider or normal database."""
import json,os,sys,tempfile
from datetime import date
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from app import earnings as e,earnings_reports as r,earnings_history as h,earnings_market_cap as cap
from app.database import activate_earnings as base,activate_earnings_financials as snapshots
from tests.postgres_earnings_report_validation import seed
from tests.postgres_http_guard import no_publisher_http
from tests.test_earnings_market_cap import snapshot


def seed_all(c):
    seed(c);r.initialize_isolated(c);r.import_records(c,json.loads(r.DATA.read_text()))
    h.initialize_isolated(c);h.import_records(c,json.loads(h.DATA.read_text()))


def synthetic_records(c):
    return [{**snapshot(),'cik':cik} for cik, in c.execute('SELECT cik FROM earnings_companies ORDER BY cik').fetchall()]


def verify(factory):
    with factory() as c:seed_all(c)
    with factory() as c, tempfile.TemporaryDirectory(prefix='macrolens-cap-') as tmp, patch.object(cap,'utc_today',return_value=date(2026,11,4)):
        records=synthetic_records(c);assert len(records)==53
        ledger=Path(tmp)/'synthetic.json';ledger.write_text(json.dumps(records));c.rollback()
        before=snapshots.table_snapshots(c);prior=e.load_events(c);c.rollback()
        assert all(x['market_cap_status']=='not_activated' for x in prior)
        with patch.object(cap,'DATA',ledger):
            try:
                with c.transaction():cap.initialize_isolated(c);cap.import_records(c,records);c.execute('SELECT 1/0')
            except psycopg.errors.DivisionByZero:pass
            else:raise AssertionError('DDL+seed failure not exercised')
            assert snapshots.table_snapshots(c)==before;c.rollback()
            cap.initialize_isolated(c);cap.import_records(c,records)
            after=snapshots.table_snapshots(c);signature=base.digest(base.catalog(c,True));c.rollback()
            assert len(after)==25 and all(after[t]==s for t,s in before.items())
            assert after['earnings_market_cap_snapshots']['rows']==53
            assert cap.initialize_isolated(c,signature)=='already_initialized'
            cap.import_records(c,records);assert snapshots.table_snapshots(c)==after;c.rollback()
            events=e.load_events(c)
            assert all(x['market_cap_usd']=='850400000000.123456789' and x['market_cap_as_of']=='2026-11-03' for x in events)
            assert [{k:v for k,v in x.items() if not k.startswith('market_cap_')} for x in events]==[{k:v for k,v in x.items() if not k.startswith('market_cap_')} for x in prior]
            nvda=[x for x in events if x['ticker']=='NVDA'];assert len({x['market_cap_usd'] for x in nvda})==1
            with patch.object(cap,'utc_today',return_value=date(2026,11,11)):
                stale=e.load_events(c)
                assert all(x['market_cap_usd'] is None and x['market_cap_status']=='stale' and x['market_cap_snapshot']['as_of']=='2026-11-03' for x in stale)
            c.rollback()
            for statement in ('UPDATE earnings_market_cap_snapshots SET market_cap_usd=1','DELETE FROM earnings_market_cap_snapshots','TRUNCATE earnings_market_cap_snapshots'):
                try:
                    with c.transaction():c.execute(statement)
                except psycopg.Error:pass
                else:raise AssertionError('Mutable market cap accepted')
            # A later verification/capture cannot promote an older measurement.
            older={**records[0],'as_of':'2026-11-02','source_version':'older-but-imported-later','market_cap_usd':'1'}
            ledger.write_text(json.dumps([*records,older]))
            with c.transaction(force_rollback=True):
                cap.import_records(c,[older]);selected=e.load_events(c)
                assert all(x['market_cap_usd']=='850400000000.123456789' for x in selected)
            for column,value in [('market_cap_usd','0'),('market_cap_usd',"'NaN'::numeric"),('currency',"'EUR'"),('method',"'enterprise_value'"),('issuer_scope',"'ADR_only'"),('cik',"'0000000000'"),('measured_at',"'2026-11-02T00:00:00Z'::timestamptz")]:
                try:
                    with c.transaction():
                        c.execute('CREATE TEMP TABLE bad_cap (LIKE earnings_market_cap_snapshots INCLUDING DEFAULTS) ON COMMIT DROP')
                        c.execute('INSERT INTO bad_cap SELECT * FROM earnings_market_cap_snapshots LIMIT 1')
                        c.execute('UPDATE bad_cap SET snapshot_id=%s,fingerprint=%s,source_version=%s',(uuid4(),uuid4().hex*2,'bad'))
                        c.execute('UPDATE bad_cap SET '+column+'='+value)
                        c.execute('INSERT INTO earnings_market_cap_snapshots SELECT * FROM bad_cap')
                except psycopg.Error:pass
                else:raise AssertionError('Invalid SQL market cap: '+column)
            with c.transaction(force_rollback=True):
                c.execute('DROP TRIGGER earnings_market_cap_no_truncate ON earnings_market_cap_snapshots')
                try:cap.initialize_isolated(c,signature)
                except ValueError:pass
                else:raise AssertionError('Foreign schema accepted')
            from fastapi.testclient import TestClient
            from app.api.main import app
            with patch.object(e,'get_independent_connection',factory),TestClient(app) as client:
                query='/api/v1/calendar/events?domains=earnings&start_date=2026-05-01&end_date=2026-12-31'
                result=client.get(query);assert result.status_code==200 and len(result.json()['events'])==34
                for a,b in [('GOOG','GOOGL'),('BRK.B','BRK-B')]:
                    assert client.get(query+'&tickers='+a).json()['events']==client.get(query+'&tickers='+b).json()['events']
                detail=client.get('/api/v1/earnings/events/'+events[0]['event_id']);assert detail.status_code==200
                assert detail.json()['market_cap_snapshot']['issuer_scope']=='whole_issuer_all_classes'
            assert snapshots.table_snapshots(c)==after
    print('Market Cap PASSED: 53 synthetic whole-issuer USD snapshots, precision, latest date, aliases, ADR/class rejection, idempotency/append-only/rollback, real API, all 24 previous tables unchanged')


def main():
    if os.environ.get('DB_NAME')!='macrolens_cap_control':raise ValueError('Owned cap control name required')
    params={k:os.environ[v] for k,v in [('host','DB_HOST'),('port','DB_PORT'),('user','DB_USER'),('password','DB_PASSWORD')]}
    if params['host']!='127.0.0.1':raise ValueError('Owned loopback required')
    with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
        name=cap.PREFIX+uuid4().hex[:12];admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:verify(lambda:psycopg.connect(**params,dbname=name))
        finally:admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))


if __name__=='__main__':
    with no_publisher_http():main()
