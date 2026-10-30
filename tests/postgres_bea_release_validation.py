"""R3: real lock/state/rollback in an owned DB; synthetic HTTP and clocks only."""
import sys,os,json,copy
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime,timedelta
from unittest.mock import patch
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx,psycopg
from psycopg import sql
from app.database.connection import get_independent_connection,get_connection
from app.database import init_db
from app import source_checks
from app.analytics import overview_refresh as refresh,overview_refresh_store as stores,bea_release_refresh as policy
from app.ingestion import sync_bea_reports as source
from tests.test_bea_direct import schedule,gdp,pio,URL,PIO
from tests.test_bea_release_refresh import T


def verify(factory):
    with patch.object(init_db,'get_connection',factory):assert init_db.main()==0
    with factory() as c:
        c.execute("INSERT INTO series(series_id,name,category,frequency) VALUES ('PRESERVED','Synthetic legacy','test','monthly')")
        c.execute("INSERT INTO observation_vintages(series_id,observation_date,vintage_date,value,source) VALUES ('PRESERVED','2026-01-01','2026-02-01',1,'fred_snapshot'),('PRESERVED','2026-01-01','2026-02-02',2,'alfred')")
        proofs=source.discover(schedule(),T.isoformat())
        c.execute("INSERT INTO source_check_runs(id,resource,attempted_at,finished_at,status,scope) VALUES (%s,%s,%s,%s,'success',%s::jsonb)",(uuid4(),source.RESOURCE,T-timedelta(hours=1),T-timedelta(hours=1),json.dumps({'validated_schedule':proofs})))
    clock=[T];calls=[];work=[];partial=pio().replace('Excluding food and energy, the PCE price index increased','Other prices increased')
    bodies={URL:None,PIO:partial};schedule_body=[schedule()]
    def transport(request):
        url=str(request.url);calls.append(url)
        body=schedule_body[0] if url==source.SCHEDULE else bodies[url]
        if body=='RATE_LIMIT':return httpx.Response(429,text='Synthetic throttle',headers={'Retry-After':'3600'})
        return httpx.Response(404 if body is None else 200,text=body or 'Not published')
    original_client=httpx.Client;original_capture=source.capture
    def client(**kwargs):return original_client(transport=httpx.MockTransport(transport),**kwargs)
    def capture(response,url,stamp,root):return original_capture(response,url,clock[0]+timedelta(seconds=1),raw_root)
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return clock[0]+timedelta(seconds=1)
    def brief():
        with get_connection().cursor() as c:c.execute("SELECT series_id,value FROM observation_vintages WHERE source='bea_official' ORDER BY series_id");rows=c.fetchall()
        return {'source_checks':{'status':'partial'},'synthetic_bea':[(s,str(v)) for s,v in rows]}
    with TemporaryDirectory(prefix='bea-release-test-') as temp:
        raw_root=Path(temp)
        with patch.object(stores,'get_independent_connection',factory),patch.object(refresh,'get_independent_connection',factory),patch.object(source_checks,'get_connection',factory),patch.object(refresh.httpx,'Client',client),patch.object(source,'capture',capture),patch.object(source,'datetime',Clock),patch.object(refresh,'utc_now',lambda:clock[0]+timedelta(seconds=2)),patch.object(refresh.economy_brief,'build_brief',brief),patch.object(refresh,'collect_histories',lambda *a:{}):
            store=stores.RefreshStore()
            with factory() as c:
                baseline=store.publish(c,{'synthetic':'baseline'},{},T-timedelta(hours=1))
                store.update(dict(status='complete',completed_at=T-timedelta(minutes=5),next_check_at=T+timedelta(minutes=10)),c)
                legacy=c.execute("SELECT row_to_json(o)::text FROM observation_vintages o WHERE source IN ('fred_snapshot','alfred') ORDER BY id").fetchall()
            a=refresh.RefreshCoordinator(store,clock=lambda:clock[0],launch=work.append)
            b=refresh.RefreshCoordinator(stores.RefreshStore(),clock=lambda:clock[0],launch=work.append)
            one=a.request();two=b.request();three=a.request()
            assert one['job_id']==two['job_id']==three['job_id'] and len(work)==1 and not calls
            assert all(v['attempts']==1 for v in store.read()['source_versions'][policy.KEY]['events'].values())
            work.pop(0)()
            first=store.read();assert first['publication_id']!=baseline
            assert len(calls)==3 and first['publication_created_at'] is not None
            assert a.status()['standard_next_check_at']==(T+timedelta(minutes=10)).isoformat()
            clock[0]=T+timedelta(minutes=2);bodies[URL]=gdp();a.request();work.pop(0)();clock[0]+=timedelta(seconds=3)
            state=a.status();assert [p['status'] for p in state['bea_release_checks']]==['confirmed','partial']
            clock[0]=T+timedelta(minutes=5);bodies[PIO]=pio();a.request();work.pop(0)();clock[0]+=timedelta(seconds=3)
            assert calls[-2:]==[source.SCHEDULE,PIO]
            assert all(p['status']=='confirmed' for p in a.status()['bea_release_checks'])
            previous=store.read()['publication_id'];count=len(calls)
            clock[0]=T+timedelta(minutes=7);a.request();assert not work and len(calls)==count
            # A new independent instance retains claims. A failed narrow SQL
            # transaction cannot undo the already committed reservation.
            clock[0]=T+timedelta(days=27)
            new_url=URL+'-second';new_pio=PIO+'-october'
            schedule_body[0]=schedule().replace('October 29','November 25').replace('Advance Estimate','Second Estimate').replace('September 2026','October 2026').replace(URL,new_url).replace(PIO,new_pio)
            proofs=source.discover(schedule_body[0],clock[0].isoformat())
            with factory() as c:
                c.execute("INSERT INTO source_check_runs(id,resource,attempted_at,finished_at,status,scope) VALUES (%s,%s,%s,%s,'success',%s::jsonb)",(uuid4(),source.RESOURCE,clock[0],clock[0],json.dumps({'validated_schedule':proofs})))
                c.execute("CREATE FUNCTION release_fail() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RAISE EXCEPTION 'Synthetic R3 rollback'; END$$")
                c.execute("CREATE TRIGGER release_fail BEFORE INSERT ON observation_vintages FOR EACH ROW WHEN (NEW.source='bea_official') EXECUTE FUNCTION release_fail()")
                store.update(dict(status='complete',next_check_at=clock[0]+timedelta(minutes=10),source_versions={policy.KEY:{'events':{},'standard_next_at':(clock[0]+timedelta(minutes=10)).isoformat()}}),c)
                before=c.execute('SELECT row_to_json(o)::text FROM observation_vintages o ORDER BY id').fetchall();docs=source.receipts(c)
            # EST release is an hour later in UTC than the October example.
            clock[0]+=timedelta(hours=1)
            with factory() as c:store.update({'source_versions':{policy.KEY:{'events':{},'standard_next_at':(clock[0]+timedelta(minutes=10)).isoformat()}}},c)
            bodies[new_url]=gdp().replace('Advance Estimate','Second Estimate').replace('EDT, Thursday, October 29','EST, Wednesday, November 25')
            bodies[new_pio]=pio().replace('September','October').replace('August','September').replace('EDT, Thursday, October 29','EST, Wednesday, November 25')
            restarted=refresh.RefreshCoordinator(stores.RefreshStore(),clock=lambda:clock[0],launch=work.append)
            restarted.request();assert len(work)==1;work.pop(0)()
            assert store.read()['status']=='error' and store.read()['publication_id']==previous
            assert all(v['attempts']==1 for v in store.read()['source_versions'][policy.KEY]['events'].values())
            with factory() as c:
                assert c.execute('SELECT row_to_json(o)::text FROM observation_vintages o ORDER BY id').fetchall()==before
                assert source.receipts(c)==docs
                assert c.execute("SELECT row_to_json(o)::text FROM observation_vintages o WHERE source IN ('fred_snapshot','alfred') ORDER BY id").fetchall()==legacy
            # The transport backoff must survive a later failure of the job's
            # final transaction, independently of its source_versions update.
            clock[0]+=timedelta(minutes=2);bodies[new_url]='RATE_LIMIT'
            original_update=store.update
            def fail_final(fields,connection=None):
                if connection is not None and fields.get('status')=='partial':raise RuntimeError('Synthetic final job write failure')
                return original_update(fields,connection)
            retry=refresh.RefreshCoordinator(store,clock=lambda:clock[0],launch=work.append)
            with patch.object(store,'update',fail_final):retry.request();work.pop(0)()
            assert not store.read()['source_versions'][policy.KEY].get('backoff_until')
            with factory() as c:
                assert policy.load_context(c)['backoff_until'] is not None
                assert c.execute("SELECT count(*) FROM source_check_runs WHERE resource='bea:reports' AND status='running'").fetchone()[0]==0
                assert c.execute("SELECT status,error_code FROM source_check_runs WHERE scope ? 'backoff_until' ORDER BY attempted_at DESC LIMIT 1").fetchone()==('error','refresh_interrupted')
            count=len(calls);clock[0]+=timedelta(minutes=3);retry.request()
            assert len(calls)==count and not work and store.read()['publication_id']==previous
    print('R3 real PostgreSQL: shared lock, two workers/three requests, durable counters, partial PIO, targeted stop, atomic generation, SQL rollback and preserved FRED/ALFRED PASSED')


def main():
    original=get_independent_connection();params=original.info.get_parameters();user_db=params['dbname'];original.close()
    params.update(dbname='postgres',password=os.environ['DB_PASSWORD']);name='macrolens_bea_release_test_'+uuid4().hex
    assert name.startswith('macrolens_bea_release_test_') and name!=user_db
    with psycopg.connect(**params,autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:verify(lambda:psycopg.connect(**{**params,'dbname':name}))
        finally:admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
    print('Only owned test database removed; user DB not modified')

if __name__=='__main__':
    from tests.postgres_http_guard import no_publisher_http
    with no_publisher_http():
        main()
