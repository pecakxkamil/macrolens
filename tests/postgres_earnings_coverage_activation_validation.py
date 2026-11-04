"""E2C activation on owned PostgreSQL only, with real backup/restore."""
import copy
import json
import os
import re
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from app.database import activate_earnings as b, activate_earnings_financials as f
from app.database import activate_earnings_coverage as a
from app.database.init_db import SCHEMA_PATH
from app.database.init_earnings_db import initialize
from app import earnings as dates, earnings_financials as financials
from tests.postgres_earnings_financial_activation_validation import make_backup
from tests.postgres_http_guard import no_publisher_http


def reference(connection):
    old = a.rows(connection)
    result = {'e2b_catalog':b.catalog(connection,True)}
    with connection.transaction(force_rollback=True):
        a.coverage.initialize_isolated(connection)
        a.coverage.import_records(connection,a.seed())
        result['e2c_catalog'] = b.catalog(connection,True)
        new = a.rows(connection)
        result['additions'] = {t:sorted(set(new[t])-set(old[t])) for t in a.TABLES}
    # JSON types match plans loaded from disk.
    result=json.loads(json.dumps(result,default=str))
    a.check_reference(result)
    return result


def verify(factory, admin, name, container, ref, directory):
    backup=make_backup(factory,admin,name,container,directory)
    with factory() as c:
        c.read_only=True
        plan=a.prepare(c,backup['target'],backup,ref)
        assert c.info.transaction_status==psycopg.pq.TransactionStatus.IDLE
    token=b.digest(plan);target=plan['target_label']
    def rejected(plan_to_try, label, hash_value, exception=ValueError):
        with factory() as c:
            before=f.table_snapshots(c);c.rollback()
            try:a.apply(c,plan_to_try,label,hash_value)
            except exception:pass
            else:raise AssertionError('Invalid activation accepted')
            assert c.info.transaction_status==psycopg.pq.TransactionStatus.IDLE
            assert f.table_snapshots(c)==before
    rejected(plan,'wrong',token)
    rejected(plan,target,'wrong')
    for modify in ('artifact','backup','target','rows','schema'):
        bad=copy.deepcopy(plan)
        if modify=='artifact':bad['artifacts']['app/earnings_coverage.py']='wrong'
        elif modify=='backup':bad['backup']['sha256']='0'*64
        elif modify=='target':bad['target']['database_oid']+=1
        elif modify=='rows':bad['original_rows']['earnings_companies']=[]
        else:bad['macro_signature']='wrong'
        rejected(bad,target,b.digest(bad))
    # Real schema/data drift on this owned database must also refuse activation.
    with factory() as c:
        c.execute('ALTER TABLE earnings_companies ADD COLUMN foreign_probe integer')
    try:
        rejected(plan,target,token)
    finally:
        with factory() as c:c.execute('ALTER TABLE earnings_companies DROP COLUMN foreign_probe')
    with factory() as c:
        old=c.execute("SELECT name FROM earnings_companies WHERE cik='0001045810'").fetchone()[0]
        c.execute("UPDATE earnings_companies SET name='Synthetic drift probe' WHERE cik='0001045810'")
    try:
        rejected(plan,target,token)
    finally:
        with factory() as c:c.execute("UPDATE earnings_companies SET name=%s WHERE cik='0001045810'",(old,))
    with factory() as c:
        baseline=f.table_snapshots(c);c.rollback()
        real=a.coverage.import_records
        def broken(connection, records):
            real(connection,records)
            connection.execute('SELECT 1/0')
        with patch.object(a.coverage,'import_records',broken):
            try:a.apply(c,plan,target,token)
            except psycopg.errors.DivisionByZero:pass
            else:raise AssertionError('SQL error not raised')
        assert f.table_snapshots(c)==baseline
        assert a.timezone_check(c)==plan['ddl']['before'];c.rollback()
        receipt=a.apply(c,plan,target,token)
        assert receipt['outcome']=='created' and receipt['counts']==a.AFTER
        repeated=a.apply(c,plan,target,token)
        assert repeated['outcome']=='already_initialized'
        assert repeated['after_snapshots']==receipt['after_snapshots']
        assert a.rows(c)==a.expected_rows(plan,'e2c');c.rollback()
    (directory/'test-results.json').write_text(json.dumps({'outcome':'passed','plan_sha256':token,'counts':receipt['counts'],'after_snapshots':receipt['after_snapshots'],'ddl_seed_sql_rollback':True,'idempotency':True},indent=2),encoding='utf-8')
    return plan,receipt


def main():
    control=os.environ.get('DB_NAME')
    if control not in ('macrolens_coverage_activation_control','macrolens_ci_control'):
        raise ValueError('Owned E2C activation control database required')
    params={k:os.environ[v] for k,v in [('host','DB_HOST'),('port','DB_PORT'),('user','DB_USER'),('password','DB_PASSWORD')]}
    container=os.environ['COVERAGE_TEST_CONTAINER']
    ci_service=(os.environ.get('GITHUB_ACTIONS')=='true' and control=='macrolens_ci_control'
                and params['host']=='127.0.0.1' and params['user']=='macrolens_ci'
                and re.fullmatch(r'[0-9a-f]{64}',container))
    if not container.startswith('macrolens_coverage_activation_') and not ci_service:
        raise ValueError('Owned container required')
    with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
        name='macrolens_earnings_e2b_e2c_'+uuid4().hex
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:
            factory=lambda:psycopg.connect(**params,dbname=name)
            with factory() as c:
                c.execute(SCHEMA_PATH.read_text(encoding='utf-8'))
                c.execute("INSERT INTO series(series_id,name,category,frequency) VALUES('COVERAGE_PRESERVE','Synthetic','test','quarterly')")
                initialize(c);dates.import_records(c,json.loads(dates.DATA.read_text(encoding='utf-8')))
                financials.initialize_isolated(c);financials.import_records(c,f.seed())
            with factory() as c:ref=reference(c)
            with TemporaryDirectory(prefix='coverage_activation_') as temp:
                verify(factory,admin,name,container,ref,Path(temp))
        finally:
            assert name.startswith('macrolens_earnings_e2b_e2c_')
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
    print('E2C Activation PASSED: actual backup/restore, read-only prepare, approval/identity/artifact/data/schema gates, SQL rollback CHECK+seed, idempotency, original E2A/E2B and 13 macro tables preserved')


if __name__=='__main__':
    with no_publisher_http():main()
