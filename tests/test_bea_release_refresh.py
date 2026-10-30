"""Publication clocks, bounded durable claims and isolated narrow jobs, offline."""
import copy
from datetime import datetime,timedelta,timezone
from threading import Event
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from zoneinfo import ZoneInfo
import httpx
import pytest
from app.analytics import bea_release_refresh as policy,overview_refresh as refresh
from app.ingestion import sync_bea_reports as source
from tests.test_bea_direct import PROOF,P_PROOF,gdp,pio
from tests.test_overview_refresh import MemoryStore

T=datetime(2026,10,29,12,30,tzinfo=timezone.utc)
def entry(proof=PROOF):return policy.event({**proof,'source_url':source.SCHEDULE,'source_timezone':'America/New_York'})
def context():return {'events':[entry(),entry(P_PROOF)],'data':{'documents':[],'observations':{}}}
def control(standard=None):return {'standard_next_at':(standard or T+timedelta(minutes=15)).isoformat(),'events':{}}
def data_for(item,body,stamp=T):
    meta=source.parse_report(body,item,'https://www.bea.gov/news/2026/synthetic',stamp.isoformat())
    doc=dict(id='doc'+str(item['release_id']),kind=meta['identity'],source_url=meta['source_url'],retrieved_at=stamp,raw_hash='a'*64,metadata=meta)
    return {'documents':[doc],'observations':{(source.storage_id(r['series_id'],r['feature_name'],item['estimate_stage']),item['reference_period']):dict(value=r['value'],document_id=doc['id'],publication_document_id=doc['id'],vintage_date=str(stamp.date())) for r in meta['readings']}}
def merge(*states):return {'documents':sum((s['documents'] for s in states),[]),'observations':{k:v for s in states for k,v in s['observations'].items()}}

@pytest.mark.parametrize('day,stage,period,pl',[
 ('2026-10-29','advance','2026-07-01','13:30'),('2026-11-25','second','2026-07-01','14:30'),('2026-12-23','third','2026-07-01','14:30')])
def test_control_dates_and_stages_use_iana(day,stage,period,pl):
    p=entry({**PROOF,'release_date':day,'estimate_stage':stage,'reference_period':period})
    assert policy.instant(p['scheduled_at']).astimezone(ZoneInfo('Europe/Warsaw')).strftime('%H:%M')==pl
    assert stage in p['id'] and day in p['id']

def test_unlinked_future_row_still_proves_its_own_clock_without_a_report_url():
    import re
    from tests.test_bea_direct import schedule
    body=re.sub(r'<a href="[^"]+">(.*?)</a>',r'\1',schedule()).replace('October 29','November 25').replace('Advance Estimate','Second Estimate').replace('September 2026','October 2026')
    rows=source.discover(body,T.isoformat())
    assert len(rows)==2 and all(not p.get('report_url') for p in rows)
    assert all(p['scheduled_at']=='2026-11-25T13:30:00+00:00' for p in policy.canonical(rows))

def test_conflicting_clocks_on_unlinked_future_rows_are_not_chosen_arbitrarily():
    import re
    from tests.test_bea_direct import schedule
    body=re.sub(r'<a href="[^"]+">(.*?)</a>',r'\1',schedule())
    duplicate='<tr><td>October 29 9:30 AM</td><td>News</td><td>GDP (Advance Estimate), 3rd Quarter 2026</td></tr>'
    with pytest.raises(ValueError):source.discover(body.replace('</table>',duplicate+'</table>'),T.isoformat())

@pytest.mark.parametrize('field,value',[('source_url','https://example.test/schedule'),('source_timezone','UTC'),('release_time',None),('release_time','08:30:00+03:00'),('reference_period','2026-02-01')])
def test_unconfirmed_schedule_does_not_create_a_short_window(field,value):
    p={**PROOF,'source_url':source.SCHEDULE,'source_timezone':'America/New_York',field:value}
    assert policy.canonical([p])==[]

@pytest.mark.parametrize('seconds',[-300,-1,0,119,120,299,300,599,600,1199,1200,1799,1800,1801])
def test_window_has_no_prepublication_or_postexpiry_attempt(seconds):
    result=policy.plan(context(),control(),T+timedelta(seconds=seconds))
    assert bool(result['due'])==(0<=seconds<1800)

def test_five_opportunities_and_no_replay_of_missed_slots():
    versions={policy.KEY:control()};ctx=context()
    for i,offset in enumerate(policy.SLOTS):
        now=T+timedelta(seconds=offset)
        assert len(policy.plan(ctx,versions[policy.KEY],now)['due'])==2
        versions=policy.claim(versions,ctx,now,T+timedelta(hours=1),'bea_release_aware')
        assert all(r['attempts']==i+1 for r in versions[policy.KEY]['events'].values())
        assert not policy.plan(ctx,versions[policy.KEY],now)['due']
    assert all(r['status']=='attempt_limit' for r in policy.plan(ctx,versions[policy.KEY],T+timedelta(minutes=25))['checks'])
    late=policy.claim({policy.KEY:control()},ctx,T+timedelta(minutes=7),T+timedelta(hours=1),'bea_release_aware')
    assert all(r['attempts']==1 and r['slot']==2 for r in late[policy.KEY]['events'].values())
    assert policy.plan(ctx,late[policy.KEY],T+timedelta(minutes=7))['next_check_at']==T+timedelta(minutes=10)

def test_a_fresh_install_can_discover_bea_in_a_standard_job():
    ctx={'events':[],'data':{'documents':[],'observations':{}}}
    versions=policy.claim({},ctx,T,T,'standard')
    assert versions['_bea_selection'] is None
    assert versions[policy.KEY]['events']=={}

def test_partial_pio_keeps_its_own_attempts_after_gdp_confirmation():
    ctx=context();ctx['data']=merge(data_for(entry(),gdp()),data_for(entry(P_PROOF),pio().replace('Excluding food and energy, the PCE price index increased','Other prices increased')))
    decision=policy.plan(ctx,control(),T)
    assert [p['release_id'] for p in decision['due']]==[54]
    assert decision['checks'][0]['status']=='confirmed'
    assert decision['checks'][1]['confirmed_measures']==5
    ctx['data']=merge(data_for(entry(),gdp()),data_for(entry(P_PROOF),pio()))
    assert not policy.plan(ctx,control(),T)['due']

def test_changed_or_conflicting_official_time_cannot_reuse_old_claim():
    a=entry();later=entry({**PROOF,'release_time':'10:00:00'})
    assert policy.canonical([a,later])==[]
    assert later['id']!=a['id']
    old=policy.claim({policy.KEY:control()},context(),T,T+timedelta(hours=1),'bea_release_aware')
    ctx={'events':[later],'data':{'documents':[],'observations':{}}}
    assert not policy.plan(ctx,old[policy.KEY],T)['due']
    assert policy.plan(ctx,old[policy.KEY],policy.instant(later['scheduled_at']))['due']==[later]

def test_new_etag_or_receipt_without_sql_does_not_confirm_a_report():
    ctx=context();ctx['data']=data_for(entry(),gdp());ctx['data']['observations']={}
    assert policy.plan(ctx,control(),T)['checks'][0]['status']=='due'

@pytest.mark.parametrize('status,header,expected',[(429,None,900),(429,'120',120),(503,'300',300),(404,None,None),(500,None,None),(503,None,None),(429,'invalid',900),(503,'invalid',None),(429,'-5',900),(429,'999999999999999999999',900),(429,'Thu, 29 Oct 2026 12:35:00 GMT',300)])
def test_provider_backoff(status,header,expected):
    r=httpx.Response(status,headers={'Retry-After':header} if header else {},request=httpx.Request('GET',source.SCHEDULE))
    error=httpx.HTTPStatusError('synthetic',request=r.request,response=r)
    value=source.backoff_from_error(error,T)
    assert value==((T+timedelta(seconds=expected)).isoformat() if expected is not None else None)

def test_backoff_beyond_window_ends_narrow_checks_without_erasing_full_cadence():
    ctl=control();ctl['backoff_until']=(T+timedelta(hours=1)).isoformat()
    p=policy.plan(context(),ctl,T)
    assert not p['due'] and p['next_check_at'] is None
    state=dict(status='partial',source_versions={policy.KEY:ctl},next_check_at=T,completed_at=T)
    assert policy.decorate(state,context(),T,900,900)['next_check_at']==T+timedelta(minutes=15)

def test_transport_backoff_survives_loss_of_uncommitted_job_state():
    ctx=context();ctx['backoff_until']=(T+timedelta(minutes=8)).isoformat()
    assert not policy.plan(ctx,control(),T)['due']
    versions=policy.claim({},ctx,T,T,'standard')
    assert versions['_bea_selection']==[] and versions[policy.KEY]['backoff_until']==ctx['backoff_until']

def test_a_check_already_due_after_a_slow_job_gets_a_future_ui_deadline():
    state=dict(status='partial',source_versions={policy.KEY:control()},next_check_at=T,completed_at=T)
    assert policy.decorate(state,context(),T,900,900)['next_check_at']==T+timedelta(seconds=5)
    assert policy.decorate(state,context(),T,900,900,busy=True)['next_check_at']==T+timedelta(seconds=30)

class Store(MemoryStore):
    def __init__(self):
        super().__init__();self.ctx=context()
        self.state.update(status='complete',completed_at=T-timedelta(minutes=5),next_check_at=T+timedelta(minutes=10))
    def release_context(self):return copy.deepcopy(self.ctx)

def completed(store,previous,now,interval,retry):
    versions=policy.finish(previous['source_versions'],previous['source_versions'][policy.KEY]['mode'],now,interval,retry)
    store.update(dict(status='partial',completed_at=now,next_check_at=policy.instant(versions[policy.KEY]['standard_next_at']),source_versions=versions))

def test_narrow_job_runs_during_full_cooldown_without_moving_standard_deadline():
    store=Store();now=[T];calls=[]
    def narrow(*args):calls.append('bea');completed(*args)
    def full(*args):calls.append('full');completed(*args)
    coordinator=refresh.RefreshCoordinator(store,full,lambda:now[0],lambda f:f(),release_runner=narrow)
    coordinator.request();assert calls==['bea']
    assert coordinator.status()['standard_next_check_at']==(T+timedelta(minutes=10)).isoformat()
    assert coordinator.status()['next_check_at']==(T+timedelta(minutes=2)).isoformat()
    coordinator.request();assert calls==['bea']
    now[0]=T+timedelta(minutes=2);coordinator.request();assert calls==['bea','bea']
    now[0]=T+timedelta(minutes=10);coordinator.request();assert calls[-1]=='bea'
    now[0]+=timedelta(seconds=5);coordinator.request();assert calls[-1]=='full'

def test_due_bea_runs_before_an_also_due_full_job_to_avoid_its_batch_latency():
    store=Store();store.state.update(completed_at=None,next_check_at=T);now=[T];calls=[]
    def narrow(*args):calls.append('bea');completed(*args)
    def full(*args):calls.append('full');completed(*args)
    c=refresh.RefreshCoordinator(store,full,lambda:now[0],lambda f:f(),release_runner=narrow)
    c.request();assert calls==['bea'] and c.status()['standard_next_check_at']==T.isoformat()
    now[0]+=timedelta(seconds=5);c.request();assert calls==['bea','full']

def test_three_tabs_and_two_workers_share_one_reserved_attempt_and_lock():
    store=Store();work=[]
    a=refresh.RefreshCoordinator(store,clock=lambda:T,launch=work.append)
    b=refresh.RefreshCoordinator(store,clock=lambda:T,launch=work.append)
    with ThreadPoolExecutor(max_workers=3) as pool:responses=list(pool.map(lambda n:(a if n%2 else b).request(),range(3)))
    assert len(work)==1 and len({r['job_id'] for r in responses})==1
    assert all(v['attempts']==1 for v in store.state['source_versions'][policy.KEY]['events'].values())
    store.release(store.lock)

def test_crash_restart_keeps_reserved_attempt_and_does_not_replay_slot():
    store=Store();clock=[T];work=[]
    a=refresh.RefreshCoordinator(store,clock=lambda:clock[0],launch=work.append);a.request();store.release(store.lock)
    b=refresh.RefreshCoordinator(store,clock=lambda:clock[0],launch=work.append)
    assert b.status()['status']=='error'
    b.request();assert len(work)==1
    assert all(v['attempts']==1 for v in store.state['source_versions'][policy.KEY]['events'].values())
    clock[0]=T+timedelta(minutes=2);b.request();assert len(work)==2
    assert all(v['attempts']==2 for v in store.state['source_versions'][policy.KEY]['events'].values())
    store.release(store.lock)

def test_confirmed_document_stops_opportunities_and_normal_job_skips_it_in_window():
    store=Store();store.ctx['data']=merge(data_for(entry(),gdp()),data_for(entry(P_PROOF),pio()))
    coordinator=refresh.RefreshCoordinator(store,clock=lambda:T,launch=lambda f:pytest.fail('unexpected provider job'))
    assert all(c['status']=='confirmed' for c in coordinator.status()['bea_release_checks'])
    assert coordinator.request()['status']=='complete'
    versions=policy.claim({},store.ctx,T,T,'standard')
    assert versions['_bea_selection']==[]

def test_standard_jobs_can_still_check_later_revisions_after_the_short_window():
    ctx=context();ctx['data']=merge(data_for(entry(),gdp()),data_for(entry(P_PROOF),pio()))
    versions=policy.claim({},ctx,T+timedelta(minutes=31),T,'standard')
    assert len(versions['_bea_selection'])==2 and versions[policy.KEY]['events']=={}

def test_november_25_second_and_october_pio_sequence_keeps_advance_and_third_separate():
    from app.analytics import bea_direct
    release=datetime(2026,11,25,13,30,tzinfo=timezone.utc)
    second=entry({**PROOF,'release_date':'2026-11-25','estimate_stage':'second'})
    october=entry({**P_PROOF,'release_date':'2026-11-25','reference_period':'2026-10-01'})
    third=entry({**PROOF,'release_date':'2026-12-23','estimate_stage':'third'})
    store=Store();store.ctx={'events':[second,october,third],'data':data_for(entry(),gdp())}
    standard=release+timedelta(minutes=10)
    store.state.update(completed_at=release-timedelta(hours=1),next_check_at=standard)
    clock=[release-timedelta(minutes=10)];calls=[]
    def document(body):return body.replace('EDT, Thursday, October 29','EST, Wednesday, November 25')
    def narrow(store,previous,now,interval,retry):
        selected=previous['source_versions']['_bea_selection'];calls.append([p['release_id'] for p in selected])
        states=[store.ctx['data']]
        if now>=release+timedelta(minutes=2) and second in selected:
            states.append(data_for(second,document(gdp().replace('Advance Estimate','Second Estimate')),now))
        if now>=release+timedelta(minutes=5) and october in selected:
            states.append(data_for(october,document(pio().replace('September','October').replace('August','September')),now))
        store.ctx['data']=merge(*states);completed(store,previous,now,interval,retry)
    coordinator=refresh.RefreshCoordinator(store,runner=lambda *a:pytest.fail('unexpected full/FRED refresh'),clock=lambda:clock[0],launch=lambda fn:fn(),release_runner=narrow)
    for minutes in (-10,-1):
        clock[0]=release+timedelta(minutes=minutes);coordinator.request();assert not calls
    for minutes in (0,2,5):
        clock[0]=release+timedelta(minutes=minutes);coordinator.request()
        assert coordinator.status()['standard_next_check_at']==standard.isoformat()
        assert (policy.readings(second,store.ctx['data'],clock[0])[0][2] is not None)==(minutes>=2)
        assert sum(r[2] is not None for r in policy.readings(october,store.ctx['data'],clock[0]))==(6 if minutes==5 else 0)
    assert calls==[[53,54],[53,54],[54]]
    assert policy.readings(entry(),store.ctx['data'],clock[0])[0][2]==1.2
    assert policy.readings(third,store.ctx['data'],clock[0])[0][2] is None
    measure=dict(series_id='PCEPI',feature_name='mom',frequency='monthly',reference_period='2026-10-01',actual=None,previous=None)
    assert bea_direct.select(measure,october,store.ctx['data'],clock[0])['forecast'] is None
    clock[0]=release+timedelta(minutes=7);coordinator.request();assert len(calls)==3


@pytest.mark.parametrize('changed',[False,True,'metadata'])
def test_narrow_runner_only_calls_bea_and_publishes_on_semantic_change(monkeypatch,changed):
    class Connection:
        def transaction(self):return nullcontext()
        def cursor(self):return self
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def execute(self,*a):pass
        def close(self):pass
    store=Store()
    empty=context()['data'];confirmed=merge(data_for(entry(),gdp()),data_for(entry(P_PROOF),pio()))
    if changed=='metadata':
        empty=data_for(entry(P_PROOF),pio().replace('Excluding food and energy, the PCE price index increased','Other prices increased'))
        confirmed=copy.deepcopy(empty);confirmed['documents'][0].update(id='new-doc',raw_hash='b'*64,retrieved_at=T+timedelta(seconds=1))
        for p in confirmed['observations'].values():p.update(document_id='new-doc',publication_document_id='new-doc')
        store.ctx['data']=empty
    previous=store.read();previous['source_versions']=policy.claim({},store.ctx,T,T+timedelta(minutes=10),'bea_release_aware')
    states=iter([empty,confirmed if changed else empty]);calls=[]
    monkeypatch.setattr(refresh,'get_independent_connection',Connection)
    monkeypatch.setattr(policy.bea_direct,'load_state',lambda c:next(states))
    monkeypatch.setattr(refresh,'utc_now',lambda:T+timedelta(seconds=1))
    monkeypatch.setattr(refresh,'refresh_sources',lambda *a:pytest.fail('full source cycle in narrow mode'))
    monkeypatch.setattr(refresh,'refresh_bea',lambda *a,**k:calls.append('bea') or {'resource':'bea:reports','status':'success'})
    monkeypatch.setattr(refresh.economy_brief,'build_brief',lambda:{'source_checks':{'status':'partial'}})
    monkeypatch.setattr(refresh,'collect_histories',lambda *a:{})
    store.publish=lambda *a:calls.append('publish')
    refresh.run_bea_refresh(store,previous,T,900,900)
    assert calls==(['bea','publish'] if changed is True else ['bea'])
    assert policy.instant(store.state['source_versions'][policy.KEY]['standard_next_at'])==T+timedelta(minutes=10)
