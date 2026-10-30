"""Overview refresh tests use no external services or configured database."""
import copy
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from app.analytics import overview_refresh as refresh
from app.analytics.features import calculate_features
from app.database import connection as connections
from app.ingestion import discover_ism, fred
from app import source_checks
from app.api.main import app

NOW = datetime(2026,10,26,12,tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def isolated_ism_schedule(monkeypatch):
    from app.ingestion import sync_ism_calendar
    monkeypatch.setattr(sync_ism_calendar,'sync_schedule',lambda *a,**k:{'events':[],'check':{'status':'success'}})
    monkeypatch.setattr(sync_ism_calendar,'read_schedule',lambda:{'adapter_version':sync_ism_calendar.SCHEDULE_ADAPTER_VERSION})
    from app.ingestion import sync_michigan_calendar
    monkeypatch.setattr(sync_michigan_calendar,'sync_schedule',lambda *a,**k:{'events':[],'check':{'status':'success'}})
    from app.ingestion import sync_adp_calendar
    monkeypatch.setattr(sync_adp_calendar,'sync_schedule',lambda *a,**k:{'events':[],'check':{'status':'success'}})


class MemoryStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.state = dict(status='idle',job_id=None,attempted_at=None,completed_at=None,next_check_at=None,
                          publication_id='stored',source_versions={},results=[])
    def publication(self):return ('stored',{})
    def acquire(self): return self.lock if self.lock.acquire(blocking=False) else None
    def release(self, lease): lease.release()
    def read(self): return copy.deepcopy(self.state)
    def start(self, job_id, now, next_check):
        self.update(dict(job_id=job_id,status='running',attempted_at=now,next_check_at=next_check,results=[]))
    def update(self, fields, connection=None): self.state.update(copy.deepcopy(fields))


@pytest.fixture(autouse=True)
def isolated_provenance(monkeypatch):
    rows = {}
    monkeypatch.setattr(source_checks,'write_run',lambda row:rows.__setitem__(row['id'],copy.deepcopy(row)))
    return rows


def test_simultaneous_requests_share_one_job_and_persistent_lock():
    store = MemoryStore()
    started, done = threading.Event(), threading.Event()
    calls=[]
    def runner(store, previous, now, interval, retry):
        calls.append(previous);started.set();done.wait(5)
        store.update({'status':'complete','next_check_at':now+timedelta(seconds=interval)})
    coordinator = refresh.RefreshCoordinator(store,runner,lambda:NOW)
    # Separate coordinator instances model separate Uvicorn workers sharing PostgreSQL.
    other = refresh.RefreshCoordinator(store,runner,lambda:NOW)
    with ThreadPoolExecutor(max_workers=6) as pool:
        responses=list(pool.map(lambda n:(coordinator if n%2 else other).request(),range(6)))
    assert started.wait(1) and len(calls)==1
    assert len({row['job_id'] for row in responses})==1
    assert all(row['status']=='running' for row in responses)
    done.set()
    assert store.lock.acquire(timeout=2);store.lock.release()


def test_minimum_interval_and_failure_retry_are_backend_owned(monkeypatch):
    monkeypatch.setenv('OVERVIEW_REFRESH_INTERVAL_SECONDS','10')
    monkeypatch.setenv('OVERVIEW_REFRESH_RETRY_SECONDS','20')
    now=[NOW];store=MemoryStore();calls=[]
    def runner(store, previous, started, interval, retry):
        calls.append(started)
        if len(calls)==1: raise RuntimeError('private provider detail')
        store.update({'status':'complete','next_check_at':started+timedelta(seconds=interval)})
    coordinator=refresh.RefreshCoordinator(store,runner,lambda:now[0],lambda fn:fn())
    coordinator.request()
    assert store.state['status']=='error' and store.state['publication_id']=='stored'
    assert store.state['next_check_at']==NOW+timedelta(seconds=20)
    now[0]+=timedelta(seconds=19);coordinator.request();assert len(calls)==1
    now[0]+=timedelta(seconds=1);coordinator.request();assert len(calls)==2
    coordinator.request();assert len(calls)==2
    assert 'private' not in str(coordinator.status())


def test_interrupted_worker_preserves_publication_and_backs_off(monkeypatch):
    store=MemoryStore();store.state.update(status='running',job_id='old')
    coordinator=refresh.RefreshCoordinator(store,clock=lambda:NOW)
    status=coordinator.status()
    assert status['status']=='error' and status['publication_id']=='stored'
    assert status['results'][0]['error_code']=='refresh_interrupted'
    assert datetime.fromisoformat(status['next_check_at'])>NOW


def test_shared_connection_does_not_commit_close_or_rollback_early(monkeypatch):
    calls=[]
    class Connection:
        def commit(self):calls.append('commit')
        def rollback(self):calls.append('rollback')
        def close(self):calls.append('close')
    physical=Connection();outside=Connection()
    monkeypatch.setattr(connections,'get_independent_connection',lambda:outside)
    with connections.shared_connection(physical):
        borrowed=connections.get_connection()
        assert borrowed.connection is physical
        borrowed.commit();borrowed.rollback();borrowed.close()
        assert not calls
    assert connections.get_connection() is outside


@pytest.mark.parametrize('revision,new_period',[(False,False),(True,False),(False,True)])
def test_fred_check_handles_no_new_data_revisions_and_new_periods(monkeypatch,revision,new_period,isolated_provenance):
    from app.ingestion import ingest_series
    from app.analytics import compute_features
    values={date(2026,7,1):100.,date(2026,8,1):110.,date(2026,9,1):120.}
    previous={'last_updated':'old','local_signature':['stored'],'transformations':['level','mom','yoy','moving_average_3m']}
    local={'start':'2026-07-01','signature':['stored']}
    updated=revision or new_period
    monkeypatch.setattr(fred,'fetch_series_metadata',lambda sid:{'id':sid,'last_updated':'new' if updated else 'old'})
    calls=[]
    def fetched(sid,observation_start=None):
        calls.append(observation_start)
        if revision:values[date(2026,8,1)]=115.
        if new_period:values[date(2026,10,1)]=125.
        return {'observations':list(values)}
    monkeypatch.setattr(fred,'fetch_series_observations',fetched)
    monkeypatch.setattr(ingest_series,'_ingest_series',lambda sid,response_data=None:None)
    monkeypatch.setattr(refresh,'inventory',lambda c,s:{'HOUST':{'signature':['updated']}})
    computed=[]
    def compute(sid,preserve_history=False):
        assert preserve_history
        computed.append(calculate_features(sid,pd.DataFrame([{'observation_date':d,'value':v} for d,v in values.items()]),['level','mom']))
    monkeypatch.setattr(compute_features,'compute_features',compute)
    _,result=refresh.refresh_fred('HOUST',previous,local,None,NOW)
    assert result['status']=='success' and result['outcome']==('updated' if updated else 'unchanged')
    assert bool(computed)==updated and calls==(['2026-07-01'] if updated else [])
    if revision:
        september=computed[0][(computed[0].observation_date==date(2026,9,1))&(computed[0].feature_name=='mom')]
        assert september.iloc[0].feature_value==pytest.approx((120/115-1)*100)
    recorded=next(iter(isolated_provenance.values()))
    assert recorded['status']=='success'
    assert recorded['scope']['observation_fetch_status']==('fetched' if updated else 'metadata_unchanged')


def test_source_failure_records_error_without_overwriting_last_success(monkeypatch,isolated_provenance):
    previous=dict(id='previous',resource='fred:HOUST',attempted_at=NOW-timedelta(days=1),finished_at=NOW-timedelta(days=1),status='success',scope={},error_code=None)
    isolated_provenance['previous']=previous
    def fail(sid):raise RuntimeError('private key')
    monkeypatch.setattr(fred,'fetch_series_metadata',fail)
    with pytest.raises(RuntimeError):refresh.refresh_fred('HOUST',{}, {},None,NOW)
    assert isolated_provenance['previous']==previous
    assert any(row['status']=='error' for row in isolated_provenance.values())


def listing():
    return '''<h1>News from Institute for Supply Management</h1>
      <a href="/news-releases/manufacturing-september.html">September 2026 ISM Manufacturing PMI Report</a>
      <a href="/news-releases/services-september.html">September 2026 ISM Services PMI Report</a>
      <a href="/news-releases/manufacturing-august.html">August 2026 ISM Manufacturing PMI Report</a>'''


def test_ism_discovery_identifies_latest_period_and_kind_not_a_fixed_old_url():
    found=discover_ism.discover(listing())
    assert set(found)=={'manufacturing','services'}
    assert found['manufacturing'][0]==date(2026,9,1)
    with pytest.raises(ValueError):discover_ism.discover('<h1>Challenge page</h1>')
    with pytest.raises(ValueError):discover_ism.discover(listing().replace('Services PMI Report','Unrelated report'))


def test_older_discovered_ism_report_cannot_replace_newer_document(monkeypatch):
    from app.ingestion import import_ism
    class Connection:
        def cursor(self):return self
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,*args):pass
        def fetchone(self):return (date(2026,9,1),NOW)
        def close(self):pass
    monkeypatch.setattr(discover_ism,'get_connection',Connection)
    monkeypatch.setattr(import_ism,'fetch_report',lambda url,kind:({'report_month':date(2026,8,1),'series_id':'ISM_MANUFACTURING_PMI','published_at':NOW-timedelta(days=30)},b'old'))
    monkeypatch.setattr(import_ism,'store_report',lambda *args:pytest.fail('Older document must not be stored'))
    with pytest.raises(ValueError):discover_ism.import_discovered('manufacturing',(date(2026,8,1),'https://www.prnewswire.com/news-releases/old.html'))


def test_fred_current_snapshot_paginates_and_keeps_requested_history_start(monkeypatch):
    calls=[]
    def fetch(path,params):
        calls.append(dict(params));offset=params['offset']
        return {'count':3,'offset':offset,'observations':[{'date':str(i)} for i in range(offset,min(offset+2,3))]}
    monkeypatch.setattr(fred,'_fetch',fetch)
    result=fred.fetch_series_observations('HOUST',date(1990,1,1))
    assert len(result['observations'])==3 and [p['offset'] for p in calls]==[0,2]
    assert all(p['observation_start']=='1990-01-01' for p in calls)


def test_refresh_api_does_not_run_provider_in_request_thread(monkeypatch):
    class Coordinator:
        def request(self):return {'status':'running','job_id':'shared'}
        def status(self):return {'status':'partial','job_id':'shared','results':[{'resource':'ism:services','status':'error'}]}
    monkeypatch.setattr(refresh,'coordinator',Coordinator())
    client=TestClient(app)
    assert client.post('/api/v1/economy/us/brief/refresh').json()['job_id']=='shared'
    assert client.get('/api/v1/economy/us/brief/refresh').json()['status']=='partial'
    preflight=client.options('/api/v1/economy/us/brief/refresh',headers={'Origin':'http://127.0.0.1:5173','Access-Control-Request-Method':'POST'})
    assert preflight.status_code==200


def test_chart_history_uses_published_revision_not_mutating_live_tables(monkeypatch):
    class Store:
        def publication(self,revision,key):
            assert revision=='old' and key=='HOUST:level'
            return ('old',{'observations':[{'observation_date':'2026-08-01','value':100},{'observation_date':'2026-09-01','value':110}]})
    class Coordinator:store=Store()
    monkeypatch.setattr(refresh,'coordinator',Coordinator())
    chart=refresh.read_chart('old','HOUST:level',date(2026,9,1))
    assert chart['data_revision']=='old' and chart['observations']==[{'observation_date':'2026-09-01','value':110}]

def test_budget_throttles_fred_and_stops_requests_at_deadline(monkeypatch):
    from app.ingestion import request_budget as budget
    now=[100.0];waits=[]
    monkeypatch.setattr(budget.time,'monotonic',lambda:now[0])
    def sleep(seconds):waits.append(seconds);now[0]+=seconds
    monkeypatch.setattr(budget.time,'sleep',sleep)
    with budget.request_budget(2,fred_spacing=.6):
        budget.before_request('FRED');budget.before_request('FRED')
        assert waits==pytest.approx([.6])
        now[0]=102
        with pytest.raises(TimeoutError):budget.before_request('ISM')
    budget.before_request('FRED')  # Existing explicit pipelines are unaffected.


def test_failed_source_uses_savepoint_and_partial_job_keeps_successful_sources(monkeypatch):
    from contextlib import contextmanager
    from app.ingestion import sync_release_calendar, sync_fomc_calendar, import_ism
    calls=[]
    class Connection:
        @contextmanager
        def transaction(self):
            calls.append('savepoint')
            try:yield
            except Exception:calls.append('rollback');raise
            else:calls.append('release')
    monkeypatch.setattr(refresh,'FRED_SERIES',{'A','B'})
    monkeypatch.setattr(refresh,'inventory',lambda *args:{})
    def fred_source(sid,*args):
        calls.append(sid)
        if sid=='A':raise ValueError('provider unavailable')
        return {'version':'new'},{'resource':'fred:B','status':'success','outcome':'updated'}
    monkeypatch.setattr(refresh,'refresh_fred',fred_source)
    previous={key:{'attempted_at':NOW.isoformat()} for key in ['fred:calendar','fed:calendar',*['ism:'+sid for sid in import_ism.KINDS.values()]]}
    versions,results=refresh.refresh_sources(Connection(),previous,NOW)
    assert calls[:6]==['savepoint','A','rollback','savepoint','B','release']
    assert versions['fred:B']=={'version':'new'} and 'fred:A' not in versions
    by_resource={row['resource']:row for row in results}
    assert by_resource['fred:A']['status']=='error' and by_resource['fred:B']['status']=='success'


def test_rate_limit_stops_further_fred_requests_and_calendar(monkeypatch):
    from contextlib import nullcontext
    from app.ingestion import import_ism
    class Connection:
        def transaction(self):return nullcontext()
    monkeypatch.setattr(refresh,'FRED_SERIES',{'A','B'})
    monkeypatch.setattr(refresh,'inventory',lambda *args:{})
    calls=[]
    def limited(sid,*args):calls.append(sid);raise RuntimeError('FRED HTTP 429')
    monkeypatch.setattr(refresh,'refresh_fred',limited)
    previous={key:{'attempted_at':NOW.isoformat()} for key in ['fed:calendar',*['ism:'+sid for sid in import_ism.KINDS.values()]]}
    _,results=refresh.refresh_sources(Connection(),previous,NOW)
    assert calls==['A']
    skipped={r['resource'] for r in results if r['status']=='skipped'}
    assert skipped=={'fred:B','fred:calendar'}


def test_requested_calendar_scope_is_fetched_even_inside_cache_interval(monkeypatch):
    from contextlib import nullcontext
    from app.ingestion import sync_release_calendar,import_ism,sync_calendar_periods
    from app.database import sync_series
    from app.analytics import release_calendar
    class Connection:
        def transaction(self):return nullcontext()
    monkeypatch.setattr(refresh,'FRED_SERIES',set())
    monkeypatch.setattr(refresh,'inventory',lambda *a:{})
    monkeypatch.setattr(sync_series,'load_series_config',lambda:{})
    calls=[]
    monkeypatch.setattr(sync_release_calendar,'sync_release_calendar',lambda start,end,series:calls.append((start,end)))
    monkeypatch.setattr(release_calendar,'list_calendar_events',lambda *a:{'events':[]})
    monkeypatch.setattr(sync_calendar_periods,'sync_periods',lambda *a:{'checks':[]})
    prior={key:{'attempted_at':NOW.isoformat()} for key in ['fred:calendar','fed:calendar',*['ism:'+sid for sid in import_ism.KINDS.values()]]}
    prior['fred:calendar'].update(start_date='2026-10-01',end_date='2026-12-31')
    prior['calendar_requested_window']={'start_date':'2026-09-01','end_date':'2026-09-07'}
    versions,results=refresh.refresh_sources(Connection(),prior,NOW)
    assert calls==[(date(2026,9,1),date(2026,9,7))]
    assert versions['fred:calendar']['start_date']=='2026-09-01'
    calls.clear()
    refresh.refresh_sources(Connection(),versions,NOW)
    assert calls==[]
