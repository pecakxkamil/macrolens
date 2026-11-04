"""E2E isolation: no synthetic Calendar events and no publisher transport."""
import copy
import json
import os
import sys
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from app import earnings as e, earnings_reports as r, earnings_history as h
from app.database import activate_earnings as base, activate_earnings_financials as snapshots
from tests.postgres_earnings_report_validation import seed
from tests.postgres_http_guard import no_publisher_http


def verify(factory):
    records=json.loads(h.DATA.read_text(encoding='utf-8'))
    with factory() as c:
        seed(c);r.initialize_isolated(c);r.import_records(c,json.loads(r.DATA.read_text(encoding='utf-8')))
    with factory() as c:
        before=snapshots.table_snapshots(c);c.rollback()
        fallback=e.load_events(c);assert all(x['previous_store_status']=='not_activated' for x in fallback);c.rollback()
        try:
            with c.transaction():
                h.initialize_isolated(c);h.import_records(c,records);c.execute('SELECT 1/0')
        except psycopg.errors.DivisionByZero:pass
        else:raise AssertionError('SQL rollback not exercised')
        assert snapshots.table_snapshots(c)==before;c.rollback()
        h.initialize_isolated(c);h.import_records(c,records)
        after=snapshots.table_snapshots(c);signature=base.digest(base.catalog(c,True));c.rollback()
        assert len(after)==24 and after['earnings_historical_reports']['rows']==23
        assert all(after[t]==value for t,value in before.items())
        assert h.initialize_isolated(c,signature)=='already_initialized'
        h.import_records(c,records);assert snapshots.table_snapshots(c)==after;c.rollback()
        events=e.load_events(c)
        def find(ticker,quarter):return next(x for x in events if x['ticker']==ticker and x['fiscal_quarter']==quarter)
        for ticker,q,current_eps,prior_eps,current_rev,prior_rev in [
            ('INTC',3,'0.60','-2.16','16513000000','16128000000'),
            ('AMZN',3,'1.89','5.75','201944000000','200606000000'),
            ('NVDA',2,'2.46','2.39','96221000000','81615000000')]:
            event=find(ticker,q)
            for key,value in [('current_eps_actual',current_eps),('previous_eps_actual',prior_eps),('current_revenue_actual',current_rev),('previous_revenue_actual',prior_rev)]:
                from decimal import Decimal
                assert Decimal(event[key]['actual'])==Decimal(value),(ticker,key,event[key])
        future=find('NVDA',3);assert future['current_eps_actual'] is None and future['previous_eps_actual']['actual']=='2.46'
        for record in records:
            current=next(x for x in events if x['ticker']==record['ticker'])
            assert current['previous_period']['fiscal_quarter']==record['fiscal_quarter']
            assert current['previous_revenue_actual']['source_url']==record['source_url']
            assert all(current[k] is None for k in current if k.endswith('_forecast'))
        assert find('MSFT',1)['previous_period']['fiscal_year']==2026
        assert find('CRWD',2)['previous_eps_actual'] is None
        assert find('TSM',3)['previous_eps_actual']['currency']=='TWD'
        assert find('ASML',3)['previous_eps_actual']['reporting_standard']=='US_GAAP'
        c.rollback()
        for statement in ('UPDATE earnings_historical_reports SET version=version','DELETE FROM earnings_historical_reports','TRUNCATE earnings_historical_reports'):
            try:
                with c.transaction():c.execute(statement)
            except psycopg.Error:pass
            else:raise AssertionError('Mutable history accepted')
        row=c.execute('SELECT document_id,company_id,cik,fiscal_year,fiscal_quarter,payload FROM earnings_historical_reports WHERE cik=%s',(records[0]['cik'],)).fetchone();c.rollback()
        def revision(payload,version=2,supersedes=None):
            c.execute('''INSERT INTO earnings_historical_reports(document_id,company_id,cik,fiscal_year,fiscal_quarter,version,supersedes_id,correction_reason,record_fingerprint,payload)
              VALUES(%s,%s,%s,%s,%s,%s,%s,'Synthetic revision',%s,%s)''',(uuid4(),*row[1:5],version,supersedes or row[0],uuid4().hex*2,Jsonb(payload)))
        for change in ('scale','currency','basic','missing','duplicate','issuer','period','null','nonfinite','precision'):
            bad=copy.deepcopy(row[5])
            if change=='scale':bad['observations'][0]['actual']='1'
            if change=='currency':bad['observations'][0]['currency']='EUR'
            if change=='basic':bad['observations'][1]['methodology']='basic_eps'
            if change=='missing':bad['observations'][0].pop('source_value')
            if change=='duplicate':bad['observations']=[bad['observations'][0]]*2
            if change=='issuer':bad['cik']='0000000000'
            if change=='period':bad['fiscal_quarter']=1
            if change=='null':bad['observations'][0]['share_basis']=None
            if change=='nonfinite':bad['observations'][0]['source_value']='NaN'
            if change=='precision':bad['observations'][1]['decimal_places']='0'
            try:
                with c.transaction():revision(bad)
            except psycopg.Error:pass
            else:raise AssertionError('Invalid historical SQL accepted: '+change)
        # A new complete report snapshot must not inherit omitted old EPS.
        with c.transaction(force_rollback=True):
            partial=copy.deepcopy(row[5]);partial['observations']=partial['observations'][:1]
            revision(partial)
            current=next(x for x in e.load_events(c) if x['ticker']==records[0]['ticker'])
            assert current['previous_eps_actual'] is None and current['previous_revenue_actual'] is not None
            assert len(current['previous_history'])==2
            h.import_records(c,[records[0]])
            assert next(x for x in e.load_events(c) if x['ticker']==records[0]['ticker'])['previous_eps_actual'] is None
            try:
                with c.transaction():revision(partial,version=4)
            except psycopg.Error:pass
            else:raise AssertionError('Skipped revision accepted')
        assert snapshots.table_snapshots(c)==after;c.rollback()
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from app.api.main import app
        with patch.object(e,'get_independent_connection',factory),TestClient(app) as client:
            result=client.get('/api/v1/calendar/events?domains=earnings&start_date=2026-05-01&end_date=2026-12-31')
            assert result.status_code==200 and len(result.json()['events'])==34
            a=client.get('/api/v1/calendar/events?domains=earnings&start_date=2026-05-01&end_date=2026-12-31&tickers=GOOG').json()
            b=client.get('/api/v1/calendar/events?domains=earnings&start_date=2026-05-01&end_date=2026-12-31&tickers=GOOGL').json()
            assert a['events']==b['events'] and len(a['events'])==1
            detail=client.get('/api/v1/earnings/events/'+find('INTC',3)['event_id'])
            assert detail.status_code==200 and detail.json()['previous_eps_actual']['actual']=='-2.16'
        assert snapshots.table_snapshots(c)==after
    print('E2E PASSED: 23 historical reports / 45 metrics; exact fiscal previous, real API, aliases, immutable history, revisions, stale captures, rollback, 23 original tables unchanged; no new events')


def main():
    if os.environ.get('DB_NAME')!='macrolens_e2e_control':raise ValueError('Owned E2E control name required')
    params={k:os.environ[v] for k,v in [('host','DB_HOST'),('port','DB_PORT'),('user','DB_USER'),('password','DB_PASSWORD')]}
    if params['host'] not in ('127.0.0.1','localhost'):raise ValueError('Loopback required')
    with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
        name=h.PREFIX+uuid4().hex[:12]
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:verify(lambda:psycopg.connect(**params,dbname=name))
        finally:admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))


if __name__=='__main__':
    with no_publisher_http():main()
