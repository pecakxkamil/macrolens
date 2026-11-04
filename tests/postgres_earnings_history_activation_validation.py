"""E2E activation on owned restored PostgreSQL 17 only; real backup/restore."""
import copy
import json
import os
import re
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from app import earnings as dates
from app.database import activate_earnings as b,activate_earnings_financials as f,activate_earnings_history as a
from tests.postgres_earnings_report_validation import seed as original_seed
from tests.postgres_earnings_financial_activation_validation import make_backup
from tests.postgres_http_guard import no_publisher_http


def objects(catalog):
    return sorted([['public',r[0],r[1]] for r in catalog['relations']]+[['public',r[0],'function'] for r in catalog['functions']],key=lambda r:(r[0],r[1]))


def reference(connection):
    before=b.catalog(connection,True);connection.rollback()
    with connection.transaction(force_rollback=True):
        a.reports.initialize_isolated(connection)
        a.import_seed(connection,a.seed())
        a.verify_seed(connection,a.manifest(a.seed()))
        after=b.catalog(connection,True)
    result=json.loads(json.dumps({name:dict(catalog=catalog,objects=objects(catalog)) for name,catalog in [('before',before),('after',after)]},default=str))
    a.check_reference(result)
    return result


def verify(factory,admin,name,container,ref,directory):
    backup=make_backup(factory,admin,name,container,directory)
    with factory() as c:
        c.read_only=True;plan=a.prepare(c,backup['target'],backup,ref)
        assert c.info.transaction_status==psycopg.pq.TransactionStatus.IDLE
    token=b.digest(plan);target=plan['target_label']
    def rejected(candidate=plan,label=target,hash_value=token):
        with factory() as c:
            before=f.table_snapshots(c);c.rollback()
            try:a.apply(c,candidate,label,hash_value)
            except ValueError:pass
            else:raise AssertionError('Invalid activation accepted')
            assert c.info.transaction_status==psycopg.pq.TransactionStatus.IDLE
            assert f.table_snapshots(c)==before
    rejected(label='wrong');rejected(hash_value='wrong')
    for kind in ('artifact','backup','restore','identity','manifest'):
        bad=copy.deepcopy(plan)
        if kind=='artifact':bad['artifacts']['app/earnings_reports.py']='wrong'
        elif kind=='backup':bad['backup']['sha256']='0'*64
        elif kind=='restore':bad['backup']['restore_validation']['sha256']='0'*64
        elif kind=='identity':bad['target']['database_oid']+=1
        else:bad['seed_manifest'][a.TABLES[0]][0]['payload']['observations'][0]['actual']='999'
        rejected(bad,target,b.digest(bad))
    # Actual damaged archive, not only a manifest mismatch.
    archive=directory/'damaged.dump';archive.write_bytes(b'BROKEN'+Path(backup['path']).read_bytes()[6:])
    bad=copy.deepcopy(plan);bad['backup'].update(path=str(archive),bytes=archive.stat().st_size,sha256=b.file_hash(archive))
    rejected(bad,target,b.digest(bad))
    with patch.object(a,'artifacts',return_value={**a.artifacts(),'app/earnings_reports.py':'changed'}):rejected()
    bad_seed=a.seed();bad_seed[0]['observations'][0]['source_value']='999'
    with patch.object(a,'seed',return_value=bad_seed):rejected()
    # A real different connection/database cannot pass the approved identity.
    with psycopg.connect(host=admin.info.host,port=admin.info.port,user=admin.info.user,password=os.environ['DB_PASSWORD'],dbname='postgres') as wrong:
        try:a.apply(wrong,plan,target,token)
        except ValueError:pass
        else:raise AssertionError('Different live database accepted')
    with factory() as c:c.execute('ALTER TABLE earnings_companies ADD COLUMN foreign_probe integer')
    try:rejected()
    finally:
        with factory() as c:c.execute('ALTER TABLE earnings_companies DROP COLUMN foreign_probe')
    with factory() as c:
        series_id,old=c.execute('SELECT series_id,name FROM series ORDER BY series_id LIMIT 1').fetchone()
        c.execute("UPDATE series SET name='Synthetic activation drift probe' WHERE series_id=%s",(series_id,))
    try:rejected()
    finally:
        with factory() as c:c.execute('UPDATE series SET name=%s WHERE series_id=%s',(old,series_id))
    with factory() as c:c.execute('CREATE TABLE earnings_historical_reports (unrelated integer)')
    try:rejected()
    finally:
        with factory() as c:c.execute('DROP TABLE earnings_historical_reports')
    with factory() as c:
        before=f.table_snapshots(c);c.rollback()
        original=a.import_seed
        def broken(connection,records):
            original(connection,records[:1]);connection.execute('SELECT 1/0')
        with patch.object(a,'import_seed',broken):
            try:a.apply(c,plan,target,token)
            except psycopg.errors.DivisionByZero:pass
            else:raise AssertionError('Controlled SQL failure not raised')
        assert f.table_snapshots(c)==before and b.digest(b.catalog(c,True))==b.digest(ref['before']['catalog']);c.rollback()
        receipt=a.apply(c,plan,target,token)
        assert receipt['outcome']=='created' and receipt['counts']==a.AFTER and len(receipt['after_snapshots'])==24
        repeated=a.apply(c,plan,target,token)
        assert repeated['outcome']=='already_initialized' and repeated['after_snapshots']==receipt['after_snapshots']
        assert {t:s for t,s in receipt['after_snapshots'].items() if t not in a.TABLES}==before
        a.verify_seed(c,plan['seed_manifest']);c.rollback()
        from fastapi.testclient import TestClient
        from app.api.main import app
        def readonly():
            connection=factory();connection.read_only=True;return connection
        with patch.object(dates,'get_independent_connection',readonly),TestClient(app) as client:
            response=client.get('/api/v1/calendar/events?domains=earnings&start_date=2026-05-01&end_date=2026-12-31')
            assert response.status_code==200
            payload=response.json();assert len(payload['events'])==34
            new=[e for e in payload['events'] if e['ticker'] not in ('NVDA','AMZN','INTC')]
            assert len(new)==27 and sum(e['publication_state']['code']=='published_complete' for e in new)==23
            for e in new:
                if e['ticker'] in ('ARM','QCOM','PANW','SNOW'):
                    assert e['reported_eps_actual'] is None and e['revenue_actual'] is None
                    assert e['publication_state']['code'] in ('scheduled','date_passed_unconfirmed')
                assert e['eps_consensus'] is None and e['revenue_consensus'] is None
            future=next(e for e in payload['events'] if e['ticker']=='NVDA' and e['fiscal_quarter']==3)
            assert future['reported_eps_actual'] is None and future['revenue_actual'] is None
            expected={'AAPL':('2.02','109417000000'),'PLTR':('0.41','1935464000'),'AMD':('1.38','11536000000'),'INTC':('-2.16','16128000000'),'AMZN':('5.75','200606000000'),'NVDA':('2.39','81615000000')}
            from decimal import Decimal
            for ticker,(eps,revenue) in expected.items():
                candidates=[e for e in payload['events'] if e['ticker']==ticker and e['previous_eps_actual']]
                event=min(candidates,key=lambda e:int(e['fiscal_quarter'])) if ticker=='NVDA' else candidates[-1]
                assert Decimal(event['previous_eps_actual']['actual'])==Decimal(eps)
                assert Decimal(event['previous_revenue_actual']['actual'])==Decimal(revenue)
            for event in payload['events']:
                if event['ticker'] in ('ARM','QCOM'):assert event['previous_eps_actual'] is None and event['previous_revenue_actual'] is None
                if event['ticker']=='CRWD':assert event['previous_eps_actual'] is None and event['previous_revenue_actual'] is not None
            for e in new:
                detail=client.get('/api/v1/earnings/events/'+e['event_id'])
                assert detail.status_code==200 and detail.json()['report_documents']==e['report_documents']
        assert f.table_snapshots(c)==receipt['after_snapshots'];c.rollback()
    result=dict(outcome='passed',plan_sha256=token,counts=receipt['counts'],after_snapshots=receipt['after_snapshots'],sql_rollback=True,idempotency=True,http_200=28,original_23_tables_unchanged=True)
    (directory/'test-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return plan,receipt


def main():
    if os.environ.get('DB_NAME')!='macrolens_history_activation_control':raise ValueError('Owned E2E activation control database required')
    params={k:os.environ[v] for k,v in [('host','DB_HOST'),('port','DB_PORT'),('user','DB_USER'),('password','DB_PASSWORD')]}
    container=os.environ['REPORT_TEST_CONTAINER']
    ci_service=(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('DB_NAME')=='macrolens_history_activation_control'
                and params['host']=='127.0.0.1' and params['user']=='macrolens_ci'
                and re.fullmatch(r'[0-9a-f]{64}',container))
    if params['host']!='127.0.0.1' or not (container.startswith('macrolens_reports_activation_') or ci_service):raise ValueError('Owned loopback service required')
    with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
        name=a.reports.PREFIX+uuid4().hex
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:
            factory=lambda:psycopg.connect(**params,dbname=name)
            with factory() as c:
                original_seed(c)
                a.current.reports.initialize_isolated(c)
                a.current.reports.import_records(c,a.current.seed())
            with factory() as c:ref=reference(c)
            with TemporaryDirectory(prefix='reports_activation_') as temp:verify(factory,admin,name,container,ref,Path(temp))
        finally:
            assert name.startswith(a.reports.PREFIX) and len(name)==len(a.reports.PREFIX)+32
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
    print('E2E Activation PASSED: actual backup/restore, frozen 23/45, approval/identity/schema/data/backup/restore/code gates, atomic DDL+seed rollback, idempotency, real read-only API, all original 23 tables preserved')


if __name__=='__main__':
    with no_publisher_http():main()
