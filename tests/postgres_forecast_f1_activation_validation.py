"""Full restored clone F1 activation validation; no normal apply.

F1_ACTIVATION_DIR supplies a fresh genuine backup/restore evidence. All negative
mutations and forced HTTP cases target only this owned loopback PG17 clone.
"""
import sys,os,json,subprocess,copy,re
from pathlib import Path
from uuid import uuid4
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
import psycopg
from psycopg import sql
from app.database import activate_forecast_f1 as a,activate_earnings as b,activate_earnings_financials as f
from app.database.connection import get_independent_connection
from tests.postgres_earnings_financial_activation_validation import make_backup
from app import forecast_f1 as model,earnings_reports as reports
raw=Path(os.environ['F1_ACTIVATION_DIR']).resolve()
container=os.environ['F1_TEST_CONTAINER']
if os.environ.get('DB_NAME')!='macrolens_f1_activation_control' or os.environ.get('DB_HOST') not in ('localhost','127.0.0.1'):raise ValueError('Owned F1 activation control/loopback required')
params=dict(host=os.environ['DB_HOST'],port=int(os.environ['DB_PORT']),user=os.environ['DB_USER'],password=os.environ['DB_PASSWORD'])
ci_service=(os.environ.get('GITHUB_ACTIONS')=='true' and re.fullmatch(r'[0-9a-f]{64}',container))
if params['user']!='macrolens_ci' or not (container.startswith('macrolens_reports_activation_f1_') or ci_service):raise ValueError('Owned CI role/container required')
normal=json.loads((raw/'normal-backup.json').read_text());name=model.PREFIX+'activation_'+uuid4().hex[:12]
with psycopg.connect(**params,dbname='postgres',autocommit=True) as admin:
 admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
 try:
  with open(normal['path'],'rb') as stream:r=subprocess.run(['docker','exec','-i',container,'pg_restore','-U','macrolens_ci','-d',name,'--exit-on-error','--single-transaction','--no-owner','--no-acl'],stdin=stream,capture_output=True)
  assert r.returncode==0,r.stderr
  factory=lambda:psycopg.connect(**params,dbname=name)
  with factory() as c:
   before=f.table_snapshots(c);assert before==normal['source_snapshots'];c.rollback();ref=a.reference(c);c.rollback();refs=a.reference_data(c);c.rollback()
  proof=dict(source_target=normal['target'],clone_target=None,backup_sha256=normal['sha256'],reference_data=refs,schema=ref['before'])
  with factory() as c:c.read_only=True;proof['clone_target']=b.target_identity(c)
  assert proof['clone_target']!=proof['source_target']
  path=raw/'normal-f1-reference-proof.json';path.write_text(json.dumps(proof,indent=2));normal['forecast_reference_proof']=dict(path=str(path.resolve()),sha256=b.file_hash(path));(raw/'normal-backup.json').write_text(json.dumps(normal,indent=2))
  (raw/'f1-schema-reference.json').write_text(json.dumps(ref,indent=2))
  # Normal prepare only. No reference DDL is ever executed on normal target.
  from dotenv import dotenv_values
  settings=dotenv_values(root/'.env')
  def normal_factory():
   if ci_service:
    source=os.environ['F1_SYNTHETIC_SOURCE']
    if not source.startswith('macrolens_earnings_e2b_e2c_e2d_e2e_ci_source_'):raise ValueError('Synthetic CI source required')
    c=psycopg.connect(**params,dbname=source);c.read_only=True;return c
   c=psycopg.connect(host='localhost',port=5432,user='macrolens',dbname='macrolens',password=settings['DB_PASSWORD']);c.read_only=True;return c
  with normal_factory() as c:plan=a.prepare(c,normal['target'],ref,normal)
  with normal_factory() as c:assert a.prepare(c,normal['target'],ref,normal)==plan
  (raw/'normal-plan.json').write_text(json.dumps(plan,indent=2));print('NORMAL PREPARE ONLY',model.digest(plan),flush=True)
  d=raw/('clone-backup-'+uuid4().hex[:8]);d.mkdir();backup=make_backup(factory,admin,name,container,d)
  path=raw/'clone-f1-reference-proof.json';path.write_text(json.dumps(dict(source_target=backup['target'],backup_sha256=backup['sha256'],reference_data=refs,schema=ref['before']),indent=2));backup['forecast_reference_proof']=dict(path=str(path.resolve()),sha256=b.file_hash(path))
  (raw/'clone-backup.json').write_text(json.dumps(backup,indent=2))
  with factory() as c:c.read_only=True;trial=a.prepare(c,backup['target'],ref,backup)
  assert all(trial[k]==plan[k] for k in plan if k not in ('target','target_label'))
  class FailImport:
   def __init__(self,c):self.c=c;self.count=0
   def __getattr__(self,k):return getattr(self.c,k)
   def execute(self,query,*args):
    if isinstance(query,str) and query.startswith('INSERT INTO forecast_vintages'):
     self.count+=1
     if self.count==10:return self.c.execute('SELECT 1/0')
    return self.c.execute(query,*args)
  with factory() as c:
   try:a.apply(FailImport(c),trial,trial['target_label'],model.digest(trial),backup)
   except psycopg.errors.DivisionByZero:pass
   else:raise AssertionError('DDL/seed rollback missing')
   assert f.table_snapshots(c)==before;c.rollback();assert c.execute("SELECT to_regclass('forecast_vintages')").fetchone()[0] is None;c.rollback()
  # Unrelated macro rows can change without changing the plan. Always rollback
  # this synthetic probe, so the complete 26 original tables remain identical.
  from psycopg.types.json import Jsonb
  with factory() as c:
   old_results=c.execute('SELECT results FROM overview_refresh_state WHERE id=1').fetchone()[0]
   c.execute("UPDATE overview_refresh_state SET results=results||'[{\"resource\":\"f1-probe\"}]'::jsonb WHERE id=1")
  try:
   with factory() as c:c.read_only=True;assert a.prepare(c,backup['target'],ref,backup)==trial
  finally:
   with factory() as c:c.execute('UPDATE overview_refresh_state SET results=%s WHERE id=1',(Jsonb(old_results),))
  # Relevant metadata or schema changes must STOP, unlike macro results.
  with factory() as c:
   prior_frequency=c.execute("SELECT frequency FROM series WHERE series_id='CPIAUCSL'").fetchone()[0]
   c.execute("UPDATE series SET frequency='quarterly' WHERE series_id='CPIAUCSL'")
  try:
   with factory() as c:
    try:a.apply(c,trial,trial['target_label'],model.digest(trial),backup)
    except ValueError:pass
    else:raise AssertionError('Changed reference accepted')
  finally:
   with factory() as c:c.execute("UPDATE series SET frequency=%s WHERE series_id='CPIAUCSL'",(prior_frequency,))
  with factory() as c:c.execute('CREATE INDEX f1_unreviewed_dependency ON series(category)')
  try:
   with factory() as c:
    try:a.apply(c,trial,trial['target_label'],model.digest(trial),backup)
    except ValueError:pass
    else:raise AssertionError('Changed schema accepted')
  finally:
   with factory() as c:c.execute('DROP INDEX f1_unreviewed_dependency')
  import time
  with factory() as blocker:
   blocker.execute('LOCK TABLE series IN ROW EXCLUSIVE MODE')
   started=time.monotonic()
   with factory() as c:
    try:a.apply(c,trial,trial['target_label'],model.digest(trial),backup)
    except psycopg.errors.LockNotAvailable:pass
    else:raise AssertionError('Lock timeout missing')
   assert 4.5<time.monotonic()-started<8
   blocker.rollback()
  class ConcurrentProbe:
   def __init__(self,c):self.c=c;self.probed=False
   def __getattr__(self,k):return getattr(self.c,k)
   def execute(self,query,*args):
    result=self.c.execute(query,*args)
    if not self.probed and not isinstance(query,str):
     self.probed=True
     with factory() as other:
      with other.transaction(force_rollback=True):
       other.execute("SET LOCAL statement_timeout='2s'")
       other.execute("UPDATE overview_refresh_state SET results=results||'[{\"resource\":\"f1-concurrent\"}]'::jsonb WHERE id=1")
       reports.import_records(other,json.loads(reports.DATA.read_text(encoding='utf-8')))
    return result
  with factory() as c:receipt=a.apply(ConcurrentProbe(c),trial,trial['target_label'],model.digest(trial),backup)
  with factory() as c:c.read_only=True;assert a.verify(c,trial,True)['outcome']=='verified';after=f.table_snapshots(c)
  assert len(after)==29 and all(after[t]==v for t,v in before.items())
  with factory() as c:repeat=a.apply(c,trial,trial['target_label'],model.digest(trial),backup)
  assert repeat['outcome']=='already_initialized'
  with factory() as c:assert f.table_snapshots(c)==after
  # Controlled worker restart, true SQL freeze and crash-before-HTTP result.
  from app import forecast_f1_refresh as refresh
  from app.forecast_f1_bindings import publication_events
  import httpx
  token=receipt['runtime_token']
  with factory() as c:
   baseline_worker=f.table_snapshots(c);c.rollback()
  from tests.postgres_http_guard import no_publisher_http
  with no_publisher_http():
   first=refresh.run(factory,raw/'worker-cache',authorization=token,events_loader=publication_events)
   assert first['status']=='cooldown' and first['added']==0
   with factory() as c:worker=f.table_snapshots(c)
   again=refresh.run(factory,raw/'worker-cache',authorization=token,events_loader=publication_events)
   assert again['added']==0 and again['frozen']==0
   with factory() as c:assert f.table_snapshots(c)==worker
  # Only F1 freezes changed; no old rows or new forecast vintages.
  assert all(worker[t]==baseline_worker[t] for t in baseline_worker if t!='forecast_freezes')
  def force_due():
   from uuid import uuid4
   with factory() as c:c.execute("INSERT INTO forecast_refresh_checks(check_id,source_id,outcome,retry_at,detail) VALUES(%s,'cleveland-inflation','not_modified',clock_timestamp()-interval '1 second','{\"kind\":\"owned_test_due\"}')",(uuid4(),))
  class Crash(BaseException):pass
  force_due();http_calls=[]
  def crash(request):http_calls.append(str(request.url));raise Crash()
  try:refresh.run(factory,raw/'worker-cache',authorization=token,transport=httpx.MockTransport(crash))
  except Crash:pass
  else:raise AssertionError('Crash not exercised')
  calls=len(http_calls)
  assert refresh.run(factory,raw/'worker-cache',authorization=token,transport=httpx.MockTransport(crash))['status']=='cooldown'
  assert len(http_calls)==calls
  # Appending identical values from a changed page shell is not a new vintage.
  with factory() as c:
   altered=copy.deepcopy(trial['ledger']['records'][0]);altered['source_sha256']='a'*64
   assert model.append(c,[altered])==0
  # Old initialize/append/dispatch guards are still strict on normal names.
  class NormalInfo:dbname='macrolens';server_version=170000
  class Normal:info=NormalInfo()
  for func,args in [(model.initialize,()),(model.append,([] ,))]:
   try:func(Normal(),*args)
   except ValueError:pass
   else:raise AssertionError('Legacy isolation guard weakened')
  (raw/'clone-receipt.json').write_text(json.dumps(receipt,indent=2));(raw/'clone-plan.json').write_text(json.dumps(trial,indent=2));(raw/'clone-database.json').write_text(json.dumps(dict(database=name,target=backup['target']),indent=2))
  (raw/'trial-results.json').write_text(json.dumps(dict(outcome='passed',rollback=True,idempotency=True,concurrent_macro_and_earnings_writer=True,old26_unchanged=True,before=before,after=after,normal_plan_hash=model.digest(plan)),indent=2))
  print('CLONE TRIAL PASSED',name,flush=True)
  # Keep only this owned clone for actual runtime/API/Chrome tests.
  (raw/'keep-clone').write_text(name)
 except BaseException:
  admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)));raise
