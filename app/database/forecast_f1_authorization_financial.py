"""Explicit V5 financial-projection revision; one INSERT, no startup upgrade."""
import argparse,json
from pathlib import Path
from uuid import uuid5,NAMESPACE_URL
from psycopg import sql
from psycopg.types.json import Jsonb
from app import forecast_f1 as model
from app.database import forecast_f1_authorization_cpi as v4

SOURCE='activation-financial-projection-revision'
PREDECESSOR_SHA='ebfe454621a598db1745690e1d94b0d35227add8916f2823a35f9595280e689c'
PREDECESSOR_ARTIFACTS_SHA='90af2f8758569aa1ac0667855827b0b67167313ea21ec0f4cc05073cf0c23cbb'
CONDITIONS=dict(version=5,ddl=False,writes='one append-only forecast_refresh_checks authorization revision',
 scope='five reviewed historical financial publication bindings only',data_import=False,
 dispatch='unchanged',cpi_and_employment_policy='unchanged including shared BLS budget',
 runtime='explicit separately verified V5 token; no automatic upgrade')
DELIVERY_PATHS=('.gitattributes', 'app/analytics/calendar_readings.py', 'app/analytics/release_times.py', 'app/bls_employment_runtime.py', 'app/cpi_runtime.py', 'app/database/activate_forecast_f1.py', 'app/database/forecast_f1_authorization_bls.py', 'app/database/forecast_f1_authorization_cpi.py', 'app/database/forecast_f1_authorization_financial.py', 'app/database/install_financial_reviewed.py', 'app/forecast_f1_runtime.py', 'app/ingestion/bls_employment.py', 'config/calendar_period_evidence.json', 'config/forecast_f1_runtime_manifest_v2.json', 'frontend/src/api/macrolens.ts', 'frontend/src/calendar/FinancialProjection.test.tsx', 'frontend/src/calendar/calendarComparisons.ts', 'tests/fixtures/financial_publication_columns.json', 'tests/postgres_financial_projection_authorization_validation.py', 'tests/test_calendar_financial_readings.py', 'tests/test_financial_projection_authorization.py')

def own_clone(target):
 return target['host'] in ('localhost','127.0.0.1') and target['port']!=5432 and target['user']=='macrolens_ci' and target['database'].startswith('macrolens_forecast_f1_ui_')

def predecessor(c):
 rows=c.execute('SELECT check_id,outcome,detail FROM forecast_refresh_checks WHERE source_id=%s',(v4.SOURCE,)).fetchall()
 if len(rows)!=1:raise ValueError('Exactly one approved V4 predecessor required')
 identifier,outcome,detail=rows[0];p=detail['plan']
 if (outcome!='success' or set(detail)!={'plan','plan_sha256'} or detail['plan_sha256']!=PREDECESSOR_SHA
  or model.digest(p)!=PREDECESSOR_SHA or p['version']!=4 or p['test_only'] or not p['ready_for_apply']
  or str(identifier)!=str(uuid5(NAMESPACE_URL,'f1-cpi-upgrade:'+PREDECESSOR_SHA))
  or model.digest(p['artifacts'])!=PREDECESSOR_ARTIFACTS_SHA or p['conditions']!=v4.CONDITIONS):raise ValueError('Historical V4 plan/identity changed')
 if p['predecessor']!=v4.predecessor(c):raise ValueError('V1-V4 chain changed')
 if (p['schema']!=v4.v3.legacy.schema_state(c) or p['references']!=v4.v3.legacy.reference_data(c)
  or p['dispatch']!=v4.v3.legacy.policy()):raise ValueError('Historical schema/references/policy changed')
 from app.ingestion.bls_cpi import POLICY
 if p['cpi_policy']!=json.loads(json.dumps(POLICY)):raise ValueError('CPI policy changed')
 v4.validate_seed(c,p['seed'])
 seed=p['seed'];stored=c.execute('SELECT raw_hash,metadata FROM publisher_documents WHERE id=%s',(seed['id'],)).fetchone()
 if stored!=(seed['raw_hash'],seed['metadata']):raise ValueError('Historical CPI seed changed')
 return detail

def revision(c):return c.execute('SELECT check_id,outcome,detail FROM forecast_refresh_checks WHERE source_id=%s',(SOURCE,)).fetchall()

def validate_delivery(delivery):
 if [d.get('path') for d in delivery]!=list(DELIVERY_PATHS):raise ValueError('Exact reviewed delivery paths required')
 for d in delivery:
  if set(d)!={'path','before','after'} or v4.v3.base.file_hash(v4.v3.old.ROOT/d['path'])!=d['after']:raise ValueError('Delivery bytes changed')
  if d['before'] is not None and (len(d['before'])!=64 or any(ch not in '0123456789abcdef' for ch in d['before'])):raise ValueError('Invalid predecessor file hash')

def check(c,p):
 keys={'version','ready_for_apply','test_only','target','predecessor','artifacts','manifest','schema','references','dispatch','cpi_policy','bls_policy','protected','delivery','conditions','backup'}
 if set(p)!=keys or p['version']!=5 or p['conditions']!=CONDITIONS:raise ValueError('Invalid financial projection plan')
 if p['test_only']:
  if not own_clone(p['target']) or p['ready_for_apply'] is not False:raise ValueError('Test-only authorization needs an owned clone')
 elif p['ready_for_apply'] is not True or p['target']!=p['predecessor']['plan']['target']:raise ValueError('Production plan must identify approved normal target')
 if not 170000<=c.info.server_version<180000 or v4.v3.base.target_identity(c)!=p['target']:raise ValueError('Exact PG17 target required')
 if p['predecessor']!=predecessor(c):raise ValueError('V4 predecessor changed')
 if p['artifacts']!=v4.v3.old.artifacts() or p['manifest']!=v4.v3.old.spec():raise ValueError('Frozen financial runtime bytes changed')
 from app.ingestion.bls_cpi import POLICY as CPI
 from app.ingestion.bls_employment import POLICY as BLS
 if p['cpi_policy']!=json.loads(json.dumps(CPI)) or p['bls_policy']!=json.loads(json.dumps(BLS)):raise ValueError('Source policy changed')
 if (p['schema']!=v4.v3.legacy.schema_state(c) or p['references']!=v4.v3.legacy.reference_data(c)
  or p['dispatch']!=v4.v3.legacy.policy() or p['backup']['target']!=p['target']):raise ValueError('Schema/reference/dispatch/backup identity changed')

def prepare(c,delivery,backup,test_only=False):
 from app.ingestion.bls_cpi import POLICY as CPI
 from app.ingestion.bls_employment import POLICY as BLS
 with c.transaction():
  c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
  p=dict(version=5,ready_for_apply=not test_only,test_only=test_only,target=v4.v3.base.target_identity(c),predecessor=predecessor(c),
   artifacts=v4.v3.old.artifacts(),manifest=v4.v3.old.spec(),schema=v4.v3.legacy.schema_state(c),references=v4.v3.legacy.reference_data(c),
   dispatch=v4.v3.legacy.policy(),cpi_policy=json.loads(json.dumps(CPI)),bls_policy=json.loads(json.dumps(BLS)),
   protected=v4.v3.financial.table_snapshots(c,('forecast_vintages','forecast_freezes')),delivery=delivery,conditions=CONDITIONS,backup=backup)
  validate_delivery(delivery);check(c,p);v4.v3.financial.check_backup(backup,p['target'])
  if any(backup['source_snapshots'].get(t)!=v for t,v in p['protected'].items()):raise ValueError('Forecast snapshot differs from fresh restored backup')
  if revision(c):raise ValueError('V5 already exists; verify exact plan, never silently prepare replacement')
 return p

def token_for(p):return dict(version=5,plan_sha256=model.digest(p),target=p['target'],artifacts=p['artifacts'])

def authorized(c,t,check_schema=True):
 if set(t)!={'version','plan_sha256','target','artifacts'} or t['version']!=5:raise ValueError('Separate V5 token required')
 rows=revision(c)
 if len(rows)!=1:raise ValueError('Exactly one V5 revision required')
 identifier,outcome,detail=rows[0];p=detail['plan'];h=model.digest(p)
 if set(detail)!={'plan','plan_sha256'} or outcome!='success' or detail['plan_sha256']!=h or t!=token_for(p) or str(identifier)!=str(uuid5(NAMESPACE_URL,'f1-financial-upgrade:'+h)):raise ValueError('Foreign V5 receipt/token')
 check(c,p);return p

def apply(c,p,target_confirmation,hash_confirmation,backup,fail_after_insert=False):
 if target_confirmation!=v4.v3.base.target_label(p['target']) or hash_confirmation!=model.digest(p):raise ValueError('Separate exact target and plan-hash approval required')
 if backup!=p['backup']:raise ValueError('Backup replaced after plan approval')
 v4.v3.financial.check_backup(backup,p['target']);validate_delivery(p['delivery'])
 with c.transaction():
  c.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ WRITE')
  c.execute("SET LOCAL lock_timeout='5s'");c.execute("SET LOCAL statement_timeout='120s'")
  check(c,p)
  for lock in (*v4.v3.LOCKS,726530022):
   if not c.execute('SELECT pg_try_advisory_xact_lock(%s)',(lock,)).fetchone()[0]:raise ValueError('Concurrent worker or upgrade')
  tables=(*v4.v3.legacy.REF_TABLES,*v4.v3.legacy.MACRO_REF_TABLES,'forecast_vintages','forecast_freezes')
  c.execute(sql.SQL('LOCK TABLE {} IN SHARE MODE').format(sql.SQL(',').join(sql.Identifier(t) for t in tables)))
  c.execute('LOCK TABLE forecast_refresh_checks IN SHARE ROW EXCLUSIVE MODE');check(c,p)
  if revision(c):authorized(c,token_for(p));return dict(outcome='already_initialized',plan_sha256=hash_confirmation)
  if v4.v3.financial.table_snapshots(c,('forecast_vintages','forecast_freezes'))!=p['protected']:raise ValueError('Forecasts/freezes changed since plan')
  c.execute("INSERT INTO forecast_refresh_checks(check_id,source_id,outcome,retry_at,detail) VALUES(%s,%s,'success','2099-01-01',%s)",
   (uuid5(NAMESPACE_URL,'f1-financial-upgrade:'+hash_confirmation),SOURCE,Jsonb(dict(plan=p,plan_sha256=hash_confirmation))))
  if fail_after_insert:c.execute('SELECT 1/0')
  authorized(c,token_for(p))
 return dict(outcome='created',plan_sha256=hash_confirmation)

def verify(c,p):
 with c.transaction():
  c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');authorized(c,token_for(p))
  if v4.v3.financial.table_snapshots(c,('forecast_vintages','forecast_freezes'))!=p['protected']:raise ValueError('Forecasts/freezes changed during cutover')
 return dict(outcome='verified',plan_sha256=model.digest(p),runtime_token=token_for(p))

def main():
 from app.database.connection import get_independent_connection
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['prepare','plan','apply','verify'])
 for name in ('plan','delivery','backup','out'):parser.add_argument('--'+name,type=Path)
 parser.add_argument('--confirm-target');parser.add_argument('--confirm-plan');a=parser.parse_args()
 if not a.out or a.out.exists():raise ValueError('New output path required')
 read=lambda p:json.loads(p.read_text(encoding='utf-8'))
 with get_independent_connection() as c:
  c.read_only=a.command!='apply'
  if a.command=='prepare':result=prepare(c,read(a.delivery),read(a.backup))
  else:
   p=read(a.plan)
   if a.command=='plan':
    result=prepare(c,p['delivery'],read(a.backup),p['test_only'])
    if result!=p:raise ValueError('Immutable plan changed; stop, do not adapt')
   elif a.command=='apply':result=apply(c,p,a.confirm_target,a.confirm_plan,read(a.backup))
   else:result=verify(c,p)
 with a.out.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
 print(model.digest(result) if a.command in ('prepare','plan') else result['outcome'])

if __name__=='__main__':main()
