"""Explicit isolated PostgreSQL FT900 check; HTTP fixtures remain offline.

Run: python tests/postgres_ft900_validation.py
Creates/removes only its own uniquely named test database, never the user DB.
"""
import hashlib
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
from app.database.connection import get_independent_connection
from app.database import init_db
from app import source_checks
from app.ingestion import sync_ft900 as source
from tests.test_ft900 import run,BASE,bea,workbook,NOW,timedelta


def state(c):
    return c.execute('SELECT row_to_json(o)::text FROM observation_vintages o ORDER BY id').fetchall()


def verify(factory):
    with patch.object(init_db,'get_connection',factory):assert init_db.main()==0
    with factory() as c:
        c.execute("INSERT INTO series(series_id,name,category,frequency) VALUES ('PRESERVED','Synthetic legacy','test','monthly')")
        c.execute("INSERT INTO observation_vintages(series_id,observation_date,vintage_date,value,source) VALUES ('PRESERVED','2026-01-01','2026-02-01',1,'fred_snapshot'),('PRESERVED','2026-01-01','2026-02-02',2,'alfred')")
    with TemporaryDirectory(prefix='macrolens-ft900-raw-') as raw,patch.object(source_checks,'get_connection',factory):
        path=Path(raw)
        with factory() as c:
            legacy=c.execute("SELECT row_to_json(o)::text FROM observation_vintages o WHERE series_id='PRESERVED' ORDER BY id").fetchall()
            run(path,c);first=state(c);docs=source.receipts(c)
            run(path,c);assert first==state(c) and docs==source.receipts(c)
            # Old report receipts now carry real UUID/datetime PostgreSQL types.
            reduced=re.sub(r'<tr><td>(August 4|September 3).*?</tr>','',bea())
            run(path,c,bea_body=reduced,now=NOW+timedelta(minutes=1))
            assert first==state(c)
            versions=[]
            for minute,value in [(2,'-93000'),(3,'-94000')]:
                values=dict(BASE);values['2026-07-01']=(value,str(403550+int(value)),'403550')
                run(path,c,book=workbook(values),bea_body=reduced,now=NOW+timedelta(minutes=minute))
            for d in source.receipts(c):
                content=Path(d['raw_path']).read_bytes()
                assert hashlib.sha256(content).hexdigest()==d['raw_hash']
                if d['kind']=='xlsx':versions.append(source.parse_xlsx(content)['values']['2026-07-01']['balance'])
            assert versions==['-92826','-93000','-94000']
            assert legacy==c.execute("SELECT row_to_json(o)::text FROM observation_vintages o WHERE series_id='PRESERVED' ORDER BY id").fetchall()
            c.execute("CREATE FUNCTION ft900_fail() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RAISE EXCEPTION 'Synthetic FT900 failure'; END$$")
            c.execute("CREATE TRIGGER ft900_fail BEFORE INSERT OR UPDATE ON observation_vintages FOR EACH ROW WHEN (NEW.series_id='CENSUS_FT900_TOTAL') EXECUTE FUNCTION ft900_fail()")
        with factory() as c:
            before=state(c);docs=source.receipts(c);c.commit()
            values=dict(BASE);values['2026-07-01']=('-95000','308550','403550')
            try:run(path,c,book=workbook(values),bea_body=reduced,now=NOW+timedelta(minutes=4))
            except psycopg.Error:pass
            else:raise AssertionError('SQL trigger did not fail')
            assert before==state(c) and docs==source.receipts(c)
            assert c.execute('SELECT status FROM source_check_runs ORDER BY attempted_at DESC LIMIT 1').fetchone()[0]=='error'
    print('FT900 real PostgreSQL: idempotence, UUID provenance, preserved FRED/ALFRED, same-day revisions/RAW, atomic SQL rollback: PASSED')


def main():
    original=get_independent_connection();params=original.info.get_parameters();user_db=params['dbname'];original.close()
    params.update(dbname='postgres',password=os.environ['DB_PASSWORD'])
    name='macrolens_ft900_test_'+uuid4().hex
    assert name.startswith('macrolens_ft900_test_') and name!=user_db
    with psycopg.connect(**params,autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:verify(lambda:psycopg.connect(**{**params,'dbname':name}))
        finally:
            assert name.startswith('macrolens_ft900_test_') and name!=user_db
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
    print('Generated test database removed; no user database schema/data changed.')


if __name__=='__main__':
    from tests.postgres_http_guard import no_publisher_http
    with no_publisher_http():
        main()
