"""V2 real SQL, concurrent writers and real backup/restore; owned PG17 only."""
import copy,json,os,sys,re
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from decimal import Decimal
from app.database import activate_earnings_history_v2 as a,activate_earnings as b,activate_earnings_financials as f
from tests.postgres_earnings_report_validation import seed
from tests.postgres_earnings_financial_activation_validation import make_backup
from tests.postgres_http_guard import no_publisher_http


def macro_write(factory):
    with factory() as c:
        c.execute("INSERT INTO source_check_runs(id,resource,attempted_at,finished_at,status) VALUES (%s,'synthetic:v2',clock_timestamp(),clock_timestamp(),'success')",(uuid4(),))
        publication=uuid4()
        c.execute("INSERT INTO overview_publications VALUES (%s,clock_timestamp(),'{}'::jsonb,'{}'::jsonb)",(publication,))
        c.execute("UPDATE overview_refresh_state SET completed_at=clock_timestamp(),publication_id=%s WHERE id=1",(publication,))


def api_checks(factory):
    from app import earnings
    from app.api.main import app
    from fastapi.testclient import TestClient
    def readonly():
        c=factory();c.read_only=True;return c
    with patch.object(earnings,'get_independent_connection',readonly),TestClient(app) as client:
        response=client.get('/api/v1/calendar/events?domains=earnings&start_date=2026-05-01&end_date=2026-12-31')
        assert response.status_code==200
        rows=response.json()['events']
        expected={'AAPL':('2.02','109417000000'),'PLTR':('0.41','1935464000'),'AMD':('1.38','11536000000'),'INTC':('-2.16','16128000000'),'AMZN':('5.75','200606000000'),'NVDA':('2.39','81615000000')}
        for ticker,(eps,revenue) in expected.items():
            candidates=[e for e in rows if e['ticker']==ticker and e['previous_eps_actual']]
            e=min(candidates,key=lambda r:int(r['fiscal_quarter'])) if ticker=='NVDA' else candidates[-1]
            assert Decimal(e['previous_eps_actual']['actual'])==Decimal(eps)
            assert Decimal(e['previous_revenue_actual']['actual'])==Decimal(revenue)
        for e in rows:
            if e['ticker'] in ('ARM','QCOM'):assert not e['previous_eps_actual'] and not e['previous_revenue_actual']
            if e['ticker']=='CRWD':assert e['previous_eps_actual'] is None and e['previous_revenue_actual']
            if e['ticker']=='NVDA' and e['fiscal_quarter']==3:
                assert e['current_eps_actual'] is None and e['previous_eps_actual']['actual']=='2.46'
        return len(rows)


def verify(factory,admin,name,container,directory):
    with factory() as c:ref=a.reference(c)
    backup=make_backup(factory,admin,name,container,directory)
    with factory() as c:
        c.read_only=True;plan=a.prepare(c,backup['target'],ref)
    token=b.digest(plan);label=plan['target_label']
    macro_write(factory)
    with factory() as c:
        c.read_only=True;assert a.prepare(c,backup['target'],ref)==plan
    def rejected(p=plan,expected=ValueError):
        with factory() as c:
            before=f.table_snapshots(c);c.rollback()
            try:a.apply(c,p,p['target_label'],b.digest(p),backup)
            except expected:pass
            else:raise AssertionError('Invalid V2 accepted')
            assert f.table_snapshots(c)==before
    for field in ('ledger','ddl','target','manifest','count'):
        bad=copy.deepcopy(plan)
        if field=='ledger':bad['ledger']['records'][0]['observations'].pop()
        if field=='ddl':bad['ddl']['text']+='\n-- changed'
        if field=='target':bad['target']['database_oid']+=1
        if field=='manifest':bad['seed_manifest'][a.TABLE][0]['payload']['observations'][0]['actual']='999'
        if field=='count':bad['expected_counts'][a.TABLE]=22
        rejected(bad)
    with factory() as c:
        key,old=c.execute('SELECT company_id,name FROM earnings_companies ORDER BY company_id LIMIT 1').fetchone()
        c.execute("UPDATE earnings_companies SET name='Synthetic V2 change' WHERE company_id=%s",(key,))
    rejected()
    with factory() as c:
        c.read_only=True;assert b.digest(a.prepare(c,backup['target'],ref))!=token
    with factory() as c:c.execute('UPDATE earnings_companies SET name=%s WHERE company_id=%s',(old,key))
    with factory() as c:c.execute('ALTER TABLE earnings_companies ADD COLUMN v2_probe uuid REFERENCES overview_publications(id)')
    rejected()
    with factory() as c:c.execute('ALTER TABLE earnings_companies DROP COLUMN v2_probe')
    with factory() as c:c.execute('CREATE TABLE earnings_historical_reports (foreign_probe integer)')
    rejected()
    with factory() as c:c.execute('DROP TABLE earnings_historical_reports')
    with factory() as concurrent:
        concurrent.execute('SELECT pg_advisory_xact_lock(726530020)')
        rejected()
        concurrent.rollback()
    # An already active Earnings writer causes bounded lock_timeout, no bypass.
    with factory() as writer:
        writer.execute('UPDATE earnings_companies SET name=name WHERE company_id=%s',(key,))
        rejected(expected=psycopg.errors.LockNotAvailable)
        writer.rollback()
    with factory() as c:
        before=f.table_snapshots(c);c.rollback();original=a.legacy.import_seed
        def broken(connection,records):original(connection,records[:1]);connection.execute('SELECT 1/0')
        with patch.object(a.legacy,'import_seed',broken):
            try:a.apply(c,plan,label,token,backup)
            except psycopg.errors.DivisionByZero:pass
            else:raise AssertionError('SQL error not raised')
        assert f.table_snapshots(c)==before;c.rollback()
        macro_names=set(before)-set(a.PROTECTED)
        observed={}
        def during(connection,records):
            # A separate committed macro writer works while all Earnings locks
            # are held; its changes remain intact after activation.
            macro_write(factory)
            with factory() as writer:
                writer.execute("SET LOCAL lock_timeout='100ms'")
                try:writer.execute('UPDATE earnings_companies SET name=name WHERE company_id=%s',(key,))
                except psycopg.errors.LockNotAvailable:writer.rollback()
                else:raise AssertionError('Earnings writer entered protected interval')
            with factory() as audit:observed['macro']=f.table_snapshots(audit,macro_names)
            original(connection,records)
        # Macro lease deliberately held: V2 must NOT acquire it or stop macros.
        with factory() as macro_lease:
            macro_lease.execute('SELECT pg_advisory_xact_lock(726530019)')
            with patch.object(a.legacy,'import_seed',during):receipt=a.apply(c,plan,label,token,backup)
            macro_lease.rollback()
        assert receipt['outcome']=='created'
        after=f.table_snapshots(c);c.rollback()
        assert {t:after[t] for t in a.PROTECTED}==plan['protected_snapshots']
        assert {t:after[t] for t in macro_names}==observed['macro']
        repeated=a.apply(c,plan,label,token,backup)
        assert repeated['outcome']=='already_initialized' and f.table_snapshots(c)==after;c.rollback()
        for query in ['UPDATE earnings_historical_reports SET version=version','DELETE FROM earnings_historical_reports','TRUNCATE earnings_historical_reports']:
            try:
                with c.transaction():c.execute(query)
            except psycopg.Error:pass
            else:raise AssertionError('Append-only guard failed')
        assert api_checks(factory)==34
        assert f.table_snapshots(c)==after
    (directory/'v2-result.json').write_text(json.dumps(dict(outcome='passed',plan_sha256=token,receipt=receipt,macro_drift_hash_stable=True,concurrent_macro_writer=True,earnings_writer_blocked=True,sql_rollback=True,idempotency=True),indent=2))
    return plan,receipt


def main():
    if os.environ.get('DB_NAME')!='macrolens_history_v2_control':raise ValueError('Owned V2 control required')
    params={k:os.environ[v] for k,v in [('host','DB_HOST'),('port','DB_PORT'),('user','DB_USER'),('password','DB_PASSWORD')]}
    container=os.environ['REPORT_TEST_CONTAINER']
    ci_service=(os.environ.get('GITHUB_ACTIONS')=='true' and params['user']=='macrolens_ci'
                and re.fullmatch(r'[0-9a-f]{64}',container))
    if params['host']!='127.0.0.1' or not (container.startswith('macrolens_reports_activation_') or ci_service):raise ValueError('Owned local V2 container required')
    with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
        name=a.legacy.reports.PREFIX+'v2_'+uuid4().hex[:12]
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:
            factory=lambda:psycopg.connect(**params,dbname=name)
            with factory() as c:
                seed(c);a.legacy.current.reports.initialize_isolated(c);a.legacy.current.reports.import_records(c,a.legacy.current.seed())
            with TemporaryDirectory(prefix='history_v2_') as temp:verify(factory,admin,name,container,Path(temp))
        finally:admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
    print('V2 PASSED: deterministic scoped plan, three macro tables before/during apply, actual backup/restore, FK dependencies, Earnings drift STOP, bounded locks, concurrent activation STOP, SQL rollback, 23/45, idempotency and read-only API')


if __name__=='__main__':
    with no_publisher_http():main()
