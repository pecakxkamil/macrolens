"""E2C on owned PostgreSQL 17 only; no normal database, HTTP or automatic feed."""
import copy,json,os,sys
from datetime import date
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from fastapi.testclient import TestClient
from app import earnings as e,earnings_financials as f,earnings_coverage as coverage
from app.database.init_db import SCHEMA_PATH
from app.database.init_earnings_db import initialize
from app.database.activate_earnings_financials import table_snapshots
from tests.postgres_http_guard import no_publisher_http


def rows(c,table):
    return set(x[0] for x in c.execute(sql.SQL('SELECT row_to_json(t)::text FROM {} t').format(sql.Identifier(table))))


def reject(c,operation):
    try:
        with c.transaction(): operation()
    except (ValueError,psycopg.Error): return
    raise AssertionError('Unsafe import accepted')


def verify(factory):
    records=json.loads(coverage.DATA.read_text(encoding='utf-8'))
    with factory() as c:
        c.execute(SCHEMA_PATH.read_text(encoding='utf-8'))
        c.execute("INSERT INTO series(series_id,name,category,frequency) VALUES('E2C_PRESERVE','Synthetic','test','quarterly')")
        c.execute("INSERT INTO observation_vintages(series_id,observation_date,vintage_date,value,source) VALUES('E2C_PRESERVE','2026-01-01','2026-02-01',1,'fred_snapshot'),('E2C_PRESERVE','2026-01-01','2026-03-01',2,'alfred')")
        initialize(c);e.import_records(c,json.loads(e.DATA.read_text(encoding='utf-8')))
        f.initialize_isolated(c);f.import_records(c,json.loads(f.DATA.read_text(encoding='utf-8')))
    with factory() as c:
        before=table_snapshots(c);original={t:rows(c,t) for t in before if t.startswith('earnings_')}
        c.commit()
        def migration_and_import_failure():
            coverage.initialize_isolated(c)
            coverage.import_records(c,records)
            c.execute('SELECT 1/0')
        reject(c,migration_and_import_failure)
        assert table_snapshots(c)==before;c.commit()
        assert coverage.initialize_isolated(c)=='created'
        assert coverage.initialize_isolated(c)=='already_initialized'
        c.commit()
        # A failure after inserting registry companies rolls back the entire batch.
        bad=copy.deepcopy(records);bad[-1]['period_label']='wrong fiscal period'
        reject(c,lambda:coverage.import_records(c,bad))
        assert table_snapshots(c)==before;c.commit()
        coverage.import_records(c,records)
    with factory() as c:
        first=table_snapshots(c)
        assert first['earnings_companies']['rows']==53
        assert first['earnings_events']['rows']==37
        assert first['earnings_financial_documents']==before['earnings_financial_documents']
        assert first['earnings_financial_observations']==before['earnings_financial_observations']
        for t in before:
            if not t.startswith('earnings_'):assert first[t]==before[t]
        for t,old in original.items():assert old<=rows(c,t)
        c.commit();coverage.import_records(c,records)
    with factory() as c:
        assert table_snapshots(c)==first;c.commit()
        # Registry-only emitters never generate quarterly periods or unknown events.
        assert c.execute("SELECT count(*) FROM earnings_events e JOIN earnings_companies c USING(company_id) WHERE c.ticker='JPM'").fetchone()[0]==0
        assert c.execute("SELECT count(*) FROM earnings_company_aliases WHERE ticker IN ('GOOG','GOOGL')").fetchone()[0]==2
        assert c.execute("SELECT count(*) FROM earnings_events e JOIN earnings_companies c USING(company_id) WHERE c.ticker='GOOGL'").fetchone()[0]==1
        c.commit()
        # Force a real SQL failure after registration: no partial issuer additions.
        def sql_failure():
            coverage.import_records(c,[])
            c.execute('SELECT 1/0')
        reject(c,sql_failure)
        assert table_snapshots(c)==first;c.commit()
        amended=copy.deepcopy(next(r for r in records if r['ticker']=='AMD'))
        amended['release'].update(date_status='changed',source_local_date='2026-11-04')
        amended['release']['evidence']['facts']='Synthetic date correction for SQL transition test only'
        coverage.import_records(c,[amended])
    previous=e.get_independent_connection;e.get_independent_connection=factory
    try:
        assert len(e.companies())==53
        all_events=e.calendar_events(date(2026,1,1),date(2026,12,31))
        assert len(all_events['events'])==34 and len(all_events['undated'])==3
        assert len(e.calendar_events(date(2026,1,1),date(2026,12,31),{'GOOG','GOOGL'})['events'])==1
        assert not e.calendar_events(date(2026,1,1),date(2026,12,31),{'JPM'})['events']
        amd=next(r for r in all_events['events'] if r['ticker']=='AMD')
        assert amd['release']['source_local_date']=='2026-11-04' and amd['call']['source_local_date']=='2026-11-03'
        assert amd['release']['scheduled_at_utc'] is None
        with factory() as c:coverage.import_records(c,records)
        assert next(r for r in e.calendar_events(date(2026,1,1),date(2026,12,31))['events'] if r['ticker']=='AMD')['release']['source_local_date']=='2026-11-04'
        with factory() as c:before_get=table_snapshots(c)
        from app.api.main import app
        with TestClient(app) as client:
            response=client.get('/api/v1/calendar/events?domains=earnings&start_date=2026-10-26&end_date=2026-11-01')
            assert response.status_code==200
            assert {'INTC','AMZN','MSFT','GOOGL','KLAC','NOW'}<={r['ticker'] for r in response.json()['events']}
            assert len(client.get('/api/v1/earnings/companies').json())==53
            for event in response.json()['events']:
                assert client.get('/api/v1/earnings/events/'+event['event_id']).status_code==200
        with factory() as c:assert table_snapshots(c)==before_get
    finally:e.get_independent_connection=previous
    print('E2C PASSED: 53 issuers, 27 new dates, aliases, fiscal validation, idempotency, revisions, SQL rollback, real API, E2A/E2B and 13 macro tables preserved')


def main():
    if os.environ.get('DB_NAME')!='macrolens_ci_control':raise ValueError('Owned control database required')
    params={k:os.environ[v] for k,v in [('host','DB_HOST'),('port','DB_PORT'),('user','DB_USER'),('password','DB_PASSWORD')]}
    name='macrolens_earnings_e2b_e2c_'+uuid4().hex
    with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:verify(lambda:psycopg.connect(**params,dbname=name))
        finally:
            assert name.startswith('macrolens_earnings_e2b_e2c_') and name!='macrolens'
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))


if __name__=='__main__':
    with no_publisher_http(): main()
