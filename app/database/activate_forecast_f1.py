"""Controlled F1 prepare/plan/apply/verify. Normal APPLY needs a NEW full hash."""
import argparse
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from uuid import uuid5,NAMESPACE_URL
from psycopg import sql
from psycopg.types.json import Jsonb
from app import forecast_f1 as f
from app.database import activate_earnings as base,activate_earnings_financials as financial
from app.database.connection import get_independent_connection

ROOT=Path(__file__).resolve().parents[2]
LEDGER=ROOT/'config/forecast_f1_activation_ledger.json'
POLICY=ROOT/'config/forecast_f1_dispatch_policy.json'
DDL=ROOT/'app/database/forecast_f1_schema.sql'
REF_TABLES=('earnings_companies','earnings_company_aliases','earnings_periods','earnings_events','earnings_date_confirmations','earnings_source_evidence')
MACRO_REF_TABLES=('series','release_dates','economic_releases')
CONDITIONS=dict(isolation='READ COMMITTED',locks=[726530032,726530031],lock_timeout='5s',statement_timeout='120s',reference_table_locks='SHARE on six Earnings and three macro-reference tables; no locks on observations/features/macro state, no macro lease726530019',seed_count=20,seed_kind_counts={'model_nowcast':16,'issuer_guidance':4},initial_checks=2,initial_freezes=0,apply_http=False,runtime='separate approved token after read-only verification',post_commit='no automatic restore or rollback',freeze='worker only; no retrospective knowledge')

def artifacts():
 import httpx,psycopg,pypdf
 paths=sorted({p for folder in ('app','config') for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ('.py','.sql','.json','.yaml','.yml') and '__pycache__' not in p.parts})
 front=sorted(str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'frontend/src').rglob('*') if p.is_file() and p.suffix in ('.ts','.tsx','.css'))
 front += [p for p in ('requirements.txt','frontend/package.json','frontend/package-lock.json') if (ROOT/p).exists()]
 return {**{str(p.relative_to(ROOT)).replace('\\','/'):base.file_hash(p) for p in paths},**{p:base.file_hash(ROOT/p) for p in front},'httpx_version':httpx.__version__,'psycopg_version':psycopg.__version__,'pypdf_version':pypdf.__version__}

def seed():
 ledger=json.loads(LEDGER.read_text(encoding='utf-8'));records=ledger['records']
 if len(records)!=20 or sum(r['kind']=='model_nowcast' for r in records)!=16 or sum(r['kind']=='issuer_guidance' for r in records)!=4 or len({f.digest(r) for r in records})!=20:raise ValueError('Exact reviewed twenty forecasts required')
 for r in records:f.validate(r)
 return records

def policy():return json.loads(POLICY.read_text(encoding='utf-8'))

def schema_state(c):
 # Full public definitions plus actual pg_depend closure: runtime PL/pgSQL
 # references are additionally explicit in REF_TABLES and reference_data.
 edges=c.execute("""WITH RECURSIVE roots(classid,objid,objsubid) AS (
 SELECT 'pg_class'::regclass::oid,c.oid,0 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'
 UNION SELECT 'pg_proc'::regclass::oid,p.oid,0 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'
 UNION SELECT 'pg_constraint'::regclass::oid,k.oid,0 FROM pg_constraint k JOIN pg_namespace n ON n.oid=k.connamespace WHERE n.nspname='public'
 UNION SELECT 'pg_trigger'::regclass::oid,t.oid,0 FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal
 ), closure(classid,objid,objsubid) AS (SELECT * FROM roots UNION SELECT d.refclassid,d.refobjid,d.refobjsubid FROM pg_depend d JOIN closure q ON d.classid=q.classid AND d.objid=q.objid)
 SELECT DISTINCT pg_describe_object(d.classid,d.objid,d.objsubid),pg_describe_object(d.refclassid,d.refobjid,d.refobjsubid),d.deptype FROM pg_depend d JOIN closure q ON d.classid=q.classid AND d.objid=q.objid ORDER BY 1,2,3""").fetchall()
 states=c.execute("""SELECT c.relname,t.tgname,t.tgenabled,t.tgisinternal FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY 1,2""").fetchall()
 indexes=c.execute("""SELECT c.relname,i.indisvalid,i.indisready,i.indislive FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY 1""").fetchall()
 return json.loads(json.dumps(dict(earnings=base.catalog(c,True),other=base.catalog(c,False),dependencies=edges,triggers=states,indexes=indexes)))

def reference_data(c):
 from app.forecast_f1_bindings import reference_data as read
 return read(c)

def reference(c):
 f.isolated(c);before=schema_state(c);c.rollback()
 with c.transaction(force_rollback=True):f.initialize(c);after=schema_state(c)
 return dict(before=before,after=after)

def check_backup(backup,plan):
 proof=financial.check_backup(backup,plan['target'])
 evidence=backup['forecast_reference_proof'];path=Path(evidence['path'])
 if base.file_hash(path)!=evidence['sha256']:raise ValueError('F1 backup reference evidence changed')
 ref=json.loads(path.read_text(encoding='utf-8'))
 if ref['source_target']!=plan['target'] or ref['backup_sha256']!=backup['sha256'] or ref['reference_data']!=plan['reference_data'] or ref['schema']!=plan['reference']['before']:raise ValueError('Backup reference data/schema differ')
 if any(proof['source_snapshots'][t]!=plan['reference_data']['earnings_tables'][t] for t in REF_TABLES):raise ValueError('Backup Earnings references changed')

def prepare(c,target,ref,backup):
 with c.transaction():
  c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
  if base.target_identity(c)!=target or not 170000<=c.info.server_version<180000:raise ValueError('Exact PG17 target required')
  if any(c.execute('SELECT to_regclass(%s)',(t,)).fetchone()[0] for t in f.TABLES):raise ValueError('F1 present/partial: use verify, never repair')
  state=schema_state(c)
  if state!=ref['before']:raise ValueError('Schema/reference closure changed')
  data=reference_data(c)
 result=dict(version=1,ready_for_apply=True,target=target,target_label=base.target_label(target),reference=ref,reference_data=data,ddl=dict(text=DDL.read_text(encoding='utf-8'),sha256=base.file_hash(DDL)),ledger=dict(records=seed(),sha256=base.file_hash(LEDGER),fingerprint=f.digest(seed())),artifacts=artifacts(),dispatch=policy(),conditions=CONDITIONS)
 check_backup(backup,result)
 return result

def frozen(plan):
 if plan.get('version')!=1 or plan.get('ready_for_apply') is not True or plan['conditions']!=CONDITIONS or plan['artifacts']!=artifacts() or plan['dispatch']!=policy() or plan['ledger']!=dict(records=seed(),sha256=base.file_hash(LEDGER),fingerprint=f.digest(seed())) or plan['ddl']!=dict(text=DDL.read_text(encoding='utf-8'),sha256=base.file_hash(DDL)):raise ValueError('Frozen F1 plan/artifacts/ledger changed')

def policy_row(c):
 rows=c.execute("SELECT detail FROM forecast_refresh_checks WHERE source_id='activation-policy' ORDER BY checked_at").fetchall()
 if len(rows)!=1:raise ValueError('One immutable F1 policy required')
 return rows[0][0]

def authorized(c,token,check_schema=True):
 if token.get("version")==5:
  from app.database.forecast_f1_authorization_financial import authorized as financial_authorized
  return financial_authorized(c,token,check_schema)
 if token.get("version")==4:
  from app.database.forecast_f1_authorization_cpi import authorized as cpi_authorized
  return cpi_authorized(c,token,check_schema)
 if token.get("version")==3:
  from app.database.forecast_f1_authorization_bls import authorized as authorize_bls
  return authorize_bls(c,token,check_schema)
 if token.get("version")==2:
  from app.database.forecast_f1_authorization_v2 import authorized as authorize_v2
  return authorize_v2(c,token,check_schema)
 if set(token)!={'plan_sha256','target','artifacts'} or token['artifacts']!=artifacts() or base.target_identity(c)!=token['target'] or not 170000<=c.info.server_version<180000:raise ValueError('F1 runtime target/artifacts changed')
 row=policy_row(c)
 if row['plan_sha256']!=token['plan_sha256'] or row['target']!=token['target'] or row['artifacts']!=token['artifacts'] or row['dispatch']!=policy() or row['reference_data']!=reference_data(c):raise ValueError('F1 policy/reference data changed')
 if check_schema and row['schema_sha256']!=f.digest(schema_state(c)):raise ValueError('F1 schema/dependencies changed')
 return row

def verify(c,plan,seed_only=False):
 frozen(plan)
 with c.transaction():
  c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
  token=dict(plan_sha256=f.digest(plan),target=plan['target'],artifacts=plan['artifacts']);authorized(c,token)
  actual=[(str(x[0]),x[1],x[2]) for x in c.execute('SELECT forecast_id,fingerprint,payload FROM forecast_vintages WHERE version=1').fetchall()]
  expected=[(str(uuid5(NAMESPACE_URL,'macrolens-f1:'+f.digest(r))),f.digest(r),r) for r in plan['ledger']['records']]
  if sorted(actual,key=lambda x:x[0])!=sorted(expected,key=lambda x:x[0]):raise ValueError('F1 seed differs')
  if seed_only and (c.execute('SELECT count(*) FROM forecast_vintages').fetchone()[0]!=20 or c.execute('SELECT count(*) FROM forecast_freezes').fetchone()[0]!=0 or c.execute('SELECT count(*) FROM forecast_refresh_checks').fetchone()[0]!=2):raise ValueError('F1 initial counts differ')
 return dict(outcome='verified',plan_sha256=f.digest(plan),seed_count=20)

def apply(c,plan,target_confirmation,hash_confirmation,backup):
 if target_confirmation!=plan['target_label'] or hash_confirmation!=f.digest(plan):raise ValueError('Separate exact F1 target/hash approval required')
 frozen(plan);check_backup(backup,plan)
 # Idempotent path is genuinely read-only, with no timestamps/versions changed.
 with c.transaction():
  c.execute('SET TRANSACTION READ ONLY')
  if base.target_identity(c)!=plan['target']:raise ValueError('Wrong target')
  exists=tuple(bool(c.execute('SELECT to_regclass(%s)',(t,)).fetchone()[0]) for t in f.TABLES)
 if all(exists):return {**verify(c,plan),'outcome':'already_initialized','runtime_token':dict(plan_sha256=hash_confirmation,target=plan['target'],artifacts=plan['artifacts'])}
 if any(exists):raise ValueError('Partial F1 store')
 with c.transaction():
  c.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ WRITE');c.execute('SET LOCAL search_path TO public,pg_catalog');c.execute("SET LOCAL lock_timeout='5s'");c.execute("SET LOCAL statement_timeout='120s'")
  for lock in CONDITIONS['locks']:
   if not c.execute('SELECT pg_try_advisory_xact_lock(%s)',(lock,)).fetchone()[0]:raise ValueError('Concurrent F1 activation/worker')
  c.execute(sql.SQL('LOCK TABLE {} IN SHARE MODE').format(sql.SQL(',').join(sql.Identifier(t) for t in (*REF_TABLES,*MACRO_REF_TABLES))))
  if base.target_identity(c)!=plan['target'] or reference_data(c)!=plan['reference_data'] or schema_state(c)!=plan['reference']['before']:raise ValueError('F1 protected target/references/schema changed')
  c.execute(plan['ddl']['text'])
  detail=dict(plan_sha256=hash_confirmation,target=plan['target'],artifacts=plan['artifacts'],dispatch=plan['dispatch'],reference_data=plan['reference_data'],schema_sha256=f.digest(plan['reference']['after']))
  c.execute("INSERT INTO forecast_refresh_checks(check_id,source_id,outcome,retry_at,detail) VALUES(%s,'activation-policy','success','2099-01-01',%s)",(uuid5(NAMESPACE_URL,'f1-policy:'+hash_confirmation),Jsonb(detail)))
  # Private writer preserves isolated guards; only this exact controlled plan
  # reaches it on a normal target. IDs and complete payloads are frozen.
  if f._append_prepared(c,plan['ledger']['records'],lambda r:uuid5(NAMESPACE_URL,'macrolens-f1:'+f.digest(r)))!=20:raise ValueError('F1 seed count')
  c.execute("INSERT INTO forecast_refresh_checks(check_id,source_id,outcome,retry_at,detail) VALUES(%s,'cleveland-inflation','success',clock_timestamp()+interval '1 day',%s)",(uuid5(NAMESPACE_URL,'f1-seed-check:'+hash_confirmation),Jsonb(dict(kind='seed_cooldown_not_new_http',source_receipt=json.loads(LEDGER.read_text(encoding='utf-8'))['source_receipt']))))
  if schema_state(c)!=plan['reference']['after'] or reference_data(c)!=plan['reference_data']:raise ValueError('F1 postconditions changed')
  frozen(plan)  # Recheck on-disk code/ledger/rights immediately before COMMIT.
  if c.execute('SELECT count(*) FROM forecast_vintages').fetchone()[0]!=20:raise ValueError('F1 seed incomplete')
 return dict(outcome='created',plan_sha256=hash_confirmation,target=plan['target'],runtime_token=dict(plan_sha256=hash_confirmation,target=plan['target'],artifacts=plan['artifacts']))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','plan','apply','verify','enable-runtime']);p.add_argument('--plan',type=Path);p.add_argument('--backup',type=Path);p.add_argument('--identity',type=Path);p.add_argument('--reference',type=Path);p.add_argument('--confirm-target');p.add_argument('--confirm-plan');p.add_argument('--out',type=Path,required=True);args=p.parse_args()
 if args.out.exists():raise ValueError('Refuse overwrite')
 read=lambda path:json.loads(path.read_text(encoding='utf-8'))
 if args.command=='enable-runtime':
  from app.forecast_f1_runtime import TOKEN
  receipt=read(args.plan);result=receipt['runtime_token']
  if args.out.resolve()!=TOKEN.resolve() or args.confirm_plan!=result['plan_sha256'] or args.confirm_target!=base.target_label(result['target']):raise ValueError('Explicit F1 runtime approval required')
  with get_independent_connection() as c:c.read_only=True;authorized(c,result)
 else:
  with get_independent_connection() as c:
   if args.command=='prepare':c.read_only=True;result=prepare(c,read(args.identity),read(args.reference),read(args.backup))
   elif args.command=='plan':
    c.read_only=True;result=read(args.plan);frozen(result)
    if prepare(c,result['target'],result['reference'],read(args.backup))!=result:raise ValueError('Plan no longer matches live target/references')
   elif args.command=='verify':c.read_only=True;result=verify(c,read(args.plan))
   else:result=apply(c,read(args.plan),args.confirm_target,args.confirm_plan,read(args.backup))
 args.out.parent.mkdir(parents=True,exist_ok=True)
 with args.out.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
 print(json.dumps(dict(command=args.command,sha256=f.digest(result) if args.command in ('prepare','plan') else result.get('plan_sha256'))))

if __name__=='__main__':main()
