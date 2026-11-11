"""Actual full restored PG17 clone. Never writes a normal database.

BACKFILL_TEST_DIR supplies a freshly verified normal dump and owned clone.
The target of each negative mutation is guarded by the exact clone prefix,
loopback port and CI role. Publisher HTTP is blocked throughout.
"""
import copy,json,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from integrations.earnings_history_backfill import activation as a
from app import earnings
from tests.postgres_earnings_financial_activation_validation import make_backup
from tests.postgres_http_guard import no_publisher_http


def main():
    raw=Path(os.environ['BACKFILL_TEST_DIR']).resolve();own=json.loads((raw/'clone.json').read_text());params=own['params'];name=own['name'];container=own['container']
    if not(name.startswith('macrolens_earnings_e2b_e2c_e2d_e2e_backfill_') and params['host']=='127.0.0.1' and params['port']==55531 and params['user']=='macrolens_ci' and len(container)==64):raise ValueError('Owned backfill clone/PG17/role required')
    factory=lambda:psycopg.connect(**params,dbname=name)
    checks=[]
    def check(ok,label):assert ok,label;checks.append(label);print('PASS',label,flush=True)
    def rejected(call,label):
        try:call()
        except (ValueError,psycopg.Error):check(True,label)
        else:raise AssertionError(label)
    with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
        directory=raw/('clone-backup-'+str(time.time_ns()));directory.mkdir();os.environ['DB_PASSWORD']=params['password']
        backup=make_backup(factory,admin,name,container,directory)
        (raw/'clone-backup.json').write_text(json.dumps(backup,indent=2),encoding='utf-8')
        with factory() as c:c.read_only=True;target=a.base.target_identity(c)
        with factory() as c:c.read_only=True;plan=a.prepare(c,target,backup)
        digest=a.base.digest(plan);label=plan['target_label'];(raw/'clone-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
        with factory() as c:
            c.read_only=True;before=a.financial.table_snapshots(c);old=earnings.load_events(c)
        for target_label,approval in [('wrong',digest),(label,'0'*64)]:
            with factory() as c:rejected(lambda:a.apply(c,plan,target_label,approval,backup),'bad approval/target')
        with factory() as lock:
            lock.autocommit=True;lock.execute('SELECT pg_advisory_lock(726530020)')
            try:
                with factory() as c:rejected(lambda:a.apply(c,plan,label,digest,backup),'concurrent writer stops')
            finally:lock.execute('SELECT pg_advisory_unlock(726530020)')
        class Broken:
            def __init__(self,c):self.c=c;self.n=0
            def __getattr__(self,key):return getattr(self.c,key)
            def execute(self,query,*args):
                result=self.c.execute(query,*args)
                if isinstance(query,str) and query.startswith('INSERT INTO earnings_historical_reports'):
                    self.n+=1
                    if self.n==2:self.c.execute('SELECT 1/0')
                return result
        with factory() as c:rejected(lambda:a.apply(Broken(c),plan,label,digest,backup),'actual SQL error rolls back whole batch')
        with factory() as c:check(a.financial.table_snapshots(c)==before,'all 29 tables identical after rollback')
        with factory() as blocker:
            blocker.execute('LOCK TABLE earnings_historical_reports IN ACCESS EXCLUSIVE MODE');started=time.monotonic()
            with factory() as c:rejected(lambda:a.apply(c,plan,label,digest,backup),'bounded lock timeout')
            check(4.5<time.monotonic()-started<12,'lock budget remains five seconds')
        # Drift probes are rolled back on the owned clone only.
        with factory() as c:
            c.execute('CREATE INDEX backfill_foreign_probe ON earnings_events(company_id)')
            rejected(lambda:a.live(c,plan),'foreign schema stops');c.rollback()
        with factory() as c:
            receipt=a.apply(c,plan,label,digest,backup)
        check(receipt['outcome']=='created','seven historical reports committed')
        with factory() as c:c.read_only=True;a.verify(c,plan);new=earnings.load_events(c);after=a.financial.table_snapshots(c)
        check(all(after[t]==before[t] for t in before if t!=a.TABLE),'28 other full tables unchanged')
        check(after[a.TABLE]['rows']==30,'23 to 30 historical reports')
        oldby={e['event_id']:e for e in old};newby={e['event_id']:e for e in new}
        check(set(oldby)==set(newby),'no new calendar event identity')
        for identifier,e in newby.items():
            prior=oldby[identifier]
            for field in ('current_eps_actual','current_revenue_actual','release','call','report_documents','market_cap_usd'):
                check(e.get(field)==prior.get(field),'unchanged '+field+' '+e['ticker'])
            for field in ('previous_eps_actual','previous_revenue_actual'):
                if prior.get(field) is not None:check(e.get(field)==prior.get(field),'existing '+field+' preserved '+e['ticker'])
        expected={'ARM':('0.25','1289000000',2027,1),'QCOM':('1.87','9947000000',2026,3),'PANW':('-0.35','3410000000',2026,4),'SNOW':('-0.55','1546793000',2027,2),'NVDA':('1.76','68127000000',2026,4),'AMZN':('2.78','181519000000',2026,1),'INTC':(None,'13577000000',2026,1)}
        for ticker,(eps,revenue,year,quarter) in expected.items():
            e=next(e for e in new if e['ticker']==ticker and a.earnings_previous.previous_quarter(e['fiscal_year'],e['fiscal_quarter'])==(year,quarter))
            check((e['previous_eps_actual']['actual'] if e['previous_eps_actual'] else None)==eps and e['previous_revenue_actual']['actual']==revenue,'exact official pair '+ticker)
            check((e['previous_period']['fiscal_year'],e['previous_period']['fiscal_quarter'])==(year,quarter),'exact fiscal predecessor '+ticker)
        check(next(e for e in new if e['ticker']=='CRWD')['previous_eps_actual'] is None,'CRWD incompatible pre-split EPS remains null')
        with factory() as c:check(a.apply(c,plan,label,digest,backup)['outcome']=='already_initialized','idempotent apply')
        with factory() as c:check(a.financial.table_snapshots(c)==after,'all timestamps unchanged on retry')
        with factory() as c:
            rejected(lambda:c.execute('UPDATE earnings_historical_reports SET version=version'),'append-only UPDATE blocked');c.rollback()
        # Real TestClient reads from this real SQL target, no fabricated response.
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from app.database import connection
        def readonly():c=factory();c.read_only=True;return c
        with patch.object(connection,'get_independent_connection',readonly):
            from app.api.main import app
            from app import earnings as reader
            with patch.object(reader,'get_independent_connection',readonly),TestClient(app) as client:
                response=client.get('/api/v1/calendar/events',params=dict(domains='earnings',start_date='2026-01-01',end_date='2026-12-31'))
                check(response.status_code==200,'actual API/SQL HTTP200')
                data=response.json();check(len(data['events'])==34,'34 dated events remain')
                for ticker in expected:
                    year,quarter=expected[ticker][2:]
                    e=next(e for e in data['events'] if e['ticker']==ticker and a.earnings_previous.previous_quarter(e['fiscal_year'],e['fiscal_quarter'])==(year,quarter))
                    check((e['previous_eps_actual']['actual'] if e['previous_eps_actual'] else None)==expected[ticker][0],'actual API previous '+ticker)
        (raw/'trial-results.json').write_text(json.dumps(dict(checks=checks,before=before,after=after,receipt=receipt),indent=2),encoding='utf-8')
        (raw/'after-events.json').write_text(json.dumps(new,indent=2,default=str),encoding='utf-8')
        print('BACKFILL PG PASSED',len(checks),'checks; seven reports/13 metrics',flush=True)


if __name__=='__main__':
    with no_publisher_http():main()
