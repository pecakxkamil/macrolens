"""Activation rehearsal on an owned database only, never the configured user DB."""
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from app import earnings
from app.database import activate_earnings as a
from app.database.init_db import SCHEMA_PATH
from app.database.init_earnings_db import initialize
from tests.postgres_http_guard import no_publisher_http


def verify(connection, directory):
    with connection.transaction():
        connection.execute(SCHEMA_PATH.read_text(encoding='utf-8'))
        connection.execute("INSERT INTO series(series_id,name,category,frequency) VALUES('ACTIVATION_SENTINEL','Synthetic','test','monthly')")
        connection.execute("INSERT INTO observation_vintages(series_id,observation_date,vintage_date,value,source) VALUES('ACTIVATION_SENTINEL','2026-01-01','2026-02-01',1,'fred_snapshot'),('ACTIVATION_SENTINEL','2026-01-01','2026-02-02',2,'alfred')")
    try:initialize(connection)
    except ValueError:pass
    else:raise AssertionError('The existing isolated-only guard must remain intact')
    before_rows=connection.execute('SELECT row_to_json(o)::text FROM observation_vintages o ORDER BY id').fetchall()
    initial=a.inspect(connection)
    # Compile the exact DDL in an owned transaction, then roll it all back.
    with connection.transaction(force_rollback=True):
        connection.execute('SET LOCAL search_path TO public,pg_catalog')
        connection.execute(a.SCHEMA.read_text(encoding='utf-8'))
        signature=a.digest(a.catalog(connection,True))
    assert not a.inspect(connection)['existing_objects']
    fake=Path(directory)/'synthetic-backup-for-gate-tests.dump'
    fake.write_bytes(b'PGDMPsynthetic-rehearsal-only-not-a-user-backup')
    backup=dict(target=initial['target'],path=str(fake),sha256=a.file_hash(fake),bytes=fake.stat().st_size,format='pg_dump_custom',toc_verified=True)
    plan=a.prepare(connection,backup,signature);token=a.digest(plan)
    assert a.inspect(connection)['read_only']=='on' and not a.inspect(connection)['existing_objects']
    for target,approval in [('wrong',token),(plan['target_label'],'wrong')]:
        try:a.apply(connection,plan,target,approval)
        except ValueError:pass
        else:raise AssertionError('Expected approval gate rejection')
    original=earnings.import_records
    def fail_after_seed(c,rows):
        original(c,rows)
        c.execute('SELECT 1/0')
    with patch.object(earnings,'import_records',fail_after_seed):
        try:a.apply(connection,plan,plan['target_label'],token)
        except psycopg.Error:pass
        else:raise AssertionError('Expected real SQL failure')
    assert not a.inspect(connection)['existing_objects']
    assert a.inspect(connection)['macro_schema_signature']==initial['macro_schema_signature']
    assert connection.execute('SELECT row_to_json(o)::text FROM observation_vintages o ORDER BY id').fetchall()==before_rows
    first=a.apply(connection,plan,plan['target_label'],token)
    assert first['outcome']=='created'
    assert first['counts']==dict(zip(a.TABLES,[3,3,6,6,5,12]))
    captured=a.digest(earnings.load_events(connection))
    second=a.apply(connection,plan,plan['target_label'],token)
    assert second['outcome']=='already_initialized' and second['counts']==first['counts']
    assert captured==a.digest(earnings.load_events(connection))
    assert connection.execute('SELECT row_to_json(o)::text FROM observation_vintages o ORDER BY id').fetchall()==before_rows
    assert a.inspect(connection)['macro_schema_signature']==initial['macro_schema_signature']
    # Verify the explicit post-commit rollback plan, only in this owned test DB.
    connection.execute((a.ROOT/'app/database/earnings_activation_rollback.sql').read_text(encoding='utf-8'))
    assert not a.inspect(connection)['existing_objects']
    assert a.inspect(connection)['macro_schema_signature']==initial['macro_schema_signature']
    assert connection.execute('SELECT row_to_json(o)::text FROM observation_vintages o ORDER BY id').fetchall()==before_rows
    return signature


def main():
    if os.environ.get('DB_NAME') not in ('macrolens_activation_control','macrolens_ci_control'):
        raise ValueError('Use only the explicit owned activation test service')
    params=dict(host=os.environ['DB_HOST'],port=os.environ['DB_PORT'],user=os.environ['DB_USER'],password=os.environ['DB_PASSWORD'])
    name='macrolens_activation_test_'+uuid4().hex
    with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:
            with psycopg.connect(**params,dbname=name,autocommit=True) as connection,TemporaryDirectory(prefix='earnings-activation-') as temp:
                signature=verify(connection,temp)
        finally:
            assert name.startswith('macrolens_activation_test_')
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
        assert not admin.execute('SELECT 1 FROM pg_database WHERE datname=%s',(name,)).fetchone()
    if len(sys.argv)>1:
        Path(sys.argv[1]).write_text(json.dumps({'earnings_schema_signature':signature,'validated':'PostgreSQL 17 owned synthetic rehearsal; DDL+seed rollback, idempotence, explicit recovery and macro preservation passed'},indent=2),encoding='utf-8')
    print('Activation PostgreSQL: read-only prepare, exact approval gates, atomic DDL+seed rollback, repeat/no duplicate, unchanged macro and explicit recovery PASSED; owned database removed.')


if __name__=='__main__':
    with no_publisher_http():main()
