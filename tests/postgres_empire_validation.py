"""Explicit PostgreSQL integration check, separate from the offline pytest suite.

Run: python tests/postgres_empire_validation.py --baseline <pre-Empire-commit>
Requires local DB credentials and CREATE DATABASE permission. Creates and drops
only two uniquely named test databases. Never initializes the configured user DB.
Provider responses are synthetic; no publisher requests are made.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from app.database.connection import get_independent_connection
from app.database import init_db
from app import source_checks
from app.ingestion import sync_empire_state as sync
import test_empire_state as fixtures


def rows(connection, query, params=()):
    return connection.execute(query, params or None).fetchall()


def snapshot(connection):
    return rows(connection, "SELECT row_to_json(o)::text FROM observation_vintages o ORDER BY id")


def initialize(factory):
    with patch.object(init_db, 'get_connection', factory):
        assert init_db.main() == 0


def schema_checks(factory, old_schema=None):
    if old_schema:
        with factory() as connection:
            connection.execute(old_schema)
            connection.execute("INSERT INTO series(series_id,name,category,frequency) VALUES ('TEST_FRED','Synthetic','test','monthly')")
            connection.execute("INSERT INTO observation_vintages(series_id,observation_date,vintage_date,value,source) VALUES ('TEST_FRED','2026-01-01','2026-02-01',1,'fred_snapshot'),('TEST_FRED','2026-01-01','2026-02-02',2,'alfred')")
        with factory() as connection:
            before = snapshot(connection)
    initialize(factory)
    initialize(factory)
    with factory() as connection:
        if old_schema:
            # Added nullable columns are the only shape change; all old values persist.
            after = [json.loads(row[0]) for row in snapshot(connection)]
            for row in after:
                assert row.pop('source_document_id') is None
                assert row.pop('publication_document_id') is None
            assert after == [json.loads(row[0]) for row in before]
        columns = rows(connection, "SELECT column_name,is_nullable,data_type FROM information_schema.columns WHERE table_name='observation_vintages' AND column_name LIKE '%document_id'")
        assert sorted(columns) == [('publication_document_id','YES','uuid'),('source_document_id','YES','uuid')]
        foreign_keys = rows(connection, "SELECT confupdtype,confdeltype FROM pg_constraint WHERE conrelid='observation_vintages'::regclass AND confrelid='publisher_documents'::regclass")
        assert foreign_keys == [('a','a'),('a','a')]
        indexes = {r[0] for r in rows(connection, "SELECT indexname FROM pg_indexes WHERE schemaname='public'")}
        assert {'publisher_documents_source_retrieved_idx','observation_vintages_source_document_idx','observation_vintages_publication_document_idx'} <= indexes
        connection.execute('SET LOCAL enable_seqscan=off')
        plan = rows(connection, "EXPLAIN SELECT id FROM publisher_documents WHERE source=%s ORDER BY retrieved_at,id", (sync.SOURCE,))
        assert 'publisher_documents_source_retrieved_idx' in str(plan)
        try:
            with connection.transaction():
                connection.execute("UPDATE observation_vintages SET source_document_id=%s", (uuid4(),))
        except psycopg.errors.ForeignKeyViolation:
            pass
        else:
            assert not old_schema, 'Dangling FK accepted'


def importer_checks(factory):
    with TemporaryDirectory(prefix='macrolens-empire-raw-') as raw, patch.object(source_checks, 'get_connection', factory):
        path = Path(raw)
        with factory() as connection:
            fixtures.run(path, connection)
            before = snapshot(connection)
            documents = rows(connection, 'SELECT id FROM publisher_documents')
            fixtures.run(path, connection)
            assert before == snapshot(connection)
            assert documents == rows(connection, 'SELECT id FROM publisher_documents')
            # A new raw version with unchanged values keeps observation timestamps.
            fixtures.run(path, connection, content=fixtures.csv_data()+b'\n', now=fixtures.NOW+fixtures.timedelta(minutes=1))
            assert before == snapshot(connection)
            assert len(rows(connection, "SELECT id FROM publisher_documents WHERE kind='csv'")) == 2
            for minute, value in [(2,'7.8'),(3,'7.9')]:
                fixtures.run(path, connection, content=fixtures.csv_data(('20.6',value,'25.5')), now=fixtures.NOW+fixtures.timedelta(minutes=minute))
            assert sync.load_observations(connection)['2026-09-01']['value'] == 7.9
            docs = sync.receipts(connection)
            revisions = [r for d in docs for r in d['metadata'].get('revisions',[])]
            assert [(r['before'],r['after']) for r in revisions] == [(7.6,7.8),(7.8,7.9)]
            assert len(rows(connection, "SELECT id FROM observation_vintages WHERE series_id=%s", (sync.SID,))) == 3
            for doc in docs:
                content = Path(doc['raw_path']).read_bytes()
                assert hashlib.sha256(content).hexdigest() == doc['raw_hash']
                if doc['kind'] == 'csv':
                    assert sync.parse_csv(content)['2026-09-01'] in (7.6,7.8,7.9)
            # Known stale version cannot replace the last accepted version.
            _, result, _ = fixtures.run(path, connection, now=fixtures.NOW+fixtures.timedelta(minutes=4))
            assert not result['csv_validated']
            assert sync.load_observations(connection)['2026-09-01']['value'] == 7.9
            # Independent failures preserve observations, while attempts show partial.
            before = snapshot(connection)
            import httpx
            for bad_url in (sync.CSV, '2026-10.pdf'):
                def handle(request):
                    url=str(request.url)
                    body=fixtures.html().encode() if url==sync.HOME else fixtures.csv_data(('20.6','7.9','25.5')) if url==sync.CSV else b'bad pdf'
                    if '2026-10.pdf' in url and bad_url==sync.CSV:
                        body=fixtures.pdf('2026-10-01',25.5,7.6)
                    return httpx.Response(503 if bad_url in url else 200, content=body, request=request)
                with httpx.Client(transport=httpx.MockTransport(handle)) as client:
                    result=sync.sync_source(client,connection,fixtures.NOW,path,clock=lambda:fixtures.NOW)
                assert result['status']=='partial' and snapshot(connection)==before
            linked=rows(connection, 'SELECT source_document_id FROM observation_vintages WHERE source_document_id IS NOT NULL LIMIT 1')[0][0]
            for command in ('DELETE FROM publisher_documents WHERE id=%s','UPDATE publisher_documents SET id=gen_random_uuid() WHERE id=%s'):
                try:
                    with connection.transaction(): connection.execute(command,(linked,))
                except psycopg.errors.ForeignKeyViolation: pass
                else: raise AssertionError('Referenced document changed/deleted')
        # Actual SQL error after writing receipts must roll the entire import back.
        with factory() as connection:
            connection.execute("CREATE FUNCTION fail_empire_write() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RAISE EXCEPTION 'Synthetic import failure'; END$$")
            connection.execute("CREATE TRIGGER fail_empire BEFORE INSERT OR UPDATE ON observation_vintages FOR EACH ROW WHEN (NEW.series_id='NYFED_EMPIRE_GACDISA') EXECUTE FUNCTION fail_empire_write()")
        with factory() as connection:
            before = snapshot(connection)
            doc_before = rows(connection, 'SELECT id FROM publisher_documents ORDER BY id')
            connection.commit()
            try:
                fixtures.run(path,connection,content=fixtures.csv_data(('20.6','8.0','25.5')),now=fixtures.NOW+fixtures.timedelta(minutes=5))
            except psycopg.Error: pass
            else: raise AssertionError('Synthetic SQL failure not raised')
            assert before == snapshot(connection)
            assert doc_before == rows(connection, 'SELECT id FROM publisher_documents ORDER BY id')
            assert rows(connection, "SELECT status FROM source_check_runs ORDER BY attempted_at DESC LIMIT 1")[0][0] == 'error'
            assert rows(connection, 'SELECT count(*) FROM observation_vintages o LEFT JOIN publisher_documents d ON d.id=o.source_document_id WHERE o.source_document_id IS NOT NULL AND d.id IS NULL')[0][0] == 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',required=True)
    args=parser.parse_args()
    baseline=subprocess.check_output(['git','show',args.baseline+':app/database/schema.sql'],text=True,encoding='utf-8')
    original=get_independent_connection()
    parameters=original.info.get_parameters()
    parameters['password']=os.environ['DB_PASSWORD']
    user_database=parameters['dbname']
    original.close()
    parameters['dbname']='postgres'
    names=['macrolens_empire_test_'+uuid4().hex for _ in range(2)]
    with psycopg.connect(**parameters,autocommit=True) as admin:
        created=[]
        try:
            for name in names:
                assert name.startswith('macrolens_empire_test_') and name!=user_database
                admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
                created.append(name)
            for index,name in enumerate(names):
                def factory(): return psycopg.connect(**{**parameters,'dbname':name})
                schema_checks(factory,baseline if index else None)
                importer_checks(factory)
                print(('UPGRADE' if index else 'FRESH')+': schema twice, nullable FKs, indexes, FRED/ALFRED preservation, importer revisions/RAW, HTTP failures and SQL rollback: PASSED')
        finally:
            for name in created:
                assert name in names and name.startswith('macrolens_empire_test_') and name!=user_database
                admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
    print('Only generated test databases removed; configured user database untouched.')


if __name__=='__main__':
    main()
