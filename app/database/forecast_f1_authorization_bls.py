"""One explicitly reviewed BLS backend upgrade, preserving the immutable V1/V2 chain."""
import argparse
import json
from pathlib import Path
from uuid import uuid5,NAMESPACE_URL
from psycopg.types.json import Jsonb
from psycopg import sql
from app.database import forecast_f1_authorization_v2 as old
from app.database import activate_forecast_f1 as legacy, activate_earnings as base, activate_earnings_financials as financial
from app import forecast_f1 as model

SOURCE='activation-bls-revision'
LOCKS=(726530032,726530031,726530033)
CONDITIONS=dict(version=3,ddl=False,scope='one BLS Employment Situation backend upgrade',
    writes='one authorization revision, one reviewed BLS document, one non-HTTP seed receipt',forecast_import=False,
    previous='exactly one complete V2 UI revision',runtime='verified separate token; no normal auto-upgrade')


def predecessor(c):
    rows=old.revisions(c)
    if len(rows)!=1:raise ValueError('Exactly one complete V2 predecessor required')
    p=rows[0]['plan'];root=old.root_policy(c)
    if p['version']!=2 or p['revision']!=1 or p['original_policy']!=root:raise ValueError('Foreign predecessor/root')
    h=p['historical_plan'];policy=root['detail']
    if (model.digest(h)!=p['previous_plan_sha256'] or policy['plan_sha256']!=p['previous_plan_sha256']
        or h['artifacts']!=policy['artifacts'] or h['target']!=policy['target']
        or p['dispatch']!=legacy.policy() or p['dispatch']!=h['dispatch'] or policy['dispatch']!=p['dispatch']
        or p['reference_data']!=policy['reference_data'] or p['reference_data']!=h['reference_data']
        or model.digest(p['schema'])!=policy['schema_sha256'] or h['reference']['after']!=p['schema']
        or h['ledger']['records']!=legacy.seed()):raise ValueError('Invalid immutable historical chain')
    return rows[0]


def revision(c):
    return c.execute('SELECT check_id,outcome,detail FROM forecast_refresh_checks WHERE source_id=%s',(SOURCE,)).fetchall()


def token_for(p):return dict(version=3,plan_sha256=model.digest(p),target=p['target'],artifacts=p['artifacts'])


def validate_seed(c,seed):
    import hashlib
    from datetime import datetime,timedelta,timezone
    from app.ingestion import bls_employment as source
    from app.database.connection import shared_connection
    if set(seed)!={'id','source','kind','source_url','retrieved_at','http_status','raw_hash','raw_path','metadata'}:raise ValueError('Incomplete reviewed snapshot')
    meta=seed['metadata'];raw=meta['raw_utf8'].encode('utf-8');event=meta['event']
    if (seed['source']!=source.SOURCE or seed['kind']!='employment-batch' or seed['source_url']!=source.URL or seed['http_status']!=200
        or hashlib.sha256(raw).hexdigest()!=seed['raw_hash'] or Path(seed['raw_path']).read_bytes()!=raw
        or meta['contract']!=json.loads(json.dumps(source.POLICY)) or source.parse(raw,event['reference_period'])!=meta['readings']):raise ValueError('Unverified BLS snapshot')
    stamp=source.instant(seed['retrieved_at']);scheduled=source.instant(event['scheduled_at'])
    if not scheduled<=stamp<=datetime.now(timezone.utc):raise ValueError('BLS capture precedes release or is in future')
    expected=uuid5(NAMESPACE_URL,source.SOURCE+':'+event['release_date']+':'+event['reference_period']+':'+seed['raw_hash'])
    if str(expected)!=seed['id']:raise ValueError('Wrong BLS document identity')
    with shared_connection(c):eligible=source.events(scheduled+timedelta(seconds=1))
    if not any(all(e.get(k)==event.get(k) for k in ('release_id','release_date','reference_period','scheduled_at')) for e in eligible):raise ValueError('BLS seed schedule or period changed')


def stored_seed(c,p):
    seed=p['seed'];row=c.execute('SELECT id::text,source,kind,source_url,retrieved_at,http_status,raw_hash,raw_path,metadata FROM publisher_documents WHERE id=%s',(seed['id'],)).fetchone()
    if not row:raise ValueError('Reviewed BLS seed missing')
    actual=dict(zip(('id','source','kind','source_url','retrieved_at','http_status','raw_hash','raw_path','metadata'),row));actual['retrieved_at']=row[4].isoformat()
    if actual!=seed:raise ValueError('Reviewed BLS document changed')


def check(c,p):
    from app.ingestion.bls_employment import POLICY
    keys={'version','ready_for_apply','target','predecessor','artifacts','schema','references','dispatch','bls_policy','protected','delivery','conditions','seed'}
    if set(p)!=keys or p['version']!=3 or p['ready_for_apply'] is not True or p['conditions']!=CONDITIONS:raise ValueError('Invalid BLS upgrade plan')
    if p['artifacts']!=old.artifacts() or p['bls_policy']!=json.loads(json.dumps(POLICY)) or p['dispatch']!=legacy.policy():raise ValueError('Frozen backend/source policy changed')
    if not 170000<=c.info.server_version<180000 or base.target_identity(c)!=p['target']:raise ValueError('Exact PG17 target required')
    validate_seed(c,p['seed'])
    pred=predecessor(c)
    if pred!=p['predecessor'] or p['schema']!=pred['plan']['schema'] or p['references']!=pred['plan']['reference_data']:raise ValueError('Broken predecessor continuity')
    if legacy.schema_state(c)!=p['schema'] or legacy.reference_data(c)!=p['references']:raise ValueError('Schema or critical reference changed')
    old_target=pred['plan']['target'];new=p['target']
    if new!=old_target and not(new['host'] in ('localhost','127.0.0.1') and new['port']!=5432 and new['user']=='macrolens_ci' and new['database'].startswith('macrolens_forecast_f1_ui_')):raise ValueError('Only own clone may retain original predecessor identity')


def prepare(c,delivery,backup,seed):
    from app.ingestion.bls_employment import POLICY
    with c.transaction():
        c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        p=dict(version=3,ready_for_apply=True,target=base.target_identity(c),predecessor=predecessor(c),artifacts=old.artifacts(),
            schema=legacy.schema_state(c),references=legacy.reference_data(c),dispatch=legacy.policy(),bls_policy=json.loads(json.dumps(POLICY)),
            protected=financial.table_snapshots(c,model.TABLES),delivery=delivery,conditions=CONDITIONS,seed=seed)
        check(c,p);financial.check_backup(backup,p['target'])
        if any(backup['source_snapshots'].get(t)!=v for t,v in p['protected'].items()):raise ValueError('Backup protected state differs')
        if revision(c):raise ValueError('Upgrade exists: verify, never silently prepare a new plan')
    return p


def authorized(c,t,check_schema=True):
    if t.get("version")==5:
        from app.database.forecast_f1_authorization_financial import authorized as financial_authorized
        return financial_authorized(c,t,check_schema)
    if t.get('version')==4:
        from app.database.forecast_f1_authorization_cpi import authorized as cpi_authorized
        return cpi_authorized(c,t,check_schema)
    if set(t)!={'version','plan_sha256','target','artifacts'} or t['version']!=3:raise ValueError('BLS requires separately approved version-3 token')
    rows=revision(c)
    if len(rows)!=1:raise ValueError('One complete BLS authorization revision required')
    identifier,outcome,detail=rows[0]
    if set(detail)!={'plan','plan_sha256'} or model.digest(detail['plan'])!=detail['plan_sha256'] or outcome!='success':raise ValueError('Invalid BLS authorization receipt')
    if str(identifier)!=str(uuid5(NAMESPACE_URL,'f1-bls-upgrade:'+detail['plan_sha256'])) or t!=token_for(detail['plan']):raise ValueError('Foreign or stale token')
    check(c,detail['plan']);stored_seed(c,detail['plan']);return detail['plan']


def apply(c,p,target_confirmation,hash_confirmation,backup,fail_after_insert=False):
    if target_confirmation!=base.target_label(p['target']) or hash_confirmation!=model.digest(p):raise ValueError('Separate exact target/hash approval required')
    financial.check_backup(backup,p['target'])
    with c.transaction():
        c.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ WRITE')
        c.execute("SET LOCAL lock_timeout='5s'");c.execute("SET LOCAL statement_timeout='120s'")
        for lock in LOCKS:
            if not c.execute('SELECT pg_try_advisory_xact_lock(%s)',(lock,)).fetchone()[0]:raise ValueError('Concurrent upgrade/worker')
        c.execute(sql.SQL('LOCK TABLE {} IN SHARE MODE').format(sql.SQL(',').join(sql.Identifier(t) for t in (*legacy.REF_TABLES,*legacy.MACRO_REF_TABLES,'forecast_vintages','forecast_freezes'))))
        c.execute('LOCK TABLE forecast_refresh_checks IN SHARE ROW EXCLUSIVE MODE');check(c,p)
        if revision(c):
            authorized(c,token_for(p));return dict(outcome='already_initialized',plan_sha256=hash_confirmation)
        if financial.table_snapshots(c,model.TABLES)!=p['protected']:raise ValueError('Protected data changed since prepare')
        seed=p['seed']
        c.execute('INSERT INTO publisher_documents(id,source,kind,source_url,retrieved_at,http_status,raw_hash,raw_path,metadata) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (seed['id'],seed['source'],seed['kind'],seed['source_url'],seed['retrieved_at'],seed['http_status'],seed['raw_hash'],seed['raw_path'],Jsonb(seed['metadata'])))
        from app.ingestion.bls_employment import SOURCE as BLS_SOURCE
        c.execute("INSERT INTO source_check_runs(id,resource,attempted_at,finished_at,status,scope) VALUES(%s,%s,clock_timestamp(),clock_timestamp(),'success',%s)",
            (uuid5(NAMESPACE_URL,'bls-reviewed-seed:'+hash_confirmation),BLS_SOURCE+':seed',Jsonb(dict(phase='reviewed_snapshot_import_not_new_http',raw_hash=seed['raw_hash'],original_captured_at=seed['retrieved_at'],plan_sha256=hash_confirmation))))
        c.execute("INSERT INTO forecast_refresh_checks(check_id,source_id,outcome,retry_at,detail) VALUES(%s,%s,'success','2099-01-01',%s)",
            (uuid5(NAMESPACE_URL,'f1-bls-upgrade:'+hash_confirmation),SOURCE,Jsonb(dict(plan=p,plan_sha256=hash_confirmation))))
        if fail_after_insert:c.execute('SELECT 1/0')
        authorized(c,token_for(p))
    return dict(outcome='created',plan_sha256=hash_confirmation)


def verify(c,p):
    with c.transaction():
        c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        authorized(c,token_for(p))
        protected=financial.table_snapshots(c,('forecast_vintages','forecast_freezes'))
        if any(v!=p['protected'][k] for k,v in protected.items()):raise ValueError('Forecast data changed during cutover')
    return dict(outcome='verified',plan_sha256=model.digest(p),runtime_token=token_for(p))


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
