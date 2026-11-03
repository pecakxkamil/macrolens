"""Real PostgreSQL 17 E2A validation; only its owned database is changed."""
import copy
import json
import os
import sys
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from app import earnings as e
from app.database.init_earnings_db import initialize
from app.database import init_db
from tests.postgres_http_guard import no_publisher_http


def verify(factory,upgrade=False):
    rows=json.loads(e.DATA.read_text(encoding='utf-8'))
    with factory() as c:
        if not upgrade:initialize(c)  # fresh without any macro tables
        c.execute(init_db.SCHEMA_PATH.read_text(encoding='utf-8'))
        c.execute("INSERT INTO series(series_id,name,category,frequency) VALUES('E2A_PRESERVE','Synthetic legacy','test','monthly')")
        c.execute("INSERT INTO observation_vintages(series_id,observation_date,vintage_date,value,source) VALUES('E2A_PRESERVE','2026-01-01','2026-02-01',1,'fred_snapshot'),('E2A_PRESERVE','2026-01-01','2026-02-02',2,'alfred')")
        initialize(c);initialize(c) # upgrade/repeat, macro untouched
        before=c.execute('SELECT row_to_json(o)::text FROM observation_vintages o ORDER BY id').fetchall()
        e.import_records(c,rows); first=e.load_events(c)
        assert len(first)==6 and len({r['event_id'] for r in first})==6
        e.import_records(c,rows);assert first==e.load_events(c)
        assert c.execute('SELECT count(*) FROM earnings_date_confirmations').fetchone()[0]==12
        n=copy.deepcopy(rows[0]);n['release'].update(date_status='changed',source_local_date='2026-11-18')
        e.import_records(c,[n]);changed=e.load_events(c)
        event=next(x for x in changed if x['ticker']=='NVDA' and x['fiscal_quarter']==3)
        assert event['release']['sequence']==2 and len(event['history'])==3
        e.import_records(c,rows);assert changed==e.load_events(c) # known stale evidence does not reactivate
        n['release']['date_status']='cancelled';e.import_records(c,[n])
        assert next(x for x in e.load_events(c) if x['event_id']==event['event_id'])['release']['date_status']=='cancelled'
        stable=e.load_events(c)
        # Real constraints, not only Python validation. Each attempt rolls back to its savepoint.
        attempts=[
          ("UPDATE earnings_date_confirmations SET date_status='confirmed'",()),
          ("DELETE FROM earnings_source_evidence",()),
          ("INSERT INTO earnings_events SELECT %s,period_id,company_id,publication_status FROM earnings_events LIMIT 1",(uuid4(),)),
          ("UPDATE earnings_periods SET company_id=(SELECT company_id FROM earnings_companies WHERE ticker='AMZN') WHERE company_id=(SELECT company_id FROM earnings_companies WHERE ticker='NVDA')",()),
          ("INSERT INTO earnings_source_evidence SELECT %s,event_id,(SELECT company_id FROM earnings_companies WHERE ticker='AMZN'),source_url,source_kind,verification_method,verified_on,facts,%s FROM earnings_source_evidence WHERE company_id=(SELECT company_id FROM earnings_companies WHERE ticker='NVDA') LIMIT 1",(uuid4(),'f'*64)),
          ("INSERT INTO earnings_date_confirmations SELECT %s,event_id,company_id,component,sequence+1,'changed','approximate',source_local_date,source_local_time,source_timezone,timezone_label_raw,scheduled_at_utc,expected_time_utc,evidence_id,confirmation_id FROM earnings_date_confirmations WHERE precision='exact' LIMIT 1",(uuid4(),)),
        ]
        for command,params in attempts:
            try:
                with c.transaction():c.execute(command,params)
            except psycopg.Error:pass
            else:raise AssertionError('Constraint failed to reject invalid write')
            assert e.load_events(c)==stable
        # A SQL failure after beginning a new evidence batch leaves no partial import.
        c.execute("CREATE FUNCTION earnings_test_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic failure'; END $$")
        c.execute('CREATE TRIGGER earnings_test_fail BEFORE INSERT ON earnings_date_confirmations FOR EACH ROW EXECUTE FUNCTION earnings_test_fail()')
        n['release'].update(date_status='changed',source_local_date='2026-11-19')
        count=c.execute('SELECT count(*) FROM earnings_source_evidence').fetchone()[0]
        try:e.import_records(c,[n])
        except psycopg.Error:pass
        else:raise AssertionError('Expected trigger failure')
        assert e.load_events(c)==stable and c.execute('SELECT count(*) FROM earnings_source_evidence').fetchone()[0]==count
        assert c.execute('SELECT row_to_json(o)::text FROM observation_vintages o ORDER BY id').fetchall()==before
    print('E2A PostgreSQL fresh/upgrade/repeat, metadata, history, stale evidence, constraints, cross-company FK, rollback and macro preservation PASSED')


def main():
    # Control must be the explicit isolated service or CI service, never the developer database.
    if os.environ.get('DB_NAME') not in ('macrolens_earnings_control','macrolens_ci_control'):
        raise ValueError('Explicit isolated control database required')
    params=dict(host=os.environ['DB_HOST'],port=os.environ['DB_PORT'],user=os.environ['DB_USER'],password=os.environ['DB_PASSWORD'])
    with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
        for upgrade in (False,True):
            name='macrolens_earnings_test_'+uuid4().hex
            admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
            try:verify(lambda:psycopg.connect(**params,dbname=name),upgrade)
            finally:
                assert name.startswith('macrolens_earnings_test_') and len(name)==56
                admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
            assert not admin.execute('SELECT 1 FROM pg_database WHERE datname=%s',(name,)).fetchone()
    print('Owned E2A test database removed.')


if __name__=='__main__':
    with no_publisher_http():main()
