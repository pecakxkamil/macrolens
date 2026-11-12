"""Explicit CPI V4 upgrade, pinned to the approved V3 predecessor. No startup APPLY."""
import json
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid5,NAMESPACE_URL
from psycopg import sql
from psycopg.types.json import Jsonb
from app import forecast_f1 as model
from app.database import forecast_f1_authorization_bls as v3

SOURCE='activation-cpi-revision'
PREDECESSOR_SHA='374e93e3c7f21cf232db989e0532045c073328f71b2e4c3e5b3da3265499e2ad'
ARTIFACTS_SHA='541d41bf1a7156f1f9d3e90d9f037428118e0c19790309c9309f60be38823fb8'
CONDITIONS=dict(version=4,scope='CPI only; shared BLS budget with existing Employment window unchanged',
 ddl=False,writes='one reviewed CPI document, one non-HTTP receipt, one append-only authorization revision',
 forecast_methodology='unchanged SA model subjects; NSA readings excluded from SA evidence',
 runtime='separate verified V4 token; no automatic normal upgrade')


def predecessor(c):
 rows=v3.revision(c)
 if len(rows)!=1:raise ValueError('Exactly one complete V3 predecessor required')
 identifier,outcome,detail=rows[0];p=detail['plan']
 if outcome!='success' or model.digest(p)!=PREDECESSOR_SHA or detail['plan_sha256']!=PREDECESSOR_SHA:
  raise ValueError('Not the explicitly approved V3 predecessor')
 if str(identifier)!=str(uuid5(NAMESPACE_URL,'f1-bls-upgrade:'+PREDECESSOR_SHA)):
  raise ValueError('Foreign V3 receipt identity')
 if model.digest(p['artifacts'])!=ARTIFACTS_SHA or p['conditions']!=v3.CONDITIONS:
  raise ValueError('Historical V3 artifacts/conditions changed')
 if p['predecessor']!=v3.predecessor(c):raise ValueError('V1/V2/V3 continuity changed')
 if v3.legacy.schema_state(c)!=p['schema'] or v3.legacy.reference_data(c)!=p['references']:
  raise ValueError('Historical schema/reference data changed')
 if v3.legacy.policy()!=p['dispatch']:raise ValueError('Forecast dispatch changed')
 v3.validate_seed(c,p['seed']);v3.stored_seed(c,p)
 return detail


def own_clone(target):
 return target['host'] in ('localhost','127.0.0.1') and target['port']==55553 and target['user']=='macrolens_ci' and target['database'].startswith('macrolens_forecast_f1_ui_')


def validate_seed(c,seed):
 from app.ingestion import bls_cpi as source
 import hashlib
 if seed is None:return
 if set(seed)!={'id','source','kind','source_url','retrieved_at','http_status','raw_hash','raw_path','metadata'}:raise ValueError('Incomplete CPI seed')
 meta=seed['metadata'];raw=meta['raw_utf8'].encode('utf-8');event=meta['event']
 if (seed['source']!=source.SOURCE or seed['kind']!='cpi-batch' or seed['source_url']!=source.URL
  or seed['http_status']!=200 or hashlib.sha256(raw).hexdigest()!=seed['raw_hash']
  or Path(seed['raw_path']).read_bytes()!=raw or meta['contract']!=json.loads(json.dumps(source.POLICY))
  or source.parse(raw,event['reference_period'])!=meta['readings']):raise ValueError('Unverified CPI seed')
 stamp=source.instant(seed['retrieved_at']);at=source.instant(event['scheduled_at'])
 if not at<=stamp<=datetime.now(timezone.utc):raise ValueError('CPI capture chronology invalid')
 expected=uuid5(NAMESPACE_URL,source.SOURCE+':'+event['release_date']+':'+event['reference_period']+':'+seed['raw_hash'])
 if str(expected)!=seed['id']:raise ValueError('CPI seed identity changed')
 from app.database.connection import shared_connection
 with shared_connection(c):eligible=source.events(at)
 if not any(all(e[k]==event[k] for k in ('release_id','release_date','reference_period','scheduled_at')) for e in eligible):
  raise ValueError('CPI seed schedule/period changed')


def check(c,p):
 from app.ingestion.bls_cpi import POLICY
 keys={'version','ready_for_apply','test_only','target','predecessor','artifacts','schema','references','dispatch','cpi_policy','protected','delivery','conditions','seed'}
 if set(p)!=keys or p['version']!=4 or p['conditions']!=CONDITIONS:raise ValueError('Invalid CPI plan')
 if p['test_only']:
  if not own_clone(p['target']) or p['ready_for_apply'] is not False:raise ValueError('Test-only token requires own real clone')
 elif p['ready_for_apply'] is not True or p['seed'] is None:raise ValueError('Final production plan needs a reviewed capture')
 if v3.base.target_identity(c)!=p['target'] or not 170000<=c.info.server_version<180000:raise ValueError('Exact PG17 target required')
 if p['predecessor']!=predecessor(c):raise ValueError('CPI predecessor changed')
 if p['artifacts']!=v3.old.artifacts() or p['cpi_policy']!=json.loads(json.dumps(POLICY)):
  raise ValueError('Candidate code/source policy changed')
 if p['schema']!=v3.legacy.schema_state(c) or p['references']!=v3.legacy.reference_data(c) or p['dispatch']!=v3.legacy.policy():
  raise ValueError('Schema, references or F1 dispatch changed')
 validate_seed(c,p['seed'])


def token_for(p):return dict(version=4,plan_sha256=model.digest(p),target=p['target'],artifacts=p['artifacts'])


def prepare(c,delivery,backup,seed,test_only=False):
 from app.ingestion.bls_cpi import POLICY
 with c.transaction():
  c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
  p=dict(version=4,ready_for_apply=not test_only,test_only=test_only,target=v3.base.target_identity(c),
   predecessor=predecessor(c),artifacts=v3.old.artifacts(),schema=v3.legacy.schema_state(c),
   references=v3.legacy.reference_data(c),dispatch=v3.legacy.policy(),cpi_policy=json.loads(json.dumps(POLICY)),
   protected=v3.financial.table_snapshots(c,('forecast_vintages','forecast_freezes')),
   delivery=delivery,conditions=CONDITIONS,seed=seed)
  check(c,p);v3.financial.check_backup(backup,p['target'])
  if any(backup['source_snapshots'].get(t)!=v for t,v in p['protected'].items()):raise ValueError('Fresh backup required')
 return p


def authorized(c,t,check_schema=True):
 if set(t)!={'version','plan_sha256','target','artifacts'} or t['version']!=4:raise ValueError('CPI requires separate V4 authorization')
 rows=c.execute('SELECT check_id,outcome,detail FROM forecast_refresh_checks WHERE source_id=%s',(SOURCE,)).fetchall()
 if len(rows)!=1:raise ValueError('Exactly one CPI revision required')
 identifier,outcome,detail=rows[0];p=detail['plan']
 if (outcome!='success' or detail['plan_sha256']!=model.digest(p) or t!=token_for(p)
  or str(identifier)!=str(uuid5(NAMESPACE_URL,'f1-cpi-upgrade:'+model.digest(p)))):raise ValueError('Foreign CPI token/receipt')
 check(c,p)
 if p['seed']:
  row=c.execute('SELECT raw_hash,metadata FROM publisher_documents WHERE id=%s',(p['seed']['id'],)).fetchone()
  if not row or row!=(p['seed']['raw_hash'],p['seed']['metadata']):raise ValueError('Reviewed CPI seed changed')
 return p


def apply(c,p,target_confirmation,hash_confirmation,backup,fail_after_insert=False):
 if target_confirmation!=v3.base.target_label(p['target']) or hash_confirmation!=model.digest(p):raise ValueError('Separate exact target/hash approval required')
 v3.financial.check_backup(backup,p['target'])
 with c.transaction():
  c.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ WRITE')
  c.execute("SET LOCAL lock_timeout='5s'");c.execute("SET LOCAL statement_timeout='120s'")
  for lock in v3.LOCKS:
   if not c.execute('SELECT pg_try_advisory_xact_lock(%s)',(lock,)).fetchone()[0]:raise ValueError('Concurrent worker/upgrade')
  tables=(*v3.legacy.REF_TABLES,*v3.legacy.MACRO_REF_TABLES,'forecast_vintages','forecast_freezes')
  c.execute(sql.SQL('LOCK TABLE {} IN SHARE MODE').format(sql.SQL(',').join(sql.Identifier(t) for t in tables)))
  c.execute('LOCK TABLE forecast_refresh_checks IN SHARE ROW EXCLUSIVE MODE');check(c,p)
  if c.execute('SELECT 1 FROM forecast_refresh_checks WHERE source_id=%s',(SOURCE,)).fetchone():
   authorized(c,token_for(p));return dict(outcome='already_initialized',plan_sha256=hash_confirmation)
  if v3.financial.table_snapshots(c,('forecast_vintages','forecast_freezes'))!=p['protected']:raise ValueError('Forecast data changed')
  seed=p['seed']
  if seed:
   c.execute('INSERT INTO publisher_documents(id,source,kind,source_url,retrieved_at,http_status,raw_hash,raw_path,metadata) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',tuple(seed[k] for k in ('id','source','kind','source_url','retrieved_at','http_status','raw_hash','raw_path'))+(Jsonb(seed['metadata']),))
   c.execute("INSERT INTO source_check_runs(id,resource,attempted_at,finished_at,status,scope) VALUES(%s,'bls:cpi:seed',clock_timestamp(),clock_timestamp(),'success',%s)",
    (uuid5(NAMESPACE_URL,'cpi-seed:'+hash_confirmation),Jsonb(dict(phase='reviewed_snapshot_import_not_new_http',raw_hash=seed['raw_hash'],original_captured_at=seed['retrieved_at']))))
  c.execute("INSERT INTO forecast_refresh_checks(check_id,source_id,outcome,retry_at,detail) VALUES(%s,%s,'success','2099-01-01',%s)",
   (uuid5(NAMESPACE_URL,'f1-cpi-upgrade:'+hash_confirmation),SOURCE,Jsonb(dict(plan=p,plan_sha256=hash_confirmation))))
  if fail_after_insert:c.execute('SELECT 1/0')
  authorized(c,token_for(p))
 return dict(outcome='created',plan_sha256=hash_confirmation)


def verify(c,p):
 with c.transaction():
  c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');authorized(c,token_for(p))
  if v3.financial.table_snapshots(c,('forecast_vintages','forecast_freezes'))!=p['protected']:raise ValueError('Forecast changed during cutover')
 return dict(outcome='verified',plan_sha256=model.digest(p),runtime_token=token_for(p))


import argparse

def main():
    from app.database.connection import get_independent_connection
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['prepare','plan','apply','verify'])
    for a in ('plan','delivery','backup','out','seed'):parser.add_argument('--'+a,type=Path)
    parser.add_argument('--confirm-target');parser.add_argument('--confirm-plan');a=parser.parse_args()
    if not a.out or a.out.exists():raise ValueError('New output required')
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    with get_independent_connection() as c:
        c.read_only=a.command!='apply'
        if a.command=='prepare':result=prepare(c,read(a.delivery),read(a.backup),read(a.seed))
        else:
            p=read(a.plan)
            if a.command=='plan':
                result=prepare(c,p['delivery'],read(a.backup),p['seed'])
                if result!=p:raise ValueError('Plan changed')
            elif a.command=='apply':result=apply(c,p,a.confirm_target,a.confirm_plan,read(a.backup))
            else:result=verify(c,p)
    a.out.write_text(json.dumps(result,indent=2),encoding='utf-8');print(model.digest(result) if a.command in ('prepare','plan') else result['outcome'])

if __name__=='__main__':main()
