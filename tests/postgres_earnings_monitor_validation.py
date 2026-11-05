"""Real PG17, actual cached official PDFs, durable slots and two processes.

Owned loopback only; all publisher requests use MockTransport. Live retrieval
and Chrome are exercised separately, with real HTTP, on the owned demo.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
import psycopg
from psycopg import sql
from app import earnings as e,earnings_reports as r,earnings_history as h,earnings_monitor as m
from app import earnings_monitor_policy as p
from app.database import activate_earnings as b,activate_earnings_financials as f,activate_earnings_monitor as a
from tests.postgres_earnings_report_validation import seed
from tests.postgres_earnings_financial_activation_validation import make_backup
from tests.postgres_http_guard import no_publisher_http


def initialize(factory):
    with factory() as c:
        seed(c);r.initialize_isolated(c);r.import_records(c,json.loads(r.DATA.read_text(encoding='utf-8')))
        h.initialize_isolated(c);h.import_records(c,json.loads(h.DATA.read_text(encoding='utf-8')))


def main():
    if os.environ.get('DB_NAME')!='macrolens_monitor_control':raise ValueError('Owned monitor control required')
    params={k:os.environ[v] for k,v in [('host','DB_HOST'),('port','DB_PORT'),('user','DB_USER'),('password','DB_PASSWORD')]}
    container=os.environ['REPORT_TEST_CONTAINER']
    if params['host']!='127.0.0.1' or not container.startswith('macrolens_reports_activation_'):raise ValueError('Owned local service required')
    if len(sys.argv)>1 and sys.argv[1]=='--busy-probe':
        name=sys.argv[2];assert name.startswith(r.PREFIX)
        token=json.loads(Path(sys.argv[3]).read_text())
        result=m.run(lambda:psycopg.connect(**params,dbname=name),token=token)
        assert result==dict(status='busy',checked=0);print(json.dumps(result));return
    pdfs=Path(os.environ['MONITOR_REAL_PDFS_DIR'])
    arm=(pdfs/'arm.pdf').read_bytes();qcom=(pdfs/'qcom.pdf').read_bytes()
    with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin,TemporaryDirectory(prefix='earnings_monitor_') as temp:
        root=Path(temp)
        for scenario in ('success','rollback','restart'):
            name=h.PREFIX+'monitor_'+uuid4().hex[:12]
            admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
            try:
                factory=lambda:psycopg.connect(**params,dbname=name)
                initialize(factory)
                directory=root/scenario;directory.mkdir()
                with factory() as c:reference=a.reference(c)
                backup=make_backup(factory,admin,name,container,directory)
                with factory() as c:c.read_only=True;plan=a.prepare(c,backup['target'],reference,backup)
                with factory() as c:
                    try:a.apply(c,plan,plan['target_label'],'old-e2e-hash',backup)
                    except ValueError:pass
                    else:raise AssertionError('Old approval accepted')
                class FailPolicyInsert:
                    def __init__(self,c):self.c=c
                    def __getattr__(self,key):return getattr(self.c,key)
                    def execute(self,query,*args):
                        if isinstance(query,str) and query.startswith('INSERT INTO earnings_monitor_policy'):return self.c.execute('SELECT 1/0')
                        return self.c.execute(query,*args)
                with factory() as c:
                    before=f.table_snapshots(c);c.rollback()
                    try:a.apply(FailPolicyInsert(c),plan,plan['target_label'],b.digest(plan),backup)
                    except psycopg.errors.DivisionByZero:pass
                    else:raise AssertionError('Activation SQL rollback missing')
                    assert f.table_snapshots(c)==before;c.rollback()
                    receipt=a.apply(c,plan,plan['target_label'],b.digest(plan),backup)
                token=receipt['runtime_token'];tokenfile=directory/'token.json';tokenfile.write_text(json.dumps(token))
                with factory() as c:
                    old=f.table_snapshots(c);old_docs=set(row[0] for row in c.execute('SELECT row_to_json(t)::text FROM earnings_report_documents t'))
                    old_obs=set(row[0] for row in c.execute('SELECT row_to_json(t)::text FROM earnings_report_observations t'))
                    events=e.load_events(c)
                arm_id=next(x['event_id'][9:] for x in events if x['ticker']=='ARM')
                calls=[]
                def actual(request):
                    calls.append(str(request.url))
                    if request.url.host=='investors.arm.com':return httpx.Response(200,content=arm,headers={'content-type':'application/pdf'})
                    if request.url.host=='investor.qualcomm.com':return httpx.Response(302,headers={'location':'//s204.q4cdn.com/645488518/files/content_files/FY2026-4th-Quarter-Earnings-Release.pdf'})
                    return httpx.Response(200,content=qcom,headers={'content-type':'application/pdf'})
                now=p.instant('2026-11-04T21:00:00Z')
                if scenario=='success':
                    not_found=httpx.MockTransport(lambda request:httpx.Response(404))
                    assert m.run(factory,token,lambda:now,not_found,directory)['checked']==2
                    assert m.run(factory,token,lambda:now,not_found,directory)['checked']==0
                    now+=p.timedelta(minutes=15)
                    retry=httpx.MockTransport(lambda request:httpx.Response(429,headers={'retry-after':'1800'}))
                    assert m.run(factory,token,lambda:now,retry,directory)['checked']==2
                    now+=p.timedelta(minutes=15)
                    assert m.run(factory,token,lambda:now,httpx.MockTransport(actual),directory)['checked']==0 and not calls
                    # A second process sees the same SQL advisory lease and never fetches.
                    with factory() as busy:
                        busy.execute('SELECT pg_advisory_lock(%s)',(m.LOCK,));busy.commit()
                        probe=subprocess.run([sys.executable,__file__,'--busy-probe',name,str(tokenfile)],env=os.environ,capture_output=True,text=True)
                        assert probe.returncode==0,probe.stdout+probe.stderr
                        busy.execute('SELECT pg_advisory_unlock(%s)',(m.LOCK,));busy.commit()
                    now+=p.timedelta(minutes=15)
                    # Macro lease does not stop Earnings; no data are written to macro.
                    with factory() as macro:
                        macro.execute('SELECT pg_advisory_lock(726530019)');macro.commit()
                        assert m.run(factory,token,lambda:now,httpx.MockTransport(actual),directory)['checked']==2
                        macro.execute('SELECT pg_advisory_unlock(726530019)');macro.commit()
                    assert len(calls)==3
                    assert m.run(factory,token,lambda:now+p.timedelta(minutes=15),httpx.MockTransport(actual),directory)['checked']==0
                    assert len(calls)==3
                    with factory() as c:
                        after=f.table_snapshots(c);events=e.load_events(c)
                        assert set(row[0] for row in c.execute('SELECT row_to_json(t)::text FROM earnings_report_documents t'))>=old_docs
                        assert set(row[0] for row in c.execute('SELECT row_to_json(t)::text FROM earnings_report_observations t'))>=old_obs
                        assert after['earnings_report_documents']['rows']==29 and after['earnings_report_observations']['rows']==50
                        for t,snapshot in old.items():
                            if t not in (*r.TABLES,'earnings_report_checks'):assert after[t]==snapshot,t
                        for ticker,eps,revenue in [('ARM','0.12','1443000000'),('QCOM','1.17','10322000000')]:
                            current=next(x for x in events if x['ticker']==ticker)
                            assert current['publication_state']['code']=='published_complete'
                            assert current['current_eps_actual']['actual']==eps and current['current_revenue_actual']['actual']==revenue
                            assert current['previous_eps_actual'] is None and current['current_eps_forecast'] is None
                        for table in ('earnings_monitor_policy','earnings_report_checks'):
                            try:
                                with c.transaction():c.execute('DELETE FROM '+table)
                            except psycopg.Error:pass
                            else:raise AssertionError('Mutable policy/audit')
                    from app.api.main import app
                    from fastapi.testclient import TestClient
                    def readonly():
                        c=factory();c.read_only=True;return c
                    with patch.object(e,'get_independent_connection',readonly),TestClient(app) as client:
                        response=client.get('/api/v1/calendar/events?domains=earnings&start_date=2026-11-04&end_date=2026-11-04')
                        assert response.status_code==200 and all(x['current_eps_actual'] for x in response.json()['events'])
                elif scenario=='rollback':
                    original=r._append_prepared
                    def broken(connection,records):original(connection,records);connection.execute('SELECT 1/0')
                    with patch.object(r,'_append_prepared',broken):
                        assert m.run(factory,token,lambda:now,httpx.MockTransport(actual),directory)['checked']==2
                    with factory() as c:
                        after=f.table_snapshots(c)
                        assert all(after[t]==old[t] for t in old if t!='earnings_report_checks')
                        assert c.execute("SELECT count(*) FROM earnings_report_checks WHERE status='review_required'").fetchone()[0]==2
                else:
                    slot=now
                    with factory() as c:m.audit(c,e.identity('monitor:'+arm_id+':'+slot.isoformat()),arm_id,slot,now-p.timedelta(minutes=6),'started','started',{})
                    assert m.run(factory,token,lambda:now,httpx.MockTransport(lambda request:httpx.Response(404)),directory)['checked']==1
                    with factory() as c:assert c.execute("SELECT count(*) FROM earnings_report_checks WHERE status='interrupted'").fetchone()[0]==1
                    now+=p.timedelta(minutes=15)
                    assert m.run(factory,token,lambda:now,httpx.MockTransport(actual),directory)['checked']==2
                print('MONITOR SQL',scenario,'passed',flush=True)
            finally:admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
    print('MONITOR PG17 PASSED: controlled activation rollback, durable15min slots,404/429/backoff,real PDFs,GAAP2/4,new process,macro lease independence,atomic import rollback,restart,idempotency,API200,Previous/macro preserved')


if __name__=='__main__':
    with no_publisher_http():main()
