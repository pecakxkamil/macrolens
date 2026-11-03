"""E2B PostgreSQL checks. Owned databases only, no publisher HTTP."""
import copy
import json
import os
import sys
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from app import earnings as e, earnings_financials as f
from app.database.init_earnings_db import initialize
from app.database.init_db import SCHEMA_PATH
from app.database.activate_earnings import catalog,digest
from tests.postgres_http_guard import no_publisher_http

TABLES=['earnings_companies','earnings_company_aliases','earnings_periods','earnings_events','earnings_source_evidence','earnings_date_confirmations']

def snapshot(c,tables):
    return {t:c.execute(sql.SQL('SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text').format(sql.Identifier(t))).fetchall() for t in tables}

def rejects(c,fn):
    try:
        with c.transaction(): fn()
    except (ValueError,psycopg.Error): return
    raise AssertionError('Invalid financial operation accepted')

def verify(factory,upgrade):
    records=json.loads(f.DATA.read_text(encoding='utf-8'))
    with factory() as c:
        if upgrade:
            c.execute(SCHEMA_PATH.read_text(encoding='utf-8'))
            c.execute("INSERT INTO series(series_id,name,category,frequency) VALUES('E2B_PRESERVE','Synthetic','test','quarterly')")
            c.execute("INSERT INTO observation_vintages(series_id,observation_date,vintage_date,value,source) VALUES('E2B_PRESERVE','2026-01-01','2026-02-01',1,'fred_snapshot'),('E2B_PRESERVE','2026-01-01','2026-03-01',2,'alfred')")
        initialize(c);e.import_records(c,json.loads(e.DATA.read_text(encoding='utf-8')))
        c.commit()
        from app.database.prepare_earnings_financials import prepare
        from app.database.activate_earnings import target_identity,target_label
        with factory() as reader:
            target=target_label(target_identity(reader));reader.rollback()
            plan=prepare(reader,target)
            assert not plan['ready_for_apply'] and plan['preflight']['read_only']=='on'
            assert plan['new_events']==4 and plan['manual_documents']==6 and plan['manual_observations']==12
            rejects(reader,lambda:prepare(reader,'wrong:5432/database'))
        original=snapshot(c,TABLES)
        macro=digest(catalog(c,False));macro_data=snapshot(c,['series','observation_vintages']) if upgrade else {}
        before=e.load_events(c)
        assert all(r['financial_store_status']=='not_activated' for r in before)
        # A deployed E2B reader must keep an E2A-only store available via HTTP.
        from fastapi.testclient import TestClient
        from app.api.main import app
        prior_factory=e.get_independent_connection
        e.get_independent_connection=factory
        try:
            with TestClient(app) as client:
                response=client.get('/api/v1/calendar/events?domains=earnings&start_date=2026-11-17&end_date=2026-11-17')
                assert response.status_code==200
                payload=response.json()
                assert len(payload['events'])==1 and len(payload['undated'])==3
                assert all(r['financial_store_status']=='not_activated' and r['revenue_actual'] is None
                           and r['gaap_diluted_eps_actual'] is None for r in payload['events']+payload['undated'])
                detail=client.get('/api/v1/earnings/events/'+payload['events'][0]['event_id'])
                assert detail.status_code==200 and detail.json()['financial_store_status']=='not_activated'
        finally:e.get_independent_connection=prior_factory
        assert snapshot(c,TABLES)==original
        def ddl_failure():
            f.initialize_isolated(c);f.import_records(c,records)
            c.execute('SELECT 1/0')
        rejects(c,ddl_failure)
        assert c.execute("SELECT to_regclass('earnings_financial_documents')").fetchone()[0] is None
        assert snapshot(c,TABLES)==original
        assert f.initialize_isolated(c)=='created'
        signature=digest(catalog(c,True))
        assert f.initialize_isolated(c,signature)=='already_initialized'
        rejects(c,lambda:f.initialize_isolated(c,'0'*64))
        partial=copy.deepcopy(records[3]);partial['observations']=partial['observations'][:1]
        f.import_records(c,[partial])
        assert next(r for r in e.load_events(c) if r['ticker']=='AMZN' and r['fiscal_quarter']==3)['financial_data_status']=='partial'
        f.import_records(c,records)
        first=e.load_events(c);f.import_records(c,records);assert e.load_events(c)==first
        assert len(first)==10 and c.execute('SELECT count(*) FROM earnings_financial_documents').fetchone()[0]==6
        assert c.execute('SELECT count(*) FROM earnings_financial_observations').fetchone()[0]==12
        assert sum(r['financial_data_status']=='complete' for r in first)==6
        assert all(r['eps_consensus'] is None and r['revenue_consensus'] is None for r in first)
        future=next(r for r in first if r['ticker']=='NVDA' and r['fiscal_quarter']==3)
        assert future['gaap_diluted_eps_actual'] is None and future['financial_publication_status']=='unconfirmed'
        assert future['release']==next(r for r in before if r['event_id']==future['event_id'])['release']
        correction=copy.deepcopy(records[0]);correction['document']['source_version']='synthetic-correction'
        correction['observations']=correction['observations'][1:]
        correction['observations'][0].update(source_value='2.40',correction_reason='Synthetic revision test')
        f.import_records(c,[correction]);corrected=e.load_events(c)
        f.import_records(c,records);assert e.load_events(c)==corrected
        row=next(r for r in corrected if r['ticker']=='NVDA' and r['fiscal_quarter']==1)
        assert row['gaap_diluted_eps_actual']['actual']=='2.40' and len(row['financial_history'])==3
        assert [o['actual'] for o in row['financial_history'] if o['metric']=='gaap_diluted_eps']==['2.39','2.40']
        # Direct SQL tests exercise composite FKs, attribution, period and append-only guards.
        commands=[
         "UPDATE earnings_financial_observations SET actual=0",
         "DELETE FROM earnings_financial_documents",
         "TRUNCATE earnings_financial_observations",
         "INSERT INTO earnings_financial_documents SELECT gen_random_uuid(),company_id,period_id,event_id,'0000000000',period_end,release_date,source_url,document_type,sec_accession,verified_on,evidence_method,source_version,availability_status,repeat('f',64),captured_at FROM earnings_financial_documents LIMIT 1",
         "INSERT INTO earnings_financial_documents SELECT gen_random_uuid(),company_id,period_id,event_id,cik,period_end+1,release_date,source_url,document_type,sec_accession,verified_on,evidence_method,source_version,availability_status,repeat('f',64),captured_at FROM earnings_financial_documents LIMIT 1",
         "INSERT INTO earnings_financial_documents SELECT gen_random_uuid(),company_id,period_id,(SELECT event_id FROM earnings_events WHERE company_id=d.company_id AND event_id<>d.event_id LIMIT 1),cik,period_end,release_date,source_url,document_type,sec_accession,verified_on,evidence_method,source_version,availability_status,repeat('f',64),captured_at FROM earnings_financial_documents d LIMIT 1",
        ]
        for command in commands: rejects(c,lambda:c.execute(command))
        # Parameterized direct insert bypasses Python validators to exercise observation constraints.
        with c.cursor(row_factory=psycopg.rows.dict_row) as cursor:
            cursor.execute("SELECT * FROM earnings_financial_observations WHERE metric='gaap_diluted_eps' AND version=1 LIMIT 1")
            template=cursor.fetchone()
        for changes in [dict(unit='USD'),dict(currency='EUR'),dict(methodology='non_gaap'),dict(metric='segment'),dict(actual='NaN'),dict(actual='0',source_value='0.001'),dict(version=99),dict(document_id=uuid4()),dict(company_id=uuid4())]:
            candidate={**template,**changes,'observation_id':uuid4(),'record_fingerprint':'e'*64}
            columns=list(candidate)
            command=sql.SQL('INSERT INTO earnings_financial_observations ({}) VALUES ({})').format(sql.SQL(',').join(map(sql.Identifier,columns)),sql.SQL(',').join(sql.Placeholder() for _ in columns))
            rejects(c,lambda:c.execute(command,[candidate[k] for k in columns]))
        bad=copy.deepcopy(records[0]);bad['period_end']='2026-04-25';rejects(c,lambda:f.import_records(c,[bad]))
        # Failure after period/event/document creation rolls back the entire batch.
        stable=snapshot(c,TABLES+['earnings_financial_documents','earnings_financial_observations'])
        c.execute("CREATE FUNCTION e2b_test_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Synthetic SQL failure'; END $$")
        c.execute('CREATE TRIGGER e2b_test_fail BEFORE INSERT ON earnings_financial_observations FOR EACH ROW EXECUTE FUNCTION e2b_test_fail()')
        bad=copy.deepcopy(records[0]);bad.update(fiscal_year=2026,period_label='Q1 FY2026',period_end='2025-04-27',release_date='2025-05-28')
        rejects(c,lambda:f.import_records(c,[bad]))
        assert snapshot(c,TABLES+['earnings_financial_documents','earnings_financial_observations'])==stable
        c.execute('DROP TRIGGER e2b_test_fail ON earnings_financial_observations');c.execute('DROP FUNCTION e2b_test_fail()')
        # Existing date importer remains idempotent; no mutation of its six original events.
        e.import_records(c,json.loads(e.DATA.read_text(encoding='utf-8')))
        final=snapshot(c,TABLES)
        for t in TABLES:
            assert all(r in final[t] for r in original[t])
            if t not in ('earnings_periods','earnings_events'): assert original[t]==final[t]
        assert digest(catalog(c,False))==macro
        if upgrade: assert snapshot(c,['series','observation_vintages'])==macro_data
        c.commit()
    # Actual reader/API run with a read-only connection to this isolated database.
    from datetime import date
    original_factory=e.get_independent_connection
    e.get_independent_connection=factory
    try:
        result=e.calendar_events(date(2026,1,1),date(2026,12,31))
        assert len(result['events'])==7 and len(result['undated'])==3
        assert len(e.companies())==3
        from fastapi.testclient import TestClient
        from app.api.main import app
        with TestClient(app) as client:
            response=client.get('/api/v1/calendar/events?domains=earnings&start_date=2026-01-01&end_date=2026-12-31')
            assert response.status_code==200 and len(response.json()['events'])==7
            detail=client.get('/api/v1/earnings/events/'+row['event_id'])
            assert detail.status_code==200 and detail.json()['gaap_diluted_eps_actual']['actual']=='2.40'
        with factory() as c:
            fourth=uuid4();p=uuid4();event=uuid4()
            c.execute("INSERT INTO earnings_companies VALUES(%s,'0000000001','Synthetic fourth','FOUR')",(fourth,))
            c.execute("INSERT INTO earnings_periods VALUES(%s,%s,2026,4,'quarter','Q4 2026',NULL)",(p,fourth))
            c.execute('INSERT INTO earnings_events(event_id,period_id,company_id) VALUES(%s,%s,%s)',(event,p,fourth))
        assert len(e.companies())==4
        assert any(r['ticker']=='FOUR' for r in e.calendar_events(date(2026,1,1),date(2026,12,31))['undated'])
    finally:e.get_independent_connection=original_factory
    print('E2B', 'upgrade' if upgrade else 'fresh', 'PASSED: SQL, revisions, partial, rollback, read-only API, E2A and macro preservation')

def main():
    if os.environ.get('DB_NAME')!='macrolens_ci_control':raise ValueError('Isolated control database required')
    params={k:os.environ[v] for k,v in [('host','DB_HOST'),('port','DB_PORT'),('user','DB_USER'),('password','DB_PASSWORD')]}
    with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
        for upgrade in (False,True):
            name='macrolens_earnings_e2b_'+uuid4().hex
            admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
            try:verify(lambda:psycopg.connect(**params,dbname=name),upgrade)
            finally:admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
    print('Owned E2B databases removed')

if __name__=='__main__':
    with no_publisher_http():main()
