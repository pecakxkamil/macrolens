"""E2B Activation on owned PostgreSQL 17 only; real backup/restore, no HTTP."""
import copy
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from app.database import activate_earnings as b,activate_earnings_financials as a
from app.database.init_db import SCHEMA_PATH
from app.database.init_earnings_db import initialize
from app import earnings as e,earnings_financials as f
from tests.postgres_http_guard import no_publisher_http


def rejected(c,fn,expected=(ValueError,psycopg.Error)):
    try:fn()
    except expected:
        assert c.info.transaction_status==psycopg.pq.TransactionStatus.IDLE
        return
    raise AssertionError('Invalid operation accepted')


def own_create(admin):
    name='macrolens_earnings_e2b_'+uuid4().hex
    admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)));return name


def own_drop(admin,name):
    assert name.startswith('macrolens_earnings_e2b_') and len(name)==55
    admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
    assert not admin.execute('SELECT 1 FROM pg_database WHERE datname=%s',(name,)).fetchone()


def make_backup(factory,admin,name,container,directory):
    path=directory/'actual-owned-backup.dump'
    with factory() as c:
        c.read_only=True
        with c.transaction():
            c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            target=b.target_identity(c);source=a.table_snapshots(c)
            earnings=b.digest(b.catalog(c,True));macro=b.digest(b.catalog(c,False))
            snapshot=c.execute('SELECT pg_export_snapshot()').fetchone()[0]
            with path.open('xb') as stream:
                p=subprocess.run(['docker','exec','--env','PGOPTIONS=-c default_transaction_read_only=on',container,'pg_dump','-U',target['user'],'-d',name,'--format=custom','--no-owner','--no-acl','--snapshot='+snapshot],stdout=stream,stderr=subprocess.PIPE)
            assert p.returncode==0,p.stderr
    restore_name=own_create(admin)
    try:
        with path.open('rb') as stream:
            p=subprocess.run(['docker','exec','-i',container,'pg_restore','-U',target['user'],'-d',restore_name,'--exit-on-error','--single-transaction','--no-owner','--no-acl'],stdin=stream,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert p.returncode==0,p.stderr
        params=dict(host=admin.info.host,port=admin.info.port,user=admin.info.user)
        with psycopg.connect(host=params['host'],port=params['port'],user=params['user'],password=os.environ['DB_PASSWORD'],dbname=restore_name) as c:
            c.read_only=True
            with c.transaction():
                c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                restored=a.table_snapshots(c)
                match=b.digest(b.catalog(c,True))==earnings and b.digest(b.catalog(c,False))==macro
                invalid=c.execute("SELECT count(*) FROM pg_constraint k JOIN pg_namespace n ON n.oid=k.connamespace WHERE n.nspname='public' AND NOT convalidated").fetchone()[0]
        assert source==restored and match and invalid==0
    finally:own_drop(admin,restore_name)
    receipt=directory/'actual-restore-proof.json'
    receipt.write_text(json.dumps({'source_target':target,'backup_sha256':b.file_hash(path),
        'source_snapshots':source,'restored_snapshots':restored,'source_earnings_signature':earnings,
        'source_macro_signature':macro,'restore_exit_code':0,'unvalidated_constraints':invalid,
        'schema_match':match,'owned_database_removed':True},default=str),encoding='utf-8')
    toc=subprocess.run(['docker','exec','-i',container,'pg_restore','--list'],input=path.read_bytes(),capture_output=True)
    assert toc.returncode==0
    return dict(target=target,path=str(path),bytes=path.stat().st_size,sha256=b.file_hash(path),
        format='pg_dump_custom',toc_verified=True,source_snapshots=source,
        restore_validation={'path':str(receipt),'sha256':b.file_hash(receipt)})


def verify(factory,admin,name,container,reference,upgrade):
    with factory() as c:
        if upgrade:
            c.execute(SCHEMA_PATH.read_text(encoding='utf-8'))
            c.execute("INSERT INTO series(series_id,name,category,frequency) VALUES('ACTIVATION_PRESERVE','Synthetic','test','quarterly')")
            c.execute("INSERT INTO observation_vintages(series_id,observation_date,vintage_date,value,source) VALUES('ACTIVATION_PRESERVE','2026-01-01','2026-02-01',1,'fred_snapshot'),('ACTIVATION_PRESERVE','2026-01-01','2026-03-01',2,'alfred')")
        initialize(c);e.import_records(c,json.loads(e.DATA.read_text(encoding='utf-8')))
    with TemporaryDirectory(prefix='macrolens_financial_activation_') as temp:
        backup=make_backup(factory,admin,name,container,Path(temp))
        with factory() as c:
            c.read_only=True
            plan=a.prepare(c,b.target_label(backup['target']),backup,reference)
            assert plan['preflight']['read_only']=='on'
        token=b.digest(plan);label=plan['target_label']
        other=own_create(admin)
        try:
            params=dict(host=admin.info.host,port=admin.info.port,user=admin.info.user)
            with psycopg.connect(host=params['host'],port=params['port'],user=params['user'],password=os.environ['DB_PASSWORD'],dbname=other) as wrong:
                rejected(wrong,lambda:a.apply(wrong,plan,label,token))
                assert not b.inspect(wrong)['existing_objects']
        finally:own_drop(admin,other)
        with factory() as c:
            rejected(c,lambda:a.apply(c,plan,'wrong',token))
            rejected(c,lambda:a.apply(c,plan,label,'wrong'))
            bad=copy.deepcopy(plan);bad['artifacts']['app/earnings_financials.py']='changed'
            rejected(c,lambda:a.apply(c,bad,label,b.digest(bad)))
            bad=copy.deepcopy(plan);bad['backup']['sha256']='0'*64
            rejected(c,lambda:a.apply(c,bad,label,b.digest(bad)))
            # Different live target/cluster/OID is rejected before DDL.
            live=b.inspect(c);live['target']={**live['target'],'database_oid':live['target']['database_oid']+1}
            with patch.object(b,'inspect',return_value=live):
                rejected(c,lambda:a.apply(c,plan,label,token))
            # Refuse changed macro state, with the deliberate test change rolled back.
            if upgrade:
                c.execute("UPDATE observation_vintages SET value=999 WHERE series_id='ACTIVATION_PRESERVE'");c.commit()
                rejected(c,lambda:a.apply(c,plan,label,token))
                c.execute("UPDATE observation_vintages SET value=CASE source WHEN 'alfred' THEN 2 ELSE 1 END WHERE series_id='ACTIVATION_PRESERVE'");c.commit()
            # Wrong financial facts fail validation. No E2A or macro writes survive.
            for mutate in [lambda r:r.update(cik='0000000000'),lambda r:r.update(period_end='2027-01-01'),lambda r:r['observations'][0].update(source_unit='shares'),lambda r:r['observations'][1].update(methodology='non_gaap')]:
                row=a.seed()[0];mutate(row)
                rejected(c,lambda:f.import_records(c,[row]))
            original_import=f.import_records
            def fail_after_seed(connection,rows):
                original_import(connection,rows[:1]);connection.execute('SELECT 1/0')
            with patch.object(f,'import_records',side_effect=fail_after_seed):
                rejected(c,lambda:a.apply(c,plan,label,token))
            assert b.inspect(c)['earnings_schema_signature']==reference['e2a']['earnings_schema_signature']
            with c.transaction():
                c.execute('SET TRANSACTION READ ONLY')
                assert a.table_snapshots(c)==plan['source_snapshots']
            # Actual schema drift must refuse, without repairing it.
            c.execute('CREATE TABLE earnings_financial_documents (unrelated INT)');c.commit()
            rejected(c,lambda:a.apply(c,plan,label,token))
            c.execute('DROP TABLE earnings_financial_documents');c.commit()
            receipt=a.apply(c,plan,label,token)
            assert receipt['outcome']=='created' and receipt['counts']==a.EXPECTED_AFTER
            repeated=a.apply(c,plan,label,token)
            assert repeated['outcome']=='already_initialized' and repeated['after_snapshots']==receipt['after_snapshots']
            # A normal GET must remain read-only and cannot import or perform HTTP.
            original_factory=e.get_independent_connection;e.get_independent_connection=factory
            try:
                from fastapi.testclient import TestClient
                from app.api.main import app
                with TestClient(app) as client:
                    result=client.get('/api/v1/calendar/events?domains=earnings&start_date=2026-01-01&end_date=2026-12-31')
                    assert result.status_code==200
                    payload=result.json()
                    assert len(payload['events'])==7 and len(payload['undated'])==3
                    future=next(r for r in payload['events'] if r['ticker']=='NVDA' and r['fiscal_quarter']==3)
                    assert future['revenue_actual'] is None and future['gaap_diluted_eps_actual'] is None
            finally:e.get_independent_connection=original_factory
            with c.transaction():
                c.execute('SET TRANSACTION READ ONLY')
                assert a.table_snapshots(c)==receipt['after_snapshots']
        print('E2B Activation', 'upgrade' if upgrade else 'fresh', 'PASSED: real restore, approval/target/hash/backup gates, data validation, schema drift, DDL+seed rollback, repeat, read-only API, E2A/macro preservation')


def main():
    control=os.environ.get('DB_NAME')
    if control not in ('macrolens_financial_control','macrolens_ci_control'):raise ValueError('Explicit isolated control database required')
    params={k:os.environ[v] for k,v in [('host','DB_HOST'),('port','DB_PORT'),('user','DB_USER'),('password','DB_PASSWORD')]}
    container=os.environ['FINANCIAL_TEST_CONTAINER']
    ci_service=(os.environ.get('GITHUB_ACTIONS')=='true' and control=='macrolens_ci_control'
                and params['host']=='127.0.0.1' and params['user']=='macrolens_ci'
                and re.fullmatch(r'[0-9a-f]{64}',container))
    if not container.startswith('macrolens_financial_') and not ci_service:raise ValueError('Owned test container required')
    with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
        ref_name=own_create(admin)
        try:
            with psycopg.connect(**params,dbname=ref_name) as c:
                initialize(c);e.import_records(c,json.loads(e.DATA.read_text(encoding='utf-8')))
            with psycopg.connect(**params,dbname=ref_name) as c:e2a=b.inspect(c)
            with psycopg.connect(**params,dbname=ref_name) as c:
                f.initialize_isolated(c);f.import_records(c,a.seed())
            with psycopg.connect(**params,dbname=ref_name) as c:e2b=b.inspect(c)
            reference={'e2a':e2a,'e2b':e2b}
        finally:own_drop(admin,ref_name)
        for upgrade in (False,True):
            name=own_create(admin)
            try:verify(lambda:psycopg.connect(**params,dbname=name),admin,name,container,reference,upgrade)
            finally:own_drop(admin,name)
    print('All owned activation test databases removed; no developer database writes')


if __name__=='__main__':
    with no_publisher_http():main()
