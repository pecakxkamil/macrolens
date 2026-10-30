"""Explicit real PostgreSQL check in an owned disposable database; HTTP is synthetic.

Run: python tests/postgres_bea_validation.py
"""
import hashlib
import os
import sys
from datetime import datetime,timezone,timedelta
from functools import partial
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
from app.analytics.bea_direct import load_state,select
from tests.test_bea_direct import source,run,gdp,pio,NOW,PROOF,measure

# HTTP capture uses the real clock. Keep the synthetic projection after all
# captures so this explicit validation remains runnable after its fixture date.
NOW=max(NOW,datetime.now(timezone.utc)+timedelta(days=1))
run=partial(run,now=NOW)

def state(c):return c.execute('SELECT row_to_json(o)::text FROM observation_vintages o ORDER BY id').fetchall()

def verify(factory):
    with patch.object(init_db,'get_connection',factory):assert init_db.main()==0
    with factory() as c:
        c.execute("INSERT INTO series(series_id,name,category,frequency) VALUES ('PRESERVED','Legacy synthetic','test','monthly')")
        c.execute("INSERT INTO observation_vintages(series_id,observation_date,vintage_date,value,source) VALUES ('PRESERVED','2026-01-01','2026-02-01',1,'fred_snapshot'),('PRESERVED','2026-01-01','2026-02-02',2,'alfred')")
    with TemporaryDirectory(prefix='macrolens-bea-raw-') as raw,patch.object(source_checks,'get_connection',factory):
        with factory() as c:
            legacy=state(c);assert run(raw,c)['status']=='success'
            first=state(c);docs=source.receipts(c);assert len(first)==9 and len(docs)==2
            run(raw,c);assert first==state(c) and docs==source.receipts(c)
            assert select(measure(),PROOF,load_state(c),NOW)['actual']==1.2
            for value in ('1.3','1.4'):
                assert run(raw,c,gdp_body=gdp(value))['status']=='success'
            transitions=[d['metadata']['revisions'] for d in source.receipts(c) if d['metadata']['release_id']==53]
            assert transitions[1][0]['before']['value']=='1.2' and transitions[2][0]['after']['value']=='1.4'
            # A previously unseen body has no provider sequence marker. Capture
            # ordering proves retrieval order only; identical rates stay 1.4.
            unseen=gdp('1.4')+'<!-- synthetic unsequenced representation -->'
            assert run(raw,c,gdp_body=unseen)['status']=='success'
            newest=source.receipts(c)[-1]
            assert newest['metadata']['readings'][0]['value']=='1.4' and newest['metadata']['revisions']==[]
            assert select(measure(),PROOF,load_state(c),NOW)['actual']==1.4
            for d in source.receipts(c):assert hashlib.sha256(Path(d['raw_path']).read_bytes()).hexdigest()==d['raw_hash']
            before=state(c);docs=source.receipts(c)
            assert run(raw,c)['status']=='partial' and state(c)==before
            assert run(raw,c,status=503)['status']=='partial' and state(c)==before
            assert run(raw,c,gdp_body='<h1>Wrong report</h1>',pio_body=pio().replace('September 2026','August 2026'))['status']=='partial'
            assert state(c)==before
            assert legacy==c.execute("SELECT row_to_json(o)::text FROM observation_vintages o WHERE series_id='PRESERVED' ORDER BY id").fetchall()
            c.execute("CREATE FUNCTION bea_fail() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RAISE EXCEPTION 'Synthetic BEA failure'; END$$")
            c.execute("CREATE TRIGGER bea_fail BEFORE INSERT OR UPDATE ON observation_vintages FOR EACH ROW WHEN (NEW.source='bea_official') EXECUTE FUNCTION bea_fail()")
        with factory() as c:
            before=state(c);docs=source.receipts(c);c.commit()
            try:run(raw,c,gdp_body=gdp('1.5'))
            except psycopg.Error:pass
            else:raise AssertionError('Expected SQL rollback')
            assert state(c)==before and source.receipts(c)==docs
            assert c.execute('SELECT status FROM source_check_runs ORDER BY attempted_at DESC LIMIT 1').fetchone()[0]=='error'
    print('BEA PostgreSQL: idempotence, same-day revisions, RAW recovery, SQL bindings, FRED/ALFRED preservation, HTTP/parser failures and atomic rollback PASSED')

def main():
    original=get_independent_connection();params=original.info.get_parameters();user_db=params['dbname'];original.close()
    params.update(dbname='postgres',password=os.environ['DB_PASSWORD'])
    name='macrolens_bea_test_'+uuid4().hex
    assert name.startswith('macrolens_bea_test_') and name!=user_db
    with psycopg.connect(**params,autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:verify(lambda:psycopg.connect(**{**params,'dbname':name}))
        finally:
            assert name.startswith('macrolens_bea_test_') and name!=user_db
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
    print('Only the owned test database was removed; user database unchanged.')

if __name__=='__main__':main()
