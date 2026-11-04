"""E2D PostgreSQL 17 integration, synthetic macro + reviewed local metadata only."""
import copy
import json
import os
import sys
from pathlib import Path
from datetime import datetime,timezone
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from app import earnings as e,earnings_financials as f,earnings_coverage as coverage,earnings_reports as r
from app.database import activate_earnings as base,activate_earnings_financials as snapshots
from app.database.init_db import SCHEMA_PATH
from app.database.init_earnings_db import initialize
from tests.postgres_http_guard import no_publisher_http


def seed(connection):
    connection.execute(SCHEMA_PATH.read_text(encoding='utf-8'))
    connection.execute("INSERT INTO series(series_id,name,category,frequency) VALUES('E2D_PRESERVE','Synthetic','test','quarterly')")
    connection.execute("INSERT INTO observation_vintages(series_id,observation_date,vintage_date,value,source) VALUES('E2D_PRESERVE','2026-01-01','2026-02-01',1,'fred_snapshot'),('E2D_PRESERVE','2026-01-01','2026-03-01',2,'alfred')")
    initialize(connection);e.import_records(connection,json.loads(e.DATA.read_text(encoding='utf-8')))
    f.initialize_isolated(connection);f.import_records(connection,snapshots.seed())
    coverage.initialize_isolated(connection);coverage.import_records(connection,json.loads(coverage.DATA.read_text(encoding='utf-8')))


def verify(factory):
    records=json.loads(r.DATA.read_text(encoding='utf-8'))
    with factory() as c:seed(c)
    with factory() as c:
        before=snapshots.table_snapshots(c);schema=base.digest(base.catalog(c,True));c.rollback()
        fallback=e.load_events(c)
        assert all(x['report_store_status']=='not_activated' for x in fallback);c.rollback()
        try:
            with c.transaction():
                r.initialize_isolated(c);r.import_records(c,records[:2]);c.execute('SELECT 1/0')
        except psycopg.errors.DivisionByZero:pass
        else:raise AssertionError('Controlled SQL failure not raised')
        assert snapshots.table_snapshots(c)==before and base.digest(base.catalog(c,True))==schema;c.rollback()
        with c.transaction():
            r.initialize_isolated(c)
            pending=copy.deepcopy(records[0]);pending['observations']=[]
            r.import_records(c,[pending])
            observed=next(x for x in e.load_events(c) if x['ticker']==pending['ticker'])
            assert observed['publication_state']['code']=='published_pending' and observed['revenue_actual'] is None
            partial=copy.deepcopy(records[0]);partial['observations']=partial['observations'][:1]
            r.import_records(c,[partial])
            observed=next(x for x in e.load_events(c) if x['ticker']==pending['ticker'])
            assert observed['publication_state']['code']=='published_partial' and observed['publication_state']['missing_metrics']==['reported_diluted_eps']
            r.import_records(c,records)
        signature=base.digest(base.catalog(c,True));c.rollback()
        assert r.initialize_isolated(c,signature)=='already_initialized'
        after=snapshots.table_snapshots(c);c.rollback()
        assert all(after[t]==s for t,s in before.items())
        assert after['earnings_report_documents']['rows']==27 and after['earnings_report_observations']['rows']==46
        r.import_records(c,records)
        assert snapshots.table_snapshots(c)==after;c.rollback()
        # Publication status is time-dependent. Verify the audited morning
        # explicitly; CI run dates must not redefine the reviewed evidence.
        events=e.load_events(c)
        for item in events:
            item['publication_state']=r.publication_state(item,item['report_documents'],now=datetime(2026,11,4,10,tzinfo=timezone.utc))
        by={x['ticker']:x for x in events if x['ticker'] not in ('NVDA','AMZN','INTC')}
        assert by['AAPL']['publication_state']['code']=='published_complete'
        assert by['PLTR']['reported_eps_actual']['actual']=='0.44'
        assert by['AMD']['reported_eps_actual']['actual']=='1.46'
        assert by['TSM']['reported_eps_actual']['currency']=='TWD' and by['TSM']['gaap_diluted_eps_actual'] is None
        assert by['ASML']['reported_eps_actual']['reporting_standard']=='US_GAAP' and by['ASML']['revenue_actual']['currency']=='EUR'
        for ticker in ('QCOM','ARM','PANW','SNOW'):
            assert by[ticker]['publication_state']['code']=='scheduled' and by[ticker]['reported_eps_actual'] is None
        c.rollback()
        # Append-only at SQL level, including TRUNCATE.
        for table in r.TABLES:
            for command in (f'UPDATE {table} SET record_fingerprint=record_fingerprint',f'DELETE FROM {table}',f'TRUNCATE {table}'):
                try:
                    with c.transaction():c.execute(command)
                except psycopg.Error:pass
                else:raise AssertionError('Mutable report history accepted')
        # Real FK/CHECK/transition failures, never weakening global guards.
        first=c.execute('SELECT observation_id FROM earnings_report_observations LIMIT 1').fetchone()[0];c.rollback()
        for modification in ("actual=actual*1000", "currency='EUR'", "share_basis='ADR'", "company_id='00000000-0000-0000-0000-000000000000'", "period_id='00000000-0000-0000-0000-000000000000'"):
            try:
                with c.transaction():
                    c.execute('CREATE TEMP TABLE bad (LIKE earnings_report_observations INCLUDING DEFAULTS) ON COMMIT DROP')
                    c.execute('INSERT INTO bad SELECT * FROM earnings_report_observations WHERE observation_id=%s',(first,))
                    c.execute('UPDATE bad SET observation_id=%s,record_fingerprint=%s,version=version+1,supersedes_id=%s,correction_reason=%s',(uuid4(),'f'*64,first,'Synthetic invalid revision'))
                    c.execute('UPDATE bad SET '+modification)
                    c.execute('INSERT INTO earnings_report_observations SELECT * FROM bad')
            except psycopg.Error:pass
            else:raise AssertionError('Invalid SQL metric accepted: '+modification)
        # Genuine version correction, then stale known capture must not reactivate.
        apple=next(x for x in records if x['ticker']=='AAPL')
        corrected=copy.deepcopy(apple);corrected['observations'][1].update(source_value='2.11',correction_reason='Synthetic correction test, not production data')
        r.import_records(c,[corrected]);revised=snapshots.table_snapshots(c);c.rollback()
        r.import_records(c,[apple]);assert snapshots.table_snapshots(c)==revised;c.rollback()
        current=next(x for x in e.load_events(c) if x['ticker']=='AAPL')
        assert current['reported_eps_actual']['actual']=='2.11' and current['reported_eps_actual']['version']=='2';c.rollback()
        # Full rollback of an import batch after a real SQL error on its second row.
        try:
            with c.transaction():
                c.execute("CREATE FUNCTION pg_temp.reject_pltr() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.company_id='"+e.identity('0001321655')+"'::uuid THEN RAISE EXCEPTION 'controlled failure'; END IF; RETURN NEW; END $$")
                c.execute('CREATE TRIGGER synthetic_e2d_failure BEFORE INSERT ON earnings_report_observations FOR EACH ROW EXECUTE FUNCTION pg_temp.reject_pltr()')
                x=copy.deepcopy(corrected);x['observations'][1].update(source_value='2.12',correction_reason='Synthetic rollback test')
                y=copy.deepcopy(next(x for x in records if x['ticker']=='PLTR'));y['observations'][1].update(source_value='0.45',correction_reason='Synthetic rollback test')
                r.import_records(c,[x,y])
        except psycopg.Error:pass
        else:raise AssertionError('SQL rollback test did not fail')
        assert snapshots.table_snapshots(c)==revised;c.rollback()
        final=snapshots.table_snapshots(c)
        assert all(final[t]==s for t,s in before.items());c.rollback()
        # Real HTTP endpoints over the same SQL, with no transport fixtures.
        from fastapi.testclient import TestClient
        from app.api.main import app
        from unittest.mock import patch
        with patch.object(e,'get_independent_connection',factory),TestClient(app) as client:
            payload=client.get('/api/v1/calendar/events?domains=earnings&start_date=2026-05-01&end_date=2026-12-31')
            assert payload.status_code==200 and len(payload.json()['events'])==34
            detail=client.get('/api/v1/earnings/events/'+current['event_id'])
            assert detail.status_code==200 and detail.json()['publication_state']['code']=='published_complete'
        assert snapshots.table_snapshots(c)==final
    print('E2D PASSED: 27 reviewed documents/46 actuals, US GAAP/IFRS and USD/EUR/TWD, states, real API, idempotency/revisions/append-only, SQL rollback DDL+seed/batch, all 21 original tables unchanged')


def main():
    if os.environ.get('DB_NAME')!='macrolens_e2d_control':raise ValueError('Owned E2D control database required')
    params={k:os.environ[v] for k,v in [('host','DB_HOST'),('port','DB_PORT'),('user','DB_USER'),('password','DB_PASSWORD')]}
    with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
        name=r.PREFIX+uuid4().hex
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:verify(lambda:psycopg.connect(**params,dbname=name))
        finally:
            assert name.startswith(r.PREFIX) and len(name)==len(r.PREFIX)+32
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))


if __name__=='__main__':
    with no_publisher_http():main()
