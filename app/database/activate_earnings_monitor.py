"""Separately approved monitor activation. Prepare is strictly read-only.

No normal apply unless the user approves THIS complete new plan. The old
E2D/E2E tokens never authorize a new verification method or background writes.
"""
import argparse
import json
from pathlib import Path
from psycopg import sql
from psycopg.types.json import Jsonb
from app import earnings_monitor as monitor, earnings_reports as reports
from app.database import activate_earnings as base, activate_earnings_financials as financial
from app.database.connection import get_independent_connection
from app.database.activate_earnings_history_v2 import schema_state

TABLES = tuple(sorted((*reports.TABLES,'earnings_companies','earnings_company_aliases','earnings_periods',
                       'earnings_events','earnings_source_evidence','earnings_date_confirmations',
                       'earnings_financial_documents','earnings_financial_observations','earnings_historical_reports')))
NEW_TABLES = ('earnings_monitor_policy','earnings_report_checks')
CONDITIONS = dict(isolation='READ COMMITTED',lock_timeout='5s',statement_timeout='120s',
                  advisory_locks=[726530022,726530020],preserve_tables=list(TABLES),
                  runtime='separate approved token after successful COMMIT and verification',
                  scopes='only reviewed source bindings; other publishers require review',
                  post_commit='read-only schema/data/empty audit checks; no automatic restore')


def prepare(connection,target,reference,backup):
    with connection.transaction():
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        if base.target_identity(connection)!=target or not 170000<=connection.info.server_version<180000:
            raise ValueError('Exact PG17 target required')
        if any(connection.execute("SELECT to_regclass('earnings_monitor_policy'),to_regclass('earnings_report_checks')").fetchone()):
            raise ValueError('Monitor already/partially activated')
        catalog=schema_state(connection)
        if base.digest(catalog)!=base.digest(reference['before']):
            raise ValueError('Protected schema changed')
        snapshots=financial.table_snapshots(connection,TABLES)
    result=dict(version=1,ready_for_apply=True,status='awaiting_separate_monitor_approval',target=target,
                target_label=base.target_label(target),artifacts=monitor.artifacts(),
                protected_snapshots=snapshots,reference=reference,
                ddl=monitor.SCHEMA.read_text(encoding='utf-8'),conditions=CONDITIONS)
    check_backup(backup,result)
    return result


def check_backup(backup,plan):
    proof=financial.check_backup(backup,plan['target'])
    if ({t:proof['source_snapshots'][t] for t in TABLES}!=plan['protected_snapshots']
        or proof['source_earnings_signature']!=base.digest(plan['reference']['before']['catalog'])):
        raise ValueError('Backup protected data/schema differ')


def apply(connection,plan,target_confirmation,hash_confirmation,backup):
    if hash_confirmation!=base.digest(plan) or target_confirmation!=plan['target_label']:
        raise ValueError('Separate full monitor hash/target approval required')
    if (plan.get('version')!=1 or plan.get('ready_for_apply') is not True
        or plan['artifacts']!=monitor.artifacts() or plan['conditions']!=CONDITIONS
        or plan['ddl']!=monitor.SCHEMA.read_text(encoding='utf-8')):
        raise ValueError('Frozen monitor activation changed')
    check_backup(backup,plan)
    with connection.transaction():
        connection.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ WRITE')
        connection.execute('SET LOCAL search_path TO public,pg_catalog')
        connection.execute("SET LOCAL lock_timeout='5s'")
        connection.execute("SET LOCAL statement_timeout='120s'")
        for key in CONDITIONS['advisory_locks']:
            if not connection.execute('SELECT pg_try_advisory_xact_lock(%s)',(key,)).fetchone()[0]:
                raise ValueError('Concurrent Earnings worker/activation')
        connection.execute(sql.SQL('LOCK TABLE {} IN SHARE MODE').format(sql.SQL(',').join(sql.Identifier(t) for t in TABLES)))
        if base.target_identity(connection)!=plan['target']:
            raise ValueError('Target changed')
        if financial.table_snapshots(connection,TABLES)!=plan['protected_snapshots']:
            raise ValueError('Protected Earnings data changed')
        if base.digest(schema_state(connection))!=base.digest(plan['reference']['before']):
            raise ValueError('Schema changed or previous/partial activation')
        connection.execute(plan['ddl'])
        connection.execute('INSERT INTO earnings_monitor_policy(id,approved_plan_sha256,target,artifacts,schema_sha256) VALUES(1,%s,%s,%s,%s)',
                           (hash_confirmation,Jsonb(plan['target']),Jsonb(plan['artifacts']),base.digest(plan['reference']['after'])))
        if (base.digest(schema_state(connection))!=base.digest(plan['reference']['after'])
            or financial.table_snapshots(connection,TABLES)!=plan['protected_snapshots']
            or connection.execute('SELECT count(*) FROM earnings_report_checks').fetchone()[0]!=0):
            raise ValueError('Monitor activation postconditions failed')
    return dict(outcome='created',approved_plan_sha256=hash_confirmation,target=plan['target'],
                runtime_token=dict(plan_sha256=hash_confirmation,target=plan['target'],artifacts=plan['artifacts']))


def reference(connection):
    before=schema_state(connection);connection.rollback()
    with connection.transaction(force_rollback=True):
        connection.execute(monitor.SCHEMA.read_text(encoding='utf-8'))
        after=schema_state(connection)
    return json.loads(json.dumps(dict(before=before,after=after)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['prepare','apply','enable-runtime'])
    p.add_argument('--plan',type=Path);p.add_argument('--backup',type=Path)
    p.add_argument('--reference',type=Path);p.add_argument('--identity',type=Path)
    p.add_argument('--confirm-target');p.add_argument('--confirm-plan');p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if args.out.exists():raise ValueError('Refuse overwrite')
    read=lambda path:json.loads(path.read_text(encoding='utf-8'))
    if args.command=='enable-runtime':
        receipt=read(args.plan);token=receipt['runtime_token']
        if args.confirm_plan!=token['plan_sha256'] or args.confirm_target!=base.target_label(token['target']):
            raise ValueError('Explicit runtime approval required')
        if args.out.resolve()!=monitor.TOKEN.resolve():raise ValueError('Exact runtime token path required')
        with get_independent_connection() as c:
            c.read_only=True;monitor.authorized(c,token)
        result=token
    else:
        with get_independent_connection() as c:
            if args.command=='prepare':
                c.read_only=True;result=prepare(c,read(args.identity),read(args.reference),read(args.backup))
            else:result=apply(c,read(args.plan),args.confirm_target,args.confirm_plan,read(args.backup))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(dict(command=args.command,plan_sha256=base.digest(result) if args.command=='prepare' else args.confirm_plan)))


if __name__=='__main__':main()
